#!/bin/bash

# Lab 4.0: Deploy Churn Agent Infrastructure and Configure
# This script deploys the CDK stack, configures AgentCore, and calls the launch script
# Usage: ./lab4.0-deploy-churn-agent.sh

set -e  # Exit on any error

echo "🚀 Lab 4.0: Deploying Churn Agent Infrastructure..."
echo "=================================================="

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

# Get absolute paths
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Deploy CDK stack
print_status "Deploying Churn Agent CDK stack..."
cd "$PROJECT_ROOT"
npx cdk deploy AgenticInsightsChurnAgent --require-approval never

# Get stack outputs
print_status "Retrieving stack outputs..."
STACK_OUTPUTS=$(aws cloudformation describe-stacks --stack-name AgenticInsightsChurnAgent --region $REGION --query 'Stacks[0].Outputs' --output json)

# Extract values from outputs
BEDROCK_ROLE_ARN=$(echo $STACK_OUTPUTS | jq -r '.[] | select(.OutputKey=="BedrockAgentRoleArn") | .OutputValue')

# Get App Plane outputs for Admin Panel
APP_PLANE_OUTPUTS=$(aws cloudformation describe-stacks --stack-name AgenticInsightsAppPlane --region $REGION --query 'Stacks[0].Outputs' --output json)
ADMIN_PANEL_URL=$(echo $APP_PLANE_OUTPUTS | jq -r '.[] | select(.OutputKey=="AdminPanelUrl") | .OutputValue')
ADMIN_PANEL_BUCKET=$(aws cloudformation describe-stack-resources --stack-name AgenticInsightsAppPlane --query "StackResources[?LogicalResourceId=='AdminPanelBucket974362C9'].PhysicalResourceId" --output text)

if [ -z "$ADMIN_PANEL_BUCKET" ]; then
    print_error "Could not find Admin Panel bucket. Please check if AgenticInsightsAppPlane stack exists."
    exit 1
fi



# Get Control Plane outputs for admin user pool
CONTROL_OUTPUTS=$(aws cloudformation describe-stacks --stack-name AgenticInsightsControlPlane --region $REGION --query 'Stacks[0].Outputs' --output json)
ADMIN_USER_POOL_ID=$(echo $CONTROL_OUTPUTS | jq -r '.[] | select(.OutputKey=="AdminUserPoolId") | .OutputValue')
CONTROL_PLANE_API_URL=$(echo $CONTROL_OUTPUTS | jq -r '.[] | select(.OutputKey=="ControlPlaneApiUrl") | .OutputValue')

print_status "Stack outputs retrieved successfully"

# Setup AgentCore CLI and configure
print_status "Setting up AgentCore CLI..."
cd "$PROJECT_ROOT/src/control-plane/agents/churn-agent"

# Install AgentCore CLI toolkit
pip install bedrock-agentcore-starter-toolkit pyyaml

print_status "Configuring churn agent for deployment..."

# Configure the agent with AgentCore CLI using our IAM role and OAuth
DISCOVERY_URL="https://cognito-idp.$REGION.amazonaws.com/$ADMIN_USER_POOL_ID/.well-known/openid-configuration"
CLIENT_ID=$(aws cognito-idp list-user-pool-clients --user-pool-id $ADMIN_USER_POOL_ID --query 'UserPoolClients[0].ClientId' --output text --region $REGION)

# Pre-create S3 bucket for AgentCore deployment
print_status "Preparing S3 bucket for AgentCore deployment..."
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
AGENTCORE_BUCKET="bedrock-agentcore-codebuild-sources-$ACCOUNT_ID-$REGION"

if aws s3api head-bucket --bucket "$AGENTCORE_BUCKET" 2>/dev/null; then
    print_status "S3 bucket already exists: $AGENTCORE_BUCKET"
else
    print_status "Creating S3 bucket: $AGENTCORE_BUCKET"
    if [ "$REGION" = "us-east-1" ]; then
        aws s3api create-bucket --bucket "$AGENTCORE_BUCKET" --region "$REGION"
    else
        aws s3api create-bucket --bucket "$AGENTCORE_BUCKET" --region "$REGION" \
            --create-bucket-configuration LocationConstraint="$REGION"
    fi
    print_success "S3 bucket created successfully: $AGENTCORE_BUCKET"
fi

# Verify installation and add to PATH
export PATH="$HOME/.local/bin:$PATH"

if ! command -v agentcore &> /dev/null; then
    print_error "agentcore command not found after installation"
    exit 1
fi

print_success "agentcore CLI is ready"

agentcore configure \
    --entrypoint main.py \
    --s3 $AGENTCORE_BUCKET \
    --region $REGION \
    --execution-role "$BEDROCK_ROLE_ARN" \
    --name "churn_agent" \
    --authorizer-config "{\"customJWTAuthorizer\":{\"discoveryUrl\":\"$DISCOVERY_URL\",\"allowedClients\":[\"$CLIENT_ID\"]}}" \
    --non-interactive || true

print_success "AgentCore configured successfully"

# Launch churn agent
print_status "Launching churn agent..."
cd "$PROJECT_ROOT"

set +e
LAUNCH_OUTPUT=$("$SCRIPT_DIR/lab4.1-launch-churn-agent.sh" 2>&1)
set -e

echo "$LAUNCH_OUTPUT"

AGENT_ARN=$(echo "$LAUNCH_OUTPUT" | grep -o 'arn:aws:bedrock-agentcore:[^[:space:]]*' | head -1)

if [ -z "$AGENT_ARN" ]; then
    print_error "Failed to extract Agent ARN from launch output"
    exit 1
fi

# Update frontend environment files
print_status "Updating frontend environment files..."

mkdir -p "$PROJECT_ROOT/web/admin-panel"

cat > "$PROJECT_ROOT/web/admin-panel/.env" << EOF
VITE_REGION=$REGION
VITE_CONTROL_PLANE_API_URL=$CONTROL_PLANE_API_URL
VITE_CHURN_AGENT_ARN=$AGENT_ARN
EOF

print_success "Environment file updated"

# Redeploy Admin Panel with updated environment
print_status "Redeploying Admin Panel with Churn Agent configuration..."
cd "$PROJECT_ROOT/web/admin-panel"

npm install
npm run build
aws s3 sync dist/ s3://$ADMIN_PANEL_BUCKET --delete --region $REGION

print_success "Admin Panel redeployed successfully"

# Display deployment summary
echo ""
echo "🎉 Lab 4.0 Deployment Complete!"
echo "================================"
echo ""
echo "📊 Churn Agent Resources:"
echo "  • AgentCore Runtime ARN: $AGENT_ARN"
echo "  • Admin Panel URL: $ADMIN_PANEL_URL"
echo "✅ Next Steps:"
echo "  1. Access the churn agent UI at: $ADMIN_PANEL_URL"
echo "  2. Use your admin credentials to authenticate"
echo "  3. Start analyzing customer churn patterns"
echo ""

print_success "Lab 4.0 deployment complete!"
