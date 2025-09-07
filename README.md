# Agentic Insights - Multi-Tenant E-commerce SaaS Platform

A comprehensive multi-tenant e-commerce SaaS platform built with AWS serverless technologies, designed as a reference solution for AWS workshops. The platform enables vendors (tenants) to self-provision through a landing page with tier-based deployment strategies.

## 🏗️ Architecture Overview

The solution follows a **Control Plane** and **Application Plane** architecture with **AI-powered features**:

- **Control Plane**: Handles tenant registration, authentication, and provisioning
- **Application Plane**: Provides e-commerce functionality (products, orders, users)
- **AI Description Agent**: Generates compelling product descriptions using Amazon Bedrock
- **3 Web Applications**: Landing page, admin panel, and tenant SaaS app

### Tier-Based Resource Strategy

**Basic Tier ($29/month)**:
- Shared Lambda functions and DynamoDB tables
- Shared Cognito User Pool for all Basic tenants
- Cost-optimized through resource sharing

**Premium Tier ($99/month)**:
- Shared Lambda functions but dedicated DynamoDB table for orders
- Shared Cognito User Pool for all Premium tenants
- Better isolation while maintaining cost efficiency

## 🚀 Quick Start

### Prerequisites

- AWS CLI configured with appropriate permissions
- Node.js (v18 or later)
- npm or yarn
- AWS CDK CLI (`npm install -g aws-cdk`)

### Deployment

#### Default Deployment (us-east-1)

1. **Clone and setup**:
   ```bash
   git clone <repository-url>
   cd agentic-insights-saas
   npm install
   ```

2. **Deploy to AWS**:
   ```bash
   ./scripts/deploy.sh
   ```

3. **Deploy AI Product Description Agent** (Optional):
   ```bash
   ./scripts/deploy-ai-desc-agent.sh
   ```

#### Smart Configuration Management

The deployment script automatically generates and manages configuration files for all web applications:

**Automatic Configuration**:
- ✅ **Auto-generated config** - API URLs and CloudFront URLs automatically populated
- ✅ **Change detection** - Only redeploys web apps when URLs actually change
- ✅ **Region-agnostic** - Works seamlessly across all AWS regions
- ✅ **Single source of truth** - All configuration centralized in `web/shared/config.js`

**Deployment Options**:
```bash
# Normal deployment - only redeploys web apps if configuration changed
./scripts/deploy.sh

# Force deployment - always redeploys web apps (useful for testing)
./scripts/deploy.sh --force
```

**Configuration Structure**:
```javascript
// Auto-generated web/shared/config.js
window.APP_CONFIG = {
    CONTROL_PLANE_API_URL: 'https://api-id.execute-api.region.amazonaws.com/prod',
    APP_PLANE_API_URL: 'https://api-id.execute-api.region.amazonaws.com/prod',
    SAAS_APP_URL: 'https://cloudfront-id.cloudfront.net',
    ADMIN_PANEL_URL: 'https://cloudfront-id.cloudfront.net',
    LANDING_PAGE_URL: 'https://cloudfront-id.cloudfront.net',
    REGION: 'us-east-2'
};
```

**Benefits**:
- 🚀 **Faster deployments** - Skips unnecessary web app redeployments
- 🔧 **No manual updates** - Configuration automatically synced with infrastructure
- 🌍 **Multi-region ready** - Deploy to any region without code changes
- ⚡ **Efficient caching** - CloudFront cache only invalidated when needed

#### Deployment to Different AWS Region

To deploy the solution to a different AWS region (e.g., us-east-2, eu-west-1):

1. **Set target region**:
   ```bash
   export AWS_DEFAULT_REGION=us-east-2
   export CDK_DEFAULT_REGION=us-east-2
   
   # Or update AWS CLI configuration
   aws configure set region us-east-2
   ```

2. **Update Bedrock model configuration** (if deploying AI agent):
   ```bash
   # Edit src/app-plane/agents/product-desc/agent-config.yaml
   # Change model ID format based on region:
   
   # For us-east-1: us.anthropic.claude-3-haiku-20240307-v1:0
   # For other regions: anthropic.claude-3-haiku-20240307-v1:0
   ```

3. **Verify Bedrock model availability**:
   ```bash
   # Check if Claude 3 Haiku is available in target region
   aws bedrock list-foundation-models --region us-east-2 \
     --query 'modelSummaries[?contains(modelId, `claude-3-haiku`)]'
   ```

4. **Deploy to new region**:
   ```bash
   ./scripts/deploy.sh
   ```

#### Region-Specific Considerations

- **Bedrock Availability**: Ensure Claude 3 Haiku is available in your target region
- **Model ID Format**: Some regions use different model ID formats (with/without region prefix)
- **Service Availability**: All core AWS services (Lambda, DynamoDB, API Gateway, EventBridge, S3, CloudFront) are available in all major regions
- **Frontend URLs**: The deployment script automatically updates frontend configurations with new region-specific API Gateway URLs

#### Access Applications

After successful deployment:
- **Landing Page**: For tenant registration
- **Admin Panel**: For platform management  
- **SaaS App**: For tenant e-commerce operations

URLs will be displayed in the deployment output and are region-specific.

### Cleanup

To remove all resources:
```bash
./scripts/delete-all.sh
```

## 📁 Project Structure

```
agentic-insights-saas/
├── infra/                          # CDK Infrastructure (TypeScript)
│   ├── main.ts                     # CDK app entry point
│   ├── control-plane-stack.ts      # Control plane resources
│   ├── app-plane-stack.ts          # Application plane resources
│   └── ai-description-stack.ts     # AI product description agent
├── src/                            # Lambda Functions (Python)
│   ├── control-plane/              # Control plane services
│   │   ├── registration/           # Tenant registration
│   │   ├── login/                  # Authentication
│   │   ├── tenant-management/      # Tenant CRUD
│   │   └── tenant-provisioning/    # Resource provisioning
│   └── app-plane/                  # Application plane services
│       ├── authorizer/             # JWT validation
│       ├── product/                # Product management
│       ├── product-desc/           # AI description generation
│       ├── order/                  # Order processing
│       ├── user/                   # User management
│       └── user-creation/          # EventBridge user creation
├── web/                            # Frontend Applications
│   ├── shared/                     # Shared configuration
│   │   ├── config.template.js      # Configuration template
│   │   └── config.js               # Auto-generated config (deployment)
│   ├── landing-page/               # Tenant registration
│   ├── admin-panel/                # Platform management
│   └── saas-app/                   # E-commerce application
├── scripts/                        # Deployment scripts
│   ├── deploy.sh                   # Full deployment
│   └── delete-all.sh               # Complete cleanup
└── specs/                          # Documentation
    ├── requirements.md             # Detailed requirements
    ├── design.md                   # Technical design
    └── tasks.md                    # Implementation plan
```

## 🔧 Key Features

### Multi-Tenant Architecture
- Complete data isolation using tenant_id filtering
- Tier-based resource allocation (Basic vs Premium)
- EventBridge-driven tenant provisioning and user creation

### E-commerce Functionality
- **Product Management**: Create, read, update, delete products
- **AI Product Descriptions**: Generate compelling descriptions using Amazon Bedrock
- **Shopping Cart**: Multi-product cart with real-time totals and visual indicators
- **Order Processing**: Multi-product order creation with success notifications
- **User Management**: Role-based access control with self-deletion prevention

### Modern Web Applications
- **Landing Page**: Tier selection and self-registration with form validation
- **Admin Panel**: Tenant management dashboard with statistics and insights
- **SaaS App**: Full e-commerce functionality with modular JavaScript architecture

### Security & Authentication
- JWT-based authentication with Cognito and token expiration handling
- Lambda authorizer for API protection
- Role-based access control (tenant_admin vs tenant_user)
- Cross-tenant access prevention with comprehensive input validation

### Enhanced User Experience
- **Responsive Design**: Mobile-optimized layouts with modern CSS animations
- **Real-time Updates**: Live cart totals and loading states for all operations
- **Error Handling**: Comprehensive validation with user-friendly error messages
- **Success Feedback**: Visual confirmations and auto-dismiss notifications

### Operational Excellence
- **Automated Deployment**: One-command deployment with configuration updates
- **Smart Configuration Management**: Auto-generated config files with change detection
- **Efficient Deployments**: Only redeploys web apps when URLs actually change
- **Smart Cleanup**: Comprehensive resource removal with S3 bucket emptying
- **Admin Tools**: Dashboard statistics and tenant management interface
- **Monitoring Ready**: Structured logging and error tracking

## 🛠️ Technology Stack

### Infrastructure
- **AWS CDK**: Infrastructure as Code (TypeScript)
- **AWS Lambda**: Serverless compute (Python 3.11)
- **Amazon DynamoDB**: NoSQL database
- **Amazon Cognito**: User authentication
- **Amazon EventBridge**: Event-driven architecture
- **Amazon API Gateway**: REST APIs
- **Amazon S3 + CloudFront**: Web hosting
- **Amazon Bedrock**: AI-powered content generation (Claude 3 Haiku)

### Frontend
- **Vanilla JavaScript**: No frameworks, modern ES6+
- **HTML5 + CSS3**: Responsive design
- **Modular Architecture**: Organized JavaScript modules

## 📊 API Endpoints

### Control Plane APIs
- `POST /register` - Tenant self-registration
- `POST /login` - User authentication
- `GET /tenants` - List tenants (admin only)
- `POST /tenants` - Create tenant (admin only)
- `DELETE /tenants/{id}` - Delete tenant (admin only)

### Application Plane APIs

#### Basic Tier
- `GET /basic/products` - List products
- `POST /basic/products` - Create product
- `GET /basic/products/{id}` - Get product details
- `PUT /basic/products/{id}` - Update product
- `DELETE /basic/products/{id}` - Delete product
- `GET /basic/orders` - List orders
- `POST /basic/orders` - Create order

#### Premium Tier
- `GET /premium/products` - List products
- `POST /premium/products` - Create product
- `GET /premium/products/{id}` - Get product details
- `PUT /premium/products/{id}` - Update product
- `DELETE /premium/products/{id}` - Delete product
- `GET /premium/orders` - List orders
- `POST /premium/orders` - Create order

#### Common APIs
- `GET /user` - List tenant users
- `POST /user` - Create tenant user
- `PUT /user/{id}` - Update tenant user
- `DELETE /user/{id}` - Delete tenant user

#### AI-Powered APIs
- `POST /ai/generate-description` - Generate AI product descriptions

## 🔄 Event-Driven Architecture

The platform uses EventBridge for decoupled communication:

1. **Tenant Registration**: Triggers provisioning events
2. **User Creation**: EventBridge-driven user creation in appropriate Cognito pools
3. **Premium Provisioning**: Dynamic DynamoDB table creation for Premium tenants

## ✨ Implementation Enhancements

Beyond the core specifications, this implementation includes several enhancements for production readiness:

### 🎨 **User Experience Improvements**
- **Modular JavaScript Architecture**: Organized into separate files (auth.js, products.js, cart.js, orders.js, users.js) for maintainability
- **Enhanced Admin Dashboard**: Statistics, tenant insights, and visual status indicators
- **Real-time Cart Updates**: Live totals, visual indicators, and smooth animations
- **Comprehensive Loading States**: Progress indicators for all async operations
- **Success Notifications**: Auto-dismissing confirmations with detailed feedback

### 🤖 **AI-Powered Features**
- **Intelligent Content Generation**: One-click AI product description generation using Amazon Bedrock
- **Cost-Effective AI**: Claude 3 Haiku model optimized for speed and cost efficiency
- **Usage Tracking**: Real-time token consumption and cost monitoring per tenant
- **Seamless Integration**: Generate button embedded in product creation/editing forms
- **Professional Quality**: Expert e-commerce copywriter persona for compelling descriptions
- **Structured Logging**: Comprehensive usage analytics in CloudWatch for billing and monitoring

### 🔒 **Security Enhancements**
- **Token Expiration Handling**: Automatic logout on expired sessions
- **Self-Deletion Prevention**: Users cannot delete their own accounts
- **Input Sanitization**: Comprehensive validation at all layers
- **Automatic Session Management**: Seamless token refresh and error handling

### 🚀 **Operational Excellence**
- **Smart Deployment Scripts**: Automatic configuration updates and admin user creation
- **Centralized Configuration**: Auto-generated config files with change detection and region portability
- **Efficient Deployments**: Only redeploys web apps when URLs actually change, with force flag support
- **Intelligent Cleanup**: S3 bucket emptying and premium table cleanup
- **Colored Console Output**: Enhanced deployment feedback with progress indicators
- **Responsive Design**: Mobile-optimized layouts with modern CSS animations

### 🎯 **Developer Experience**
- **Comprehensive Error Messages**: User-friendly validation with specific guidance
- **Retry Mechanisms**: Robust deployment with automatic retries
- **Structured Logging**: CloudWatch integration with tenant context
- **Professional UI/UX**: Modern gradients, hover effects, and smooth transitions

All enhancements maintain full compatibility with the original specifications while providing a production-ready experience.

## 🎯 Usage Scenarios

### For Workshop Participants
1. Deploy the complete solution with one command
2. Explore multi-tenant SaaS patterns
3. Understand tier-based resource allocation
4. Learn EventBridge-driven architecture
5. Clean up everything with one command

### For Developers
1. Reference implementation for multi-tenant SaaS
2. Modern serverless architecture patterns
3. Cost optimization strategies
4. Security best practices
5. Event-driven microservices

## 🔐 Security Features

- **JWT Authentication**: Secure token-based authentication
- **Tenant Isolation**: Complete data separation
- **Role-Based Access**: Admin vs user permissions
- **API Authorization**: Lambda authorizer protection
- **Input Validation**: Comprehensive validation at all layers

## 📈 Monitoring & Observability

- **CloudWatch Logs**: All Lambda functions log structured data
- **X-Ray Tracing**: End-to-end request tracing
- **EventBridge Monitoring**: Event processing metrics
- **API Gateway Metrics**: Request/response monitoring

## 🧪 Testing

The solution includes comprehensive testing strategies:
- **Unit Testing**: Python Lambda functions with pytest
- **Integration Testing**: API Gateway endpoints
- **End-to-End Testing**: Complete user workflows
- **Multi-Tenant Testing**: Data isolation verification

## 🤝 Contributing

This is a reference implementation for AWS workshops. For improvements:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For issues and questions:
1. Check the documentation in the `specs/` folder
2. Review the CloudFormation outputs after deployment
3. Check CloudWatch logs for debugging
4. Ensure AWS permissions are correctly configured

## 🎉 Acknowledgments

Built as a reference solution for AWS workshops, demonstrating:
- Modern serverless architecture patterns
- Multi-tenant SaaS best practices
- Cost optimization strategies
- Event-driven design principles
- Security and compliance considerations

---

**Happy Building! 🚀**
