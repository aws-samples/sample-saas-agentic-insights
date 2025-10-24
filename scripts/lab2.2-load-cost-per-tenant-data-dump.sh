#!/bin/bash

# Lab 03.2: Load Cost Per Tenant Data Dump
# This script loads sample cost data into the CostPerTenantTable for testing
# Usage: ./lab2.2-load-cost-per-tenant-data-dump.sh

set -e  # Exit on any error

echo "📊 Lab 03.2: Loading Cost Per Tenant Data Dump..."
echo "================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Get AWS region and display it
AWS_REGION=$(aws configure get region 2>/dev/null || echo "us-east-1")
print_status "AWS Region: $AWS_REGION"

# Check prerequisites
print_status "Checking prerequisites..."

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    print_error "AWS CLI is not installed. Please install it first."
    exit 1
fi

# Check AWS credentials
if ! aws sts get-caller-identity &> /dev/null; then
    print_error "AWS credentials not configured. Please run 'aws configure' first."
    exit 1
fi

# Check if MetricsFramework stack exists
if ! aws cloudformation describe-stacks --stack-name AgenticInsightsMetricsFramework &> /dev/null; then
    print_error "MetricsFramework stack not found. Please run lab-02.1-metering-framework.sh first."
    exit 1
fi

print_success "Prerequisites check completed"

# Get AWS region
AWS_REGION=$(aws configure get region)
if [ -z "$AWS_REGION" ]; then
    print_error "AWS region is not set. Please configure your AWS region."
    exit 1
fi

# Navigate to project root
cd "$(dirname "$0")/.."

# Get CostPerTenant table name from stack outputs
print_status "Getting CostPerTenant table name..."
COST_TABLE_NAME=$(aws cloudformation describe-stacks \
    --stack-name AgenticInsightsMetricsFramework \
    --query 'Stacks[0].Outputs[?OutputKey==`CostPerTenantTableName`].OutputValue' \
    --output text 2>/dev/null)

if [ -z "$COST_TABLE_NAME" ]; then
    print_error "Could not find CostPerTenant table name in stack outputs."
    exit 1
fi

print_status "Found table: $COST_TABLE_NAME"

# Check if data dump file exists
DATA_FILE="scripts/lab2.2-cost-per-tenant-data-dump.json"
if [ ! -f "$DATA_FILE" ]; then
    print_error "Data dump file not found: $DATA_FILE"
    exit 1
fi

print_status "Loading data from: $DATA_FILE"

# Load data using AWS CLI batch-write-item
print_status "Loading cost data into DynamoDB table..."

# Convert JSON array to DynamoDB batch format
python3 -c "
import json
import sys

# Read the data file
with open('$DATA_FILE', 'r') as f:
    data = json.load(f)

# Convert to DynamoDB format
items = []
for item in data:
    ddb_item = {
        'tenant_id': {'S': item['tenant_id']},
        'month': {'S': item['month']},
        'cost': {'N': str(item['cost'])},
        'revenue': {'N': str(item['revenue'])},
        'margin': {'N': str(item['margin'])},
        'margin_percentage': {'N': str(item['margin_percentage'])},
        'tier': {'S': item['tier']}
    }
    items.append({'PutRequest': {'Item': ddb_item}})

# Split into batches of 25 (DynamoDB limit)
batch_size = 25
batches = [items[i:i + batch_size] for i in range(0, len(items), batch_size)]

print(f'Total items: {len(items)}')
print(f'Total batches: {len(batches)}')

for i, batch in enumerate(batches):
    batch_data = {
        '$COST_TABLE_NAME': batch
    }
    print(json.dumps(batch_data))
    print('---BATCH_SEPARATOR---')
" | while IFS= read -r line; do
    if [ "$line" = "---BATCH_SEPARATOR---" ]; then
        if [ -n "$batch_json" ]; then
            echo "$batch_json" > /tmp/batch.json
            aws dynamodb batch-write-item --request-items file:///tmp/batch.json --region "$AWS_REGION"
            print_status "Batch loaded successfully"
            batch_json=""
        fi
    elif [[ "$line" =~ ^(Total|Loading) ]]; then
        print_status "$line"
    else
        batch_json="$line"
    fi
done

# Handle the last batch if it exists
if [ -n "$batch_json" ]; then
    echo "$batch_json" > /tmp/batch.json
    aws dynamodb batch-write-item --request-items file:///tmp/batch.json --region "$AWS_REGION"
    print_status "Final batch loaded successfully"
fi

# Clean up temp file
rm -f /tmp/batch.json

# Verify data was loaded
print_status "Verifying data load..."
ITEM_COUNT=$(aws dynamodb scan --table-name "$COST_TABLE_NAME" --select COUNT --region "$AWS_REGION" --query 'Count' --output text)

print_success "Data load completed successfully!"
print_success "Total items in table: $ITEM_COUNT"

echo
echo "================================================="
print_success "🎉 Cost Per Tenant Data Dump loaded successfully!"
echo "================================================="
echo
echo "📋 Summary:"
echo "Table: $COST_TABLE_NAME"
echo "Items loaded: $ITEM_COUNT"
echo "Region: $AWS_REGION"
echo
echo "================================================="
