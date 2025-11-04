#!/bin/bash

# Lab 4: Deploy Churn Agent with AgentCore Runtime
# This script deploys the churn prediction agent using Bedrock AgentCore Runtime
# Usage: ./lab4-deploy-churn-agent.sh

set -e  # Exit on any error

echo "🚀 Lab 4: Deploying Churn Agent..."
echo "=================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
print_status "Checking prerequisites..."

if ! command -v aws &> /dev/null; then
    print_error "AWS CLI is not installed. Please install it first."
    exit 1
fi

if ! command -v npm &> /dev/null; then
    print_error "npm is not installed. Please install Node.js first."
    exit 1
fi

# Get current region
REGION=$(aws configure get region)
if [ -z "$REGION" ]; then
    print_error "AWS region not configured. Please run 'aws configure' first."
    exit 1
fi

print_status "Using AWS region: $REGION"

# Deploy CDK stack first
print_status "Deploying Churn Agent CDK stack..."
cd "$(dirname "$0")/.."
# npm run build
npx cdk deploy AgenticInsightsChurnAgent --require-approval never

# Get stack outputs
print_status "Retrieving stack outputs..."
STACK_OUTPUTS=$(aws cloudformation describe-stacks --stack-name AgenticInsightsChurnAgent --region $REGION --query 'Stacks[0].Outputs' --output json)

# Extract values from outputs
BEDROCK_ROLE_ARN=$(echo $STACK_OUTPUTS | jq -r '.[] | select(.OutputKey=="BedrockAgentRoleArn") | .OutputValue')
DSQL_CLUSTER_ID=$(echo $STACK_OUTPUTS | jq -r '.[] | select(.OutputKey=="DSQLClusterId") | .OutputValue')
DSQL_ENDPOINT=$(echo $STACK_OUTPUTS | jq -r '.[] | select(.OutputKey=="DSQLEndpoint") | .OutputValue')
S3_BUCKET=$(echo $STACK_OUTPUTS | jq -r '.[] | select(.OutputKey=="ReactAppBucketName") | .OutputValue')
CLOUDFRONT_URL=$(echo $STACK_OUTPUTS | jq -r '.[] | select(.OutputKey=="CloudFrontDistributionUrl") | .OutputValue')

# Get Control Plane outputs for admin user pool
CONTROL_OUTPUTS=$(aws cloudformation describe-stacks --stack-name AgenticInsightsControlPlane --region $REGION --query 'Stacks[0].Outputs' --output json)
ADMIN_USER_POOL_ID=$(echo $CONTROL_OUTPUTS | jq -r '.[] | select(.OutputKey=="AdminUserPoolId") | .OutputValue')
CONTROL_PLANE_API_URL=$(echo $CONTROL_OUTPUTS | jq -r '.[] | select(.OutputKey=="ControlPlaneApiUrl") | .OutputValue')

print_status "Stack outputs retrieved successfully"

# Create AgentCore Runtime using AgentCore CLI
print_status "Setting up virtual environment and installing AgentCore CLI..."
cd src/control-plane/agents/churn-agent

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install AgentCore CLI toolkit
pip install --upgrade pip
pip install bedrock-agentcore-starter-toolkit pyyaml

print_status "Configuring churn agent for deployment..."

# Configure the agent with AgentCore CLI using our IAM role and OAuth
DISCOVERY_URL="https://cognito-idp.$REGION.amazonaws.com/$ADMIN_USER_POOL_ID/.well-known/openid-configuration"
CLIENT_ID=$(aws cognito-idp list-user-pool-clients --user-pool-id $ADMIN_USER_POOL_ID --query 'UserPoolClients[0].ClientId' --output text --region $REGION)

agentcore configure \
    --entrypoint main.py \
    --region $REGION \
    --execution-role "$BEDROCK_ROLE_ARN" \
    --name "churn_agent" \
    --authorizer-config "{\"customJWTAuthorizer\":{\"discoveryUrl\":\"$DISCOVERY_URL\",\"allowedClients\":[\"$CLIENT_ID\"]}}" \
    --non-interactive

# Deploy the agent
print_status "Deploying churn agent to AgentCore Runtime..."
LAUNCH_OUTPUT=$(agentcore launch \
    --agent "churn_agent" \
    --env "DSQL_CLUSTER_ID=$DSQL_CLUSTER_ID" \
    --env "DSQL_REGION=$REGION" \
    --env "DSQL_HOST=$DSQL_ENDPOINT" \
    --env "DSQL_PORT=5432" \
    --env "DSQL_DATABASE=postgres" \
    --env "DSQL_USERNAME=admin" \
    2>&1)
echo "$LAUNCH_OUTPUT"

# Extract agent ARN from output
AGENT_ARN=$(echo "$LAUNCH_OUTPUT" | grep -o 'arn:aws:bedrock-agentcore:[^[:space:]]*' | head -1)

if [ -z "$AGENT_ARN" ]; then
    print_error "Failed to extract agent ARN from launch output"
    exit 1
fi

print_success "AgentCore Runtime deployed: $AGENT_ARN"

# Deactivate virtual environment
deactivate

cd - > /dev/null

# Update frontend environment files
print_status "Updating frontend environment files..."

# Update frontend .env file
cat > web/churn-agent-ui/.env << EOF
VITE_REGION=$REGION
VITE_CHURN_AGENT_ARN=$AGENT_ARN
VITE_CONTROL_PLANE_API_URL=$CONTROL_PLANE_API_URL
EOF

print_success "Environment files updated"

# Build and deploy frontend
print_status "Building and deploying React frontend..."
cd web/churn-agent-ui

# Install dependencies and build
npm install
npm run build

# Deploy to S3
print_status "Uploading build to S3 bucket: $S3_BUCKET"
aws s3 sync dist/ s3://$S3_BUCKET --delete --region $REGION

# Invalidate CloudFront cache - NOT NECESSARY BECAUSE WE DON'T CACHE THIS ANYWAY
# DISTRIBUTION_ID=$(echo $CLOUDFRONT_URL | sed 's|https://||' | sed 's|\.cloudfront\.net||')
# print_status "Invalidating CloudFront cache..."
# aws cloudfront create-invalidation --distribution-id $DISTRIBUTION_ID --paths "/*" --region $REGION

print_success "Frontend deployed successfully"

# Display deployment summary
echo ""
echo "🎉 Lab 4 Deployment Complete!"
echo "============================="
echo ""
echo "📊 Churn Agent Resources:"
echo "  • AgentCore Runtime ARN: $AGENT_ARN"
echo "  • DSQL Cluster: $DSQL_CLUSTER_ID"
echo "  • Frontend URL: $CLOUDFRONT_URL"
echo ""
echo "🔧 Environment Configuration:"
echo "  • Region: $REGION"
echo "  • S3 Bucket: $S3_BUCKET"
echo "  • Admin User Pool: $ADMIN_USER_POOL_ID"
echo ""
echo "✅ Next Steps:"
echo "  1. Access the churn agent UI at: $CLOUDFRONT_URL"
echo "  2. Use your admin credentials to authenticate"
echo "  3. Start analyzing customer churn patterns"
echo "  4. Test the agent with: agentcore invoke '{\"prompt\": \"analyze churn\"}'"
echo ""
