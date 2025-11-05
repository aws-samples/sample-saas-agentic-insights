#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { ControlPlaneStack } from './control-plane-stack';
import { AppPlaneStack } from './app-plane-stack';
import { MetricsFrameworkStack } from './metrics-framework-stack';
import { CostAnalysisAgentStack } from './cost-analysis-agent-stack';
import { ChurnAgentStack } from './churn-agent-stack';
import { UsageInsightsAgentStack } from './usage-insights-agent-stack';

const app = new cdk.App();

// Control Plane Stack - handles tenant management and provisioning
const controlPlaneStack = new ControlPlaneStack(app, 'AgenticInsightsControlPlane', {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION,
  },
});

// Metrics Framework Stack - handles metrics collection and processing
const metricsFrameworkStack = new MetricsFrameworkStack(app, 'AgenticInsightsMetricsFramework', {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION,
  },
  eventBus: controlPlaneStack.eventBus,
});

// Application Plane Stack - handles e-commerce functionality with AI
const appPlaneStack = new AppPlaneStack(app, 'AgenticInsightsAppPlane', {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION,
  },
  // Pass EventBridge bus from control plane for tenant provisioning
  eventBus: controlPlaneStack.eventBus,
  // Pass metrics collector layer for application services
  metricsCollectorLayer: metricsFrameworkStack.metricsCollectorLayer,
  metricsEventBusName: controlPlaneStack.eventBus.eventBusName,
});

// Cost Analysis Agent Stack - handles cost analysis with tables from metrics framework
const costAnalysisAgentStack = new CostAnalysisAgentStack(app, 'AgenticInsightsCostAnalysisAgent', {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION,
  },
  metricsTable: metricsFrameworkStack.metricsTable,
  costAggregationTable: metricsFrameworkStack.costAggregationTable,
  costPerTenantTable: metricsFrameworkStack.costPerTenantTable,
});

// Churn Agent Stack - handles churn prediction with React app and DSQL
const churnAgentStack = new ChurnAgentStack(app, 'AgenticInsightsChurnAgent', {

// Usage Insights Agent Stack - handles advanced usage insights with Strands agent
// Note: This stack uses CDK parameters for dynamic values during deployment
const usageInsightsAgentStack = new UsageInsightsAgentStack(app, 'AgenticInsightsUsageInsightsAgent', {

  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION,
  },
});

// Add dependencies
metricsFrameworkStack.addDependency(controlPlaneStack);
appPlaneStack.addDependency(controlPlaneStack);
appPlaneStack.addDependency(metricsFrameworkStack);
costAnalysisAgentStack.addDependency(metricsFrameworkStack);
churnAgentStack.addDependency(controlPlaneStack);
