"""
Feature Adoption Rate Analyzer Tool

Analyzes feature adoption rates across tenants by calculating the percentage of active users
utilizing each feature. Identifies low-adoption features and provides improvement recommendations.
"""

import boto3
import os
from datetime import datetime, timedelta
from decimal import Decimal
from boto3.dynamodb.conditions import Key, Attr
from typing import Dict, List, Optional, Set
from tools.datetime_utils import utcnow, parse_iso_datetime, to_iso_string


def analyze_feature_adoption_rates(tenant_id: str, time_period_days: int = 30) -> Dict:
    """
    Analyze feature adoption rates across tenants.
    
    Args:
        tenant_id: Target tenant ID or 'all' for platform-wide analysis
        time_period_days: Time period in days for adoption calculation (default: 30)
    
    Returns:
        Feature adoption analysis with rates, rankings, and recommendations
    """
    
    # Initialize DynamoDB clients
    dynamodb = boto3.resource('dynamodb')
    tenants_table = dynamodb.Table(os.environ.get('TENANTS_TABLE_NAME', 'Tenants'))
    metrics_table = dynamodb.Table(os.environ.get('USAGE_METRICS_TABLE_NAME', 'AgenticInsights-UsageMetrics'))
    
    try:
        # Ensure time_period_days is an integer (handle string/float from API)
        if isinstance(time_period_days, str):
            time_period_days = int(time_period_days)
        elif isinstance(time_period_days, float):
            time_period_days = int(time_period_days)
        
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
        
        # Calculate date range for analysis
        end_date = utcnow()
        start_date = end_date - timedelta(days=time_period_days)
        
        # Analyze feature adoption
        if tenant_id.lower() == 'all':
            features = analyze_platform_wide_adoption(metrics_table, tenants, start_date, end_date)
        else:
            features = analyze_tenant_adoption(metrics_table, tenant_id, start_date, end_date)
        
        # Rank features by adoption rate
        features.sort(key=lambda x: x['adoption_rate'], reverse=True)
        for idx, feature in enumerate(features, 1):
            feature['rank'] = idx
        
        # Identify low-adoption features
        low_adoption_features = [f for f in features if f['adoption_rate'] < 20]
        
        # Generate recommendations
        recommendations = generate_adoption_recommendations(features, low_adoption_features)
        
        # Build response
        response = {
            "analysis_type": "feature_adoption",
            "timestamp": to_iso_string(utcnow()),
            "tenant_id": tenant_id,
            "data": {
                "features": features,
                "summary": {
                    "total_features": len(features),
                    "low_adoption_count": len(low_adoption_features),
                    "avg_adoption_rate": round(sum(f['adoption_rate'] for f in features) / len(features), 2) if features else 0
                }
            },
            "recommendations": recommendations,
            "metadata": {
                "query_duration_ms": 0,  # Placeholder
                "records_analyzed": len(features),
                "date_range": {
                    "start": start_date.isoformat() + 'Z',
                    "end": end_date.isoformat() + 'Z'
                },
                "time_period_days": time_period_days
            }
        }
        
        return response
        
    except Exception as e:
        return {
            "error": True,
            "error_code": "ADOPTION_ANALYSIS_FAILED",
            "error_message": f"Failed to analyze feature adoption: {str(e)}",
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


def analyze_tenant_adoption(metrics_table, tenant_id: str, start_date: datetime, end_date: datetime) -> List[Dict]:
    """
    Analyze feature adoption for a single tenant.
    
    Adoption Rate = (Feature_Users / Active_Users) * 100
    """
    try:
        # Get all active users in the time period
        active_users = get_active_users(metrics_table, tenant_id, start_date, end_date)
        total_active_users = len(active_users)
        
        if total_active_users == 0:
            return []
        
        # Get feature usage data
        feature_data = get_feature_usage_data(metrics_table, tenant_id, start_date, end_date)
        
        # Calculate adoption rates for each feature
        features = []
        for feature_name, data in feature_data.items():
            feature_users = data['unique_users']
            total_operations = data['total_operations']
            
            adoption_rate = (len(feature_users) / total_active_users) * 100
            
            feature_info = {
                "feature_name": feature_name,
                "adoption_rate": round(adoption_rate, 2),
                "active_users": total_active_users,
                "feature_users": len(feature_users),
                "total_operations": total_operations,
                "rank": 0  # Will be assigned later
            }
            
            # Add status flag for low adoption
            if adoption_rate < 20:
                feature_info['status'] = 'low_adoption'
            
            features.append(feature_info)
        
        return features
        
    except Exception as e:
        print(f"Error analyzing tenant adoption: {str(e)}")
        return []


def analyze_platform_wide_adoption(metrics_table, tenants: List[Dict], start_date: datetime, end_date: datetime) -> List[Dict]:
    """
    Analyze feature adoption across all tenants (platform-wide).
    """
    try:
        # Aggregate data across all tenants
        all_active_users = set()
        feature_aggregates = {}
        
        for tenant in tenants:
            tenant_id = tenant.get('tenant_id')
            
            # Get active users for this tenant
            tenant_active_users = get_active_users(metrics_table, tenant_id, start_date, end_date)
            all_active_users.update(tenant_active_users)
            
            # Get feature usage data for this tenant
            tenant_feature_data = get_feature_usage_data(metrics_table, tenant_id, start_date, end_date)
            
            # Aggregate feature data
            for feature_name, data in tenant_feature_data.items():
                if feature_name not in feature_aggregates:
                    feature_aggregates[feature_name] = {
                        'unique_users': set(),
                        'total_operations': 0
                    }
                
                feature_aggregates[feature_name]['unique_users'].update(data['unique_users'])
                feature_aggregates[feature_name]['total_operations'] += data['total_operations']
        
        total_active_users = len(all_active_users)
        
        if total_active_users == 0:
            return []
        
        # Calculate adoption rates
        features = []
        for feature_name, data in feature_aggregates.items():
            feature_users = len(data['unique_users'])
            total_operations = data['total_operations']
            
            adoption_rate = (feature_users / total_active_users) * 100
            
            feature_info = {
                "feature_name": feature_name,
                "adoption_rate": round(adoption_rate, 2),
                "active_users": total_active_users,
                "feature_users": feature_users,
                "total_operations": total_operations,
                "rank": 0  # Will be assigned later
            }
            
            # Add status flag for low adoption
            if adoption_rate < 20:
                feature_info['status'] = 'low_adoption'
            
            features.append(feature_info)
        
        return features
        
    except Exception as e:
        print(f"Error analyzing platform-wide adoption: {str(e)}")
        return []


def get_active_users(metrics_table, tenant_id: str, start_date: datetime, end_date: datetime) -> Set[str]:
    """
    Get set of unique active users for a tenant in the time period.
    
    Active user = any user with at least one feature usage metric.
    """
    active_users = set()
    
    try:
        # Query months in the date range
        current_date = start_date.replace(day=1)
        end_month = end_date.replace(day=1)
        
        while current_date <= end_month:
            month = current_date.strftime('%Y-%m')
            
            # Query feature_usage metrics for this month
            pk = f"TENANT#{tenant_id}#METRIC#feature_usage#PERIOD#{month}"
            
            try:
                response = metrics_table.query(
                    KeyConditionExpression=Key('PK').eq(pk) & Key('SK').begins_with('TIMESTAMP#')
                )
                
                items = response.get('Items', [])
                
                # Extract unique users from metrics
                for item in items:
                    timestamp_str = item.get('timestamp', '')
                    
                    # Check if timestamp is within our date range
                    try:
                        item_date = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                        if start_date <= item_date <= end_date:
                            # Extract user_id if present in the metric
                            user_id = item.get('user_id')
                            if user_id:
                                active_users.add(user_id)
                            
                            # Also check unique_users field (may be a number or list)
                            unique_users = item.get('unique_users')
                            if unique_users:
                                if isinstance(unique_users, (int, Decimal)):
                                    # If it's a count, we can't get individual user IDs
                                    # Use a placeholder approach based on tenant and feature
                                    pass
                                elif isinstance(unique_users, list):
                                    active_users.update(unique_users)
                    except:
                        pass
                
            except Exception as e:
                print(f"Error querying metrics for {month}: {str(e)}")
            
            # Move to next month
            current_date = (current_date + timedelta(days=32)).replace(day=1)
        
        # If we couldn't extract individual user IDs, create synthetic user set
        # based on the unique_users counts in the metrics
        if not active_users:
            active_users = estimate_active_users_from_counts(metrics_table, tenant_id, start_date, end_date)
        
        return active_users
        
    except Exception as e:
        print(f"Error getting active users: {str(e)}")
        return set()


def estimate_active_users_from_counts(metrics_table, tenant_id: str, start_date: datetime, end_date: datetime) -> Set[str]:
    """
    Estimate active users when individual user IDs are not available.
    Uses unique_users counts from metrics to create synthetic user identifiers.
    """
    # Get the maximum unique_users count across all features as an estimate
    max_users = 0
    
    try:
        current_date = start_date.replace(day=1)
        end_month = end_date.replace(day=1)
        
        while current_date <= end_month:
            month = current_date.strftime('%Y-%m')
            pk = f"TENANT#{tenant_id}#METRIC#feature_usage#PERIOD#{month}"
            
            try:
                response = metrics_table.query(
                    KeyConditionExpression=Key('PK').eq(pk) & Key('SK').begins_with('TIMESTAMP#')
                )
                
                for item in response.get('Items', []):
                    unique_users = item.get('unique_users', 0)
                    if isinstance(unique_users, Decimal):
                        unique_users = int(unique_users)
                    if isinstance(unique_users, int):
                        max_users = max(max_users, unique_users)
            except:
                pass
            
            current_date = (current_date + timedelta(days=32)).replace(day=1)
        
        # Create synthetic user set
        return {f"{tenant_id}_user_{i}" for i in range(max_users)}
        
    except Exception as e:
        print(f"Error estimating active users: {str(e)}")
        return set()


def get_feature_usage_data(metrics_table, tenant_id: str, start_date: datetime, end_date: datetime) -> Dict[str, Dict]:
    """
    Get feature usage data for a tenant in the time period.
    
    Returns dict mapping feature_name to {unique_users: set, total_operations: int}
    """
    feature_data = {}
    
    try:
        # Query months in the date range
        current_date = start_date.replace(day=1)
        end_month = end_date.replace(day=1)
        
        while current_date <= end_month:
            month = current_date.strftime('%Y-%m')
            
            # Query feature_usage metrics for this month
            pk = f"TENANT#{tenant_id}#METRIC#feature_usage#PERIOD#{month}"
            
            try:
                response = metrics_table.query(
                    KeyConditionExpression=Key('PK').eq(pk) & Key('SK').begins_with('TIMESTAMP#')
                )
                
                items = response.get('Items', [])
                
                # Process each metric
                for item in items:
                    timestamp_str = item.get('timestamp', '')
                    
                    # Check if timestamp is within our date range
                    try:
                        item_date = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                        if not (start_date <= item_date <= end_date):
                            continue
                    except:
                        continue
                    
                    feature_name = item.get('feature_name')
                    if not feature_name:
                        continue
                    
                    # Initialize feature data if not exists
                    if feature_name not in feature_data:
                        feature_data[feature_name] = {
                            'unique_users': set(),
                            'total_operations': 0
                        }
                    
                    # Add usage count
                    usage_count = item.get('usage_count', 0)
                    if isinstance(usage_count, Decimal):
                        usage_count = int(usage_count)
                    feature_data[feature_name]['total_operations'] += usage_count
                    
                    # Add unique users
                    user_id = item.get('user_id')
                    if user_id:
                        feature_data[feature_name]['unique_users'].add(user_id)
                    
                    # Handle unique_users field
                    unique_users = item.get('unique_users')
                    if unique_users:
                        if isinstance(unique_users, list):
                            feature_data[feature_name]['unique_users'].update(unique_users)
                        elif isinstance(unique_users, (int, Decimal)):
                            # Create synthetic users for this feature
                            count = int(unique_users) if isinstance(unique_users, Decimal) else unique_users
                            for i in range(count):
                                feature_data[feature_name]['unique_users'].add(f"{tenant_id}_{feature_name}_user_{i}")
                
            except Exception as e:
                print(f"Error querying feature data for {month}: {str(e)}")
            
            # Move to next month
            current_date = (current_date + timedelta(days=32)).replace(day=1)
        
        return feature_data
        
    except Exception as e:
        print(f"Error getting feature usage data: {str(e)}")
        return {}


def generate_adoption_recommendations(features: List[Dict], low_adoption_features: List[Dict]) -> List[Dict]:
    """
    Generate recommendations for improving feature adoption.
    
    Creates specific recommendations for low-performing features.
    """
    recommendations = []
    
    if not features:
        recommendations.append({
            "priority": "medium",
            "action": "Insufficient data for feature adoption analysis",
            "rationale": "No feature usage data found in the specified time period"
        })
        return recommendations
    
    # Recommendation: Low adoption features
    if low_adoption_features:
        for feature in low_adoption_features[:3]:  # Top 3 lowest adoption
            feature_name = feature['feature_name']
            adoption_rate = feature['adoption_rate']
            feature_users = feature['feature_users']
            active_users = feature['active_users']
            
            # Calculate improvement potential
            target_adoption = 40  # Target 40% adoption
            potential_new_users = int((target_adoption / 100) * active_users) - feature_users
            
            recommendations.append({
                "priority": "high" if adoption_rate < 10 else "medium",
                "feature": feature_name,
                "action": f"Increase adoption of '{feature_name}' feature",
                "rationale": f"Only {adoption_rate}% adoption rate ({feature_users}/{active_users} users)",
                "improvement_potential": f"{potential_new_users} additional users to reach 40% adoption",
                "suggested_tactics": generate_feature_specific_tactics(feature_name, adoption_rate)
            })
    
    # Recommendation: High-performing features
    high_adoption_features = [f for f in features if f['adoption_rate'] >= 70]
    if high_adoption_features:
        top_feature = high_adoption_features[0]
        recommendations.append({
            "priority": "low",
            "action": f"Leverage success of '{top_feature['feature_name']}' feature",
            "rationale": f"High adoption rate of {top_feature['adoption_rate']}% demonstrates strong user value",
            "suggested_tactics": [
                "Document best practices from this feature",
                "Apply similar UX patterns to low-adoption features",
                "Use as case study in user onboarding"
            ]
        })
    
    # Recommendation: Overall adoption improvement
    avg_adoption = sum(f['adoption_rate'] for f in features) / len(features)
    if avg_adoption < 50:
        recommendations.append({
            "priority": "high",
            "action": "Platform-wide feature adoption improvement program",
            "rationale": f"Average feature adoption of {avg_adoption:.1f}% indicates underutilization",
            "affected_features": len(features),
            "target_adoption": "60%",
            "suggested_improvements": [
                "Implement in-app feature discovery",
                "Create feature highlight campaigns",
                "Add contextual tooltips and tutorials",
                "Send targeted feature adoption emails"
            ]
        })
    
    # Recommendation: Feature portfolio optimization
    very_low_adoption = [f for f in features if f['adoption_rate'] < 5]
    if very_low_adoption:
        recommendations.append({
            "priority": "medium",
            "action": "Evaluate feature portfolio for potential deprecation",
            "rationale": f"{len(very_low_adoption)} features with <5% adoption may not provide sufficient value",
            "affected_features": [f['feature_name'] for f in very_low_adoption],
            "suggested_approach": [
                "Conduct user research on feature value",
                "Consider feature redesign or simplification",
                "Evaluate deprecation if no improvement path exists"
            ]
        })
    
    return recommendations


def generate_feature_specific_tactics(feature_name: str, adoption_rate: float) -> List[str]:
    """
    Generate feature-specific improvement tactics based on feature name and adoption rate.
    """
    # Base tactics for all low-adoption features
    tactics = [
        "Create in-app tutorial or walkthrough",
        "Add feature to onboarding checklist",
        "Send targeted email campaign highlighting benefits"
    ]
    
    # Feature-specific tactics
    feature_tactics = {
        'ai_descriptions': [
            "Showcase AI-generated examples in product catalog",
            "Add 'Generate with AI' button prominently in UI",
            "Demonstrate time savings with before/after examples"
        ],
        'users': [
            "Simplify user creation workflow",
            "Add bulk user import capability",
            "Provide user management templates"
        ],
        'orders': [
            "Highlight order tracking benefits",
            "Add order analytics dashboard",
            "Integrate with popular e-commerce platforms"
        ],
        'products': [
            "Improve product catalog navigation",
            "Add product import/export features",
            "Provide product templates"
        ]
    }
    
    # Add feature-specific tactics if available
    if feature_name in feature_tactics:
        tactics.extend(feature_tactics[feature_name])
    else:
        # Generic tactics for unknown features
        tactics.extend([
            f"Improve discoverability of {feature_name} in navigation",
            f"Add contextual help for {feature_name}",
            f"Collect user feedback on {feature_name} usability"
        ])
    
    # Add urgency-based tactics
    if adoption_rate < 5:
        tactics.append("Consider feature redesign or UX improvements")
    
    return tactics
