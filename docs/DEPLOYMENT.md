# Deployment Guide - AWS re:Invent Workshop

## Overview

This workshop demonstrates a complete multi-tenant SaaS platform built with AWS serverless technologies. The deployment follows a **base + labs** approach where participants first deploy the foundational architecture, then incrementally add features through individual labs.

## Prerequisites

### Required Tools
- **AWS CLI** configured with appropriate permissions
- **Node.js** (v18 or later)
- **AWS CDK CLI**: `npm install -g aws-cdk`

### AWS Permissions
Ensure your AWS credentials have permissions for:
- CloudFormation, Lambda, DynamoDB, API Gateway
- Cognito, EventBridge, S3, CloudFront
- Bedrock (for AI labs)

## Workshop Architecture

### Base Platform Components
- **Control Plane**: Tenant registration, authentication, provisioning
- **Application Plane**: Product management, order processing, user management  
- **Web Applications**: Landing page, admin panel, tenant SaaS app
- **Multi-Tenancy**: Complete data isolation with tier-based resource allocation

### Lab Extensions
- **Lab 01.1**: Base Architecture (foundational platform)
- **Lab 01.2**: AI Product Description Generator (Bedrock + Claude 3 Haiku)

## Lab 01.1: Base Architecture Deployment

### 1. Clone and Setup
```bash
git clone <repository-url>
cd agentic-insights-saas
npm install
```

### 2. Deploy the base architecture
```bash
./scripts/lab-01.1-deploy-base-architecture.sh
```

**What gets deployed:**
- Control Plane Stack (tenant management)
- Application Plane Stack (e-commerce functionality)
- 3 Web applications with auto-generated configurations
- Default admin user creation

### 3. Deployment Output
After successful deployment, you'll receive:
```
✅ Lab 01.1: Base Architecture deployed successfully!

🌐 Application URLs:
├── Landing Page: https://d1a2b3c4d5e6f7.cloudfront.net
├── Admin Panel:  https://d2b3c4d5e6f7g8.cloudfront.net  
└── SaaS App:     https://d3c4d5e6f7g8h9.cloudfront.net

🔑 Default Admin Credentials:
├── Email:    admin@example.com
└── Password: TempPassword123!

🚀 Ready for Lab 01.2!
```

## Lab 01.2: AI Product Description Generator

Deploy AI-powered product description generation:
```bash
./scripts/lab-01.2-deploy-product-description-ai-agent.sh
```

**Features added:**
- Amazon Bedrock integration with Claude 3 Haiku
- One-click AI description generation in product forms
- Usage tracking and cost monitoring
- Tenant-isolated AI requests

**Verification:**
1. Login to SaaS app as tenant admin
2. Create/edit a product
3. Click "Generate" button next to description field
4. AI generates professional product description

## Multi-Region Deployment

### Deploy to Different AWS Region

```bash
# Set target region
export AWS_DEFAULT_REGION=eu-west-1
export CDK_DEFAULT_REGION=eu-west-1

# Deploy base architecture
./scripts/lab-01.1-deploy-base-architecture.sh

# Deploy labs (optional)
./scripts/lab-01.2-deploy-product-description-ai-agent.sh
```

### Region Considerations

**Bedrock Availability (AI Labs):**
- Verify Bedrock is available in target region
- Check model availability:
```bash
aws bedrock list-foundation-models --region eu-west-1 \
  --query 'modelSummaries[?contains(modelId, `claude-3-haiku`)]'
```

**Model ID Formats:**
- **us-east-1**: `us.anthropic.claude-3-haiku-20240307-v1:0`
- **Other regions**: `anthropic.claude-3-haiku-20240307-v1:0`

## Workshop Activities

### Recommended Flow

#### Phase 1: Base Platform Exploration (Lab 01.1)
1. **Deploy Base**: `./scripts/lab-01.1-deploy-base-architecture.sh`
2. **Admin Access**: Login to admin panel with default credentials
3. **Tenant Registration**: Use landing page to create tenants
4. **Multi-Tenancy**: Create Basic ($29) and Premium ($99) tenants
5. **Data Isolation**: Verify tenant data separation

#### Phase 2: E-commerce Functionality
1. **Product Management**: Create products as tenant admin
2. **Shopping Experience**: Add products to cart, create orders
3. **User Management**: Create additional tenant users
4. **Role-Based Access**: Compare tenant_admin vs tenant_user capabilities

#### Phase 3: Tier Differences
1. **Basic Tier**: Shared DynamoDB tables for products and orders
2. **Premium Tier**: Dedicated Order tables per tenant
3. **Resource Allocation**: Observe tier-specific provisioning
4. **Cost Optimization**: Understand shared vs dedicated resource strategies

#### Phase 4: AI Integration (Lab 01.2)
1. **Deploy AI Lab**: `./scripts/lab-01.2-deploy-product-description-ai-agent.sh`
2. **Generate Descriptions**: Use AI to create product descriptions
3. **Usage Tracking**: Monitor token consumption and costs
4. **Tenant Isolation**: Verify AI requests are tenant-scoped

### Key Learning Objectives

**Multi-Tenant SaaS Patterns:**
- Tenant isolation strategies
- Tier-based resource allocation
- Event-driven provisioning
- Cost optimization techniques

**AWS Serverless Architecture:**
- Lambda-based microservices
- API Gateway with custom authorizers
- DynamoDB with tenant partitioning
- EventBridge for decoupled communication

**AI Integration:**
- Amazon Bedrock agent integration
- Usage tracking and cost monitoring
- Tenant-aware AI services
- Streaming response processing

## Troubleshooting

### Common Issues

**Deployment Failures:**
```bash
# Check CDK bootstrap status
cdk bootstrap

# Verify AWS credentials
aws sts get-caller-identity

# Check region support
aws ec2 describe-regions --region <region_name>
```

**Permission Errors:**
- Ensure IAM user/role has CloudFormation permissions
- Verify Bedrock access for AI labs
- Check S3 bucket creation permissions

**Region-Specific Issues:**
- Bedrock not available: Choose supported region
- Service limits: Check AWS service quotas
- Model access: Request Bedrock model access if needed

### Debugging Resources

**CloudWatch Logs:**
- Control Plane: `/aws/lambda/AgenticInsightsControlPlane-*`
- Application Plane: `/aws/lambda/AgenticInsightsAppPlane-*`
- AI Services: `/aws/lambda/AgenticInsightsAIDescription-*`

**Useful Commands:**
```bash
# Check stack status
aws cloudformation describe-stacks --stack-name AgenticInsightsControlPlane

# View recent logs
aws logs describe-log-groups --log-group-name-prefix "/aws/lambda/AgenticInsights"

# Test API endpoints
curl -X GET https://your-api-gateway-url/prod/tenants
```

## Cleanup

### Remove All Resources
```bash
./scripts/delete-all.sh
```

**What gets removed:**
- All CloudFormation stacks
- S3 buckets (after emptying)
- DynamoDB tables (including Premium tenant tables)
- Cognito user pools
- CloudFront distributions

**Note:** Cleanup is region-specific. Run in each region where you deployed.

## Architecture Deep Dive

### Control Plane vs Application Plane

**Control Plane (Shared):**
- Tenant registration and provisioning
- Authentication and authorization
- Platform-wide tenant management
- EventBridge-driven workflows

**Application Plane (Tenant-Aware):**
- Product and order management
- User management within tenants
- Tier-specific resource routing
- Business logic execution

### Tenant Isolation Strategy

**Data Level:**
- All DynamoDB operations filter by `tenant_id`
- Premium tenants get dedicated Order tables
- Shared tables use tenant_id as partition key

**API Level:**
- Lambda authorizer extracts tenant context from JWT
- All requests include tenant_id in headers
- Cross-tenant access prevention at application layer

**Resource Level:**
- Basic: Shared Lambda + Shared DynamoDB + Shared Cognito
- Premium: Shared Lambda + Dedicated Order DDB + Shared Cognito

### Event-Driven Architecture

**Tenant Provisioning Flow:**
1. Registration service publishes `tenant.created` event
2. Tenant provisioning service creates tier-specific resources
3. User creation service creates admin in appropriate Cognito pool
4. Tenant status updated to `active`

**Benefits:**
- Decoupled microservices
- Reliable resource provisioning
- Scalable tenant onboarding
- Error handling and retries

## Next Steps

After completing the workshop:

1. **Explore Code**: Review the complete source code structure
2. **Customize Features**: Modify the platform for your use cases
3. **Add Monitoring**: Implement comprehensive observability
4. **Security Hardening**: Add production-ready security measures
5. **Scale Testing**: Test with multiple tenants and high load

## Support

For workshop support:
- **Architecture Guide**: See `ARCHITECTURE.md` for detailed system design
- **API Documentation**: All endpoints documented in architecture guide
- **Source Code**: Complete implementation available in `src/` directory
- **Frontend Code**: Web applications in `web/` directory

This workshop provides a comprehensive foundation for building production-ready multi-tenant SaaS applications on AWS.
