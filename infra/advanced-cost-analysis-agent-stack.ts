import * as cdk from 'aws-cdk-lib';
import * as bedrock from 'aws-cdk-lib/aws-bedrock';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as fs from 'fs';
import * as path from 'path';
import { Construct } from 'constructs';

export class AdvancedCostAnalysisAgentStack extends cdk.Stack {
  public readonly advancedCostAnalysisAgent: bedrock.CfnAgent;
  public readonly advancedCostAnalysisAgentAlias: bedrock.CfnAgentAlias;

  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // Load agent configuration
    const agentConfigPath = path.join(__dirname, '../src/control-plane/agents/advanced-cost-analysis/agent-config.yaml');
    const instructionsPath = path.join(__dirname, '..', 'src', 'control-plane', 'agents', 'advanced-cost-analysis', 'instructions.txt');
    
    // Parse agent config
    const agentConfigContent = fs.readFileSync(agentConfigPath, 'utf8');
    const agentName = agentConfigContent.match(/name:\s*(.+)/)?.[1]?.trim() || 'agentic-insights-advanced-cost-analysis-agent';
    const agentModel = agentConfigContent.match(/model:\s*(.+)/)?.[1]?.trim() || 'us.anthropic.claude-3-haiku-20240307-v1:0';
    const agentDescription = agentConfigContent.match(/description:\s*(.+)/)?.[1]?.trim() || 'Advanced SaaS cost analysis agent';
    
    const agentInstructions = fs.readFileSync(instructionsPath, 'utf8');

    // Get region for IAM resources
    const region = cdk.Stack.of(this).region;

    // IAM role for the agent
    const agentRole = new iam.Role(this, 'AdvancedCostAnalysisAgentRole', {
      assumedBy: new iam.ServicePrincipal('bedrock.amazonaws.com'),
      roleName: `agentic-insights-advanced-cost-analysis-agent-role-${region}`,
      inlinePolicies: {
        BedrockAgentPolicy: new iam.PolicyDocument({
          statements: [
            new iam.PolicyStatement({
              effect: iam.Effect.ALLOW,
              actions: [
                'bedrock:InvokeModel',
              ],
              resources: [
                `arn:aws:bedrock:${region}::foundation-model/${agentModel}`,
              ],
            }),
          ],
        }),
      },
    });

    // Bedrock Agent (no action groups)
    this.advancedCostAnalysisAgent = new bedrock.CfnAgent(this, 'AdvancedCostAnalysisAgent', {
      agentName: `${agentName}-${region}`,
      description: `${agentDescription} in ${region}`,
      foundationModel: agentModel,
      agentResourceRoleArn: agentRole.roleArn,
      instruction: agentInstructions,
      idleSessionTtlInSeconds: 1800
    });

    // Agent Alias
    this.advancedCostAnalysisAgentAlias = new bedrock.CfnAgentAlias(this, 'AdvancedCostAnalysisAgentAlias', {
      agentId: this.advancedCostAnalysisAgent.attrAgentId,
      agentAliasName: 'prod',
      description: 'Production alias for advanced cost analysis agent',
    });

    // Outputs
    new cdk.CfnOutput(this, 'AdvancedCostAnalysisAgentId', {
      value: this.advancedCostAnalysisAgent.attrAgentId,
      description: 'Advanced Cost Analysis Agent ID',
    });

    new cdk.CfnOutput(this, 'AdvancedCostAnalysisAgentAliasId', {
      value: this.advancedCostAnalysisAgentAlias.attrAgentAliasId,
      description: 'Advanced Cost Analysis Agent Alias ID',
    });
  }
}
