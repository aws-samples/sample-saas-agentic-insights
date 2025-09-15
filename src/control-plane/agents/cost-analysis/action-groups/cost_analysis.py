"""
COST ANALYSIS ACTION GROUP
Purpose: Per-tenant detailed profitability analysis

Extracts:
├── Individual tenant costs (tenant-by-tenant breakdown)
├── Tenant tier information (basic vs premium)
├── Revenue calculations per tenant ($29 vs $99)
├── Profit margins per tenant
└── Tenant names and IDs

Returns data for AI agent sections:
- === TENANT ANALYSIS === (TenantID | TierName | MonthlyCost | MonthlyRevenue | Margin)
- Platform margin calculation for === OVERVIEW METRICS ===
"""

import json
import boto3
import os
from datetime import datetime, timedelta
from decimal import Decimal
from boto3.dynamodb.conditions import Key

def handler(event, context):
    """Action Group Lambda for per-tenant cost analysis and profitability"""
    
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
    """Analyze costs and profitability for each tenant individually"""
    
    print(f"DEBUG: Starting tenant analysis with tenant_ids: {tenant_ids}")
    
    tenant_analyses = []
    tenants_table = boto3.resource('dynamodb').Table('Tenants')
    aggregation_table = boto3.resource('dynamodb').Table(os.environ['METRICS_AGGREGATION_TABLE_NAME'])
    
    # Get current month date range
    end_date = datetime.now().date()
    start_date = end_date.replace(day=1)
    month_filter = start_date.strftime('%Y-%m')
    
    print(f"DEBUG: Filtering by month: {month_filter}")
    
    # Get all tenants if 'all' specified
    if tenant_ids == ['all']:
        response = tenants_table.scan()
        tenant_ids = [item['tenant_id'] for item in response['Items']]
        print(f"DEBUG: Found {len(tenant_ids)} tenants: {tenant_ids}")
    
    total_revenue = 0
    total_cost = 0
    
    for tenant_id in tenant_ids:
        if not tenant_id.strip():
            continue
            
        try:
            print(f"DEBUG: Processing tenant: {tenant_id}")
            
            # Get tenant info from Tenants table
            tenant_response = tenants_table.get_item(Key={'tenant_id': tenant_id.strip()})
            if 'Item' not in tenant_response:
                print(f"DEBUG: Tenant {tenant_id} not found in Tenants table")
                continue
                
            tenant_info = tenant_response['Item']
            tier = tenant_info.get('tier', 'basic')
            tenant_name = tenant_info.get('tenant_name', tenant_id)
            
            print(f"DEBUG: Tenant {tenant_id} - {tenant_name} - {tier}")
            
            # Calculate tenant cost from aggregated metrics
            tenant_cost = 0
            
            # Query current month metrics for this tenant
            response = aggregation_table.query(
                KeyConditionExpression=Key('tenant_id').eq(tenant_id.strip()) & 
                                     Key('metric_date_type').begins_with(month_filter)
            )
            
            print(f"DEBUG: Found {len(response['Items'])} metrics for tenant {tenant_id}")
            
            for item in response['Items']:
                # Use pre-calculated cost if available
                if 'estimated_cost' in item:
                    cost = float(item['estimated_cost'])
                    tenant_cost += cost
                    print(f"DEBUG: Added cost {cost} from {item['metric_name']}")
            
            # Calculate revenue and margin
            revenue = 29.00 if tier == 'basic' else 99.00
            margin = revenue - tenant_cost
            margin_percentage = (margin / revenue * 100) if revenue > 0 else 0
            
            print(f"DEBUG: Tenant {tenant_id} - Cost: {tenant_cost}, Revenue: {revenue}, Margin: {margin_percentage}%")
            
            tenant_analyses.append({
                'tenant_id': tenant_id,
                'tenant_name': tenant_name,
                'tier': tier,
                'monthly_cost': round(tenant_cost, 2),
                'monthly_revenue': revenue,
                'margin': round(margin, 2),
                'margin_percentage': round(margin_percentage, 1)
            })
            
            total_revenue += revenue
            total_cost += tenant_cost
            
        except Exception as e:
            print(f"ERROR analyzing tenant {tenant_id}: {str(e)}")
            continue
    
    # Calculate platform-wide margin
    platform_margin = ((total_revenue - total_cost) / total_revenue * 100) if total_revenue > 0 else 0
    
    print(f"DEBUG: Final results - {len(tenant_analyses)} tenants analyzed")
    
    return {
        'tenant_analysis': tenant_analyses,
        'platform_totals': {
            'total_revenue': round(total_revenue, 2),
            'total_cost': round(total_cost, 2),
            'platform_margin_percentage': round(platform_margin, 1)
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
