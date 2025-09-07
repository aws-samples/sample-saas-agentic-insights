import json
import boto3
import uuid
import os
from datetime import datetime
from typing import Dict, Any
from decimal import Decimal

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
    """Handle product management operations"""
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
        user_role = authorizer_context.get('role', 'tenant_user')
        
        if not tenant_id:
            return {
                'statusCode': 403,
                'headers': cors_headers,
                'body': json.dumps({'error': 'Missing tenant context'})
            }
        
        if http_method == 'GET':
            product_id = path_parameters.get('product_id')
            if product_id:
                return get_product(tenant_id, product_id)
            else:
                return list_products(tenant_id)
        elif http_method == 'POST':
            if user_role != 'tenant_admin':
                return {
                    'statusCode': 403,
                    'headers': cors_headers,
                    'body': json.dumps({'error': 'Only tenant admins can create products'})
                }
            return create_product(event, tenant_id, authorizer_context.get('user_id'))
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
            return update_product(event, tenant_id, product_id)
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
            return delete_product(tenant_id, product_id)
        else:
            return {
                'statusCode': 405,
                'headers': cors_headers,
                'body': json.dumps({'error': 'Method not allowed'})
            }
            
    except Exception as e:
        print(f"Product service error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'error': 'Internal server error'})
        }

def list_products(tenant_id: str) -> Dict[str, Any]:
    """List all products for a tenant"""
    try:
        table = dynamodb.Table(PRODUCTS_TABLE)
        response = table.query(
            KeyConditionExpression='tenant_id = :tenant_id',
            ExpressionAttributeValues={':tenant_id': tenant_id}
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
        
        return {
            'statusCode': 200,
            'headers': cors_headers,
            'body': json.dumps({'products': products})
        }
        
    except Exception as e:
        print(f"List products error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'error': 'Failed to list products'})
        }

def get_product(tenant_id: str, product_id: str) -> Dict[str, Any]:
    """Get a specific product"""
    try:
        table = dynamodb.Table(PRODUCTS_TABLE)
        response = table.get_item(
            Key={'tenant_id': tenant_id, 'product_id': product_id}
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
        print(f"Get product error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'error': 'Failed to get product'})
        }

def create_product(event: Dict[str, Any], tenant_id: str, user_id: str) -> Dict[str, Any]:
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
        print(f"Create product error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'error': 'Failed to create product'})
        }

def update_product(event: Dict[str, Any], tenant_id: str, product_id: str) -> Dict[str, Any]:
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
        print(f"Update product error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'error': 'Failed to update product'})
        }

def delete_product(tenant_id: str, product_id: str) -> Dict[str, Any]:
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
        
        # Delete product
        table.delete_item(Key={'tenant_id': tenant_id, 'product_id': product_id})
        
        return {
            'statusCode': 200,
            'headers': cors_headers,
            'body': json.dumps({
                'message': 'Product deleted successfully',
                'product_id': product_id
            })
        }
        
    except Exception as e:
        print(f"Delete product error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'error': 'Failed to delete product'})
        }
