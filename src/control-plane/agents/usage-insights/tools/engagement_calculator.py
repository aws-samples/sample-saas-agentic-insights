"""
Tenant Engagement Metrics Collector Tool

Collects tenant-level engagement metrics for analysis by the Bedrock agent.
The agent will calculate scores, categorize tenants, and provide recommendations.
"""

import boto3
import os
from datetime import datetime, timedelta
from decimal import Decimal
from boto3.dynamodb.conditions import Key, Attr
from typing import Dict, List, Optional
import statistics
from tools.datetime_utils import utcnow, parse_iso_datetime, to_iso_string


def calculate_engagement_scores(tenant_id: str, user_id: Optional[str] = None) -> Dict:
    """
    Collect tenant-level engagement metrics.
    
    Args:
        tenant_id: Target tenant ID (or 'all' for platform-wide)
        user_id: Not used (kept for API compatibility)
    
    Returns:
        Tenant-level engagement metrics for agent analysis
    """
    
    # Initialize DynamoDB clients
    dynamodb = boto3.resource('dynamodb')
    tenants_table = dynamodb.Table(os.environ.get('TENANTS_TABLE_NAME', 'Tenants'))
    metrics_table = dynamodb.Table(os.environ.get('USAGE_METRICS_TABLE_NAME', 'AgenticInsights-UsageMetrics'))
    
    try:
        print(f"[DEBUG] calculate_engagement_scores called with tenant_id='{tenant_id}', user_id='{user_id}'")
        
        # Get tenant(s) to analyze (case-insensitive check for "all")
        if tenant_id and tenant_id.lower() == "all":
            print(f"[DEBUG] Fetching all tenants for platform-wide analysis")
            tenants = get_all_tenants(tenants_table)
        else:
            print(f"[DEBUG] Fetching single tenant: {tenant_id}")
            tenant = get_tenant(tenants_table, tenant_id)
            tenants = [tenant] if tenant else []
        
        print(f"[DEBUG] Found {len(tenants)} tenant(s) to analyze")
        
        if not tenants:
            return {
                "error": True,
                "error_code": "NO_TENANTS_FOUND",
                "error_message": f"No tenants found for analysis",
                "timestamp": to_iso_string(utcnow())
            }
        
        # Date range for analysis (last 30 days)
        end_date = utcnow()
        start_date = end_date - timedelta(days=30)
        
        print(f"[DEBUG] Date range: {start_date.isoformat()} to {end_date.isoformat()}")
        
        # Collect tenant-level metrics
        tenant_metrics = []
        
        for tenant in tenants:
            tid = tenant.get('tenant_id')
            if not tid:
                print(f"[DEBUG] Skipping tenant with no tenant_id")
                continue
            
            print(f"[DEBUG] Collecting metrics for tenant: {tid}")
            metrics = collect_tenant_engagement_metrics(
                metrics_table, tid, tenant, start_date, end_date
            )
            if metrics:
                tenant_metrics.append(metrics)
            else:
                print(f"[DEBUG] No metrics returned for tenant {tid}")
        
        if not tenant_metrics:
            return {
                "error": True,
                "error_code": "INSUFFICIENT_DATA",
                "error_message": "Insufficient data to collect engagement metrics",
                "timestamp": to_iso_string(utcnow()),
                "tenant_id": tenant_id
            }
        
        # Calculate platform-wide aggregated statistics for comparison
        aggregated_stats = calculate_engagement_statistics(tenant_metrics)
        
        # Build response with tenant-level metrics for agent analysis
        response = {
            "analysis_type": "user_engagement",
            "timestamp": to_iso_string(utcnow()),
            "tenant_id": tenant_id,
            "data": {
                "tenant_metrics": tenant_metrics,
                "aggregated_statistics": aggregated_stats,
                "analysis_instructions": (
                    "Analyze tenant engagement metrics. Calculate average engagement scores per tenant. "
                    "Compare each tenant against platform benchmarks (mean, median, percentiles). "
                    "Identify high-performing and low-performing tenants. "
                    "Categorize tenants into engagement tiers: high (>70), medium (40-70), low (<40). "
                    "Provide actionable recommendations for improving tenant engagement."
                )
            },
            "metadata": {
                "tenant_metrics_count": len(tenant_metrics),
                "platform_tenants_in_stats": aggregated_stats.get('total_tenants_analyzed', 0),
                "date_range": {
                    "start": start_date.isoformat() + 'Z',
                    "end": end_date.isoformat() + 'Z',
                    "days": 30
                }
            }
        }
        
        return response
        
    except Exception as e:
        return {
            "error": True,
            "error_code": "ENGAGEMENT_COLLECTION_FAILED",
            "error_message": f"Failed to collect engagement metrics: {str(e)}",
            "timestamp": to_iso_string(utcnow()),
            "tenant_id": tenant_id
        }


def collect_tenant_engagement_metrics(metrics_table, tenant_id: str, tenant: Dict,
                                      start_date: datetime, end_date: datetime) -> Optional[Dict]:
    """
    Collect aggregated engagement metrics for a single tenant from aggregated metrics table.
    
    Returns tenant-level summary data for agent analysis.
    """
    
    try:
        # Query aggregated metrics for this tenant
        feature_metrics = get_tenant_feature_metrics(metrics_table, tenant_id, start_date, end_date)
        
        print(f"[DEBUG] Tenant {tenant_id}: Found {len(feature_metrics)} feature metric records")
        
        if not feature_metrics:
            return {
                "tenant_id": tenant_id,
                "tenant_name": tenant.get('tenant_name', tenant_id),
                "tier": tenant.get('tier', 'basic'),
                "status": "no_activity",
                "total_requests": 0,
                "unique_users": 0,
                "unique_days_active": 0,
                "features_used": [],
                "total_features_used": 0
            }
        
        # Aggregate metrics across all features and time periods
        total_requests = 0
        unique_users_set = set()
        unique_days_set = set()
        features_used = set()
        total_days = (end_date - start_date).days + 1
        
        for metric in feature_metrics:
            # Sum up usage counts (total requests)
            usage_count = metric.get('usage_count', 0)
            if isinstance(usage_count, Decimal):
                usage_count = int(usage_count)
            total_requests += usage_count
            
            # Track unique users (note: this is per time bucket, so we can't get exact unique users across all time)
            unique_users = metric.get('unique_users', 0)
            if isinstance(unique_users, Decimal):
                unique_users = int(unique_users)
            # Use max unique users as an approximation
            if unique_users > 0:
                unique_users_set.add(unique_users)
            
            # Track features used
            feature_name = metric.get('feature_name')
            if feature_name:
                features_used.add(feature_name)
            
            # Track unique days active
            timestamp_str = metric.get('timestamp')
            if timestamp_str:
                try:
                    metric_date = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                    if start_date <= metric_date <= end_date:
                        unique_days_set.add(metric_date.date())
                except Exception as e:
                    print(f"[DEBUG] Error parsing timestamp {timestamp_str}: {e}")
        
        # Calculate metrics
        # Use max unique users as approximation (since we can't get exact count from aggregated data)
        approx_unique_users = max(unique_users_set) if unique_users_set else 0
        unique_days_active = len(unique_days_set)
        activity_frequency = (unique_days_active / total_days) * 100 if total_days > 0 else 0
        feature_diversity = (len(features_used) / 6) * 100  # 6 total features available
        
        # Estimate engagement based on request volume (requests per day)
        avg_requests_per_day = total_requests / total_days if total_days > 0 else 0
        
        print(f"[DEBUG] Tenant {tenant_id} metrics: requests={total_requests}, users~{approx_unique_users}, days={unique_days_active}, features={len(features_used)}")
        
        return {
            "tenant_id": tenant_id,
            "tenant_name": tenant.get('tenant_name', tenant_id),
            "tier": tenant.get('tier', 'basic'),
            "status": "active",
            "total_requests": total_requests,
            "unique_users": approx_unique_users,
            "unique_days_active": unique_days_active,
            "activity_frequency": round(activity_frequency, 1),
            "feature_diversity": round(feature_diversity, 1),
            "avg_requests_per_day": round(avg_requests_per_day, 1),
            "total_features_used": len(features_used),
            "features_list": list(features_used)
        }
        
    except Exception as e:
        print(f"Error collecting engagement metrics for tenant {tenant_id}: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def get_tenant_feature_metrics(metrics_table, tenant_id: str, start_date: datetime, end_date: datetime) -> List[Dict]:
    """
    Query aggregated feature usage metrics for a tenant within the date range.
    
    Args:
        metrics_table: DynamoDB metrics table
        tenant_id: Tenant ID
        start_date: Start date for query
        end_date: End date for query
    
    Returns:
        List of feature usage metric records
    """
    metrics = []
    
    try:
        # Query through months in the date range
        current_date = start_date.replace(day=1)
        
        while current_date <= end_date:
            month = current_date.strftime('%Y-%m')
            
            # Query feature_usage metrics for this month
            pk = f"TENANT#{tenant_id}#METRIC#feature_usage#PERIOD#{month}"
            
            print(f"[DEBUG] Querying metrics with PK: {pk}")
            
            try:
                response = metrics_table.query(
                    KeyConditionExpression=Key('PK').eq(pk) & Key('SK').begins_with('TIMESTAMP#')
                )
                
                items = response.get('Items', [])
                print(f"[DEBUG] Found {len(items)} metric records for month {month}")
                
                # Filter by date range
                for item in items:
                    timestamp_str = item.get('timestamp')
                    if timestamp_str:
                        try:
                            item_date = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                            if start_date <= item_date <= end_date:
                                metrics.append(item)
                        except Exception:
                            pass
                
            except Exception as e:
                print(f"Error querying metrics for {month}: {str(e)}")
                import traceback
                traceback.print_exc()
            
            # Move to next month
            current_date = (current_date + timedelta(days=32)).replace(day=1)
        
        print(f"[DEBUG] Total metrics found after date filtering: {len(metrics)}")
        return metrics
        
    except Exception as e:
        print(f"Error getting tenant feature metrics: {str(e)}")
        import traceback
        traceback.print_exc()
        return []


def calculate_engagement_statistics(tenant_metrics: List[Dict]) -> Dict:
    """
    Calculate platform-wide aggregated statistics for engagement metrics.
    
    Args:
        tenant_metrics: List of tenant engagement metrics
    
    Returns:
        Aggregated statistics including mean, median, and percentiles
    """
    if not tenant_metrics:
        return {}
    
    # Extract metrics for active tenants only
    active_tenants = [t for t in tenant_metrics if t.get('status') == 'active']
    
    if not active_tenants:
        return {
            "total_tenants_analyzed": len(tenant_metrics),
            "active_tenants": 0,
            "note": "No active tenants with engagement data"
        }
    
    # Calculate statistics for each metric
    activity_frequencies = [t['activity_frequency'] for t in active_tenants if t.get('activity_frequency') is not None]
    feature_diversities = [t['feature_diversity'] for t in active_tenants if t.get('feature_diversity') is not None]
    requests_per_day = [t['avg_requests_per_day'] for t in active_tenants if t.get('avg_requests_per_day') is not None]
    
    stats = {
        "total_tenants_analyzed": len(tenant_metrics),
        "active_tenants": len(active_tenants),
        "scope": "platform_wide",
        "note": "Statistics calculated from all active tenants for comparison context"
    }
    
    if activity_frequencies:
        sorted_activity = sorted(activity_frequencies)
        stats["activity_frequency"] = {
            "mean": round(statistics.mean(activity_frequencies), 1),
            "median": round(statistics.median(activity_frequencies), 1),
            "percentile_25": round(sorted_activity[len(sorted_activity) // 4], 1),
            "percentile_75": round(sorted_activity[3 * len(sorted_activity) // 4], 1),
            "percentile_90": round(sorted_activity[9 * len(sorted_activity) // 10], 1) if len(sorted_activity) >= 10 else round(sorted_activity[-1], 1)
        }
    
    if feature_diversities:
        sorted_diversity = sorted(feature_diversities)
        stats["feature_diversity"] = {
            "mean": round(statistics.mean(feature_diversities), 1),
            "median": round(statistics.median(feature_diversities), 1),
            "percentile_25": round(sorted_diversity[len(sorted_diversity) // 4], 1),
            "percentile_75": round(sorted_diversity[3 * len(sorted_diversity) // 4], 1),
            "percentile_90": round(sorted_diversity[9 * len(sorted_diversity) // 10], 1) if len(sorted_diversity) >= 10 else round(sorted_diversity[-1], 1)
        }
    
    if requests_per_day:
        sorted_requests = sorted(requests_per_day)
        stats["requests_per_day"] = {
            "mean": round(statistics.mean(requests_per_day), 1),
            "median": round(statistics.median(requests_per_day), 1),
            "percentile_25": round(sorted_requests[len(sorted_requests) // 4], 1),
            "percentile_75": round(sorted_requests[3 * len(sorted_requests) // 4], 1),
            "percentile_90": round(sorted_requests[9 * len(sorted_requests) // 10], 1) if len(sorted_requests) >= 10 else round(sorted_requests[-1], 1)
        }
    
    return stats


def get_all_tenants(tenants_table) -> List[Dict]:
    """Retrieve all tenants from DynamoDB"""
    try:
        lab_tenant_ids = ['tenant-acme', 'tenant-globex', 'tenant-initech']
        scan_kwargs = {
                'FilterExpression': Attr('status').eq('active') & Attr('tenant_id').is_in(lab_tenant_ids),
                'Limit': 100  # Process in batches
            }
        response = tenants_table.scan(**scan_kwargs)
        tenants = response.get('Items', [])
        
        # Handle pagination if needed
        while 'LastEvaluatedKey' in response:
            response = tenants_table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
            tenants.extend(response.get('Items', []))
        
        return tenants
    except Exception as e:
        print(f"Error retrieving all tenants: {str(e)}")
        return []


def get_tenant(tenants_table, tenant_id: str) -> Optional[Dict]:
    """Retrieve a single tenant from DynamoDB"""
    try:
        response = tenants_table.get_item(Key={'tenant_id': tenant_id})
        return response.get('Item')
    except Exception as e:
        print(f"Error retrieving tenant {tenant_id}: {str(e)}")
        return None
