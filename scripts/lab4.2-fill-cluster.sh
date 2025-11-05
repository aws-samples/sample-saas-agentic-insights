#!/bin/bash

# Lab 4.2: Fill DSQL Cluster with Churn Data
# Usage: ./lab4.2-fill-cluster.sh

set -e

echo "🚀 Lab 4.2: Filling DSQL Cluster with Churn Data..."

# Get current region
REGION=$(aws configure get region)

# Get DSQL cluster info from CloudFormation
STACK_OUTPUTS=$(aws cloudformation describe-stacks --stack-name AgenticInsightsChurnAgent --region $REGION --query 'Stacks[0].Outputs' --output json)
DSQL_CLUSTER_ID=$(echo $STACK_OUTPUTS | jq -r '.[] | select(.OutputKey=="DSQLClusterId") | .OutputValue')

echo "DSQL Cluster ID: $DSQL_CLUSTER_ID"

# Install required packages
pip install numpy pandas boto3 psycopg2-binary python-dateutil tqdm

# Generate and load data using merged script
python3 "$SCRIPT_DIR/lab4-fill-data.py" \
    --cluster-id "$DSQL_CLUSTER_ID" \
    --region "$REGION" \
    --num-tenants 100000 \
    --seed 42 \
    --drop-existing
    
echo "✅ Successfully filled DSQL cluster with churn data!"
