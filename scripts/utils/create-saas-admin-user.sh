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

# Auto-create admin user function
auto_create_admin_user() {
    local email="$1"
    local password="$2"
    
    ADMIN_USER_POOL_ID=$(aws cloudformation describe-stacks \
        --stack-name AgenticInsightsControlPlane \
        --query 'Stacks[0].Outputs[?OutputKey==`AdminUserPoolId`].OutputValue' \
        --output text \
        --region "$AWS_REGION" 2>/dev/null || echo "")
    
    if [ -z "$ADMIN_USER_POOL_ID" ]; then
        print_error "Could not retrieve Admin User Pool ID"
        return 1
    fi

    print_status "Creating admin user with email: $email"
    
    # Check if user already exists
    if aws cognito-idp admin-get-user \
        --user-pool-id "$ADMIN_USER_POOL_ID" \
        --username "$email" \
        --region "$AWS_REGION" &>/dev/null; then
        
        print_status "Admin user already exists, updating password..."
        
        # User exists, just update password
        if aws cognito-idp admin-set-user-password \
            --user-pool-id "$ADMIN_USER_POOL_ID" \
            --username "$email" \
            --password "$password" \
            --permanent \
            --region "$AWS_REGION" 2>/dev/null; then
            
            print_success "Admin user password updated successfully"
            return 0
        else
            print_error "Failed to update admin user password. Check password policy requirements."
            return 1
        fi
    else
        # User doesn't exist, create new user
        print_status "Creating new admin user..."
        
        # Create admin user
        if aws cognito-idp admin-create-user \
            --user-pool-id "$ADMIN_USER_POOL_ID" \
            --username "$email" \
            --user-attributes Name=email,Value="$email" Name=email_verified,Value=true \
            --temporary-password "TempPass123!" \
            --message-action SUPPRESS \
            --region "$AWS_REGION" 2>/dev/null; then
            
            # Set permanent password
            if aws cognito-idp admin-set-user-password \
                --user-pool-id "$ADMIN_USER_POOL_ID" \
                --username "$email" \
                --password "$password" \
                --permanent \
                --region "$AWS_REGION" 2>/dev/null; then
                
                print_success "Admin user created successfully"
                return 0
            else
                print_error "User created but failed to set password. Check password policy requirements."
                return 1
            fi
        else
            print_error "Failed to create admin user"
            return 1
        fi
    fi
}

# Interactive admin user creation
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
                        auto_create_admin_user "$ADMIN_EMAIL" "$ADMIN_PASSWORD"
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

# Check for auto flag
if [[ "$1" == "--auto" ]]; then
    email="$2"
    password="$3"
    
    if [ -z "$email" ] || [ -z "$password" ]; then
        print_error "Usage: $0 --auto <email> <password>"
        exit 1
    fi
    
    echo "🔐 Creating Default Admin User"
    echo "================================"
    echo
    
    auto_create_admin_user "$email" "$password"
    
    # Don't print URLs here - let the calling script handle the final summary
else
    echo "🔐 Creating SaaS Admin User"
    echo "================================"
    create_admin_user
    echo
    echo "✅ Admin user creation process completed"
fi
