import json
import boto3
import os
import time
import re
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
        
        # Handle cost-analysis type with Cost Analysis Agent
        if analysis_type == 'cost-analysis':
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
            
            ##====== SECTION 1: TREND ANALYSIS ======
            prompt = """
            Analyze the cost per-tenant dataset and provide the following. Note, Each analysis/recommendation item must be filled with numerical values, numbers, dollar values to justify, and each item MUST NOT exceed more than 150 characters in size including space. 
            
            1. TREND ANALYSIS: Examine cost and margin trends over the last 6 months for both Basic and Premium tiers. Identify the 5 most important cost per-tenant and margin trends, variations and deep insights.
            
        
            "Response JSON": Return ONLY a JSON object in this exact format.
            {
                "trends": ["t1", "t2", "t3", "t4", "t5"],
                "cache_uid": "cache-uid-from-action-group"
            }
            """
            
            # ##====== SECTION 2: PREDICTIVE ANALYSIS ======
            # prompt += """
            # Also provide : 

            # 2. PREDICTIVE ANALYSIS: Examine predicted cost and margin data over next 6 months. Forecast the 5 most important trends, patterns, tier-specific growth and deep insights.

            # Add these items too to the "Response JSON":
            # {
            #     "predictions": ["p1", "p2", "p3", "p4", "p5"]
            # }
            # """
            # ##============= END of SECTION 2 ==============


            # ##====== SECTION 3: ADVANCED INSIGHTS ==========
            # prompt += """
            # Add this flag to the"Response JSON":
            # {
            #     "enable_advanced_insights": true
            # }
            # """
            # ##============= END of SECTION 2 ================


            # ##====== SECTION 4: AI RECOMMENDATIONS ============
            # prompt += """
            # Also provide : 

            # 3. RECOMMENDATIONS: Refer to the TREND ANALYSIS, PREDICTIVE ANALYSIS and the cost per-tenant averages and cost per-tenant predictions DATASETS, and then identify most critical and important 5 actionable cost/infrastructure optimization action items for the SaaS provider to improve the revenue/margin. Do NOT just provide generic output such as "Explore further cost reduction opportunities in the basic tier, potentially through automation or process improvements." or "Continue to focus on operational efficiency in the premium tier to drive down costs and improve margins." etc. Dive deeper, be specific and use data-driven analysis to provide recommendations. I need to see dollar values, % values, numbers in these recommendations to convince the SaaS provider. 

            # Add these items too to the "Response JSON":
            # {
            #     "recommendations": ["rec1", "rec2", "rec3", "rec4", "rec5"]
            # }
            # """
            # ##============= END of SECTION 4 ================


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
                
                # Extract JSON using regex to handle all markdown/special characters
                json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
                if json_match:
                    json_text = json_match.group(0)
                else:
                    json_text = result_text
                
                print(f"DEBUG: Raw agent response: {result_text}")
                print(f"DEBUG: Extracted JSON text: {json_text}")
                
                # Parse JSON response from agent
                try:
                    analysis_json = json.loads(json_text)
                    cache_uid = analysis_json.get('cache_uid')
                    print(f"DEBUG: Parsed JSON successfully, cache_uid: {cache_uid}")
                except json.JSONDecodeError as json_error:
                    print(f"DEBUG: JSON decode error: {str(json_error)}")
                    analysis_json = {"error": "Invalid JSON response", "raw_text": result_text}
                    cache_uid = None
                
                # Fetch cached data if cache_uid is available
                cached_data = {}
                if cache_uid:
                    try:
                        dynamodb = boto3.resource('dynamodb')
                        cache_table = dynamodb.Table('cost-analysis')
                        
                        cache_response = cache_table.get_item(Key={'cache_uid': cache_uid})
                        if 'Item' in cache_response:
                            cached_item = cache_response['Item']
                            cached_data = {
                                'cost_per_tenant_averages': cached_item.get('cost_per_tenant_averages', []),
                                'cost_per_tenant_predictions': cached_item.get('cost_per_tenant_predictions', [])
                            }
                            print(f"Successfully fetched cached data for UID: {cache_uid}")
                        else:
                            print(f"No cached data found for UID: {cache_uid}")
                    except Exception as cache_error:
                        print(f"Error fetching cached data: {str(cache_error)}")
                
                # Combine agent insights with cached data
                final_analysis = {**analysis_json, **cached_data}
                
                response_body = {
                    'success': True,
                    'analysis': final_analysis,
                    'analysis_type': analysis_type,
                    'timestamp': context.aws_request_id,
                    'agent': 'cost-analysis-agent'
                }
                
                return {
                    'statusCode': 200,
                    'headers': cors_headers,
                    'body': json.dumps(response_body, default=decimal_default)
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
