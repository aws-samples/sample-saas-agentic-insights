"""
Customer Lifetime Value (CLTV) Projector Tool

Projects customer lifetime value based on historical usage patterns and retention metrics.
Provides segmentation by tenant tier and strategic recommendations.
"""

import boto3
import os
from datetime import datetime, timedelta
from decimal import Decimal
from boto3.dynamodb.conditions import Key, Attr
from typing import Dict, List, Optional
import statistics
from tools.datetime_utils import utcnow, parse_iso_datetime, to_iso_string


# Tier pricing configuration
TIER_PRICING = {
    'basic': 29,
    'premium': 99,
    'enterprise': 299,
    'unknown': 29  # Default to basic pricing
}


def project_customer_lifetime_value(tenant_id: str, projection_months: int = 12) -> Dict:
    """
    Project Customer Lifetime Value for tenants.
    
    Args:
        tenant_id: Target tenant ID or 'all' for platform-wide analysis
        projection_months: Number of months to project (default: 12)
    
    Returns:
        CLTV projections with tenant data, segments, and recommendations
    """
    
    # Initialize DynamoDB clients
    dynamodb = boto3.resource('dynamodb')
    tenants_table = dynamodb.Table(os.environ.get('TENANTS_TABLE_NAME', 'Tenants'))
    metrics_table = dynamodb.Table(os.environ.get('USAGE_METRICS_TABLE_NAME', 'AgenticInsights-UsageMetrics'))
    
    try:
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
        
        # Calculate CLTV for each tenant
        tenant_projections = []
        
        for tenant in tenants:
            cltv_data = calculate_tenant_cltv(tenant, metrics_table, projection_months)
            if cltv_data:
                tenant_projections.append(cltv_data)
        
        # Segment tenants by CLTV
        segments = segment_by_cltv(tenant_projections)
        
        # Generate recommendations
        recommendations = generate_cltv_recommendations(tenant_projections, segments)
        
        # Build response
        response = {
            "analysis_type": "customer_lifetime_value",
            "timestamp": to_iso_string(utcnow()),
            "tenant_id": tenant_id,
            "data": {
                "tenant_projections": tenant_projections,
                "segments": segments
            },
            "recommendations": recommendations,
            "metadata": {
                "query_duration_ms": 0,  # Placeholder
                "records_analyzed": len(tenant_projections),
                "projection_months": projection_months
            }
        }
        
        return response
        
    except Exception as e:
        return {
            "error": True,
            "error_code": "CLTV_CALCULATION_FAILED",
            "error_message": f"Failed to calculate CLTV: {str(e)}",
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


def calculate_tenant_cltv(tenant: Dict, metrics_table, projection_months: int) -> Optional[Dict]:
    """
    Calculate CLTV projection for a single tenant.
    
    CLTV = Monthly_Revenue * Retention_Rate * projection_months
    """
    tenant_id = tenant.get('tenant_id')
    tier_raw = tenant.get('tier', 'unknown')
    
    # Handle tier value - could be string, Decimal, or other type from DynamoDB
    if isinstance(tier_raw, Decimal):
        tier = str(tier_raw).lower()
    elif isinstance(tier_raw, str):
        tier = tier_raw.lower()
    else:
        tier = 'unknown'
    
    created_at_str = tenant.get('created_at')
    
    if not created_at_str:
        return None
    
    try:
        # Get monthly revenue based on tier
        monthly_revenue = TIER_PRICING.get(tier, TIER_PRICING['unknown'])
        
        # Ensure monthly_revenue is a number (handle DynamoDB Decimal or string)
        if isinstance(monthly_revenue, str):
            monthly_revenue = float(monthly_revenue)
        elif isinstance(monthly_revenue, Decimal):
            monthly_revenue = float(monthly_revenue)
        elif not isinstance(monthly_revenue, (int, float)):
            # Fallback to unknown tier pricing
            monthly_revenue = float(TIER_PRICING['unknown'])
        
        # Calculate retention rate based on usage patterns
        retention_rate = calculate_retention_rate(tenant, metrics_table)
        
        # Ensure retention_rate is a number
        if isinstance(retention_rate, str):
            retention_rate = float(retention_rate)
        elif isinstance(retention_rate, Decimal):
            retention_rate = float(retention_rate)
        
        # Ensure projection_months is a number
        if isinstance(projection_months, str):
            projection_months = int(projection_months)
        
        # Calculate CLTV projection
        projected_cltv = monthly_revenue * retention_rate * projection_months
        
        # Calculate tenant tenure
        onboarding_date = parse_iso_datetime(created_at_str)
        tenure_days = (utcnow() - onboarding_date).days
        tenure_months = max(1, tenure_days / 30)  # At least 1 month
        
        return {
            "tenant_id": tenant_id,
            "tenant_name": tenant.get('tenant_name', 'Unknown'),
            "tier": tier,
            "monthly_revenue": monthly_revenue,
            "retention_rate": round(retention_rate, 3),
            "projected_cltv_12m": round(projected_cltv, 2),
            "tenure_months": round(tenure_months, 1),
            "segment": None  # Will be assigned during segmentation
        }
        
    except Exception as e:
        print(f"Error calculating CLTV for tenant {tenant_id}: {str(e)}")
        print(f"Debug - monthly_revenue type: {type(monthly_revenue)}, value: {monthly_revenue}")
        print(f"Debug - retention_rate type: {type(retention_rate)}, value: {retention_rate}")
        print(f"Debug - projection_months type: {type(projection_months)}, value: {projection_months}")
        print(f"Debug - tier: {tier}, tier_raw: {tier_raw}")
        return None


def calculate_retention_rate(tenant: Dict, metrics_table) -> float:
    """
    Calculate retention rate based on usage patterns.
    
    Retention_Rate = (active_months / total_months_since_onboarding)
    
    An active month is one where the tenant has at least one feature usage metric.
    """
    tenant_id = tenant.get('tenant_id')
    created_at_str = tenant.get('created_at')
    
    try:
        onboarding_date = parse_iso_datetime(created_at_str)
        current_date = utcnow()
        
        # Calculate total months since onboarding
        tenure_days = (current_date - onboarding_date).days
        total_months = max(1, int(tenure_days / 30))  # At least 1 month
        
        # Limit analysis to last 12 months or tenure, whichever is shorter
        analysis_months = min(12, total_months)
        
        # Count active months
        active_months = 0
        start_date = current_date - timedelta(days=analysis_months * 30)
        
        current_check = start_date
        while current_check <= current_date:
            month = current_check.strftime('%Y-%m')
            
            # Check if tenant has any activity in this month
            if has_activity_in_month(metrics_table, tenant_id, month):
                active_months += 1
            
            # Move to next month
            current_check = (current_check.replace(day=1) + timedelta(days=32)).replace(day=1)
        
        # Calculate retention rate
        retention_rate = active_months / analysis_months if analysis_months > 0 else 0.0
        
        # Apply minimum retention rate of 0.5 for very new tenants
        if total_months < 2:
            retention_rate = max(retention_rate, 0.5)
        
        return min(1.0, retention_rate)  # Cap at 1.0
        
    except Exception as e:
        print(f"Error calculating retention rate for tenant {tenant_id}: {str(e)}")
        return 0.7  # Default to 70% retention if calculation fails


def has_activity_in_month(metrics_table, tenant_id: str, month: str) -> bool:
    """
    Check if tenant has any feature usage activity in a specific month.
    """
    try:
        pk = f"TENANT#{tenant_id}#METRIC#feature_usage#PERIOD#{month}"
        
        response = metrics_table.query(
            KeyConditionExpression=Key('PK').eq(pk),
            Limit=1  # We only need to know if any records exist
        )
        
        items = response.get('Items', [])
        
        # Check if any item has usage_count > 0
        for item in items:
            usage_count = item.get('usage_count', 0)
            if isinstance(usage_count, Decimal):
                usage_count = float(usage_count)
            if usage_count > 0:
                return True
        
        return len(items) > 0  # Consider active if any metrics exist
        
    except Exception as e:
        print(f"Error checking activity for {tenant_id} in {month}: {str(e)}")
        return False


def segment_by_cltv(tenant_projections: List[Dict]) -> Dict:
    """
    Segment tenants by CLTV value and tier.
    
    Segments:
    - high_value: CLTV > 75th percentile
    - medium_value: CLTV between 25th and 75th percentile
    - at_risk: Low retention rate (< 0.7) regardless of CLTV
    """
    if not tenant_projections:
        return {}
    
    try:
        # Extract CLTV values
        cltv_values = [t['projected_cltv_12m'] for t in tenant_projections]
        sorted_cltv = sorted(cltv_values)
        
        # Calculate percentiles
        p25 = calculate_percentile(sorted_cltv, 25)
        p75 = calculate_percentile(sorted_cltv, 75)
        
        # Segment tenants
        high_value_tenants = []
        medium_value_tenants = []
        at_risk_tenants = []
        
        for tenant in tenant_projections:
            cltv = tenant['projected_cltv_12m']
            retention = tenant['retention_rate']
            
            # At-risk: low retention
            if retention < 0.7:
                tenant['segment'] = 'at_risk'
                at_risk_tenants.append(tenant)
            # High value: above 75th percentile
            elif cltv >= p75:
                tenant['segment'] = 'high_value'
                high_value_tenants.append(tenant)
            # Medium value: between 25th and 75th percentile
            else:
                tenant['segment'] = 'medium_value'
                medium_value_tenants.append(tenant)
        
        # Calculate segment statistics
        segments = {}
        
        if high_value_tenants:
            segments['high_value'] = {
                "count": len(high_value_tenants),
                "avg_cltv": round(statistics.mean([t['projected_cltv_12m'] for t in high_value_tenants]), 2),
                "avg_retention": round(statistics.mean([t['retention_rate'] for t in high_value_tenants]), 3),
                "threshold": f"75th percentile (${p75:.2f})",
                "tier_breakdown": calculate_tier_breakdown(high_value_tenants)
            }
        
        if medium_value_tenants:
            segments['medium_value'] = {
                "count": len(medium_value_tenants),
                "avg_cltv": round(statistics.mean([t['projected_cltv_12m'] for t in medium_value_tenants]), 2),
                "avg_retention": round(statistics.mean([t['retention_rate'] for t in medium_value_tenants]), 3),
                "tier_breakdown": calculate_tier_breakdown(medium_value_tenants)
            }
        
        if at_risk_tenants:
            segments['at_risk'] = {
                "count": len(at_risk_tenants),
                "avg_cltv": round(statistics.mean([t['projected_cltv_12m'] for t in at_risk_tenants]), 2),
                "avg_retention": round(statistics.mean([t['retention_rate'] for t in at_risk_tenants]), 3),
                "tier_breakdown": calculate_tier_breakdown(at_risk_tenants)
            }
        
        return segments
        
    except Exception as e:
        print(f"Error segmenting tenants: {str(e)}")
        return {}


def calculate_tier_breakdown(tenants: List[Dict]) -> Dict:
    """Calculate count of tenants by tier"""
    tier_counts = {}
    for tenant in tenants:
        tier = tenant.get('tier', 'unknown')
        tier_counts[tier] = tier_counts.get(tier, 0) + 1
    return tier_counts


def calculate_percentile(sorted_values: List[float], percentile: int) -> float:
    """Calculate a specific percentile from sorted values"""
    if not sorted_values:
        return 0.0
    
    index = (percentile / 100) * (len(sorted_values) - 1)
    lower_index = int(index)
    upper_index = min(lower_index + 1, len(sorted_values) - 1)
    
    if lower_index == upper_index:
        return sorted_values[lower_index]
    
    # Linear interpolation
    weight = index - lower_index
    return sorted_values[lower_index] * (1 - weight) + sorted_values[upper_index] * weight


def generate_cltv_recommendations(tenant_projections: List[Dict], segments: Dict) -> List[Dict]:
    """
    Generate strategic recommendations based on CLTV analysis.
    
    Creates recommendations for retention, upselling, and at-risk mitigation.
    """
    recommendations = []
    
    if not tenant_projections:
        return recommendations
    
    # Recommendation: At-risk tenants
    at_risk_segment = segments.get('at_risk', {})
    at_risk_count = at_risk_segment.get('count', 0)
    
    if at_risk_count > 0:
        avg_retention = at_risk_segment.get('avg_retention', 0)
        potential_revenue_loss = at_risk_segment.get('avg_cltv', 0) * at_risk_count
        
        recommendations.append({
            "priority": "critical",
            "action": "Implement retention program for at-risk tenants",
            "rationale": f"{at_risk_count} tenants with retention rate below 70% (avg: {avg_retention:.1%})",
            "affected_tenants": at_risk_count,
            "estimated_revenue_impact": round(potential_revenue_loss * 0.3, 2),  # 30% recovery potential
            "suggested_tactics": [
                "Schedule customer success check-ins",
                "Identify and resolve usage blockers",
                "Provide personalized training sessions",
                "Offer incentives for continued engagement"
            ]
        })
    
    # Recommendation: High-value segment growth
    high_value_segment = segments.get('high_value', {})
    high_value_count = high_value_segment.get('count', 0)
    
    if high_value_count > 0:
        tier_breakdown = high_value_segment.get('tier_breakdown', {})
        basic_in_high_value = tier_breakdown.get('basic', 0)
        
        if basic_in_high_value > 0:
            upsell_potential = basic_in_high_value * (TIER_PRICING['premium'] - TIER_PRICING['basic']) * 12
            
            recommendations.append({
                "priority": "high",
                "action": "Upsell basic tier tenants in high-value segment to premium",
                "rationale": f"{basic_in_high_value} basic tier tenants showing high engagement and retention",
                "affected_tenants": basic_in_high_value,
                "estimated_revenue_impact": round(upsell_potential, 2),
                "conversion_rate_assumption": "30%"
            })
    
    # Recommendation: Medium-value segment optimization
    medium_value_segment = segments.get('medium_value', {})
    medium_value_count = medium_value_segment.get('count', 0)
    
    if medium_value_count > 0:
        avg_retention = medium_value_segment.get('avg_retention', 0)
        
        if avg_retention < 0.85:
            recommendations.append({
                "priority": "medium",
                "action": "Improve retention for medium-value segment",
                "rationale": f"{medium_value_count} tenants with moderate retention ({avg_retention:.1%})",
                "affected_tenants": medium_value_count,
                "target_retention": "90%",
                "suggested_improvements": [
                    "Enhance feature adoption programs",
                    "Provide regular usage insights",
                    "Create community engagement opportunities"
                ]
            })
    
    # Recommendation: Overall CLTV improvement
    total_tenants = len(tenant_projections)
    avg_cltv = statistics.mean([t['projected_cltv_12m'] for t in tenant_projections])
    avg_retention = statistics.mean([t['retention_rate'] for t in tenant_projections])
    
    if avg_retention < 0.8:
        retention_improvement = 0.9 - avg_retention
        revenue_impact = total_tenants * avg_cltv * retention_improvement
        
        recommendations.append({
            "priority": "high",
            "action": "Platform-wide retention improvement initiative",
            "rationale": f"Average retention of {avg_retention:.1%} below target of 90%",
            "affected_tenants": total_tenants,
            "estimated_revenue_impact": round(revenue_impact, 2),
            "key_metrics": {
                "current_avg_cltv": round(avg_cltv, 2),
                "current_avg_retention": round(avg_retention, 3),
                "target_retention": 0.90
            }
        })
    
    # Positive recommendation: Strong performance
    if avg_retention >= 0.85 and at_risk_count == 0:
        recommendations.append({
            "priority": "low",
            "action": "Maintain current customer success practices",
            "rationale": f"Strong retention performance ({avg_retention:.1%}) with no at-risk tenants",
            "affected_tenants": total_tenants,
            "avg_cltv": round(avg_cltv, 2)
        })
    
    return recommendations

