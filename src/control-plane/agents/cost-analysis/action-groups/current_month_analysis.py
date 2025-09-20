import json
import boto3
import os
from datetime import datetime
from decimal import Decimal
from boto3.dynamodb.conditions import Key

def handler(event, context):
    """
    Action Group: current-month-cost-analysis
    Action: get-current-month-tenant-and-platform-metrics
    
    Expected JSON Response Format:
    {
      "current_month": "2025-09",
      "tenant_analysis": [
        {
          "tenant_id": "233fc720-2bb6-459c-8f5e-c6b607115f55",
          "tier": "premium", 
          "cost": 100.00,
          "revenue": 99.00,
          "margin": -1.00,
          "margin_percentage": -1.01
        }
      ],
      "platform_overview": {
        "total_platform_cost": 150.00,
        "total_platform_revenue": 128.00,
        "platform_margin": -22.00,
        "platform_margin_percentage": -17.19,
        "average_cost_per_tenant_basic": 50.00,
        "average_cost_per_tenant_premium": 100.00,
        "tenant_count_basic": 1,
        "tenant_count_premium": 1
      },
      "service_breakdown": [
        {
          "tier": "basic",
          "lambda_cost": 20.00,
          "dynamodb_cost": 20.00,
          "api_gateway_cost": 10.00,
          "total_tier_cost": 50.00
        }
      ]
    }
    """
    
    try:
        # Get current month (YYYY-MM format)
        current_month = datetime.now().strftime('%Y-%m')
        
        # Get current month data
        result = get_current_month_data(current_month)
        
        # Log the JSON response before returning
        print(f"DEBUG: Returning JSON response to agent: {json.dumps(result, indent=2, default=decimal_serializer)}")
        
        return {
            'messageVersion': '1.0',
            'response': {
                'actionGroup': 'current-month-cost-analysis',
                'apiPath': '/get-current-month-tenant-and-platform-metrics',
                'httpMethod': 'POST',
                'httpStatusCode': 200,
                'responseBody': {
                    'application/json': {
                        'body': json.dumps(result, default=decimal_serializer)
                    }
                }
            }
        }
        
    except Exception as e:
        print(f"Error in current month analysis: {str(e)}")
        return {
            'messageVersion': '1.0',
            'response': {
                'actionGroup': 'current-month-cost-analysis',
                'apiPath': '/get-current-month-tenant-and-platform-metrics',
                'httpMethod': 'POST',
                'httpStatusCode': 500,
                'responseBody': {
                    'application/json': {
                        'body': json.dumps({
                            'error': str(e),
                            'error_type': 'current_month_analysis_error'
                        })
                    }
                }
            }
        }

def get_current_month_data(current_month):
    """Get comprehensive current month analysis"""
    
    aggregation_table = boto3.resource('dynamodb').Table(os.environ['METRICS_AGGREGATION_TABLE_NAME'])
    
    print(f"DEBUG: Analyzing current month: {current_month}")
    
    # Query all metrics for current month using MonthIndex GSI
    response = aggregation_table.query(
        IndexName='MonthIndex',
        KeyConditionExpression=Key('month').eq(current_month)
    )
    
    print(f"DEBUG: Found {len(response['Items'])} metrics for {current_month}")
    
    # Group data by tenant
    tenant_data = {}
    service_costs_by_tier = {'basic': {}, 'premium': {}}
    
    for item in response['Items']:
        tenant_id = item['tenant_id']
        tier_name = item['tier_name']
        metric_name = item['metric_name']
        estimated_cost = float(item['estimated_cost'])
        
        # Initialize tenant data
        if tenant_id not in tenant_data:
            tenant_data[tenant_id] = {
                'tenant_id': tenant_id,
                'tier': tier_name,
                'cost': 0.0,
                'revenue': 29.00 if tier_name == 'basic' else 99.00
            }
        
        # Add cost to tenant
        tenant_data[tenant_id]['cost'] += estimated_cost
        
        # Categorize service costs by tier
        service_type = get_service_type(metric_name)
        if service_type not in service_costs_by_tier[tier_name]:
            service_costs_by_tier[tier_name][service_type] = 0.0
        service_costs_by_tier[tier_name][service_type] += estimated_cost
    
    # Calculate tenant analysis with margins
    tenant_analysis = []
    for tenant in tenant_data.values():
        margin = tenant['revenue'] - tenant['cost']
        margin_percentage = (margin / tenant['revenue'] * 100) if tenant['revenue'] > 0 else 0
        
        tenant_analysis.append({
            'tenant_id': tenant['tenant_id'],
            'tier': tenant['tier'],
            'cost': round(tenant['cost'], 2),
            'revenue': round(tenant['revenue'], 2),
            'margin': round(margin, 2),
            'margin_percentage': round(margin_percentage, 2)
        })
    
    # Calculate platform overview
    total_cost = sum(t['cost'] for t in tenant_analysis)
    total_revenue = sum(t['revenue'] for t in tenant_analysis)
    platform_margin = total_revenue - total_cost
    platform_margin_percentage = (platform_margin / total_revenue * 100) if total_revenue > 0 else 0
    
    # Calculate averages by tier
    basic_tenants = [t for t in tenant_analysis if t['tier'] == 'basic']
    premium_tenants = [t for t in tenant_analysis if t['tier'] == 'premium']
    
    avg_cost_basic = sum(t['cost'] for t in basic_tenants) / len(basic_tenants) if basic_tenants else 0
    avg_cost_premium = sum(t['cost'] for t in premium_tenants) / len(premium_tenants) if premium_tenants else 0
    
    platform_overview = {
        'total_platform_cost': round(total_cost, 2),
        'total_platform_revenue': round(total_revenue, 2),
        'platform_margin': round(platform_margin, 2),
        'platform_margin_percentage': round(platform_margin_percentage, 2),
        'average_cost_per_tenant_basic': round(avg_cost_basic, 2),
        'average_cost_per_tenant_premium': round(avg_cost_premium, 2),
        'tenant_count_basic': len(basic_tenants),
        'tenant_count_premium': len(premium_tenants)
    }
    
    # Build service breakdown
    service_breakdown = []
    for tier in ['basic', 'premium']:
        if service_costs_by_tier[tier]:
            tier_data = {
                'tier': tier,
                'lambda_cost': round(service_costs_by_tier[tier].get('lambda', 0), 2),
                'dynamodb_cost': round(service_costs_by_tier[tier].get('dynamodb', 0), 2),
                'api_gateway_cost': round(service_costs_by_tier[tier].get('api_gateway', 0), 2),
                'total_tier_cost': round(sum(service_costs_by_tier[tier].values()), 2)
            }
            service_breakdown.append(tier_data)
    
    result = {
        'current_month': current_month,
        'tenant_analysis': tenant_analysis,
        'platform_overview': platform_overview,
        'service_breakdown': service_breakdown
    }
    
    return result

def get_service_type(metric_name):
    """Map metric name to service type"""
    if 'lambda' in metric_name:
        return 'lambda'
    elif 'dynamodb' in metric_name:
        return 'dynamodb'
    elif 'api_gateway' in metric_name:
        return 'api_gateway'
    elif 'bedrock' in metric_name:
        return 'bedrock'
    else:
        return 'other'

def decimal_serializer(obj):
    """JSON serializer for Decimal objects"""
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
