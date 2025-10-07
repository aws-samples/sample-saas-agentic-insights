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
            prompt = """Using the Historical Cost Dataset API, please execute the getHistoricalCostDataset action to retrieve the complete dataset from the CostPerTenant table. This dataset contains tenant cost/margin data in format: [tenant_id | month | tier | cost | revenue | margin | margin_percentage].

Once you have retrieved the historical cost dataset using the getHistoricalCostDataset action, provide the following analysis for the Cost analysis admin dashboard in this EXACT format:

            1. === COST ANALYSIS ===
            Summarize the historical cost dataset and calculate the average cost/revenue per month by tier:
            [month | tier | avg_cost | avg_revenue | avg_margin | avg_margin_percentage]

            2. === COST FORECAST ===
            Based on the historical trends, forecast the next 6 months using Monte Carlo simulation:
            [month | tier | forecasted_cost | forecasted_revenue | forecasted_margin | forecasted_margin_percentage]

            3. === AI SUMMARY ===
            Analyze the historical data and forecasts to provide TOP 5 key findings about tenant behavior, cost patterns, and margin variations.

            4. === AI RECOMMENDATIONS ===
            Based on the analysis, provide TOP 5 actionable recommendations for the SaaS provider to reduce costs and improve margins. Include specific dollar impact estimates where possible."""
            
            # Invoke agent with retry logic
            max_retries = 3
            retry_delay = 2
            result_text = ""
            
            print(f"Starting Advanced Cost Analysis Agent invocation with {max_retries} max retries")
            
            for attempt in range(max_retries):
                try:
                    print(f"Attempt {attempt + 1} of {max_retries}")
                    response = bedrock_agent_runtime.invoke_agent(
                        agentId='JSJBYKS3WL',  # Advanced cost analysis agent
                        agentAliasId='E65OALIJPR',  # Advanced agent alias
                        sessionId=f"advanced-cost-analysis-session-{context.aws_request_id}",
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
                'agent': 'advanced-cost-analysis'  # Advanced agent
            }
            print(f"Final response body: {json.dumps(response_body)}")
            
            return {
                'statusCode': 200,
                'headers': cors_headers,
                'body': json.dumps(response_body)
            }
        
        # Handle simple-cost-analysis type with test agent
        elif analysis_type == 'simple-cost-analysis':
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
            
            # Simple prompt for test agent
            prompt = "Please analyze the CostPerTenant dataset and provide your top 5 recommendations for improving our SaaS platform economics."
            
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
