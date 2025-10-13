#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print functions
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

# Get AWS region
AWS_REGION=$(aws configure get region 2>/dev/null || echo "us-east-1")

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
                echo "Ok, won't create the admin user"
                return 0
                ;;
                
            *)
                echo "Do you want to create a SaaS admin user? Please enter 'y' or 'n': "
                continue
                ;;
        esac
    done
}

echo "🔐 Creating SaaS Admin User"
echo "================================"

# Create admin user
create_admin_user

echo
echo "✅ Admin user creation process completed"
