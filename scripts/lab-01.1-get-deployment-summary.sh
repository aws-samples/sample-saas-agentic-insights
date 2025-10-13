#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

# Get AWS region and account
AWS_REGION=$(aws configure get region 2>/dev/null || echo "us-east-1")
AWS_ACCOUNT=$(aws sts get-caller-identity --query Account --output text 2>/dev/null || echo "")

# Get CloudFormation outputs
CONTROL_PLANE_API=$(aws cloudformation describe-stacks \
    --stack-name AgenticInsightsControlPlane \
    --query 'Stacks[0].Outputs[?OutputKey==`ControlPlaneApiUrl`].OutputValue' \
    --output text 2>/dev/null || echo "")

APP_PLANE_API=$(aws cloudformation describe-stacks \
    --stack-name AgenticInsightsAppPlane \
    --query 'Stacks[0].Outputs[?OutputKey==`AppPlaneApiUrl`].OutputValue' \
    --output text 2>/dev/null || echo "")

LANDING_PAGE_URL=$(aws cloudformation describe-stacks \
    --stack-name AgenticInsightsAppPlane \
    --query 'Stacks[0].Outputs[?OutputKey==`LandingPageUrl`].OutputValue' \
    --output text 2>/dev/null || echo "")

SAAS_APP_URL=$(aws cloudformation describe-stacks \
    --stack-name AgenticInsightsAppPlane \
    --query 'Stacks[0].Outputs[?OutputKey==`SaasAppUrl`].OutputValue' \
    --output text 2>/dev/null || echo "")

ADMIN_PANEL_URL=$(aws cloudformation describe-stacks \
    --stack-name AgenticInsightsAppPlane \
    --query 'Stacks[0].Outputs[?OutputKey==`AdminPanelUrl`].OutputValue' \
    --output text 2>/dev/null || echo "")

echo "=================================================="
print_success "🎉 Deployment completed successfully!"
echo "=================================================="
echo
echo "📋 Deployment Summary:"
echo "----------------------"
echo "AWS Account: $AWS_ACCOUNT"
echo "AWS Region: $AWS_REGION"
echo
echo "🔗 Application URLs:"
if [ -n "$LANDING_PAGE_URL" ]; then
    echo "Landing Page: $LANDING_PAGE_URL"
fi
if [ -n "$ADMIN_PANEL_URL" ]; then
    echo "Admin Panel: $ADMIN_PANEL_URL"
fi
if [ -n "$SAAS_APP_URL" ]; then
    echo "SaaS Application: $SAAS_APP_URL"
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
print_success "========= 🎉 Base Architecture Deployment completed successfully! =============="
