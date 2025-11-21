#!/bin/bash

# Lab 4.1: Launch Churn Agent with AgentCore Runtime
# This script launches the churn agent using AgentCore Runtime
# Usage: ./lab4.1-launch-churn-agent.sh

set -e  # Exit on any error

echo "🚀 Lab 4.1: Launching Churn Agent..."
echo "===================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Get current region
REGION=$(aws configure get region)

# Get stack outputs
STACK_OUTPUTS=$(aws cloudformation describe-stacks --stack-name AgenticInsightsChurnAgent --region $REGION --query 'Stacks[0].Outputs' --output json)

DSQL_CLUSTER_ID=$(echo $STACK_OUTPUTS | jq -r '.[] | select(.OutputKey=="DSQLClusterId") | .OutputValue')
DSQL_ENDPOINT=$(echo $STACK_OUTPUTS | jq -r '.[] | select(.OutputKey=="DSQLEndpoint") | .OutputValue')

# Navigate to agent directory
cd "$(dirname "$0")/../src/control-plane/agents/churn-agent"

# Ensure PATH includes agentcore
export PATH="$HOME/.local/bin:$PATH"

# Deploy the agent
print_status "Deploying churn agent to AgentCore Runtime..."
set +e
LAUNCH_OUTPUT=$(agentcore launch \
    --agent "churn_agent" \
    --auto-update-on-conflict \
    --env "DSQL_CLUSTER_ID=$DSQL_CLUSTER_ID" \
    --env "DSQL_REGION=$REGION" \
    --env "DSQL_HOST=$DSQL_ENDPOINT" \
    --env "DSQL_PORT=5432" \
    --env "DSQL_DATABASE=postgres" \
    --env "DSQL_USERNAME=admin" \
    2>&1)
LAUNCH_EXIT_CODE=$?
set -e
echo "$LAUNCH_OUTPUT"

if [ $LAUNCH_EXIT_CODE -ne 0 ]; then
    print_error "AgentCore launch failed with exit code $LAUNCH_EXIT_CODE"
    exit 1
fi

# Extract agent ARN from output
AGENT_ARN=$(echo "$LAUNCH_OUTPUT" | grep -o 'arn:aws:bedrock-agentcore:[^[:space:]]*' | head -1)

if [ -z "$AGENT_ARN" ]; then
    print_error "Failed to extract agent ARN from launch output"
    exit 1
fi

print_success "AgentCore Runtime deployed: $AGENT_ARN"
