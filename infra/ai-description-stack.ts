import * as cdk from 'aws-cdk-lib';
import * as apigateway from 'aws-cdk-lib/aws-apigateway';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as logs from 'aws-cdk-lib/aws-logs';
import * as bedrock from 'aws-cdk-lib/aws-bedrock';
import * as fs from 'fs';
import * as path from 'path';
import { Construct } from 'constructs';

interface AIDescriptionStackProps extends cdk.StackProps {
  appPlaneApiId: string;
  appPlaneApiRootResourceId: string;
  authorizer: apigateway.TokenAuthorizer;
}

export class AIDescriptionStack extends cdk.Stack {
  public readonly productDescFunction: lambda.Function;
  public readonly bedrockAgent: bedrock.CfnAgent;
  public readonly bedrockAgentAlias: bedrock.CfnAgentAlias;

  constructor(scope: Construct, id: string, props: AIDescriptionStackProps) {
    super(scope, id, props);

    // Load agent configuration
    const agentConfigPath = path.join(__dirname, '../src/app-plane/agents/product-desc/agent-config.yaml');
    const agentInstructionsPath = path.join(__dirname, '../src/app-plane/agents/product-desc/instructions.txt');
    
    // Parse agent config (simple YAML parsing for our use case)
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
      // Explicitly set to not use any action groups or knowledge bases
      actionGroups: [],
      knowledgeBases: [],
      // Override the orchestration prompt to remove function-calling expectations
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
    this.productDescFunction = new lambda.Function(this, 'ProductDescFunction', {
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'handler.handler',
      code: lambda.Code.fromAsset('src/app-plane/product-desc'),
      environment: {
        BEDROCK_AGENT_ID: this.bedrockAgent.attrAgentId,
        BEDROCK_AGENT_ALIAS_ID: this.bedrockAgentAlias.attrAgentAliasId,
        CLAUDE_INPUT_TOKEN_PRICE: '0.00025',  // Claude 3 Haiku pricing
        CLAUDE_OUTPUT_TOKEN_PRICE: '0.00125',
      },
      timeout: cdk.Duration.seconds(30),
      memorySize: 512,
      description: 'AI Product Description Generator using Bedrock Agent',
    });

    // CloudWatch Log Group with retention
    new logs.LogGroup(this, 'ProductDescLogGroup', {
      logGroupName: `/aws/lambda/${this.productDescFunction.functionName}`,
      retention: logs.RetentionDays.ONE_WEEK,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    // IAM permissions for Bedrock agent invocation
    this.productDescFunction.addToRolePolicy(new iam.PolicyStatement({
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

    // Get reference to existing API Gateway
    const existingApi = apigateway.RestApi.fromRestApiAttributes(this, 'ExistingAppPlaneApi', {
      restApiId: props.appPlaneApiId,
      rootResourceId: props.appPlaneApiRootResourceId,
    });

    // Create AI resource exactly like basic/premium resources
    const aiResource = existingApi.root.addResource('ai');
    const generateDescResource = aiResource.addResource('generate-description');

    // Lambda integration
    const productDescIntegration = new apigateway.LambdaIntegration(this.productDescFunction, {
      requestTemplates: { 'application/json': '{ "statusCode": "200" }' },
      proxy: true,
    });

    // Add POST method with authorizer (exact same pattern as orders)
    generateDescResource.addMethod('POST', productDescIntegration, {
      authorizer: props.authorizer
    });

    // Add explicit OPTIONS method without authorization (like working endpoints)
    generateDescResource.addMethod('OPTIONS', new apigateway.MockIntegration({
      integrationResponses: [{
        statusCode: '204',
        responseParameters: {
          'method.response.header.Access-Control-Allow-Headers': "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token,tenant-id,tier-name'",
          'method.response.header.Access-Control-Allow-Methods': "'OPTIONS,GET,PUT,POST,DELETE,PATCH,HEAD'",
          'method.response.header.Access-Control-Allow-Origin': "'*'",
        },
      }],
      passthroughBehavior: apigateway.PassthroughBehavior.NEVER,
      requestTemplates: {
        'application/json': '{"statusCode": 204}',
      },
    }), {
      methodResponses: [{
        statusCode: '204',
        responseParameters: {
          'method.response.header.Access-Control-Allow-Headers': true,
          'method.response.header.Access-Control-Allow-Methods': true,
          'method.response.header.Access-Control-Allow-Origin': true,
        },
      }],
    });

    // Force API Gateway deployment to make endpoints immediately available
    new apigateway.Deployment(this, 'AIEndpointDeployment', {
      api: existingApi,
      description: 'Deploy AI endpoints to prod stage',
    });

    // Outputs
    new cdk.CfnOutput(this, 'ProductDescFunctionName', {
      value: this.productDescFunction.functionName,
      description: 'Product Description Lambda Function Name',
    });

    new cdk.CfnOutput(this, 'AIDescriptionEndpoint', {
      value: `https://${props.appPlaneApiId}.execute-api.${this.region}.amazonaws.com/prod/ai/generate-description`,
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

    new cdk.CfnOutput(this, 'BedrockAgentArn', {
      value: this.bedrockAgent.attrAgentArn,
      description: 'Bedrock Agent ARN',
    });
  }
}
