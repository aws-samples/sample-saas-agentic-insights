import * as cdk from "aws-cdk-lib";
import * as iam from "aws-cdk-lib/aws-iam";
import * as dsql from "aws-cdk-lib/aws-dsql";
import { Construct } from "constructs";

export class ChurnAgentStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);



    // Aurora DSQL Cluster (L1 construct)
    const dsqlCluster = new dsql.CfnCluster(this, "ChurnAgentDSQLCluster", {
      deletionProtectionEnabled: false,
    });

    // IAM Role for Bedrock Agent Core
    const bedrockAgentRole = new iam.Role(this, "BedrockAgentRole", {
      assumedBy: new iam.ServicePrincipal("bedrock-agentcore.amazonaws.com"),
    });

    // Add inline policies to the role
    bedrockAgentRole.addToPolicy(
      new iam.PolicyStatement({
        sid: "ECRImageAccess",
        effect: iam.Effect.ALLOW,
        actions: ["ecr:BatchGetImage", "ecr:GetDownloadUrlForLayer"],
        resources: [`arn:aws:ecr:${this.region}:${this.account}:repository/*`],
      })
    );

    bedrockAgentRole.addToPolicy(
      new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        actions: ["logs:DescribeLogStreams", "logs:CreateLogGroup"],
        resources: [
          `arn:aws:logs:${this.region}:${this.account}:log-group:/aws/bedrock-agentcore/runtimes/*`,
        ],
      })
    );

    bedrockAgentRole.addToPolicy(
      new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        actions: ["logs:DescribeLogGroups"],
        resources: [`arn:aws:logs:${this.region}:${this.account}:log-group:*`],
      })
    );

    bedrockAgentRole.addToPolicy(
      new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        actions: ["logs:CreateLogStream", "logs:PutLogEvents"],
        resources: [
          `arn:aws:logs:${this.region}:${this.account}:log-group:/aws/bedrock-agentcore/runtimes/*:log-stream:*`,
        ],
      })
    );

    bedrockAgentRole.addToPolicy(
      new iam.PolicyStatement({
        sid: "ECRTokenAccess",
        effect: iam.Effect.ALLOW,
        actions: ["ecr:GetAuthorizationToken"],
        resources: ["*"],
      })
    );

    bedrockAgentRole.addToPolicy(
      new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        actions: [
          "xray:PutTraceSegments",
          "xray:PutTelemetryRecords",
          "xray:GetSamplingRules",
          "xray:GetSamplingTargets",
        ],
        resources: ["*"],
      })
    );

    bedrockAgentRole.addToPolicy(
      new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        actions: ["cloudwatch:PutMetricData"],
        resources: ["*"],
        conditions: {
          StringEquals: {
            "cloudwatch:namespace": "bedrock-agentcore",
          },
        },
      })
    );

    bedrockAgentRole.addToPolicy(
      new iam.PolicyStatement({
        sid: "BedrockAgentCoreRuntime",
        effect: iam.Effect.ALLOW,
        actions: [
          "bedrock-agentcore:InvokeAgentRuntime",
          "bedrock-agentcore:InvokeAgentRuntimeForUser",
        ],
        resources: [
          `arn:aws:bedrock-agentcore:${this.region}:${this.account}:runtime/*`,
        ],
      })
    );

    bedrockAgentRole.addToPolicy(
      new iam.PolicyStatement({
        sid: "BedrockAgentCoreMemoryCreateMemory",
        effect: iam.Effect.ALLOW,
        actions: ["bedrock-agentcore:CreateMemory"],
        resources: ["*"],
      })
    );

    bedrockAgentRole.addToPolicy(
      new iam.PolicyStatement({
        sid: "BedrockAgentCoreMemory",
        effect: iam.Effect.ALLOW,
        actions: [
          "bedrock-agentcore:CreateEvent",
          "bedrock-agentcore:GetEvent",
          "bedrock-agentcore:GetMemory",
          "bedrock-agentcore:GetMemoryRecord",
          "bedrock-agentcore:ListActors",
          "bedrock-agentcore:ListEvents",
          "bedrock-agentcore:ListMemoryRecords",
          "bedrock-agentcore:ListSessions",
          "bedrock-agentcore:DeleteEvent",
          "bedrock-agentcore:DeleteMemoryRecord",
          "bedrock-agentcore:RetrieveMemoryRecords",
        ],
        resources: [
          `arn:aws:bedrock-agentcore:${this.region}:${this.account}:memory/*`,
        ],
      })
    );

    bedrockAgentRole.addToPolicy(
      new iam.PolicyStatement({
        sid: "BedrockAgentCoreIdentityGetResourceApiKey",
        effect: iam.Effect.ALLOW,
        actions: ["bedrock-agentcore:GetResourceApiKey"],
        resources: [
          `arn:aws:bedrock-agentcore:${this.region}:${this.account}:token-vault/default`,
          `arn:aws:bedrock-agentcore:${this.region}:${this.account}:token-vault/default/apikeycredentialprovider/*`,
          `arn:aws:bedrock-agentcore:${this.region}:${this.account}:workload-identity-directory/default`,
          `arn:aws:bedrock-agentcore:${this.region}:${this.account}:workload-identity-directory/default/workload-identity/churn_agent-*`,
        ],
      })
    );

    bedrockAgentRole.addToPolicy(
      new iam.PolicyStatement({
        sid: "BedrockAgentCoreIdentityGetCredentialProviderClientSecret",
        effect: iam.Effect.ALLOW,
        actions: ["secretsmanager:GetSecretValue"],
        resources: [
          `arn:aws:secretsmanager:${this.region}:${this.account}:secret:bedrock-agentcore-identity!default/oauth2/*`,
        ],
      })
    );

    bedrockAgentRole.addToPolicy(
      new iam.PolicyStatement({
        sid: "BedrockAgentCoreIdentityGetResourceOauth2Token",
        effect: iam.Effect.ALLOW,
        actions: ["bedrock-agentcore:GetResourceOauth2Token"],
        resources: [
          `arn:aws:bedrock-agentcore:${this.region}:${this.account}:token-vault/default`,
          `arn:aws:bedrock-agentcore:${this.region}:${this.account}:token-vault/default/oauth2credentialprovider/*`,
          `arn:aws:bedrock-agentcore:${this.region}:${this.account}:workload-identity-directory/default`,
          `arn:aws:bedrock-agentcore:${this.region}:${this.account}:workload-identity-directory/default/workload-identity/churn_agent-*`,
        ],
      })
    );

    bedrockAgentRole.addToPolicy(
      new iam.PolicyStatement({
        sid: "BedrockModelInvocation",
        effect: iam.Effect.ALLOW,
        actions: [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream",
          "bedrock:ApplyGuardrail",
        ],
        resources: [
          "arn:aws:bedrock:*::foundation-model/*",
          "arn:aws:bedrock:*:*:inference-profile/*",
          `arn:aws:bedrock:${this.region}:${this.account}:*`,
        ],
      })
    );

    bedrockAgentRole.addToPolicy(
      new iam.PolicyStatement({
        sid: "BedrockAgentCoreCodeInterpreter",
        effect: iam.Effect.ALLOW,
        actions: [
          "bedrock-agentcore:CreateCodeInterpreter",
          "bedrock-agentcore:StartCodeInterpreterSession",
          "bedrock-agentcore:InvokeCodeInterpreter",
          "bedrock-agentcore:StopCodeInterpreterSession",
          "bedrock-agentcore:DeleteCodeInterpreter",
          "bedrock-agentcore:ListCodeInterpreters",
          "bedrock-agentcore:GetCodeInterpreter",
          "bedrock-agentcore:GetCodeInterpreterSession",
          "bedrock-agentcore:ListCodeInterpreterSessions",
        ],
        resources: [
          `arn:aws:bedrock-agentcore:${this.region}:aws:code-interpreter/*`,
          `arn:aws:bedrock-agentcore:${this.region}:${this.account}:code-interpreter/*`,
          `arn:aws:bedrock-agentcore:${this.region}:${this.account}:code-interpreter-custom/*`,
        ],
      })
    );

    // DSQL cluster read/write access
    bedrockAgentRole.addToPolicy(
      new iam.PolicyStatement({
        sid: "DSQLAccess",
        effect: iam.Effect.ALLOW,
        actions: ["dsql:DbConnect", "dsql:DbConnectAdmin"],
        resources: [dsqlCluster.attrResourceArn],
      })
    );

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

    // Outputs

    new cdk.CfnOutput(this, "DSQLClusterArn", {
      value: dsqlCluster.attrResourceArn,
      description: "Aurora DSQL cluster ARN",
    });

    new cdk.CfnOutput(this, "DSQLClusterId", {
      value: dsqlCluster.attrIdentifier,
      description: "Aurora DSQL cluster ID",
    });

    new cdk.CfnOutput(this, "DSQLEndpoint", {
      value: `${dsqlCluster.attrIdentifier}.dsql.${this.region}.on.aws`,
      description: "Aurora DSQL cluster endpoint",
    });

    new cdk.CfnOutput(this, "BedrockAgentRoleArn", {
      value: bedrockAgentRole.roleArn,
      description: "Bedrock Agent IAM role ARN",
    });
  }
}
