import * as cdk from 'aws-cdk-lib';
import * as apigateway from 'aws-cdk-lib/aws-apigateway';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as logs from 'aws-cdk-lib/aws-logs';
import { Construct } from 'constructs';

interface UsageAnalysisStackProps extends cdk.StackProps {
  agentId: string;
  agentAliasId: string;
  metricsAggregationTableName: string;
  tenantsTableName: string;
  controlPlaneApiId: string;
  controlPlaneApiRootResourceId: string;
  appPlaneApiId: string;
  appPlaneApiRootResourceId: string;
  lambdaAuthorizerId: string;
}

export class UsageAnalysisStack extends cdk.Stack {
  public readonly usageAnalysisFunction: lambda.Function;

  constructor(scope: Construct, id: string, props: UsageAnalysisStackProps) {
    super(scope, id, props);

    // Import existing API Gateways
    const existingControlApi = apigateway.RestApi.fromRestApiAttributes(this, 'ExistingControlApi', {
      restApiId: props.controlPlaneApiId,
      rootResourceId: props.controlPlaneApiRootResourceId,
    });

    const existingAppApi = apigateway.RestApi.fromRestApiAttributes(this, 'ExistingAppApi', {
      restApiId: props.appPlaneApiId,
      rootResourceId: props.appPlaneApiRootResourceId,
    });

    // Import existing Lambda authorizer
    const existingAuthorizer = apigateway.Authorizer.fromAuthorizerId(this, 'ExistingAuth', props.lambdaAuthorizerId);

    // Usage Analysis Lambda Function
    this.usageAnalysisFunction = new lambda.Function(this, 'UsageAnalysisFunction', {
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'usage_analysis_service.lambda_handler',
      code: lambda.Code.fromAsset('src/agents/usage-analysis-api'),
      environment: {
        BEDROCK_AGENT_ID: props.agentId,
        BEDROCK_AGENT_ALIAS_ID: props.agentAliasId,
        METRICS_AGGREGATION_TABLE_NAME: props.metricsAggregationTableName,
        TENANTS_TABLE_NAME: props.tenantsTableName,
      },
      timeout: cdk.Duration.seconds(60),
      memorySize: 1024, // Increased memory for AI workload
      description: 'Usage Analysis Service using Strands agent via Bedrock AgentCore',
    });

    // CloudWatch Log Group with retention
    new logs.LogGroup(this, 'UsageAnalysisLogGroup', {
      logGroupName: `/aws/lambda/${this.usageAnalysisFunction.functionName}`,
      retention: logs.RetentionDays.ONE_MONTH,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    // Bedrock AgentCore permissions
    this.usageAnalysisFunction.addToRolePolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: [
        'bedrock:InvokeAgent',
        'bedrock-agent-runtime:InvokeAgent',
        'bedrock:GetAgent',
        'bedrock:ListAgents',
      ],
      resources: [
        `arn:aws:bedrock:${this.region}:${this.account}:agent/${props.agentId}`,
        `arn:aws:bedrock:${this.region}:${this.account}:agent-alias/${props.agentId}/${props.agentAliasId}`,
        `arn:aws:bedrock:*::foundation-model/anthropic.claude-3-haiku-*`,
      ],
    }));

    // DynamoDB permissions for metrics and tenants tables
    this.usageAnalysisFunction.addToRolePolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: [
        'dynamodb:Query',
        'dynamodb:GetItem',
        'dynamodb:Scan',
      ],
      resources: [
        `arn:aws:dynamodb:${this.region}:${this.account}:table/${props.metricsAggregationTableName}`,
        `arn:aws:dynamodb:${this.region}:${this.account}:table/${props.metricsAggregationTableName}/index/*`,
        `arn:aws:dynamodb:${this.region}:${this.account}:table/${props.tenantsTableName}`,
        `arn:aws:dynamodb:${this.region}:${this.account}:table/${props.tenantsTableName}/index/*`,
      ],
    }));

    // Request validator for API Gateway
    const requestValidator = new apigateway.RequestValidator(this, 'UsageAnalysisRequestValidator', {
      restApi: existingControlApi,
      validateRequestBody: true,
      validateRequestParameters: true,
    });

    // Lambda integration
    const lambdaIntegration = new apigateway.LambdaIntegration(this.usageAnalysisFunction, {
      requestTemplates: {
        'application/json': '{"statusCode": "200"}',
      },
    });

    // Control Plane API integration (for platform admins)
    const controlUsageResource = existingControlApi.root.addResource('usage-analysis');
    
    // Add CORS OPTIONS method for Control Plane
    controlUsageResource.addMethod('OPTIONS', new apigateway.MockIntegration({
      integrationResponses: [{
        statusCode: '200',
        responseParameters: {
          'method.response.header.Access-Control-Allow-Headers': "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'",
          'method.response.header.Access-Control-Allow-Origin': "'*'",
          'method.response.header.Access-Control-Allow-Methods': "'GET,POST,OPTIONS'",
        },
      }],
      requestTemplates: {
        'application/json': '{"statusCode": 200}',
      },
    }), {
      methodResponses: [{
        statusCode: '200',
        responseParameters: {
          'method.response.header.Access-Control-Allow-Headers': true,
          'method.response.header.Access-Control-Allow-Origin': true,
          'method.response.header.Access-Control-Allow-Methods': true,
        },
      }],
    });

    // GET method for Control Plane (dashboard data retrieval)
    controlUsageResource.addMethod('GET', lambdaIntegration, {
      authorizer: existingAuthorizer,
      requestValidator: requestValidator,
      methodResponses: [{
        statusCode: '200',
        responseParameters: {
          'method.response.header.Access-Control-Allow-Origin': true,
        },
      }],
    });

    // POST method for Control Plane (analysis requests)
    controlUsageResource.addMethod('POST', lambdaIntegration, {
      authorizer: existingAuthorizer,
      requestValidator: requestValidator,
      methodResponses: [{
        statusCode: '200',
        responseParameters: {
          'method.response.header.Access-Control-Allow-Origin': true,
        },
      }],
    });

    // Application Plane API integration (for tenant users)
    const appUsageResource = existingAppApi.root.addResource('usage-analysis');
    
    // Add CORS OPTIONS method for Application Plane
    appUsageResource.addMethod('OPTIONS', new apigateway.MockIntegration({
      integrationResponses: [{
        statusCode: '200',
        responseParameters: {
          'method.response.header.Access-Control-Allow-Headers': "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token,tenant-id,tier-name'",
          'method.response.header.Access-Control-Allow-Origin': "'*'",
          'method.response.header.Access-Control-Allow-Methods': "'GET,POST,OPTIONS'",
        },
      }],
      requestTemplates: {
        'application/json': '{"statusCode": 200}',
      },
    }), {
      methodResponses: [{
        statusCode: '200',
        responseParameters: {
          'method.response.header.Access-Control-Allow-Headers': true,
          'method.response.header.Access-Control-Allow-Origin': true,
          'method.response.header.Access-Control-Allow-Methods': true,
        },
      }],
    });

    // GET method for Application Plane (tenant dashboard data)
    appUsageResource.addMethod('GET', lambdaIntegration, {
      authorizer: existingAuthorizer,
      requestValidator: requestValidator,
      methodResponses: [{
        statusCode: '200',
        responseParameters: {
          'method.response.header.Access-Control-Allow-Origin': true,
        },
      }],
    });

    // POST method for Application Plane (tenant analysis requests)
    appUsageResource.addMethod('POST', lambdaIntegration, {
      authorizer: existingAuthorizer,
      requestValidator: requestValidator,
      methodResponses: [{
        statusCode: '200',
        responseParameters: {
          'method.response.header.Access-Control-Allow-Origin': true,
        },
      }],
    });

    // Outputs
    new cdk.CfnOutput(this, 'UsageAnalysisFunctionName', {
      value: this.usageAnalysisFunction.functionName,
      description: 'Usage Analysis Lambda Function Name',
    });

    new cdk.CfnOutput(this, 'UsageAnalysisFunctionArn', {
      value: this.usageAnalysisFunction.functionArn,
      description: 'Usage Analysis Lambda Function ARN',
    });

    new cdk.CfnOutput(this, 'ControlPlaneUsageAnalysisUrl', {
      value: `https://${props.controlPlaneApiId}.execute-api.${this.region}.amazonaws.com/prod/usage-analysis`,
      description: 'Control Plane Usage Analysis API endpoint',
    });

    new cdk.CfnOutput(this, 'AppPlaneUsageAnalysisUrl', {
      value: `https://${props.appPlaneApiId}.execute-api.${this.region}.amazonaws.com/prod/usage-analysis`,
      description: 'Application Plane Usage Analysis API endpoint',
    });

    new cdk.CfnOutput(this, 'UsageAnalysisAgentId', {
      value: props.agentId,
      description: 'Bedrock Agent ID for usage analysis',
    });

    new cdk.CfnOutput(this, 'UsageAnalysisAgentAliasId', {
      value: props.agentAliasId,
      description: 'Bedrock Agent Alias ID',
    });
  }
}