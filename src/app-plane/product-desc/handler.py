import json
import boto3
import os
import time
import re
import logging
from datetime import datetime
from typing import Dict, Any
from decimal import Decimal

# Import metrics collector from Lambda Layer
try:
    from metrics_collector import MetricsCollector
    METRICS_ENABLED = True
except ImportError:
    METRICS_ENABLED = False
    print("Metrics collector not available - running without metrics")

# Configure structured logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Global CORS headers
cors_headers = {
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization, tenant-id, tier-name'
}

# Initialize Bedrock client
bedrock_agent_runtime = boto3.client('bedrock-agent-runtime')

def estimate_tokens(text: str) -> int:
    """
    Estimate token count using multiple methods for accuracy
    Based on OpenAI/Claude tokenization patterns:
    - Average: ~4 characters per token
    - Average: ~0.75 words per token  
    - Punctuation and special chars count as separate tokens
    """
    if not text or not text.strip():
        return 0
    
    # Method 1: Character-based estimation (primary)
    char_count = len(text)
    char_based_tokens = max(1, char_count // 4)
    
    # Method 2: Word-based estimation (secondary)
    words = len(text.split())
    word_based_tokens = max(1, int(words / 0.75))
    
    # Method 3: Account for punctuation and special characters
    punctuation_count = len(re.findall(r'[^\w\s]', text))
    
    # Weighted average with punctuation adjustment
    estimated_tokens = int((char_based_tokens * 0.6 + word_based_tokens * 0.4) + (punctuation_count * 0.3))
    
    return max(1, estimated_tokens)

# Environment variables
BEDROCK_AGENT_ID = os.environ.get('BEDROCK_AGENT_ID')
BEDROCK_AGENT_ALIAS_ID = os.environ.get('BEDROCK_AGENT_ALIAS_ID', 'TSTALIASID')
CLAUDE_INPUT_TOKEN_PRICE = float(os.environ.get('CLAUDE_INPUT_TOKEN_PRICE', '0.000003'))
CLAUDE_OUTPUT_TOKEN_PRICE = float(os.environ.get('CLAUDE_OUTPUT_TOKEN_PRICE', '0.000015'))

def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Handle AI product description generation requests with metrics instrumentation"""
    
    start_time = time.time()
    
    try:
        http_method = event['httpMethod']
        
        # Handle OPTIONS preflight requests
        if http_method == 'OPTIONS':
            return {
                'statusCode': 200,
                'headers': cors_headers,
                'body': ''
            }
        
        # Extract tenant context from authorizer
        request_context = event.get('requestContext', {})
        authorizer_context = request_context.get('authorizer', {})
        tenant_id = authorizer_context.get('tenant_id')
        tier = authorizer_context.get('tier', 'basic')
        user_id = authorizer_context.get('user_id')
        
        # Initialize metrics collector
        metrics = None
        if METRICS_ENABLED and tenant_id and tier:
            metrics = MetricsCollector("ai-description-service", tenant_id, tier)
        
        if not tenant_id:
            logger.error(json.dumps({
                "event": "missing_tenant_context",
                "authorizer_context": authorizer_context
            }))
            return {
                'statusCode': 403,
                'headers': cors_headers,
                'body': json.dumps({'error': 'Missing tenant context', 'status': 'error'})
            }
        
        if http_method == 'POST':
            result = generate_description(event, tenant_id, tier, user_id, context, metrics)
        else:
            result = {
                'statusCode': 405,
                'headers': cors_headers,
                'body': json.dumps({'error': 'Method not allowed', 'status': 'error'})
            }
        
        # Track Lambda execution metrics
        if metrics:
            execution_time = (time.time() - start_time) * 1000
            metrics.track_lambda_execution(
                function_name=context.function_name,
                memory_mb=int(context.memory_limit_in_mb),
                duration_ms=execution_time
            )
        
        return result
            
    except Exception as e:
        logger.error(json.dumps({
            "event": "product_desc_service_error",
            "error": str(e),
            "error_type": type(e).__name__
        }))
        result = {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'error': 'Internal server error', 'status': 'error'})
        }
        # Track error response
        if metrics:
            execution_time = (time.time() - start_time) * 1000
            metrics.track_lambda_execution(
                function_name=context.function_name,
                memory_mb=int(context.memory_limit_in_mb),
                duration_ms=execution_time
            )
        
        return result
            
    except Exception as e:
        print(f"Product description service error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'error': 'Internal server error', 'status': 'error'})
        }

def generate_description(event: Dict[str, Any], tenant_id: str, tier: str, user_id: str, context: Any, metrics=None) -> Dict[str, Any]:
    """Generate AI product description using Bedrock agent with metrics tracking"""
    try:
        # Parse request body
        body = json.loads(event['body']) if isinstance(event.get('body'), str) else event.get('body', {})
        
        # Validate required fields
        product_name = body.get('product_name', '').strip()
        short_description = body.get('short_description', '').strip()
        
        if not product_name:
            return {
                'statusCode': 400,
                'headers': cors_headers,
                'body': json.dumps({'error': 'Product name is required', 'status': 'error'})
            }
        
        if not short_description:
            return {
                'statusCode': 400,
                'headers': cors_headers,
                'body': json.dumps({'error': 'Short description is required', 'status': 'error'})
            }
        
        # Validate field lengths
        if len(product_name) > 100:
            return {
                'statusCode': 400,
                'headers': cors_headers,
                'body': json.dumps({'error': 'Product name must be 100 characters or less', 'status': 'error'})
            }
        
        if len(short_description) > 300:
            return {
                'statusCode': 400,
                'headers': cors_headers,
                'body': json.dumps({'error': 'Short description must be 300 characters or less', 'status': 'error'})
            }
        
        # Check if agent is configured
        if not BEDROCK_AGENT_ID:
            return {
                'statusCode': 503,
                'headers': cors_headers,
                'body': json.dumps({'error': 'AI service not configured', 'status': 'error'})
            }
        
        # Call Bedrock agent with fixed orchestration prompt
        start_time = time.time()
        
        try:
            response = bedrock_agent_runtime.invoke_agent(
                agentId=BEDROCK_AGENT_ID,
                agentAliasId=BEDROCK_AGENT_ALIAS_ID,
                sessionId=f"{tenant_id}-{int(time.time())}",
                inputText=f"Generate a product description for: {product_name}. Key features: {short_description}"
            )
            
            # Process streaming response
            generated_description = ""
            
            for event_chunk in response['completion']:
                if 'chunk' in event_chunk:
                    chunk_data = event_chunk['chunk']
                    if 'bytes' in chunk_data:
                        chunk_text = chunk_data['bytes'].decode('utf-8')
                        generated_description += chunk_text
            
            generated_description = generated_description.strip()
            
            if not generated_description:
                return {
                    'statusCode': 500,
                    'headers': cors_headers,
                    'body': json.dumps({'error': 'Failed to generate description', 'status': 'error'})
                }
            
            # Count tokens using estimation function
            input_text = f"Generate a product description for: {product_name}. Key features: {short_description}"
            input_tokens = estimate_tokens(input_text)
            output_tokens = estimate_tokens(generated_description)
            
            # Calculate costs and usage
            response_time = time.time() - start_time
            usage_data = calculate_usage_and_cost(input_tokens, output_tokens, tenant_id, tier, response_time)
            
            # Track Bedrock invocation metrics
            if metrics:
                metrics.track_bedrock_invocation(
                    model_id="global.anthropic.claude-haiku-4-5-20251001-v1:0",
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    user_id=user_id
                )
            
            # Log usage for monitoring
            log_usage(tenant_id, tier, user_id, product_name, usage_data, response_time)
            
            return {
                'statusCode': 200,
                'headers': cors_headers,
                'body': json.dumps({
                    'generated_description': generated_description,
                    'usage': usage_data,
                    'status': 'success'
                })
            }
            
        except Exception as e:
            print(f"Bedrock agent error: {str(e)}")
            return {
                'statusCode': 500,
                'headers': cors_headers,
                'body': json.dumps({'error': 'AI generation failed, please try again', 'status': 'error'})
            }
        
    except json.JSONDecodeError:
        return {
            'statusCode': 400,
            'headers': cors_headers,
            'body': json.dumps({'error': 'Invalid JSON in request body', 'status': 'error'})
        }
    except Exception as e:
        print(f"Generate description error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'error': 'Failed to generate description', 'status': 'error'})
        }

def calculate_usage_and_cost(input_tokens: int, output_tokens: int, tenant_id: str, tier: str, response_time: float) -> Dict[str, Any]:
    """Calculate token usage and costs"""
    try:
        total_tokens = input_tokens + output_tokens
        input_cost = (input_tokens / 1000) * CLAUDE_INPUT_TOKEN_PRICE
        output_cost = (output_tokens / 1000) * CLAUDE_OUTPUT_TOKEN_PRICE
        total_cost = input_cost + output_cost
        
        return {
            'input_tokens': input_tokens,
            'output_tokens': output_tokens,
            'total_tokens': total_tokens,
            'input_cost': round(input_cost, 6),
            'output_cost': round(output_cost, 6),
            'total_cost': round(total_cost, 6),
            'response_time_seconds': round(response_time, 2)
        }
    except Exception as e:
        print(f"Usage calculation error: {str(e)}")
        # Return basic usage data even if calculation fails
        return {
            'input_tokens': input_tokens,
            'output_tokens': output_tokens,
            'total_tokens': input_tokens + output_tokens,
            'input_cost': 0.0,
            'output_cost': 0.0,
            'total_cost': 0.0,
            'response_time_seconds': round(response_time, 2)
        }

def log_usage(tenant_id: str, tier: str, user_id: str, product_name: str, usage_data: Dict[str, Any], response_time: float) -> None:
    """Log structured usage data for monitoring"""
    try:
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'tenant_id': tenant_id,
            'tier': tier,
            'user_id': user_id,
            'product_name': product_name[:50],  # Truncate for logging
            'service': 'ai-product-description',
            'usage': usage_data,
            'response_time_seconds': response_time
        }
        
        print(f"USAGE_LOG: {json.dumps(log_entry)}")
        
    except Exception as e:
        print(f"Usage logging error: {str(e)}")
        # Don't fail the request if logging fails
