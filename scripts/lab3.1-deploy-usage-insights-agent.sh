#!/bin/bash

# Deploy Advanced Usage Insights Agent
# This script deploys the Usage Insights Agent to Bedrock AgentCore
# and integrates it with the CDK infrastructure
# Usage: ./scripts/lab-05.1-deploy-usage-insights-agent.sh

set -e  # Exit on any error

echo "🚀 Deploying Advanced Usage Insights Agent..."
echo "=============================================="

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

# Global variables
AWS_ACCOUNT_ID=""
AWS_REGION=""
BEDROCK_AGENT_ID=""
BEDROCK_AGENT_ALIAS_ID=""
CONTROL_PLANE_API_ID=""
USAGE_METRICS_TABLE_NAME=""
TENANTS_TABLE_NAME=""

# Main deployment function
main() {
    echo "🤖 Starting deployment of Usage Insights Agent..."
    echo "================================================="
    
    # Step 1: Prerequisites check
    check_prerequisites
    
    # Step 2: Get AWS context and existing infrastructure
    get_aws_context
    get_existing_infrastructure
    
    # Step 3: Deploy CDK infrastructure stack (includes Bedrock agent creation)
    deploy_cdk_stack
    
    # Step 4: Get agent IDs from CDK outputs
    get_agent_ids_from_stack
    
    # Step 5: Wait for agent preparation
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
    
    # Check Bedrock CLI access
    if ! aws bedrock-agent list-agents --max-results 1 &> /dev/null; then
        print_error "AWS Bedrock Agent access not available. Please ensure you have proper permissions."
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
    
    # Check base infrastructure exists
    if ! aws cloudformation describe-stacks --stack-name AgenticInsightsControlPlane &> /dev/null; then
        print_error "Base architecture not found. Please run lab-01.1-deploy-base-architecture.sh first."
        exit 1
    fi
    
    if ! aws cloudformation describe-stacks --stack-name AgenticInsightsAppPlane &> /dev/null; then
        print_error "Application plane not found. Please run lab-01.1-deploy-base-architecture.sh first."
        exit 1
    fi
    
    if ! aws cloudformation describe-stacks --stack-name AgenticInsightsMetricsFramework &> /dev/null; then
        print_error "Metrics framework not found. Please run lab-02.1-metering-framework-with-cost-analysis-agent.sh first."
        exit 1
    fi
    
    # Check agent configuration files exist
    if [ ! -f "src/control-plane/agents/usage-insights/agent.yaml" ]; then
        print_error "Agent configuration file not found: src/control-plane/agents/usage-insights/agent.yaml"
        exit 1
    fi
    
    if [ ! -f "src/control-plane/agents/usage-insights/prompts/system_prompt.txt" ]; then
        print_error "Agent system prompt file not found: src/control-plane/agents/usage-insights/prompts/system_prompt.txt"
        exit 1
    fi
    
    # Check agent tools exist
    local tools_dir="src/control-plane/agents/usage-insights/tools"
    for tool in "ttv_calculator.py" "cltv_projector.py" "feature_adoption_analyzer.py" "engagement_calculator.py" "at_risk_identifier.py"; do
        if [ ! -f "$tools_dir/$tool" ]; then
            print_error "Agent tool not found: $tools_dir/$tool"
            exit 1
        fi
    done
    
    print_success "Prerequisites check completed"
}

get_aws_context() {
    print_status "Getting AWS context..."
    
    AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    AWS_REGION=$(aws configure get region)
    
    if [ -z "$AWS_REGION" ]; then
        print_error "AWS region is not set. Please configure your AWS region."
        exit 1
    fi
    
    print_status "Deploying to AWS Account: $AWS_ACCOUNT_ID in Region: $AWS_REGION"
}

get_existing_infrastructure() {
    print_status "Retrieving existing infrastructure information..."
    
    # Get Control Plane API Gateway ID
    CONTROL_PLANE_API_ID=$(aws cloudformation describe-stacks \
        --stack-name AgenticInsightsControlPlane \
        --query "Stacks[0].Outputs[?OutputKey=='ControlPlaneApiID'].OutputValue" \
        --output text 2>/dev/null || echo "")
    
    if [ -z "$CONTROL_PLANE_API_ID" ] || [ "$CONTROL_PLANE_API_ID" = "None" ]; then
        print_error "Could not retrieve Control Plane API Gateway ID"
        exit 1
    fi
    
    # Get Usage Metrics Table Name
    USAGE_METRICS_TABLE_NAME="AgenticInsights-UsageMetrics"
    
    # Get Tenants Table Name
    TENANTS_TABLE_NAME=$(aws cloudformation describe-stacks \
        --stack-name AgenticInsightsControlPlane \
        --query "Stacks[0].Outputs[?OutputKey=='TenantsTableName'].OutputValue" \
        --output text 2>/dev/null || echo "")
    
    if [ -z "$TENANTS_TABLE_NAME" ] || [ "$TENANTS_TABLE_NAME" = "None" ]; then
        print_error "Could not retrieve Tenants Table Name"
        exit 1
    fi
    
    print_success "Retrieved existing infrastructure:"
    print_status "Control Plane API ID: $CONTROL_PLANE_API_ID"
    print_status "Usage Metrics Table: $USAGE_METRICS_TABLE_NAME"
    print_status "Tenants Table: $TENANTS_TABLE_NAME"
}

get_agent_ids_from_stack() {
    print_status "Retrieving Bedrock agent IDs from CDK stack outputs..."
    
    # Get agent ID from stack outputs
    BEDROCK_AGENT_ID=$(aws cloudformation describe-stacks \
        --stack-name AgenticInsightsUsageInsightsAgent \
        --query "Stacks[0].Outputs[?OutputKey=='BedrockAgentId'].OutputValue" \
        --output text 2>/dev/null || echo "")
    
    if [ -z "$BEDROCK_AGENT_ID" ] || [ "$BEDROCK_AGENT_ID" = "None" ]; then
        print_error "Could not retrieve Bedrock Agent ID from stack outputs"
        exit 1
    fi
    
    # Get agent alias ID from stack outputs
    BEDROCK_AGENT_ALIAS_ID=$(aws cloudformation describe-stacks \
        --stack-name AgenticInsightsUsageInsightsAgent \
        --query "Stacks[0].Outputs[?OutputKey=='BedrockAgentAliasId'].OutputValue" \
        --output text 2>/dev/null || echo "")
    
    if [ -z "$BEDROCK_AGENT_ALIAS_ID" ] || [ "$BEDROCK_AGENT_ALIAS_ID" = "None" ]; then
        print_error "Could not retrieve Bedrock Agent Alias ID from stack outputs"
        exit 1
    fi
    
    print_success "Retrieved agent IDs from stack:"
    print_status "Agent ID: $BEDROCK_AGENT_ID"
    print_status "Alias ID: $BEDROCK_AGENT_ALIAS_ID"
}

# This function is no longer needed as CDK creates the agent
# Keeping it for reference but it won't be called
deploy_bedrock_agent_legacy() {
    print_status "Deploying Bedrock agent using AWS CLI..."
    
    # Navigate to agent directory
    cd src/control-plane/agents/usage-insights/
    
    # Validate agent configuration
    print_status "Validating agent configuration..."
    if [ ! -f "agent.yaml" ]; then
        print_error "Agent configuration file not found: agent.yaml"
        exit 1
    fi
    
    if [ ! -f "prompts/system_prompt.txt" ]; then
        print_error "System prompt file not found: prompts/system_prompt.txt"
        exit 1
    fi
    
    print_success "Agent configuration files validated"
    
    # Read system prompt
    local system_prompt=$(cat prompts/system_prompt.txt)
    
    # Create IAM role for Bedrock agent
    print_status "Creating IAM role for Bedrock agent..."
    local role_name="UsageInsightsBedrockAgentRole"
    local role_arn="arn:aws:iam::$AWS_ACCOUNT_ID:role/$role_name"
    
    # Check if role exists
    if ! aws iam get-role --role-name "$role_name" &> /dev/null; then
        print_status "Creating IAM role: $role_name"
        
        # Create trust policy
        local trust_policy='{
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {
                        "Service": "bedrock.amazonaws.com"
                    },
                    "Action": "sts:AssumeRole"
                }
            ]
        }'
        
        # Create role
        aws iam create-role \
            --role-name "$role_name" \
            --assume-role-policy-document "$trust_policy" \
            --description "IAM role for Usage Insights Bedrock Agent" > /dev/null
        
        # Attach Bedrock permissions
        aws iam attach-role-policy \
            --role-name "$role_name" \
            --policy-arn "arn:aws:iam::aws:policy/AmazonBedrockFullAccess" > /dev/null
        
        print_success "IAM role created: $role_arn"
        
        # Wait for role to be available
        print_status "Waiting for IAM role to be available..."
        sleep 10
    else
        print_success "Using existing IAM role: $role_arn"
    fi
    
    # Create Bedrock agent
    print_status "Creating Bedrock agent (this may take 2-3 minutes)..."
    
    local agent_name="usage-insights-agent"
    local foundation_model="anthropic.claude-3-haiku-20240307-v1:0"
    
    # Check if agent already exists
    BEDROCK_AGENT_ID=$(aws bedrock-agent list-agents \
        --query "agentSummaries[?agentName=='$agent_name'] | [0].agentId" \
        --output text 2>/dev/null || echo "")
    
    if [ -n "$BEDROCK_AGENT_ID" ] && [ "$BEDROCK_AGENT_ID" != "None" ] && [ "$BEDROCK_AGENT_ID" != "null" ]; then
        print_warning "Agent '$agent_name' already exists with ID: $BEDROCK_AGENT_ID"
        print_status "Updating existing agent..."
        
        # Update existing agent
        aws bedrock-agent update-agent \
            --agent-id "$BEDROCK_AGENT_ID" \
            --agent-name "$agent_name" \
            --foundation-model "$foundation_model" \
            --description "AI agent for advanced usage analytics including TTV, CLTV, engagement, and at-risk feature identification" \
            --instruction "$system_prompt" \
            --agent-resource-role-arn "$role_arn" \
            --idle-session-ttl-in-seconds 900 > /dev/null
        
        if [ $? -eq 0 ]; then
            print_success "Agent updated successfully"
        else
            print_error "Failed to update existing agent"
            exit 1
        fi
    else
        print_status "Creating new Bedrock agent..."
        
        # Create new agent
        local create_output=$(aws bedrock-agent create-agent \
            --agent-name "$agent_name" \
            --foundation-model "$foundation_model" \
            --description "AI agent for advanced usage analytics including TTV, CLTV, engagement, and at-risk feature identification" \
            --instruction "$system_prompt" \
            --agent-resource-role-arn "$role_arn" \
            --idle-session-ttl-in-seconds 900 \
            --output json 2>/dev/null)
        
        if [ $? -eq 0 ]; then
            BEDROCK_AGENT_ID=$(echo "$create_output" | grep -o '"agentId"[[:space:]]*:[[:space:]]*"[^"]*"' | sed 's/.*"agentId"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/')
            
            if [ -n "$BEDROCK_AGENT_ID" ]; then
                print_success "Agent created successfully with ID: $BEDROCK_AGENT_ID"
            else
                print_error "Failed to extract agent ID from creation response"
                exit 1
            fi
        else
            print_error "Failed to create Bedrock agent"
            exit 1
        fi
    fi
    
    # Prepare the agent
    print_status "Preparing agent..."
    aws bedrock-agent prepare-agent --agent-id "$BEDROCK_AGENT_ID" > /dev/null
    
    if [ $? -eq 0 ]; then
        print_success "Agent preparation initiated"
    else
        print_warning "Agent preparation may have failed, but continuing..."
    fi
    
    # Create or get agent alias
    print_status "Setting up agent alias..."
    
    # Check if 'prod' alias exists
    BEDROCK_AGENT_ALIAS_ID=$(aws bedrock-agent list-agent-aliases \
        --agent-id "$BEDROCK_AGENT_ID" \
        --query "agentAliasSummaries[?agentAliasName=='prod'] | [0].agentAliasId" \
        --output text 2>/dev/null || echo "")
    
    if [ -n "$BEDROCK_AGENT_ALIAS_ID" ] && [ "$BEDROCK_AGENT_ALIAS_ID" != "None" ] && [ "$BEDROCK_AGENT_ALIAS_ID" != "null" ]; then
        print_success "Using existing 'prod' alias: $BEDROCK_AGENT_ALIAS_ID"
    else
        print_status "Creating 'prod' alias..."
        
        local alias_output=$(aws bedrock-agent create-agent-alias \
            --agent-id "$BEDROCK_AGENT_ID" \
            --agent-alias-name "prod" \
            --description "Production alias for usage insights agent" \
            --output json 2>/dev/null)
        
        if [ $? -eq 0 ]; then
            BEDROCK_AGENT_ALIAS_ID=$(echo "$alias_output" | grep -o '"agentAliasId"[[:space:]]*:[[:space:]]*"[^"]*"' | sed 's/.*"agentAliasId"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/')
            
            if [ -n "$BEDROCK_AGENT_ALIAS_ID" ]; then
                print_success "Agent alias created successfully: $BEDROCK_AGENT_ALIAS_ID"
            else
                print_error "Failed to extract alias ID from creation response"
                exit 1
            fi
        else
            print_error "Failed to create agent alias"
            exit 1
        fi
    fi
    
    print_success "Bedrock agent deployment completed!"
    print_status "Agent ID: $BEDROCK_AGENT_ID"
    print_status "Alias ID: $BEDROCK_AGENT_ALIAS_ID"
    
    # Navigate back to project root
    cd ../../../../
}

deploy_cdk_stack() {
    print_status "Installing dependencies and building CDK..."
    
    # Install dependencies
    npm install
    
    # Build TypeScript
    npm run build
    
    print_status "Deploying Usage Insights CDK Stack with agent parameters..."
    
    # Get additional required parameters
    local control_plane_root_resource_id=$(aws apigateway get-resources \
        --rest-api-id "$CONTROL_PLANE_API_ID" \
        --query 'items[?path==`/`].id' \
        --output text 2>/dev/null || echo "")
        
    # Get or create AI resource IDs
    local control_plane_ai_resource_id=$(aws apigateway get-resources \
        --rest-api-id "$CONTROL_PLANE_API_ID" \
        --query 'items[?pathPart==`ai`].id' \
        --output text 2>/dev/null || echo "")
    
    # Create AI resources if they don't exist
    if [ -z "$control_plane_ai_resource_id" ] || [ "$control_plane_ai_resource_id" = "None" ]; then
        print_status "Creating 'ai' resource in Control Plane API..."
        control_plane_ai_resource_id=$(aws apigateway create-resource \
            --rest-api-id "$CONTROL_PLANE_API_ID" \
            --parent-id "$control_plane_root_resource_id" \
            --path-part "ai" \
            --query 'id' \
            --output text 2>/dev/null || echo "")
        
        if [ -z "$control_plane_ai_resource_id" ]; then
            print_error "Failed to create 'ai' resource in Control Plane API"
            exit 1
        fi
        print_success "Created Control Plane AI resource: $control_plane_ai_resource_id"
    fi
    
    # Get authorizer IDs
    print_status "Retrieving authorizer IDs..."
    
    local control_plane_authorizer_id=$(aws cloudformation describe-stacks \
        --stack-name AgenticInsightsControlPlane \
        --query "Stacks[0].Outputs[?OutputKey=='ControlPlaneAuthorizerId'].OutputValue" \
        --output text 2>/dev/null || echo "NONE")
    
    # Control Plane authorizer is required
    if [ -z "$control_plane_authorizer_id" ] || [ "$control_plane_authorizer_id" = "None" ]; then
        print_error "Failed to retrieve Control Plane authorizer ID"
        exit 1
    fi
    
    print_success "Retrieved authorizer IDs"
    print_status "  Control Plane: $control_plane_authorizer_id"
    
    # Validate required parameters
    if [ -z "$control_plane_root_resource_id" ]; then
        print_error "Could not retrieve required API Gateway parameters"
        exit 1
    fi
    
    if [ -z "$control_plane_ai_resource_id" ]; then
        print_error "Could not retrieve or create AI resource IDs"
        exit 1
    fi
    
    # Deploy CDK stack with all required parameters
    # Note: agentId and agentAliasId are no longer parameters - they're created by CDK
    cdk deploy AgenticInsightsUsageInsightsAgent \
        --parameters usageMetricsTableName="$USAGE_METRICS_TABLE_NAME" \
        --parameters tenantsTableName="$TENANTS_TABLE_NAME" \
        --parameters controlPlaneApiId="$CONTROL_PLANE_API_ID" \
        --parameters controlPlaneApiRootResourceId="$control_plane_root_resource_id" \
        --parameters controlPlaneAiResourceId="$control_plane_ai_resource_id" \
        --parameters controlPlaneAuthorizerId="$control_plane_authorizer_id" \
        --require-approval never
    
    print_success "CDK stack deployed successfully"
    
    # Redeploy API Gateway to activate changes
    print_status "Redeploying API Gateway to activate endpoints..."
    
    aws apigateway create-deployment \
        --rest-api-id "$CONTROL_PLANE_API_ID" \
        --stage-name prod \
        --description "Activate usage-insights endpoint - $(date)" \
        > /dev/null 2>&1
    
    if [ $? -eq 0 ]; then
        print_success "API Gateway redeployed successfully"
    else
        print_warning "API Gateway redeployment failed - endpoints may not be active"
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
        local current_status=$(aws bedrock-agent get-agent \
            --agent-id "$BEDROCK_AGENT_ID" \
            --query 'agent.agentStatus' \
            --output text 2>/dev/null || echo "UNKNOWN")
        
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
        local agent_status=$(aws bedrock-agent get-agent \
            --agent-id "$BEDROCK_AGENT_ID" \
            --query 'agent.agentStatus' \
            --output text 2>/dev/null || echo "UNKNOWN")
        if [ "$agent_status" = "PREPARED" ]; then
            print_success "✅ Bedrock agent is ready"
        else
            print_warning "⚠️ Bedrock agent status: $agent_status"
        fi
    fi
    
    # Check alias status
    if [ -n "$BEDROCK_AGENT_ID" ] && [ -n "$BEDROCK_AGENT_ALIAS_ID" ]; then
        local alias_status=$(aws bedrock-agent get-agent-alias \
            --agent-id "$BEDROCK_AGENT_ID" \
            --agent-alias-id "$BEDROCK_AGENT_ALIAS_ID" \
            --query 'agentAlias.agentAliasStatus' \
            --output text 2>/dev/null || echo "UNKNOWN")
        if [ "$alias_status" = "PREPARED" ]; then
            print_success "✅ Agent alias is ready"
        else
            print_warning "⚠️ Agent alias status: $alias_status"
        fi
    fi
    
    # Check Lambda function
    local function_name=$(aws cloudformation describe-stacks \
        --stack-name AgenticInsightsUsageInsightsAgent \
        --query "Stacks[0].Outputs[?OutputKey=='UsageInsightsFunctionName'].OutputValue" \
        --output text 2>/dev/null || echo "")
    
    if [ -n "$function_name" ] && [ "$function_name" != "None" ]; then
        local function_status=$(aws lambda get-function \
            --function-name "$function_name" \
            --query 'Configuration.State' \
            --output text 2>/dev/null || echo "UNKNOWN")
        if [ "$function_status" = "Active" ]; then
            print_success "✅ Lambda function is active"
        else
            print_warning "⚠️ Lambda function status: $function_status"
        fi
    fi
    
    # Check API endpoints
    local control_endpoint=$(aws cloudformation describe-stacks \
        --stack-name AgenticInsightsUsageInsightsAgent \
        --query "Stacks[0].Outputs[?OutputKey=='ControlPlaneUsageInsightsEndpoint'].OutputValue" \
        --output text 2>/dev/null || echo "")
    
    local app_endpoint=$(aws cloudformation describe-stacks \
        --stack-name AgenticInsightsUsageInsightsAgent \
        --query "Stacks[0].Outputs[?OutputKey=='AppPlaneUsageInsightsEndpoint'].OutputValue" \
        --output text 2>/dev/null || echo "")
    
    if [ -n "$control_endpoint" ] && [ "$control_endpoint" != "None" ]; then
        print_success "✅ Control Plane API endpoint available"
    fi
    
    if [ -n "$app_endpoint" ] && [ "$app_endpoint" != "None" ]; then
        print_success "✅ Application Plane API endpoint available"
    fi
}

display_results() {
    echo ""
    echo "================================================================="
    print_success "🎉 Advanced Usage Insights Agent deployed successfully!"
    echo "================================================================="
    echo ""
    echo "📋 Deployment Summary:"
    echo "----------------------"
    echo "AWS Account: $AWS_ACCOUNT_ID"
    echo "AWS Region: $AWS_REGION"
    echo ""
    echo "🤖 Bedrock Agent (Created by CDK):"
    echo "Agent ID: ${BEDROCK_AGENT_ID:-'Check CDK outputs'}"
    echo "Alias ID: ${BEDROCK_AGENT_ALIAS_ID:-'Check CDK outputs'}"
    echo "Model: Claude 3 Haiku (anthropic.claude-3-haiku-20240307-v1:0)"
    echo "Tool Lambdas: 5 functions (ttv, cltv, feature_adoption, engagement, at_risk)"
    echo ""
    
    # Get API endpoints
    local control_endpoint=$(aws cloudformation describe-stacks \
        --stack-name AgenticInsightsUsageInsightsAgent \
        --query "Stacks[0].Outputs[?OutputKey=='ControlPlaneUsageInsightsEndpoint'].OutputValue" \
        --output text 2>/dev/null || echo "Not available")
    
    local app_endpoint=$(aws cloudformation describe-stacks \
        --stack-name AgenticInsightsUsageInsightsAgent \
        --query "Stacks[0].Outputs[?OutputKey=='AppPlaneUsageInsightsEndpoint'].OutputValue" \
        --output text 2>/dev/null || echo "Not available")
    
    echo "🔗 API Endpoints:"
    echo "Control Plane (Platform Admin): $control_endpoint"
    echo "Application Plane (Tenant Users): $app_endpoint"
    echo ""
    echo "🔒 Security:"
    echo "Application Plane: Lambda Authorizer ENABLED (JWT required)"
    echo "Control Plane: No Authorizer (open for testing)"
    echo ""
    echo "🔧 Analysis Tools:"
    echo "• calculate_time_to_value - Calculate TTV metrics for tenants"
    echo "• project_customer_lifetime_value - Project CLTV based on usage patterns"
    echo "• analyze_feature_adoption_rates - Analyze feature adoption across tenants"
    echo "• calculate_engagement_scores - Calculate user engagement scores"
    echo "• identify_at_risk_features - Identify features with declining usage"
    echo ""
    echo "📊 Data Sources Connected:"
    echo "• Usage Metrics Table: $USAGE_METRICS_TABLE_NAME"
    echo "• Tenants Table: $TENANTS_TABLE_NAME"
    echo "• Role-based access control (platform_admin, tenant_admin, tenant_user)"
    echo ""
    echo "✨ Features Deployed:"
    echo "• Advanced usage analytics with AI insights"
    echo "• Time to Value (TTV) calculation"
    echo "• Customer Lifetime Value (CLTV) projections"
    echo "• Feature adoption rate analysis"
    echo "• User engagement scoring"
    echo "• At-risk feature identification"
    echo ""
    echo "📚 Next Steps:"
    echo "1. Test the usage insights feature in the admin panel and SaaS app"
    echo "2. Verify role-based access control works correctly"
    echo "3. Check CloudWatch logs for agent invocations and debugging"
    echo "4. Monitor Bedrock agent costs in the AWS Billing console"
    echo ""
    echo "🧪 Testing Commands:"
    if [ "$control_endpoint" != "Not available" ]; then
        echo "# Platform Admin (Control Plane):"
        echo "curl -X POST $control_endpoint \\"
        echo "  -H 'Content-Type: application/json' \\"
        echo "  -d '{\"analysis_type\":\"time_to_value\",\"tenant_id\":\"all\"}'"
        echo ""
    fi
    if [ "$app_endpoint" != "Not available" ]; then
        echo "# Tenant User (Application Plane - Requires JWT Token):"
        echo "curl -X POST $app_endpoint \\"
        echo "  -H 'Authorization: Bearer \$JWT_TOKEN' \\"
        echo "  -H 'Content-Type: application/json' \\"
        echo "  -d '{\"analysis_type\":\"engagement_scores\"}'"
    fi
    echo ""
    echo "🗑️ To remove the Usage Insights feature:"
    echo "./scripts/lab3.3-rollback-usage-insights-agent.sh"
    echo "================================================================="
}

# Run main function
main "$@"
