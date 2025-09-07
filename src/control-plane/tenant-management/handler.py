import json
import boto3
import uuid
import os
from datetime import datetime
from typing import Dict, Any
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource('dynamodb')
events_client = boto3.client('events')

TENANTS_TABLE = os.environ['TENANTS_TABLE']
EVENT_BUS_NAME = os.environ['EVENT_BUS_NAME']

# CORS headers
cors_headers = {
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, POST, DELETE, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Amz-Date, X-Api-Key, X-Amz-Security-Token'
}

def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Handle tenant management operations"""
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
        
        if http_method == 'GET':
            return list_tenants()
        elif http_method == 'POST':
            return create_tenant(event)
        elif http_method == 'DELETE':
            tenant_id = path_parameters.get('tenant_id')
            if not tenant_id:
                return {
                    'statusCode': 400,
                    'headers': cors_headers,
                    'body': json.dumps({'error': 'tenant_id is required'})
                }
            return delete_tenant(tenant_id)
        else:
            return {
                'statusCode': 405,
                'headers': cors_headers,
                'body': json.dumps({'error': 'Method not allowed'})
            }
            
    except Exception as e:
        print(f"Tenant management error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'error': 'Internal server error'})
        }

def list_tenants() -> Dict[str, Any]:
    """List all tenants"""
    try:
        table = dynamodb.Table(TENANTS_TABLE)
        response = table.scan()
        
        tenants = []
        for item in response['Items']:
            tenants.append({
                'tenant_id': item['tenant_id'],
                'tenant_name': item['tenant_name'],
                'tier': item['tier'],
                'status': item['status'],
                'admin_email': item['admin_email'],
                'created_at': item['created_at'],
                'order_table_name': item.get('order_table_name')
            })
        
        return {
            'statusCode': 200,
            'headers': cors_headers,
            'body': json.dumps({'tenants': tenants})
        }
        
    except Exception as e:
        print(f"List tenants error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'error': 'Failed to list tenants'})
        }

def create_tenant(event: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new tenant (admin operation)"""
    try:
        body = json.loads(event['body']) if isinstance(event.get('body'), str) else event.get('body', {})
        
        # Validate required fields
        required_fields = ['tenant_name', 'admin_email', 'tier']
        for field in required_fields:
            if not body.get(field):
                return {
                    'statusCode': 400,
                    'headers': {'Content-Type': 'application/json'},
                    'body': json.dumps({'error': f'Missing required field: {field}'})
                }
        
        # Validate tier
        if body['tier'] not in ['basic', 'premium']:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'Tier must be either "basic" or "premium"'})
            }
        
        # Generate tenant ID
        tenant_id = str(uuid.uuid4())
        
        # Create tenant record
        table = dynamodb.Table(TENANTS_TABLE)
        tenant_item = {
            'tenant_id': tenant_id,
            'tenant_name': body['tenant_name'],
            'tier': body['tier'],
            'status': 'provisioning',
            'admin_email': body['admin_email'],
            'created_at': datetime.utcnow().isoformat(),
            'order_table_name': f"Orders-{tenant_id}" if body['tier'] == 'premium' else None
        }
        
        table.put_item(Item=tenant_item)
        
        # Publish tenant creation event for provisioning
        try:
            events_client.put_events(
                Entries=[
                    {
                        'Source': 'tenant.service',
                        'DetailType': 'Tenant Created',
                        'Detail': json.dumps({
                            'tenant_id': tenant_id,
                            'tier': body['tier'],
                            'tenant_name': body['tenant_name']
                        }),
                        'EventBusName': EVENT_BUS_NAME
                    }
                ]
            )
        except Exception as e:
            print(f"Failed to publish event: {str(e)}")
        
        return {
            'statusCode': 201,
            'headers': cors_headers,
            'body': json.dumps({
                'message': 'Tenant created successfully',
                'tenant_id': tenant_id,
                'status': 'provisioning'
            })
        }
        
    except json.JSONDecodeError:
        return {
            'statusCode': 400,
            'headers': cors_headers,
            'body': json.dumps({'error': 'Invalid JSON in request body'})
        }
    except Exception as e:
        print(f"Create tenant error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'error': 'Failed to create tenant'})
        }

def delete_tenant(tenant_id: str) -> Dict[str, Any]:
    """Delete a tenant and associated resources"""
    try:
        table = dynamodb.Table(TENANTS_TABLE)
        
        # Get tenant details first
        response = table.get_item(Key={'tenant_id': tenant_id})
        if 'Item' not in response:
            return {
                'statusCode': 404,
                'headers': cors_headers,
                'body': json.dumps({'error': 'Tenant not found'})
            }
        
        tenant = response['Item']
        
        # Delete tenant record
        table.delete_item(Key={'tenant_id': tenant_id})
        
        # TODO: Add cleanup logic for:
        # - Cognito users
        # - Premium tenant DynamoDB tables
        # - Other tenant-specific resources
        
        return {
            'statusCode': 200,
            'headers': cors_headers,
            'body': json.dumps({
                'message': 'Tenant deleted successfully',
                'tenant_id': tenant_id
            })
        }
        
    except Exception as e:
        print(f"Delete tenant error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'error': 'Failed to delete tenant'})
        }
