#!/bin/bash

echo "Loading environment variables from .env file..."
# Load environment variables from .env file
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
    echo "Loaded .env file"
else
    echo "No .env file found"
fi

echo "Getting AWS credentials from current environment..."
# For SSO/assumed role, credentials are already in environment
echo "AWS_ACCESS_KEY_ID: ${AWS_ACCESS_KEY_ID:0:10}..."
echo "AWS_DEFAULT_REGION: $AWS_DEFAULT_REGION"
echo "DSQL_CLUSTER_ID: $DSQL_CLUSTER_ID"
echo "S3_BUCKET: $S3_BUCKET"

echo "Launching agentcore..."
# Launch agentcore with environment variables
agentcore launch -l \
    --env DSQL_CLUSTER_ID="$DSQL_CLUSTER_ID" \
    --env DSQL_REGION="$DSQL_REGION" \
    --env DSQL_HOST="$DSQL_HOST" \
    --env DSQL_PORT="$DSQL_PORT" \
    --env DSQL_DATABASE="$DSQL_DATABASE" \
    --env DSQL_USERNAME="$DSQL_USERNAME" \
    --env S3_BUCKET="$S3_BUCKET" \
    --env AWS_ACCESS_KEY_ID="$AWS_ACCESS_KEY_ID" \
    --env AWS_SECRET_ACCESS_KEY="$AWS_SECRET_ACCESS_KEY" \
    --env AWS_SESSION_TOKEN="$AWS_SESSION_TOKEN" \
    --env AWS_DEFAULT_REGION="$AWS_DEFAULT_REGION"
