"""
Trend Calculation Logic

Queries historical metrics from DynamoDB and calculates period-over-period trends,
growth rates, rolling averages, and seasonality indicators.
"""

import boto3
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Any, Optional
import statistics


dynamodb = boto3.resource('dynamodb')


def calculate_trends_for_metrics(
    table_name: str,
    current_metrics: List[Dict],
    time_period: str
) -> List[Dict]:
    """
    Calculate trends for current metrics by comparing with historical data
    
    Args:
        table_name: DynamoDB table name
        current_metrics: List of current metric dictionaries
        time_period: Time period (hourly, daily, monthly)
        
    Returns:
        List of metrics enriched with trend data
    """
    table = dynamodb.Table(table_name)
    enriched_metrics = []
    
    for metric in current_metrics:
        try:
            # Query historical metrics
            historical_metrics = query_historical_metrics(
                table,
                metric['tenant_id'],
                metric['metric_type'],
                metric['timestamp'],
                time_period
            )
            
            # Calculate trends
            trend_data = calculate_trend_indicators(
                metric,
                historical_metrics,
                time_period
            )
            
            # Merge trend data into metric
            enriched_metric = {**metric, **trend_data}
            enriched_metrics.append(enriched_metric)
            
        except Exception as e:
            print(f"Warning: Error calculating trends for metric: {str(e)}")
            # Add metric without trend data
            enriched_metrics.append(metric)
            continue
    
    return enriched_metrics


def query_historical_metrics(
    table,
    tenant_id: str,
    metric_type: str,
    current_timestamp: str,
    time_period: str
) -> List[Dict]:
    """
    Query historical metrics from DynamoDB
    
    Args:
        table: DynamoDB table resource
        tenant_id: Tenant ID
        metric_type: Type of metric (feature_usage, performance, ai_usage)
        current_timestamp: Current metric timestamp
        time_period: Time period (hourly, daily, monthly)
        
    Returns:
        List of historical metric dictionaries
    """
    try:
        # Parse current timestamp
        current_dt = datetime.fromisoformat(current_timestamp.replace('Z', '+00:00'))
        
        # Determine lookback period
        if time_period == 'hourly':
            lookback_days = 7  # Last 7 days
        elif time_period == 'daily':
            lookback_days = 90  # Last 90 days
        else:  # monthly
            lookback_days = 730  # Last 24 months
        
        # Calculate start timestamp
        start_dt = current_dt - timedelta(days=lookback_days)
        start_timestamp = start_dt.isoformat().replace('+00:00', 'Z')
        
        # Extract month for PK
        month = current_timestamp[:7]
        
        # Build PK
        pk = f"TENANT#{tenant_id}#METRIC#{metric_type}#PERIOD#{month}"
        
        # Query DynamoDB
        response = table.query(
            KeyConditionExpression='PK = :pk AND SK >= :start_sk',
            ExpressionAttributeValues={
                ':pk': pk,
                ':start_sk': f"TIMESTAMP#{start_timestamp}"
            },
            ScanIndexForward=True,  # Sort ascending by timestamp
            Limit=100  # Limit to recent history
        )
        
        return response.get('Items', [])
        
    except Exception as e:
        print(f"Warning: Error querying historical metrics: {str(e)}")
        return []


def calculate_trend_indicators(
    current_metric: Dict,
    historical_metrics: List[Dict],
    time_period: str
) -> Dict:
    """
    Calculate trend indicators from historical data
    
    Args:
        current_metric: Current metric dictionary
        historical_metrics: List of historical metrics
        time_period: Time period (hourly, daily, monthly)
        
    Returns:
        Dictionary with trend indicators
    """
    trend_data = {}
    
    if not historical_metrics or len(historical_metrics) < 2:
        # Not enough data for trend analysis
        trend_data['trend_direction'] = 'insufficient_data'
        return trend_data
    
    try:
        # Determine the metric value to track
        value_key = determine_value_key(current_metric['metric_type'])
        
        if value_key not in current_metric:
            return trend_data
        
        current_value = float(current_metric[value_key])
        
        # Extract historical values
        historical_values = []
        for hist_metric in historical_metrics:
            if value_key in hist_metric:
                try:
                    val = float(hist_metric[value_key])
                    historical_values.append(val)
                except (ValueError, TypeError):
                    continue
        
        if not historical_values:
            trend_data['trend_direction'] = 'insufficient_data'
            return trend_data
        
        # Calculate period-over-period change
        if len(historical_values) >= 1:
            previous_value = historical_values[-1]
            if previous_value > 0:
                period_over_period_change = ((current_value - previous_value) / previous_value) * 100
                trend_data['period_over_period_change'] = round(period_over_period_change, 2)
                
                # Calculate growth rate
                trend_data['growth_rate'] = round(period_over_period_change, 2)
                
                # Determine trend direction
                if period_over_period_change > 5:
                    trend_data['trend_direction'] = 'increasing'
                elif period_over_period_change < -5:
                    trend_data['trend_direction'] = 'decreasing'
                else:
                    trend_data['trend_direction'] = 'stable'
        
        # Calculate rolling averages
        if len(historical_values) >= 7:
            # 7-period rolling average
            recent_7 = historical_values[-7:]
            trend_data['rolling_avg_7d'] = round(statistics.mean(recent_7), 2)
        
        if len(historical_values) >= 30:
            # 30-period rolling average
            recent_30 = historical_values[-30:]
            trend_data['rolling_avg_30d'] = round(statistics.mean(recent_30), 2)
        
        # Identify seasonality patterns (simplified)
        if len(historical_values) >= 7:
            # Check for weekly patterns
            seasonality = detect_seasonality(historical_values)
            if seasonality:
                trend_data['seasonality_indicator'] = seasonality
        
    except Exception as e:
        print(f"Warning: Error calculating trend indicators: {str(e)}")
    
    return trend_data


def determine_value_key(metric_type: str) -> str:
    """
    Determine which field to use for trend analysis based on metric type
    
    Args:
        metric_type: Type of metric
        
    Returns:
        Field name to track
    """
    if metric_type == 'feature_usage':
        return 'usage_count'
    elif metric_type == 'performance':
        return 'avg_response_time'
    elif metric_type == 'ai_usage':
        return 'ai_invocations'
    else:
        return 'usage_count'


def detect_seasonality(values: List[float]) -> Optional[str]:
    """
    Detect seasonality patterns in time series data
    
    Args:
        values: List of historical values
        
    Returns:
        Seasonality indicator or None
    """
    try:
        if len(values) < 7:
            return None
        
        # Calculate coefficient of variation
        mean_val = statistics.mean(values)
        if mean_val == 0:
            return None
        
        std_val = statistics.stdev(values)
        cv = (std_val / mean_val) * 100
        
        # High variation suggests seasonality
        if cv > 30:
            return 'high_variation'
        elif cv > 15:
            return 'moderate_variation'
        else:
            return 'low_variation'
        
    except Exception as e:
        print(f"Warning: Error detecting seasonality: {str(e)}")
        return None


def enrich_metrics_with_trends(
    table_name: str,
    metrics: List[Dict],
    time_period: str
) -> List[Dict]:
    """
    Main function to enrich metrics with trend data
    
    This is called from the main handler after initial aggregation.
    
    Args:
        table_name: DynamoDB table name
        metrics: List of aggregated metrics
        time_period: Time period (hourly, daily, monthly)
        
    Returns:
        List of metrics enriched with trend data
    """
    return calculate_trends_for_metrics(table_name, metrics, time_period)
