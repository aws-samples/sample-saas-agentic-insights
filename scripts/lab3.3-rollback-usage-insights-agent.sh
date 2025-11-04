#!/bin/bash

# Rollback Advanced Usage Insights Agent
# This script removes the Usage Insights Agent deployment
# Usage: ./scripts/lab-05.2-rollback-usage-insights-agent.sh

set -e  # Exit on any error

echo "🗑️ Rolling back Advanced Usage Insights Agent..."
echo "================================================"

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

# Main rollback function
main() {
    echo "🔄 Starting rollback of Usage Insights Agent..."
    echo "==============================================="
    
    # Step 1: Get AWS context
    get_aws_context
    
    # Step 2: Confirm rollback
    confirm_rollback
    
    # Step 3: Destroy CDK stack
    destroy_cdk_stack
    
    # Step 4: Delete Bedrock agent (optional)
    delete_bedrock_agent
    
    # Step 5: Delete IAM role (optional)
    delete_iam_role
    
    # Step 6: Display results
    display_results
}

get_aws_context() {
    print_status "Getting AWS context..."
    
    # Check AWS CLI
    if ! command -v aws &> /dev/null; then
        print_error "AWS CLI not found. Please install AWS CLI."
        exit 1
    fi
    
    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        print_error "AWS credentials not configured. Please run 'aws configure'."
        exit 1
    fi
    
    AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    AWS_REGION=$(aws configure get region)
    
    if [ -z "$AWS_REGION" ]; then
        print_error "AWS region is not set. Please configure your AWS region."
        exit 1
    fi
    
    print_status "AWS Account: $AWS_ACCOUNT_ID"
    print_status "AWS Region: $AWS_REGION"
}

confirm_rollback() {
    echo ""
    print_warning "⚠️  WARNING: This will remove the following resources:"
    echo "  • CDK Stack: AgenticInsightsUsageInsights"
    echo "  • Lambda function and API Gateway endpoints"
    echo "  • Bedrock agent: usage-insights-agent (optional)"
    echo "  • IAM role: UsageInsightsBedrockAgentRole (optional)"
    echo ""
    print_warning "This action cannot be undone!"
    echo ""
    read -p "Are you sure you want to continue? (yes/no): " confirm
    
    if [ "$confirm" != "yes" ]; then
        print_status "Rollback cancelled by user"
        exit 0
    fi
    
    print_success "Rollback confirmed"
}

destroy_cdk_stack() {
    print_status "Destroying CDK stack..."
    
    # Check if stack exists
    if ! aws cloudformation describe-stacks --stack-name AgenticInsightsUsageInsights &> /dev/null; then
        print_warning "CDK stack 'AgenticInsightsUsageInsights' not found, skipping..."
        return
    fi
    
    # Check CDK
    if ! command -v cdk &> /dev/null; then
        print_error "AWS CDK not found. Please install AWS CDK to destroy the stack."
        print_status "Alternatively, delete the stack manually from AWS CloudFormation console."
        exit 1
    fi
    
    # Destroy stack
    print_status "Running: cdk destroy AgenticInsightsUsageInsights"
    cdk destroy AgenticInsightsUsageInsights --force
    
    if [ $? -eq 0 ]; then
        print_success "CDK stack destroyed successfully"
    else
        print_error "Failed to destroy CDK stack"
        print_status "You may need to delete the stack manually from AWS CloudFormation console"
        exit 1
    fi
}

delete_bedrock_agent() {
    echo ""
    print_status "Checking for Bedrock agent..."
    
    # Find agent ID
    BEDROCK_AGENT_ID=$(aws bedrock-agent list-agents \
        --query "agentSummaries[?agentName=='usage-insights-agent'] | [0].agentId" \
        --output text 2>/dev/null || echo "")
    
    if [ -z "$BEDROCK_AGENT_ID" ] || [ "$BEDROCK_AGENT_ID" = "None" ] || [ "$BEDROCK_AGENT_ID" = "null" ]; then
        print_warning "Bedrock agent 'usage-insights-agent' not found, skipping..."
        return
    fi
    
    print_status "Found Bedrock agent: $BEDROCK_AGENT_ID"
    echo ""
    read -p "Do you want to delete the Bedrock agent? (yes/no): " delete_agent
    
    if [ "$delete_agent" != "yes" ]; then
        print_status "Keeping Bedrock agent (you can delete it manually later)"
        print_status "To delete manually: aws bedrock-agent delete-agent --agent-id $BEDROCK_AGENT_ID"
        return
    fi
    
    print_status "Deleting Bedrock agent..."
    
    # Delete all agent aliases first
    local aliases=$(aws bedrock-agent list-agent-aliases \
        --agent-id "$BEDROCK_AGENT_ID" \
        --query "agentAliasSummaries[].agentAliasId" \
        --output text 2>/dev/null || echo "")
    
    if [ -n "$aliases" ]; then
        for alias_id in $aliases; do
            print_status "Deleting agent alias: $alias_id"
            aws bedrock-agent delete-agent-alias \
                --agent-id "$BEDROCK_AGENT_ID" \
                --agent-alias-id "$alias_id" > /dev/null 2>&1 || true
        done
    fi
    
    # Delete the agent
    aws bedrock-agent delete-agent --agent-id "$BEDROCK_AGENT_ID" --skip-resource-in-use-check > /dev/null
    
    if [ $? -eq 0 ]; then
        print_success "Bedrock agent deleted successfully"
    else
        print_warning "Failed to delete Bedrock agent"
        print_status "You may need to delete it manually: aws bedrock-agent delete-agent --agent-id $BEDROCK_AGENT_ID"
    fi
}

delete_iam_role() {
    echo ""
    print_status "Checking for IAM role..."
    
    local role_name="UsageInsightsBedrockAgentRole"
    
    # Check if role exists
    if ! aws iam get-role --role-name "$role_name" &> /dev/null; then
        print_warning "IAM role '$role_name' not found, skipping..."
        return
    fi
    
    print_status "Found IAM role: $role_name"
    echo ""
    read -p "Do you want to delete the IAM role? (yes/no): " delete_role
    
    if [ "$delete_role" != "yes" ]; then
        print_status "Keeping IAM role (you can delete it manually later)"
        print_status "To delete manually:"
        print_status "  aws iam detach-role-policy --role-name $role_name --policy-arn arn:aws:iam::aws:policy/AmazonBedrockFullAccess"
        print_status "  aws iam delete-role --role-name $role_name"
        return
    fi
    
    print_status "Deleting IAM role..."
    
    # Detach all policies
    local policies=$(aws iam list-attached-role-policies \
        --role-name "$role_name" \
        --query "AttachedPolicies[].PolicyArn" \
        --output text 2>/dev/null || echo "")
    
    if [ -n "$policies" ]; then
        for policy_arn in $policies; do
            print_status "Detaching policy: $policy_arn"
            aws iam detach-role-policy \
                --role-name "$role_name" \
                --policy-arn "$policy_arn" > /dev/null 2>&1 || true
        done
    fi
    
    # Delete the role
    aws iam delete-role --role-name "$role_name" > /dev/null
    
    if [ $? -eq 0 ]; then
        print_success "IAM role deleted successfully"
    else
        print_warning "Failed to delete IAM role"
        print_status "You may need to delete it manually from the IAM console"
    fi
}

display_results() {
    echo ""
    echo "================================================================="
    print_success "✅ Rollback completed!"
    echo "================================================================="
    echo ""
    echo "📋 Rollback Summary:"
    echo "--------------------"
    echo "• CDK Stack: Destroyed"
    echo "• Lambda function: Removed"
    echo "• API Gateway endpoints: Removed"
    
    if [ -n "$BEDROCK_AGENT_ID" ]; then
        echo "• Bedrock agent: Deleted (or kept based on your choice)"
    fi
    
    echo "• IAM role: Deleted (or kept based on your choice)"
    echo ""
    echo "📚 Manual Cleanup (if needed):"
    echo "-------------------------------"
    echo "If you chose to keep the Bedrock agent or IAM role, you can delete them manually:"
    echo ""
    
    if [ -n "$BEDROCK_AGENT_ID" ]; then
        echo "# Delete Bedrock agent:"
        echo "aws bedrock-agent delete-agent --agent-id $BEDROCK_AGENT_ID"
        echo ""
    fi
    
    echo "# Delete IAM role:"
    echo "aws iam detach-role-policy \\"
    echo "  --role-name UsageInsightsBedrockAgentRole \\"
    echo "  --policy-arn arn:aws:iam::aws:policy/AmazonBedrockFullAccess"
    echo "aws iam delete-role --role-name UsageInsightsBedrockAgentRole"
    echo ""
    echo "================================================================="
}

# Run main function
main "$@"
