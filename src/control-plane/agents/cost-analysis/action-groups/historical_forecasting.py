import json
import boto3
import os
from datetime import datetime, timedelta
from decimal import Decimal
from boto3.dynamodb.conditions import Key

def handler(event, context):
    """
    Action Group: historical-cost-forecasting
    Action: get-historical-trends-and-forecasting-data
    
    Expected JSON Response Format:
    {
      "analysis_period": {
        "months_analyzed": 3,
        "start_month": "2025-07", 
        "end_month": "2025-09"
      },
      "historical_cost_trends": [
        {
          "tier": "basic",
          "monthly_data": [
            {"month": "2025-07", "avg_cost_per_tenant": 0.00, "tenant_count": 0},
            {"month": "2025-08", "avg_cost_per_tenant": 0.00, "tenant_count": 0}, 
            {"month": "2025-09", "avg_cost_per_tenant": 50.00, "tenant_count": 1}
          ]
        }
      ],
      "historical_revenue_trends": [
        {
          "tier": "basic", 
          "monthly_data": [
            {"month": "2025-07", "total_cost": 0.00, "total_revenue": 0.00, "margin": 0.00},
            {"month": "2025-08", "total_cost": 0.00, "total_revenue": 0.00, "margin": 0.00},
            {"month": "2025-09", "total_cost": 50.00, "total_revenue": 29.00, "margin": -21.00}
          ]
        }
      ],
      "trend_summary": {
        "basic_tier": {
          "cost_trend": "new_tier_started",
          "growth_rate": 0.0
        },
        "premium_tier": {
          "cost_trend": "stable", 
          "growth_rate": 0.0
        }
      }
    }
    """
    
    try:
        # Handle both dict and string inputs from Bedrock Agent
        if isinstance(event, dict):
            request_body = event.get('requestBody', {})
            if isinstance(request_body, str):
                request_body = json.loads(request_body)
        else:
            request_body = json.loads(event.get('requestBody', '{}'))
        
        months_back = request_body.get('months_back', 3)
        
        # Get historical data
        result = get_historical_trends_data(months_back)
        
        # Log the JSON response before returning
        print(f"DEBUG: Returning JSON response to agent: {json.dumps(result, indent=2, default=decimal_serializer)}")
        
        return {
            'messageVersion': '1.0',
            'response': {
                'actionGroup': 'historical-cost-forecasting',
                'apiPath': '/get-historical-trends-and-forecasting-data',
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
        print(f"Error in historical forecasting: {str(e)}")
        return {
            'messageVersion': '1.0',
            'response': {
                'actionGroup': 'historical-cost-forecasting',
                'apiPath': '/get-historical-trends-and-forecasting-data',
                'httpMethod': 'POST',
                'httpStatusCode': 500,
                'responseBody': {
                    'application/json': {
                        'body': json.dumps({
                            'error': str(e),
                            'error_type': 'historical_forecasting_error'
                        })
                    }
                }
            }
        }

def get_historical_trends_data(months_back):
    """Get historical cost and revenue trends for forecasting"""
    
    aggregation_table = boto3.resource('dynamodb').Table(os.environ['METRICS_AGGREGATION_TABLE_NAME'])
    
    # Generate list of months to analyze
    current_date = datetime.now()
    months_to_analyze = []
    
    for i in range(months_back):
        month_date = current_date.replace(day=1) - timedelta(days=i*30)
        month_str = month_date.strftime('%Y-%m')
        months_to_analyze.append(month_str)
    
    months_to_analyze.reverse()  # Chronological order
    
    print(f"DEBUG: Analyzing months: {months_to_analyze}")
    
    # Collect data for each month
    monthly_data = {}
    
    for month in months_to_analyze:
        print(f"DEBUG: Processing month {month}")
        
        # Query all metrics for this month using MonthIndex GSI
        response = aggregation_table.query(
            IndexName='MonthIndex',
            KeyConditionExpression=Key('month').eq(month)
        )
        
        print(f"DEBUG: Found {len(response['Items'])} metrics for {month}")
        
        # Group by tier and tenant
        tier_data = {'basic': {}, 'premium': {}}
        
        for item in response['Items']:
            tenant_id = item['tenant_id']
            tier_name = item['tier_name']
            estimated_cost = float(item['estimated_cost'])
            
            if tenant_id not in tier_data[tier_name]:
                tier_data[tier_name][tenant_id] = 0.0
            
            tier_data[tier_name][tenant_id] += estimated_cost
        
        monthly_data[month] = tier_data
    
    # Build historical cost trends
    historical_cost_trends = []
    
    for tier in ['basic', 'premium']:
        monthly_cost_data = []
        
        for month in months_to_analyze:
            tenant_costs = list(monthly_data[month][tier].values())
            tenant_count = len(tenant_costs)
            avg_cost = sum(tenant_costs) / tenant_count if tenant_count > 0 else 0.0
            
            monthly_cost_data.append({
                'month': month,
                'avg_cost_per_tenant': round(avg_cost, 2),
                'tenant_count': tenant_count
            })
        
        historical_cost_trends.append({
            'tier': tier,
            'monthly_data': monthly_cost_data
        })
    
    # Build historical revenue trends
    historical_revenue_trends = []
    
    for tier in ['basic', 'premium']:
        monthly_revenue_data = []
        revenue_per_tenant = 29.00 if tier == 'basic' else 99.00
        
        for month in months_to_analyze:
            tenant_costs = list(monthly_data[month][tier].values())
            tenant_count = len(tenant_costs)
            total_cost = sum(tenant_costs)
            total_revenue = tenant_count * revenue_per_tenant
            margin = total_revenue - total_cost
            
            monthly_revenue_data.append({
                'month': month,
                'total_cost': round(total_cost, 2),
                'total_revenue': round(total_revenue, 2),
                'margin': round(margin, 2)
            })
        
        historical_revenue_trends.append({
            'tier': tier,
            'monthly_data': monthly_revenue_data
        })
    
    # Calculate trend summary
    trend_summary = {}
    
    for tier in ['basic', 'premium']:
        tier_costs = [data['avg_cost_per_tenant'] for data in 
                     next(t for t in historical_cost_trends if t['tier'] == tier)['monthly_data']]
        
        # Calculate growth rate
        non_zero_costs = [c for c in tier_costs if c > 0]
        if len(non_zero_costs) >= 2:
            growth_rate = (non_zero_costs[-1] - non_zero_costs[0]) / non_zero_costs[0]
            if growth_rate == 0:
                trend = 'stable'
            elif growth_rate > 0:
                trend = 'growing'
            else:
                trend = 'declining'
        elif len(non_zero_costs) == 1:
            growth_rate = 0.0
            trend = 'new_tier_started'
        else:
            growth_rate = 0.0
            trend = 'no_data'
        
        trend_summary[f'{tier}_tier'] = {
            'cost_trend': trend,
            'growth_rate': round(growth_rate, 3)
        }
    
    result = {
        'analysis_period': {
            'months_analyzed': months_back,
            'start_month': months_to_analyze[0],
            'end_month': months_to_analyze[-1]
        },
        'historical_cost_trends': historical_cost_trends,
        'historical_revenue_trends': historical_revenue_trends,
        'trend_summary': trend_summary
    }
    
    return result

def decimal_serializer(obj):
    """JSON serializer for Decimal objects"""
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
