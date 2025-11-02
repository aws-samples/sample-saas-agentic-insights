import * as cdk from 'aws-cdk-lib';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as events from 'aws-cdk-lib/aws-events';
import * as targets from 'aws-cdk-lib/aws-events-targets';
import * as logs from 'aws-cdk-lib/aws-logs';
import * as logs_destinations from 'aws-cdk-lib/aws-logs-destinations';
import * as iam from 'aws-cdk-lib/aws-iam';
import { DynamoEventSource } from 'aws-cdk-lib/aws-lambda-event-sources';
import { Construct } from 'constructs';

interface MetricsFrameworkStackProps extends cdk.StackProps {
  eventBus: events.EventBus;
}

export class MetricsFrameworkStack extends cdk.Stack {
  public readonly metricsTable: dynamodb.Table;
  public readonly usageMetricsTable: dynamodb.Table;
  public readonly metricsCollectorLayer: lambda.LayerVersion;
  public readonly costAggregationTable: dynamodb.Table;
  public readonly costPerTenantTable: dynamodb.Table;
  private usageMetricsAggregator?: lambda.Function;

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

    // DynamoDB table for aggregated metrics (monthly aggregation)
    this.costAggregationTable = new dynamodb.Table(this, 'CostAggregationTable', {
      tableName: 'AgenticInsights-CostAggregation',
      partitionKey: { name: 'tenant_id', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'metric_date_type', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      stream: dynamodb.StreamViewType.NEW_AND_OLD_IMAGES,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    // GSI for month-based queries
    this.costAggregationTable.addGlobalSecondaryIndex({
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

    // DynamoDB table for enhanced usage metrics (with TTL-based retention)
    this.usageMetricsTable = new dynamodb.Table(this, 'UsageMetricsTable', {
      tableName: 'AgenticInsights-UsageMetrics',
      partitionKey: { name: 'PK', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'SK', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      timeToLiveAttribute: 'ttl',
      pointInTimeRecovery: true,
      encryption: dynamodb.TableEncryption.AWS_MANAGED,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    // GSI 1: MonthIndex - For monthly queries and trend analysis
    this.usageMetricsTable.addGlobalSecondaryIndex({
      indexName: 'MonthIndex',
      partitionKey: { name: 'month', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'tenant_id', type: dynamodb.AttributeType.STRING },
      projectionType: dynamodb.ProjectionType.ALL,
    });

    // GSI 2: FeatureIndex - For feature-specific queries
    this.usageMetricsTable.addGlobalSecondaryIndex({
      indexName: 'FeatureIndex',
      partitionKey: { name: 'feature_name', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'tenant_timestamp', type: dynamodb.AttributeType.STRING },
      projectionType: dynamodb.ProjectionType.ALL,
    });

    // GSI 3: PlatformIndex - For cross-tenant platform analytics
    this.usageMetricsTable.addGlobalSecondaryIndex({
      indexName: 'PlatformIndex',
      partitionKey: { name: 'metric_type_month', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'aggregation_level', type: dynamodb.AttributeType.STRING },
      projectionType: dynamodb.ProjectionType.ALL,
    });

    // GSI 4: TenantTimestampIndex - Optimized for TTV first interaction queries
    // Enables direct timestamp-based queries without month-by-month iteration
    this.usageMetricsTable.addGlobalSecondaryIndex({
      indexName: 'TenantTimestampIndex',
      partitionKey: { name: 'tenant_id', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'timestamp', type: dynamodb.AttributeType.STRING },
      projectionType: dynamodb.ProjectionType.INCLUDE,
      nonKeyAttributes: ['usage_count', 'feature_name', 'metric_type'],
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

    // CostAggregatorService Lambda function
    const costAggregatorService = new lambda.Function(this, 'CostAggregatorService', {
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'handler.handler',
      code: lambda.Code.fromAsset('src/control-plane/cost-analysis/cost-aggregator'),
      environment: {
        COST_AGGREGATION_TABLE_NAME: this.costAggregationTable.tableName,
      },
      timeout: cdk.Duration.seconds(60),
    });

    // CostPerTenantService Lambda function (processes MetricsAggregation stream)
    const costPerTenantService = new lambda.Function(this, 'CostPerTenantService', {
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'handler.handler',
      code: lambda.Code.fromAsset('src/control-plane/cost-analysis/cost-per-tenant'),
      environment: {
        COST_PER_TENANT_TABLE_NAME: this.costPerTenantTable.tableName,
        COST_AGGREGATION_TABLE_NAME: this.costAggregationTable.tableName,
      },
      timeout: cdk.Duration.seconds(60),
    });

    // Add DynamoDB stream event sources
    costAggregatorService.addEventSource(
      new DynamoEventSource(this.metricsTable, {
        startingPosition: lambda.StartingPosition.LATEST,
        batchSize: 10,
        retryAttempts: 3,
      })
    );

    costPerTenantService.addEventSource(new DynamoEventSource(this.costAggregationTable, {
      startingPosition: lambda.StartingPosition.LATEST,
      batchSize: 10,
      retryAttempts: 3,
    }));

    // Grant permissions
    this.metricsTable.grantWriteData(metricsService);
    this.metricsTable.grantReadData(costAggregatorService);
    this.costAggregationTable.grantReadWriteData(costAggregatorService);
    this.costAggregationTable.grantReadData(costPerTenantService);
    this.costPerTenantTable.grantReadWriteData(costPerTenantService);

    // EventBridge rule for metrics processing (reuse existing bus)
    new events.Rule(this, 'MetricsProcessingRule', {
      eventBus: props.eventBus,
      eventPattern: {
        source: ['agentic-insights.metrics'],
        detailType: ['Tenant Metric Event'],
      },
      targets: [new targets.LambdaFunction(metricsService)],
    });

// Usage Metrics Aggregator Lambda function (processes CloudWatch Logs)
    this.usageMetricsAggregator = new lambda.Function(this, 'UsageMetricsAggregator', {
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'handler.lambda_handler',
      code: lambda.Code.fromAsset('src/control-plane/usage-metrics-aggregator'),
      environment: {
        USAGE_METRICS_TABLE_NAME: this.usageMetricsTable.tableName,
        AGGREGATION_INTERVAL: 'hourly',
        BATCH_SIZE: '25',
      },
      timeout: cdk.Duration.minutes(5),
      memorySize: 512,
    });

    // Grant permissions to usage metrics aggregator
    this.usageMetricsTable.grantReadWriteData(this.usageMetricsAggregator);

    // Outputs
    new cdk.CfnOutput(this, 'MetricsTableName', {
      value: this.metricsTable.tableName,
      description: 'DynamoDB table for raw metrics',
    });

    new cdk.CfnOutput(this, 'MetricsCollectorLayerArn', {
      value: this.metricsCollectorLayer.layerVersionArn,
      description: 'Lambda Layer ARN for metrics collection',
    });

    new cdk.CfnOutput(this, 'UsageMetricsTableName', {
      value: this.usageMetricsTable.tableName,
      description: 'DynamoDB table for enhanced usage metrics with aggregations',
    });

    new cdk.CfnOutput(this, 'UsageMetricsAggregatorArn', {
      value: this.usageMetricsAggregator.functionArn,
      description: 'Lambda function ARN for usage metrics aggregation',
    });

    new cdk.CfnOutput(this, 'CostAggregationTableName', {
      value: this.costAggregationTable.tableName,
      description: 'DynamoDB table for aggregated cost metrics',
    });

    new cdk.CfnOutput(this, 'CostPerTenantTableName', {
      value: this.costPerTenantTable.tableName,
      description: 'DynamoDB table for cost per tenant data',
    });
  }
  /**
     * Get the usage metrics aggregator Lambda function
     * This is used by AppPlaneStack to create the subscription filter
     */
  public getUsageMetricsAggregator(): lambda.IFunction {
    if (!this.usageMetricsAggregator) {
      throw new Error('Usage metrics aggregator not initialized');
    }
    return this.usageMetricsAggregator;
  }
}
