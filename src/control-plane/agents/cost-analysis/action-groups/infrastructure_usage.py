import json
import boto3
import os
from datetime import datetime, timedelta
from decimal import Decimal
from boto3.dynamodb.conditions import Key

def handler(event, context):
    """Action Group Lambda for calculating infrastructure usage"""
    
    try:
        # Parse request body (Bedrock Agent format)
        request_body = event.get('requestBody', {})
        if isinstance(request_body, str):
            request_body = json.loads(request_body)
        
        tenant_ids = request_body.get('tenant_ids', ['all'])
        time_period = request_body.get('time_period', 'last_30_days')
        
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
    """Calculate infrastructure usage from aggregated metrics data"""
    
    pricing = {
        'api_gateway_requests': 3.50e-6,
        'lambda_gb_second': 0.0000166667,
        'lambda_request': 2.0e-7,
        'dynamodb_wcu': 1.25e-6,
        'dynamodb_rcu': 0.25e-6,
        'claude_haiku_input_token': 0.25e-6,
        'claude_haiku_output_token': 1.25e-6,
        's3_requests': 0.4e-3,
        's3_storage_gb_month': 0.023,
    }
    
    # Calculate date range
    end_date = datetime.now().date()
    if time_period == 'last_30_days':
        start_date = end_date - timedelta(days=30)
    elif time_period == 'last_7_days':
        start_date = end_date - timedelta(days=7)
    else:
        start_date = end_date - timedelta(days=30)
    
    total_costs = {'lambda': 0, 'dynamodb': 0, 'api_gateway': 0, 'bedrock': 0, 's3': 0}
    aggregation_table = boto3.resource('dynamodb').Table(os.environ['METRICS_AGGREGATION_TABLE_NAME'])
    
    for tenant_id in tenant_ids:
        if not tenant_id.strip():
            continue
            
        # Query aggregated metrics for this tenant in date range
        current_date = start_date
        while current_date <= end_date:
            date_str = current_date.strftime('%Y-%m-%d')
            
            response = aggregation_table.query(
                KeyConditionExpression=Key('tenant_id').eq(tenant_id.strip()) & 
                                     Key('metric_date_type').begins_with(date_str)
            )
            
            for item in response['Items']:
                metric_name = item['metric_name']
                sum_value = float(item['sum'])
                
                if metric_name == 'api_gateway_requests':
                    total_costs['api_gateway'] += sum_value * pricing['api_gateway_requests']
                elif metric_name == 'lambda_gb_seconds':
                    total_costs['lambda'] += sum_value * pricing['lambda_gb_second']
                elif metric_name == 'lambda_requests':
                    total_costs['lambda'] += sum_value * pricing['lambda_request']
                elif metric_name == 'dynamodb_rcu_consumed':
                    total_costs['dynamodb'] += sum_value * pricing['dynamodb_rcu']
                elif metric_name == 'dynamodb_wcu_consumed':
                    total_costs['dynamodb'] += sum_value * pricing['dynamodb_wcu']
                elif metric_name == 'bedrock_input_tokens':
                    total_costs['bedrock'] += sum_value * pricing['claude_haiku_input_token']
                elif metric_name == 'bedrock_output_tokens':
                    total_costs['bedrock'] += sum_value * pricing['claude_haiku_output_token']
                elif metric_name == 's3_requests':
                    total_costs['s3'] += sum_value * pricing['s3_requests'] / 1000
                elif metric_name == 's3_storage_gb_hours':
                    total_costs['s3'] += sum_value * pricing['s3_storage_gb_month'] / (30 * 24)
            
            current_date += timedelta(days=1)
    
    total_cost = sum(total_costs.values())
    tenant_count = len([t for t in tenant_ids if t.strip()])
    
    return {
        'platform_totals': {
            'total_cost': total_cost,
            'total_tenants': tenant_count,
            'avg_cost_per_tenant': total_cost / max(tenant_count, 1)
        },
        'service_breakdown': {
            service: {
                'cost': cost,
                'percentage': (cost / total_cost * 100) if total_cost > 0 else 0
            }
            for service, cost in total_costs.items()
        }
    }

def decimal_serializer(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
