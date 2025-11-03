import boto3
import os
from datetime import datetime, timedelta
from boto3.dynamodb.conditions import Key
from typing import Dict, Any, List


def analyze_feature_adoption(tenant_id: str, scope: str, user_role: str = "tenant_admin") -> Dict[str, Any]:
    """
    Analyzes feature adoption patterns and utilization rates
    
    Args:
        tenant_id: Target tenant ID
        scope: Analysis scope (platform, tenant, user)
        user_role: Role of requesting user for access control
    
    Returns:
        Feature adoption analysis with recommendations
    """
    
    # Query usage patterns across different features
    adoption_data = query_feature_adoption_data(tenant_id, scope, user_role)
    
    # Calculate adoption rates and usage frequency
    adoption_metrics = calculate_adoption_metrics(adoption_data)
    
    # Identify underutilized features
    underutilized = identify_underutilized_features(adoption_metrics)
    
    return {
        "tenant_id": tenant_id,
        "scope": scope,
        "user_role": user_role,
        "adoption_summary": adoption_metrics,
        "underutilized_features": underutilized,
        "recommendations": generate_adoption_recommendations(adoption_metrics, underutilized)
    }


def query_feature_adoption_data(tenant_id: str, scope: str, user_role: str) -> Dict[str, Any]:
    """Query feature adoption data from metrics"""
    
    dynamodb = boto3.resource('dynamodb')
    metrics_table = dynamodb.Table(os.environ.get('METRICS_AGGREGATION_TABLE_NAME', 'MetricsAggregation'))
    
    # Get current month
    current_month = datetime.now().strftime('%Y-%m')
    
    try:
        if scope == "platform" and user_role == "platform_admin":
            # Platform-wide feature adoption
            response = metrics_table.query(
                IndexName='MonthIndex',
                KeyConditionExpression=Key('month').eq(current_month)
            )
        else:
            # Single tenant feature adoption
            response = metrics_table.query(
                IndexName='MonthIndex',
                KeyConditionExpression=Key('month').eq(current_month),
                FilterExpression=Key('tenant_id').eq(tenant_id)
            )
        
        return process_feature_data(response['Items'], scope)
        
    except Exception as e:
        return {"error": f"Failed to query feature adoption data: {str(e)}"}


def process_feature_data(metrics_items: List[Dict], scope: str) -> Dict[str, Any]:
    """Process raw metrics into feature adoption data"""
    
    feature_metrics = {
        "products": {"usage_count": 0, "active_tenants": set(), "total_operations": 0},
        "orders": {"usage_count": 0, "active_tenants": set(), "total_operations": 0},
        "users": {"usage_count": 0, "active_tenants": set(), "total_operations": 0},
        "ai_descriptions": {"usage_count": 0, "active_tenants": set(), "total_operations": 0}
    }
    
    total_tenants = set()
    
    for item in metrics_items:
        tenant_id = item['tenant_id']
        metric_name = item['metric_name']
        total_count = float(item['total_count'])
        
        total_tenants.add(tenant_id)
        
        # Categorize metrics by feature
        # This is a simplified approach - in production, you'd have more specific feature metrics
        if any(keyword in metric_name.lower() for keyword in ['product', 'catalog']):
            feature_metrics["products"]["usage_count"] += total_count
            feature_metrics["products"]["active_tenants"].add(tenant_id)
            feature_metrics["products"]["total_operations"] += total_count
            
        elif any(keyword in metric_name.lower() for keyword in ['order', 'cart', 'checkout']):
            feature_metrics["orders"]["usage_count"] += total_count
            feature_metrics["orders"]["active_tenants"].add(tenant_id)
            feature_metrics["orders"]["total_operations"] += total_count
            
        elif any(keyword in metric_name.lower() for keyword in ['user', 'auth', 'login']):
            feature_metrics["users"]["usage_count"] += total_count
            feature_metrics["users"]["active_tenants"].add(tenant_id)
            feature_metrics["users"]["total_operations"] += total_count
            
        elif 'bedrock' in metric_name.lower():
            feature_metrics["ai_descriptions"]["usage_count"] += total_count
            feature_metrics["ai_descriptions"]["active_tenants"].add(tenant_id)
            feature_metrics["ai_descriptions"]["total_operations"] += total_count
    
    # Convert sets to counts for JSON serialization
    for feature in feature_metrics:
        feature_metrics[feature]["active_tenant_count"] = len(feature_metrics[feature]["active_tenants"])
        del feature_metrics[feature]["active_tenants"]
    
    return {
        "feature_metrics": feature_metrics,
        "total_tenant_count": len(total_tenants),
        "analysis_period": datetime.now().strftime('%Y-%m')
    }


def calculate_adoption_metrics(adoption_data: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate adoption rates and usage frequency"""
    
    if "error" in adoption_data:
        return adoption_data
    
    feature_metrics = adoption_data["feature_metrics"]
    total_tenants = adoption_data["total_tenant_count"]
    
    adoption_summary = {}
    
    for feature_name, metrics in feature_metrics.items():
        active_tenants = metrics["active_tenant_count"]
        total_operations = metrics["total_operations"]
        
        # Calculate adoption rate
        adoption_rate = active_tenants / max(total_tenants, 1)
        
        # Determine usage frequency category
        if total_operations > 1000:
            usage_frequency = "high"
        elif total_operations > 100:
            usage_frequency = "medium"
        elif total_operations > 10:
            usage_frequency = "low"
        else:
            usage_frequency = "minimal"
        
        # Calculate average operations per active tenant
        avg_operations = total_operations / max(active_tenants, 1)
        
        adoption_summary[feature_name] = {
            "adoption_rate": round(adoption_rate, 3),
            "usage_frequency": usage_frequency,
            "active_tenants": active_tenants,
            "total_operations": int(total_operations),
            "avg_operations_per_tenant": round(avg_operations, 1),
            "adoption_status": get_adoption_status(adoption_rate, usage_frequency)
        }
    
    return adoption_summary


def get_adoption_status(adoption_rate: float, usage_frequency: str) -> str:
    """Determine overall adoption status"""
    
    if adoption_rate > 0.8 and usage_frequency in ["high", "medium"]:
        return "excellent"
    elif adoption_rate > 0.6 and usage_frequency in ["medium", "high"]:
        return "good"
    elif adoption_rate > 0.3:
        return "moderate"
    else:
        return "low"


def identify_underutilized_features(adoption_metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Identify features with low adoption or usage"""
    
    if "error" in adoption_metrics:
        return []
    
    underutilized = []
    
    for feature_name, metrics in adoption_metrics.items():
        adoption_rate = metrics["adoption_rate"]
        usage_frequency = metrics["usage_frequency"]
        adoption_status = metrics["adoption_status"]
        
        if adoption_status in ["low", "moderate"]:
            # Determine potential impact
            if feature_name == "ai_descriptions":
                potential_impact = "high"
                reason = "AI descriptions can significantly reduce content creation time"
            elif feature_name == "orders":
                potential_impact = "high"
                reason = "Order processing is core to e-commerce functionality"
            elif feature_name == "products":
                potential_impact = "medium"
                reason = "Product management is essential for catalog operations"
            else:
                potential_impact = "medium"
                reason = "Feature utilization affects overall platform value"
            
            underutilized.append({
                "feature": feature_name,
                "adoption_rate": adoption_rate,
                "usage_frequency": usage_frequency,
                "potential_impact": potential_impact,
                "reason": reason,
                "improvement_opportunity": calculate_improvement_opportunity(adoption_rate, feature_name)
            })
    
    # Sort by potential impact and improvement opportunity
    underutilized.sort(key=lambda x: (
        {"high": 3, "medium": 2, "low": 1}[x["potential_impact"]],
        x["improvement_opportunity"]
    ), reverse=True)
    
    return underutilized


def calculate_improvement_opportunity(adoption_rate: float, feature_name: str) -> float:
    """Calculate the improvement opportunity score"""
    
    # Base opportunity is inverse of adoption rate
    base_opportunity = 1.0 - adoption_rate
    
    # Weight by feature importance
    feature_weights = {
        "ai_descriptions": 1.5,  # High value feature
        "orders": 1.3,
        "products": 1.2,
        "users": 1.0
    }
    
    weight = feature_weights.get(feature_name, 1.0)
    
    return round(base_opportunity * weight, 3)


def generate_adoption_recommendations(adoption_metrics: Dict[str, Any], underutilized: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Generate actionable recommendations for feature adoption"""
    
    recommendations = []
    
    if "error" in adoption_metrics:
        return [{"type": "error", "message": "Unable to generate recommendations due to data error"}]
    
    # Recommendations for underutilized features
    for feature in underutilized[:3]:  # Top 3 underutilized features
        feature_name = feature["feature"]
        
        if feature_name == "ai_descriptions":
            recommendations.append({
                "type": "feature_adoption",
                "title": "Increase AI Description Usage",
                "description": f"Only {feature['adoption_rate']:.1%} adoption rate. AI descriptions can save 2-3 hours per week on content creation.",
                "action_steps": [
                    "Provide team training on AI description generator",
                    "Create templates for effective AI prompts",
                    "Set up workflow to use AI for all new products"
                ],
                "estimated_impact": "2-3 hours saved per week",
                "priority": "high"
            })
            
        elif feature_name == "orders":
            recommendations.append({
                "type": "feature_adoption",
                "title": "Optimize Order Processing",
                "description": f"Order feature has {feature['adoption_rate']:.1%} adoption. Improving order workflows can increase sales efficiency.",
                "action_steps": [
                    "Review order creation process for usability",
                    "Implement order templates for common products",
                    "Add bulk order processing capabilities"
                ],
                "estimated_impact": "15-20% improvement in order processing speed",
                "priority": "high"
            })
            
        elif feature_name == "products":
            recommendations.append({
                "type": "feature_adoption",
                "title": "Enhance Product Management",
                "description": f"Product management shows {feature['adoption_rate']:.1%} adoption. Better product organization improves catalog efficiency.",
                "action_steps": [
                    "Organize products with categories and tags",
                    "Use bulk import for large product catalogs",
                    "Implement product templates for consistency"
                ],
                "estimated_impact": "10-15% faster catalog management",
                "priority": "medium"
            })
    
    # Overall adoption recommendations
    total_features = len(adoption_metrics)
    well_adopted = sum(1 for metrics in adoption_metrics.values() if metrics.get("adoption_status") in ["good", "excellent"])
    
    if well_adopted / total_features < 0.5:
        recommendations.append({
            "type": "general",
            "title": "Improve Overall Feature Adoption",
            "description": f"Only {well_adopted}/{total_features} features are well-adopted. Consider comprehensive user training.",
            "action_steps": [
                "Conduct user training sessions",
                "Create feature adoption dashboard",
                "Implement guided onboarding for new features"
            ],
            "estimated_impact": "20-30% increase in platform utilization",
            "priority": "medium"
        })
    
    return recommendations