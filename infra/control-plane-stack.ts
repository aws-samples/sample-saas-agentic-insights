import * as cdk from 'aws-cdk-lib';
import * as apigateway from 'aws-cdk-lib/aws-apigateway';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as cognito from 'aws-cdk-lib/aws-cognito';
import * as events from 'aws-cdk-lib/aws-events';
import * as targets from 'aws-cdk-lib/aws-events-targets';
import * as iam from 'aws-cdk-lib/aws-iam';
import { Construct } from 'constructs';

export class ControlPlaneStack extends cdk.Stack {
  public readonly eventBus: events.EventBus;
  public readonly controlPlaneApi: apigateway.RestApi;

  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // DynamoDB table for tenant management
    const tenantsTable = new dynamodb.Table(this, 'TenantsTable', {
      tableName: 'Tenants',
      partitionKey: { name: 'tenant_id', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    // EventBridge custom bus for tenant provisioning
    this.eventBus = new events.EventBus(this, 'TenantProvisioningBus', {
      eventBusName: 'tenant-provisioning-bus',
    });

    // Cognito User Pool for SaaS admins
    const adminUserPool = new cognito.UserPool(this, 'AdminUserPool', {
      userPoolName: 'saas-admin-pool',
      selfSignUpEnabled: false,
      signInAliases: { email: true },
      autoVerify: { email: true },
      passwordPolicy: {
        minLength: 8,
        requireLowercase: true,
        requireUppercase: true,
        requireDigits: true,
        requireSymbols: true,
      },
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    const adminUserPoolClient = new cognito.UserPoolClient(this, 'AdminUserPoolClient', {
      userPool: adminUserPool,
      generateSecret: false,
      authFlows: {
        userPassword: true,
        userSrp: true,
        adminUserPassword: true,  // Required for AdminInitiateAuth
      },
    });

    // Registration Service Lambda
    const registrationFunction = new lambda.Function(this, 'RegistrationFunction', {
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'handler.handler',
      code: lambda.Code.fromAsset('src/control-plane/registration'),
      environment: {
        TENANTS_TABLE: tenantsTable.tableName,
        EVENT_BUS_NAME: this.eventBus.eventBusName,
      },
      timeout: cdk.Duration.seconds(30),
    });

    // Login Service Lambda
    const loginFunction = new lambda.Function(this, 'LoginFunction', {
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'handler.handler',
      code: lambda.Code.fromAsset('src/control-plane/login'),
      environment: {
        ADMIN_USER_POOL_ID: adminUserPool.userPoolId,
        ADMIN_USER_POOL_CLIENT_ID: adminUserPoolClient.userPoolClientId,
      },
      timeout: cdk.Duration.seconds(30),
    });

    // Grant Cognito and CloudFormation permissions to login function
    loginFunction.addToRolePolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: [
        'cognito-idp:AdminInitiateAuth',
        'cognito-idp:AdminGetUser',
        'cognito-idp:ListUserPoolClients'
      ],
      resources: ['*']  // Allow access to all user pools
    }));

    loginFunction.addToRolePolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: [
        'cloudformation:DescribeStacks'
      ],
      resources: ['*']
    }));

    // Tenant Management Service Lambda
    const tenantManagementFunction = new lambda.Function(this, 'TenantManagementFunction', {
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'handler.handler',
      code: lambda.Code.fromAsset('src/control-plane/tenant-management'),
      environment: {
        TENANTS_TABLE: tenantsTable.tableName,
        EVENT_BUS_NAME: this.eventBus.eventBusName,
      },
      timeout: cdk.Duration.seconds(30),
    });

    // Tenant Provisioning Service Lambda
    const tenantProvisioningFunction = new lambda.Function(this, 'TenantProvisioningFunction', {
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'handler.handler',
      code: lambda.Code.fromAsset('src/control-plane/tenant-provisioning'),
      environment: {
        TENANTS_TABLE: tenantsTable.tableName,
      },
      timeout: cdk.Duration.minutes(5),
    });

    // Insight Dashboard API Lambda
    const insightDashboardApiFunction = new lambda.Function(this, 'InsightDashboardApiFunction', {
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'handler.handler',
      code: lambda.Code.fromAsset('src/control-plane/insight-dashboard-api'),
      timeout: cdk.Duration.seconds(30),
      environment: {
        // Environment variables will be set via deployment script or separate stack
        // ADVANCED_COST_ANALYSIS_AGENT_ID and ADVANCED_COST_ANALYSIS_AGENT_ALIAS_ID
      },
    });

    // Grant permissions
    tenantsTable.grantReadWriteData(registrationFunction);
    tenantsTable.grantReadWriteData(tenantManagementFunction);
    tenantsTable.grantReadWriteData(tenantProvisioningFunction);

    // Grant Bedrock permissions to insight dashboard function
    insightDashboardApiFunction.addToRolePolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: [
        'bedrock-agent-runtime:InvokeAgent',
      ],
      resources: ['*'], // Will be restricted to specific agent in deployment
    }));

    this.eventBus.grantPutEventsTo(registrationFunction);
    this.eventBus.grantPutEventsTo(tenantManagementFunction);

    // Grant CDK permissions to tenant provisioning function for dynamic resource creation
    tenantProvisioningFunction.addToRolePolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: [
        'dynamodb:CreateTable',
        'dynamodb:DescribeTable',
        'dynamodb:TagResource',
        'lambda:UpdateFunctionConfiguration',
        'lambda:GetFunction',
      ],
      resources: ['*'],
    }));

    // API Gateway for Control Plane
    this.controlPlaneApi = new apigateway.RestApi(this, 'ControlPlaneApi', {
      restApiName: 'Agentic Insights Control Plane API',
      description: 'API for tenant management and authentication',
      defaultCorsPreflightOptions: {
        allowOrigins: apigateway.Cors.ALL_ORIGINS,
        allowMethods: apigateway.Cors.ALL_METHODS,
        allowHeaders: ['Content-Type', 'X-Amz-Date', 'Authorization', 'X-Api-Key', 'X-Amz-Security-Token'],
      },
    });

    // API Gateway integrations
    const registrationIntegration = new apigateway.LambdaIntegration(registrationFunction);
    const loginIntegration = new apigateway.LambdaIntegration(loginFunction);
    const tenantManagementIntegration = new apigateway.LambdaIntegration(tenantManagementFunction);
    const insightDashboardIntegration = new apigateway.LambdaIntegration(insightDashboardApiFunction);

    // API routes
    this.controlPlaneApi.root.addResource('register').addMethod('POST', registrationIntegration);
    this.controlPlaneApi.root.addResource('login').addMethod('POST', loginIntegration);
    
    const tenantsResource = this.controlPlaneApi.root.addResource('tenants');
    tenantsResource.addMethod('GET', tenantManagementIntegration);
    tenantsResource.addMethod('POST', tenantManagementIntegration);
    tenantsResource.addResource('{tenant_id}').addMethod('DELETE', tenantManagementIntegration);

    // Insight Dashboard API
    const insightDashboardResource = this.controlPlaneApi.root.addResource('insight-dashboard');
    insightDashboardResource.addMethod('POST', insightDashboardIntegration);

    // EventBridge rule for tenant provisioning
    new events.Rule(this, 'TenantProvisioningRule', {
      eventBus: this.eventBus,
      eventPattern: {
        source: ['tenant.service'],
        detailType: ['Tenant Created'],
      },
      targets: [new targets.LambdaFunction(tenantProvisioningFunction)],
    });

    // Outputs
    new cdk.CfnOutput(this, 'ControlPlaneApiUrl', {
      value: this.controlPlaneApi.url,
      description: 'Control Plane API Gateway URL',
    });

    new cdk.CfnOutput(this, 'AdminUserPoolId', {
      value: adminUserPool.userPoolId,
      description: 'Admin Cognito User Pool ID',
    });

    new cdk.CfnOutput(this, 'AdminUserPoolClientId', {
      value: adminUserPoolClient.userPoolClientId,
      description: 'Admin Cognito User Pool Client ID',
    });
  }
}
