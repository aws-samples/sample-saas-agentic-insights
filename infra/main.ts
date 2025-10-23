#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { ControlPlaneStack } from './control-plane-stack';
import { AppPlaneStack } from './app-plane-stack';
import { MetricsFrameworkStack } from './metrics-framework-stack';
import { CostAnalysisAgentStack } from './cost-analysis-agent-stack';

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

// Cost Analysis Agent Stack - handles cost analysis with moved components
const costAnalysisAgentStack = new CostAnalysisAgentStack(app, 'AgenticInsightsCostAnalysisAgent', {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION,
  },
  metricsTable: metricsFrameworkStack.metricsTable,
});

// Add dependencies
metricsFrameworkStack.addDependency(controlPlaneStack);
appPlaneStack.addDependency(controlPlaneStack);
appPlaneStack.addDependency(metricsFrameworkStack);
costAnalysisAgentStack.addDependency(metricsFrameworkStack);
