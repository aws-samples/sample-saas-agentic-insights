#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { ControlPlaneStack } from './control-plane-stack';
import { AppPlaneStack } from './app-plane-stack';
import { AIDescriptionStack } from './ai-description-stack';
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

// Application Plane Stack - handles e-commerce functionality
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

// AI Description Stack - handles AI-powered product description generation
const aiDescriptionStack = new AIDescriptionStack(app, 'AgenticInsightsAIDescription', {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION,
  },
  appPlaneApiId: appPlaneStack.appPlaneApi.restApiId,
  appPlaneApiRootResourceId: appPlaneStack.appPlaneApi.root.resourceId,
  authorizer: appPlaneStack.authorizer,
});





// Cost Analysis Agent Stack - simple agent for dataset exploration
const costAnalysisAgentStack = new CostAnalysisAgentStack(app, 'AgenticInsightsCostAnalysisAgent', {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION,
  },
  costPerTenantTableName: metricsFrameworkStack.costPerTenantTable.tableName,
});

// Add dependencies
metricsFrameworkStack.addDependency(controlPlaneStack);
appPlaneStack.addDependency(controlPlaneStack);
appPlaneStack.addDependency(metricsFrameworkStack);
aiDescriptionStack.addDependency(appPlaneStack);


costAnalysisAgentStack.addDependency(metricsFrameworkStack);
