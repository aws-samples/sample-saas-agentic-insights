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
        
        # Handle cost-analysis type with working cost analysis agent
        if analysis_type == 'cost-analysis':
            # Use the working cost analysis agent instead of advanced agent
            bedrock_agent_runtime = boto3.client('bedrock-agent-runtime')
            
            # Create prompt for cost analysis
            prompt = """Refer to the "historical dataset" from CostPerTenant table and Provide following data for the Cost analysis admin dashboard. Follow this EXACT format: 
            1. === COST ANALYSIS ===
            Summarize the given "historical dataset" and calculate the "average cost per tenant" dataset per month basis on following format
            [month | tier | avg_cost | profit | margin | margin_percentage]

            2. === COST FORECAST ===
            Use Monte Carlo simulation to forecast the next 6 months dataset ("6 months forecast") on the following format by referring to the above "average cost per tenant" dataset. Must generate the best realistic values: 
            [month | tier | avg_cost | profit | margin | margin_percentage]

            3. === AI SUMMARY ===
            Provide TOP 5 findings looking at the "average cost per tenant" and "6 months forecast" datasets for the tenant behavior, cost margin variations. 

            4. === AI RECOMMENDATIONS ===
            Looking at the  "average cost per tenant" and "6 months forecast", Provide TOP 5 actionable  recommendations for the SaaS provider that helps to reduce cost per tenant and improve overall margin. Focus on actionable insights and specific dollar amounts where possible."""
            
            # Invoke agent with retry logic
            max_retries = 3
            retry_delay = 2
            result_text = ""
            
            print(f"Starting Advanced Cost Analysis Agent invocation with {max_retries} max retries")
            
            for attempt in range(max_retries):
                try:
                    print(f"Attempt {attempt + 1} of {max_retries}")
                    response = bedrock_agent_runtime.invoke_agent(
                        agentId='EIRUIXKAT9',  # Working cost analysis agent
                        agentAliasId='HPYPHQSMIU',  # Working agent alias
                        sessionId=f"cost-analysis-session-{context.aws_request_id}",
                        inputText=prompt
                    )
                    
                    # Process streaming response
                    result_text = ""
                    chunk_count = 0
                    for event_chunk in response['completion']:
                        chunk_count += 1
                        print(f"Processing chunk {chunk_count}: {event_chunk.keys()}")
                        if 'chunk' in event_chunk:
                            chunk_data = event_chunk['chunk']
                            print(f"Chunk data keys: {chunk_data.keys()}")
                            if 'bytes' in chunk_data:
                                decoded_text = chunk_data['bytes'].decode('utf-8')
                                print(f"Decoded text length: {len(decoded_text)}")
                                result_text += decoded_text
                    
                    print(f"Total result text length: {len(result_text)}")
                    print(f"Success on attempt {attempt + 1}")
                    break
                    
                except ClientError as e:
                    error_code = e.response['Error']['Code']
                    print(f"Attempt {attempt + 1} failed with error: {error_code}")
                    
                    if error_code == 'ThrottlingException' and attempt < max_retries - 1:
                        print(f"Throttling detected, retrying in {retry_delay} seconds")
                        time.sleep(retry_delay)
                        retry_delay *= 2
                        continue
                    else:
                        print(f"Max retries reached or non-throttling error, raising exception")
                        raise e
            
            response_body = {
                'success': True,
                'analysis': result_text,
                'analysis_type': analysis_type,
                'timestamp': context.aws_request_id,
                'agent': 'cost-analysis'  # Working agent
            }
            print(f"Final response body: {json.dumps(response_body)}")
            
            return {
                'statusCode': 200,
                'headers': cors_headers,
                'body': json.dumps(response_body)
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
