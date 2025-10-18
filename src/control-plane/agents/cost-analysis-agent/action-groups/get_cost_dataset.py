import json
import boto3
import os
import random
import math
from datetime import datetime, timedelta
from decimal import Decimal
from collections import defaultdict

def handler(event, context):
    """
    Action Group: cost-dataset-fetcher
    Action: getCostPerTenantDataset
    
    Fetches CostPerTenant dataset, calculates averages per month per tier,
    and generates cost predictions for next 6 months using Monte Carlo simulation
    """
    
    try:
        # Get CostPerTenant table
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table(os.environ['COST_PER_TENANT_TABLE_NAME'])
        
        # Scan entire table
        response = table.scan()
        items = response['Items']
        
        # Handle pagination if needed
        while 'LastEvaluatedKey' in response:
            response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
            items.extend(response['Items'])
        
        # Group data by month and tier for averaging
        grouped = defaultdict(lambda: {'costs': [], 'revenues': [], 'margins': []})
        
        for item in items:
            month = item.get('month', '')
            tier = item.get('tier', '')
            cost = float(item.get('cost', 0))
            revenue = float(item.get('revenue', 0))
            margin = float(item.get('margin', 0))
            
            key = (month, tier)
            grouped[key]['costs'].append(cost)
            grouped[key]['revenues'].append(revenue)
            grouped[key]['margins'].append(margin)
        
        # Calculate averages per month per tier
        averaged_data = []
        for (month, tier), values in grouped.items():
            avg_cost = sum(values['costs']) / len(values['costs'])
            avg_revenue = sum(values['revenues']) / len(values['revenues'])
            avg_margin = sum(values['margins']) / len(values['margins'])
            
            averaged_data.append({
                'month': month,
                'tier': tier,
                'cost': round(avg_cost, 1),
                'revenue': round(avg_revenue, 1),
                'margin': round(avg_margin, 1)
            })
        
        # Sort by month and tier
        averaged_data.sort(key=lambda x: (x['month'], x['tier']))
        
        # Generate Monte Carlo predictions for next 6 months
        cost_predictions = generate_monte_carlo_predictions(averaged_data)
        
        result = {
            'total_records': len(items),
            'cost_per_tenant_averages': averaged_data,
            'cost_per_tenant_predictions': cost_predictions,
            'prediction_metadata': {
                'method': 'monte_carlo_simulation',
                'simulation_runs': 1000,
                'confidence_level': '80_percent',
                'forecast_months': 6
            }
        }
        
        print(f"DEBUG: Processed {len(items)} records into {len(averaged_data)} averaged records")
        print("DEBUG: Averaged Dataset JSON:")
        print(json.dumps(averaged_data, indent=2))
        print(f"DEBUG: Generated {len(cost_predictions)} Monte Carlo predictions")
        print("DEBUG: Cost Predictions JSON:")
        print(json.dumps(cost_predictions, indent=2))
        
        return {
            'messageVersion': '1.0',
            'response': {
                'actionGroup': 'cost-dataset-fetcher',
                'apiPath': '/getCostPerTenantDataset',
                'httpMethod': 'GET',
                'httpStatusCode': 200,
                'responseBody': {
                    'application/json': {
                        'body': json.dumps(result, default=decimal_serializer)
                    }
                }
            }
        }
        
    except Exception as e:
        print(f"Error fetching dataset: {str(e)}")
        return {
            'messageVersion': '1.0',
            'response': {
                'actionGroup': 'cost-dataset-fetcher',
                'apiPath': '/getCostPerTenantDataset',
                'httpMethod': 'GET',
                'httpStatusCode': 500,
                'responseBody': {
                    'application/json': {
                        'body': json.dumps({
                            'error': str(e),
                            'error_type': 'dataset_fetch_error'
                        })
                    }
                }
            }
        }

def generate_monte_carlo_predictions(historical_data, months=6, simulations=1000):
    """
    Generate Monte Carlo cost predictions for next 6 months
    """
    predictions = []
    
    # Revenue per tier (fixed)
    tier_revenue = {
        'basic': 29.0,
        'premium': 99.0
    }
    
    for tier in ['basic', 'premium']:
        # Extract historical costs for this tier
        tier_costs = []
        for record in historical_data:
            if record['tier'] == tier:
                tier_costs.append(record['cost'])
        
        if not tier_costs:
            continue
            
        # Calculate statistics
        mean_cost = sum(tier_costs) / len(tier_costs)
        variance = sum((x - mean_cost) ** 2 for x in tier_costs) / len(tier_costs)
        std_dev = math.sqrt(variance)
        trend = calculate_trend(tier_costs)
        
        # Generate predictions for next 6 months
        for month in range(1, months + 1):
            simulated_costs = []
            
            # Run Monte Carlo simulation
            for _ in range(simulations):
                # Add trend + random variation (normal distribution approximation)
                random_factor = random.gauss(0, std_dev)
                predicted_cost = mean_cost + (trend * month) + random_factor
                # Ensure no negative costs
                predicted_cost = max(5.0, predicted_cost)  # Minimum $5 cost
                simulated_costs.append(predicted_cost)
            
            # Calculate statistics from simulation
            avg_predicted_cost = sum(simulated_costs) / len(simulated_costs)
            simulated_costs.sort()
            confidence_low = simulated_costs[int(0.1 * len(simulated_costs))]  # 10th percentile
            confidence_high = simulated_costs[int(0.9 * len(simulated_costs))]  # 90th percentile
            
            revenue = tier_revenue[tier]
            predicted_margin = revenue - avg_predicted_cost
            
            predictions.append({
                "month": get_future_month(month, historical_data),
                "tier": tier,
                "predicted_cost": round(avg_predicted_cost, 1),
                "confidence_low": round(confidence_low, 1),
                "confidence_high": round(confidence_high, 1),
                "revenue": revenue,
                "predicted_margin": round(predicted_margin, 1)
            })
    
    return predictions

def calculate_trend(costs):
    """
    Calculate linear trend from historical costs
    """
    if len(costs) < 2:
        return 0
    
    # Simple linear regression slope
    n = len(costs)
    x = list(range(n))
    y = costs
    
    # Calculate slope (trend)
    sum_x = sum(x)
    sum_y = sum(y)
    sum_xy = sum(x[i] * y[i] for i in range(n))
    sum_x2 = sum(xi ** 2 for xi in x)
    
    slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x ** 2)
    return slope

def get_future_month(months_ahead, historical_data):
    """
    Get future month string (YYYY-MM format) based on latest historical data
    """
    # Find the latest month in historical data
    latest_month = None
    for record in historical_data:
        if latest_month is None or record['month'] > latest_month:
            latest_month = record['month']
    
    # If no historical data, use current month as fallback
    if latest_month is None:
        latest_month = datetime.now().strftime("%Y-%m")
    
    # Parse latest month and add months_ahead
    year, month = map(int, latest_month.split('-'))
    base_date = datetime(year, month, 1)
    future_date = base_date + timedelta(days=30 * months_ahead)
    return future_date.strftime("%Y-%m")

def decimal_serializer(obj):
    """JSON serializer for Decimal objects"""
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
