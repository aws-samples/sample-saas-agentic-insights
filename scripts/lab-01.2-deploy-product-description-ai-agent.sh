#!/bin/bash

# Lab 01.2: Deploy Product Description AI Agent
# This script deploys a complete AI-powered product description generator
# using Amazon Bedrock Agent with Claude 3 Haiku via CDK

set -e  # Exit on any error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Print functions
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

# Global variables
AWS_ACCOUNT_ID=""
AWS_REGION=""
BEDROCK_AGENT_ID=""
BEDROCK_AGENT_ALIAS_ID=""

# Main deployment function
main() {
    echo "🤖 Starting deployment of AI Product Description Generator..."
    echo "================================================================"
    
    # Step 1: Prerequisites check
    check_prerequisites
    
    # Step 2: Get AWS context
    get_aws_context
    
    # Step 3: Deploy CDK stack (creates everything)
    deploy_cdk_stack
    
    # Step 4: Verify and ensure API Gateway deployment
    verify_api_gateway_deployment
    
    # Step 5: Wait for agent to be prepared
    wait_for_agent_preparation
    
    # Step 6: Verify deployment
    verify_deployment
    
    # Step 7: Display results
    display_results
}

check_prerequisites() {
    print_status "Checking prerequisites..."
    
    # Check AWS CLI
    if ! command -v aws &> /dev/null; then
        print_error "AWS CLI not found. Please install AWS CLI."
        exit 1
    fi
    
    # Check CDK
    if ! command -v cdk &> /dev/null; then
        print_error "AWS CDK not found. Please install AWS CDK."
        exit 1
    fi
    
    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        print_error "AWS credentials not configured. Please run 'aws configure'."
        exit 1
    fi
    
    # Check Node.js and npm
    if ! command -v npm &> /dev/null; then
        print_error "npm not found. Please install Node.js and npm."
        exit 1
    fi
    
    # Check agent config files exist
    if [ ! -f "src/app-plane/agents/product-desc/agent-config.yaml" ]; then
        print_error "Agent configuration file not found: src/app-plane/agents/product-desc/agent-config.yaml"
        exit 1
    fi
    
    if [ ! -f "src/app-plane/agents/product-desc/instructions.txt" ]; then
        print_error "Agent instructions file not found: src/app-plane/agents/product-desc/instructions.txt"
        exit 1
    fi
    
    print_success "Prerequisites check completed"
}

get_aws_context() {
    print_status "Getting AWS context..."
    
    AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    AWS_REGION=$(aws configure get region)
    
    if [ -z "$AWS_REGION" ]; then
        print_error "AWS region is not set. Please configure your AWS region:"
        echo "  aws configure set region <region_name>"
        echo "  or export AWS_DEFAULT_REGION=<region_name>"
        exit 1
    fi
    
    print_status "Deploying to AWS Account: $AWS_ACCOUNT_ID in Region: $AWS_REGION"
}

deploy_cdk_stack() {
    print_status "Installing dependencies and building..."
    
    # Install dependencies
    npm install
    
    # Build TypeScript
    npm run build
    
    print_status "Deploying AI Description Stack (this creates the Bedrock agent, IAM roles, Lambda, and API Gateway)..."
    
    # Deploy AI Description stack specifically
    cdk deploy AgenticInsightsAIDescription --require-approval never
    
    print_success "CDK stacks deployed successfully"
    
    # Get agent IDs from CDK outputs
    print_status "Retrieving Bedrock agent information..."
    
    BEDROCK_AGENT_ID=$(aws cloudformation describe-stacks \
        --stack-name AgenticInsightsAIDescription \
        --query "Stacks[0].Outputs[?OutputKey=='BedrockAgentId'].OutputValue" \
        --output text 2>/dev/null || echo "")
    
    BEDROCK_AGENT_ALIAS_ID=$(aws cloudformation describe-stacks \
        --stack-name AgenticInsightsAIDescription \
        --query "Stacks[0].Outputs[?OutputKey=='BedrockAgentAliasId'].OutputValue" \
        --output text 2>/dev/null || echo "")
    
    if [ -n "$BEDROCK_AGENT_ID" ] && [ -n "$BEDROCK_AGENT_ALIAS_ID" ]; then
        print_success "Retrieved agent information:"
        print_status "Agent ID: $BEDROCK_AGENT_ID"
        print_status "Alias ID: $BEDROCK_AGENT_ALIAS_ID"
    else
        print_warning "Could not retrieve agent IDs from CDK outputs"
    fi
}

verify_api_gateway_deployment() {
    print_status "Ensuring API Gateway deployment..."
    
    # Get API Gateway ID
    local api_id=$(aws cloudformation describe-stacks \
        --stack-name AgenticInsightsAppPlane \
        --query "Stacks[0].Outputs[?OutputKey=='ExportsOutputRefAppPlaneApi1864DF3FAA9EC325'].OutputValue" \
        --output text 2>/dev/null)
    
    if [ -z "$api_id" ] || [ "$api_id" = "None" ]; then
        print_warning "⚠️ Could not find API Gateway ID, skipping deployment"
        return
    fi
    
    print_status "Found API Gateway ID: $api_id"
    
    # Always force deployment
    local deployment_id=$(aws apigateway create-deployment \
        --rest-api-id "$api_id" \
        --stage-name prod \
        --description "Deploy AI endpoints - $(date)" \
        --query 'id' \
        --output text 2>/dev/null)
    
    if [ -n "$deployment_id" ]; then
        print_status "Deployment initiated (ID: $deployment_id), waiting for readiness..."
        
        local endpoint_url="https://${api_id}.execute-api.${AWS_REGION}.amazonaws.com/prod/ai/generate-description"
        local max_attempts=12
        local attempt=1
        
        while [ $attempt -le $max_attempts ]; do
            sleep 10
            
            # Test CORS (should return 204 when ready)
            local status_code=$(curl -X OPTIONS \
                -H "Origin: https://example.com" \
                -H "Access-Control-Request-Method: POST" \
                -H "Access-Control-Request-Headers: Content-Type,Authorization" \
                -s -o /dev/null -w "%{http_code}" \
                "$endpoint_url" 2>/dev/null || echo "000")
            
            if [ "$status_code" = "204" ]; then
                print_success "✅ API Gateway endpoint is ready!"
                return
            fi
            
            print_status "Attempt $attempt/$max_attempts: Status $status_code, waiting..."
            attempt=$((attempt + 1))
        done
        
        print_warning "⚠️ Endpoint may not be fully ready, but continuing..."
    else
        print_warning "⚠️ Could not force API Gateway deployment"
    fi
}

wait_for_agent_preparation() {
    if [ -z "$BEDROCK_AGENT_ID" ]; then
        print_warning "No agent ID available, skipping preparation wait"
        return
    fi
    
    print_status "Waiting for Bedrock agent to be prepared..."
    
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        local current_status=$(aws bedrock-agent get-agent --agent-id "$BEDROCK_AGENT_ID" --query 'agent.agentStatus' --output text 2>/dev/null || echo "UNKNOWN")
        
        if [ "$current_status" = "PREPARED" ]; then
            print_success "✅ Bedrock agent is prepared and ready!"
            return 0
        fi
        
        if [ "$current_status" = "FAILED" ]; then
            print_error "❌ Bedrock agent preparation failed"
            exit 1
        fi
        
        print_status "Agent status: $current_status (attempt $attempt/$max_attempts)"
        sleep 10
        ((attempt++))
    done
    
    print_warning "⚠️ Timeout waiting for agent preparation, but continuing..."
}

verify_deployment() {
    print_status "Verifying deployment..."
    
    # Check agent status
    if [ -n "$BEDROCK_AGENT_ID" ]; then
        local agent_status=$(aws bedrock-agent get-agent --agent-id "$BEDROCK_AGENT_ID" --query 'agent.agentStatus' --output text 2>/dev/null || echo "UNKNOWN")
        if [ "$agent_status" = "PREPARED" ]; then
            print_success "✅ Bedrock agent is ready"
        else
            print_warning "⚠️ Bedrock agent status: $agent_status"
        fi
    fi
    
    # Check alias status
    if [ -n "$BEDROCK_AGENT_ID" ] && [ -n "$BEDROCK_AGENT_ALIAS_ID" ]; then
        local alias_status=$(aws bedrock-agent get-agent-alias --agent-id "$BEDROCK_AGENT_ID" --agent-alias-id "$BEDROCK_AGENT_ALIAS_ID" --query 'agentAlias.agentAliasStatus' --output text 2>/dev/null || echo "UNKNOWN")
        if [ "$alias_status" = "PREPARED" ]; then
            print_success "✅ Agent alias is ready"
        else
            print_warning "⚠️ Agent alias status: $alias_status"
        fi
    fi
    
    # Get API endpoint
    local api_endpoint=$(aws cloudformation describe-stacks \
        --stack-name AgenticInsightsAIDescription \
        --query "Stacks[0].Outputs[?OutputKey=='AIDescriptionEndpoint'].OutputValue" \
        --output text 2>/dev/null || echo "")
    
    if [ -n "$api_endpoint" ]; then
        print_success "✅ API endpoint available"
    else
        print_warning "⚠️ Could not retrieve API endpoint"
    fi
}

display_results() {
    echo ""
    echo "================================================================"
    print_success "🎉 AI Product Description Generator deployed successfully!"
    echo "================================================================"
    echo ""
    echo "📋 Deployment Summary:"
    echo "----------------------"
    echo "AWS Account: $AWS_ACCOUNT_ID"
    echo "AWS Region: $AWS_REGION"
    echo ""
    echo "🤖 Bedrock Agent:"
    echo "Agent ID: ${BEDROCK_AGENT_ID:-'Check CDK outputs'}"
    echo "Alias ID: ${BEDROCK_AGENT_ALIAS_ID:-'Check CDK outputs'}"
    echo "Model: Claude 3 Haiku (inference profile)"
    echo ""
    
    # Get API endpoint
    local api_endpoint=$(aws cloudformation describe-stacks \
        --stack-name AgenticInsightsAIDescription \
        --query "Stacks[0].Outputs[?OutputKey=='AIDescriptionEndpoint'].OutputValue" \
        --output text 2>/dev/null || echo "Not available")
    
    echo "🔗 API Endpoint:"
    echo "AI Description API: $api_endpoint"
    echo ""
    echo "📚 Next Steps:"
    echo "1. Test the AI generation feature in the SaaS app product creation modal"
    echo "2. Check CloudWatch logs for usage tracking and debugging"
    echo "3. Monitor costs in the AWS Billing console"
    echo ""
    echo "🧪 Testing:"
    if [ "$api_endpoint" != "Not available" ]; then
        echo "curl -X POST $api_endpoint \\"
        echo "  -H 'Authorization: Bearer <your-jwt-token>' \\"
        echo "  -H 'Content-Type: application/json' \\"
        echo "  -H 'tenant-id: <your-tenant-id>' \\"
        echo "  -d '{\"product_name\":\"Test Product\",\"short_description\":\"A great product\"}'"
    fi
    echo ""
    echo "🗑️ To remove the AI feature, run: cdk destroy AgenticInsightsAppPlane"
    echo "================================================================"
}

# Run main function
main "$@"
