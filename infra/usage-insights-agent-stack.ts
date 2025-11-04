import * as cdk from 'aws-cdk-lib';
import * as apigateway from 'aws-cdk-lib/aws-apigateway';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as logs from 'aws-cdk-lib/aws-logs';
import * as bedrock from 'aws-cdk-lib/aws-bedrock';
import { Construct } from 'constructs';
import * as fs from 'fs';
import * as path from 'path';

export class UsageInsightsAgentStack extends cdk.Stack {
  public readonly usageInsightsFunction: lambda.Function;
  public readonly bedrockAgent: bedrock.CfnAgent;
  public readonly bedrockAgentAlias: bedrock.CfnAgentAlias;

  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // Define CDK parameters
    const usageMetricsTableName = new cdk.CfnParameter(this, 'usageMetricsTableName', {
      type: 'String',
      description: 'Name of the usage metrics DynamoDB table',
      default: 'AgenticInsights-UsageMetrics',
    });

    const tenantsTableName = new cdk.CfnParameter(this, 'tenantsTableName', {
      type: 'String',
      description: 'Name of the tenants DynamoDB table',
      default: 'Tenants',
    });

    // ========================================
    // BEDROCK AGENT SETUP
    // ========================================

    // Create IAM role for Bedrock Agent
    // Note: roleName is not specified to allow CDK to generate a unique name
    // This avoids conflicts with existing roles from previous deployments
    const bedrockAgentRole = new iam.Role(this, 'BedrockAgentRole', {
      assumedBy: new iam.ServicePrincipal('bedrock.amazonaws.com'),
      description: 'IAM role for Usage Insights Bedrock Agent',
    });

    // Add Bedrock model invocation permissions
    bedrockAgentRole.addToPolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: [
        'bedrock:InvokeModel',
        'bedrock:GetInferenceProfile',
        'bedrock:ListInferenceProfiles'
      ],
      resources: [
        `arn:aws:bedrock:*::foundation-model/*`,
        `arn:aws:bedrock:${this.region}:${this.account}:inference-profile/*`
      ],
    }));

    // Add AWS Marketplace permissions for third-party models
    // Sid: MarketplaceOperationsFromBedrockFor3pModels
    bedrockAgentRole.addToPolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: [
        'aws-marketplace:Subscribe',
        'aws-marketplace:ViewSubscriptions',
        'aws-marketplace:Unsubscribe'
      ],
      resources: ['*'],
      conditions: {
        StringEquals: {
          'aws:CalledViaLast': 'bedrock.amazonaws.com'
        }
      }
    }));

    // Read system prompt from file
    const systemPromptPath = path.join(__dirname, '../src/control-plane/agents/usage-insights/prompts/system_prompt.txt');
    const systemPrompt = fs.readFileSync(systemPromptPath, 'utf-8');

    // Define tool schemas for Bedrock Agent
    const toolSchemas = [
      {
        name: 'calculate_time_to_value',
        description: 'Calculate Time to Value metrics for tenants',
        inputSchema: {
          json: {
            type: 'object',
            properties: {
              tenant_id: {
                type: 'string',
                description: 'Tenant ID to analyze (or "all" for platform-wide)',
              },
              date_range: {
                type: 'object',
                properties: {
                  start_date: {
                    type: 'string',
                    description: 'Start date (YYYY-MM-DD)',
                  },
                  end_date: {
                    type: 'string',
                    description: 'End date (YYYY-MM-DD)',
                  },
                },
              },
            },
            required: ['tenant_id'],
          },
        },
      },
      {
        name: 'project_customer_lifetime_value',
        description: 'Project Customer Lifetime Value for tenants',
        inputSchema: {
          json: {
            type: 'object',
            properties: {
              tenant_id: {
                type: 'string',
                description: 'Tenant ID to analyze (or "all" for platform-wide)',
              },
              projection_months: {
                type: 'integer',
                description: 'Number of months to project (default: 12)',
              },
            },
            required: ['tenant_id'],
          },
        },
      },
      {
        name: 'analyze_feature_adoption_rates',
        description: 'Analyze feature adoption rates across tenants',
        inputSchema: {
          json: {
            type: 'object',
            properties: {
              tenant_id: {
                type: 'string',
                description: 'Tenant ID to analyze (or "all" for platform-wide)',
              },
              time_period_days: {
                type: 'integer',
                description: 'Time period in days for adoption calculation (default: 30)',
              },
            },
            required: ['tenant_id'],
          },
        },
      },
      {
        name: 'calculate_engagement_scores',
        description: 'Calculate user engagement scores',
        inputSchema: {
          json: {
            type: 'object',
            properties: {
              tenant_id: {
                type: 'string',
                description: 'Tenant ID to analyze',
              },
              user_id: {
                type: 'string',
                description: 'Specific user ID (optional, omit for all users)',
              },
            },
            required: ['tenant_id'],
          },
        },
      },
      {
        name: 'identify_at_risk_features',
        description: 'Identify features with declining usage or low adoption',
        inputSchema: {
          json: {
            type: 'object',
            properties: {
              tenant_id: {
                type: 'string',
                description: 'Tenant ID to analyze (or "all" for platform-wide)',
              },
              analysis_period_days: {
                type: 'integer',
                description: 'Period for trend analysis (default: 90)',
              },
            },
            required: ['tenant_id'],
          },
        },
      },
    ];

    // Create Lambda functions for each tool
    const toolLambdas = this.createToolLambdas(usageMetricsTableName, tenantsTableName);

    // Create action groups for Bedrock Agent using function schema
    // Note: Function schema doesn't support nested objects, so we flatten parameters
    const actionGroups = toolSchemas.map((tool, index) => {
      const parameters: Record<string, any> = {};

      // Flatten parameters - convert nested objects to top-level parameters
      Object.entries(tool.inputSchema.json.properties).forEach(([key, value]: [string, any]) => {
        if (value.type === 'object' && value.properties) {
          // Flatten nested object properties
          Object.entries(value.properties).forEach(([nestedKey, nestedValue]: [string, any]) => {
            parameters[nestedKey] = {
              type: nestedValue.type,
              description: nestedValue.description,
              required: false,
            };
          });
        } else if (value.type === 'integer') {
          // Handle integer type
          parameters[key] = {
            type: 'number',
            description: value.description,
            required: tool.inputSchema.json.required?.includes(key) || false,
          };
        } else {
          // Handle simple types (string, number, boolean)
          parameters[key] = {
            type: value.type,
            description: value.description,
            required: tool.inputSchema.json.required?.includes(key) || false,
          };
        }
      });

      return {
        actionGroupName: tool.name,
        description: tool.description,
        actionGroupExecutor: {
          lambda: toolLambdas[index].functionArn,
        },
        functionSchema: {
          functions: [
            {
              name: tool.name,
              description: tool.description,
              parameters: parameters,
            },
          ],
        },
      };
    });

    // Create Bedrock Agent with optimized configuration
    // PERFORMANCE OPTIMIZATION: Reduced idleSessionTtlInSeconds and optimized system prompt
    this.bedrockAgent = new bedrock.CfnAgent(this, 'UsageInsightsAgent', {
      agentName: 'usage-insights-agent',
      agentResourceRoleArn: bedrockAgentRole.roleArn,
      foundationModel: 'global.anthropic.claude-sonnet-4-5-20250929-v1:0',  // Use inference profile instead of direct model
      instruction: systemPrompt,
      description: 'AI agent for advanced usage analytics including TTV, CLTV, engagement, and at-risk feature identification',
      idleSessionTtlInSeconds: 600, // Reduced from 900 to 600 seconds (10 minutes) for performance
      actionGroups: actionGroups,
    });

    // Grant Lambda invoke permissions to Bedrock Agent
    toolLambdas.forEach((lambdaFunc) => {
      lambdaFunc.grantInvoke(new iam.ServicePrincipal('bedrock.amazonaws.com', {
        conditions: {
          StringEquals: {
            'aws:SourceAccount': this.account,
          },
          ArnLike: {
            'aws:SourceArn': `arn:aws:bedrock:${this.region}:${this.account}:agent/*`,
          },
        },
      }));
    });

    // Create Agent Alias
    this.bedrockAgentAlias = new bedrock.CfnAgentAlias(this, 'UsageInsightsAgentAlias', {
      agentId: this.bedrockAgent.attrAgentId,
      agentAliasName: 'prod',
      description: 'Production alias for usage insights agent',
    });

    // ========================================
    // LAMBDA FUNCTION FOR API GATEWAY
    // ========================================

    const controlPlaneApiId = new cdk.CfnParameter(this, 'controlPlaneApiId', {
      type: 'String',
      description: 'Control Plane API Gateway ID',
    });

    const controlPlaneApiRootResourceId = new cdk.CfnParameter(this, 'controlPlaneApiRootResourceId', {
      type: 'String',
      description: 'Control Plane API Gateway root resource ID',
    });

    const controlPlaneAuthorizerId = new cdk.CfnParameter(this, 'controlPlaneAuthorizerId', {
      type: 'String',
      description: 'Control Plane Lambda Authorizer ID',
      default: 'NONE', // Optional - Control Plane authorizer may not be enabled
    });

    // Create log group first to avoid circular dependency
    const logGroup = new logs.LogGroup(this, 'UsageInsightsLogGroup', {
      logGroupName: '/aws/lambda/usage-insights-function',
      retention: logs.RetentionDays.ONE_WEEK,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    // Usage Insights Lambda function with configuration optimized for AI workload
    this.usageInsightsFunction = new lambda.Function(this, 'UsageInsightsFunction', {
      functionName: 'usage-insights-function',
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'usage_insights_service.lambda_handler',
      code: lambda.Code.fromAsset('src/control-plane/usage-insights-api'),
      environment: {
        BEDROCK_AGENT_ID: this.bedrockAgent.attrAgentId,
        BEDROCK_AGENT_ALIAS_ID: this.bedrockAgentAlias.attrAgentAliasId,
        USAGE_METRICS_TABLE_NAME: usageMetricsTableName.valueAsString,
        TENANTS_TABLE_NAME: tenantsTableName.valueAsString,
        PYTHONPATH: '/var/runtime:/var/task:/opt/python',
      },
      timeout: cdk.Duration.seconds(60), // 60 seconds timeout for AI analysis
      memorySize: 1024, // 1024 MB for AI workload and caching
      reservedConcurrentExecutions: 10, // Reserve capacity for consistent performance
      insightsVersion: lambda.LambdaInsightsVersion.VERSION_1_0_229_0, // Enable Lambda Insights
      logGroup: logGroup,
    });

    // Bedrock Agent permissions - includes both agent and agent-alias resources
    this.usageInsightsFunction.addToRolePolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: [
        'bedrock-agent-runtime:InvokeAgent',  // Required for invoking agent at runtime
        'bedrock:InvokeAgent',
        'bedrock:GetAgent',
      ],
      resources: [
        `arn:aws:bedrock:${this.region}:${this.account}:agent/*`,
        `arn:aws:bedrock:${this.region}:${this.account}:agent-alias/*/*`
      ]
    }));

    // DynamoDB permissions for usage metrics table with GSI access
    this.usageInsightsFunction.addToRolePolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: [
        'dynamodb:Query',
        'dynamodb:GetItem',
        'dynamodb:BatchGetItem',
      ],
      resources: [
        `arn:aws:dynamodb:${this.region}:${this.account}:table/${usageMetricsTableName.valueAsString}`,
        `arn:aws:dynamodb:${this.region}:${this.account}:table/${usageMetricsTableName.valueAsString}/index/*`
      ]
    }));

    // DynamoDB permissions for tenants table
    this.usageInsightsFunction.addToRolePolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: [
        'dynamodb:Query',
        'dynamodb:GetItem',
        'dynamodb:BatchGetItem',
        'dynamodb:Scan'
      ],
      resources: [
        `arn:aws:dynamodb:${this.region}:${this.account}:table/${tenantsTableName.valueAsString}`,
        `arn:aws:dynamodb:${this.region}:${this.account}:table/${tenantsTableName.valueAsString}/index/*`
      ]
    }));

    // CloudWatch Logs permissions (automatically granted by Lambda service)
    // CloudWatch metrics permissions for performance monitoring
    this.usageInsightsFunction.addToRolePolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: [
        'cloudwatch:PutMetricData',
      ],
      resources: ['*'],
      conditions: {
        StringEquals: {
          'cloudwatch:namespace': ['AWS/Lambda', 'LambdaInsights', 'UsageInsights/Performance']
        }
      }
    }));

    // Add parameters for existing AI resource IDs
    const controlPlaneAiResourceId = new cdk.CfnParameter(this, 'controlPlaneAiResourceId', {
      type: 'String',
      description: 'Control Plane AI resource ID (should exist from previous deployments)',
    });

    // Create usage-insights resources under existing AI resources
    const controlPlaneInsightsResource = new apigateway.CfnResource(this, 'ControlPlaneInsightsResource', {
      restApiId: controlPlaneApiId.valueAsString,
      parentId: controlPlaneAiResourceId.valueAsString,
      pathPart: 'usage-insights',
    });

    // Control Plane GET method with Lambda Authorizer
    new apigateway.CfnMethod(this, 'ControlPlaneInsightsGET', {
      restApiId: controlPlaneApiId.valueAsString,
      resourceId: controlPlaneInsightsResource.ref,
      httpMethod: 'GET',
      authorizationType: 'COGNITO_USER_POOLS',
      authorizerId: controlPlaneAuthorizerId.valueAsString,
      integration: {
        type: 'AWS_PROXY',
        integrationHttpMethod: 'POST',
        uri: `arn:aws:apigateway:${this.region}:lambda:path/2015-03-31/functions/${this.usageInsightsFunction.functionArn}/invocations`,
        requestParameters: {
          'integration.request.header.x-admin-request': "'true'",
        },
      },
    });

    // Control Plane POST method with Lambda Authorizer
    new apigateway.CfnMethod(this, 'ControlPlaneInsightsPOST', {
      restApiId: controlPlaneApiId.valueAsString,
      resourceId: controlPlaneInsightsResource.ref,
      httpMethod: 'POST',
      authorizationType: 'COGNITO_USER_POOLS',
      authorizerId: controlPlaneAuthorizerId.valueAsString,
      integration: {
        type: 'AWS_PROXY',
        integrationHttpMethod: 'POST',
        uri: `arn:aws:apigateway:${this.region}:lambda:path/2015-03-31/functions/${this.usageInsightsFunction.functionArn}/invocations`,
        requestParameters: {
          'integration.request.header.x-admin-request': "'true'",
        },
      },
    });

    // Control Plane OPTIONS method for CORS
    new apigateway.CfnMethod(this, 'ControlPlaneInsightsOPTIONS', {
      restApiId: controlPlaneApiId.valueAsString,
      resourceId: controlPlaneInsightsResource.ref,
      httpMethod: 'OPTIONS',
      authorizationType: 'NONE',
      integration: {
        type: 'MOCK',
        integrationResponses: [{
          statusCode: '200',
          responseParameters: {
            'method.response.header.Access-Control-Allow-Headers': "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'",
            'method.response.header.Access-Control-Allow-Methods': "'GET,POST,OPTIONS'",
            'method.response.header.Access-Control-Allow-Origin': "'*'",
          },
        }],
        requestTemplates: {
          'application/json': '{"statusCode": 200}',
        },
      },
      methodResponses: [{
        statusCode: '200',
        responseParameters: {
          'method.response.header.Access-Control-Allow-Headers': true,
          'method.response.header.Access-Control-Allow-Methods': true,
          'method.response.header.Access-Control-Allow-Origin': true,
        },
      }],
    });

    // Lambda permissions for API Gateway invocation
    new lambda.CfnPermission(this, 'ControlPlaneApiInvokePermission', {
      action: 'lambda:InvokeFunction',
      functionName: this.usageInsightsFunction.functionName,
      principal: 'apigateway.amazonaws.com',
      sourceArn: `arn:aws:execute-api:${this.region}:${this.account}:${controlPlaneApiId.valueAsString}/*/*`,
    });

    // Add Gateway Responses to handle CORS for errors (Control Plane)
    // This ensures CORS headers are returned even when authorizer or other errors occur
    new apigateway.CfnGatewayResponse(this, 'ControlPlaneUnauthorizedResponse', {
      restApiId: controlPlaneApiId.valueAsString,
      responseType: 'UNAUTHORIZED',
      responseParameters: {
        'gatewayresponse.header.Access-Control-Allow-Origin': "'*'",
        'gatewayresponse.header.Access-Control-Allow-Headers': "'Content-Type,Authorization,tenant-id'",
        'gatewayresponse.header.Access-Control-Allow-Methods': "'GET,POST,OPTIONS'",
      },
      statusCode: '401',
    });

    new apigateway.CfnGatewayResponse(this, 'ControlPlaneAccessDeniedResponse', {
      restApiId: controlPlaneApiId.valueAsString,
      responseType: 'ACCESS_DENIED',
      responseParameters: {
        'gatewayresponse.header.Access-Control-Allow-Origin': "'*'",
        'gatewayresponse.header.Access-Control-Allow-Headers': "'Content-Type,Authorization,tenant-id'",
        'gatewayresponse.header.Access-Control-Allow-Methods': "'GET,POST,OPTIONS'",
      },
      statusCode: '403',
    });

    new apigateway.CfnGatewayResponse(this, 'ControlPlaneAuthorizerFailureResponse', {
      restApiId: controlPlaneApiId.valueAsString,
      responseType: 'AUTHORIZER_FAILURE',
      responseParameters: {
        'gatewayresponse.header.Access-Control-Allow-Origin': "'*'",
        'gatewayresponse.header.Access-Control-Allow-Headers': "'Content-Type,Authorization,tenant-id'",
        'gatewayresponse.header.Access-Control-Allow-Methods': "'GET,POST,OPTIONS'",
      },
      statusCode: '500',
    });

    new apigateway.CfnGatewayResponse(this, 'ControlPlaneAuthorizerConfigErrorResponse', {
      restApiId: controlPlaneApiId.valueAsString,
      responseType: 'AUTHORIZER_CONFIGURATION_ERROR',
      responseParameters: {
        'gatewayresponse.header.Access-Control-Allow-Origin': "'*'",
        'gatewayresponse.header.Access-Control-Allow-Headers': "'Content-Type,Authorization,tenant-id'",
        'gatewayresponse.header.Access-Control-Allow-Methods': "'GET,POST,OPTIONS'",
      },
      statusCode: '500',
    });

    // Outputs
    new cdk.CfnOutput(this, 'UsageInsightsFunctionName', {
      value: this.usageInsightsFunction.functionName,
      description: 'Usage Insights Lambda Function Name',
      exportName: 'UsageInsightsFunctionName',
    });

    new cdk.CfnOutput(this, 'UsageInsightsFunctionArn', {
      value: this.usageInsightsFunction.functionArn,
      description: 'Usage Insights Lambda Function ARN',
      exportName: 'UsageInsightsFunctionArn',
    });

    new cdk.CfnOutput(this, 'ControlPlaneInsightsEndpoint', {
      value: `https://${controlPlaneApiId.valueAsString}.execute-api.${this.region}.amazonaws.com/prod/ai/usage-insights`,
      description: 'Control Plane Usage Insights API Endpoint',
      exportName: 'ControlPlaneInsightsEndpoint',
    });

    // Bedrock Agent outputs
    new cdk.CfnOutput(this, 'BedrockAgentId', {
      value: this.bedrockAgent.attrAgentId,
      description: 'Bedrock Agent ID',
      exportName: 'UsageInsightsBedrockAgentId',
    });

    new cdk.CfnOutput(this, 'BedrockAgentAliasId', {
      value: this.bedrockAgentAlias.attrAgentAliasId,
      description: 'Bedrock Agent Alias ID',
      exportName: 'UsageInsightsBedrockAgentAliasId',
    });
  }

  /**
   * Create Lambda functions for each Bedrock Agent tool
   * Note: Using a single Lambda function with a wrapper that routes to all tools
   */
  private createToolLambdas(
    usageMetricsTableName: cdk.CfnParameter,
    tenantsTableName: cdk.CfnParameter
  ): lambda.Function[] {
    // Create log group for the shared tool Lambda
    const toolLogGroup = new logs.LogGroup(this, 'ToolsLogGroup', {
      logGroupName: '/aws/lambda/usage-insights-tools',
      retention: logs.RetentionDays.ONE_WEEK,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    // Create a single Lambda function that handles all tools
    // PERFORMANCE OPTIMIZATION: Increased memory to 1024MB for faster CPU allocation
    const toolFunction = new lambda.Function(this, 'ToolsFunction', {
      functionName: 'usage-insights-tools',
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'tools.lambda_wrapper.lambda_handler',
      code: lambda.Code.fromAsset('src/control-plane/agents/usage-insights'),
      environment: {
        USAGE_METRICS_TABLE_NAME: usageMetricsTableName.valueAsString,
        TENANTS_TABLE_NAME: tenantsTableName.valueAsString,
        PYTHONPATH: '/var/runtime:/var/task:/opt/python',
      },
      timeout: cdk.Duration.seconds(30),
      memorySize: 1024, // Increased from 512MB for better performance
      logGroup: toolLogGroup,
    });

    // Grant DynamoDB permissions
    toolFunction.addToRolePolicy(
      new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        actions: ['dynamodb:Query', 'dynamodb:GetItem', 'dynamodb:BatchGetItem', 'dynamodb:Scan'],
        resources: [
          `arn:aws:dynamodb:${this.region}:${this.account}:table/${usageMetricsTableName.valueAsString}`,
          `arn:aws:dynamodb:${this.region}:${this.account}:table/${usageMetricsTableName.valueAsString}/index/*`,
          `arn:aws:dynamodb:${this.region}:${this.account}:table/${tenantsTableName.valueAsString}`,
          `arn:aws:dynamodb:${this.region}:${this.account}:table/${tenantsTableName.valueAsString}/index/*`,
        ],
      })
    );

    // Return array with 5 references to the same function (one for each action group)
    // This is because the action groups expect separate Lambda ARNs
    return [toolFunction, toolFunction, toolFunction, toolFunction, toolFunction];
  }
}
