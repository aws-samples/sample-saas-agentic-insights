import * as cdk from 'aws-cdk-lib';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as events from 'aws-cdk-lib/aws-events';
import * as targets from 'aws-cdk-lib/aws-events-targets';
import * as iam from 'aws-cdk-lib/aws-iam';
import { Construct } from 'constructs';

interface MetricsFrameworkStackProps extends cdk.StackProps {
  eventBus: events.EventBus;
}

export class MetricsFrameworkStack extends cdk.Stack {
  public readonly metricsTable: dynamodb.Table;
  public readonly metricsCollectorLayer: lambda.LayerVersion;

  constructor(scope: Construct, id: string, props: MetricsFrameworkStackProps) {
    super(scope, id, props);

    // DynamoDB table for raw metrics (90-day TTL)
    this.metricsTable = new dynamodb.Table(this, 'MetricsTable', {
      tableName: 'AgenticInsights-Metrics',
      partitionKey: { name: 'tenant_id', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'timestamp_event', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      timeToLiveAttribute: 'ttl',
      stream: dynamodb.StreamViewType.NEW_AND_OLD_IMAGES,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    // GSI for event_type queries
    this.metricsTable.addGlobalSecondaryIndex({
      indexName: 'EventTypeIndex',
      partitionKey: { name: 'event_type', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'timestamp', type: dynamodb.AttributeType.STRING },
    });

    // GSI for service_name queries
    this.metricsTable.addGlobalSecondaryIndex({
      indexName: 'ServiceNameIndex',
      partitionKey: { name: 'service_name', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'timestamp', type: dynamodb.AttributeType.STRING },
    });

    // Lambda Layer for metrics collection
    this.metricsCollectorLayer = new lambda.LayerVersion(this, 'MetricsCollectorLayer', {
      layerVersionName: 'agentic-insights-metrics-collector',
      code: lambda.Code.fromAsset('src/layers/metrics-collector'),
      compatibleRuntimes: [lambda.Runtime.PYTHON_3_11],
      description: 'Enhanced metrics collection library with real-time cost calculation',
    });

    // MetricsService Lambda function
    const metricsService = new lambda.Function(this, 'MetricsService', {
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'handler.handler',
      code: lambda.Code.fromAsset('src/control-plane/metrics'),
      environment: {
        METRICS_TABLE_NAME: this.metricsTable.tableName,
      },
      timeout: cdk.Duration.seconds(30),
    });

    // Grant permissions
    this.metricsTable.grantWriteData(metricsService);

    // EventBridge rule for metrics processing (reuse existing bus)
    new events.Rule(this, 'MetricsProcessingRule', {
      eventBus: props.eventBus,
      eventPattern: {
        source: ['agentic-insights.metrics'],
        detailType: ['Tenant Metric Event'],
      },
      targets: [new targets.LambdaFunction(metricsService)],
    });

    // Outputs
    new cdk.CfnOutput(this, 'MetricsTableName', {
      value: this.metricsTable.tableName,
      description: 'DynamoDB table for raw metrics',
    });

    new cdk.CfnOutput(this, 'MetricsCollectorLayerArn', {
      value: this.metricsCollectorLayer.layerVersionArn,
      description: 'Lambda Layer ARN for metrics collection',
    });
  }
}
