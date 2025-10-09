#!/bin/bash

# Lab 02.1: Deploy Metering Framework
# This script deploys comprehensive tenant-specific metrics collection framework
# Usage: ./lab-02.1-metering-framework.sh

set -e  # Exit on any error

echo "📊 Lab 02.1: Deploying Metering Framework..."
echo "============================================"

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

# Check if base architecture is deployed
if ! aws cloudformation describe-stacks --stack-name AgenticInsightsControlPlane &> /dev/null; then
    print_error "Base architecture not found. Please run lab-01.1-deploy-base-architecture.sh first."
    exit 1
fi

if ! aws cloudformation describe-stacks --stack-name AgenticInsightsAppPlane &> /dev/null; then
    print_error "Application plane not found. Please run lab-01.1-deploy-base-architecture.sh first."
    exit 1
fi

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    print_error "AWS CLI is not installed. Please install it first."
    exit 1
fi

# Check if CDK is installed
if ! command -v cdk &> /dev/null; then
    print_error "AWS CDK is not installed. Installing it now..."
    npm install -g aws-cdk
fi

# Check AWS credentials
if ! aws sts get-caller-identity &> /dev/null; then
    print_error "AWS credentials not configured. Please run 'aws configure' first."
    exit 1
fi

print_success "Prerequisites check completed"

# Get AWS account and region
AWS_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION=$(aws configure get region)

if [ -z "$AWS_REGION" ]; then
    print_error "AWS region is not set. Please configure your AWS region."
    exit 1
fi

print_status "Deploying to AWS Account: $AWS_ACCOUNT in Region: $AWS_REGION"

# Navigate to project root
cd "$(dirname "$0")/.."

# Install dependencies
print_status "Installing dependencies..."
npm install

# Build TypeScript
print_status "Building TypeScript code..."
npm run build

print_status "Phase 1: Deploying Metrics Framework Stack..."
cdk deploy AgenticInsightsMetricsFramework --require-approval never

print_status "Phase 2: Updating Application Services with Metrics Collection..."
cdk deploy AgenticInsightsAppPlane --require-approval never

# Get deployment outputs
print_status "Retrieving deployment outputs..."

CONTROL_PLANE_API=$(aws cloudformation describe-stacks \
    --stack-name AgenticInsightsControlPlane \
    --query 'Stacks[0].Outputs[?OutputKey==`ControlPlaneApiUrl`].OutputValue' \
    --output text 2>/dev/null || echo "")

APP_PLANE_API=$(aws cloudformation describe-stacks \
    --stack-name AgenticInsightsAppPlane \
    --query 'Stacks[0].Outputs[?OutputKey==`AppPlaneApiUrl`].OutputValue' \
    --output text 2>/dev/null || echo "")

ADMIN_PANEL_URL=$(aws cloudformation describe-stacks \
    --stack-name AgenticInsightsAppPlane \
    --query 'Stacks[0].Outputs[?OutputKey==`AdminPanelUrl`].OutputValue' \
    --output text 2>/dev/null || echo "")

SAAS_APP_URL=$(aws cloudformation describe-stacks \
    --stack-name AgenticInsightsAppPlane \
    --query 'Stacks[0].Outputs[?OutputKey==`SaasAppUrl`].OutputValue' \
    --output text 2>/dev/null || echo "")

LANDING_PAGE_URL=$(aws cloudformation describe-stacks \
    --stack-name AgenticInsightsAppPlane \
    --query 'Stacks[0].Outputs[?OutputKey==`LandingPageUrl`].OutputValue' \
    --output text 2>/dev/null || echo "")

# Update admin panel configuration
if [ -n "$CONTROL_PLANE_API" ] && [ -n "$APP_PLANE_API" ]; then
    print_status "Updating admin panel configuration..."
    
    # Remove trailing slashes
    CONTROL_PLANE_API=${CONTROL_PLANE_API%/}
    APP_PLANE_API=${APP_PLANE_API%/}
    
    # Generate updated config content
    config_content="// Auto-generated configuration file
// This file is generated during deployment and should not be edited manually
window.APP_CONFIG = {
    CONTROL_PLANE_API_URL: '$CONTROL_PLANE_API',
    APP_PLANE_API_URL: '$APP_PLANE_API',
    SAAS_APP_URL: '$SAAS_APP_URL',
    ADMIN_PANEL_URL: '$ADMIN_PANEL_URL',
    LANDING_PAGE_URL: '$LANDING_PAGE_URL',
    INSIGHT_DASHBOARD_API_URL: '${CONTROL_PLANE_API}/insight-dashboard',
    REGION: '$AWS_REGION'
};"
    
    # Update admin panel config
    echo "$config_content" > web/admin-panel/config.js
    
    # Deploy updated admin panel
    print_status "Deploying updated admin panel..."
    cdk deploy AgenticInsightsAppPlane --require-approval never
    
    print_success "Admin panel configuration updated"
fi

# Display deployment summary
echo
echo "============================================"
print_success "🎉 Metering Framework deployed successfully!"
echo "============================================"
echo
echo "📋 Deployment Summary:"
echo "----------------------"
echo "AWS Account: $AWS_ACCOUNT"
echo "AWS Region: $AWS_REGION"
echo
echo "🔗 Application URLs:"
if [ -n "$ADMIN_PANEL_URL" ]; then
    echo "Admin Panel: $ADMIN_PANEL_URL"
fi
if [ -n "$SAAS_APP_URL" ]; then
    echo "SaaS App: $SAAS_APP_URL"
fi
if [ -n "$LANDING_PAGE_URL" ]; then
    echo "Landing Page: $LANDING_PAGE_URL"
fi
echo
echo "🔧 API Endpoints:"
if [ -n "$CONTROL_PLANE_API" ]; then
    echo "Control Plane API: $CONTROL_PLANE_API"
fi
if [ -n "$APP_PLANE_API" ]; then
    echo "Application Plane API: $APP_PLANE_API"
fi
echo
echo "📊 Features Deployed:"
echo "• Enhanced Metrics Collection Library (Lambda Layer)"
echo "• Event-Driven Metrics Pipeline (EventBridge)"
echo "• Metrics Aggregation Service (DynamoDB Streams)"
echo "• Cost Per Tenant Tracking (90-day retention)"
echo "• Real-time Metrics Collection from Tenant Activities"
echo
echo "📚 Next Steps:"
echo "1. Deploy Cost Analysis Agent: ./scripts/lab-02.2-deploy-cost-analysis-agent.sh"
echo "2. Visit the Admin Panel: $ADMIN_PANEL_URL"
echo "3. Monitor metrics collection in CloudWatch"
echo
echo "🗑️  To remove everything, run: ./scripts/delete-all.sh"
echo "============================================"
