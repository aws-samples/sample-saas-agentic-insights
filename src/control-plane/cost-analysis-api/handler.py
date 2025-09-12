import json
import boto3
import os

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
        bedrock_agent = boto3.client('bedrock-agent-runtime')
        
        # Create platform-wide prompts for SaaS admin analysis
        if analysis_type == 'overview':
            prompt = "Analyze infrastructure usage and costs across all tenants for the last 30 days. Provide platform totals and service breakdown."
        elif analysis_type == 'tenant_analysis':
            prompt = "Analyze cost per tenant including profitability across all tiers. Compare with tier pricing and identify optimization opportunities."
        elif analysis_type == 'predictions':
            prompt = "Predict platform costs for the next 3 months based on current usage patterns across all tenants. Include growth projections and cost optimization recommendations."
        else:
            prompt = "Provide comprehensive platform-wide cost analysis across all tenants and services"
        
        # Invoke agent with platform session
        response = bedrock_agent.invoke_agent(
            agentId=os.environ['BEDROCK_AGENT_ID'],
            agentAliasId=os.environ['BEDROCK_AGENT_ALIAS_ID'],
            sessionId=f"platform-admin-session",
            inputText=prompt
        )
        
        # Process streaming response
        result_text = ""
        for event_chunk in response['completion']:
            if 'chunk' in event_chunk:
                chunk_data = event_chunk['chunk']
                if 'bytes' in chunk_data:
                    result_text += chunk_data['bytes'].decode('utf-8')
        
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
