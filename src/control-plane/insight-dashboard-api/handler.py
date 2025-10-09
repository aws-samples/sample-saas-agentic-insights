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
        
        # Handle simple-cost-analysis type with test agent
        if analysis_type == 'simple-cost-analysis':
            bedrock_agent_runtime = boto3.client('bedrock-agent-runtime')
            
            # Get test agent IDs from environment variables
            test_agent_id = os.environ.get('TEST_AGENT_ID')
            test_agent_alias_id = os.environ.get('TEST_AGENT_ALIAS_ID')
            
            if not test_agent_id or not test_agent_alias_id:
                return {
                    'statusCode': 500,
                    'headers': cors_headers,
                    'body': json.dumps({'error': 'Test agent not configured'})
                }
            
            return_format = """use JSON format for the response like this: 
            {
                "historical": [
                    {
                        "month": "YYYY-MM",
                        "tier": "basic",
                        ....
                    }
                ],
                "forecast": [
                    {
                        "month": "YYYY-MM",
                        "tier": "basic",
                        ....
                    }
                ]
                
            } """


            prompt = f"""
            Refer to CostPerTenant dataset, analyze it and do the following. 
            
            1. Calculate the average cost per-tenant, per-month basis. 
            2. Based on this dataset per-tier basis, forecast the cost per-tenant, per-month for the next 6 months from current month using Monte Carlo simulation. 
            3. And then, return only these attributes [month | tier | cost | revenue | margin]. Add Basic tier values first and then Premium tier.
            
            Use {return_format} as the return JSON format. 
            """

            # Also, explore the historical cost-per-tenant values, and forecasted values, and provide TOP 5 actionable insights AND TOP 5 Recommendations for the SaaS provider to reduce costs and improve margins. Include specific dollar impact, numbers and data in each insight and recommendation. Each should not more than 300 characters 

            # "recommendations": [
            #         {
            #             "recommendations 01"
            #         },
            #         ....
            #     ]

            
            
            try:
                print(f"Invoking test agent: {test_agent_id}")
                response = bedrock_agent_runtime.invoke_agent(
                    agentId=test_agent_id,
                    agentAliasId=test_agent_alias_id,
                    sessionId=f"test-agent-session-{context.aws_request_id}",
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
                    'agent': 'test-agent'
                }
                
                return {
                    'statusCode': 200,
                    'headers': cors_headers,
                    'body': json.dumps(response_body)
                }
                
            except Exception as e:
                print(f"Test agent error: {str(e)}")
                return {
                    'statusCode': 500,
                    'headers': cors_headers,
                    'body': json.dumps({'error': f'Test agent invocation failed: {str(e)}'})
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
