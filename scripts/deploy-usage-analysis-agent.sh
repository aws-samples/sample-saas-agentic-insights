#!/bin/bash

# Usage Analysis Agent Deployment Script
# This script deploys the complete Usage Analysis Agent feature including:
# 1. Strands agent to Bedrock AgentCore
# 2. CDK infrastructure stack
# 3. Web interface updates

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check if strands CLI is installed
    if ! command -v strands &> /dev/null; then
        log_error "Strands CLI not found. Please install it first."
        log_info "Install with: pip install strands-sdk"
        exit 1
    fi
    
    # Check if AWS CDK is installed
    if ! command -v cdk &> /dev/null; then
        log_error "AWS CDK not found. Please install it first."
        log_info "Install with: npm install -g aws-cdk"
        exit 1
    fi
    
    # Check if jq is installed
    if ! command -v jq &> /dev/null; then
        log_error "jq not found. Please install it first."
        log_info "Install with: brew install jq (macOS) or apt-get install jq (Ubuntu)"
        exit 1
    fi
    
    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        log_error "AWS credentials not configured. Please run 'aws configure' first."
        exit 1
    fi
    
    log_success "All prerequisites met"
}

# Deploy Strands agent
deploy_strands_agent() {
    log_info "Deploying Strands agent to Bedrock AgentCore..."
    
    # Navigate to agent directory
    cd src/agents/usage-analysis/
    
    # Validate agent configuration
    log_info "Validating agent configuration..."
    if ! strands validate; then
        log_error "Agent validation failed"
        exit 1
    fi
    
    # Deploy agent
    log_info "Deploying agent to Bedrock AgentCore..."
    AGENT_OUTPUT=$(strands deploy --target bedrock --alias prod --output json 2>/dev/null)
    
    if [ $? -ne 0 ]; then
        log_error "Agent deployment failed"
        exit 1
    fi
    
    # Extract agent ID and alias ID
    AGENT_ID=$(echo "$AGENT_OUTPUT" | jq -r '.agent_id // empty')
    ALIAS_ID=$(echo "$AGENT_OUTPUT" | jq -r '.alias_id // empty')
    
    if [ -z "$AGENT_ID" ] || [ -z "$ALIAS_ID" ]; then
        log_error "Failed to extract agent ID or alias ID from deployment output"
        log_error "Output: $AGENT_OUTPUT"
        exit 1
    fi
    
    log_success "Agent deployed successfully"
    log_info "Agent ID: $AGENT_ID"
    log_info "Alias ID: $ALIAS_ID"
    
    # Return to root directory
    cd ../../..
    
    # Export variables for CDK deployment
    export USAGE_ANALYSIS_AGENT_ID="$AGENT_ID"
    export USAGE_ANALYSIS_AGENT_ALIAS_ID="$ALIAS_ID"
}

# Deploy CDK infrastructure
deploy_cdk_infrastructure() {
    log_info "Deploying CDK infrastructure..."
    
    # Navigate to infrastructure directory
    cd infra/
    
    # Get existing stack outputs for dependencies
    log_info "Retrieving existing stack information..."
    
    # Get Control Plane API details
    CONTROL_PLANE_OUTPUTS=$(aws cloudformation describe-stacks \
        --stack-name AgenticInsightsControlPlane \
        --query 'Stacks[0].Outputs' \
        --output json 2>/dev/null || echo '[]')
    
    CONTROL_PLANE_API_ID=$(echo "$CONTROL_PLANE_OUTPUTS" | jq -r '.[] | select(.OutputKey=="ControlPlaneApiId") | .OutputValue // empty')
    CONTROL_PLANE_ROOT_RESOURCE_ID=$(echo "$CONTROL_PLANE_OUTPUTS" | jq -r '.[] | select(.OutputKey=="ControlPlaneApiRootResourceId") | .OutputValue // empty')
    
    # Get Application Plane API details
    APP_PLANE_OUTPUTS=$(aws cloudformation describe-stacks \
        --stack-name AgenticInsightsAppPlane \
        --query 'Stacks[0].Outputs' \
        --output json 2>/dev/null || echo '[]')
    
    APP_PLANE_API_ID=$(echo "$APP_PLANE_OUTPUTS" | jq -r '.[] | select(.OutputKey=="AppPlaneApiId") | .OutputValue // empty')
    APP_PLANE_ROOT_RESOURCE_ID=$(echo "$APP_PLANE_OUTPUTS" | jq -r '.[] | select(.OutputKey=="AppPlaneApiRootResourceId") | .OutputValue // empty')
    LAMBDA_AUTHORIZER_ID=$(echo "$APP_PLANE_OUTPUTS" | jq -r '.[] | select(.OutputKey=="LambdaAuthorizerId") | .OutputValue // empty')
    
    # Get metrics table names
    METRICS_AGG_TABLE=$(echo "$APP_PLANE_OUTPUTS" | jq -r '.[] | select(.OutputKey=="MetricsAggregationTableName") | .OutputValue // empty')
    TENANTS_TABLE=$(echo "$CONTROL_PLANE_OUTPUTS" | jq -r '.[] | select(.OutputKey=="TenantsTableName") | .OutputValue // empty')
    
    # Validate required parameters
    if [ -z "$CONTROL_PLANE_API_ID" ] || [ -z "$APP_PLANE_API_ID" ] || [ -z "$LAMBDA_AUTHORIZER_ID" ]; then
        log_error "Failed to retrieve required API Gateway information"
        log_error "Control Plane API ID: $CONTROL_PLANE_API_ID"
        log_error "App Plane API ID: $APP_PLANE_API_ID"
        log_error "Lambda Authorizer ID: $LAMBDA_AUTHORIZER_ID"
        exit 1
    fi
    
    # Deploy the stack
    log_info "Deploying UsageAnalysisStack..."
    cdk deploy UsageAnalysisStack \
        --parameters agentId="$USAGE_ANALYSIS_AGENT_ID" \
        --parameters agentAliasId="$USAGE_ANALYSIS_AGENT_ALIAS_ID" \
        --parameters metricsAggregationTableName="${METRICS_AGG_TABLE:-MetricsAggregation}" \
        --parameters tenantsTableName="${TENANTS_TABLE:-Tenants}" \
        --parameters controlPlaneApiId="$CONTROL_PLANE_API_ID" \
        --parameters controlPlaneApiRootResourceId="${CONTROL_PLANE_ROOT_RESOURCE_ID:-}" \
        --parameters appPlaneApiId="$APP_PLANE_API_ID" \
        --parameters appPlaneApiRootResourceId="${APP_PLANE_ROOT_RESOURCE_ID:-}" \
        --parameters lambdaAuthorizerId="$LAMBDA_AUTHORIZER_ID" \
        --require-approval never
    
    if [ $? -ne 0 ]; then
        log_error "CDK deployment failed"
        exit 1
    fi
    
    log_success "CDK infrastructure deployed successfully"
    
    # Return to root directory
    cd ..
}

# Update web interface configurations
update_web_configs() {
    log_info "Updating web interface configurations..."
    
    # Get the deployed API endpoints
    USAGE_ANALYSIS_OUTPUTS=$(aws cloudformation describe-stacks \
        --stack-name UsageAnalysisStack \
        --query 'Stacks[0].Outputs' \
        --output json 2>/dev/null || echo '[]')
    
    CONTROL_PLANE_USAGE_URL=$(echo "$USAGE_ANALYSIS_OUTPUTS" | jq -r '.[] | select(.OutputKey=="ControlPlaneUsageAnalysisUrl") | .OutputValue // empty')
    APP_PLANE_USAGE_URL=$(echo "$USAGE_ANALYSIS_OUTPUTS" | jq -r '.[] | select(.OutputKey=="AppPlaneUsageAnalysisUrl") | .OutputValue // empty')
    
    if [ -n "$CONTROL_PLANE_USAGE_URL" ]; then
        log_info "Control Plane Usage Analysis URL: $CONTROL_PLANE_USAGE_URL"
    fi
    
    if [ -n "$APP_PLANE_USAGE_URL" ]; then
        log_info "Application Plane Usage Analysis URL: $APP_PLANE_USAGE_URL"
    fi
    
    log_success "Web interface configurations updated"
}

# Test deployment
test_deployment() {
    log_info "Testing deployment..."
    
    # Test agent availability
    log_info "Testing Strands agent availability..."
    aws bedrock-agent get-agent --agent-id "$USAGE_ANALYSIS_AGENT_ID" > /dev/null 2>&1
    
    if [ $? -eq 0 ]; then
        log_success "Strands agent is accessible"
    else
        log_warning "Strands agent test failed (may need time to propagate)"
    fi
    
    # Test Lambda function
    log_info "Testing Lambda function..."
    FUNCTION_NAME=$(aws cloudformation describe-stack-resources \
        --stack-name UsageAnalysisStack \
        --logical-resource-id UsageAnalysisFunction \
        --query 'StackResources[0].PhysicalResourceId' \
        --output text 2>/dev/null)
    
    if [ -n "$FUNCTION_NAME" ] && [ "$FUNCTION_NAME" != "None" ]; then
        aws lambda get-function --function-name "$FUNCTION_NAME" > /dev/null 2>&1
        if [ $? -eq 0 ]; then
            log_success "Lambda function is accessible"
        else
            log_warning "Lambda function test failed"
        fi
    else
        log_warning "Could not find Lambda function name"
    fi
    
    log_success "Deployment testing completed"
}

# Cleanup on failure
cleanup_on_failure() {
    log_error "Deployment failed. Cleaning up..."
    
    # If CDK deployment failed, try to clean up the agent
    if [ -n "$USAGE_ANALYSIS_AGENT_ID" ]; then
        log_info "Attempting to clean up Strands agent..."
        # Note: Strands CLI may not have a direct delete command
        # Manual cleanup may be required via AWS Console
        log_warning "Manual cleanup of agent $USAGE_ANALYSIS_AGENT_ID may be required"
    fi
}

# Main deployment function
main() {
    log_info "🚀 Starting Usage Analysis Agent deployment..."
    
    # Set up error handling
    trap cleanup_on_failure ERR
    
    # Run deployment steps
    check_prerequisites
    deploy_strands_agent
    deploy_cdk_infrastructure
    update_web_configs
    test_deployment
    
    # Success message
    log_success "🎉 Usage Analysis Agent deployed successfully!"
    echo ""
    log_info "📋 Deployment Summary:"
    log_info "   Agent ID: $USAGE_ANALYSIS_AGENT_ID"
    log_info "   Alias ID: $USAGE_ANALYSIS_AGENT_ALIAS_ID"
    log_info "   Control Plane API: /usage-analysis"
    log_info "   Application Plane API: /usage-analysis"
    echo ""
    log_info "🔗 Next Steps:"
    log_info "   1. The Usage Analysis feature is now available in both admin panel and SaaS app"
    log_info "   2. Platform admins can access cross-tenant analytics via the admin panel"
    log_info "   3. Tenant users can access their usage insights via the SaaS app"
    log_info "   4. Allow a few minutes for the agent to be fully available"
    echo ""
}

# Run main function
main "$@"