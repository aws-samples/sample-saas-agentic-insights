import json
import boto3
import os
from datetime import datetime, timedelta
from decimal import Decimal
from boto3.dynamodb.conditions import Key

def handler(event, context):
    """Action Group Lambda for cost analysis per tenant"""
    
    try:
        # Parse request body (Bedrock Agent format)
        request_body = event.get('requestBody', {})
        if isinstance(request_body, str):
            request_body = json.loads(request_body)
        
        tenant_ids = request_body.get('tenant_ids', ['all'])
        
        analysis_data = analyze_tenant_costs(tenant_ids)
        
        return {
            "messageVersion": "1.0",
            "response": {
                "actionGroup": "cost-analysis",
                "apiPath": "/analyze-costs",
                "httpMethod": "POST",
                "httpStatusCode": 200,
                "responseBody": {
                    "application/json": {
                        "body": json.dumps(analysis_data, default=decimal_serializer)
                    }
                }
            }
        }
        
    except Exception as e:
        return {
            "messageVersion": "1.0",
            "response": {
                "actionGroup": "cost-analysis",
                "apiPath": "/analyze-costs",
                "httpMethod": "POST",
                "httpStatusCode": 500,
                "responseBody": {
                    "application/json": {
                        "body": json.dumps({'error': str(e), 'error_type': 'processing_error'})
                    }
                }
            }
        }

def analyze_tenant_costs(tenant_ids):
    """Analyze costs for each tenant with real data"""
    
    tenant_analyses = []
    tenants_table = boto3.resource('dynamodb').Table('Tenants')
    aggregation_table = boto3.resource('dynamodb').Table(os.environ['METRICS_AGGREGATION_TABLE_NAME'])
    
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
    
    # Get current month date range
    end_date = datetime.now().date()
    start_date = end_date.replace(day=1)  # First day of current month
    
    for tenant_id in tenant_ids:
        if not tenant_id.strip():
            continue
            
        try:
            # Get tenant tier from Tenants table
            tenant_response = tenants_table.get_item(Key={'tenant_id': tenant_id.strip()})
            if 'Item' not in tenant_response:
                continue
                
            tenant_info = tenant_response['Item']
            tier = tenant_info.get('tier', 'basic')
            tenant_name = tenant_info.get('tenant_name', tenant_id)
            
            # Calculate total cost for this tenant
            total_cost = 0
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
                        total_cost += sum_value * pricing['api_gateway_requests']
                    elif metric_name == 'lambda_gb_seconds':
                        total_cost += sum_value * pricing['lambda_gb_second']
                    elif metric_name == 'lambda_requests':
                        total_cost += sum_value * pricing['lambda_request']
                    elif metric_name == 'dynamodb_rcu_consumed':
                        total_cost += sum_value * pricing['dynamodb_rcu']
                    elif metric_name == 'dynamodb_wcu_consumed':
                        total_cost += sum_value * pricing['dynamodb_wcu']
                    elif metric_name == 'bedrock_input_tokens':
                        total_cost += sum_value * pricing['claude_haiku_input_token']
                    elif metric_name == 'bedrock_output_tokens':
                        total_cost += sum_value * pricing['claude_haiku_output_token']
                    elif metric_name == 's3_requests':
                        total_cost += sum_value * pricing['s3_requests'] / 1000
                    elif metric_name == 's3_storage_gb_hours':
                        total_cost += sum_value * pricing['s3_storage_gb_month'] / (30 * 24)
                
                current_date += timedelta(days=1)
            
            # Calculate revenue and margin
            revenue = 29.00 if tier == 'basic' else 99.00
            margin = revenue - total_cost
            margin_percentage = (margin / revenue * 100) if revenue > 0 else 0
            
            analysis = {
                'tenant_id': tenant_id.strip(),
                'tenant_name': tenant_name,
                'tier': tier,
                'total_cost': total_cost,
                'revenue': revenue,
                'margin': margin,
                'margin_percentage': margin_percentage,
                'status': 'profitable' if margin > 0 else 'loss_making'
            }
            
            tenant_analyses.append(analysis)
            
        except Exception as e:
            print(f"Error analyzing tenant {tenant_id}: {str(e)}")
            continue
    
    # Sort by cost descending
    tenant_analyses.sort(key=lambda x: x['total_cost'], reverse=True)
    
    # Calculate tier comparison
    basic_tenants = [t for t in tenant_analyses if t['tier'] == 'basic']
    premium_tenants = [t for t in tenant_analyses if t['tier'] == 'premium']
    
    return {
        'tenant_analysis': tenant_analyses,
        'tier_comparison': {
            'basic_tier': {
                'tenant_count': len(basic_tenants),
                'avg_cost': sum(t['total_cost'] for t in basic_tenants) / max(len(basic_tenants), 1),
                'avg_margin': sum(t['margin'] for t in basic_tenants) / max(len(basic_tenants), 1),
                'total_profit_loss': sum(t['margin'] for t in basic_tenants)
            },
            'premium_tier': {
                'tenant_count': len(premium_tenants),
                'avg_cost': sum(t['total_cost'] for t in premium_tenants) / max(len(premium_tenants), 1),
                'avg_margin': sum(t['margin'] for t in premium_tenants) / max(len(premium_tenants), 1),
                'total_profit_loss': sum(t['margin'] for t in premium_tenants)
            }
        }
    }

def decimal_serializer(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
