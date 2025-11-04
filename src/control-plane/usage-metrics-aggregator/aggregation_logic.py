"""
Metrics Aggregation Logic

Contains functions for aggregating different types of metrics:
- Feature usage metrics
- Performance metrics
- AI usage metrics
- Trend calculations
"""

import json
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Any, Optional
from collections import defaultdict
import statistics


def aggregate_feature_metrics(log_entries: List[Dict], time_period: str) -> List[Dict]:
    """
    Aggregate feature usage metrics
    
    Groups logs by tenant_id, feature_name, and time period,
    calculates usage_count, unique_users, and tracks operations.
    
    Args:
        log_entries: List of parsed log entries
        time_period: Time period for aggregation (hourly, daily, monthly)
        
    Returns:
        List of feature usage metric dictionaries
    """
    # Group logs by tenant, feature, and time bucket
    feature_groups = defaultdict(lambda: {
        'usage_count': 0,
        'unique_users': set(),
        'operations': defaultdict(int),
        'timestamps': []
    })
    
    for log_entry in log_entries:
        try:
            # Extract required fields
            tenant_id = log_entry.get('tenantId') or log_entry.get('tenant_id')
            user_id = log_entry.get('userId') or log_entry.get('user_id')
            path = log_entry.get('path', '')
            http_method = log_entry.get('httpMethod', '')
            request_time = log_entry.get('requestTime', '')
            
            # Skip if missing required fields
            if not tenant_id or not path:
                continue
            
            # Determine feature name from path
            feature_name = extract_feature_from_path(path)
            if not feature_name:
                continue
            
            # Determine operation type from HTTP method
            operation_type = map_http_method_to_operation(http_method)
            
            # Parse timestamp
            timestamp = parse_timestamp(request_time, log_entry.get('requestTimeEpoch'))
            if not timestamp:
                continue
            
            # Round timestamp to time period bucket
            time_bucket = round_to_time_bucket(timestamp, time_period)
            
            # Create group key
            group_key = (tenant_id, feature_name, time_bucket)
            
            # Aggregate metrics
            feature_groups[group_key]['usage_count'] += 1
            if user_id:
                feature_groups[group_key]['unique_users'].add(user_id)
            feature_groups[group_key]['operations'][operation_type] += 1
            feature_groups[group_key]['timestamps'].append(timestamp)
            
        except Exception as e:
            print(f"Warning: Error processing log entry for feature metrics: {str(e)}")
            continue
    
    # Convert aggregated data to metric items
    metrics = []
    current_time = datetime.utcnow().isoformat() + 'Z'
    
    for (tenant_id, feature_name, time_bucket), data in feature_groups.items():
        try:
            # Calculate first and last used dates
            timestamps = sorted(data['timestamps'])
            first_used_date = timestamps[0].split('T')[0] if timestamps else time_bucket.split('T')[0]
            last_used_date = timestamps[-1].split('T')[0] if timestamps else time_bucket.split('T')[0]
            
            # Extract month for GSI
            month = time_bucket[:7]  # "2024-10"
            
            # Generate PK and SK
            pk = f"TENANT#{tenant_id}#METRIC#feature_usage#PERIOD#{month}"
            sk = f"TIMESTAMP#{time_bucket}"
            
            # Create metric item
            metric = {
                'PK': pk,
                'SK': sk,
                'tenant_id': tenant_id,
                'metric_type': 'feature_usage',
                'time_period': time_period,
                'timestamp': time_bucket,
                'month': month,
                'feature_name': feature_name,
                'usage_count': data['usage_count'],
                'unique_users': len(data['unique_users']),
                'first_used_date': first_used_date,
                'last_used_date': last_used_date,
                'aggregation_level': 'tenant',
                'data_points_count': data['usage_count'],
                'last_updated': current_time,
                'tenant_timestamp': f"{tenant_id}#{time_bucket}",  # For FeatureIndex GSI
            }
            
            # Add operation breakdown if available
            if data['operations']:
                metric['operations'] = dict(data['operations'])
                # Find most common operation
                metric['operation_type'] = max(data['operations'].items(), key=lambda x: x[1])[0]
            
            # Calculate TTL based on time period
            metric['ttl'] = calculate_ttl(time_bucket, time_period)
            
            metrics.append(metric)
            
        except Exception as e:
            print(f"Warning: Error creating feature metric: {str(e)}")
            continue
    
    return metrics


def aggregate_performance_metrics(log_entries: List[Dict], time_period: str) -> List[Dict]:
    """
    Aggregate performance metrics
    
    Calculates response time percentiles, error rates, and throughput.
    
    Args:
        log_entries: List of parsed log entries
        time_period: Time period for aggregation (hourly, daily, monthly)
        
    Returns:
        List of performance metric dictionaries
    """
    # Group logs by tenant, feature, and time bucket
    performance_groups = defaultdict(lambda: {
        'response_times': [],
        'total_requests': 0,
        'successful_requests': 0,
        'failed_requests': 0,
        'error_by_status': defaultdict(int)
    })
    
    for log_entry in log_entries:
        try:
            # Extract required fields
            tenant_id = log_entry.get('tenantId') or log_entry.get('tenant_id')
            path = log_entry.get('path', '')
            status = log_entry.get('status', 0)
            response_time = log_entry.get('responseTime', 0)
            request_time = log_entry.get('requestTime', '')
            
            # Skip if missing required fields
            if not tenant_id or not path:
                continue
            
            # Determine feature name from path
            feature_name = extract_feature_from_path(path)
            if not feature_name:
                continue
            
            # Parse timestamp
            timestamp = parse_timestamp(request_time, log_entry.get('requestTimeEpoch'))
            if not timestamp:
                continue
            
            # Round timestamp to time period bucket
            time_bucket = round_to_time_bucket(timestamp, time_period)
            
            # Create group key
            group_key = (tenant_id, feature_name, time_bucket)
            
            # Aggregate metrics
            performance_groups[group_key]['response_times'].append(response_time)
            performance_groups[group_key]['total_requests'] += 1
            
            # Track success/failure
            if 200 <= status < 300:
                performance_groups[group_key]['successful_requests'] += 1
            else:
                performance_groups[group_key]['failed_requests'] += 1
                performance_groups[group_key]['error_by_status'][str(status)] += 1
            
        except Exception as e:
            print(f"Warning: Error processing log entry for performance metrics: {str(e)}")
            continue
    
    # Convert aggregated data to metric items
    metrics = []
    current_time = datetime.utcnow().isoformat() + 'Z'
    
    for (tenant_id, feature_name, time_bucket), data in performance_groups.items():
        try:
            response_times = sorted(data['response_times'])
            
            if not response_times:
                continue
            
            # Calculate percentiles
            avg_response_time = statistics.mean(response_times)
            p50_response_time = calculate_percentile(response_times, 50)
            p95_response_time = calculate_percentile(response_times, 95)
            p99_response_time = calculate_percentile(response_times, 99)
            min_response_time = min(response_times)
            max_response_time = max(response_times)
            
            # Calculate error rate
            total_requests = data['total_requests']
            failed_requests = data['failed_requests']
            error_rate = (failed_requests / total_requests * 100) if total_requests > 0 else 0
            
            # Extract month for GSI
            month = time_bucket[:7]  # "2024-10"
            
            # Generate PK and SK
            pk = f"TENANT#{tenant_id}#METRIC#performance#PERIOD#{month}"
            sk = f"TIMESTAMP#{time_bucket}"
            
            # Create metric item
            metric = {
                'PK': pk,
                'SK': sk,
                'tenant_id': tenant_id,
                'metric_type': 'performance',
                'time_period': time_period,
                'timestamp': time_bucket,
                'month': month,
                'feature_name': feature_name,
                'total_requests': total_requests,
                'successful_requests': data['successful_requests'],
                'failed_requests': failed_requests,
                'avg_response_time': avg_response_time,
                'p50_response_time': p50_response_time,
                'p95_response_time': p95_response_time,
                'p99_response_time': p99_response_time,
                'min_response_time': min_response_time,
                'max_response_time': max_response_time,
                'error_rate': error_rate,
                'aggregation_level': 'tenant',
                'data_points_count': total_requests,
                'last_updated': current_time,
                'tenant_timestamp': f"{tenant_id}#{time_bucket}",  # For FeatureIndex GSI
                'metric_type_month': f"performance#{month}",  # For PlatformIndex GSI
            }
            
            # Add error breakdown if available
            if data['error_by_status']:
                metric['error_count_by_status'] = dict(data['error_by_status'])
            
            # Identify performance anomalies
            if p95_response_time > 1000:  # > 1 second
                metric['performance_anomaly'] = 'high_latency'
            if error_rate > 5:  # > 5% error rate
                metric['performance_anomaly'] = 'high_error_rate'
            
            # Calculate TTL based on time period
            metric['ttl'] = calculate_ttl(time_bucket, time_period)
            
            metrics.append(metric)
            
        except Exception as e:
            print(f"Warning: Error creating performance metric: {str(e)}")
            continue
    
    return metrics


def aggregate_ai_metrics(log_entries: List[Dict], time_period: str) -> List[Dict]:
    """
    Aggregate AI usage metrics
    
    Sums token usage, calculates costs, and tracks AI invocations.
    
    Args:
        log_entries: List of parsed log entries
        time_period: Time period for aggregation (hourly, daily, monthly)
        
    Returns:
        List of AI usage metric dictionaries
    """
    # Group logs by tenant and time bucket
    ai_groups = defaultdict(lambda: {
        'ai_invocations': 0,
        'total_input_tokens': 0,
        'total_output_tokens': 0,
        'successful_invocations': 0,
        'failed_invocations': 0,
        'generation_times': [],
        'model_usage': defaultdict(int)
    })
    
    for log_entry in log_entries:
        try:
            # Check if this is an AI request
            ai_metadata = log_entry.get('aiMetadata')
            if not ai_metadata:
                continue
            
            # Extract required fields
            tenant_id = log_entry.get('tenantId') or log_entry.get('tenant_id')
            request_time = log_entry.get('requestTime', '')
            response_time = log_entry.get('responseTime', 0)
            
            # Skip if missing required fields
            if not tenant_id:
                continue
            
            # Parse timestamp
            timestamp = parse_timestamp(request_time, log_entry.get('requestTimeEpoch'))
            if not timestamp:
                continue
            
            # Round timestamp to time period bucket
            time_bucket = round_to_time_bucket(timestamp, time_period)
            
            # Create group key
            group_key = (tenant_id, time_bucket)
            
            # Extract AI metadata
            input_tokens = ai_metadata.get('inputTokens', 0)
            output_tokens = ai_metadata.get('outputTokens', 0)
            model_id = ai_metadata.get('modelId', 'unknown')
            success = ai_metadata.get('success', False)
            
            # Aggregate metrics
            ai_groups[group_key]['ai_invocations'] += 1
            ai_groups[group_key]['total_input_tokens'] += input_tokens
            ai_groups[group_key]['total_output_tokens'] += output_tokens
            ai_groups[group_key]['model_usage'][model_id] += 1
            ai_groups[group_key]['generation_times'].append(response_time)
            
            if success:
                ai_groups[group_key]['successful_invocations'] += 1
            else:
                ai_groups[group_key]['failed_invocations'] += 1
            
        except Exception as e:
            print(f"Warning: Error processing log entry for AI metrics: {str(e)}")
            continue
    
    # Convert aggregated data to metric items
    metrics = []
    current_time = datetime.utcnow().isoformat() + 'Z'
    
    # Claude 3 Haiku pricing (per 1M tokens)
    INPUT_TOKEN_PRICE = 0.00025  # $0.25 per 1M input tokens
    OUTPUT_TOKEN_PRICE = 0.00125  # $1.25 per 1M output tokens
    
    for (tenant_id, time_bucket), data in ai_groups.items():
        try:
            ai_invocations = data['ai_invocations']
            
            if ai_invocations == 0:
                continue
            
            # Calculate averages
            total_input_tokens = data['total_input_tokens']
            total_output_tokens = data['total_output_tokens']
            avg_tokens_per_request = (total_input_tokens + total_output_tokens) / ai_invocations
            
            # Calculate costs
            input_cost = (total_input_tokens / 1_000_000) * INPUT_TOKEN_PRICE
            output_cost = (total_output_tokens / 1_000_000) * OUTPUT_TOKEN_PRICE
            estimated_cost = input_cost + output_cost
            cost_per_generation = estimated_cost / ai_invocations if ai_invocations > 0 else 0
            
            # Calculate success rate
            successful_invocations = data['successful_invocations']
            generation_success_rate = (successful_invocations / ai_invocations * 100) if ai_invocations > 0 else 0
            
            # Calculate average generation time
            generation_times = data['generation_times']
            avg_generation_time = statistics.mean(generation_times) / 1000 if generation_times else 0  # Convert to seconds
            
            # Extract month for GSI
            month = time_bucket[:7]  # "2024-10"
            
            # Generate PK and SK
            pk = f"TENANT#{tenant_id}#METRIC#ai_usage#PERIOD#{month}"
            sk = f"TIMESTAMP#{time_bucket}"
            
            # Create metric item
            metric = {
                'PK': pk,
                'SK': sk,
                'tenant_id': tenant_id,
                'metric_type': 'ai_usage',
                'time_period': time_period,
                'timestamp': time_bucket,
                'month': month,
                'feature_name': 'ai_descriptions',
                'ai_invocations': ai_invocations,
                'total_input_tokens': total_input_tokens,
                'total_output_tokens': total_output_tokens,
                'avg_tokens_per_request': avg_tokens_per_request,
                'estimated_cost': estimated_cost,
                'cost_per_generation': cost_per_generation,
                'generation_success_rate': generation_success_rate,
                'avg_generation_time': avg_generation_time,
                'aggregation_level': 'tenant',
                'data_points_count': ai_invocations,
                'last_updated': current_time,
                'tenant_timestamp': f"{tenant_id}#{time_bucket}",  # For FeatureIndex GSI
                'metric_type_month': f"ai_usage#{month}",  # For PlatformIndex GSI
            }
            
            # Add model usage breakdown
            if data['model_usage']:
                metric['model_usage'] = dict(data['model_usage'])
            
            # Calculate TTL based on time period
            metric['ttl'] = calculate_ttl(time_bucket, time_period)
            
            metrics.append(metric)
            
        except Exception as e:
            print(f"Warning: Error creating AI metric: {str(e)}")
            continue
    
    return metrics


def calculate_trends(current_metrics: Dict, historical_metrics: List[Dict]) -> Dict:
    """
    Calculate period-over-period trends
    
    Compares current metrics with historical data to identify trends.
    
    Args:
        current_metrics: Current period metrics
        historical_metrics: List of historical metrics for comparison
        
    Returns:
        Dictionary with trend indicators
    """
    # This will be implemented in task 3.5
    # For now, return empty dict
    return {}


# Helper functions

def extract_feature_from_path(path: str) -> Optional[str]:
    """
    Extract feature name from API path
    
    Args:
        path: API request path
        
    Returns:
        Feature name or None
    """
    # Remove leading slash and query parameters
    path = path.lstrip('/').split('?')[0]
    
    # Map paths to features
    if path.startswith('products'):
        return 'products'
    elif path.startswith('orders'):
        return 'orders'
    elif path.startswith('users'):
        return 'users'
    elif path.startswith('product-desc') or 'description' in path:
        return 'ai_descriptions'
    else:
        # Use first path segment as feature name
        parts = path.split('/')
        return parts[0] if parts else None


def map_http_method_to_operation(http_method: str) -> str:
    """
    Map HTTP method to CRUD operation
    
    Args:
        http_method: HTTP method (GET, POST, PUT, DELETE, etc.)
        
    Returns:
        Operation type (create, read, update, delete)
    """
    method_map = {
        'POST': 'create',
        'GET': 'read',
        'PUT': 'update',
        'PATCH': 'update',
        'DELETE': 'delete'
    }
    return method_map.get(http_method.upper(), 'read')


def parse_timestamp(request_time: str, request_time_epoch: Optional[int] = None) -> Optional[str]:
    """
    Parse timestamp from request time or epoch
    
    Args:
        request_time: ISO 8601 timestamp string
        request_time_epoch: Unix timestamp in milliseconds
        
    Returns:
        ISO 8601 timestamp string or None
    """
    try:
        if request_time:
            # Parse ISO 8601 format
            if 'T' in request_time:
                return request_time
            # Try parsing other formats
            dt = datetime.fromisoformat(request_time.replace('Z', '+00:00'))
            return dt.isoformat().replace('+00:00', 'Z')
        elif request_time_epoch:
            # Convert epoch milliseconds to datetime
            dt = datetime.utcfromtimestamp(request_time_epoch / 1000)
            return dt.isoformat() + 'Z'
    except Exception as e:
        print(f"Warning: Error parsing timestamp: {str(e)}")
    
    return None


def round_to_time_bucket(timestamp: str, time_period: str) -> str:
    """
    Round timestamp to time period bucket
    
    Args:
        timestamp: ISO 8601 timestamp
        time_period: Time period (hourly, daily, monthly)
        
    Returns:
        Rounded timestamp string
    """
    try:
        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        
        if time_period == 'hourly':
            # Round to hour
            dt = dt.replace(minute=0, second=0, microsecond=0)
        elif time_period == 'daily':
            # Round to day
            dt = dt.replace(hour=0, minute=0, second=0, microsecond=0)
        elif time_period == 'monthly':
            # Round to month
            dt = dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        return dt.isoformat().replace('+00:00', 'Z')
    except Exception as e:
        print(f"Warning: Error rounding timestamp: {str(e)}")
        return timestamp


def calculate_percentile(sorted_values: List[float], percentile: int) -> float:
    """
    Calculate percentile from sorted values
    
    Args:
        sorted_values: Sorted list of values
        percentile: Percentile to calculate (0-100)
        
    Returns:
        Percentile value
    """
    if not sorted_values:
        return 0.0
    
    if len(sorted_values) == 1:
        return sorted_values[0]
    
    # Calculate index
    index = (percentile / 100) * (len(sorted_values) - 1)
    
    # Interpolate if needed
    lower_index = int(index)
    upper_index = min(lower_index + 1, len(sorted_values) - 1)
    weight = index - lower_index
    
    return sorted_values[lower_index] * (1 - weight) + sorted_values[upper_index] * weight


def calculate_ttl(timestamp: str, time_period: str) -> int:
    """
    Calculate TTL (time to live) for metric based on retention policy
    
    Args:
        timestamp: Metric timestamp
        time_period: Time period (hourly, daily, monthly)
        
    Returns:
        Unix timestamp for TTL
    """
    try:
        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        
        # Retention policies
        if time_period == 'hourly':
            # 7 days retention
            ttl_dt = dt + timedelta(days=7)
        elif time_period == 'daily':
            # 90 days retention
            ttl_dt = dt + timedelta(days=90)
        elif time_period == 'monthly':
            # 24 months retention
            ttl_dt = dt + timedelta(days=730)
        else:
            # Default 30 days
            ttl_dt = dt + timedelta(days=30)
        
        return int(ttl_dt.timestamp())
    except Exception as e:
        print(f"Warning: Error calculating TTL: {str(e)}")
        # Default to 30 days from now
        return int((datetime.utcnow() + timedelta(days=30)).timestamp())
