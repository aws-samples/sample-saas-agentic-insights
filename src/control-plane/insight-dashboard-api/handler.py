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
            
            prompt = """
            Analyze the cost per-tenant dataset and provide:
            
            1. TREND ANALYSIS: Examine cost and margin trends over the last 6 months for both Basic and Premium tiers. Identify the 5 most important cost per-tenant and margin trends, variations and deep insights.
            
            2. PREDICTIVE ANALYSIS: Examine predicted cost and margin data over next 6 months. Forecast the 5 most important trends, patterns, tier-specific growth and deep insights.
            
 

            Return ONLY a JSON object in this exact format:
            {
                "trends": ["trend 1", "trend 2", "trend 3", "trend 4", "trend 5"],
                "predictions": ["prediction 1", "prediction 2", "prediction 3", "prediction 4", "prediction 5"],
                "recommendations": ["recommendation 1", "recommendation 2", "recommendation 3", "recommendation 4", "recommendation 5"]
            }
            """
            
            try:
                print(f"Invoking cost analysis agent: {cost_analysis_agent_id}")
                
                # Use the correct invoke_agent API
                response = bedrock_agent_runtime.invoke_agent(
                    agentId=cost_analysis_agent_id,
                    agentAliasId=cost_analysis_agent_alias_id,
                    sessionId=f"cost-analysis-session-{int(time.time())}",
                    inputText=prompt
                )
                
                # Process streaming response
                result_text = ""
                for event in response['completion']:
                    if 'chunk' in event:
                        chunk = event['chunk']
                        if 'bytes' in chunk:
                            result_text += chunk['bytes'].decode('utf-8')
                
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
