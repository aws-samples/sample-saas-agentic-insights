import json
import boto3
import os
import time
from botocore.exceptions import ClientError

def handler(event, context):
    """Cost Analysis API - Interface with Bedrock Agent"""
    
    # CORS headers
    cors_headers = {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization, tenant-id, tier-name'
    }
    
    try:
        if event['httpMethod'] == 'OPTIONS':
            return {'statusCode': 200, 'headers': cors_headers, 'body': ''}
        
        # Platform-wide cost analysis for SaaS admin
        # No tenant context needed - analyze across all tenants
        
        # Parse request body for POST, use default for GET
        if event['httpMethod'] == 'POST':
            body = json.loads(event['body']) if event.get('body') else {}
            analysis_type = body.get('analysis_type', 'overview')
        else:
            # GET method - default to predictions for dashboard
            analysis_type = 'predictions'
        
        # Invoke Bedrock Agent
        bedrock_agent_runtime = boto3.client('bedrock-agent-runtime')
        
        # Create platform-wide prompts for SaaS admin analysis
        if analysis_type == 'overview':
            prompt = "Analyze infrastructure usage and costs across all tenants for the last 30 days. Provide platform totals and service breakdown."
        elif analysis_type == 'tenant_analysis':
            prompt = "Analyze cost per tenant including profitability across all tiers. Compare with tier pricing and identify optimization opportunities."
        elif analysis_type == 'predictions':
            prompt = "Predict platform costs for the next 3 months based on current usage patterns across all tenants. Include growth projections and cost optimization recommendations."
        elif analysis_type == 'dashboard_complete':
            prompt = """Provide a comprehensive cost analysis for the Cost analysis admin dashboard. Follow this EXACT format: 

1. === METRICS OVERVIEW === 
For the current month,  
Total Platform Cost: $X.XXXXX
Average Cost Per Tenant (Basic): $X.XXXXX  
Average Cost Per Tenant (Premium): $X.XXXXX  
Platform Margin: X.XXXXX%
Total AI Usage: X tokens (input + output)

2. === SERVICE BREAKDOWN ===
For the current month,  
Lambda Cost: $X.XXXXX
DynamoDB Cost: $X.XXXXX
API Gateway Cost: $X.XXXXX
Bedrock AI Cost: $X.XXXXX
Any other AWS service cost available : $X.XXXXX

3. === TENANT ANALYSIS ===
for the current month,  
[For each tenant: TenantID | Tier | Cost | Revenue | Margin | Margin %]

4. === COST FORECAST ===
Based on the average cost per tenant values during last 2 months and current month, Predict and forecast the cost per tenant for the next 3 months. Use cost-prediction action group. Include last 2 months, current month and next 3 month. Format as follows. Use numbering for denoting Months, 0 is current month : -2, -1, 0, 1, 2, 3
[Month | average cost per tenant ]

5. === REVENUE FORECAST ===
Based on the Revenue and Margin during last 2 months and current month, Predict and forecast the Revenue and Margin for the next 3 months. Use cost-prediction action group. Include current month's values too. Format as follows. Use numbering for denoting Months, 0 is current month : -2, -1, 0, 1, 2, 3
[Month | Cost | Revenue | Margin ]

6. === AI RECOMMENDATIONS ===
Looking at the historical values and above metrics, Provide TOP 5 actionable cost optimization and forecasting recommendations for the SaaS provider with specific impact estimates.MUST use given groups to get real data. Base ALL recommendations on the ACTUAL data and costs provided, not generic advices.

Format the response as a structured analysis that can be parsed for dashboard display. Focus on actionable insights and specific dollar amounts where possible."""
        else:
            prompt = "Provide comprehensive platform-wide cost analysis across all tenants and services"
        
        # Invoke agent with retry logic for throttling
        max_retries = 3
        retry_delay = 2
        result_text = ""
        
        print(f"Starting Bedrock Agent invocation with {max_retries} max retries")
        
        for attempt in range(max_retries):
            try:
                print(f"Attempt {attempt + 1} of {max_retries}")
                response = bedrock_agent_runtime.invoke_agent(
                    agentId=os.environ['BEDROCK_AGENT_ID'],
                    agentAliasId=os.environ['BEDROCK_AGENT_ALIAS_ID'],
                    sessionId=f"platform-admin-session-{context.aws_request_id}",
                    inputText=prompt
                )
                
                # Process streaming response with retry protection
                result_text = ""
                for event_chunk in response['completion']:
                    if 'chunk' in event_chunk:
                        chunk_data = event_chunk['chunk']
                        if 'bytes' in chunk_data:
                            result_text += chunk_data['bytes'].decode('utf-8')
                
                print(f"Success on attempt {attempt + 1}")
                break
                
            except ClientError as e:
                error_code = e.response['Error']['Code']
                print(f"Attempt {attempt + 1} failed with error: {error_code}")
                
                if error_code == 'ThrottlingException' and attempt < max_retries - 1:
                    print(f"Throttling detected, retrying in {retry_delay} seconds (attempt {attempt + 1})")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                    continue
                else:
                    print(f"Max retries reached or non-throttling error, raising exception")
                    raise e
        
        return {
            'statusCode': 200,
            'headers': cors_headers,
            'body': json.dumps({
                'analysis': result_text,
                'analysis_type': analysis_type,
                'timestamp': context.aws_request_id
            })
        }
        
    except Exception as e:
        print(f"Cost analysis API error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'error': 'Internal server error'})
        }


