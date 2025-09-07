import json
import boto3
import uuid
import os
from datetime import datetime
from typing import Dict, Any

dynamodb = boto3.resource('dynamodb')
events_client = boto3.client('events')

TENANTS_TABLE = os.environ['TENANTS_TABLE']
EVENT_BUS_NAME = os.environ['EVENT_BUS_NAME']

def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Handle tenant registration requests"""
    # CORS headers for all responses
    cors_headers = {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization'
    }
    
    try:
        # Parse request body
        body = json.loads(event['body']) if isinstance(event.get('body'), str) else event.get('body', {})
        
        # Validate required fields
        required_fields = ['tenant_name', 'admin_email', 'admin_password', 'tier']
        for field in required_fields:
            if not body.get(field):
                return {
                    'statusCode': 400,
                    'headers': cors_headers,
                    'body': json.dumps({'error': f'Missing required field: {field}'})
                }
        
        # Validate tier
        if body['tier'] not in ['basic', 'premium']:
            return {
                'statusCode': 400,
                'headers': cors_headers,
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
        
        # Publish events for tenant provisioning and user creation
        events = [
            {
                'Source': 'tenant.service',
                'DetailType': 'Tenant Created',
                'Detail': json.dumps({
                    'tenant_id': tenant_id,
                    'tier': body['tier'],
                    'tenant_name': body['tenant_name']
                }),
                'EventBusName': EVENT_BUS_NAME
            },
            {
                'Source': 'tenant.service',
                'DetailType': 'Admin User Creation Requested',
                'Detail': json.dumps({
                    'tenant_id': tenant_id,
                    'tier': body['tier'],
                    'admin_email': body['admin_email'],
                    'admin_password': body['admin_password'],
                    'role': 'tenant_admin'
                }),
                'EventBusName': EVENT_BUS_NAME
            }
        ]
        
        try:
            events_client.put_events(Entries=events)
        except Exception as e:
            print(f"Failed to publish events: {str(e)}")
            # Rollback tenant creation if event publishing fails
            table.delete_item(Key={'tenant_id': tenant_id})
            return {
                'statusCode': 500,
                'headers': cors_headers,
                'body': json.dumps({'error': 'Failed to initiate tenant provisioning'})
            }
        
        return {
            'statusCode': 201,
            'headers': cors_headers,
            'body': json.dumps({
                'message': 'Tenant registration initiated successfully',
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
        print(f"Registration error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'error': 'Internal server error'})
        }
