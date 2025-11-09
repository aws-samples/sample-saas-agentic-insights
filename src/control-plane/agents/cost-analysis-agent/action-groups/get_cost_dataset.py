import json
import boto3
import os
import random
import math
import time
from datetime import datetime, timedelta
from decimal import Decimal
from collections import defaultdict

def convert_floats_to_decimal(obj):
    """Recursively convert all float values to Decimal for DynamoDB compatibility"""
    if isinstance(obj, float):
        return Decimal(str(obj))
    elif isinstance(obj, dict):
        return {k: convert_floats_to_decimal(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_floats_to_decimal(item) for item in obj]
    else:
        return obj

def handler(event, context):
    """
    Action Group: cost-dataset-fetcher
    Action: getCostPerTenantDataset
    
    Fetches CostPerTenant dataset, calculates averages per month per tier,
    generates cost predictions, saves to cache table, and returns cache UID
    """
    
    try:
        # Get DynamoDB resources
        dynamodb = boto3.resource('dynamodb')
        cost_table = dynamodb.Table(os.environ['COST_PER_TENANT_TABLE_NAME'])
        cache_table = dynamodb.Table(os.environ['COST_ANALYSIS_CACHE_TABLE_NAME'])
        
        # Scan entire cost table
        response = cost_table.scan()
        items = response['Items']
        
        # Handle pagination if needed
        while 'LastEvaluatedKey' in response:
            response = cost_table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
            items.extend(response['Items'])
        
        # Group data by month and tier for averaging
        grouped = defaultdict(lambda: {'costs': [], 'revenues': [], 'margins': []})
        
        for item in items:
            month = item.get('month', '')
            tier = item.get('tier', '')
            cost = item.get('cost', 0)
            revenue = item.get('revenue', 0)
            margin = item.get('margin', 0)
            
            # Convert Decimal to float for calculations
            if isinstance(cost, Decimal):
                cost = float(cost)
            if isinstance(revenue, Decimal):
                revenue = float(revenue)
            if isinstance(margin, Decimal):
                margin = float(margin)
            
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
        
        # Create cache UID and save to cache table
        cache_uid = f"cost-data-{int(time.time())}"
        ttl = int(time.time()) + 3600  # 1 hour TTL
        
        # Convert all float values to Decimal for DynamoDB compatibility
        cache_item = {
            'cache_uid': cache_uid,
            'cost_per_tenant_averages': convert_floats_to_decimal(averaged_data),
            'cost_per_tenant_predictions': convert_floats_to_decimal(cost_predictions),
            'computed_at': datetime.utcnow().isoformat(),
            'total_records': len(items),
            'ttl': ttl
        }
        
        # Save to cache table
        cache_table.put_item(Item=cache_item)
        
        print(f"DEBUG: Processed {len(items)} records into {len(averaged_data)} averaged records")
        print(f"DEBUG: Generated {len(cost_predictions)} Monte Carlo predictions")
        print(f"DEBUG: Saved to cache with UID: {cache_uid}")
        
        # Return response with actual data for agent analysis
        result = {
            'cache_uid': cache_uid,
            'cost_per_tenant_averages': averaged_data,
            'cost_per_tenant_predictions': cost_predictions
        }
        
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
    Generate realistic hybrid Monte Carlo predictions with extreme volatility and state-based modeling
    """
    predictions = []
    
    # Revenue per tier (fixed) - use floats for calculations
    tier_revenue = {
        'basic': 29.0,
        'premium': 99.0
    }
    
    for tier in ['basic', 'premium']:
        # Extract chronological costs for this tier
        tier_records = []
        for record in historical_data:
            if record['tier'] == tier:
                cost_value = record['cost']
                # Ensure cost is float for calculations
                if isinstance(cost_value, Decimal):
                    cost_value = float(cost_value)
                tier_records.append((record['month'], cost_value))
        
        tier_records.sort(key=lambda x: x[0])  # Sort by month
        tier_costs = [cost for _, cost in tier_records]
        
        if len(tier_costs) < 3:
            continue
        
        # Calculate actual historical range and patterns
        min_cost = min(tier_costs)
        max_cost = max(tier_costs)
        cost_range = max_cost - min_cost
        
        # Detect cost states: Low, Medium, High
        low_threshold = min_cost + cost_range * 0.33
        high_threshold = min_cost + cost_range * 0.67
        
        # Classify recent months into states
        recent_states = []
        for cost in tier_costs[-3:]:
            if cost <= low_threshold:
                recent_states.append('low')
            elif cost >= high_threshold:
                recent_states.append('high')
            else:
                recent_states.append('medium')
        
        # State transition probabilities based on historical patterns
        current_state = recent_states[-1] if recent_states else 'medium'
        
        # Extreme volatility multiplier based on actual range
        volatility_factor = cost_range / 4  # Use quarter of historical range as base volatility
        
        # Generate predictions for next 6 months
        for month in range(1, months + 1):
            future_month_str = get_future_month(month, historical_data)
            future_month_num = int(future_month_str.split('-')[1])
            
            # Aggressive seasonal patterns based on historical extremes - use floats for calculations
            seasonal_factors = {
                1: 0.6, 2: 0.5, 3: 1.4, 4: 1.2, 
                5: 0.4, 6: 1.0, 7: 0.3, 8: 1.8, 
                9: 1.0, 10: 0.5, 11: 2.0, 12: 1.5
            }
            seasonal_factor = seasonal_factors.get(future_month_num, 1.0)
            
            simulated_costs = []
            
            # Run extreme volatility Monte Carlo simulation
            for _ in range(simulations):
                # State-based prediction with high transition probability
                if random.random() < 0.4:  # 40% chance of extreme state change
                    if current_state == 'high':
                        # High cost month often followed by low cost
                        base_cost = random.uniform(min_cost, low_threshold)
                    elif current_state == 'low':
                        # Low cost month can spike to high
                        base_cost = random.uniform(high_threshold, max_cost)
                    else:
                        # Medium can go anywhere
                        base_cost = random.uniform(min_cost, max_cost)
                else:
                    # Stay in similar range with some drift
                    last_cost = tier_costs[-1]
                    base_cost = last_cost + random.uniform(-cost_range*0.3, cost_range*0.3)
                
                # Apply aggressive seasonal adjustment
                seasonal_cost = base_cost * seasonal_factor
                
                # Add extreme volatility (50% chance of major swing)
                if random.random() < 0.5:
                    # Major swing event
                    swing_magnitude = volatility_factor * random.uniform(0.5, 2.0)
                    swing_direction = 1 if random.random() < 0.5 else -1
                    predicted_cost = seasonal_cost + (swing_magnitude * swing_direction)
                else:
                    # Normal variation
                    normal_variation = volatility_factor * random.uniform(-0.5, 0.5)
                    predicted_cost = seasonal_cost + normal_variation
                
                # Realistic bounds (allow extreme lows and highs)
                predicted_cost = max(8.0, min(predicted_cost, max_cost * 1.5))
                simulated_costs.append(predicted_cost)
            
            # Calculate statistics with wider confidence intervals
            avg_predicted_cost = sum(simulated_costs) / len(simulated_costs)
            simulated_costs.sort()
            confidence_low = simulated_costs[int(0.05 * len(simulated_costs))]  # 5th percentile
            confidence_high = simulated_costs[int(0.95 * len(simulated_costs))]  # 95th percentile
            
            revenue = tier_revenue[tier]
            predicted_margin = revenue - avg_predicted_cost
            
            predictions.append({
                "month": future_month_str,
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
    
    # Parse latest month and add months_ahead using proper month arithmetic
    year, month = map(int, latest_month.split('-'))
    month += months_ahead
    while month > 12:
        month -= 12
        year += 1
    
    return f"{year:04d}-{month:02d}"

def decimal_serializer(obj):
    """JSON serializer for Decimal objects"""
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
