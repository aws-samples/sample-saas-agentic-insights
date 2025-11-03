import boto3
import os
from datetime import datetime, timedelta
from boto3.dynamodb.conditions import Key
from typing import Dict, Any, List
import statistics


def analyze_performance_metrics(tenant_id: str, metrics_type: List[str] = None) -> Dict[str, Any]:
    """
    Analyzes performance metrics and identifies optimization opportunities
    
    Args:
        tenant_id: Target tenant ID
        metrics_type: Types of metrics to analyze
    
    Returns:
        Performance analysis with optimization recommendations
    """
    
    if not metrics_type:
        metrics_type = ["response_time", "error_rate", "throughput", "efficiency"]
    
    # Query performance-related metrics
    performance_data = query_performance_data(tenant_id, metrics_type)
    
    # Analyze trends and patterns
    performance_analysis = analyze_performance_trends(performance_data)
    
    # Identify optimization opportunities
    optimizations = identify_performance_optimizations(performance_analysis)
    
    return {
        "tenant_id": tenant_id,
        "metrics_analyzed": metrics_type,
        "performance_summary": performance_analysis,
        "optimization_opportunities": optimizations,
        "recommendations": generate_performance_recommendations(optimizations)
    }


def query_performance_data(tenant_id: str, metrics_type: List[str]) -> Dict[str, Any]:
    """Query performance-related metrics from DynamoDB"""
    
    dynamodb = boto3.resource('dynamodb')
    metrics_table = dynamodb.Table(os.environ.get('METRICS_AGGREGATION_TABLE_NAME', 'MetricsAggregation'))
    
    # Get current month and previous month for trend analysis
    current_date = datetime.now()
    current_month = current_date.strftime('%Y-%m')
    previous_month = (current_date - timedelta(days=30)).strftime('%Y-%m')
    
    performance_data = {
        "current_month": {},
        "previous_month": {},
        "raw_metrics": []
    }
    
    try:
        # Query current month
        current_response = metrics_table.query(
            IndexName='MonthIndex',
            KeyConditionExpression=Key('month').eq(current_month),
            FilterExpression=Key('tenant_id').eq(tenant_id)
        )
        
        # Query previous month for comparison
        previous_response = metrics_table.query(
            IndexName='MonthIndex',
            KeyConditionExpression=Key('month').eq(current_month),
            FilterExpression=Key('tenant_id').eq(tenant_id)
        )
        
        performance_data["current_month"] = process_performance_metrics(current_response['Items'])
        performance_data["previous_month"] = process_performance_metrics(previous_response['Items'])
        performance_data["raw_metrics"] = current_response['Items']
        
        return performance_data
        
    except Exception as e:
        return {"error": f"Failed to query performance data: {str(e)}"}


def process_performance_metrics(metrics_items: List[Dict]) -> Dict[str, Any]:
    """Process raw metrics into performance indicators"""
    
    # Initialize performance counters
    api_requests = 0
    lambda_executions = 0
    dynamodb_operations = 0
    total_cost = 0.0
    
    # Performance indicators (simulated from available data)
    response_times = []
    error_counts = 0
    
    for item in metrics_items:
        metric_name = item['metric_name']
        total_count = float(item['total_count'])
        estimated_cost = float(item['estimated_cost'])
        
        # Count operations by type
        if 'api_gateway' in metric_name:
            api_requests += total_count
            # Simulate response times based on request volume
            # In production, you'd have actual response time metrics
            avg_response_time = simulate_response_time(total_count)
            response_times.extend([avg_response_time] * int(total_count))
            
        elif 'lambda' in metric_name:
            lambda_executions += total_count
            
        elif 'dynamodb' in metric_name:
            dynamodb_operations += total_count
        
        total_cost += estimated_cost
        
        # Simulate error detection (in production, you'd have actual error metrics)
        if total_count > 1000:  # High volume operations might have more errors
            error_counts += int(total_count * 0.01)  # 1% error rate simulation
    
    # Calculate performance metrics
    avg_response_time = statistics.mean(response_times) if response_times else 0
    p95_response_time = statistics.quantiles(response_times, n=20)[18] if len(response_times) > 20 else avg_response_time * 1.5
    error_rate = error_counts / max(api_requests, 1)
    throughput = api_requests / 30  # Requests per day (assuming monthly data)
    
    return {
        "api_requests": int(api_requests),
        "lambda_executions": int(lambda_executions),
        "dynamodb_operations": int(dynamodb_operations),
        "total_cost": round(total_cost, 4),
        "avg_response_time": round(avg_response_time, 2),
        "p95_response_time": round(p95_response_time, 2),
        "error_rate": round(error_rate, 4),
        "error_count": int(error_counts),
        "throughput": round(throughput, 2)
    }


def simulate_response_time(request_count: float) -> float:
    """Simulate response time based on request volume (for demo purposes)"""
    
    # Base response time increases with load
    base_time = 200  # 200ms base
    load_factor = min(request_count / 1000, 2.0)  # Max 2x increase
    
    return base_time + (load_factor * 100)


def analyze_performance_trends(performance_data: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze performance trends between current and previous periods"""
    
    if "error" in performance_data:
        return performance_data
    
    current = performance_data["current_month"]
    previous = performance_data["previous_month"]
    
    # Calculate trends
    trends = {}
    
    for metric in ["avg_response_time", "error_rate", "throughput", "total_cost"]:
        current_value = current.get(metric, 0)
        previous_value = previous.get(metric, 0)
        
        if previous_value > 0:
            change_percent = ((current_value - previous_value) / previous_value) * 100
        else:
            change_percent = 0
        
        # Determine trend direction
        if abs(change_percent) < 5:
            trend = "stable"
        elif change_percent > 0:
            trend = "increasing"
        else:
            trend = "decreasing"
        
        trends[metric] = {
            "current": current_value,
            "previous": previous_value,
            "change_percent": round(change_percent, 2),
            "trend": trend
        }
    
    # Overall performance assessment
    performance_score = calculate_performance_score(current)
    
    return {
        "current_metrics": current,
        "trends": trends,
        "performance_score": performance_score,
        "assessment": get_performance_assessment(performance_score)
    }


def calculate_performance_score(metrics: Dict[str, Any]) -> float:
    """Calculate overall performance score (0-100)"""
    
    score = 100
    
    # Response time impact (0-30 points)
    avg_response_time = metrics.get("avg_response_time", 0)
    if avg_response_time > 1000:  # > 1 second
        score -= 30
    elif avg_response_time > 500:  # > 500ms
        score -= 20
    elif avg_response_time > 300:  # > 300ms
        score -= 10
    
    # Error rate impact (0-40 points)
    error_rate = metrics.get("error_rate", 0)
    if error_rate > 0.05:  # > 5%
        score -= 40
    elif error_rate > 0.02:  # > 2%
        score -= 25
    elif error_rate > 0.01:  # > 1%
        score -= 15
    
    # Throughput efficiency (0-20 points)
    throughput = metrics.get("throughput", 0)
    api_requests = metrics.get("api_requests", 0)
    if api_requests > 0 and throughput < api_requests * 0.5:  # Low efficiency
        score -= 20
    elif api_requests > 0 and throughput < api_requests * 0.7:
        score -= 10
    
    # Cost efficiency (0-10 points)
    total_cost = metrics.get("total_cost", 0)
    if total_cost > 100:  # High cost
        score -= 10
    elif total_cost > 50:
        score -= 5
    
    return max(0, score)


def get_performance_assessment(score: float) -> str:
    """Get performance assessment based on score"""
    
    if score >= 90:
        return "excellent"
    elif score >= 75:
        return "good"
    elif score >= 60:
        return "fair"
    elif score >= 40:
        return "poor"
    else:
        return "critical"


def identify_performance_optimizations(performance_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Identify specific performance optimization opportunities"""
    
    if "error" in performance_analysis:
        return []
    
    optimizations = []
    current_metrics = performance_analysis["current_metrics"]
    trends = performance_analysis["trends"]
    
    # Response time optimizations
    avg_response_time = current_metrics.get("avg_response_time", 0)
    if avg_response_time > 500:
        optimizations.append({
            "type": "response_time",
            "severity": "high" if avg_response_time > 1000 else "medium",
            "issue": f"Average response time is {avg_response_time}ms",
            "impact": "User experience degradation",
            "potential_improvement": "30-50% faster response times"
        })
    
    # Error rate optimizations
    error_rate = current_metrics.get("error_rate", 0)
    if error_rate > 0.01:  # > 1%
        optimizations.append({
            "type": "error_rate",
            "severity": "high" if error_rate > 0.05 else "medium",
            "issue": f"Error rate is {error_rate:.2%}",
            "impact": "Failed operations and poor user experience",
            "potential_improvement": "Reduce errors by 50-80%"
        })
    
    # Throughput optimizations
    throughput = current_metrics.get("throughput", 0)
    api_requests = current_metrics.get("api_requests", 0)
    if api_requests > 100 and throughput < api_requests * 0.6:
        optimizations.append({
            "type": "throughput",
            "severity": "medium",
            "issue": f"Low throughput efficiency: {throughput:.1f} requests/day",
            "impact": "Underutilized system capacity",
            "potential_improvement": "20-40% increase in throughput"
        })
    
    # Cost optimizations
    total_cost = current_metrics.get("total_cost", 0)
    if total_cost > 50:
        cost_trend = trends.get("total_cost", {}).get("trend", "stable")
        if cost_trend == "increasing":
            optimizations.append({
                "type": "cost",
                "severity": "medium",
                "issue": f"Rising costs: ${total_cost:.2f} with {cost_trend} trend",
                "impact": "Increased operational expenses",
                "potential_improvement": "10-25% cost reduction"
            })
    
    # Trend-based optimizations
    for metric, trend_data in trends.items():
        if trend_data["trend"] == "increasing" and metric in ["avg_response_time", "error_rate"]:
            optimizations.append({
                "type": "trend",
                "severity": "medium",
                "issue": f"{metric.replace('_', ' ').title()} trending upward ({trend_data['change_percent']:+.1f}%)",
                "impact": "Performance degradation over time",
                "potential_improvement": "Stabilize and reverse negative trends"
            })
    
    return optimizations


def generate_performance_recommendations(optimizations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Generate actionable performance recommendations"""
    
    recommendations = []
    
    # Group optimizations by type
    optimization_types = {}
    for opt in optimizations:
        opt_type = opt["type"]
        if opt_type not in optimization_types:
            optimization_types[opt_type] = []
        optimization_types[opt_type].append(opt)
    
    # Generate recommendations for each type
    for opt_type, opts in optimization_types.items():
        if opt_type == "response_time":
            recommendations.append({
                "type": "performance",
                "title": "Optimize Response Times",
                "description": f"Response times are above optimal thresholds. {len(opts)} issues identified.",
                "action_steps": [
                    "Review and optimize database queries",
                    "Implement caching for frequently accessed data",
                    "Consider increasing Lambda memory allocation",
                    "Optimize API Gateway configuration"
                ],
                "estimated_impact": "30-50% improvement in response times",
                "priority": "high" if any(opt["severity"] == "high" for opt in opts) else "medium"
            })
            
        elif opt_type == "error_rate":
            recommendations.append({
                "type": "reliability",
                "title": "Reduce Error Rates",
                "description": f"Error rates are above acceptable levels. {len(opts)} issues identified.",
                "action_steps": [
                    "Implement comprehensive error handling",
                    "Add input validation and sanitization",
                    "Set up monitoring and alerting",
                    "Review and fix common error patterns"
                ],
                "estimated_impact": "50-80% reduction in error rates",
                "priority": "high"
            })
            
        elif opt_type == "throughput":
            recommendations.append({
                "type": "efficiency",
                "title": "Improve System Throughput",
                "description": f"System throughput can be optimized. {len(opts)} opportunities identified.",
                "action_steps": [
                    "Optimize Lambda concurrency settings",
                    "Implement connection pooling",
                    "Review DynamoDB capacity settings",
                    "Consider batch processing for bulk operations"
                ],
                "estimated_impact": "20-40% increase in throughput",
                "priority": "medium"
            })
            
        elif opt_type == "cost":
            recommendations.append({
                "type": "cost_optimization",
                "title": "Optimize Infrastructure Costs",
                "description": f"Cost optimization opportunities identified. {len(opts)} areas for improvement.",
                "action_steps": [
                    "Right-size Lambda memory and timeout settings",
                    "Optimize DynamoDB read/write capacity",
                    "Implement efficient caching strategies",
                    "Review and eliminate unused resources"
                ],
                "estimated_impact": "10-25% cost reduction",
                "priority": "medium"
            })
    
    # Add general performance recommendation if multiple issues exist
    if len(optimizations) > 3:
        recommendations.append({
            "type": "general",
            "title": "Comprehensive Performance Review",
            "description": f"Multiple performance issues detected ({len(optimizations)} total). Consider a comprehensive review.",
            "action_steps": [
                "Conduct performance audit",
                "Implement performance monitoring dashboard",
                "Set up automated performance alerts",
                "Create performance optimization roadmap"
            ],
            "estimated_impact": "Overall system performance improvement",
            "priority": "high"
        })
    
    return recommendations