#!/bin/bash

# Deploy Test Agent
# This script deploys the test agent and updates the insight dashboard API with agent IDs

set -e

echo "🤖 Deploying Test Agent..."
echo "================================"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

# Deploy test agent stack
print_status "Deploying test agent stack..."
cdk deploy AgenticInsightsTestAgent --require-approval never

# Get agent IDs from stack outputs
print_status "Retrieving agent IDs..."
TEST_AGENT_ID=$(aws cloudformation describe-stacks \
    --stack-name AgenticInsightsTestAgent \
    --query 'Stacks[0].Outputs[?OutputKey==`TestAgentId`].OutputValue' \
    --output text)

TEST_AGENT_ALIAS_ID=$(aws cloudformation describe-stacks \
    --stack-name AgenticInsightsTestAgent \
    --query 'Stacks[0].Outputs[?OutputKey==`TestAgentAliasId`].OutputValue' \
    --output text)

print_status "Test Agent ID: $TEST_AGENT_ID"
print_status "Test Agent Alias ID: $TEST_AGENT_ALIAS_ID"

# Get insight dashboard function name
INSIGHT_FUNCTION_NAME=$(aws cloudformation describe-stacks \
    --stack-name AgenticInsightsControlPlane \
    --query 'Stacks[0].Outputs[?contains(OutputKey, `InsightDashboard`) || contains(OutputValue, `InsightDashboard`)].OutputValue' \
    --output text)

# If not found by output, get by resource type
if [ -z "$INSIGHT_FUNCTION_NAME" ]; then
    INSIGHT_FUNCTION_NAME=$(aws cloudformation list-stack-resources \
        --stack-name AgenticInsightsControlPlane \
        --query 'StackResourceSummaries[?ResourceType==`AWS::Lambda::Function` && contains(LogicalResourceId, `InsightDashboard`)].PhysicalResourceId' \
        --output text)
fi

print_status "Updating insight dashboard function: $INSIGHT_FUNCTION_NAME"

# Update Lambda environment variables
aws lambda update-function-configuration \
    --function-name "$INSIGHT_FUNCTION_NAME" \
    --environment "Variables={TEST_AGENT_ID=$TEST_AGENT_ID,TEST_AGENT_ALIAS_ID=$TEST_AGENT_ALIAS_ID}" \
    --no-cli-pager

print_success "Test agent deployed and configured successfully!"
print_status "You can now test with analysis_type='simple-cost-analysis'"
