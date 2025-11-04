"""
At-Risk Feature Identifier Tool (Simplified)

Collects raw feature usage data for trend analysis.
Returns usage metrics for current and previous periods to enable the Bedrock agent
to identify at-risk features and provide recommendations.
"""

import boto3
import os
from datetime import datetime, timedelta
from decimal import Decimal
from boto3.dynamodb.conditions import Key
from typing import Dict, List, Optional
from tools.datetime_utils import utcnow, parse_iso_datetime, to_iso_string


def identify_at_risk_features(tenant_id: str, analysis_period_days: int = 90) -> Dict:
    """
    Collect raw feature usage data for at-risk analysis.
    
    Returns usage metrics for current and previous periods. The Bedrock agent will:
    - Identify features with declining usage
    - Assess risk levels (critical, moderate)
    - Provide actionable recommendations with priorities
    
    Args:
        tenant_id: Target tenant ID or 'all' for platform-wide analysis
        analysis_period_days: Period for trend analysis in days (default: 90)
    
    Returns:
        Raw feature usage data for current and previous periods
    """
    
    # Initialize DynamoDB clients
    dynamodb = boto3.resource('dynamodb')
    tenants_table = dynamodb.Table(os.environ.get('TENANTS_TABLE_NAME', 'Tenants'))
    metrics_table = dynamodb.Table(os.environ.get('USAGE_METRICS_TABLE_NAME', 'AgenticInsights-UsageMetrics'))
    
    try:
        # Ensure analysis_period_days is an integer (handle string/float from API)
        if isinstance(analysis_period_days, str):
            analysis_period_days = int(analysis_period_days)
        elif isinstance(analysis_period_days, float):
            analysis_period_days = int(analysis_period_days)
        
        # Get tenant(s) to analyze
        if tenant_id.lower() == 'all':
            tenants = get_all_active_tenants(tenants_table)
        else:
            tenant = get_tenant(tenants_table, tenant_id)
            tenants = [tenant] if tenant else []
        
        if not tenants:
            return {
                "error": True,
                "error_code": "NO_TENANTS_FOUND",
                "error_message": f"No tenants found for analysis",
                "timestamp": to_iso_string(utcnow())
            }
        
        # Calculate date ranges for trend analysis
        end_date = utcnow()
        start_date = end_date - timedelta(days=analysis_period_days)
        
        # Split into current and previous periods (30 days each)
        current_period_end = end_date
        current_period_start = end_date - timedelta(days=30)
        previous_period_end = current_period_start
        previous_period_start = current_period_start - timedelta(days=30)
        
        # Collect raw feature usage data for both periods
        if tenant_id.lower() == 'all':
            feature_data = collect_platform_feature_usage(
                metrics_table, tenants, 
                current_period_start, current_period_end,
                previous_period_start, previous_period_end
            )
        else:
            feature_data = collect_tenant_feature_usage(
                metrics_table, tenant_id,
                current_period_start, current_period_end,
                previous_period_start, previous_period_end
            )
        
        # Return raw data for agent to analyze
        response = {
            "analysis_type": "at_risk_features",
            "timestamp": to_iso_string(utcnow()),
            "tenant_id": tenant_id,
            "data": {
                "features": feature_data,
                "analysis_context": {
                    "current_period": {
                        "start": to_iso_string(current_period_start),
                        "end": to_iso_string(current_period_end),
                        "days": 30
                    },
                    "previous_period": {
                        "start": to_iso_string(previous_period_start),
                        "end": to_iso_string(previous_period_end),
                        "days": 30
                    },
                    "total_analysis_days": analysis_period_days,
                    "instructions_for_agent": "Analyze the feature usage data to identify at-risk features. Each feature includes monthly_breakdown showing usage trends over time. A feature is at-risk if: (1) usage declined by >25% between periods, OR (2) adoption rate is <15%. Classify risk as 'critical' if both conditions are met, otherwise 'moderate'. Use the monthly breakdown to identify specific months where decline occurred and provide month-specific insights. Provide specific recommendations with priority levels."
                }
            },
            "metadata": {
                "features_analyzed": len(feature_data),
                "date_range": {
                    "start": to_iso_string(start_date),
                    "end": to_iso_string(end_date)
                }
            }
        }
        
        return response
        
    except Exception as e:
        return {
            "error": True,
            "error_code": "AT_RISK_ANALYSIS_FAILED",
            "error_message": f"Failed to collect feature usage data: {str(e)}",
            "timestamp": to_iso_string(utcnow()),
            "tenant_id": tenant_id
        }


def get_tenant(tenants_table, tenant_id: str) -> Optional[Dict]:
    """Retrieve a single tenant from DynamoDB"""
    try:
        response = tenants_table.get_item(Key={'tenant_id': tenant_id})
        return response.get('Item')
    except Exception as e:
        print(f"Error retrieving tenant {tenant_id}: {str(e)}")
        return None


def get_all_active_tenants(tenants_table) -> List[Dict]:
    """Retrieve all active tenants from DynamoDB"""
    try:
        response = tenants_table.scan(
            FilterExpression='#status = :active',
            ExpressionAttributeNames={'#status': 'status'},
            ExpressionAttributeValues={':active': 'active'}
        )
        return response.get('Items', [])
    except Exception as e:
        print(f"Error retrieving tenants: {str(e)}")
        return []


def collect_tenant_feature_usage(
    metrics_table,
    tenant_id: str,
    current_start: datetime,
    current_end: datetime,
    previous_start: datetime,
    previous_end: datetime
) -> List[Dict]:
    """
    Collect raw feature usage data for a single tenant across two periods.
    Returns simple usage counts without analysis.
    """
    try:
        # Get feature usage for current period
        current_usage = get_period_feature_usage(
            metrics_table, tenant_id, current_start, current_end
        )
        
        # Get feature usage for previous period
        previous_usage = get_period_feature_usage(
            metrics_table, tenant_id, previous_start, previous_end
        )
        
        # Get active users for context
        active_users = get_active_users_count(
            metrics_table, tenant_id, current_start, current_end
        )
        
        # Combine data for all features
        all_features = set(current_usage.keys()) | set(previous_usage.keys())
        
        feature_data = []
        for feature_name in all_features:
            current_data = current_usage.get(feature_name, {})
            previous_data = previous_usage.get(feature_name, {})
            
            feature_data.append({
                "feature_name": feature_name,
                "current_period": {
                    "usage_count": current_data.get('usage_count', 0),
                    "unique_users": current_data.get('unique_users', 0),
                    "monthly_breakdown": current_data.get('monthly_breakdown', {})
                },
                "previous_period": {
                    "usage_count": previous_data.get('usage_count', 0),
                    "unique_users": previous_data.get('unique_users', 0),
                    "monthly_breakdown": previous_data.get('monthly_breakdown', {})
                },
                "context": {
                    "total_active_users": active_users,
                    "tenant_id": tenant_id
                }
            })
        
        return feature_data
        
    except Exception as e:
        print(f"Error collecting tenant feature usage: {str(e)}")
        return []


def collect_platform_feature_usage(
    metrics_table,
    tenants: List[Dict],
    current_start: datetime,
    current_end: datetime,
    previous_start: datetime,
    previous_end: datetime
) -> List[Dict]:
    """
    Collect raw feature usage data across all tenants (platform-wide).
    Aggregates usage counts without analysis.
    """
    try:
        # Aggregate usage across all tenants
        current_aggregates = {}
        previous_aggregates = {}
        total_active_users = 0
        
        for tenant in tenants:
            tenant_id = tenant.get('tenant_id')
            
            # Get current period usage
            current_usage = get_period_feature_usage(
                metrics_table, tenant_id, current_start, current_end
            )
            
            # Get previous period usage
            previous_usage = get_period_feature_usage(
                metrics_table, tenant_id, previous_start, previous_end
            )
            
            # Aggregate current period
            for feature, data in current_usage.items():
                if feature not in current_aggregates:
                    current_aggregates[feature] = {'usage_count': 0, 'unique_users': 0, 'monthly_breakdown': {}}
                current_aggregates[feature]['usage_count'] += data.get('usage_count', 0)
                current_aggregates[feature]['unique_users'] += data.get('unique_users', 0)
                
                # Aggregate monthly breakdown
                for month, month_data in data.get('monthly_breakdown', {}).items():
                    if month not in current_aggregates[feature]['monthly_breakdown']:
                        current_aggregates[feature]['monthly_breakdown'][month] = {'usage_count': 0, 'unique_users': 0}
                    current_aggregates[feature]['monthly_breakdown'][month]['usage_count'] += month_data.get('usage_count', 0)
                    current_aggregates[feature]['monthly_breakdown'][month]['unique_users'] += month_data.get('unique_users', 0)
            
            # Aggregate previous period
            for feature, data in previous_usage.items():
                if feature not in previous_aggregates:
                    previous_aggregates[feature] = {'usage_count': 0, 'unique_users': 0, 'monthly_breakdown': {}}
                previous_aggregates[feature]['usage_count'] += data.get('usage_count', 0)
                previous_aggregates[feature]['unique_users'] += data.get('unique_users', 0)
                
                # Aggregate monthly breakdown
                for month, month_data in data.get('monthly_breakdown', {}).items():
                    if month not in previous_aggregates[feature]['monthly_breakdown']:
                        previous_aggregates[feature]['monthly_breakdown'][month] = {'usage_count': 0, 'unique_users': 0}
                    previous_aggregates[feature]['monthly_breakdown'][month]['usage_count'] += month_data.get('usage_count', 0)
                    previous_aggregates[feature]['monthly_breakdown'][month]['unique_users'] += month_data.get('unique_users', 0)
            
            # Count active users
            tenant_users = get_active_users_count(
                metrics_table, tenant_id, current_start, current_end
            )
            total_active_users += tenant_users
        
        # Combine data for all features
        all_features = set(current_aggregates.keys()) | set(previous_aggregates.keys())
        
        feature_data = []
        for feature_name in all_features:
            current_data = current_aggregates.get(feature_name, {})
            previous_data = previous_aggregates.get(feature_name, {})
            
            feature_data.append({
                "feature_name": feature_name,
                "current_period": {
                    "usage_count": current_data.get('usage_count', 0),
                    "unique_users": current_data.get('unique_users', 0),
                    "monthly_breakdown": current_data.get('monthly_breakdown', {})
                },
                "previous_period": {
                    "usage_count": previous_data.get('usage_count', 0),
                    "unique_users": previous_data.get('unique_users', 0),
                    "monthly_breakdown": previous_data.get('monthly_breakdown', {})
                },
                "context": {
                    "total_active_users": total_active_users,
                    "total_tenants": len(tenants),
                    "scope": "platform"
                }
            })
        
        return feature_data
        
    except Exception as e:
        print(f"Error collecting platform feature usage: {str(e)}")
        return []


def get_period_feature_usage(
    metrics_table,
    tenant_id: str,
    start_date: datetime,
    end_date: datetime
) -> Dict[str, Dict]:
    """
    Get feature usage for a specific period with month-wise breakdown.
    Returns dict of {feature_name: {usage_count, unique_users, monthly_breakdown}}
    """
    feature_usage = {}
    
    try:
        current_date = start_date
        
        while current_date <= end_date:
            month = current_date.strftime('%Y-%m')
            
            # Query feature_usage metrics for this month
            pk = f"TENANT#{tenant_id}#METRIC#feature_usage#PERIOD#{month}"
            
            try:
                response = metrics_table.query(
                    KeyConditionExpression=Key('PK').eq(pk) & Key('SK').begins_with('TIMESTAMP#'),
                    Limit=100
                )
                
                for item in response.get('Items', []):
                    feature_name = item.get('feature_name')
                    if not feature_name:
                        continue
                    
                    if feature_name not in feature_usage:
                        feature_usage[feature_name] = {
                            'usage_count': 0,
                            'unique_users': 0,
                            'monthly_breakdown': {}
                        }
                    
                    # Initialize month in breakdown if not exists
                    if month not in feature_usage[feature_name]['monthly_breakdown']:
                        feature_usage[feature_name]['monthly_breakdown'][month] = {
                            'usage_count': 0,
                            'unique_users': 0
                        }
                    
                    # Aggregate metrics for total
                    usage_count = int(item.get('usage_count', 0))
                    unique_users = int(item.get('unique_users', 0))
                    
                    feature_usage[feature_name]['usage_count'] += usage_count
                    feature_usage[feature_name]['unique_users'] += unique_users
                    
                    # Aggregate metrics for month
                    feature_usage[feature_name]['monthly_breakdown'][month]['usage_count'] += usage_count
                    feature_usage[feature_name]['monthly_breakdown'][month]['unique_users'] += unique_users
                    
            except Exception as e:
                print(f"Error querying feature usage for {month}: {str(e)}")
            
            # Move to next month
            current_date = (current_date.replace(day=1) + timedelta(days=32)).replace(day=1)
        
        return feature_usage
        
    except Exception as e:
        print(f"Error getting period feature usage: {str(e)}")
        return {}


def get_active_users_count(
    metrics_table,
    tenant_id: str,
    start_date: datetime,
    end_date: datetime
) -> int:
    """
    Get count of active users in a period by aggregating unique_users from feature_usage metrics.
    
    Note: The DynamoDB schema stores feature usage with unique_users per feature.
    We aggregate across all features to get the total active user count.
    """
    try:
        max_users = 0
        current_date = start_date
        
        while current_date <= end_date:
            month = current_date.strftime('%Y-%m')
            
            # Query feature_usage metrics to get unique_users
            pk = f"TENANT#{tenant_id}#METRIC#feature_usage#PERIOD#{month}"
            
            try:
                response = metrics_table.query(
                    KeyConditionExpression=Key('PK').eq(pk) & Key('SK').begins_with('TIMESTAMP#'),
                    Limit=100
                )
                
                # Aggregate unique users across all features for this month
                month_users = 0
                for item in response.get('Items', []):
                    unique_users = item.get('unique_users', 0)
                    if isinstance(unique_users, Decimal):
                        unique_users = int(unique_users)
                    month_users = max(month_users, unique_users)
                
                max_users = max(max_users, month_users)
            
            except Exception as e:
                print(f"Error querying active users for {month}: {str(e)}")
            
            current_date = (current_date.replace(day=1) + timedelta(days=32)).replace(day=1)
        
        return max_users
        
    except Exception as e:
        print(f"Error getting active users count: {str(e)}")
        return 0
