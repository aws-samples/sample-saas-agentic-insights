import json
import boto3
import os
import time
from decimal import Decimal
from botocore.exceptions import ClientError

def decimal_default(obj):
    """Convert Decimal objects to float for JSON serialization"""
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError

def handler(event, context):
    """Insight Dashboard API - Handles various dashboard insights"""
    
    # CORS headers
    cors_headers = {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization'
    }
    
    try:
        if event['httpMethod'] == 'OPTIONS':
            return {'statusCode': 200, 'headers': cors_headers, 'body': ''}
        
        # Parse request body
        body = json.loads(event['body']) if event.get('body') else {}
        analysis_type = body.get('analysis_type', 'default')
        
        # Handle simple-cost-analysis type with Cost Analysis Agent
        if analysis_type == 'simple-cost-analysis':
            bedrock_agent_runtime = boto3.client('bedrock-agent-runtime')
            
            # Get cost analysis agent IDs from environment variables
            cost_analysis_agent_id = os.environ.get('COST_ANALYSIS_AGENT_ID')
            cost_analysis_agent_alias_id = os.environ.get('COST_ANALYSIS_AGENT_ALIAS_ID')
            
            if not cost_analysis_agent_id or not cost_analysis_agent_alias_id:
                return {
                    'statusCode': 500,
                    'headers': cors_headers,
                    'body': json.dumps({'error': 'Cost analysis agent not configured'})
                }
            
            return_format = """
            {
                "trends": [
                    {trend 1}, {trend 2}, ...
                ],
                "predictions": [
                    {prediction 1}, {prediction 2}, ...
                ],
                "recommendations": [
                    {recommendation 1}, {recommendation 2}, ...
                ],
                "cost_per_tenant_averages": [
                    {"month": "YYYY-MM", "tier": "basic | premium", "cost": xx.x, "revenue": xx.x, "margin": xx.x},
                    ...include all the cost_per_tenant_averages data you retrieved...
                ],
                "cost_per_tenant_predictions": [
                    {"month": "YYYY-MM", "tier": "basic | premium", "predicted_cost": xx.x, "confidence_low": xx.x, "confidence_high": xx.x, "revenue": xx.x, "predicted_margin": xx.x},
                    ...include all the cost_per_tenant_predictions data you retrieved...
                ]
                
            } """

            prompt = f"""
            Analyze the "average cost per-tenant, per-month dataset" and provide:
            
            1. TREND ANALYSIS: Examine “average cost and margin per-tenant, per-month dataset” over the last 6 months for both Basic and Premium tiers and Identify most important 5 cost per-tenant and margin trends, variations and important deep insights. 
            
            2. PREDICTIVE ANALYSIS: Examine “predicted cost and margin per-tenant, per-month dataset” over next 6 months and Forecast most important 5 trends, patterns, tier-specific growth and deep insights. 
            
            3. RECOMMENDATIONS: Refer to the TREND ANALYSIS, PREDICTIVE ANALYSIS and the cost per-tenant averages and cost per-tenant predictions DATASETS, and then identify most critical and important 5 actionable cost/infrastructure optimization action items for the SaaS provider to improve the revenue/margin. Do NOT just provide generic output such as "Explore further cost reduction opportunities in the basic tier, potentially through automation or process improvements." or "Continue to focus on operational efficiency in the premium tier to drive down costs and improve margins." etc. Dive deeper, be specific and use data-driven analysis to provide recommendations. I need to see dollar values, % values, numbers in these recommendations to convince the SaaS provider. 

            In all above section, each item must be filled with numerical values, numbers, dollar values to justify, and each item MUST NOT exceed more than 100 characters in size including space. 
            
            STRICTLY use this return JSON format : {return_format}  
            """
            
            try:
                print(f"Invoking cost analysis agent: {cost_analysis_agent_id}")
                response = bedrock_agent_runtime.invoke_agent(
                    agentId=cost_analysis_agent_id,
                    agentAliasId=cost_analysis_agent_alias_id,
                    sessionId=f"cost-analysis-session-{context.aws_request_id}",
                    inputText=prompt
                )
                
                # Process streaming response
                result_text = ""
                for event_chunk in response['completion']:
                    if 'chunk' in event_chunk:
                        chunk_data = event_chunk['chunk']
                        if 'bytes' in chunk_data:
                            decoded_text = chunk_data['bytes'].decode('utf-8')
                            result_text += decoded_text
                
                response_body = {
                    'success': True,
                    'analysis': result_text,
                    'analysis_type': analysis_type,
                    'timestamp': context.aws_request_id,
                    'agent': 'cost-analysis-agent'
                }
                
                return {
                    'statusCode': 200,
                    'headers': cors_headers,
                    'body': json.dumps(response_body)
                }
                
            except Exception as e:
                print(f"Cost Analysis Agent error: {str(e)}")
                return {
                    'statusCode': 500,
                    'headers': cors_headers,
                    'body': json.dumps({'error': f'Cost Analysis Agent invocation failed: {str(e)}'})
                }
        
        # Default response for other types
        return {
            'statusCode': 200,
            'headers': cors_headers,
            'body': json.dumps({
                'message': f'Analysis type {analysis_type} not implemented yet'
            })
        }
        
    except Exception as e:
        print(f"Insight Dashboard API error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'error': 'Internal server error'})
        }
