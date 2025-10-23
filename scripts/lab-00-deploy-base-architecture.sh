#!/bin/bash

# Lab 00: Deploy Complete Base Architecture with AI
# This script deploys the foundational multi-tenant e-commerce SaaS platform with AI features
# Usage: ./lab-00-deploy-base-architecture.sh

set -e  # Exit on any error

echo "🚀 Lab 00: Deploying Complete Base Architecture with AI..."
echo "========================================================"

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

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    print_error "AWS CLI is not installed. Please install it first."
    exit 1
fi

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    print_error "Node.js is not installed. Please install it first."
    exit 1
fi

# Check if npm is installed
if ! command -v npm &> /dev/null; then
    print_error "npm is not installed. Please install it first."
    exit 1
fi

# Check if CDK is installed
if ! command -v cdk &> /dev/null; then
    print_error "AWS CDK is not installed. Installing it now..."
    npm install -g aws-cdk
fi

# Check if jq is installed (needed for JSON parsing)
if ! command -v jq &> /dev/null; then
    print_error "jq is not installed. Please install it first:"
    echo "  macOS: brew install jq"
    echo "  Ubuntu/Debian: sudo apt-get install jq"
    echo "  Amazon Linux: sudo yum install jq"
    exit 1
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
    print_error "AWS region is not set. Please configure your AWS region:"
    echo "  aws configure set region <region_name>"
    echo "  or export AWS_DEFAULT_REGION=<region_name>"
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

# Bootstrap CDK (if needed)
print_status "Bootstrapping CDK environment..."
cdk bootstrap aws://$AWS_ACCOUNT/$AWS_REGION

# Deploy the stacks
print_status "Deploying Control Plane Stack..."
if ! cdk deploy AgenticInsightsControlPlane --require-approval never; then
    print_error "Control Plane deployment failed"
    exit 1
fi

print_status "Deploying Application Plane Stack (with AI)..."
if ! cdk deploy AgenticInsightsAppPlane --require-approval never; then
    print_error "Application Plane deployment failed"
    exit 1
fi

# Get stack outputs efficiently
print_status "Retrieving deployment outputs..."

# Get Control Plane outputs
CONTROL_PLANE_OUTPUTS=$(aws cloudformation describe-stacks \
    --stack-name AgenticInsightsControlPlane \
    --query 'Stacks[0].Outputs' \
    --output json 2>/dev/null || echo "[]")

CONTROL_PLANE_API=$(echo "$CONTROL_PLANE_OUTPUTS" | jq -r '.[] | select(.OutputKey=="ControlPlaneApiUrl") | .OutputValue' 2>/dev/null || echo "")
CONTROL_PLANE_API=${CONTROL_PLANE_API%/}

# Get App Plane outputs in single call
APP_PLANE_OUTPUTS=$(aws cloudformation describe-stacks \
    --stack-name AgenticInsightsAppPlane \
    --query 'Stacks[0].Outputs' \
    --output json 2>/dev/null || echo "[]")

APP_PLANE_API=$(echo "$APP_PLANE_OUTPUTS" | jq -r '.[] | select(.OutputKey=="AppPlaneApiUrl") | .OutputValue' 2>/dev/null || echo "")
APP_PLANE_API=${APP_PLANE_API%/}

LANDING_PAGE_URL=$(echo "$APP_PLANE_OUTPUTS" | jq -r '.[] | select(.OutputKey=="LandingPageUrl") | .OutputValue' 2>/dev/null || echo "")
ADMIN_PANEL_URL=$(echo "$APP_PLANE_OUTPUTS" | jq -r '.[] | select(.OutputKey=="AdminPanelUrl") | .OutputValue' 2>/dev/null || echo "")
SAAS_APP_URL=$(echo "$APP_PLANE_OUTPUTS" | jq -r '.[] | select(.OutputKey=="SaasAppUrl") | .OutputValue' 2>/dev/null || echo "")
AI_ENDPOINT=$(echo "$APP_PLANE_OUTPUTS" | jq -r '.[] | select(.OutputKey=="AIDescriptionEndpoint") | .OutputValue' 2>/dev/null || echo "")

# Add https:// prefix where needed
[ -n "$LANDING_PAGE_URL" ] && [[ ! "$LANDING_PAGE_URL" =~ ^https?:// ]] && LANDING_PAGE_URL="https://$LANDING_PAGE_URL"
[ -n "$ADMIN_PANEL_URL" ] && [[ ! "$ADMIN_PANEL_URL" =~ ^https?:// ]] && ADMIN_PANEL_URL="https://$ADMIN_PANEL_URL"

# Validate critical outputs
if [ -z "$CONTROL_PLANE_API" ] || [ -z "$APP_PLANE_API" ]; then
    print_error "Failed to retrieve critical API endpoints from CloudFormation"
    print_warning "Control Plane API: ${CONTROL_PLANE_API:-'NOT FOUND'}"
    print_warning "App Plane API: ${APP_PLANE_API:-'NOT FOUND'}"
    exit 1
fi

print_success "Successfully retrieved all deployment outputs"

# Generate web application configuration files
generate_web_configs() {
    print_status "Generating configuration files..."
    
    # Generate config content
    local config_content="// Auto-generated configuration file
// This file is generated during deployment and should not be edited manually
window.APP_CONFIG = {
    CONTROL_PLANE_API_URL: '$CONTROL_PLANE_API',
    APP_PLANE_API_URL: '$APP_PLANE_API',
    SAAS_APP_URL: '$SAAS_APP_URL',
    ADMIN_PANEL_URL: '$ADMIN_PANEL_URL',
    LANDING_PAGE_URL: '$LANDING_PAGE_URL',
    REGION: '$AWS_REGION'
};"
    
    # Write to each web application
    echo "$config_content" > web/admin-panel/config.js
    echo "$config_content" > web/saas-app/config.js
    echo "$config_content" > web/landing-page/config.js
}

# Generate web application configuration files
print_status "Generating web application configuration files..."
generate_web_configs
print_success "Configuration files generated for all web applications"

# Redeploy App Plane to update CloudFront with correct config files
print_status "Redeploying Application Plane Stack (with config files)..."
if ! cdk deploy AgenticInsightsAppPlane --require-approval never; then
    print_error "Application Plane redeployment failed"
    exit 1
fi

# Display deployment summary
echo
echo "📋 Deployment Summary:"
echo "----------------------"
echo "AWS Account: $AWS_ACCOUNT"
echo "AWS Region: $AWS_REGION"
echo
echo "🧪 Use the following command for Testing AI product description Agent:"
echo "curl -X POST $APP_PLANE_API/ai/generate-description \\"
echo "  -H 'Authorization: Bearer <your-jwt-token>' \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -H 'tenant-id: <your-tenant-id>' \\"
# Create default admin user
echo
echo "🔐 Creating Default Admin User..."
echo "================================"
./scripts/utils/create-saas-admin-user.sh --auto "admin@example.com" "Admin123!"

echo
echo "📋 Deployment Summary:"
echo "----------------------"
echo "AWS Account: $(aws sts get-caller-identity --query Account --output text 2>/dev/null || echo 'Unknown')"
echo "AWS Region: $AWS_REGION"
echo
echo "🔗 Application URLs:"
if [ -n "$LANDING_PAGE_URL" ]; then
    echo "Landing Page: $LANDING_PAGE_URL"
fi
if [ -n "$SAAS_APP_URL" ]; then
    echo "SaaS Application: $SAAS_APP_URL"
fi
if [ -n "$ADMIN_PANEL_URL" ]; then
    echo "Admin Panel: $ADMIN_PANEL_URL | Admin User : admin@example.com | Password : Admin123!"
fi

echo
echo "=================================================="
print_success "🎉 Deployment completed successfully!"
echo "=================================================="
