#!/bin/bash

# Lab 01.1: Deploy Base Architecture
# This script deploys the foundational multi-tenant e-commerce SaaS platform
# Usage: ./lab-01.1-deploy-base-architecture.sh [--force]
#   --force: Force redeploy web apps even if configuration unchanged

set -e  # Exit on any error

echo "🚀 Lab 01.1: Deploying Base Architecture..."
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

# Check for force flag
FORCE_REDEPLOY=false
if [ "$1" = "--force" ]; then
    FORCE_REDEPLOY=true
    print_status "Force redeploy enabled"
fi

# Check prerequisites
print_status "Checking prerequisites..."

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    print_error "AWS CLI is not installed. Please install it first."
    exit 1
fi

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    print_error "Node.js is not installed. Please install it first."
    exit 1
fi

# Check if npm is installed
if ! command -v npm &> /dev/null; then
    print_error "npm is not installed. Please install it first."
    exit 1
fi

# Check if CDK is installed
if ! command -v cdk &> /dev/null; then
    print_error "AWS CDK is not installed. Installing it now..."
    npm install -g aws-cdk
fi

# Check AWS credentials
if ! aws sts get-caller-identity &> /dev/null; then
    print_error "AWS credentials not configured. Please run 'aws configure' first."
    exit 1
fi

print_success "Prerequisites check completed"

# Get AWS account and region
AWS_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION=$(aws configure get region)

if [ -z "$AWS_REGION" ]; then
    print_error "AWS region is not set. Please configure your AWS region:"
    echo "  aws configure set region <region_name>"
    echo "  or export AWS_DEFAULT_REGION=<region_name>"
    exit 1
fi

print_status "Deploying to AWS Account: $AWS_ACCOUNT in Region: $AWS_REGION"

# Navigate to project root
cd "$(dirname "$0")/.."

# Install dependencies
print_status "Installing dependencies..."
npm install

# Build TypeScript
print_status "Building TypeScript code..."
npm run build

# Bootstrap CDK (if needed)
print_status "Bootstrapping CDK environment..."
cdk bootstrap aws://$AWS_ACCOUNT/$AWS_REGION

# Deploy the stacks
print_status "Deploying Control Plane Stack..."
cdk deploy AgenticInsightsControlPlane --require-approval never

print_status "Deploying Application Plane Stack..."
cdk deploy AgenticInsightsAppPlane --require-approval never

# Get stack outputs
print_status "Retrieving deployment outputs..."

CONTROL_PLANE_API=$(aws cloudformation describe-stacks \
    --stack-name AgenticInsightsControlPlane \
    --query 'Stacks[0].Outputs[?OutputKey==`ControlPlaneApiUrl`].OutputValue' \
    --output text 2>/dev/null || echo "")
# Remove trailing slash
CONTROL_PLANE_API=${CONTROL_PLANE_API%/}

APP_PLANE_API=$(aws cloudformation describe-stacks \
    --stack-name AgenticInsightsAppPlane \
    --query 'Stacks[0].Outputs[?OutputKey==`AppPlaneApiUrl`].OutputValue' \
    --output text 2>/dev/null || echo "")
# Remove trailing slash
APP_PLANE_API=${APP_PLANE_API%/}

LANDING_PAGE_URL=$(aws cloudformation describe-stacks \
    --stack-name AgenticInsightsAppPlane \
    --query 'Stacks[0].Outputs[?OutputKey==`LandingPageUrl`].OutputValue' \
    --output text 2>/dev/null || echo "")

ADMIN_PANEL_URL=$(aws cloudformation describe-stacks \
    --stack-name AgenticInsightsAppPlane \
    --query 'Stacks[0].Outputs[?OutputKey==`AdminPanelUrl`].OutputValue' \
    --output text 2>/dev/null || echo "")

SAAS_APP_URL=$(aws cloudformation describe-stacks \
    --stack-name AgenticInsightsAppPlane \
    --query 'Stacks[0].Outputs[?OutputKey==`SaasAppUrl`].OutputValue' \
    --output text 2>/dev/null || echo "")

# Generate shared configuration file with change detection
generate_shared_config() {
    print_status "Checking configuration changes..."
    
    local config_file="web/shared/config.js"
    local temp_config="/tmp/new_config.js"
    
    # Generate new config in temp location
    cat > "$temp_config" << EOF
// Auto-generated configuration file
// This file is generated during deployment and should not be edited manually
window.APP_CONFIG = {
    CONTROL_PLANE_API_URL: '$CONTROL_PLANE_API',
    APP_PLANE_API_URL: '$APP_PLANE_API',
    SAAS_APP_URL: '$SAAS_APP_URL',
    ADMIN_PANEL_URL: '$ADMIN_PANEL_URL',
    LANDING_PAGE_URL: '$LANDING_PAGE_URL',
    REGION: '$AWS_REGION'
};
EOF

    # Check if config changed
    if [ ! -f "$config_file" ] || ! cmp -s "$config_file" "$temp_config"; then
        print_status "Configuration changed, updating web apps..."
        
        # Create shared directory if it doesn't exist
        mkdir -p web/shared
        
        # Update shared config
        cp "$temp_config" "$config_file"
        
        # Copy config.js to each web application
        cp "$config_file" web/admin-panel/config.js
        cp "$config_file" web/saas-app/config.js
        cp "$config_file" web/landing-page/config.js
        
        print_success "Configuration updated and copied to all web apps"
        return 0  # Changed
    else
        print_status "Configuration unchanged, skipping web app update"
        return 1  # No change
    fi
    
    # Cleanup temp file
    rm -f "$temp_config"
}

# Generate and distribute config, check if changed
CONFIG_CHANGED=false
if generate_shared_config; then
    CONFIG_CHANGED=true
fi

# Conditional redeployment based on configuration changes or force flag
if [ "$CONFIG_CHANGED" = true ] || [ "$FORCE_REDEPLOY" = true ]; then
    if [ "$FORCE_REDEPLOY" = true ]; then
        print_status "Force redeploy requested, updating web applications..."
    else
        print_status "Configuration changed, redeploying web applications..."
    fi
    cdk deploy AgenticInsightsAppPlane --require-approval never
    print_success "Web applications updated"
else
    print_status "No configuration changes detected, skipping web app redeployment"
    print_status "Use --force flag to redeploy anyway: ./lab-01.1-deploy-base-architecture.sh --force"
fi

# Create admin user function with robust input handling
create_admin_user() {
    while true; do
        echo "Do you want to create a SaaS admin user now? [y/n]: "
        read answer
        
        case $answer in
            [Yy])
                while true; do
                    echo "Enter the admin email: "
                    read ADMIN_EMAIL
                    echo "Enter the admin password: "
                    read ADMIN_PASSWORD
                    
                    # Check if either email or password is empty
                    if [ -z "$ADMIN_EMAIL" ] || [ -z "$ADMIN_PASSWORD" ]; then
                        echo "Error: Email and Password cannot be empty!"
                        continue
                    else
                        # Backend call logic here
                        ADMIN_USER_POOL_ID=$(aws cloudformation describe-stacks \
                            --stack-name AgenticInsightsControlPlane \
                            --query 'Stacks[0].Outputs[?OutputKey==`AdminUserPoolId`].OutputValue' \
                            --output text \
                            --region "$AWS_REGION" 2>/dev/null || echo "")
                        
                        if [ -n "$ADMIN_USER_POOL_ID" ]; then
                            print_status "Creating admin user with email: $ADMIN_EMAIL"
                            
                            # Get Admin Panel URL
                            ADMIN_PANEL_URL=$(aws cloudformation describe-stacks \
                                --stack-name AgenticInsightsAppPlane \
                                --query 'Stacks[0].Outputs[?OutputKey==`AdminPanelUrl`].OutputValue' \
                                --output text \
                                --region "$AWS_REGION" 2>/dev/null || echo "")
                            
                            # Create admin user (Cognito will send welcome email)
                            aws cognito-idp admin-create-user \
                                --user-pool-id "$ADMIN_USER_POOL_ID" \
                                --username "$ADMIN_EMAIL" \
                                --user-attributes Name=email,Value="$ADMIN_EMAIL" Name=email_verified,Value=true \
                                --temporary-password "$ADMIN_PASSWORD" \
                                --region "$AWS_REGION" 2>/dev/null || print_warning "Admin user might already exist"
                            
                            # Set permanent password
                            aws cognito-idp admin-set-user-password \
                                --user-pool-id "$ADMIN_USER_POOL_ID" \
                                --username "$ADMIN_EMAIL" \
                                --password "$ADMIN_PASSWORD" \
                                --permanent \
                                --region "$AWS_REGION" 2>/dev/null || true
                            
                            print_success "Admin user created successfully"
                            if [ -n "$ADMIN_PANEL_URL" ]; then
                                echo "Admin Panel URL: $ADMIN_PANEL_URL"
                                echo "Username: $ADMIN_EMAIL"
                                echo "Password: $ADMIN_PASSWORD"
                            fi
                        else
                            print_error "Could not retrieve Admin User Pool ID"
                        fi
                        return 0
                    fi
                done
                ;;
                
            [Nn])
                echo "Ok, won't create the admin user, lets proceed"
                return 0
                ;;
                
            *)
                echo "Do you want to create a SaaS admin user? Please enter 'y' or 'n': "
                continue
                ;;
        esac
    done
}

# Create admin user (optional)
create_admin_user

# Display deployment summary
echo
echo "=================================================="
print_success "🎉 Deployment completed successfully!"
echo "=================================================="
echo
echo "📋 Deployment Summary:"
echo "----------------------"
echo "AWS Account: $AWS_ACCOUNT"
echo "AWS Region: $AWS_REGION"
echo
echo "🔗 Application URLs:"
if [ -n "$LANDING_PAGE_URL" ]; then
    echo "Landing Page: $LANDING_PAGE_URL"
fi
if [ -n "$ADMIN_PANEL_URL" ]; then
    echo "Admin Panel: $ADMIN_PANEL_URL"
fi
if [ -n "$SAAS_APP_URL" ]; then
    echo "SaaS Application: $SAAS_APP_URL"
fi
echo
echo "🔧 API Endpoints:"
if [ -n "$CONTROL_PLANE_API" ]; then
    echo "Control Plane API: $CONTROL_PLANE_API"
fi
if [ -n "$APP_PLANE_API" ]; then
    echo "Application Plane API: $APP_PLANE_API"
fi
echo
echo "📚 Next Steps:"
echo "1. Visit the Landing Page to register your first tenant"
echo "2. Use the Admin Panel to manage tenants"
echo "3. Access the SaaS App to manage products and orders"
echo
echo "🗑️  To remove everything, run: ./scripts/delete-all.sh"
echo "=================================================="
