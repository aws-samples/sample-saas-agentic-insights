import json
import boto3
import uuid
import os
import logging
import time
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

dynamodb = boto3.resource('dynamodb')
PRODUCTS_TABLE = os.environ['PRODUCTS_TABLE']

# Global CORS headers
cors_headers = {
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization'
}

def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Handle product management operations with metrics instrumentation"""
    
    start_time = time.time()
    
    try:
        http_method = event['httpMethod']
        path_parameters = event.get('pathParameters') or {}
        
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
        tier = authorizer_context.get('tier')
        user_id = authorizer_context.get('user_id')
        user_role = authorizer_context.get('role', 'tenant_user')
        
        # Initialize metrics collector
        metrics = None
        if METRICS_ENABLED and tenant_id and tier:
            metrics = MetricsCollector("product-service", tenant_id, tier)
        
        # Validate tenant context
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
        
        if http_method == 'GET':
            product_id = path_parameters.get('product_id')
            if product_id:
                result = get_product(tenant_id, product_id, metrics)
            else:
                result = list_products(tenant_id, metrics)
        elif http_method == 'POST':
            if user_role != 'tenant_admin':
                return {
                    'statusCode': 403,
                    'headers': cors_headers,
                    'body': json.dumps({'error': 'Only tenant admins can create products'})
                }
            result = create_product(event, tenant_id, user_id, metrics)
        elif http_method == 'PUT':
            if user_role != 'tenant_admin':
                return {
                    'statusCode': 403,
                    'headers': cors_headers,
                    'body': json.dumps({'error': 'Only tenant admins can update products'})
                }
            product_id = path_parameters.get('product_id')
            if not product_id:
                return {
                    'statusCode': 400,
                    'headers': cors_headers,
                    'body': json.dumps({'error': 'product_id is required'})
                }
            result = update_product(event, tenant_id, product_id, metrics)
        elif http_method == 'DELETE':
            if user_role != 'tenant_admin':
                return {
                    'statusCode': 403,
                    'headers': cors_headers,
                    'body': json.dumps({'error': 'Only tenant admins can delete products'})
                }
            product_id = path_parameters.get('product_id')
            if not product_id:
                return {
                    'statusCode': 400,
                    'headers': cors_headers,
                    'body': json.dumps({'error': 'product_id is required'})
                }
            result = delete_product(tenant_id, product_id, metrics)
        else:
            logger.warning(f"Method not allowed: {http_method}")
            result = {
                'statusCode': 405,
                'headers': cors_headers,
                'body': json.dumps({'error': 'Method not allowed'})
            }
        
        # Track successful API request
        if metrics:
            execution_time = (time.time() - start_time) * 1000
            metrics.track_api_request(
                endpoint=event.get('resource', '/products'),
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
            
    except Exception as e:
        logger.error(json.dumps({
            "event": "product_service_error",
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
                endpoint=event.get('resource', '/products'),
                method=event.get('httpMethod', 'UNKNOWN'),
                status_code=500,
                response_time_ms=execution_time
            )
        return result

def list_products(tenant_id: str, metrics=None) -> Dict[str, Any]:
    """List all products for a tenant"""
    try:
        table = dynamodb.Table(PRODUCTS_TABLE)
        
        logger.info(json.dumps({
            "event": "querying_products_table",
            "tenant_id": tenant_id,
            "table_name": PRODUCTS_TABLE
        }))
        
        response = table.query(
            KeyConditionExpression='tenant_id = :tenant_id',
            ExpressionAttributeValues={':tenant_id': tenant_id}
        )
        
        # Track DynamoDB operation
        if metrics:
            metrics.track_dynamodb_operation(
                table_name=PRODUCTS_TABLE,
                operation="Query",
                consumed_rcu=len(response['Items']) * 0.5  # Estimate RCU consumption
            )
        
        products = []
        for item in response['Items']:
            products.append({
                'product_id': item['product_id'],
                'name': item['name'],
                'description': item['description'],
                'price': float(item['price']),
                'created_at': item['created_at'],
                'created_by': item.get('created_by')
            })
        
        logger.info(json.dumps({
            "event": "list_products_completed",
            "tenant_id": tenant_id,
            "products_count": len(products)
        }))
        
        return {
            'statusCode': 200,
            'headers': cors_headers,
            'body': json.dumps({'products': products})
        }
        
    except Exception as e:
        logger.error(json.dumps({
            "event": "list_products_error",
            "tenant_id": tenant_id,
            "table_name": PRODUCTS_TABLE,
            "error": str(e),
            "error_type": type(e).__name__
        }))
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'error': 'Failed to list products'})
        }

def get_product(tenant_id: str, product_id: str, metrics=None) -> Dict[str, Any]:
    """Get a specific product"""
    try:
        table = dynamodb.Table(PRODUCTS_TABLE)
        response = table.get_item(
            Key={'tenant_id': tenant_id, 'product_id': product_id}
        )
        
        # Track DynamoDB operation
        if metrics:
            metrics.track_dynamodb_operation(
                table_name=PRODUCTS_TABLE,
                operation="GetItem",
                consumed_rcu=0.5  # Standard read operation
            )
        
        if 'Item' not in response:
            return {
                'statusCode': 404,
                'headers': cors_headers,
                'body': json.dumps({'error': 'Product not found'})
            }
        
        item = response['Item']
        product = {
            'product_id': item['product_id'],
            'name': item['name'],
            'description': item['description'],
            'price': float(item['price']),
            'created_at': item['created_at'],
            'created_by': item.get('created_by')
        }
        
        return {
            'statusCode': 200,
            'headers': cors_headers,
            'body': json.dumps({'product': product})
        }
        
    except Exception as e:
        logger.error(json.dumps({
            "event": "get_product_error",
            "tenant_id": tenant_id,
            "product_id": product_id,
            "error": str(e),
            "error_type": type(e).__name__
        }))
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'error': 'Failed to get product'})
        }

def create_product(event: Dict[str, Any], tenant_id: str, user_id: str, metrics=None) -> Dict[str, Any]:
    """Create a new product"""
    try:
        body = json.loads(event['body']) if isinstance(event.get('body'), str) else event.get('body', {})
        
        # Validate required fields
        required_fields = ['name', 'description', 'price']
        for field in required_fields:
            if not body.get(field):
                return {
                    'statusCode': 400,
                    'headers': cors_headers,
                    'body': json.dumps({'error': f'Missing required field: {field}'})
                }
        
        # Validate price
        try:
            price = Decimal(str(body['price']))
            if price <= 0:
                raise ValueError("Price must be positive")
        except (ValueError, TypeError):
            return {
                'statusCode': 400,
                'headers': cors_headers,
                'body': json.dumps({'error': 'Invalid price format'})
            }
        
        # Generate product ID
        product_id = str(uuid.uuid4())
        
        # Create product record
        table = dynamodb.Table(PRODUCTS_TABLE)
        product_item = {
            'tenant_id': tenant_id,
            'product_id': product_id,
            'name': body['name'],
            'description': body['description'],
            'price': price,
            'created_at': datetime.utcnow().isoformat(),
            'created_by': user_id
        }
        
        table.put_item(Item=product_item)
        
        # Track DynamoDB operation
        if metrics:
            metrics.track_dynamodb_operation(
                table_name=PRODUCTS_TABLE,
                operation="PutItem",
                consumed_wcu=1.0,  # Standard write operation
                consumed_rcu=0
            )
        
        logger.info(json.dumps({
            "event": "product_created",
            "tenant_id": tenant_id,
            "product_id": product_id,
            "user_id": user_id
        }))
        
        return {
            'statusCode': 201,
            'headers': cors_headers,
            'body': json.dumps({
                'message': 'Product created successfully',
                'product_id': product_id,
                'product': {
                    'product_id': product_id,
                    'name': body['name'],
                    'description': body['description'],
                    'price': float(price),
                    'created_at': product_item['created_at']
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
        logger.error(json.dumps({
            "event": "create_product_error",
            "tenant_id": tenant_id,
            "error": str(e),
            "error_type": type(e).__name__
        }))
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'error': 'Failed to create product'})
        }

def update_product(event: Dict[str, Any], tenant_id: str, product_id: str, metrics=None) -> Dict[str, Any]:
    """Update an existing product"""
    try:
        body = json.loads(event['body']) if isinstance(event.get('body'), str) else event.get('body', {})
        
        table = dynamodb.Table(PRODUCTS_TABLE)
        
        # Check if product exists
        response = table.get_item(Key={'tenant_id': tenant_id, 'product_id': product_id})
        if 'Item' not in response:
            return {
                'statusCode': 404,
                'headers': cors_headers,
                'body': json.dumps({'error': 'Product not found'})
            }
        
        # Track initial read operation
        if metrics:
            metrics.track_dynamodb_operation(
                table_name=PRODUCTS_TABLE,
                operation="GetItem",
                consumed_rcu=0.5
            )
        
        # Build update expression
        update_expression = "SET "
        expression_values = {}
        expression_names = {}
        
        if 'name' in body:
            update_expression += "#name = :name, "
            expression_names['#name'] = 'name'
            expression_values[':name'] = body['name']
        
        if 'description' in body:
            update_expression += "description = :description, "
            expression_values[':description'] = body['description']
        
        if 'price' in body:
            try:
                price = Decimal(str(body['price']))
                if price <= 0:
                    raise ValueError("Price must be positive")
                update_expression += "price = :price, "
                expression_values[':price'] = price
            except (ValueError, TypeError):
                return {
                    'statusCode': 400,
                    'headers': cors_headers,
                    'body': json.dumps({'error': 'Invalid price format'})
                }
        
        if not expression_values:
            return {
                'statusCode': 400,
                'headers': cors_headers,
                'body': json.dumps({'error': 'No fields to update'})
            }
        
        # Remove trailing comma and space
        update_expression = update_expression.rstrip(', ')
        
        # Update product
        table.update_item(
            Key={'tenant_id': tenant_id, 'product_id': product_id},
            UpdateExpression=update_expression,
            ExpressionAttributeValues=expression_values,
            ExpressionAttributeNames=expression_names if expression_names else None
        )
        
        # Track update operation
        if metrics:
            metrics.track_dynamodb_operation(
                table_name=PRODUCTS_TABLE,
                operation="UpdateItem",
                consumed_wcu=1.0,  # Standard write operation
                consumed_rcu=0
            )
        
        logger.info(json.dumps({
            "event": "product_updated",
            "tenant_id": tenant_id,
            "product_id": product_id
        }))
        
        return {
            'statusCode': 200,
            'headers': cors_headers,
            'body': json.dumps({
                'message': 'Product updated successfully',
                'product_id': product_id
            })
        }
        
    except json.JSONDecodeError:
        return {
            'statusCode': 400,
            'headers': cors_headers,
            'body': json.dumps({'error': 'Invalid JSON in request body'})
        }
    except Exception as e:
        logger.error(json.dumps({
            "event": "update_product_error",
            "tenant_id": tenant_id,
            "product_id": product_id,
            "error": str(e),
            "error_type": type(e).__name__
        }))
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'error': 'Failed to update product'})
        }

def delete_product(tenant_id: str, product_id: str, metrics=None) -> Dict[str, Any]:
    """Delete a product"""
    try:
        table = dynamodb.Table(PRODUCTS_TABLE)
        
        # Check if product exists
        response = table.get_item(Key={'tenant_id': tenant_id, 'product_id': product_id})
        if 'Item' not in response:
            return {
                'statusCode': 404,
                'headers': cors_headers,
                'body': json.dumps({'error': 'Product not found'})
            }
        
        # Track initial read operation
        if metrics:
            metrics.track_dynamodb_operation(
                table_name=PRODUCTS_TABLE,
                operation="GetItem",
                consumed_rcu=0.5
            )
        
        # Delete product
        table.delete_item(Key={'tenant_id': tenant_id, 'product_id': product_id})
        
        # Track delete operation
        if metrics:
            metrics.track_dynamodb_operation(
                table_name=PRODUCTS_TABLE,
                operation="DeleteItem",
                consumed_wcu=1.0,  # Standard write operation
                consumed_rcu=0
            )
        
        logger.info(json.dumps({
            "event": "product_deleted",
            "tenant_id": tenant_id,
            "product_id": product_id
        }))
        
        return {
            'statusCode': 200,
            'headers': cors_headers,
            'body': json.dumps({
                'message': 'Product deleted successfully',
                'product_id': product_id
            })
        }
        
    except Exception as e:
        logger.error(json.dumps({
            "event": "delete_product_error",
            "tenant_id": tenant_id,
            "product_id": product_id,
            "error": str(e),
            "error_type": type(e).__name__
        }))
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'error': 'Failed to delete product'})
        }
