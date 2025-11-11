#!/bin/bash

# Lab 2.1.2: Automated Tenant Onboarding
# Creates two demo tenants using the open registration API

set -e

# =============================================================================
# TENANT CONFIGURATION - Modify these variables as needed
# =============================================================================

# Generate unique suffix with timestamp
TIMESTAMP=$(date +%s)

# Basic tier tenant
BASIC_COMPANY_NAME="basic-store2"
BASIC_ADMIN_EMAIL="admin+basic-store2@example.com"
BASIC_ADMIN_PASSWORD="Admin123!"
BASIC_TIER="basic"

# Premium tier tenant
PREMIUM_COMPANY_NAME="premium-store2"
PREMIUM_ADMIN_EMAIL="admin+premium-store2@example.com"
PREMIUM_ADMIN_PASSWORD="Admin123!"
PREMIUM_TIER="premium"

# =============================================================================
# SCRIPT EXECUTION - No changes needed below this line
# =============================================================================

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[1;36m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}🏢 Lab 2.1.2: Automated Tenant Onboarding${NC}"
echo "=================================================="

# Get deployment outputs and environment info
echo -e "${BLUE}[INFO]${NC} Retrieving deployment outputs..."
CURRENT_REGION=$(aws configure get region)
CONTROL_PLANE_API=$(aws cloudformation describe-stacks --stack-name AgenticInsightsControlPlane --query 'Stacks[0].Outputs[?OutputKey==`ControlPlaneApiUrl`].OutputValue' --output text)

if [ -z "$CONTROL_PLANE_API" ]; then
    echo -e "${RED}[ERROR]${NC} Failed to retrieve deployment outputs. Ensure the stack is deployed."
    exit 1
fi

echo -e "${GREEN}[SUCCESS]${NC} Retrieved deployment outputs"
echo ""
echo -e "${BLUE}📍 Environment Information:${NC}"
echo "   Region: $CURRENT_REGION"
echo ""

# Function to register tenant via open API
register_tenant() {
    local company_name=$1
    local admin_email=$2
    local admin_password=$3
    local tier=$4
    
    echo -e "${BLUE}[INFO]${NC} Registering tenant: $company_name ($tier tier)"
    
    local response=$(curl -s -X POST "${CONTROL_PLANE_API}/register" \
        -H "Content-Type: application/json" \
        -d "{
            \"tenant_name\":\"$company_name\",
            \"admin_email\":\"$admin_email\",
            \"admin_password\":\"$admin_password\",
            \"tier\":\"$tier\"
        }")
    
    local success=$(echo "$response" | jq -r '.message // empty')
    
    if [[ "$success" != *"successfully"* ]]; then
        echo -e "${RED}[ERROR]${NC} Failed to register tenant $company_name"
        echo "Response: $response"
        return 1
    fi
    
    echo -e "${GREEN}[SUCCESS]${NC} Tenant $company_name registered successfully"
    return 0
}

# Main execution
echo -e "${BLUE}[INFO]${NC} Starting tenant registration process..."

# Register tenants using open API
echo -e "${BLUE}[INFO]${NC} Registering tenants..."

# Register Basic tier tenant
if register_tenant "$BASIC_COMPANY_NAME" "$BASIC_ADMIN_EMAIL" "$BASIC_ADMIN_PASSWORD" "$BASIC_TIER"; then
    BASIC_CREATED=true
else
    BASIC_CREATED=false
fi

# Register Premium tier tenant  
if register_tenant "$PREMIUM_COMPANY_NAME" "$PREMIUM_ADMIN_EMAIL" "$PREMIUM_ADMIN_PASSWORD" "$PREMIUM_TIER"; then
    PREMIUM_CREATED=true
else
    PREMIUM_CREATED=false
fi

# Summary
echo ""
echo -e "${BLUE}📋 Tenant Registration Summary:${NC}"
echo "------------------------------"

if [ "$BASIC_CREATED" = true ]; then
    echo -e "${GREEN}✅ Basic Tenant:${NC}"
    echo "   Company: $BASIC_COMPANY_NAME"
    echo "   Admin: $BASIC_ADMIN_EMAIL"
    echo "   Password: $BASIC_ADMIN_PASSWORD"
    echo "   Tier: $BASIC_TIER"
else
    echo -e "${RED}❌ Basic Tenant: Failed to register${NC}"
fi

echo ""

if [ "$PREMIUM_CREATED" = true ]; then
    echo -e "${GREEN}✅ Premium Tenant:${NC}"
    echo "   Company: $PREMIUM_COMPANY_NAME"
    echo "   Admin: $PREMIUM_ADMIN_EMAIL"
    echo "   Password: $PREMIUM_ADMIN_PASSWORD"
    echo "   Tier: $PREMIUM_TIER"
else
    echo -e "${RED}❌ Premium Tenant: Failed to register${NC}"
fi

echo ""

if [ "$BASIC_CREATED" = true ] && [ "$PREMIUM_CREATED" = true ]; then
    echo -e "${GREEN}[SUCCESS]${NC} 🎉 All tenants registered successfully!"
    echo "=================================================="
    exit 0
else
    echo -e "${YELLOW}[WARNING]${NC} Some tenants failed to register. Check the logs above."
    echo "=================================================="
    exit 1
fi
