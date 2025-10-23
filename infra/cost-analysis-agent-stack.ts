import * as cdk from 'aws-cdk-lib';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as bedrock from 'aws-cdk-lib/aws-bedrock';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import { DynamoEventSource } from 'aws-cdk-lib/aws-lambda-event-sources';
import * as fs from 'fs';
import * as path from 'path';
import { Construct } from 'constructs';

interface CostAnalysisAgentStackProps extends cdk.StackProps {
  metricsTable: dynamodb.Table;
}

export class CostAnalysisAgentStack extends cdk.Stack {
  public readonly costAnalysisAgent: bedrock.CfnAgent;
  public readonly costAnalysisAgentAlias: bedrock.CfnAgentAlias;
  public readonly metricsAggregationTable: dynamodb.Table;
  public readonly costPerTenantTable: dynamodb.Table;

  constructor(scope: Construct, id: string, props: CostAnalysisAgentStackProps) {
    super(scope, id, props);

    // DynamoDB table for aggregated metrics (monthly aggregation)
    this.metricsAggregationTable = new dynamodb.Table(this, 'MetricsAggregationTable', {
      tableName: 'AgenticInsights-MetricsAggregation',
      partitionKey: { name: 'tenant_id', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'metric_date_type', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      stream: dynamodb.StreamViewType.NEW_AND_OLD_IMAGES,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    // GSI for month-based queries
    this.metricsAggregationTable.addGlobalSecondaryIndex({
      indexName: 'MonthIndex',
      partitionKey: { name: 'month', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'metric_type', type: dynamodb.AttributeType.STRING },
    });

    // DynamoDB table for cost per tenant (aggregated from MetricsAggregation)
    this.costPerTenantTable = new dynamodb.Table(this, 'CostPerTenantTable', {
      tableName: 'AgenticInsights-CostPerTenant',
      partitionKey: { name: 'tenant_id', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'month', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    // GSI for month-based queries across all tenants
    this.costPerTenantTable.addGlobalSecondaryIndex({
      indexName: 'MonthIndex',
      partitionKey: { name: 'month', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'tier', type: dynamodb.AttributeType.STRING },
    });

    // MetricsAggregatorService Lambda function
    const metricsAggregatorService = new lambda.Function(this, 'MetricsAggregatorService', {
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'handler.handler',
      code: lambda.Code.fromAsset('src/control-plane/metrics-aggregator'),
      environment: {
        METRICS_AGGREGATION_TABLE_NAME: this.metricsAggregationTable.tableName,
      },
      timeout: cdk.Duration.seconds(60),
    });

    // CostAggregatorService Lambda function (processes MetricsAggregation stream)
    const costAggregatorService = new lambda.Function(this, 'CostAggregatorService', {
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'handler.handler',
      code: lambda.Code.fromAsset('src/control-plane/cost-aggregator'),
      environment: {
        COST_PER_TENANT_TABLE_NAME: this.costPerTenantTable.tableName,
        METRICS_AGGREGATION_TABLE_NAME: this.metricsAggregationTable.tableName,
      },
      timeout: cdk.Duration.seconds(60),
    });

    // Add DynamoDB stream event sources
    metricsAggregatorService.addEventSource(
      new DynamoEventSource(props.metricsTable, {
        startingPosition: lambda.StartingPosition.LATEST,
        batchSize: 10,
        retryAttempts: 3,
      })
    );

    costAggregatorService.addEventSource(new DynamoEventSource(this.metricsAggregationTable, {
      startingPosition: lambda.StartingPosition.LATEST,
      batchSize: 10,
      retryAttempts: 3,
    }));

    // Grant permissions
    props.metricsTable.grantReadData(metricsAggregatorService);
    this.metricsAggregationTable.grantReadWriteData(metricsAggregatorService);
    this.metricsAggregationTable.grantReadData(costAggregatorService);
    this.costPerTenantTable.grantReadWriteData(costAggregatorService);

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
        COST_PER_TENANT_TABLE_NAME: this.costPerTenantTable.tableName,
      },
    });

    // Grant Lambda permissions
    getCostDatasetFunction.grantInvoke(new iam.ServicePrincipal('bedrock.amazonaws.com'));

    // Grant DynamoDB permissions
    this.costPerTenantTable.grantReadData(getCostDatasetFunction);

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

    new cdk.CfnOutput(this, 'MetricsAggregationTableName', {
      value: this.metricsAggregationTable.tableName,
      description: 'DynamoDB table for aggregated metrics',
    });

    new cdk.CfnOutput(this, 'CostPerTenantTableName', {
      value: this.costPerTenantTable.tableName,
      description: 'DynamoDB table for cost per tenant data',
    });
  }
}
