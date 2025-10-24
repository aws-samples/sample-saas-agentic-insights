#!/bin/bash

# Agentic Insights SaaS - Cleanup Script
# This script removes the complete multi-tenant e-commerce SaaS platform

set -e  # Exit on any error

echo "🗑️  Starting cleanup of Agentic Insights SaaS Platform..."
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

# Confirmation prompt
echo "⚠️  WARNING: This will permanently delete all resources including:"
echo "   - All Lambda functions"
echo "   - All DynamoDB tables and data"
echo "   - All Cognito User Pools and users"
echo "   - All S3 buckets and web content"
echo "   - All CloudFront distributions"
echo "   - All API Gateways"
echo "   - All EventBridge rules and buses"
echo "   - All IAM roles and policies"
echo
read -p "Are you absolutely sure you want to continue? (type 'DELETE' to confirm): " CONFIRMATION

if [ "$CONFIRMATION" != "DELETE" ]; then
    print_status "Cleanup cancelled."
    exit 0
fi

# Check prerequisites
print_status "Checking prerequisites..."

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    print_error "AWS CLI is not installed."
    exit 1
fi

# Check if CDK is installed
if ! command -v cdk &> /dev/null; then
    print_error "AWS CDK is not installed."
    exit 1
fi

# Check AWS credentials
if ! aws sts get-caller-identity &> /dev/null; then
    print_error "AWS credentials not configured."
    exit 1
fi

# Get AWS account and region
AWS_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION=$(aws configure get region)

if [ -z "$AWS_REGION" ]; then
    print_error "AWS region is not set. Please configure your AWS region:"
    echo "  aws configure set region <region_name>"
    echo "  or export AWS_DEFAULT_REGION=<region_name>"
    exit 1
fi

print_status "Cleaning up from AWS Account: $AWS_ACCOUNT in Region: $AWS_REGION"

# Navigate to project root
cd "$(dirname "$0")/.."

# Function to delete stack with retry
delete_stack_with_retry() {
    local stack_name=$1
    local max_attempts=3
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        print_status "Attempting to delete $stack_name (attempt $attempt/$max_attempts)..."
        
        if cdk destroy $stack_name --force 2>/dev/null; then
            print_success "$stack_name deleted successfully"
            return 0
        else
            print_warning "Failed to delete $stack_name on attempt $attempt"
            if [ $attempt -lt $max_attempts ]; then
                print_status "Waiting 30 seconds before retry..."
                sleep 30
            fi
            ((attempt++))
        fi
    done
    
    print_error "Failed to delete $stack_name after $max_attempts attempts"
    return 1
}

# Function to empty and delete S3 buckets
cleanup_s3_buckets() {
    print_status "Cleaning up S3 buckets..."
    
    # Get bucket names from CloudFormation outputs
    local buckets=(
        "agentic-insights-landing-${AWS_ACCOUNT}-${AWS_REGION}"
        "agentic-insights-admin-${AWS_ACCOUNT}-${AWS_REGION}"
        "agentic-insights-saas-${AWS_ACCOUNT}-${AWS_REGION}"
    )
    
    for bucket in "${buckets[@]}"; do
        if aws s3api head-bucket --bucket "$bucket" 2>/dev/null; then
            print_status "Emptying S3 bucket: $bucket"
            aws s3 rm "s3://$bucket" --recursive 2>/dev/null || true
            
            # Delete all versions and delete markers (for versioned buckets)
            aws s3api list-object-versions --bucket "$bucket" --query 'Versions[].{Key:Key,VersionId:VersionId}' --output text 2>/dev/null | while read key version; do
                if [ -n "$key" ] && [ -n "$version" ]; then
                    aws s3api delete-object --bucket "$bucket" --key "$key" --version-id "$version" 2>/dev/null || true
                fi
            done
            
            aws s3api list-object-versions --bucket "$bucket" --query 'DeleteMarkers[].{Key:Key,VersionId:VersionId}' --output text 2>/dev/null | while read key version; do
                if [ -n "$key" ] && [ -n "$version" ]; then
                    aws s3api delete-object --bucket "$bucket" --key "$key" --version-id "$version" 2>/dev/null || true
                fi
            done
            
            print_success "S3 bucket $bucket emptied"
        fi
    done
}

# Function to delete premium tenant DynamoDB tables
cleanup_premium_tables() {
    print_status "Cleaning up premium tenant DynamoDB tables..."
    
    # List all tables that match the premium tenant pattern
    aws dynamodb list-tables --query 'TableNames[?starts_with(@, `Orders-`)]' --output text 2>/dev/null | while read table; do
        if [ -n "$table" ]; then
            print_status "Deleting premium tenant table: $table"
            aws dynamodb delete-table --table-name "$table" 2>/dev/null || true
        fi
    done
}

# Start cleanup process
print_status "Starting cleanup process..."

# Clean up S3 buckets first (they need to be empty before stack deletion)
cleanup_s3_buckets

# Clean up premium tenant tables
cleanup_premium_tables

# Delete Application Plane Stack first (it depends on Control Plane)
if aws cloudformation describe-stacks --stack-name AgenticInsightsAppPlane &>/dev/null; then
    delete_stack_with_retry "AgenticInsightsAppPlane"
else
    print_warning "Application Plane stack not found or already deleted"
fi

# Delete Control Plane Stack
if aws cloudformation describe-stacks --stack-name AgenticInsightsControlPlane &>/dev/null; then
    delete_stack_with_retry "AgenticInsightsControlPlane"
else
    print_warning "Control Plane stack not found or already deleted"
fi

# Clean up any remaining resources that might not have been deleted
print_status "Cleaning up any remaining resources..."

# Wait a bit for resources to be fully deleted
sleep 10

# Check for any remaining premium tenant tables
cleanup_premium_tables

# Clean up CDK bootstrap resources (optional)
read -p "Do you want to delete CDK bootstrap resources? This will affect other CDK projects in this account/region. (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_status "Cleaning up CDK bootstrap resources..."
    
    # Delete CDK bootstrap stack
    aws cloudformation delete-stack --stack-name CDKToolkit --region "$AWS_REGION" 2>/dev/null || true
    
    # Delete CDK bootstrap bucket
    CDK_BUCKET="cdk-hnb659fds-assets-${AWS_ACCOUNT}-${AWS_REGION}"
    if aws s3api head-bucket --bucket "$CDK_BUCKET" 2>/dev/null; then
        print_status "Emptying CDK bootstrap bucket..."
        aws s3 rm "s3://$CDK_BUCKET" --recursive 2>/dev/null || true
    fi
    
    print_success "CDK bootstrap resources cleaned up"
fi

# Final verification
print_status "Verifying cleanup..."

# Check if stacks still exist
if aws cloudformation describe-stacks --stack-name AgenticInsightsControlPlane &>/dev/null; then
    print_warning "Control Plane stack still exists"
fi

if aws cloudformation describe-stacks --stack-name AgenticInsightsAppPlane &>/dev/null; then
    print_warning "Application Plane stack still exists"
fi

# Display cleanup summary
echo
echo "=================================================="
print_success "🧹 Cleanup completed!"
echo "=================================================="
echo
echo "📋 Cleanup Summary:"
echo "-------------------"
echo "AWS Account: $AWS_ACCOUNT"
echo "AWS Region: $AWS_REGION"
echo
echo "✅ Resources Removed:"
echo "   - Control Plane Stack (Lambda, DynamoDB, EventBridge, Cognito)"
echo "   - Application Plane Stack (Lambda, DynamoDB, API Gateway, Cognito)"
echo "   - S3 Buckets and web content"
echo "   - CloudFront distributions"
echo "   - Premium tenant DynamoDB tables"
echo "   - All associated IAM roles and policies"
echo
echo "⚠️  Note: Some resources may take a few minutes to be fully deleted."
echo "   You can check the CloudFormation console to monitor the deletion progress."
echo
echo "🔄 To redeploy the solution, run: ./scripts/lab1.1-deploy-base-architecture.sh"
echo "=================================================="
