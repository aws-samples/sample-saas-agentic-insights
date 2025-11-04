# Centralized metrics and event naming constants

# Event Types
class EventTypes:
    API_REQUEST = "api.request"
    LAMBDA_EXECUTION = "lambda.execution"
    DYNAMODB_OPERATION = "dynamodb.operation"
    BEDROCK_INVOCATION = "bedrock.invocation"
    S3_OPERATION = "s3.operation"

# EventBridge Sources
class EventSources:
    METRICS = "agentic-insights.metrics"
    TENANT_SERVICE = "tenant.service"

# EventBridge Detail Types
class DetailTypes:
    TENANT_METRIC_EVENT = "Tenant Metric Event"
    TENANT_CREATED = "Tenant Created"
    ADMIN_USER_CREATION_REQUESTED = "Admin User Creation Requested"

# Service Names
class ServiceNames:
    PRODUCT_SERVICE = "product-service"
    ORDER_SERVICE = "order-service"
    USER_SERVICE = "user-service"
    AI_DESCRIPTION_SERVICE = "ai-description-service"
    METRICS_SERVICE = "metrics-service"
    COST_ANALYSIS_SERVICE = "cost-analysis-service"

# Metric Names for Aggregation
class MetricNames:
    API_GATEWAY_REQUESTS = "api_gateway_requests"
    LAMBDA_GB_SECONDS = "lambda_gb_seconds"
    LAMBDA_REQUESTS = "lambda_requests"
    DYNAMODB_RCU_CONSUMED = "dynamodb_rcu_consumed"
    DYNAMODB_WCU_CONSUMED = "dynamodb_wcu_consumed"
    BEDROCK_INPUT_TOKENS = "bedrock_input_tokens"
    BEDROCK_OUTPUT_TOKENS = "bedrock_output_tokens"
    S3_REQUESTS = "s3_requests"
    S3_STORAGE_GB_HOURS = "s3_storage_gb_hours"

# AWS Pricing Constants
class Pricing:
    API_GATEWAY_REQUESTS = 3.50e-6  # $3.50 per million requests
    LAMBDA_GB_SECOND = 0.0000166667  # $0.0000166667 per GB-second
    LAMBDA_REQUEST = 2.0e-7  # $0.20 per million requests
    DYNAMODB_WCU = 1.25e-6  # $1.25 per million WCUs
    DYNAMODB_RCU = 0.25e-6  # $0.25 per million RCUs
    # Pricing for Claude Sonnet 4.5 (us.anthropic.claude-sonnet-4-5-20250929-v1:0)
    CLAUDE_SONNET_INPUT_TOKEN = 3.0e-6  # $3.00 per million input tokens
    CLAUDE_SONNET_OUTPUT_TOKEN = 15.0e-6  # $15.00 per million output tokens
    S3_REQUESTS = 0.4e-3  # $0.40 per 1000 requests
    S3_STORAGE_GB_MONTH = 0.023  # $0.023 per GB per month
