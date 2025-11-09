#!/bin/bash

# Update Usage Insights Agent System Prompt
# This script updates ONLY the system prompt for the existing Usage Insights Agent
# without redeploying the entire stack. Use this for incremental prompt changes.
# Usage: ./scripts/lab3.4-update-usage-insights-system-prompt.sh

set -e  # Exit on any error

echo "🔄 Updating Usage Insights Agent System Prompt..."
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
NEW_VERSION=""
SYSTEM_PROMPT=""

# Main update function
main() {
    echo "🔄 Starting system prompt update..."
    echo "===================================="

    # Step 1: Prerequisites check
    check_prerequisites

    # Step 2: Get AWS context
    get_aws_context

    # Step 3: Get existing agent information
    get_existing_agent

    # Step 4: Load and validate system prompt
    load_system_prompt

    # Step 5: Update agent DRAFT with new system prompt
    update_agent_draft

    # Step 6: Prepare the agent DRAFT
    prepare_agent_draft

    # Step 7: Wait for agent preparation
    wait_for_preparation

    # Step 8: Update alias - create new version and associate it
    update_alias_and_create_version

    # Step 9: Display results
    display_results
}

check_prerequisites() {
    print_status "Checking prerequisites..."

    # Check AWS CLI
    if ! command -v aws &> /dev/null; then
        print_error "AWS CLI not found. Please install AWS CLI."
        exit 1
    fi

    # Check AWS credentials
    if ! command -v aws sts get-caller-identity &> /dev/null; then
        print_error "AWS credentials not configured. Please run 'aws configure'."
        exit 1
    fi

    # Check Bedrock CLI access
    if ! command -v aws bedrock-agent list-agents --max-results 1 &> /dev/null; then
        print_error "AWS Bedrock Agent access not available. Please ensure you have proper permissions."
        exit 1
    fi

    # Check system prompt file exists
    if [ ! -f "src/control-plane/agents/usage-insights/prompts/system_prompt.txt" ]; then
        print_error "System prompt file not found: src/control-plane/agents/usage-insights/prompts/system_prompt.txt"
        exit 1
    fi

    print_success "Prerequisites check completed"
}

get_aws_context() {
    print_status "Getting AWS context..."

    AWS_REGION=$(aws configure get region)
    AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

    if [ -z "$AWS_REGION" ]; then
        print_error "AWS region is not set. Please configure your AWS region."
        exit 1
    fi

    print_status "Using AWS Account: $AWS_ACCOUNT_ID in Region: $AWS_REGION"
}

get_existing_agent() {
    print_status "Retrieving existing agent information..."

    # Try to get agent ID from CDK stack first
    BEDROCK_AGENT_ID=$(aws cloudformation describe-stacks \
        --stack-name AgenticInsightsUsageInsightsAgent \
        --query "Stacks[0].Outputs[?OutputKey=='BedrockAgentId'].OutputValue" \
        --output text 2>/dev/null || echo "")

    # If not found in stack, try to find by name
    if [ -z "$BEDROCK_AGENT_ID" ] || [ "$BEDROCK_AGENT_ID" = "None" ]; then
        print_warning "Agent ID not found in CDK stack, searching by name..."
        BEDROCK_AGENT_ID=$(aws bedrock-agent list-agents \
            --query "agentSummaries[?agentName=='usage-insights-agent'] | [0].agentId" \
            --output text 2>/dev/null || echo "")
    fi

    if [ -z "$BEDROCK_AGENT_ID" ] || [ "$BEDROCK_AGENT_ID" = "None" ]; then
        print_error "Could not find Usage Insights Agent. Please deploy it first using lab3.1-deploy-usage-insights-agent.sh"
        exit 1
    fi

    # Get agent alias ID
    BEDROCK_AGENT_ALIAS_ID=$(aws cloudformation describe-stacks \
        --stack-name AgenticInsightsUsageInsightsAgent \
        --query "Stacks[0].Outputs[?OutputKey=='BedrockAgentAliasId'].OutputValue" \
        --output text 2>/dev/null || echo "")

    # If not found in stack, try to find 'prod' alias
    if [ -z "$BEDROCK_AGENT_ALIAS_ID" ] || [ "$BEDROCK_AGENT_ALIAS_ID" = "None" ]; then
        print_warning "Alias ID not found in CDK stack, searching for 'prod' alias..."
        BEDROCK_AGENT_ALIAS_ID=$(aws bedrock-agent list-agent-aliases \
            --agent-id "$BEDROCK_AGENT_ID" \
            --query "agentAliasSummaries[?agentAliasName=='prod'] | [0].agentAliasId" \
            --output text 2>/dev/null || echo "")
    fi

    print_success "Found existing agent:"
    print_status "  Agent ID: $BEDROCK_AGENT_ID"
    if [ -n "$BEDROCK_AGENT_ALIAS_ID" ] && [ "$BEDROCK_AGENT_ALIAS_ID" != "None" ]; then
        print_status "  Alias ID: $BEDROCK_AGENT_ALIAS_ID"
    fi

    # Show current versions
    local current_versions=$(aws bedrock-agent list-agent-versions \
        --agent-id "$BEDROCK_AGENT_ID" \
        --max-results 50 \
        --query 'agentVersionSummaries[].agentVersion' \
        --output text 2>/dev/null | tr '\t' '\n' | grep -E '^[0-9]+$' | sort -n | tr '\n' ',' | sed 's/,$//')

    if [ -n "$current_versions" ]; then
        print_status "  Current versions: $current_versions"
    fi
}

load_system_prompt() {
    print_status "Loading system prompt from file..."

    local prompt_file="src/control-plane/agents/usage-insights/prompts/system_prompt.txt"

    if [ ! -f "$prompt_file" ]; then
        print_error "System prompt file not found: $prompt_file"
        exit 1
    fi

    # Read the system prompt
    SYSTEM_PROMPT=$(cat "$prompt_file")

    if [ -z "$SYSTEM_PROMPT" ]; then
        print_error "System prompt is empty"
        exit 1
    fi

    local prompt_length=${#SYSTEM_PROMPT}
    print_success "System prompt loaded successfully (${prompt_length} characters)"
}

update_agent_draft() {
    print_status "Updating agent DRAFT with new system prompt..."

    # Get current agent details
    local agent_info=$(aws bedrock-agent get-agent \
        --agent-id "$BEDROCK_AGENT_ID" \
        --output json 2>/dev/null)

    if [ $? -ne 0 ]; then
        print_error "Failed to retrieve current agent details"
        exit 1
    fi

    # Extract current configuration
    local agent_name=$(echo "$agent_info" | grep -o '"agentName"[[:space:]]*:[[:space:]]*"[^"]*"' | sed 's/.*"agentName"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/')
    local foundation_model=$(echo "$agent_info" | grep -o '"foundationModel"[[:space:]]*:[[:space:]]*"[^"]*"' | sed 's/.*"foundationModel"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/')
    local agent_role_arn=$(echo "$agent_info" | grep -o '"agentResourceRoleArn"[[:space:]]*:[[:space:]]*"[^"]*"' | sed 's/.*"agentResourceRoleArn"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/')

    # Update agent with new system prompt
    aws bedrock-agent update-agent \
        --agent-id "$BEDROCK_AGENT_ID" \
        --agent-name "$agent_name" \
        --foundation-model "$foundation_model" \
        --description "AI agent for advanced usage analytics including TTV, CLTV, engagement, and at-risk feature identification" \
        --instruction "$SYSTEM_PROMPT" \
        --agent-resource-role-arn "$agent_role_arn" \
        --idle-session-ttl-in-seconds 900 \
        > /dev/null 2>&1

    if [ $? -eq 0 ]; then
        print_success "Agent DRAFT updated with new system prompt"
    else
        print_error "Failed to update agent DRAFT"
        exit 1
    fi
}

prepare_agent_draft() {
    print_status "Preparing agent DRAFT..."

    aws bedrock-agent prepare-agent \
        --agent-id "$BEDROCK_AGENT_ID" \
        > /dev/null 2>&1

    if [ $? -eq 0 ]; then
        print_success "Agent DRAFT preparation initiated"
    else
        print_error "Failed to initiate agent preparation"
        exit 1
    fi
}

wait_for_preparation() {
    print_status "Waiting for agent DRAFT to be prepared..."

    local max_attempts=30
    local attempt=1

    while [ $attempt -le $max_attempts ]; do
        local current_status=$(aws bedrock-agent get-agent \
            --agent-id "$BEDROCK_AGENT_ID" \
            --query 'agent.agentStatus' \
            --output text 2>/dev/null || echo "UNKNOWN")

        if [ "$current_status" = "PREPARED" ]; then
            print_success "✅ Agent DRAFT is prepared!"
            return 0
        fi

        if [ "$current_status" = "FAILED" ]; then
            print_error "❌ Agent preparation failed"
            exit 1
        fi

        print_status "Agent status: $current_status (attempt $attempt/$max_attempts)"
        sleep 10
        ((attempt++))
    done

    print_error "⚠️ Timeout waiting for agent preparation"
    exit 1
}

update_alias_and_create_version() {
    if [ -z "$BEDROCK_AGENT_ALIAS_ID" ] || [ "$BEDROCK_AGENT_ALIAS_ID" = "None" ]; then
        print_warning "No agent alias found, skipping alias update"
        return 0
    fi

    print_status "Determining next version number..."

    # Get current versions
    local all_versions=$(aws bedrock-agent list-agent-versions \
        --agent-id "$BEDROCK_AGENT_ID" \
        --max-results 50 \
        --query 'agentVersionSummaries[].agentVersion' \
        --output text 2>/dev/null | tr '\t' '\n' | grep -E '^[0-9]+$' | sort -n)

    local current_max_version=0
    if [ -n "$all_versions" ]; then
        current_max_version=$(echo "$all_versions" | tail -1)
        print_status "Current versions: $(echo "$all_versions" | tr '\n' ',' | sed 's/,$//')"
        print_status "Current max version: $current_max_version"
    else
        print_status "No existing versions found"
    fi

    # Calculate next version
    NEW_VERSION=$((current_max_version + 1))
    print_status "Next version will be: v$NEW_VERSION"

    # Update alias without routing configuration - this should trigger version creation implicitly
    print_status "Updating alias (triggering implicit version creation)..."
    local update_result=$(aws bedrock-agent update-agent-alias \
        --agent-id "$BEDROCK_AGENT_ID" \
        --agent-alias-id "$BEDROCK_AGENT_ALIAS_ID" \
        --agent-alias-name "prod" \
        --output json 2>&1)

    if [ $? -eq 0 ]; then
        print_success "✅ Alias update initiated (implicit version creation)"

        # Wait for VERSIONING status - agent is creating the new version
        print_status "Waiting for version creation (VERSIONING status)..."
        local max_attempts=30
        local attempt=1
        local seen_versioning=false

        while [ $attempt -le $max_attempts ]; do
            local current_status=$(aws bedrock-agent get-agent \
                --agent-id "$BEDROCK_AGENT_ID" \
                --query 'agent.agentStatus' \
                --output text 2>/dev/null || echo "UNKNOWN")

            print_status "Agent status: $current_status (attempt $attempt/$max_attempts)"

            if [ "$current_status" = "VERSIONING" ]; then
                print_success "✅ Agent is creating new version from DRAFT..."
                seen_versioning=true
            fi

            if [ "$current_status" = "PREPARED" ] && [ "$seen_versioning" = true ]; then
                print_success "✅ Version created and agent is prepared!"
                break
            fi

            if [ "$current_status" = "FAILED" ]; then
                print_error "❌ Version creation failed"
                exit 1
            fi

            sleep 10
            ((attempt++))
        done

        if [ $attempt -gt $max_attempts ]; then
            print_warning "⚠️ Timeout waiting for version creation"
        fi

        # Get the newly created version number
        print_status "Determining newly created version..."
        local new_all_versions=$(aws bedrock-agent list-agent-versions \
            --agent-id "$BEDROCK_AGENT_ID" \
            --max-results 50 \
            --query 'agentVersionSummaries[].agentVersion' \
            --output text 2>/dev/null | tr '\t' '\n' | grep -E '^[0-9]+$' | sort -n)

        local new_max_version=0
        if [ -n "$new_all_versions" ]; then
            new_max_version=$(echo "$new_all_versions" | tail -1)
            NEW_VERSION=$new_max_version
            print_success "✅ New version created: v$NEW_VERSION"
            print_status "All versions: $(echo "$new_all_versions" | tr '\n' ',' | sed 's/,$//')"
        else
            print_error "❌ Could not determine new version number"
            exit 1
        fi

        # Verify alias configuration
        print_status "Verifying alias configuration..."
        local alias_info=$(aws bedrock-agent get-agent-alias \
            --agent-id "$BEDROCK_AGENT_ID" \
            --agent-alias-id "$BEDROCK_AGENT_ALIAS_ID" \
            --output json 2>/dev/null)

        local alias_version=$(echo "$alias_info" | grep -o '"agentVersion"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed 's/.*":\s*"\([^"]*\)".*/\1/')
        local alias_status=$(echo "$alias_info" | grep -o '"agentAliasStatus"[[:space:]]*:[[:space:]]*"[^"]*"' | sed 's/.*"agentAliasStatus"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/')

        print_status "Alias status: $alias_status"
        print_status "Alias pointing to: $alias_version"

        if [ "$alias_status" = "PREPARED" ]; then
            print_success "✅ Alias is ready (pointing to: $alias_version)"
        else
            print_warning "⚠️ Alias status: $alias_status, pointing to: $alias_version"
        fi
    else
        print_error "Failed to update alias"
        print_error "Error: $update_result"
        exit 1
    fi
}

display_results() {
    echo ""
    echo "================================================================="
    print_success "🎉 System prompt updated successfully!"
    echo "================================================================="
    echo ""
    echo "📋 Update Summary:"
    echo "------------------"
    echo "AWS Account: $AWS_ACCOUNT_ID"
    echo "AWS Region: $AWS_REGION"
    echo ""
    echo "🤖 Updated Agent:"
    echo "Agent ID: $BEDROCK_AGENT_ID"
    if [ -n "$NEW_VERSION" ]; then
        echo "New Version: v$NEW_VERSION"
    fi
    if [ -n "$BEDROCK_AGENT_ALIAS_ID" ] && [ "$BEDROCK_AGENT_ALIAS_ID" != "None" ]; then
        echo "Alias ID: $BEDROCK_AGENT_ALIAS_ID"
    fi
    echo ""
    echo "📝 Changes Applied:"
    echo "• System prompt updated in DRAFT"
    echo "• DRAFT prepared successfully"
    echo "• Alias updated - new version v$NEW_VERSION created automatically"
    echo "• No infrastructure changes (incremental update only)"
    echo ""
    echo "ℹ️  How it works:"
    echo "• update-agent: Updates the mutable DRAFT"
    echo "• prepare-agent: Prepares DRAFT for use"
    echo "• update-agent-alias to DRAFT: Creates immutable version snapshot"
    echo "• Each run increments: v1 → v2 → v3 → etc."
    echo ""
    echo "⚡ What's NOT changed:"
    echo "• Lambda functions (tools remain the same)"
    echo "• API endpoints (no redeployment needed)"
    echo "• Database tables (data unchanged)"
    echo "• IAM roles and permissions"
    echo ""
    echo "✨ The agent is now using the updated system prompt!"
    echo ""
    echo "🔄 To update the prompt again:"
    echo "./scripts/lab3.4-update-usage-insights-system-prompt.sh"
    echo "================================================================="
}

# Run main function
main "$@"
