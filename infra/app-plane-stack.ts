import * as cdk from 'aws-cdk-lib';
import * as apigateway from 'aws-cdk-lib/aws-apigateway';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as cognito from 'aws-cdk-lib/aws-cognito';
import * as events from 'aws-cdk-lib/aws-events';
import * as targets from 'aws-cdk-lib/aws-events-targets';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as cloudfront from 'aws-cdk-lib/aws-cloudfront';
import * as origins from 'aws-cdk-lib/aws-cloudfront-origins';
import * as s3deploy from 'aws-cdk-lib/aws-s3-deployment';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as logs from 'aws-cdk-lib/aws-logs';
import * as bedrock from 'aws-cdk-lib/aws-bedrock';
import * as fs from 'fs';
import * as path from 'path';
import { Construct } from 'constructs';

interface AppPlaneStackProps extends cdk.StackProps {
  eventBus: events.EventBus;
  metricsCollectorLayer?: lambda.LayerVersion;
  metricsEventBusName?: string;
}

export class AppPlaneStack extends cdk.Stack {
  public readonly appPlaneApi: apigateway.RestApi;
  public readonly authorizer: apigateway.TokenAuthorizer;
  public bedrockAgent: bedrock.CfnAgent;
  public bedrockAgentAlias: bedrock.CfnAgentAlias;

  constructor(scope: Construct, id: string, props: AppPlaneStackProps) {
    super(scope, id, props);

    // Shared DynamoDB tables
    const productsTable = new dynamodb.Table(this, 'ProductsTable', {
      tableName: 'Products',
      partitionKey: { name: 'tenant_id', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'product_id', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    const ordersTable = new dynamodb.Table(this, 'OrdersTable', {
      tableName: 'Orders',
      partitionKey: { name: 'tenant_id', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'order_id', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    // Cognito User Pools for tenants
    const basicTierUserPool = new cognito.UserPool(this, 'BasicTierUserPool', {
      userPoolName: 'basic-tier-users',
      selfSignUpEnabled: false,
      signInAliases: { email: true },
      autoVerify: { email: true },
      customAttributes: {
        tenant_id: new cognito.StringAttribute({ minLen: 1, maxLen: 256, mutable: false }),
        role: new cognito.StringAttribute({ minLen: 1, maxLen: 50, mutable: true }),
        tier: new cognito.StringAttribute({ minLen: 1, maxLen: 20, mutable: true }),
      },
      passwordPolicy: {
        minLength: 6,
        requireLowercase: false,
        requireUppercase: false,
        requireDigits: false,
        requireSymbols: false,
      },
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    const basicTierUserPoolClient = new cognito.UserPoolClient(this, 'BasicTierUserPoolClient', {
      userPool: basicTierUserPool,
      generateSecret: false,
      authFlows: {
        userPassword: true,
        userSrp: true,
        adminUserPassword: true,
      },
    });

    const premiumTierUserPool = new cognito.UserPool(this, 'PremiumTierUserPool', {
      userPoolName: 'premium-tier-users',
      selfSignUpEnabled: false,
      signInAliases: { email: true },
      autoVerify: { email: true },
      customAttributes: {
        tenant_id: new cognito.StringAttribute({ minLen: 1, maxLen: 256, mutable: false }),
        role: new cognito.StringAttribute({ minLen: 1, maxLen: 50, mutable: true }),
        tier: new cognito.StringAttribute({ minLen: 1, maxLen: 20, mutable: true }),
      },
      passwordPolicy: {
        minLength: 6,
        requireLowercase: false,
        requireUppercase: false,
        requireDigits: false,
        requireSymbols: false,
      },
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    const premiumTierUserPoolClient = new cognito.UserPoolClient(this, 'PremiumTierUserPoolClient', {
      userPool: premiumTierUserPool,
      generateSecret: false,
      authFlows: {
        userPassword: true,
        userSrp: true,
        adminUserPassword: true,
      },
    });

    // Lambda Authorizer
    const authorizerFunction = new lambda.Function(this, 'AuthorizerFunction', {
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'handler.handler',
      code: lambda.Code.fromAsset('src/app-plane/authorizer'),
      environment: {
        BASIC_USER_POOL_ID: basicTierUserPool.userPoolId,
        PREMIUM_USER_POOL_ID: premiumTierUserPool.userPoolId,
      },
      timeout: cdk.Duration.seconds(30),
    });

    // Product Service Lambda
    const productFunction = new lambda.Function(this, 'ProductFunction', {
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'handler.handler',
      code: lambda.Code.fromAsset('src/app-plane/product'),
      layers: props.metricsCollectorLayer ? [props.metricsCollectorLayer] : [],
      environment: {
        PRODUCTS_TABLE: productsTable.tableName,
        METRICS_EVENT_BUS_NAME: props.metricsEventBusName || props.eventBus.eventBusName,
      },
      timeout: cdk.Duration.seconds(30),
    });

    // Order Service Lambda
    const orderFunction = new lambda.Function(this, 'OrderFunction', {
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'handler.handler',
      code: lambda.Code.fromAsset('src/app-plane/order'),
      layers: props.metricsCollectorLayer ? [props.metricsCollectorLayer] : [],
      environment: {
        ORDERS_TABLE: ordersTable.tableName,
        METRICS_EVENT_BUS_NAME: props.metricsEventBusName || props.eventBus.eventBusName,
      },
      timeout: cdk.Duration.seconds(30),
    });

    // User Creation Service Lambda (handles EventBridge events)
    const userCreationFunction = new lambda.Function(this, 'UserCreationFunction', {
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'handler.handler',
      code: lambda.Code.fromAsset('src/app-plane/user-creation'),
      environment: {
        BASIC_USER_POOL_ID: basicTierUserPool.userPoolId,
        PREMIUM_USER_POOL_ID: premiumTierUserPool.userPoolId,
      },
      timeout: cdk.Duration.seconds(30),
    });

    // User Service Lambda
    const userFunction = new lambda.Function(this, 'UserFunction', {
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'handler.handler',
      code: lambda.Code.fromAsset('src/app-plane/user'),
      layers: props.metricsCollectorLayer ? [props.metricsCollectorLayer] : [],
      environment: {
        BASIC_USER_POOL_ID: basicTierUserPool.userPoolId,
        BASIC_USER_POOL_CLIENT_ID: basicTierUserPoolClient.userPoolClientId,
        PREMIUM_USER_POOL_ID: premiumTierUserPool.userPoolId,
        PREMIUM_USER_POOL_CLIENT_ID: premiumTierUserPoolClient.userPoolClientId,
        METRICS_EVENT_BUS_NAME: props.metricsEventBusName || props.eventBus.eventBusName,
      },
      timeout: cdk.Duration.seconds(30),
    });

    // Grant permissions
    productsTable.grantReadWriteData(productFunction);
    ordersTable.grantReadWriteData(orderFunction);

    // Grant Order function permission to read Tenants table for premium tier table lookup
    orderFunction.addToRolePolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: ['dynamodb:GetItem'],
      resources: [`arn:aws:dynamodb:${this.region}:${this.account}:table/Tenants`],
    }));

    // Grant Order function permission to access premium tenant dedicated order tables
    orderFunction.addToRolePolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: ['dynamodb:Query', 'dynamodb:PutItem', 'dynamodb:GetItem', 'dynamodb:UpdateItem', 'dynamodb:DeleteItem'],
      resources: [`arn:aws:dynamodb:${this.region}:${this.account}:table/Orders-*`],
    }));

    // Grant Cognito permissions to user creation service
    userCreationFunction.addToRolePolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: [
        'cognito-idp:AdminCreateUser',
        'cognito-idp:AdminSetUserPassword',
      ],
      resources: [basicTierUserPool.userPoolArn, premiumTierUserPool.userPoolArn],
    }));

    // Grant Cognito permissions to user service
    userFunction.addToRolePolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: [
        'cognito-idp:AdminCreateUser',
        'cognito-idp:AdminSetUserPassword',
        'cognito-idp:AdminDeleteUser',
        'cognito-idp:AdminUpdateUserAttributes',
        'cognito-idp:ListUsers',
        'cognito-idp:AdminGetUser',
      ],
      resources: [basicTierUserPool.userPoolArn, premiumTierUserPool.userPoolArn],
    }));

    // Grant EventBridge permissions for metrics collection
    if (props.metricsCollectorLayer) {
      [productFunction, orderFunction, userFunction].forEach(fn => {
        fn.addToRolePolicy(new iam.PolicyStatement({
          effect: iam.Effect.ALLOW,
          actions: ['events:PutEvents'],
          resources: [props.eventBus.eventBusArn],
        }));
      });
    }

    // API Gateway for Application Plane
    this.appPlaneApi = new apigateway.RestApi(this, 'AppPlaneApi', {
      restApiName: 'Agentic Insights App Plane API',
      description: 'API for e-commerce functionality',
      defaultCorsPreflightOptions: {
        allowOrigins: apigateway.Cors.ALL_ORIGINS,
        allowMethods: apigateway.Cors.ALL_METHODS,
        allowHeaders: [
          'Content-Type',
          'X-Amz-Date',
          'Authorization', 
          'X-Api-Key',
          'X-Amz-Security-Token',
          'tenant-id',
          'tier-name'
        ],
      },
    });

    // Add Gateway Responses for CORS on error responses
    this.appPlaneApi.addGatewayResponse('Default4XXResponse', {
      type: apigateway.ResponseType.DEFAULT_4XX,
      responseHeaders: {
        'Access-Control-Allow-Origin': "'*'",
        'Access-Control-Allow-Headers': "'Content-Type,Authorization,tenant-id,tier-name'",
        'Access-Control-Allow-Methods': "'GET,POST,PUT,DELETE,OPTIONS'"
      }
    });

    this.appPlaneApi.addGatewayResponse('Default5XXResponse', {
      type: apigateway.ResponseType.DEFAULT_5XX,
      responseHeaders: {
        'Access-Control-Allow-Origin': "'*'",
        'Access-Control-Allow-Headers': "'Content-Type,Authorization,tenant-id,tier-name'",
        'Access-Control-Allow-Methods': "'GET,POST,PUT,DELETE,OPTIONS'"
      }
    });

    // Lambda authorizer for API Gateway
    this.authorizer = new apigateway.TokenAuthorizer(this, 'ApiAuthorizer', {
      handler: authorizerFunction,
      identitySource: 'method.request.header.Authorization',
      // TODO: Re-enable caching for production performance optimization
      // Currently disabled to prevent cache conflicts between HTTP methods
      // Consider using identitySource with method.request.httpMethod for cache key
      resultsCacheTtl: cdk.Duration.seconds(0), // Disabled for now
    });

    // API Gateway integrations
    const productIntegration = new apigateway.LambdaIntegration(productFunction);
    const orderIntegration = new apigateway.LambdaIntegration(orderFunction);
    const userIntegration = new apigateway.LambdaIntegration(userFunction);

    // Basic tier routes
    const basicResource = this.appPlaneApi.root.addResource('basic');
    const basicProductsResource = basicResource.addResource('products');
    basicProductsResource.addMethod('GET', productIntegration, { authorizer: this.authorizer });
    basicProductsResource.addMethod('POST', productIntegration, { authorizer: this.authorizer });
    
    const basicProductIdResource = basicProductsResource.addResource('{product_id}');
    basicProductIdResource.addMethod('GET', productIntegration, { authorizer: this.authorizer });
    basicProductIdResource.addMethod('PUT', productIntegration, { authorizer: this.authorizer });
    basicProductIdResource.addMethod('DELETE', productIntegration, { authorizer: this.authorizer });

    const basicOrdersResource = basicResource.addResource('orders');
    basicOrdersResource.addMethod('GET', orderIntegration, { authorizer: this.authorizer });
    basicOrdersResource.addMethod('POST', orderIntegration, { authorizer: this.authorizer });

    // Premium tier routes
    const premiumResource = this.appPlaneApi.root.addResource('premium');
    const premiumProductsResource = premiumResource.addResource('products');
    premiumProductsResource.addMethod('GET', productIntegration, { authorizer: this.authorizer });
    premiumProductsResource.addMethod('POST', productIntegration, { authorizer: this.authorizer });
    
    const premiumProductIdResource = premiumProductsResource.addResource('{product_id}');
    premiumProductIdResource.addMethod('GET', productIntegration, { authorizer: this.authorizer });
    premiumProductIdResource.addMethod('PUT', productIntegration, { authorizer: this.authorizer });
    premiumProductIdResource.addMethod('DELETE', productIntegration, { authorizer: this.authorizer });

    const premiumOrdersResource = premiumResource.addResource('orders');
    premiumOrdersResource.addMethod('GET', orderIntegration, { authorizer: this.authorizer });
    premiumOrdersResource.addMethod('POST', orderIntegration, { authorizer: this.authorizer });

    // Common user routes
    const userResource = this.appPlaneApi.root.addResource('user');
    userResource.addMethod('GET', userIntegration, { authorizer: this.authorizer });
    userResource.addMethod('POST', userIntegration, { authorizer: this.authorizer });
    
    const userIdResource = userResource.addResource('{user_id}');
    userIdResource.addMethod('PUT', userIntegration, { authorizer: this.authorizer });
    userIdResource.addMethod('DELETE', userIntegration, { authorizer: this.authorizer });

    // S3 buckets for web hosting (private with CloudFront OAC)
    const landingPageBucket = new s3.Bucket(this, 'LandingPageBucket', {
      bucketName: `agentic-insights-landing-${this.account}-${this.region}`,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      autoDeleteObjects: true,
    });

    const adminPanelBucket = new s3.Bucket(this, 'AdminPanelBucket', {
      bucketName: `agentic-insights-admin-${this.account}-${this.region}`,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      autoDeleteObjects: true,
    });

    const saasAppBucket = new s3.Bucket(this, 'SaasAppBucket', {
      bucketName: `agentic-insights-saas-${this.account}-${this.region}`,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      autoDeleteObjects: true,
    });

    // Origin Access Identities for CloudFront
    const landingPageOAI = new cloudfront.OriginAccessIdentity(this, 'LandingPageOAI', {
      comment: 'CloudFront access to Landing Page S3 bucket',
    });

    const adminPanelOAI = new cloudfront.OriginAccessIdentity(this, 'AdminPanelOAI', {
      comment: 'CloudFront access to Admin Panel S3 bucket',
    });

    const saasAppOAI = new cloudfront.OriginAccessIdentity(this, 'SaasAppOAI', {
      comment: 'CloudFront access to SaaS App S3 bucket',
    });

    // S3 bucket policies for OAI access
    landingPageBucket.addToResourcePolicy(
      new iam.PolicyStatement({
        resources: [landingPageBucket.arnForObjects('*')],
        actions: ['s3:GetObject'],
        principals: [
          new iam.CanonicalUserPrincipal(landingPageOAI.cloudFrontOriginAccessIdentityS3CanonicalUserId)
        ],
      })
    );

    adminPanelBucket.addToResourcePolicy(
      new iam.PolicyStatement({
        resources: [adminPanelBucket.arnForObjects('*')],
        actions: ['s3:GetObject'],
        principals: [
          new iam.CanonicalUserPrincipal(adminPanelOAI.cloudFrontOriginAccessIdentityS3CanonicalUserId)
        ],
      })
    );

    saasAppBucket.addToResourcePolicy(
      new iam.PolicyStatement({
        resources: [saasAppBucket.arnForObjects('*')],
        actions: ['s3:GetObject'],
        principals: [
          new iam.CanonicalUserPrincipal(saasAppOAI.cloudFrontOriginAccessIdentityS3CanonicalUserId)
        ],
      })
    );

    // CloudFront distributions with Origin Access Identity (OAI)
    const landingPageDistribution = new cloudfront.Distribution(this, 'LandingPageDistribution', {
      defaultBehavior: {
        origin: new origins.S3Origin(landingPageBucket, {
          originAccessIdentity: landingPageOAI,
        }),
        viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
        compress: true,
        cachePolicy: cloudfront.CachePolicy.CACHING_OPTIMIZED,
      },
      defaultRootObject: 'index.html',
      errorResponses: [
        { httpStatus: 404, responseHttpStatus: 200, responsePagePath: '/index.html' },
        { httpStatus: 403, responseHttpStatus: 200, responsePagePath: '/index.html' },
      ],
    });

    const adminPanelDistribution = new cloudfront.Distribution(this, 'AdminPanelDistribution', {
      defaultBehavior: {
        origin: new origins.S3Origin(adminPanelBucket, {
          originAccessIdentity: adminPanelOAI,
        }),
        viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
        compress: true,
        cachePolicy: cloudfront.CachePolicy.CACHING_OPTIMIZED,
      },
      defaultRootObject: 'index.html',
      errorResponses: [
        { httpStatus: 404, responseHttpStatus: 200, responsePagePath: '/index.html' },
        { httpStatus: 403, responseHttpStatus: 200, responsePagePath: '/index.html' },
      ],
    });

    const saasAppDistribution = new cloudfront.Distribution(this, 'SaasAppDistribution', {
      defaultBehavior: {
        origin: new origins.S3Origin(saasAppBucket, {
          originAccessIdentity: saasAppOAI,
        }),
        viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
        compress: true,
        cachePolicy: cloudfront.CachePolicy.CACHING_OPTIMIZED,
      },
      defaultRootObject: 'index.html',
      errorResponses: [
        { httpStatus: 404, responseHttpStatus: 200, responsePagePath: '/index.html' },
        { httpStatus: 403, responseHttpStatus: 200, responsePagePath: '/index.html' },
      ],
    });

    // Deploy web applications
    new s3deploy.BucketDeployment(this, 'LandingPageDeployment', {
      sources: [s3deploy.Source.asset('web/landing-page')],
      destinationBucket: landingPageBucket,
      distribution: landingPageDistribution,
      distributionPaths: ['/*'],
    });

    new s3deploy.BucketDeployment(this, 'AdminPanelDeployment', {
      sources: [s3deploy.Source.asset('web/admin-panel')],
      destinationBucket: adminPanelBucket,
      distribution: adminPanelDistribution,
      distributionPaths: ['/*'],
    });

    new s3deploy.BucketDeployment(this, 'SaasAppDeployment', {
      sources: [s3deploy.Source.asset('web/saas-app')],
      destinationBucket: saasAppBucket,
      distribution: saasAppDistribution,
      distributionPaths: ['/*'],
    });

    // EventBridge rule for user creation
    new events.Rule(this, 'UserCreationRule', {
      eventBus: props.eventBus,
      eventPattern: {
        source: ['tenant.service'],
        detailType: ['Admin User Creation Requested'],
      },
      targets: [new targets.LambdaFunction(userCreationFunction)],
    });

    // AI Product Description Components
    this.addAIDescriptionComponents();

    // Outputs
    new cdk.CfnOutput(this, 'AppPlaneApiUrl', {
      value: this.appPlaneApi.url,
      description: 'Application Plane API Gateway URL',
    });

    new cdk.CfnOutput(this, 'LandingPageUrl', {
      value: `https://${landingPageDistribution.distributionDomainName}`,
      description: 'Landing Page URL',
    });

    new cdk.CfnOutput(this, 'AdminPanelUrl', {
      value: `https://${adminPanelDistribution.distributionDomainName}`,
      description: 'Admin Panel URL',
    });

    new cdk.CfnOutput(this, 'SaasAppUrl', {
      value: `https://${saasAppDistribution.distributionDomainName}`,
      description: 'SaaS Application URL',
    });

    new cdk.CfnOutput(this, 'BasicTierUserPoolId', {
      value: basicTierUserPool.userPoolId,
      description: 'Basic Tier User Pool ID',
    });

    new cdk.CfnOutput(this, 'PremiumTierUserPoolId', {
      value: premiumTierUserPool.userPoolId,
      description: 'Premium Tier User Pool ID',
    });
  }

  private addAIDescriptionComponents() {
    // Load agent configuration
    const agentConfigPath = path.join(__dirname, '../src/app-plane/agents/product-desc/agent-config.yaml');
    const agentInstructionsPath = path.join(__dirname, '../src/app-plane/agents/product-desc/instructions.txt');
    
    // Parse agent config
    const agentConfigContent = fs.readFileSync(agentConfigPath, 'utf8');
    const agentName = agentConfigContent.match(/name:\s*(.+)/)?.[1]?.trim() || 'agentic-insights-product-desc-agent';
    const agentModel = agentConfigContent.match(/model:\s*(.+)/)?.[1]?.trim() || 'us.anthropic.claude-3-haiku-20240307-v1:0';
    const agentDescription = agentConfigContent.match(/description:\s*(.+)/)?.[1]?.trim() || 'AI agent for generating e-commerce product descriptions';
    
    // Load agent instructions
    const agentInstructions = fs.readFileSync(agentInstructionsPath, 'utf8').trim();

    // Create IAM role for Bedrock agent
    const bedrockAgentRole = new iam.Role(this, 'BedrockAgentRole', {
      roleName: `${agentName}-execution-role-${this.region}`,
      assumedBy: new iam.ServicePrincipal('bedrock.amazonaws.com'),
      description: `Execution role for Bedrock agent ${agentName} in ${this.region}`,
      inlinePolicies: {
        BedrockAgentPolicy: new iam.PolicyDocument({
          statements: [
            new iam.PolicyStatement({
              effect: iam.Effect.ALLOW,
              actions: [
                'bedrock:InvokeModel',
                'bedrock:GetInferenceProfile',
                'bedrock:ListInferenceProfiles'
              ],
              resources: [
                `arn:aws:bedrock:*::foundation-model/anthropic.claude-3-haiku-*`,
                `arn:aws:bedrock:${this.region}:${this.account}:inference-profile/${agentModel}`
              ]
            })
          ]
        })
      }
    });

    // Create Bedrock Agent
    this.bedrockAgent = new bedrock.CfnAgent(this, 'BedrockAgent', {
      agentName: `${agentName}-${this.region}`,
      description: `${agentDescription} in ${this.region}`,
      agentResourceRoleArn: bedrockAgentRole.roleArn,
      foundationModel: agentModel,
      instruction: agentInstructions,
      idleSessionTtlInSeconds: 1800,
      actionGroups: [],
      knowledgeBases: [],
      promptOverrideConfiguration: {
        promptConfigurations: [
          {
            promptType: 'ORCHESTRATION',
            promptCreationMode: 'OVERRIDDEN',
            promptState: 'ENABLED',
            basePromptTemplate: `{
              "anthropic_version": "bedrock-2023-05-31",
              "system": "$instruction$",
              "messages": [
                {
                  "role": "user",
                  "content": "$question$"
                }
              ]
            }`,
            inferenceConfiguration: {
              temperature: 0.7,
              topP: 0.9,
              topK: 250,
              maximumLength: 300,
              stopSequences: []
            }
          }
        ]
      }
    });

    // Create Agent Alias
    this.bedrockAgentAlias = new bedrock.CfnAgentAlias(this, 'BedrockAgentAlias', {
      agentId: this.bedrockAgent.attrAgentId,
      agentAliasName: 'prod',
      description: 'Production alias for the agent',
    });

    // Product Description Service Lambda
    const productDescFunction = new lambda.Function(this, 'ProductDescFunction', {
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'handler.handler',
      code: lambda.Code.fromAsset('src/app-plane/product-desc'),
      environment: {
        BEDROCK_AGENT_ID: this.bedrockAgent.attrAgentId,
        BEDROCK_AGENT_ALIAS_ID: this.bedrockAgentAlias.attrAgentAliasId,
        CLAUDE_INPUT_TOKEN_PRICE: '0.00025',
        CLAUDE_OUTPUT_TOKEN_PRICE: '0.00125',
      },
      timeout: cdk.Duration.seconds(30),
      memorySize: 512,
      description: 'AI Product Description Generator using Bedrock Agent',
    });

    // CloudWatch Log Group
    new logs.LogGroup(this, 'ProductDescLogGroup', {
      logGroupName: `/aws/lambda/${productDescFunction.functionName}`,
      retention: logs.RetentionDays.ONE_WEEK,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    // IAM permissions for Bedrock agent invocation
    productDescFunction.addToRolePolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: [
        'bedrock-agent-runtime:InvokeAgent',
        'bedrock:InvokeAgent',
        'bedrock:InvokeModel',
      ],
      resources: [
        this.bedrockAgent.attrAgentArn,
        `arn:aws:bedrock:${this.region}:${this.account}:agent-alias/${this.bedrockAgent.attrAgentId}/${this.bedrockAgentAlias.attrAgentAliasId}`,
        `arn:aws:bedrock:*::foundation-model/anthropic.claude-3-haiku-*`,
      ],
    }));

    // Create AI resource
    const aiResource = this.appPlaneApi.root.addResource('ai');
    const generateDescResource = aiResource.addResource('generate-description');

    // Lambda integration
    const productDescIntegration = new apigateway.LambdaIntegration(productDescFunction, {
      requestTemplates: { 'application/json': '{ "statusCode": "200" }' },
      proxy: true,
    });

    // Add POST method with authorizer
    generateDescResource.addMethod('POST', productDescIntegration, {
      authorizer: this.authorizer
    });

    // Add AI outputs
    new cdk.CfnOutput(this, 'AIDescriptionEndpoint', {
      value: `https://${this.appPlaneApi.restApiId}.execute-api.${this.region}.amazonaws.com/prod/ai/generate-description`,
      description: 'AI Product Description Generation Endpoint',
    });

    new cdk.CfnOutput(this, 'BedrockAgentId', {
      value: this.bedrockAgent.attrAgentId,
      description: 'Bedrock Agent ID for product description generation',
    });

    new cdk.CfnOutput(this, 'BedrockAgentAliasId', {
      value: this.bedrockAgentAlias.attrAgentAliasId,
      description: 'Bedrock Agent Alias ID',
    });
  }
}
