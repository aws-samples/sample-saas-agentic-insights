"""
INFRASTRUCTURE USAGE ACTION GROUP
Purpose: Platform-wide aggregated data for OVERVIEW METRICS & SERVICE BREAKDOWN

Extracts:
├── Total platform costs by service (Lambda, DynamoDB, API Gateway, Bedrock)
├── Overall platform totals across ALL tenants
├── Service-level cost breakdown
└── Platform-wide averages

Returns data for AI agent sections:
- === OVERVIEW METRICS === (Total Platform Cost, Average Cost Per Tenant, Total AI Usage)
- === SERVICE BREAKDOWN === (Lambda Cost, DynamoDB Cost, API Gateway Cost, Bedrock AI Cost)
"""

import json
import boto3
import os
from datetime import datetime, timedelta
from decimal import Decimal
from boto3.dynamodb.conditions import Key

def handler(event, context):
    """Action Group Lambda for calculating platform-wide infrastructure usage"""
    
    try:
        # Parse request body (Bedrock Agent format)
        request_body = event.get('requestBody', {})
        if isinstance(request_body, str):
            request_body = json.loads(request_body)
        
        tenant_ids = request_body.get('tenant_ids', ['all'])
        time_period = request_body.get('time_period', 'current_month')
        
        usage_data = calculate_infrastructure_usage(tenant_ids, time_period)
        
        return {
            "messageVersion": "1.0",
            "response": {
                "actionGroup": "infrastructure-usage",
                "apiPath": "/calculate-usage",
                "httpMethod": "POST",
                "httpStatusCode": 200,
                "responseBody": {
                    "application/json": {
                        "body": json.dumps(usage_data, default=decimal_serializer)
                    }
                }
            }
        }
        
    except Exception as e:
        return {
            "messageVersion": "1.0",
            "response": {
                "actionGroup": "infrastructure-usage",
                "apiPath": "/calculate-usage",
                "httpMethod": "POST",
                "httpStatusCode": 500,
                "responseBody": {
                    "application/json": {
                        "body": json.dumps({'error': str(e), 'error_type': 'processing_error'})
                    }
                }
            }
        }

def calculate_infrastructure_usage(tenant_ids, time_period):
    """Calculate platform-wide infrastructure costs for OVERVIEW METRICS and SERVICE BREAKDOWN"""
    
    aggregation_table = boto3.resource('dynamodb').Table(os.environ['METRICS_AGGREGATION_TABLE_NAME'])
    
    # Get current month data
    end_date = datetime.now().date()
    start_date = end_date.replace(day=1)
    month_filter = start_date.strftime('%Y-%m')
    
    print(f"DEBUG: Filtering by month: {month_filter}")
    
    # Platform totals
    service_costs = {'lambda': 0, 'dynamodb': 0, 'api_gateway': 0, 'bedrock': 0}
    total_ai_usage = 0
    unique_tenants = set()
    
    # Query all metrics for current month
    response = aggregation_table.scan(
        FilterExpression='begins_with(metric_date_type, :month)',
        ExpressionAttributeValues={':month': month_filter}
    )
    
    print(f"DEBUG: Found {len(response['Items'])} items")
    
    for item in response['Items']:
        tenant_id = item['tenant_id']
        metric_name = item['metric_name']
        sum_value = float(item.get('sum', 0))
        
        print(f"DEBUG: Processing {tenant_id} - {metric_name} - sum: {sum_value}")
        
        unique_tenants.add(tenant_id)
        
        # Use pre-calculated costs from MetricsAggregation if available
        if 'estimated_cost' in item:
            cost = float(item['estimated_cost'])
            print(f"DEBUG: Found estimated_cost: {cost}")
            
            if 'lambda' in metric_name:
                service_costs['lambda'] += cost
            elif 'dynamodb' in metric_name:
                service_costs['dynamodb'] += cost
            elif 'api_gateway' in metric_name:
                service_costs['api_gateway'] += cost
            elif 'bedrock' in metric_name:
                service_costs['bedrock'] += cost
        
        # Track AI usage (tokens)
        if metric_name in ['bedrock_input_tokens', 'bedrock_output_tokens']:
            total_ai_usage += sum_value
    
    total_cost = sum(service_costs.values())
    tenant_count = len(unique_tenants)
    avg_cost_per_tenant = total_cost / tenant_count if tenant_count > 0 else 0
    
    print(f"DEBUG: Final totals - cost: {total_cost}, tenants: {tenant_count}, avg: {avg_cost_per_tenant}")
    
    return {
        'total_platform_cost': round(total_cost, 2),
        'average_cost_per_tenant': round(avg_cost_per_tenant, 2),
        'tenant_count': tenant_count,
        'total_ai_usage': int(total_ai_usage),
        'service_breakdown': {
            'lambda_cost': round(service_costs['lambda'], 2),
            'dynamodb_cost': round(service_costs['dynamodb'], 2),
            'api_gateway_cost': round(service_costs['api_gateway'], 2),
            'bedrock_cost': round(service_costs['bedrock'], 2)
        }
    }

def decimal_serializer(obj):
    """JSON serializer for Decimal objects"""
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

def decimal_serializer(obj):
    """JSON serializer for Decimal objects"""
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
