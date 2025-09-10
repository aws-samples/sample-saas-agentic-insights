import json
import boto3
import uuid
import os
import logging
import time
from datetime import datetime
from typing import Dict, Any, List
from decimal import Decimal

# Import metrics collector from Lambda Layer
try:
    from metrics_collector import MetricsCollector
    METRICS_ENABLED = True
except ImportError:
    METRICS_ENABLED = False
    print("Metrics collector not available - running without metrics")

# Configure structured logging - Updated for tier-based routing fix
logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource('dynamodb')
ORDERS_TABLE = os.environ['ORDERS_TABLE']

# Global CORS headers
cors_headers = {
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization'
}

def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Handle order management operations with tier-specific routing"""
    
    start_time = time.time()
    
    logger.info(json.dumps({
        "event": "order_request_started",
        "raw_event": event
    }))
    
    try:
        http_method = event['httpMethod']
        
        logger.info(json.dumps({
            "event": "http_method_extracted",
            "http_method": http_method
        }))
        
        # Handle OPTIONS preflight requests
        if http_method == 'OPTIONS':
            logger.info(json.dumps({
                "event": "options_request_handled"
            }))
            return {
                'statusCode': 200,
                'headers': cors_headers,
                'body': ''
            }
        
        # Extract tenant context from authorizer
        request_context = event.get('requestContext', {})
        authorizer_context = request_context.get('authorizer', {})
        tenant_id = authorizer_context.get('tenant_id')
        tier = authorizer_context.get('tier')
        user_id = authorizer_context.get('user_id')
        
        # Initialize metrics collector
        metrics = None
        if METRICS_ENABLED and tenant_id and tier:
            metrics = MetricsCollector("order-service", tenant_id, tier)
        
        logger.info(json.dumps({
            "event": "tenant_context_extracted",
            "tenant_id": tenant_id,
            "tier": tier,
            "user_id": user_id,
            "full_authorizer_context": authorizer_context
        }))
        
        if not tenant_id:
            logger.error(json.dumps({
                "event": "missing_tenant_context",
                "authorizer_context": authorizer_context
            }))
            return {
                'statusCode': 403,
                'headers': cors_headers,
                'body': json.dumps({'error': 'Missing tenant context'})
            }
        
        # Determine which table to use based on tier
        logger.info(json.dumps({
            "event": "determining_table_name",
            "tenant_id": tenant_id,
            "tier": tier
        }))
        
        table_name = get_order_table_name(tenant_id, tier)
        
        logger.info(json.dumps({
            "event": "table_name_determined",
            "table_name": table_name,
            "tier": tier
        }))
        
        if http_method == 'GET':
            result = list_orders(tenant_id, table_name, metrics)
        elif http_method == 'POST':
            result = create_order(event, tenant_id, user_id, table_name, metrics)
        else:
            logger.warning(json.dumps({
                "event": "method_not_allowed",
                "http_method": http_method
            }))
            result = {
                'statusCode': 405,
                'headers': cors_headers,
                'body': json.dumps({'error': 'Method not allowed'})
            }
        
        # Track successful API request
        if metrics:
            execution_time = (time.time() - start_time) * 1000
            metrics.track_api_request(
                endpoint=event.get('resource', '/orders'),
                method=http_method,
                status_code=result.get('statusCode', 200),
                response_time_ms=execution_time,
                user_id=user_id
            )
            metrics.track_lambda_execution(
                function_name=context.function_name,
                memory_mb=int(context.memory_limit_in_mb),
                duration_ms=execution_time
            )
        
        return result
            
    except ValueError as e:
        logger.error(json.dumps({
            "event": "validation_error",
            "error": str(e),
            "error_type": "ValueError"
        }))
        result = {
            'statusCode': 400,
            'headers': cors_headers,
            'body': json.dumps({'error': str(e)})
        }
        # Track error response
        if metrics:
            execution_time = (time.time() - start_time) * 1000
            metrics.track_api_request(
                endpoint=event.get('resource', '/orders'),
                method=event.get('httpMethod', 'UNKNOWN'),
                status_code=400,
                response_time_ms=execution_time
            )
        return result
    except Exception as e:
        logger.error(json.dumps({
            "event": "order_service_error",
            "error": str(e),
            "error_type": type(e).__name__
        }))
        result = {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'error': 'Internal server error'})
        }
        # Track error response
        if metrics:
            execution_time = (time.time() - start_time) * 1000
            metrics.track_api_request(
                endpoint=event.get('resource', '/orders'),
                method=event.get('httpMethod', 'UNKNOWN'),
                status_code=500,
                response_time_ms=execution_time
            )
        return result

def get_order_table_name(tenant_id: str, tier: str) -> str:
    """Get the appropriate order table name based on tier"""
    logger.info(json.dumps({
        "event": "get_order_table_name_started",
        "tenant_id": tenant_id,
        "tier": tier
    }))
    
    if tier == 'premium':
        logger.info(json.dumps({
            "event": "premium_tier_detected",
            "tenant_id": tenant_id
        }))
        
        # For Premium tenants we need to have a dedicated table, which has been created during onboarding
        try:
            tenants_table = dynamodb.Table('Tenants')
            
            logger.info(json.dumps({
                "event": "querying_tenants_table",
                "tenant_id": tenant_id
            }))
            
            response = tenants_table.get_item(Key={'tenant_id': tenant_id})
            
            logger.info(json.dumps({
                "event": "tenants_table_response",
                "tenant_id": tenant_id,
                "has_item": 'Item' in response,
                "response_keys": list(response.get('Item', {}).keys()) if 'Item' in response else []
            }))
            
            if 'Item' not in response or 'order_table_name' not in response['Item']:
                logger.error(json.dumps({
                    "event": "premium_table_not_found",
                    "tenant_id": tenant_id,
                    "response": response
                }))
                raise ValueError(f"Premium tenant {tenant_id} order table not found")
                
            table_name = response['Item']['order_table_name']
            logger.info(json.dumps({
                "event": "premium_table_found",
                "tenant_id": tenant_id,
                "table_name": table_name
            }))
            
            return table_name
        except Exception as e:
            logger.error(json.dumps({
                "event": "premium_table_lookup_failed",
                "tenant_id": tenant_id,
                "error": str(e),
                "error_type": type(e).__name__
            }))
            raise ValueError(f"Failed to lookup order table for tenant {tenant_id}: {str(e)}")
    else:
        # Basic tier always uses shared table
        logger.info(json.dumps({
            "event": "basic_tier_detected",
            "tenant_id": tenant_id,
            "shared_table": ORDERS_TABLE
        }))
        return ORDERS_TABLE

def list_orders(tenant_id: str, table_name: str, metrics=None) -> Dict[str, Any]:
    """List all orders for a tenant"""
    cors_headers = {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization'
    }
    
    logger.info(json.dumps({
        "event": "list_orders_started",
        "tenant_id": tenant_id,
        "table_name": table_name
    }))
    
    try:
        table = dynamodb.Table(table_name)
        
        logger.info(json.dumps({
            "event": "querying_orders_table",
            "tenant_id": tenant_id,
            "table_name": table_name
        }))
        
        response = table.query(
            KeyConditionExpression='tenant_id = :tenant_id',
            ExpressionAttributeValues={':tenant_id': tenant_id},
            ScanIndexForward=False  # Sort by order_id descending (newest first)
        )
        
        # Track DynamoDB operation
        if metrics:
            metrics.track_dynamodb_operation(
                table_name=table_name,
                operation="Query",
                consumed_rcu=len(response['Items']) * 0.5  # Estimate RCU consumption
            )
        
        logger.info(json.dumps({
            "event": "orders_query_completed",
            "tenant_id": tenant_id,
            "items_count": len(response['Items'])
        }))
        
        orders = []
        for item in response['Items']:
            # Convert Decimal to float for JSON serialization
            items = []
            for order_item in item.get('items', []):
                items.append({
                    'product_id': order_item['product_id'],
                    'product_name': order_item['product_name'],
                    'price': float(order_item['price']),
                    'quantity': int(order_item['quantity'])
                })
            
            orders.append({
                'order_id': item['order_id'],
                'items': items,
                'total_amount': float(item['total_amount']),
                'status': item['status'],
                'created_at': item['created_at'],
                'created_by': item.get('created_by')
            })
        
        logger.info(json.dumps({
            "event": "list_orders_completed",
            "tenant_id": tenant_id,
            "orders_count": len(orders)
        }))
        
        return {
            'statusCode': 200,
            'headers': cors_headers,
            'body': json.dumps({'orders': orders})
        }
        
    except Exception as e:
        logger.error(json.dumps({
            "event": "list_orders_error",
            "tenant_id": tenant_id,
            "table_name": table_name,
            "error": str(e),
            "error_type": type(e).__name__
        }))
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'error': 'Failed to list orders'})
        }

def create_order(event: Dict[str, Any], tenant_id: str, user_id: str, table_name: str, metrics=None) -> Dict[str, Any]:
    """Create a new multi-product order"""
    try:
        body = json.loads(event['body']) if isinstance(event.get('body'), str) else event.get('body', {})
        
        # Validate required fields
        if not body.get('items') or not isinstance(body['items'], list):
            return {
                'statusCode': 400,
                'headers': cors_headers,
                'body': json.dumps({'error': 'Items array is required'})
            }
        
        if len(body['items']) == 0:
            return {
                'statusCode': 400,
                'headers': cors_headers,
                'body': json.dumps({'error': 'Order must contain at least one item'})
            }
        
        # Validate and process items
        processed_items = []
        total_amount = Decimal('0')
        
        for item in body['items']:
            # Validate item fields
            required_item_fields = ['product_id', 'product_name', 'price', 'quantity']
            for field in required_item_fields:
                if field not in item:
                    return {
                        'statusCode': 400,
                        'headers': cors_headers,
                        'body': json.dumps({'error': f'Missing required item field: {field}'})
                    }
            
            # Validate price and quantity
            try:
                price = Decimal(str(item['price']))
                quantity = int(item['quantity'])
                
                if price <= 0:
                    raise ValueError("Price must be positive")
                if quantity <= 0:
                    raise ValueError("Quantity must be positive")
                
                item_total = price * quantity
                total_amount += item_total
                
                processed_items.append({
                    'product_id': item['product_id'],
                    'product_name': item['product_name'],
                    'price': price,
                    'quantity': quantity
                })
                
            except (ValueError, TypeError) as e:
                return {
                    'statusCode': 400,
                    'headers': cors_headers,
                    'body': json.dumps({'error': f'Invalid item data: {str(e)}'})
                }
        
        # Generate order ID
        order_id = str(uuid.uuid4())
        
        # Create order record
        table = dynamodb.Table(table_name)
        order_item = {
            'tenant_id': tenant_id,
            'order_id': order_id,
            'items': processed_items,
            'total_amount': total_amount,
            'status': 'completed',  # Orders are immediately completed in this simple implementation
            'created_at': datetime.utcnow().isoformat(),
            'created_by': user_id
        }
        
        table.put_item(Item=order_item)
        
        # Track DynamoDB operation
        if metrics:
            item_size = len(json.dumps(order_item, default=str))
            metrics.track_dynamodb_operation(
                table_name=table_name,
                operation="PutItem",
                consumed_wcu=1.0,  # Standard write operation
                consumed_rcu=0
            )
        
        # Convert Decimal to float for response
        response_items = []
        for item in processed_items:
            response_items.append({
                'product_id': item['product_id'],
                'product_name': item['product_name'],
                'price': float(item['price']),
                'quantity': item['quantity']
            })
        
        return {
            'statusCode': 201,
            'headers': cors_headers,
            'body': json.dumps({
                'message': 'Order created successfully',
                'order_id': order_id,
                'order': {
                    'order_id': order_id,
                    'items': response_items,
                    'total_amount': float(total_amount),
                    'status': 'completed',
                    'created_at': order_item['created_at']
                }
            })
        }
        
    except json.JSONDecodeError:
        return {
            'statusCode': 400,
            'headers': cors_headers,
            'body': json.dumps({'error': 'Invalid JSON in request body'})
        }
    except Exception as e:
        print(f"Create order error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'error': 'Failed to create order'})
        }
