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
        
        # Extract tenant context from authorizer
        request_context = event.get('requestContext', {})
        authorizer_context = request_context.get('authorizer', {})
        tenant_id = authorizer_context.get('tenant_id')
        
        if not tenant_id:
            return {
                'statusCode': 403,
                'headers': cors_headers,
                'body': json.dumps({'error': 'Missing tenant context'})
            }
        
        # Parse request body
        body = json.loads(event['body']) if event.get('body') else {}
        analysis_type = body.get('analysis_type', 'overview')
        
        # Invoke Bedrock Agent
        bedrock_agent = boto3.client('bedrock-agent-runtime')
        
        # Create prompt based on analysis type
        if analysis_type == 'overview':
            prompt = f"Analyze infrastructure usage and costs for tenant {tenant_id} for the last 30 days. Provide platform totals and service breakdown."
        elif analysis_type == 'tenant_analysis':
            prompt = f"Analyze cost per tenant including profitability for tenant {tenant_id}. Compare with tier pricing."
        elif analysis_type == 'predictions':
            prompt = f"Predict costs for tenant {tenant_id} for the next 3 months based on current usage patterns."
        else:
            prompt = f"Provide comprehensive cost analysis for tenant {tenant_id}"
        
        # Invoke agent
        response = bedrock_agent.invoke_agent(
            agentId=os.environ['BEDROCK_AGENT_ID'],
            agentAliasId=os.environ['BEDROCK_AGENT_ALIAS_ID'],
            sessionId=f"session-{tenant_id}",
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
                'tenant_id': tenant_id,
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
