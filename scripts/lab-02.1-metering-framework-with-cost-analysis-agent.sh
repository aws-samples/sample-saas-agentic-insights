#!/bin/bash

# Lab 02.1: Deploy Metering Framework with AI Cost Analysis Agent
# This script deploys comprehensive tenant-specific metrics collection and AI-powered cost analysis
# Usage: ./lab-02.1-metering-framework-with-cost-analysis-agent.sh

set -e  # Exit on any error

echo "🤖 Lab 02.1: Deploying Metering Framework with AI Cost Analysis..."
echo "=================================================================="

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

print_status "Phase 2: Deploying Cost Analysis Agent Stack..."
cdk deploy AgenticInsightsCostAnalysisAgent --require-approval never

print_status "Phase 3: Updating Application Services with Metrics Collection..."
cdk deploy AgenticInsightsAppPlane --require-approval never

print_status "Phase 4: Updating Enhanced Admin Dashboard..."
# The dashboard updates are deployed as part of the AppPlane stack

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

COST_ANALYSIS_AGENT_ID=$(aws cloudformation describe-stacks \
    --stack-name AgenticInsightsCostAnalysisAgent \
    --query 'Stacks[0].Outputs[?OutputKey==`CostAnalysisAgentId`].OutputValue' \
    --output text 2>/dev/null || echo "")

COST_ANALYSIS_API=$(aws cloudformation describe-stacks \
    --stack-name AgenticInsightsCostAnalysisAgent \
    --query 'Stacks[0].Outputs[?OutputKey==`CostAnalysisApiUrl`].OutputValue' \
    --output text 2>/dev/null || echo "")

# Wait for Bedrock Agent to be prepared
if [ -n "$COST_ANALYSIS_AGENT_ID" ]; then
    print_status "Waiting for Bedrock Agent to be prepared (this may take 2-3 minutes)..."
    
    max_attempts=30
    attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        agent_status=$(aws bedrock-agent get-agent \
            --agent-id "$COST_ANALYSIS_AGENT_ID" \
            --query 'agent.agentStatus' \
            --output text 2>/dev/null || echo "UNKNOWN")
        
        if [ "$agent_status" = "PREPARED" ]; then
            print_success "Bedrock Agent is ready!"
            break
        elif [ "$agent_status" = "FAILED" ]; then
            print_error "Bedrock Agent preparation failed"
            break
        else
            echo -n "."
            sleep 10
            attempt=$((attempt + 1))
        fi
    done
    
    if [ $attempt -gt $max_attempts ]; then
        print_warning "Bedrock Agent preparation is taking longer than expected. It may still be preparing in the background."
    fi
fi

# Display deployment summary
echo
echo "=================================================================="
print_success "🎉 Metering Framework with AI Cost Analysis deployed successfully!"
echo "=================================================================="
echo
echo "📋 Deployment Summary:"
echo "----------------------"
echo "AWS Account: $AWS_ACCOUNT"
echo "AWS Region: $AWS_REGION"
echo
echo "🔗 Application URLs:"
if [ -n "$ADMIN_PANEL_URL" ]; then
    echo "Enhanced Admin Panel: $ADMIN_PANEL_URL"
    echo "  └── Cost Analysis Tab: Available with AI badge"
fi
echo
echo "🔧 API Endpoints:"
if [ -n "$APP_PLANE_API" ]; then
    echo "Application Plane API: $APP_PLANE_API"
fi
if [ -n "$COST_ANALYSIS_API" ]; then
    echo "Cost Analysis API: $COST_ANALYSIS_API"
fi
echo
echo "🤖 AI Resources:"
if [ -n "$COST_ANALYSIS_AGENT_ID" ]; then
    echo "Bedrock Agent ID: $COST_ANALYSIS_AGENT_ID"
    echo "  └── Action Groups: Infrastructure Usage, Cost Analysis, Cost Prediction"
fi
echo
echo "📊 Features Deployed:"
echo "• Enhanced Metrics Collection Library (Lambda Layer)"
echo "• Event-Driven Metrics Pipeline (EventBridge)"
echo "• Metrics Aggregation Service (DynamoDB Streams)"
echo "• AI-Powered Cost Analysis (Claude 3 Haiku)"
echo "• Enhanced Admin Dashboard with Cost Analysis Tab"
echo "• Real-time Cost Tracking (90-day retention)"
echo
echo "📚 Next Steps:"
echo "1. Visit the Enhanced Admin Panel: $ADMIN_PANEL_URL"
echo "2. Click on 'Cost Analysis' tab in the left navigation"
echo "3. Explore AI-powered cost insights and tenant profitability"
echo "4. Monitor real-time metrics collection from tenant activities"
echo
echo "🗑️  To remove everything, run: ./scripts/delete-all.sh"
echo "=================================================================="
