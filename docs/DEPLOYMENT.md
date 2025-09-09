# Deployment Guide

## Prerequisites

- AWS CLI configured
- Node.js (v18+)
- AWS CDK CLI: `npm install -g aws-cdk`

## Deployment steps 

### 0. Prerequisites
**AWS CLI settings with AWS region you want to deploy**
```bash
export AWS_DEFAULT_REGION=eu-west-1
export CDK_DEFAULT_REGION=eu-west-1
```

**Check Bedrock Availability:**
- Verify Bedrock is available in target region
- Check model availability:
```bash
aws bedrock list-foundation-models --region eu-west-1 \
  --query 'modelSummaries[?contains(modelId, `claude-3-haiku`)]'
```

**Model ID Formats:**
- **us-east-1**: `us.anthropic.claude-3-haiku-20240307-v1:0`
- **Other regions**: `anthropic.claude-3-haiku-20240307-v1:0`

### 1. Clone and Setup
```bash
git clone <repository-url>
cd agentic-insights-saas
npm install
```

### 2. Deploy Base Architecture
```bash
./scripts/lab-01.1-deploy-base-architecture.sh
```
The script will ask to create a SaaS admin user towards the end of the deployment. Make sure to create one. You can create more users by running this script later. 

#### Access Your Applications
After the base deployment, the console output will show the following CloudFront URLs that will help to access the SaaS:
- **Landing Page URL**: Self-onboard new tenants
- **Admin Panel URL**: For SaaS admins to manage tenants & to access the Agentic Insight dashboard (an admin user is created during base architecture deployment)
- **SaaS App URL**: E-commerce functionality - for tenant users/admins to manage product catalog/create orders etc. 

### 3. Run Labs 
### Lab 01: Adding an AI agent to generate product descriptions : 
```bash
./scripts/lab-01.1-deploy-base-architecture.sh
```

### Lab 02: Adding metering framework & Cost analysis Agent: 
```bash
TODO
```

### Lab 03: Adding other Insight Agents & Insight Dashbaord
```bash
TODO
```

### Lab 04: Data Loading & advanced insights 
```bash
TODO
```


## Cleanup

```bash
./scripts/delete-all.sh
```

## Workshop link 
```url
https://studio.us-east-1.prod.workshops.aws/workshops/4b8fb79d-04da-45a2-83ee-b241fa5d7f74
```
