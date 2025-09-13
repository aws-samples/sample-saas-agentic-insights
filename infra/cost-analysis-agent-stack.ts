import * as cdk from 'aws-cdk-lib';
import * as apigateway from 'aws-cdk-lib/aws-apigateway';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as bedrock from 'aws-cdk-lib/aws-bedrock';
import * as fs from 'fs';
import * as path from 'path';
import { Construct } from 'constructs';

interface CostAnalysisAgentStackProps extends cdk.StackProps {
  metricsTableName: string;
  metricsAggregationTableName: string;
  controlPlaneApiId: string;
  controlPlaneApiRootResourceId: string;
}

export class CostAnalysisAgentStack extends cdk.Stack {
  public readonly costAnalysisAgent: bedrock.CfnAgent;
  public readonly costAnalysisAgentAlias: bedrock.CfnAgentAlias;

  constructor(scope: Construct, id: string, props: CostAnalysisAgentStackProps) {
    super(scope, id, props);

    // Load agent configuration
    const agentConfigPath = path.join(__dirname, '../src/control-plane/agents/cost-analysis/agent-config.yaml');
    const agentInstructionsPath = path.join(__dirname, '../src/control-plane/agents/cost-analysis/instructions.txt');
    
    // Parse agent config
    const agentConfigContent = fs.readFileSync(agentConfigPath, 'utf8');
    const agentName = agentConfigContent.match(/name:\s*(.+)/)?.[1]?.trim() || 'agentic-insights-cost-analysis-agent';
    const agentModel = agentConfigContent.match(/model:\s*(.+)/)?.[1]?.trim() || 'us.anthropic.claude-3-haiku-20240307-v1:0';
    const agentDescription = agentConfigContent.match(/description:\s*(.+)/)?.[1]?.trim() || 'AI agent for SaaS cost analysis and tenant economics';
    
    // Load agent instructions
    const agentInstructions = fs.readFileSync(agentInstructionsPath, 'utf8').trim();

    // Lambda functions for action groups (using agent-specific directory)
    const infrastructureUsageFunction = new lambda.Function(this, 'InfrastructureUsageFunction', {
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'infrastructure_usage.handler',
      code: lambda.Code.fromAsset('src/control-plane/agents/cost-analysis/action-groups'),
      timeout: cdk.Duration.seconds(60),
      environment: {
        METRICS_TABLE_NAME: props.metricsTableName,
        METRICS_AGGREGATION_TABLE_NAME: props.metricsAggregationTableName,
      },
    });

    const costAnalysisFunction = new lambda.Function(this, 'CostAnalysisFunction', {
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'cost_analysis.handler',
      code: lambda.Code.fromAsset('src/control-plane/agents/cost-analysis/action-groups'),
      timeout: cdk.Duration.seconds(60),
      environment: {
        METRICS_TABLE_NAME: props.metricsTableName,
        METRICS_AGGREGATION_TABLE_NAME: props.metricsAggregationTableName,
      },
    });

    const costPredictionFunction = new lambda.Function(this, 'CostPredictionFunction', {
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'cost_prediction.handler',
      code: lambda.Code.fromAsset('src/control-plane/agents/cost-analysis/action-groups'),
      timeout: cdk.Duration.seconds(60),
      environment: {
        METRICS_TABLE_NAME: props.metricsTableName,
        METRICS_AGGREGATION_TABLE_NAME: props.metricsAggregationTableName,
      },
    });

    // Grant Lambda permissions for action groups
    infrastructureUsageFunction.grantInvoke(new iam.ServicePrincipal('bedrock.amazonaws.com'));
    costAnalysisFunction.grantInvoke(new iam.ServicePrincipal('bedrock.amazonaws.com'));
    costPredictionFunction.grantInvoke(new iam.ServicePrincipal('bedrock.amazonaws.com'));

    // Grant DynamoDB permissions
    const metricsTableArn = `arn:aws:dynamodb:${this.region}:${this.account}:table/${props.metricsTableName}`;
    const metricsAggTableArn = `arn:aws:dynamodb:${this.region}:${this.account}:table/${props.metricsAggregationTableName}`;
    const tenantsTableArn = `arn:aws:dynamodb:${this.region}:${this.account}:table/Tenants`;

    [infrastructureUsageFunction, costAnalysisFunction, costPredictionFunction].forEach(fn => {
      fn.addToRolePolicy(new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        actions: ['dynamodb:Query', 'dynamodb:GetItem', 'dynamodb:Scan'],
        resources: [
          metricsTableArn, 
          metricsAggTableArn, 
          tenantsTableArn,
          `${metricsTableArn}/index/*`, 
          `${metricsAggTableArn}/index/*`
        ],
      }));
    });

    // Bedrock Agent IAM Role
    const agentRole = new iam.Role(this, 'CostAnalysisAgentRole', {
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
            }),
            new iam.PolicyStatement({
              effect: iam.Effect.ALLOW,
              actions: ['lambda:InvokeFunction'],
              resources: [
                infrastructureUsageFunction.functionArn,
                costAnalysisFunction.functionArn,
                costPredictionFunction.functionArn,
              ],
            }),
          ],
        }),
      },
    });

    // Bedrock Agent
    this.costAnalysisAgent = new bedrock.CfnAgent(this, 'CostAnalysisAgent', {
      agentName: `${agentName}-${this.region}`,
      description: `${agentDescription} in ${this.region}`,
      foundationModel: agentModel,
      agentResourceRoleArn: agentRole.roleArn,
      instruction: agentInstructions,
      idleSessionTtlInSeconds: 1800,

      actionGroups: [
        {
          actionGroupName: 'infrastructure-usage',
          description: 'Calculate detailed infrastructure usage per tenant',
          actionGroupExecutor: { lambda: infrastructureUsageFunction.functionArn },
          apiSchema: {
            payload: JSON.stringify({
              openapi: '3.0.0',
              info: { title: 'Infrastructure Usage API', version: '1.0.0' },
              paths: {
                '/calculate-usage': {
                  post: {
                    description: 'Calculate infrastructure usage for tenants',
                    requestBody: {
                      required: true,
                      content: {
                        'application/json': {
                          schema: {
                            type: 'object',
                            properties: {
                              tenant_ids: { type: 'array', items: { type: 'string' } },
                              time_period: { type: 'string' }
                            },
                            required: ['tenant_ids', 'time_period']
                          }
                        }
                      }
                    },
                    responses: {
                      '200': { description: 'Success' }
                    }
                  }
                }
              }
            })
          }
        },
        {
          actionGroupName: 'cost-analysis',
          description: 'Analyze current costs per tenant with breakdown',
          actionGroupExecutor: { lambda: costAnalysisFunction.functionArn },
          apiSchema: {
            payload: JSON.stringify({
              openapi: '3.0.0',
              info: { title: 'Cost Analysis API', version: '1.0.0' },
              paths: {
                '/analyze-costs': {
                  post: {
                    description: 'Analyze costs per tenant',
                    requestBody: {
                      required: true,
                      content: {
                        'application/json': {
                          schema: {
                            type: 'object',
                            properties: {
                              tenant_ids: { type: 'array', items: { type: 'string' } }
                            },
                            required: ['tenant_ids']
                          }
                        }
                      }
                    },
                    responses: {
                      '200': { description: 'Success' }
                    }
                  }
                }
              }
            })
          }
        },
        {
          actionGroupName: 'cost-prediction',
          description: 'Predict tenant costs for next 3 months',
          actionGroupExecutor: { lambda: costPredictionFunction.functionArn },
          apiSchema: {
            payload: JSON.stringify({
              openapi: '3.0.0',
              info: { title: 'Cost Prediction API', version: '1.0.0' },
              paths: {
                '/predict-costs': {
                  post: {
                    description: 'Predict future costs',
                    requestBody: {
                      required: true,
                      content: {
                        'application/json': {
                          schema: {
                            type: 'object',
                            properties: {
                              tenant_ids: { type: 'array', items: { type: 'string' } },
                              forecast_months: { type: 'integer' }
                            },
                            required: ['tenant_ids', 'forecast_months']
                          }
                        }
                      }
                    },
                    responses: {
                      '200': { description: 'Success' }
                    }
                  }
                }
              }
            })
          }
        }
      ]
    });

    // Agent Alias
    this.costAnalysisAgentAlias = new bedrock.CfnAgentAlias(this, 'CostAnalysisAgentAlias', {
      agentId: this.costAnalysisAgent.attrAgentId,
      agentAliasName: 'prod',
      description: 'Production alias for cost analysis agent',
    });

    // Cost Analysis API Lambda
    const costAnalysisApiFunction = new lambda.Function(this, 'CostAnalysisApiFunction', {
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'handler.handler',
      code: lambda.Code.fromAsset('src/control-plane/cost-analysis-api'),
      environment: {
        BEDROCK_AGENT_ID: this.costAnalysisAgent.attrAgentId,
        BEDROCK_AGENT_ALIAS_ID: this.costAnalysisAgentAlias.attrAgentAliasId,
      },
      timeout: cdk.Duration.seconds(60),
    });

    // Grant Bedrock permissions to API function
    costAnalysisApiFunction.addToRolePolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: [
        'bedrock-agent-runtime:InvokeAgent',
        'bedrock:InvokeAgent',
        'bedrock:InvokeModel',
      ],
      resources: [
        this.costAnalysisAgent.attrAgentArn,
        `arn:aws:bedrock:${this.region}:${this.account}:agent-alias/${this.costAnalysisAgent.attrAgentId}/${this.costAnalysisAgentAlias.attrAgentAliasId}`,
        `arn:aws:bedrock:*::foundation-model/anthropic.claude-3-haiku-*`,
      ],
    }));

    // Get reference to existing Control Plane API Gateway (not App Plane)
    const existingApi = apigateway.RestApi.fromRestApiAttributes(this, 'ExistingControlPlaneApi', {
      restApiId: props.controlPlaneApiId,
      rootResourceId: props.controlPlaneApiRootResourceId,
    });

    // Create cost-analysis resource in Control Plane API
    const costAnalysisResource = existingApi.root.addResource('cost-analysis');
    
    // Add OPTIONS method for CORS
    costAnalysisResource.addMethod('OPTIONS', new apigateway.MockIntegration({
      integrationResponses: [{
        statusCode: '200',
        responseParameters: {
          'method.response.header.Access-Control-Allow-Headers': "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'",
          'method.response.header.Access-Control-Allow-Origin': "'*'",
          'method.response.header.Access-Control-Allow-Methods': "'GET,POST,OPTIONS'"
        }
      }],
      requestTemplates: {
        'application/json': '{"statusCode": 200}'
      }
    }), {
      methodResponses: [{
        statusCode: '200',
        responseParameters: {
          'method.response.header.Access-Control-Allow-Headers': true,
          'method.response.header.Access-Control-Allow-Origin': true,
          'method.response.header.Access-Control-Allow-Methods': true
        }
      }]
    });
    
    // Add GET method for dashboard data retrieval (primary method)
    costAnalysisResource.addMethod('GET', new apigateway.LambdaIntegration(costAnalysisApiFunction));
    
    // Add POST method for analysis requests (secondary method)
    costAnalysisResource.addMethod('POST', new apigateway.LambdaIntegration(costAnalysisApiFunction));

    // Outputs
    new cdk.CfnOutput(this, 'CostAnalysisAgentId', {
      value: this.costAnalysisAgent.attrAgentId,
      description: 'Bedrock Agent ID for cost analysis',
    });

    new cdk.CfnOutput(this, 'CostAnalysisAgentAliasId', {
      value: this.costAnalysisAgentAlias.attrAgentAliasId,
      description: 'Bedrock Agent Alias ID',
    });

    new cdk.CfnOutput(this, 'CostAnalysisApiUrl', {
      value: `https://${props.controlPlaneApiId}.execute-api.${this.region}.amazonaws.com/prod/cost-analysis`,
      description: 'Cost Analysis API endpoint',
    });
  }
}
