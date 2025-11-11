#!/bin/bash

# Lab 3.5: Update Usage Insights Service - Direct Lambda Deployment
# This script updates the Usage Insights Lambda function directly without CDK

set -e

echo "🔄 Updating Usage Insights Lambda Function..."
echo "=============================================="

# Get the Lambda function name
FUNCTION_NAME=$(aws lambda list-functions --query "Functions[?contains(FunctionName, 'usage-insights-function')].FunctionName" --output text)

if [ -z "$FUNCTION_NAME" ]; then
    echo "❌ Could not find Usage Insights Lambda function"
    exit 1
fi

echo "📍 Found function: $FUNCTION_NAME"

# Create temporary directory for deployment package
TEMP_DIR=$(mktemp -d)
echo "📦 Creating deployment package in: $TEMP_DIR"

# Copy the service file
cp src/control-plane/usage-insights-api/usage_insights_service.py "$TEMP_DIR/"

# Create the deployment zip
cd "$TEMP_DIR"
zip -q -r function.zip usage_insights_service.py

echo "🚀 Updating Lambda function code..."

# Update the Lambda function
aws lambda update-function-code \
    --function-name "$FUNCTION_NAME" \
    --zip-file fileb://function.zip > /dev/null

# Wait for update to complete
echo "⏳ Waiting for function update to complete..."
aws lambda wait function-updated --function-name "$FUNCTION_NAME"

# Clean up
cd - > /dev/null 2>&1
rm -rf "$TEMP_DIR"
echo ""
echo "🔍 Lambda Function: $FUNCTION_NAME"
echo "💡 Lambda function updated successfully!"
echo "✅ Usage Insights service is Ready"
echo ""
