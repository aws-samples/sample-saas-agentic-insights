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
        
        # Normalize tenant name (lowercase, no spaces)
        tenant_name = body['tenant_name'].lower().replace(' ', '-')
        
        # Check tenant name uniqueness
        table = dynamodb.Table(TENANTS_TABLE)
        existing_tenant = table.query(
            IndexName='tenant-name-index',
            KeyConditionExpression=Key('tenant_name').eq(tenant_name)
        )
        
        if existing_tenant['Items']:
            return {
                'statusCode': 409,
                'headers': cors_headers,
                'body': json.dumps({'error': 'Tenant name already exists. Please choose a different name.'})
            }
        
        # Get user pool IDs from CloudFormation (for Basic tier only)
        cf_client = boto3.client('cloudformation')
        app_plane_response = cf_client.describe_stacks(StackName='AgenticInsightsAppPlane')
        
        basic_user_pool_id = None
        
        for output in app_plane_response['Stacks'][0]['Outputs']:
            if output['OutputKey'] == 'BasicTierUserPoolId':
                basic_user_pool_id = output['OutputValue']
                break
        
        # Determine user pool ID based on tier
        if body['tier'] == 'premium':
            user_pool_id = None  # Will be set by provisioning service
        else:
            user_pool_id = basic_user_pool_id  # Use shared Basic pool
        
        # Generate tenant ID
        tenant_id = str(uuid.uuid4())
        
        # Create tenant record
        tenant_item = {
            'tenant_id': tenant_id,
            'tenant_name': tenant_name,  # Normalized name
            'tier': body['tier'],
            'status': 'provisioning',
            'admin_email': body['admin_email'],
            'user_pool_id': user_pool_id,  # None for Premium initially, set by provisioning
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
                    'tenant_name': body['tenant_name'],
                    'admin_email': body['admin_email'],  # Include admin credentials for Premium provisioning
                    'admin_password': body['admin_password']
                }),
                'EventBusName': EVENT_BUS_NAME
            }
        ]
        
        # For Basic tier, also fire user creation event immediately since no provisioning delay
        if body['tier'] == 'basic':
            events.append({
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
            })
        
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
