#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { ControlPlaneStack } from './control-plane-stack';
import { AppPlaneStack } from './app-plane-stack';
import { AIDescriptionStack } from './ai-description-stack';

const app = new cdk.App();

// Control Plane Stack - handles tenant management and provisioning
const controlPlaneStack = new ControlPlaneStack(app, 'AgenticInsightsControlPlane', {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION,
  },
});

// Application Plane Stack - handles e-commerce functionality
const appPlaneStack = new AppPlaneStack(app, 'AgenticInsightsAppPlane', {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION,
  },
  // Pass EventBridge bus from control plane for tenant provisioning
  eventBus: controlPlaneStack.eventBus,
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

// Add dependencies
appPlaneStack.addDependency(controlPlaneStack);
aiDescriptionStack.addDependency(appPlaneStack);
