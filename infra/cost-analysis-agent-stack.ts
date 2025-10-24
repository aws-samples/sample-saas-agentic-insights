import * as cdk from 'aws-cdk-lib';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as bedrock from 'aws-cdk-lib/aws-bedrock';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as fs from 'fs';
import * as path from 'path';
import { Construct } from 'constructs';

interface CostAnalysisAgentStackProps extends cdk.StackProps {
  metricsTable: dynamodb.Table;
  metricsAggregationTable: dynamodb.Table;
  costPerTenantTable: dynamodb.Table;
}

export class CostAnalysisAgentStack extends cdk.Stack {
  public readonly costAnalysisAgent: bedrock.CfnAgent;
  public readonly costAnalysisAgentAlias: bedrock.CfnAgentAlias;

  constructor(scope: Construct, id: string, props: CostAnalysisAgentStackProps) {
    super(scope, id, props);

    // Load agent configuration
    const agentConfigPath = path.join(__dirname, '../src/control-plane/agents/cost-analysis-agent/agent-config.yaml');
    const agentInstructionsPath = path.join(__dirname, '../src/control-plane/agents/cost-analysis-agent/instructions.txt');
    
    // Parse agent config
    const agentConfigContent = fs.readFileSync(agentConfigPath, 'utf8');
    const agentName = agentConfigContent.match(/name:\s*(.+)/)?.[1]?.trim() || 'agentic-insights-cost-analysis-agent';
    const agentModel = agentConfigContent.match(/model:\s*(.+)/)?.[1]?.trim() || 'anthropic.claude-3-haiku-20240307-v1:0';
    const agentDescription = agentConfigContent.match(/description:\s*(.+)/)?.[1]?.trim() || 'AI agent for cost analysis and financial insights';
    
    // Load agent instructions
    const agentInstructions = fs.readFileSync(agentInstructionsPath, 'utf8').trim();

    // Action Group Lambda Function
    const getCostDatasetFunction = new lambda.Function(this, 'GetCostDatasetFunction', {
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'get_cost_dataset.handler',
      code: lambda.Code.fromAsset('src/control-plane/agents/cost-analysis-agent/action-groups'),
      timeout: cdk.Duration.seconds(60),
      environment: {
        COST_PER_TENANT_TABLE_NAME: props.costPerTenantTable.tableName,
      },
    });

    // Grant Lambda permissions
    getCostDatasetFunction.grantInvoke(new iam.ServicePrincipal('bedrock.amazonaws.com'));

    // Grant DynamoDB permissions
    props.costPerTenantTable.grantReadData(getCostDatasetFunction);

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
              resources: [getCostDatasetFunction.functionArn]
            })
          ]
        })
      }
    });

    // Create Bedrock Agent - use inference profile for new agents
    this.costAnalysisAgent = new bedrock.CfnAgent(this, 'CostAnalysisAgent', {
      agentName: `${agentName}-${this.region}`,
      description: `${agentDescription} in ${this.region}`,
      agentResourceRoleArn: agentRole.roleArn,
      foundationModel: 'us.anthropic.claude-3-haiku-20240307-v1:0', // Inference profile ID
      instruction: agentInstructions,
      idleSessionTtlInSeconds: 1800,
      actionGroups: [
        {
          actionGroupName: 'cost-dataset-fetcher',
          description: 'Fetches CostPerTenant dataset for analysis',
          actionGroupExecutor: {
            lambda: getCostDatasetFunction.functionArn
          },
          apiSchema: {
            payload: JSON.stringify({
              openapi: '3.0.0',
              info: {
                title: 'Cost Dataset API',
                version: '1.0.0'
              },
              paths: {
                '/getCostPerTenantDataset': {
                  get: {
                    summary: 'Get complete CostPerTenant dataset',
                    description: 'Retrieves all tenant cost data for analysis',
                    operationId: 'getCostPerTenantDataset',
                    responses: {
                      '200': {
                        description: 'Dataset retrieved successfully',
                        content: {
                          'application/json': {
                            schema: {
                              type: 'object',
                              properties: {
                                dataset_size: { type: 'integer' },
                                cost_per_tenant_data: {
                                  type: 'array',
                                  items: {
                                    type: 'object',
                                    properties: {
                                      tenant_id: { type: 'string' },
                                      month: { type: 'string' },
                                      tier: { type: 'string' },
                                      cost: { type: 'number' },
                                      revenue: { type: 'number' },
                                      margin: { type: 'number' },
                                      margin_percentage: { type: 'number' }
                                    }
                                  }
                                }
                              }
                            }
                          }
                        }
                      }
                    }
                  }
                }
              }
            })
          }
        }
      ]
    });

    // Create Agent Alias
    this.costAnalysisAgentAlias = new bedrock.CfnAgentAlias(this, 'CostAnalysisAgentAlias', {
      agentId: this.costAnalysisAgent.attrAgentId,
      agentAliasName: 'prod',
      description: 'Production alias for cost analysis agent',
    });

    // Outputs
    new cdk.CfnOutput(this, 'CostAnalysisAgentId', {
      value: this.costAnalysisAgent.attrAgentId,
      description: 'Cost Analysis Agent ID',
    });

    new cdk.CfnOutput(this, 'CostAnalysisAgentAliasId', {
      value: this.costAnalysisAgentAlias.attrAgentAliasId,
      description: 'Cost Analysis Agent Alias ID',
    });
  }
}
