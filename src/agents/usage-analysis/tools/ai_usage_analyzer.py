import boto3
import os
from datetime import datetime, timedelta
from boto3.dynamodb.conditions import Key
from typing import Dict, Any, List


def analyze_ai_usage(tenant_id: str, include_cost_analysis: bool = True) -> Dict[str, Any]:
    """
    Analyzes AI feature usage patterns and cost optimization
    
    Args:
        tenant_id: Target tenant ID
        include_cost_analysis: Include cost optimization recommendations
    
    Returns:
        AI usage analysis with cost optimization insights
    """
    
    # Query AI-specific metrics (Bedrock invocations)
    ai_metrics = query_ai_usage_data(tenant_id)
    
    # Calculate usage patterns and costs
    usage_analysis = calculate_ai_usage_patterns(ai_metrics)
    
    # Cost optimization analysis
    cost_optimizations = []
    if include_cost_analysis:
        cost_optimizations = identify_ai_cost_optimizations(usage_analysis)
    
    return {
        "tenant_id": tenant_id,
        "ai_usage_summary": usage_analysis,
        "cost_analysis": cost_optimizations,
        "recommendations": generate_ai_recommendations(usage_analysis, cost_optimizations)
    }


def query_ai_usage_data(tenant_id: str) -> Dict[str, Any]:
    """Query AI-specific metrics from DynamoDB"""
    
    dynamodb = boto3.resource('dynamodb')
    metrics_table = dynamodb.Table(os.environ.get('METRICS_AGGREGATION_TABLE_NAME', 'MetricsAggregation'))
    
    # Get current month and previous month for trend analysis
    current_date = datetime.now()
    current_month = current_date.strftime('%Y-%m')
    previous_month = (current_date - timedelta(days=30)).strftime('%Y-%m')
    
    ai_data = {
        "current_month": [],
        "previous_month": [],
        "total_ai_requests": 0,
        "total_cost": 0.0
    }
    
    try:
        # Query current month AI metrics
        current_response = metrics_table.query(
            IndexName='MonthIndex',
            KeyConditionExpression=Key('month').eq(current_month),
            FilterExpression=Key('tenant_id').eq(tenant_id)
        )
        
        # Query previous month for comparison
        previous_response = metrics_table.query(
            IndexName='MonthIndex',
            KeyConditionExpression=Key('month').eq(previous_month),
            FilterExpression=Key('tenant_id').eq(tenant_id)
        )
        
        # Filter for AI/Bedrock metrics
        current_ai_metrics = [item for item in current_response['Items'] 
                             if 'bedrock' in item['metric_name'].lower()]
        previous_ai_metrics = [item for item in previous_response['Items'] 
                              if 'bedrock' in item['metric_name'].lower()]
        
        ai_data["current_month"] = current_ai_metrics
        ai_data["previous_month"] = previous_ai_metrics
        
        # Calculate totals
        for item in current_ai_metrics:
            ai_data["total_ai_requests"] += float(item['total_count'])
            ai_data["total_cost"] += float(item['estimated_cost'])
        
        return ai_data
        
    except Exception as e:
        return {"error": f"Failed to query AI usage data: {str(e)}"}


def calculate_ai_usage_patterns(ai_metrics: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate AI usage patterns and statistics"""
    
    if "error" in ai_metrics:
        return ai_metrics
    
    current_metrics = ai_metrics["current_month"]
    previous_metrics = ai_metrics["previous_month"]
    
    # Initialize counters
    total_requests = 0
    total_input_tokens = 0
    total_output_tokens = 0
    total_cost = 0.0
    
    # Process current month metrics
    for item in current_metrics:
        metric_name = item['metric_name']
        total_count = float(item['total_count'])
        estimated_cost = float(item['estimated_cost'])
        
        if 'bedrock_input_tokens' in metric_name:
            total_input_tokens += total_count
        elif 'bedrock_output_tokens' in metric_name:
            total_output_tokens += total_count
        elif 'bedrock' in metric_name and 'requests' in metric_name:
            total_requests += total_count
        
        total_cost += estimated_cost
    
    # Calculate previous month for comparison
    prev_requests = 0
    prev_cost = 0.0
    for item in previous_metrics:
        if 'bedrock' in item['metric_name']:
            prev_requests += float(item['total_count'])
            prev_cost += float(item['estimated_cost'])
    
    # Calculate usage statistics
    avg_tokens_per_request = (total_input_tokens + total_output_tokens) / max(total_requests, 1)
    avg_cost_per_request = total_cost / max(total_requests, 1)
    
    # Calculate trends
    request_trend = calculate_trend(total_requests, prev_requests)
    cost_trend = calculate_trend(total_cost, prev_cost)
    
    # Determine usage frequency
    daily_requests = total_requests / 30  # Assuming monthly data
    if daily_requests > 10:
        usage_frequency = "high"
    elif daily_requests > 3:
        usage_frequency = "medium"
    elif daily_requests > 0.5:
        usage_frequency = "low"
    else:
        usage_frequency = "minimal"
    
    # Calculate efficiency metrics
    efficiency_score = calculate_ai_efficiency(total_input_tokens, total_output_tokens, total_cost)
    
    return {
        "total_requests": int(total_requests),
        "total_input_tokens": int(total_input_tokens),
        "total_output_tokens": int(total_output_tokens),
        "total_tokens": int(total_input_tokens + total_output_tokens),
        "estimated_cost": round(total_cost, 4),
        "avg_tokens_per_request": round(avg_tokens_per_request, 1),
        "avg_cost_per_request": round(avg_cost_per_request, 4),
        "daily_request_rate": round(daily_requests, 2),
        "usage_frequency": usage_frequency,
        "request_trend": request_trend,
        "cost_trend": cost_trend,
        "efficiency_score": efficiency_score,
        "success_rate": 0.98,  # Simulated - would be calculated from actual error metrics
        "peak_usage_hours": ["10:00-12:00", "14:00-16:00"]  # Simulated
    }


def calculate_trend(current: float, previous: float) -> Dict[str, Any]:
    """Calculate trend between current and previous values"""
    
    if previous > 0:
        change_percent = ((current - previous) / previous) * 100
    else:
        change_percent = 0
    
    if abs(change_percent) < 5:
        direction = "stable"
    elif change_percent > 0:
        direction = "increasing"
    else:
        direction = "decreasing"
    
    return {
        "direction": direction,
        "change_percent": round(change_percent, 2),
        "current": current,
        "previous": previous
    }


def calculate_ai_efficiency(input_tokens: float, output_tokens: float, cost: float) -> Dict[str, Any]:
    """Calculate AI usage efficiency metrics"""
    
    total_tokens = input_tokens + output_tokens
    
    # Token efficiency (output/input ratio)
    token_ratio = output_tokens / max(input_tokens, 1)
    
    # Cost efficiency (tokens per dollar)
    tokens_per_dollar = total_tokens / max(cost, 0.001)
    
    # Overall efficiency score (0-100)
    # Good efficiency: high output/input ratio, reasonable cost per token
    ratio_score = min(100, token_ratio * 50)  # Cap at 100
    cost_score = min(100, tokens_per_dollar / 1000 * 100)  # Normalize cost efficiency
    
    overall_score = (ratio_score + cost_score) / 2
    
    # Efficiency rating
    if overall_score > 80:
        rating = "excellent"
    elif overall_score > 60:
        rating = "good"
    elif overall_score > 40:
        rating = "fair"
    else:
        rating = "poor"
    
    return {
        "token_ratio": round(token_ratio, 2),
        "tokens_per_dollar": round(tokens_per_dollar, 1),
        "efficiency_score": round(overall_score, 1),
        "efficiency_rating": rating
    }


def identify_ai_cost_optimizations(usage_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Identify AI cost optimization opportunities"""
    
    if "error" in usage_analysis:
        return []
    
    optimizations = []
    
    # High cost per request optimization
    avg_cost_per_request = usage_analysis.get("avg_cost_per_request", 0)
    if avg_cost_per_request > 0.01:  # > 1 cent per request
        optimizations.append({
            "type": "cost_per_request",
            "severity": "high" if avg_cost_per_request > 0.05 else "medium",
            "issue": f"High cost per request: ${avg_cost_per_request:.4f}",
            "potential_savings": round(avg_cost_per_request * 0.3, 4),
            "optimization": "prompt_optimization"
        })
    
    # Token efficiency optimization
    efficiency_score = usage_analysis.get("efficiency_score", {}).get("efficiency_score", 0)
    if efficiency_score < 60:
        optimizations.append({
            "type": "token_efficiency",
            "severity": "medium",
            "issue": f"Low token efficiency: {efficiency_score:.1f}/100",
            "potential_savings": "15-25% cost reduction",
            "optimization": "prompt_engineering"
        })
    
    # High token usage optimization
    avg_tokens_per_request = usage_analysis.get("avg_tokens_per_request", 0)
    if avg_tokens_per_request > 500:
        optimizations.append({
            "type": "token_usage",
            "severity": "medium",
            "issue": f"High token usage: {avg_tokens_per_request:.1f} tokens per request",
            "potential_savings": "20-30% token reduction",
            "optimization": "input_optimization"
        })
    
    # Usage pattern optimization
    usage_frequency = usage_analysis.get("usage_frequency", "minimal")
    if usage_frequency == "minimal":
        optimizations.append({
            "type": "usage_frequency",
            "severity": "low",
            "issue": "Underutilized AI features",
            "potential_savings": "Increased productivity value",
            "optimization": "adoption_increase"
        })
    
    # Cost trend optimization
    cost_trend = usage_analysis.get("cost_trend", {})
    if cost_trend.get("direction") == "increasing" and cost_trend.get("change_percent", 0) > 20:
        optimizations.append({
            "type": "cost_trend",
            "severity": "high",
            "issue": f"Rapidly increasing costs: +{cost_trend['change_percent']:.1f}%",
            "potential_savings": "Stabilize cost growth",
            "optimization": "usage_monitoring"
        })
    
    return optimizations


def generate_ai_recommendations(usage_analysis: Dict[str, Any], cost_optimizations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Generate actionable AI usage recommendations"""
    
    recommendations = []
    
    if "error" in usage_analysis:
        return [{"type": "error", "message": "Unable to generate AI recommendations due to data error"}]
    
    # Cost optimization recommendations
    for optimization in cost_optimizations:
        opt_type = optimization["type"]
        
        if opt_type == "cost_per_request":
            recommendations.append({
                "type": "cost_optimization",
                "title": "Optimize AI Request Costs",
                "description": f"Current cost per request is ${optimization['issue'].split(': $')[1]}. Potential savings: ${optimization['potential_savings']:.4f} per request.",
                "action_steps": [
                    "Review and optimize prompt templates",
                    "Reduce unnecessary context in prompts",
                    "Use more specific and concise instructions",
                    "Consider batch processing for similar requests"
                ],
                "estimated_impact": f"Save ${optimization['potential_savings']:.4f} per request",
                "priority": optimization["severity"]
            })
            
        elif opt_type == "token_efficiency":
            recommendations.append({
                "type": "efficiency",
                "title": "Improve Token Efficiency",
                "description": f"Token efficiency score is {usage_analysis['efficiency_score']['efficiency_score']:.1f}/100. Better prompts can reduce costs.",
                "action_steps": [
                    "Create standardized prompt templates",
                    "Train team on effective prompt engineering",
                    "Implement prompt validation and testing",
                    "Monitor token usage patterns"
                ],
                "estimated_impact": "15-25% reduction in AI costs",
                "priority": "medium"
            })
            
        elif opt_type == "usage_frequency":
            recommendations.append({
                "type": "adoption",
                "title": "Increase AI Feature Utilization",
                "description": f"AI usage is {usage_analysis['usage_frequency']}. Increased adoption can improve productivity.",
                "action_steps": [
                    "Provide AI feature training to team",
                    "Create workflows that incorporate AI",
                    "Set up AI usage reminders and prompts",
                    "Share success stories and best practices"
                ],
                "estimated_impact": "2-3 hours saved per week through automation",
                "priority": "medium"
            })
    
    # Usage pattern recommendations
    usage_frequency = usage_analysis.get("usage_frequency", "minimal")
    total_requests = usage_analysis.get("total_requests", 0)
    
    if usage_frequency in ["high", "medium"] and total_requests > 50:
        recommendations.append({
            "type": "workflow",
            "title": "Optimize AI Workflow Integration",
            "description": f"With {total_requests} AI requests this month, consider workflow optimizations.",
            "action_steps": [
                "Create AI-powered content templates",
                "Implement bulk AI processing workflows",
                "Set up automated AI content generation",
                "Integrate AI into existing business processes"
            ],
            "estimated_impact": "30-40% improvement in content creation efficiency",
            "priority": "medium"
        })
    
    # Cost monitoring recommendation
    total_cost = usage_analysis.get("estimated_cost", 0)
    if total_cost > 10:  # Significant AI spending
        recommendations.append({
            "type": "monitoring",
            "title": "Implement AI Cost Monitoring",
            "description": f"Monthly AI costs of ${total_cost:.2f} warrant cost monitoring and budgeting.",
            "action_steps": [
                "Set up AI cost alerts and budgets",
                "Create monthly AI usage reports",
                "Implement cost per feature tracking",
                "Review AI ROI and value metrics"
            ],
            "estimated_impact": "Better cost control and ROI visibility",
            "priority": "low"
        })
    
    # Performance recommendation
    success_rate = usage_analysis.get("success_rate", 1.0)
    if success_rate < 0.95:
        recommendations.append({
            "type": "reliability",
            "title": "Improve AI Request Reliability",
            "description": f"AI success rate is {success_rate:.1%}. Improving reliability reduces waste.",
            "action_steps": [
                "Implement error handling and retry logic",
                "Validate inputs before AI requests",
                "Monitor and fix common failure patterns",
                "Set up AI performance alerts"
            ],
            "estimated_impact": "Reduce failed requests and improve user experience",
            "priority": "high"
        })
    
    return recommendations