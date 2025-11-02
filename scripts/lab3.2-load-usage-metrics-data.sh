#!/bin/bash

# Create Sample Tenants for Usage Analysis Testing
# This script creates sample tenant records in the Tenants DynamoDB table
# to match the sample usage metrics data

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}Creating sample tenants...${NC}"

TENANTS_TABLE="Tenants"

# Function to generate a random date between 90-120 days ago
generate_random_past_date() {
    # Generate random number of days between 90 and 120
    local random_days=$((90 + RANDOM % 31))
    
    # Calculate date that many days ago
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        date -u -v-${random_days}d +%Y-%m-%dT%H:%M:%SZ
    else
        # Linux
        date -u -d "$random_days days ago" +%Y-%m-%dT%H:%M:%SZ
    fi
}

# Function to create a tenant
create_tenant() {
    local tenant_id=$1
    local tenant_name=$2
    local tier=$3
    local status=$4
    
    echo -e "${BLUE}Creating tenant: $tenant_id ($tenant_name)${NC}"
    
    # Check if tenant already exists
    existing=$(aws dynamodb get-item \
        --table-name "$TENANTS_TABLE" \
        --key "{\"tenant_id\":{\"S\":\"$tenant_id\"}}" \
        --output json 2>/dev/null || echo '{}')
    
    if echo "$existing" | grep -q "\"Item\""; then
        echo -e "${YELLOW}  Tenant $tenant_id already exists, skipping...${NC}"
        return
    fi
    
    # Generate random creation date between 90-120 days ago
    local created_at=$(generate_random_past_date)
    echo -e "  Creation date: $created_at"
    
    # Create tenant
    aws dynamodb put-item \
        --table-name "$TENANTS_TABLE" \
        --item "{
            \"tenant_id\": {\"S\": \"$tenant_id\"},
            \"tenant_name\": {\"S\": \"$tenant_name\"},
            \"tier\": {\"S\": \"$tier\"},
            \"status\": {\"S\": \"$status\"},
            \"created_at\": {\"S\": \"$created_at\"},
            \"updated_at\": {\"S\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"},
            \"admin_email\": {\"S\": \"admin@${tenant_id#tenant-}.example.com\"},
            \"subscription_start\": {\"S\": \"2024-01-01T00:00:00Z\"},
            \"features_enabled\": {\"L\": [
                {\"S\": \"products\"},
                {\"S\": \"orders\"},
                {\"S\": \"users\"},
                {\"S\": \"ai_descriptions\"}
            ]}
        }" > /dev/null 2>&1
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}  ✓ Created tenant: $tenant_id (created_at: $created_at)${NC}"
    else
        echo -e "${YELLOW}  ✗ Failed to create tenant: $tenant_id${NC}"
    fi
}

# Create sample tenants
create_tenant "tenant-acme" "ACME Corporation" "premium" "active"
create_tenant "tenant-globex" "Globex Industries" "premium" "active"
create_tenant "tenant-initech" "Initech LLC" "basic" "active"

echo ""
echo -e "${GREEN}Sample tenants created successfully!${NC}"
echo ""
echo "Available tenants for testing:"
echo "  - tenant-acme (ACME Corporation, Premium)"
echo "  - tenant-globex (Globex Industries, Premium)"
echo "  - tenant-initech (Initech LLC, Basic)"
echo ""
echo "You can now use these tenant IDs in your test events."

#!/bin/bash

# Create Tenant Test Users Script
# Creates admin users for the 3 sample tenants in their respective Cognito user pools

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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

# Configuration
REGION="${AWS_REGION:-us-east-1}"
APP_PLANE_STACK="${APP_PLANE_STACK:-AgenticInsightsAppPlane}"

# Default password (will be prompted to change on first login)
DEFAULT_PASSWORD="${DEFAULT_PASSWORD:-TempPass123!}"

echo ""
print_status "Tenant Test Users Creation Script"
echo "===================================="
echo ""

# Get User Pool IDs from CloudFormation
print_status "Retrieving User Pool IDs from CloudFormation..."

PREMIUM_USER_POOL_ID=$(aws cloudformation describe-stacks \
    --stack-name "$APP_PLANE_STACK" \
    --region "$REGION" \
    --query "Stacks[0].Outputs[?OutputKey=='PremiumTierUserPoolId'].OutputValue" \
    --output text 2>/dev/null)

BASIC_USER_POOL_ID=$(aws cloudformation describe-stacks \
    --stack-name "$APP_PLANE_STACK" \
    --region "$REGION" \
    --query "Stacks[0].Outputs[?OutputKey=='BasicTierUserPoolId'].OutputValue" \
    --output text 2>/dev/null)

if [ -z "$PREMIUM_USER_POOL_ID" ] || [ -z "$BASIC_USER_POOL_ID" ]; then
    print_error "Failed to retrieve User Pool IDs from CloudFormation"
    echo ""
    echo "Please check that the stack '$APP_PLANE_STACK' exists and has the required outputs."
    exit 1
fi

print_success "Retrieved User Pool IDs"
print_status "  Premium Tier: $PREMIUM_USER_POOL_ID"
print_status "  Basic Tier: $BASIC_USER_POOL_ID"
echo ""

# Define tenant users
# Format: tenant_id:email:tier:role
declare -a TENANT_USERS=(
    "tenant-acme:admin@tenant-acme.com:premium:tenant_admin"
    "tenant-acme:user@tenant-acme.com:premium:tenant_user"
    "tenant-globex:admin@tenant-globex.com:premium:tenant_admin"
    "tenant-globex:user@tenant-globex.com:premium:tenant_user"
    "tenant-initech:admin@tenant-initech.com:basic:tenant_admin"
    "tenant-initech:user@tenant-initech.com:basic:tenant_user"
)

# Function to create a user
create_user() {
    local tenant_id="$1"
    local email="$2"
    local tier="$3"
    local role="$4"
    
    # Determine which user pool to use
    if [ "$tier" = "premium" ]; then
        local user_pool_id="$PREMIUM_USER_POOL_ID"
    else
        local user_pool_id="$BASIC_USER_POOL_ID"
    fi
    
    print_status "Creating user: $email (Tenant: $tenant_id, Tier: $tier, Role: $role)"
    
    # Check if user already exists
    local user_exists=$(aws cognito-idp admin-get-user \
        --user-pool-id "$user_pool_id" \
        --username "$email" \
        --region "$REGION" 2>/dev/null || echo "")
    
    if [ -n "$user_exists" ]; then
        print_warning "User $email already exists, skipping creation"
        
        # Update user attributes if needed
        aws cognito-idp admin-update-user-attributes \
            --user-pool-id "$user_pool_id" \
            --username "$email" \
            --user-attributes \
                Name=custom:tenant_id,Value="$tenant_id" \
                Name=custom:role,Value="$role" \
                Name=custom:tier,Value="$tier" \
            --region "$REGION" >/dev/null 2>&1
        
        print_success "Updated attributes for $email"
        return 0
    fi
    
    # Create the user
    aws cognito-idp admin-create-user \
        --user-pool-id "$user_pool_id" \
        --username "$email" \
        --user-attributes \
            Name=email,Value="$email" \
            Name=email_verified,Value=true \
            Name=custom:tenant_id,Value="$tenant_id" \
            Name=custom:role,Value="$role" \
            Name=custom:tier,Value="$tier" \
        --temporary-password "$DEFAULT_PASSWORD" \
        --message-action SUPPRESS \
        --region "$REGION" >/dev/null 2>&1
    
    if [ $? -eq 0 ]; then
        # Set permanent password
        aws cognito-idp admin-set-user-password \
            --user-pool-id "$user_pool_id" \
            --username "$email" \
            --password "$DEFAULT_PASSWORD" \
            --permanent \
            --region "$REGION" >/dev/null 2>&1
        
        print_success "Created user: $email"
        echo "           Username: $email"
        echo "           Password: $DEFAULT_PASSWORD"
        echo "           Tenant: $tenant_id"
        echo "           Role: $role"
        echo "           Tier: $tier"
    else
        print_error "Failed to create user: $email"
        return 1
    fi
}

# Create all users
print_status "Creating tenant users..."
echo ""

success_count=0
fail_count=0

for user_info in "${TENANT_USERS[@]}"; do
    IFS=':' read -r tenant_id email tier role <<< "$user_info"
    
    if create_user "$tenant_id" "$email" "$tier" "$role"; then
        ((success_count++))
    else
        ((fail_count++))
    fi
    echo ""
done

# Summary
echo ""
print_status "=========================================="
print_status "User Creation Summary"
print_status "=========================================="
print_success "Successfully created/updated: $success_count users"
if [ $fail_count -gt 0 ]; then
    print_error "Failed: $fail_count users"
fi
echo ""

# Display credentials table
print_status "Test User Credentials"
print_status "=========================================="
echo ""
printf "%-25s %-30s %-15s %-15s\n" "Tenant" "Email" "Password" "Role"
printf "%-25s %-30s %-15s %-15s\n" "------" "-----" "--------" "----"
printf "%-25s %-30s %-15s %-15s\n" "tenant-acme" "admin@tenant-acme.com" "$DEFAULT_PASSWORD" "tenant_admin"
printf "%-25s %-30s %-15s %-15s\n" "tenant-acme" "user@tenant-acme.com" "$DEFAULT_PASSWORD" "tenant_user"
printf "%-25s %-30s %-15s %-15s\n" "tenant-globex" "admin@tenant-globex.com" "$DEFAULT_PASSWORD" "tenant_admin"
printf "%-25s %-30s %-15s %-15s\n" "tenant-globex" "user@tenant-globex.com" "$DEFAULT_PASSWORD" "tenant_user"
printf "%-25s %-30s %-15s %-15s\n" "tenant-initech" "admin@tenant-initech.com" "$DEFAULT_PASSWORD" "tenant_admin"
printf "%-25s %-30s %-15s %-15s\n" "tenant-initech" "user@tenant-initech.com" "$DEFAULT_PASSWORD" "tenant_user"
echo ""

# Usage instructions
print_status "=========================================="
print_status "Testing Instructions"
print_status "=========================================="
echo ""
echo "1. Get JWT token for a tenant admin:"
echo "   export USERNAME=\"admin@tenant-acme.com\""
echo "   cd test/usage-analysis"
echo "   ./get-jwt-token.sh"
echo "   # Enter password: $DEFAULT_PASSWORD"
echo ""
echo "2. Run API tests:"
echo "   ./test-api.sh all"
echo ""
echo "3. Test with different tenants:"
echo "   export USERNAME=\"admin@tenant-globex.com\""
echo "   ./get-jwt-token.sh"
echo ""
echo "4. Test with tenant user (limited access):"
echo "   export USERNAME=\"user@tenant-acme.com\""
echo "   ./get-jwt-token.sh"
echo ""

# Verify users
print_status "=========================================="
print_status "Verification"
print_status "=========================================="
echo ""
print_status "Verifying users in Premium Tier User Pool..."
aws cognito-idp list-users \
    --user-pool-id "$PREMIUM_USER_POOL_ID" \
    --region "$REGION" \
    --query 'Users[*].[Username,UserStatus]' \
    --output table 2>/dev/null || print_warning "Could not list users"

echo ""
print_status "Verifying users in Basic Tier User Pool..."
aws cognito-idp list-users \
    --user-pool-id "$BASIC_USER_POOL_ID" \
    --region "$REGION" \
    --query 'Users[*].[Username,UserStatus]' \
    --output table 2>/dev/null || print_warning "Could not list users"

echo ""
print_success "Tenant test users setup complete!"
echo ""
print_warning "Note: All users have the same password: $DEFAULT_PASSWORD"
print_warning "Consider changing passwords for production use."
echo ""

#!/bin/bash

# Load Sample Usage Metrics Data (AWS CLI version - no boto3 required)
# This script generates and loads sample usage metrics data into DynamoDB
# using only AWS CLI commands (no Python dependencies)
# Usage: ./scripts/load_sample_usage_metrics_cli.sh [--table-name TABLE] [--days DAYS] [--clear]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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

# Default values
TABLE_NAME="AgenticInsights-UsageMetrics"
DAYS=90
CLEAR_DATA=false
TENANTS=("tenant-acme" "tenant-globex" "tenant-initech")
FEATURES=("products" "orders" "users" "ai_descriptions")

# Tenant profiles for realistic data generation
# Using functions instead of associative arrays for bash 3.x compatibility
get_tenant_profile() {
    case "$1" in
        "tenant-acme") echo "enterprise" ;;
        "tenant-globex") echo "premium" ;;
        "tenant-initech") echo "basic" ;;
        *) echo "basic" ;;
    esac
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --table-name)
            TABLE_NAME="$2"
            shift 2
            ;;
        --days)
            DAYS="$2"
            shift 2
            ;;
        --clear)
            CLEAR_DATA=true
            shift
            ;;
        *)
            print_error "Unknown option: $1"
            echo "Usage: $0 [--table-name TABLE] [--days DAYS] [--clear]"
            exit 1
            ;;
    esac
done

print_status "Loading sample usage metrics data..."
print_status "Table: $TABLE_NAME"
print_status "Days of data: $DAYS"

# Clear existing data if requested
if [ "$CLEAR_DATA" = true ]; then
    print_warning "Clearing existing data..."
    
    # Scan and delete all items (simplified - in production use batch operations)
    print_status "Scanning table for existing items..."
    
    # Get all items
    items=$(aws dynamodb scan \
        --table-name "$TABLE_NAME" \
        --projection-expression "PK,SK" \
        --output json 2>/dev/null || echo '{"Items":[]}')
    
    item_count=$(echo "$items" | grep -o '"PK"' | wc -l)
    
    if [ "$item_count" -gt 0 ]; then
        print_status "Found $item_count items to delete..."
        
        # Delete items (limit to first 100 for safety)
        echo "$items" | jq -r '.Items[] | @json' | head -100 | while read -r item; do
            pk=$(echo "$item" | jq -r '.PK.S')
            sk=$(echo "$item" | jq -r '.SK.S')
            
            aws dynamodb delete-item \
                --table-name "$TABLE_NAME" \
                --key "{\"PK\":{\"S\":\"$pk\"},\"SK\":{\"S\":\"$sk\"}}" \
                > /dev/null 2>&1 || true
        done
        
        print_success "Cleared existing data"
    else
        print_status "No existing data found"
    fi
fi

# Generate and load sample data using batch writes
print_status "Generating sample metrics data..."

total_items=0
current_date=$(date -u +%s)
batch_items=()
BATCH_SIZE=25

# Function to write batch to DynamoDB
write_batch() {
    if [ ${#batch_items[@]} -eq 0 ]; then
        return
    fi
    
    # Create batch write request JSON
    local request_json='{"'$TABLE_NAME'":['
    local first=true
    
    for item in "${batch_items[@]}"; do
        if [ "$first" = false ]; then
            request_json+=","
        fi
        first=false
        request_json+="{\"PutRequest\":{\"Item\":$item}}"
    done
    
    request_json+=']}'
    
    # Write batch
    aws dynamodb batch-write-item \
        --request-items "$request_json" \
        > /dev/null 2>&1
    
    # Clear batch
    batch_items=()
}

# Generate data for each tenant
for tenant in "${TENANTS[@]}"; do
    print_status "Generating data for $tenant..."
    
    # Get tenant profile
    tenant_profile=$(get_tenant_profile "$tenant")
    
    # Generate data for the past N days
    for ((day=0; day<$DAYS; day++)); do
        # Calculate timestamp for this day
        day_timestamp=$((current_date - (day * 86400)))
        date_str=$(date -u -r $day_timestamp +"%Y-%m-%dT%H:%M:%SZ")
        month=$(date -u -r $day_timestamp +"%Y-%m")
        
        # Calculate TTL (90 days from now)
        ttl=$((current_date + 7776000))
        
        # Add growth trend (more usage in recent days)
        growth_factor=$(awk "BEGIN {printf \"%.2f\", 1 + (($DAYS - $day) / $DAYS) * 0.5}")
        
        # Add weekly pattern (weekdays have more usage)
        day_of_week=$(date -u -r $day_timestamp +"%u")  # 1=Monday, 7=Sunday
        if [ "$day_of_week" -ge 6 ]; then
            weekly_factor="0.6"  # Weekend - 60% of weekday traffic
        else
            weekly_factor="1.0"
        fi
        
        # Generate feature usage metrics for each feature
        for feature in "${FEATURES[@]}"; do
            # Base usage counts by tenant profile
            if [ "$tenant_profile" = "enterprise" ]; then
                base_count=$((800 + RANDOM % 400))
                base_users=$((50 + RANDOM % 30))
            elif [ "$tenant_profile" = "premium" ]; then
                base_count=$((400 + RANDOM % 200))
                base_users=$((25 + RANDOM % 15))
            else
                base_count=$((150 + RANDOM % 100))
                base_users=$((10 + RANDOM % 8))
            fi
            
            # Adjust by feature type
            if [ "$feature" = "products" ]; then
                feature_multiplier="2.5"
                adoption_rate="95"
            elif [ "$feature" = "orders" ]; then
                feature_multiplier="1.8"
                adoption_rate="85"
            elif [ "$feature" = "users" ]; then
                feature_multiplier="1.2"
                adoption_rate="100"
            elif [ "$feature" = "ai_descriptions" ]; then
                feature_multiplier="0.8"
                adoption_rate="70"
            else
                feature_multiplier="1.0"
                adoption_rate="80"
            fi
            
            # Calculate final counts with all factors
            usage_count=$(awk "BEGIN {printf \"%.0f\", $base_count * $feature_multiplier * $growth_factor * $weekly_factor}")
            unique_users=$(awk "BEGIN {printf \"%.0f\", $base_users * $growth_factor * $weekly_factor}")
            
            # Ensure minimum values
            if [ "$usage_count" -lt 10 ]; then usage_count=10; fi
            if [ "$unique_users" -lt 2 ]; then unique_users=2; fi
            
            # Calculate engagement metrics
            avg_actions_per_user=$(awk "BEGIN {printf \"%.1f\", $usage_count / $unique_users}")
            sessions_count=$(awk "BEGIN {printf \"%.0f\", $unique_users * 1.5}")
            
            # Create PK and SK for daily metrics (PK includes month for GSI queries)
            pk="TENANT#${tenant}#METRIC#feature_usage#PERIOD#${month}"
            sk="TIMESTAMP#${date_str}#FEATURE#${feature}"
            
            # Add item to batch
            batch_items+=("{
                \"PK\": {\"S\": \"$pk\"},
                \"SK\": {\"S\": \"$sk\"},
                \"tenant_id\": {\"S\": \"$tenant\"},
                \"metric_type\": {\"S\": \"feature_usage\"},
                \"time_period\": {\"S\": \"daily\"},
                \"timestamp\": {\"S\": \"$date_str\"},
                \"month\": {\"S\": \"$month\"},
                \"feature_name\": {\"S\": \"$feature\"},
                \"usage_count\": {\"N\": \"$usage_count\"},
                \"unique_users\": {\"N\": \"$unique_users\"},
                \"sessions_count\": {\"N\": \"$sessions_count\"},
                \"avg_actions_per_user\": {\"N\": \"$avg_actions_per_user\"},
                \"adoption_rate\": {\"N\": \"$adoption_rate\"},
                \"active_users\": {\"N\": \"$unique_users\"},
                \"first_used_date\": {\"S\": \"${month}-01\"},
                \"last_used_date\": {\"S\": \"$date_str\"},
                \"aggregation_level\": {\"S\": \"tenant\"},
                \"data_points_count\": {\"N\": \"$usage_count\"},
                \"last_updated\": {\"S\": \"$date_str\"},
                \"tenant_timestamp\": {\"S\": \"${tenant}#${date_str}\"},
                \"ttl\": {\"N\": \"$ttl\"}
            }")
            
            ((total_items++))
            
            # Write batch if it reaches the limit
            if [ ${#batch_items[@]} -ge $BATCH_SIZE ]; then
                write_batch
            fi
        done
        
        # Generate performance metrics for each feature
        for perf_feature in "${FEATURES[@]}"; do
            # Base performance by tenant profile
            if [ "$tenant_profile" = "enterprise" ]; then
                base_requests=$((5000 + RANDOM % 3000))
                base_response_time=$((80 + RANDOM % 40))
                base_error_rate="0.5"
            elif [ "$tenant_profile" = "premium" ]; then
                base_requests=$((2500 + RANDOM % 1500))
                base_response_time=$((100 + RANDOM % 50))
                base_error_rate="1.0"
            else
                base_requests=$((1000 + RANDOM % 500))
                base_response_time=$((120 + RANDOM % 60))
                base_error_rate="1.5"
            fi
            
            # Apply growth and weekly factors
            total_requests=$(awk "BEGIN {printf \"%.0f\", $base_requests * $growth_factor * $weekly_factor}")
            avg_response_time=$(awk "BEGIN {printf \"%.0f\", $base_response_time / $growth_factor}")  # Performance improves over time
            
            # Calculate percentiles
            p50_response_time=$avg_response_time
            p95_response_time=$(awk "BEGIN {printf \"%.0f\", $avg_response_time * 1.8}")
            p99_response_time=$(awk "BEGIN {printf \"%.0f\", $avg_response_time * 2.5}")
            min_response_time=$(awk "BEGIN {printf \"%.0f\", $avg_response_time * 0.3}")
            max_response_time=$(awk "BEGIN {printf \"%.0f\", $avg_response_time * 4}")
            
            # Calculate errors
            error_rate_value=$(awk "BEGIN {printf \"%.2f\", $base_error_rate + (RANDOM % 100) / 100.0}")
            failed_requests=$(awk "BEGIN {printf \"%.0f\", $total_requests * $error_rate_value / 100}")
            successful_requests=$((total_requests - failed_requests))
            
            # Calculate throughput
            throughput=$(awk "BEGIN {printf \"%.2f\", $total_requests / 86400}")  # requests per second
            
            pk="TENANT#${tenant}#METRIC#performance#PERIOD#${month}"
            sk="TIMESTAMP#${date_str}#FEATURE#${perf_feature}"
            
            batch_items+=("{
                \"PK\": {\"S\": \"$pk\"},
                \"SK\": {\"S\": \"$sk\"},
                \"tenant_id\": {\"S\": \"$tenant\"},
                \"metric_type\": {\"S\": \"performance\"},
                \"time_period\": {\"S\": \"daily\"},
                \"timestamp\": {\"S\": \"$date_str\"},
                \"month\": {\"S\": \"$month\"},
                \"feature_name\": {\"S\": \"$perf_feature\"},
                \"total_requests\": {\"N\": \"$total_requests\"},
                \"successful_requests\": {\"N\": \"$successful_requests\"},
                \"failed_requests\": {\"N\": \"$failed_requests\"},
                \"avg_response_time\": {\"N\": \"$avg_response_time\"},
                \"p50_response_time\": {\"N\": \"$p50_response_time\"},
                \"p95_response_time\": {\"N\": \"$p95_response_time\"},
                \"p99_response_time\": {\"N\": \"$p99_response_time\"},
                \"min_response_time\": {\"N\": \"$min_response_time\"},
                \"max_response_time\": {\"N\": \"$max_response_time\"},
                \"error_rate\": {\"N\": \"$error_rate_value\"},
                \"throughput\": {\"N\": \"$throughput\"},
                \"aggregation_level\": {\"S\": \"tenant\"},
                \"data_points_count\": {\"N\": \"$total_requests\"},
                \"last_updated\": {\"S\": \"$date_str\"},
                \"tenant_timestamp\": {\"S\": \"${tenant}#${date_str}\"},
                \"metric_type_month\": {\"S\": \"performance#${month}\"},
                \"ttl\": {\"N\": \"$ttl\"}
            }")
            
            ((total_items++))
            
            # Write batch if it reaches the limit
            if [ ${#batch_items[@]} -ge $BATCH_SIZE ]; then
                write_batch
            fi
        done
        
        # Generate AI usage metrics (daily for all tenants)
        # Base AI usage by tenant profile
        if [ "$tenant_profile" = "enterprise" ]; then
            base_ai_invocations=$((200 + RANDOM % 150))
            ai_adoption="85"
        elif [ "$tenant_profile" = "premium" ]; then
            base_ai_invocations=$((100 + RANDOM % 80))
            ai_adoption="70"
        else
            base_ai_invocations=$((30 + RANDOM % 30))
            ai_adoption="45"
        fi
        
        # Apply growth and weekly factors
        ai_invocations=$(awk "BEGIN {printf \"%.0f\", $base_ai_invocations * $growth_factor * $weekly_factor}")
        
        # Ensure minimum
        if [ "$ai_invocations" -lt 5 ]; then ai_invocations=5; fi
        
        # Token calculations (realistic ranges)
        avg_input_tokens=$((200 + RANDOM % 150))
        avg_output_tokens=$((400 + RANDOM % 300))
        total_input_tokens=$((ai_invocations * avg_input_tokens))
        total_output_tokens=$((ai_invocations * avg_output_tokens))
        avg_tokens_per_request=$((avg_input_tokens + avg_output_tokens))
        
        # Cost calculation (AWS Bedrock Claude pricing)
        # Input: $0.00025 per 1K tokens, Output: $0.00125 per 1K tokens
        input_cost=$(awk "BEGIN {printf \"%.4f\", ($total_input_tokens / 1000.0) * 0.00025}")
        output_cost=$(awk "BEGIN {printf \"%.4f\", ($total_output_tokens / 1000.0) * 0.00125}")
        estimated_cost=$(awk "BEGIN {printf \"%.4f\", $input_cost + $output_cost}")
        cost_per_generation=$(awk "BEGIN {printf \"%.6f\", $estimated_cost / $ai_invocations}")
        
        # Performance metrics
        generation_success_rate=$(awk "BEGIN {printf \"%.1f\", 94 + (RANDOM % 60) / 10.0}")
        avg_generation_time=$(awk "BEGIN {printf \"%.2f\", 1.5 + (RANDOM % 200) / 100.0}")
        
        # Calculate successful vs failed generations
        successful_generations=$(awk "BEGIN {printf \"%.0f\", $ai_invocations * $generation_success_rate / 100}")
        failed_generations=$((ai_invocations - successful_generations))
        
        pk="TENANT#${tenant}#METRIC#ai_usage#PERIOD#${month}"
        sk="TIMESTAMP#${date_str}#FEATURE#ai_descriptions"
        
        batch_items+=("{
            \"PK\": {\"S\": \"$pk\"},
            \"SK\": {\"S\": \"$sk\"},
            \"tenant_id\": {\"S\": \"$tenant\"},
            \"metric_type\": {\"S\": \"ai_usage\"},
            \"time_period\": {\"S\": \"daily\"},
            \"timestamp\": {\"S\": \"$date_str\"},
            \"month\": {\"S\": \"$month\"},
            \"feature_name\": {\"S\": \"ai_descriptions\"},
            \"ai_invocations\": {\"N\": \"$ai_invocations\"},
            \"successful_generations\": {\"N\": \"$successful_generations\"},
            \"failed_generations\": {\"N\": \"$failed_generations\"},
            \"total_input_tokens\": {\"N\": \"$total_input_tokens\"},
            \"total_output_tokens\": {\"N\": \"$total_output_tokens\"},
            \"avg_input_tokens\": {\"N\": \"$avg_input_tokens\"},
            \"avg_output_tokens\": {\"N\": \"$avg_output_tokens\"},
            \"avg_tokens_per_request\": {\"N\": \"$avg_tokens_per_request\"},
            \"estimated_cost\": {\"N\": \"$estimated_cost\"},
            \"input_cost\": {\"N\": \"$input_cost\"},
            \"output_cost\": {\"N\": \"$output_cost\"},
            \"cost_per_generation\": {\"N\": \"$cost_per_generation\"},
            \"generation_success_rate\": {\"N\": \"$generation_success_rate\"},
            \"avg_generation_time\": {\"N\": \"$avg_generation_time\"},
            \"adoption_rate\": {\"N\": \"$ai_adoption\"},
            \"aggregation_level\": {\"S\": \"tenant\"},
            \"data_points_count\": {\"N\": \"$ai_invocations\"},
            \"last_updated\": {\"S\": \"$date_str\"},
            \"tenant_timestamp\": {\"S\": \"${tenant}#${date_str}\"},
            \"metric_type_month\": {\"S\": \"ai_usage#${month}\"},
            \"ttl\": {\"N\": \"$ttl\"}
        }")
        
        ((total_items++))
        
        # Write batch if it reaches the limit
        if [ ${#batch_items[@]} -ge $BATCH_SIZE ]; then
            write_batch
        fi
        
        # Progress indicator
        if [ $((total_items % 250)) -eq 0 ]; then
            print_status "Generated $total_items items..."
        fi
    done
    
    # Generate monthly aggregated metrics for better trend analysis
    print_status "Generating monthly aggregates for $tenant..."
    
    # Get unique months from the date range (bash 3.x compatible)
    months_list=""
    for ((day=0; day<$DAYS; day++)); do
        day_timestamp=$((current_date - (day * 86400)))
        month=$(date -u -r $day_timestamp +"%Y-%m")
        # Add month to list if not already present
        if [[ ! " $months_list " =~ " $month " ]]; then
            months_list="$months_list $month"
        fi
    done
    
    # Create monthly aggregates for each month
    for month in $months_list; do
        month_start="${month}-01T00:00:00Z"
        ttl=$((current_date + 7776000))
        
        # Monthly feature usage aggregates
        for feature in "${FEATURES[@]}"; do
            # Calculate monthly totals (approximate based on 30 days)
            if [ "$tenant_profile" = "enterprise" ]; then
                monthly_usage=$((25000 + RANDOM % 10000))
                monthly_users=$((1500 + RANDOM % 500))
            elif [ "$tenant_profile" = "premium" ]; then
                monthly_usage=$((12000 + RANDOM % 5000))
                monthly_users=$((750 + RANDOM % 250))
            else
                monthly_usage=$((4500 + RANDOM % 2000))
                monthly_users=$((300 + RANDOM % 100))
            fi
            
            # Feature-specific adjustments
            if [ "$feature" = "products" ]; then
                monthly_usage=$(awk "BEGIN {printf \"%.0f\", $monthly_usage * 2.5}")
            elif [ "$feature" = "orders" ]; then
                monthly_usage=$(awk "BEGIN {printf \"%.0f\", $monthly_usage * 1.8}")
            elif [ "$feature" = "ai_descriptions" ]; then
                monthly_usage=$(awk "BEGIN {printf \"%.0f\", $monthly_usage * 0.8}")
            fi
            
            pk="TENANT#${tenant}#METRIC#feature_usage#PERIOD#monthly"
            sk="TIMESTAMP#${month_start}#FEATURE#${feature}"
            
            batch_items+=("{
                \"PK\": {\"S\": \"$pk\"},
                \"SK\": {\"S\": \"$sk\"},
                \"tenant_id\": {\"S\": \"$tenant\"},
                \"metric_type\": {\"S\": \"feature_usage\"},
                \"time_period\": {\"S\": \"monthly\"},
                \"timestamp\": {\"S\": \"$month_start\"},
                \"month\": {\"S\": \"$month\"},
                \"feature_name\": {\"S\": \"$feature\"},
                \"usage_count\": {\"N\": \"$monthly_usage\"},
                \"unique_users\": {\"N\": \"$monthly_users\"},
                \"aggregation_level\": {\"S\": \"tenant\"},
                \"data_points_count\": {\"N\": \"30\"},
                \"last_updated\": {\"S\": \"$month_start\"},
                \"ttl\": {\"N\": \"$ttl\"}
            }")
            
            ((total_items++))
            
            if [ ${#batch_items[@]} -ge $BATCH_SIZE ]; then
                write_batch
            fi
        done
        
        # Monthly performance aggregates
        if [ "$tenant_profile" = "enterprise" ]; then
            monthly_requests=$((150000 + RANDOM % 50000))
            monthly_avg_response=$((80 + RANDOM % 20))
        elif [ "$tenant_profile" = "premium" ]; then
            monthly_requests=$((75000 + RANDOM % 25000))
            monthly_avg_response=$((100 + RANDOM % 30))
        else
            monthly_requests=$((30000 + RANDOM % 10000))
            monthly_avg_response=$((120 + RANDOM % 40))
        fi
        
        monthly_errors=$(awk "BEGIN {printf \"%.0f\", $monthly_requests * 0.01}")
        monthly_error_rate=$(awk "BEGIN {printf \"%.2f\", ($monthly_errors / $monthly_requests) * 100}")
        
        pk="TENANT#${tenant}#METRIC#performance#PERIOD#monthly"
        sk="TIMESTAMP#${month_start}"
        
        batch_items+=("{
            \"PK\": {\"S\": \"$pk\"},
            \"SK\": {\"S\": \"$sk\"},
            \"tenant_id\": {\"S\": \"$tenant\"},
            \"metric_type\": {\"S\": \"performance\"},
            \"time_period\": {\"S\": \"monthly\"},
            \"timestamp\": {\"S\": \"$month_start\"},
            \"month\": {\"S\": \"$month\"},
            \"total_requests\": {\"N\": \"$monthly_requests\"},
            \"successful_requests\": {\"N\": \"$((monthly_requests - monthly_errors))\"},
            \"failed_requests\": {\"N\": \"$monthly_errors\"},
            \"avg_response_time\": {\"N\": \"$monthly_avg_response\"},
            \"error_rate\": {\"N\": \"$monthly_error_rate\"},
            \"aggregation_level\": {\"S\": \"tenant\"},
            \"data_points_count\": {\"N\": \"30\"},
            \"last_updated\": {\"S\": \"$month_start\"},
            \"ttl\": {\"N\": \"$ttl\"}
        }")
        
        ((total_items++))
        
        if [ ${#batch_items[@]} -ge $BATCH_SIZE ]; then
            write_batch
        fi
        
        # Monthly AI usage aggregates
        if [ "$tenant_profile" = "enterprise" ]; then
            monthly_ai_invocations=$((6000 + RANDOM % 2000))
        elif [ "$tenant_profile" = "premium" ]; then
            monthly_ai_invocations=$((3000 + RANDOM % 1000))
        else
            monthly_ai_invocations=$((900 + RANDOM % 400))
        fi
        
        monthly_input_tokens=$((monthly_ai_invocations * 250))
        monthly_output_tokens=$((monthly_ai_invocations * 500))
        monthly_cost=$(awk "BEGIN {printf \"%.2f\", (($monthly_input_tokens / 1000.0) * 0.00025) + (($monthly_output_tokens / 1000.0) * 0.00125)}")
        
        pk="TENANT#${tenant}#METRIC#ai_usage#PERIOD#monthly"
        sk="TIMESTAMP#${month_start}"
        
        batch_items+=("{
            \"PK\": {\"S\": \"$pk\"},
            \"SK\": {\"S\": \"$sk\"},
            \"tenant_id\": {\"S\": \"$tenant\"},
            \"metric_type\": {\"S\": \"ai_usage\"},
            \"time_period\": {\"S\": \"monthly\"},
            \"timestamp\": {\"S\": \"$month_start\"},
            \"month\": {\"S\": \"$month\"},
            \"feature_name\": {\"S\": \"ai_descriptions\"},
            \"ai_invocations\": {\"N\": \"$monthly_ai_invocations\"},
            \"total_input_tokens\": {\"N\": \"$monthly_input_tokens\"},
            \"total_output_tokens\": {\"N\": \"$monthly_output_tokens\"},
            \"estimated_cost\": {\"N\": \"$monthly_cost\"},
            \"aggregation_level\": {\"S\": \"tenant\"},
            \"data_points_count\": {\"N\": \"30\"},
            \"last_updated\": {\"S\": \"$month_start\"},
            \"ttl\": {\"N\": \"$ttl\"}
        }")
        
        ((total_items++))
        
        if [ ${#batch_items[@]} -ge $BATCH_SIZE ]; then
            write_batch
        fi
    done
done

# Write any remaining items in the batch
if [ ${#batch_items[@]} -gt 0 ]; then
    print_status "Writing final batch of ${#batch_items[@]} items..."
    write_batch
fi

print_success "Sample data loading complete!"
print_status "Total items loaded: $total_items"
print_status "Tenants: ${TENANTS[*]}"
print_status "Features: ${FEATURES[*]}"
print_status "Date range: $DAYS days"

echo ""
print_status "You can now query the data using:"
echo "  aws dynamodb query --table-name $TABLE_NAME --key-condition-expression 'PK = :pk' --expression-attribute-values '{\":pk\":{\"S\":\"TENANT#tenant-acme#METRIC#feature_usage#PERIOD#$(date +%Y-%m)\"}}'"
