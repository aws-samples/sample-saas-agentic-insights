import json
import boto3
import os
from datetime import datetime, timedelta
from decimal import Decimal
from boto3.dynamodb.conditions import Key

def handler(event, context):
    """Action Group Lambda for cost prediction"""
    
    try:
        # Parse request body (Bedrock Agent format)
        request_body = event.get('requestBody', {})
        if isinstance(request_body, str):
            request_body = json.loads(request_body)
        
        tenant_ids = request_body.get('tenant_ids', ['all'])
        forecast_months = request_body.get('forecast_months', 3)
        
        prediction_data = predict_tenant_costs(tenant_ids, forecast_months)
        
        return {
            "messageVersion": "1.0",
            "response": {
                "actionGroup": "cost-prediction",
                "apiPath": "/predict-costs",
                "httpMethod": "POST",
                "httpStatusCode": 200,
                "responseBody": {
                    "application/json": {
                        "body": json.dumps(prediction_data, default=decimal_serializer)
                    }
                }
            }
        }
        
    except Exception as e:
        return {
            "messageVersion": "1.0",
            "response": {
                "actionGroup": "cost-prediction",
                "apiPath": "/predict-costs",
                "httpMethod": "POST",
                "httpStatusCode": 500,
                "responseBody": {
                    "application/json": {
                        "body": json.dumps({'error': str(e), 'error_type': 'processing_error'})
                    }
                }
            }
        }

def predict_tenant_costs(tenant_ids, forecast_months):
    """Predict future costs based on historical trends"""
    
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
    
    predictions = []
    
    # Get historical data for trend analysis (last 3 months)
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=90)
    
    for tenant_id in tenant_ids:
        if not tenant_id.strip():
            continue
            
        try:
            # Calculate monthly costs for trend analysis
            monthly_costs = []
            
            for month_offset in range(3):  # Last 3 months
                month_start = (end_date.replace(day=1) - timedelta(days=month_offset * 30)).replace(day=1)
                month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
                
                monthly_cost = 0
                current_date = month_start
                
                while current_date <= month_end:
                    date_str = current_date.strftime('%Y-%m-%d')
                    
                    response = aggregation_table.query(
                        KeyConditionExpression=Key('tenant_id').eq(tenant_id.strip()) & 
                                             Key('metric_date_type').begins_with(date_str)
                    )
                    
                    for item in response['Items']:
                        metric_name = item['metric_name']
                        sum_value = float(item['sum'])
                        
                        if metric_name == 'api_gateway_requests':
                            monthly_cost += sum_value * pricing['api_gateway_requests']
                        elif metric_name == 'lambda_gb_seconds':
                            monthly_cost += sum_value * pricing['lambda_gb_second']
                        elif metric_name == 'lambda_requests':
                            monthly_cost += sum_value * pricing['lambda_request']
                        elif metric_name == 'dynamodb_rcu_consumed':
                            monthly_cost += sum_value * pricing['dynamodb_rcu']
                        elif metric_name == 'dynamodb_wcu_consumed':
                            monthly_cost += sum_value * pricing['dynamodb_wcu']
                        elif metric_name == 'bedrock_input_tokens':
                            monthly_cost += sum_value * pricing['claude_haiku_input_token']
                        elif metric_name == 'bedrock_output_tokens':
                            monthly_cost += sum_value * pricing['claude_haiku_output_token']
                        elif metric_name == 's3_requests':
                            monthly_cost += sum_value * pricing['s3_requests'] / 1000
                        elif metric_name == 's3_storage_gb_hours':
                            monthly_cost += sum_value * pricing['s3_storage_gb_month'] / (30 * 24)
                    
                    current_date += timedelta(days=1)
                
                monthly_costs.append(monthly_cost)
            
            # Calculate growth rate from historical data
            if len(monthly_costs) >= 2 and monthly_costs[-1] > 0:
                # Simple linear growth calculation
                recent_avg = sum(monthly_costs[-2:]) / 2
                older_avg = sum(monthly_costs[:-2]) / max(len(monthly_costs[:-2]), 1)
                growth_rate = (recent_avg - older_avg) / max(older_avg, 0.01) if older_avg > 0 else 0.05
            else:
                growth_rate = 0.05  # Default 5% growth
            
            # Cap growth rate between -50% and +100%
            growth_rate = max(-0.5, min(1.0, growth_rate))
            
            current_cost = monthly_costs[0] if monthly_costs else 0
            
            # Generate predictions
            monthly_predictions = []
            for month in range(1, forecast_months + 1):
                predicted_cost = current_cost * (1 + growth_rate) ** month
                confidence = max(0.6, 0.9 - (month * 0.1))  # Decreasing confidence over time
                
                monthly_predictions.append({
                    'month': month,
                    'predicted_cost': predicted_cost,
                    'confidence': confidence
                })
            
            predictions.append({
                'tenant_id': tenant_id.strip(),
                'current_monthly_cost': current_cost,
                'growth_rate': growth_rate,
                'predictions': monthly_predictions,
                'total_predicted_cost': sum(p['predicted_cost'] for p in monthly_predictions),
                'historical_costs': monthly_costs
            })
            
        except Exception as e:
            print(f"Error predicting costs for tenant {tenant_id}: {str(e)}")
            continue
    
    # Platform-wide predictions
    total_current = sum(p['current_monthly_cost'] for p in predictions)
    total_predicted = sum(p['total_predicted_cost'] for p in predictions)
    
    return {
        'tenant_predictions': predictions,
        'platform_forecast': {
            'current_monthly_total': total_current,
            'predicted_total': total_predicted,
            'growth_projection': ((total_predicted / (total_current * forecast_months)) - 1) * 100 if total_current > 0 else 0,
            'confidence_level': 0.75,
            'key_drivers': ['tenant_growth', 'ai_usage_increase', 'feature_adoption'],
            'forecast_months': forecast_months
        }
    }

def decimal_serializer(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
