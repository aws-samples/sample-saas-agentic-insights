#!/bin/bash

# Deploy Cost Analysis Agent
# This script deploys the Cost Analysis Agent and updates the insight dashboard API with agent IDs

set -e

echo "🤖 Deploying Cost Analysis Agent..."
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

# Deploy Cost Analysis Agent stack
print_status "Deploying Cost Analysis Agent stack..."
cdk deploy AgenticInsightsCostAnalysisAgent --require-approval never

# Get agent IDs from stack outputs
print_status "Retrieving agent IDs..."
COST_ANALYSIS_AGENT_ID=$(aws cloudformation describe-stacks \
    --stack-name AgenticInsightsCostAnalysisAgent \
    --query 'Stacks[0].Outputs[?OutputKey==`CostAnalysisAgentId`].OutputValue' \
    --output text)

COST_ANALYSIS_AGENT_ALIAS_ID=$(aws cloudformation describe-stacks \
    --stack-name AgenticInsightsCostAnalysisAgent \
    --query 'Stacks[0].Outputs[?OutputKey==`CostAnalysisAgentAliasId`].OutputValue' \
    --output text)

print_status "Cost Analysis Agent ID: $COST_ANALYSIS_AGENT_ID"
print_status "Cost Analysis Agent Alias ID: $COST_ANALYSIS_AGENT_ALIAS_ID"

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
    --environment "Variables={COST_ANALYSIS_AGENT_ID=$COST_ANALYSIS_AGENT_ID,COST_ANALYSIS_AGENT_ALIAS_ID=$COST_ANALYSIS_AGENT_ALIAS_ID}" \
    --no-cli-pager

print_success "Cost Analysis Agent deployed and configured successfully!"
print_status "You can now use with analysis_type='simple-cost-analysis'"


# Test model access (may fail if access not yet granted)
print_status "Testing model access for US Claude Haiku 4.5..."
aws bedrock-runtime invoke-model \
  --model-id us.anthropic.claude-haiku-4-5-20251001-v1:0 \
  --body "$(echo '{
    "anthropic_version": "bedrock-2023-05-31",
    "max_tokens": 1000,
    "messages": [
      {
        "role": "user",
        "content": "Your message here"
      }
    ]
  }' | base64)" \
  --region us-east-1 \
  output_model_access_test.json 2>&1 && print_success "Model access confirmed" || print_status "Model access not yet granted (this is expected and can take up to 15 minutes)"

# Test model access (may fail if access not yet granted)
print_status "Testing model access for Global Claude Haiku 4.5..."
aws bedrock-runtime invoke-model \
  --model-id global.anthropic.claude-haiku-4-5-20251001-v1:0 \
  --body "$(echo '{
    "anthropic_version": "bedrock-2023-05-31",
    "max_tokens": 1000,
    "messages": [
      {
        "role": "user",
        "content": "Your message here"
      }
    ]
  }' | base64)" \
  --region us-east-1 \
  output_model_access_test.json 2>&1 && print_success "Model access confirmed" || print_status "Model access not yet granted (this is expected and can take up to 15 minutes)"

# Test model access (may fail if access not yet granted)
print_status "Testing model access for US Claude Sonnet 4.5..."
aws bedrock-runtime invoke-model \
  --model-id us.anthropic.claude-sonnet-4-5-20250929-v1:0 \
  --body "$(echo '{
    "anthropic_version": "bedrock-2023-05-31",
    "max_tokens": 1000,
    "messages": [
      {
        "role": "user",
        "content": "Your message here"
      }
    ]
  }' | base64)" \
  --region us-east-1 \
  output_model_access_test.json 2>&1 && print_success "Model access confirmed" || print_status "Model access not yet granted (this is expected and can take up to 15 minutes)"


# Test model access (may fail if access not yet granted)
print_status "Testing model access for Global Claude Sonnet 4.5..."
aws bedrock-runtime invoke-model \
  --model-id global.anthropic.claude-sonnet-4-5-20250929-v1:0 \
  --body "$(echo '{
    "anthropic_version": "bedrock-2023-05-31",
    "max_tokens": 1000,
    "messages": [
      {
        "role": "user",
        "content": "Your message here"
      }
    ]
  }' | base64)" \
  --region us-east-1 \
  output_model_access_test.json 2>&1 && print_success "Model access confirmed" || print_status "Model access not yet granted (this is expected and can take up to 15 minutes)"