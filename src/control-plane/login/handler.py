import json
import boto3
import os
from typing import Dict, Any
from boto3.dynamodb.conditions import Key

cognito_client = boto3.client('cognito-idp')
dynamodb = boto3.resource('dynamodb')

ADMIN_USER_POOL_ID = os.environ['ADMIN_USER_POOL_ID']
ADMIN_USER_POOL_CLIENT_ID = os.environ['ADMIN_USER_POOL_CLIENT_ID']
TENANTS_TABLE = os.environ['TENANTS_TABLE']

def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Handle login requests with tenant name-based authentication"""
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
        if not body.get('email') or not body.get('password'):
            return {
                'statusCode': 400,
                'headers': cors_headers,
                'body': json.dumps({'error': 'Email and password are required'})
            }
        
        # Check if this is an admin login (no tenant_name provided)
        if not body.get('tenant_name'):
            return authenticate_admin_user(body['email'], body['password'], cors_headers)
        
        # Tenant user login - lookup tenant by name
        return authenticate_tenant_user(body['tenant_name'], body['email'], body['password'], cors_headers)
        
    except json.JSONDecodeError:
        return {
            'statusCode': 400,
            'headers': cors_headers,
            'body': json.dumps({'error': 'Invalid JSON in request body'})
        }
    except Exception as e:
        print(f"Login error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'error': 'Internal server error'})
        }

def authenticate_admin_user(email: str, password: str, cors_headers: dict) -> dict:
    """Authenticate admin user against admin pool"""
    try:
        response = cognito_client.admin_initiate_auth(
            UserPoolId=ADMIN_USER_POOL_ID,
            ClientId=ADMIN_USER_POOL_CLIENT_ID,
            AuthFlow='ADMIN_NO_SRP_AUTH',
            AuthParameters={
                'USERNAME': email,
                'PASSWORD': password
            }
        )
        
        # Extract tokens
        auth_result = response['AuthenticationResult']
        access_token = auth_result['AccessToken']
        id_token = auth_result['IdToken']
        refresh_token = auth_result['RefreshToken']
        
        # Get user attributes
        user_response = cognito_client.admin_get_user(
            UserPoolId=ADMIN_USER_POOL_ID,
            Username=email
        )
        
        user_attributes = {attr['Name']: attr['Value'] for attr in user_response['UserAttributes']}
        
        return {
            'statusCode': 200,
            'headers': cors_headers,
            'body': json.dumps({
                'message': 'Login successful',
                'tokens': {
                    'access_token': access_token,
                    'id_token': id_token,
                    'refresh_token': refresh_token
                },
                'user': {
                    'email': user_attributes.get('email'),
                    'tenant_id': None,
                    'role': 'saas_admin',
                    'tier': 'admin'
                }
            })
        }
        
    except cognito_client.exceptions.NotAuthorizedException:
        return {
            'statusCode': 401,
            'headers': cors_headers,
            'body': json.dumps({'error': 'Invalid email or password'})
        }
    except Exception as e:
        print(f"Admin authentication error: {str(e)}")
        return {
            'statusCode': 401,
            'headers': cors_headers,
            'body': json.dumps({'error': 'Authentication failed'})
        }

def authenticate_tenant_user(tenant_name: str, email: str, password: str, cors_headers: dict) -> dict:
    """Authenticate tenant user using tenant name lookup"""
    try:
        # Normalize tenant name
        tenant_name = tenant_name.lower().replace(' ', '-')
        
        # Lookup tenant by name
        table = dynamodb.Table(TENANTS_TABLE)
        tenant_response = table.query(
            IndexName='tenant-name-index',
            KeyConditionExpression=Key('tenant_name').eq(tenant_name)
        )
        
        if not tenant_response['Items']:
            return {
                'statusCode': 404,
                'headers': cors_headers,
                'body': json.dumps({'error': 'Tenant not found'})
            }
        
        tenant = tenant_response['Items'][0]
        user_pool_id = tenant['user_pool_id']
        
        # Get client ID for the user pool
        clients_response = cognito_client.list_user_pool_clients(
            UserPoolId=user_pool_id,
            MaxResults=1
        )
        
        if not clients_response['UserPoolClients']:
            return {
                'statusCode': 500,
                'headers': cors_headers,
                'body': json.dumps({'error': 'User pool configuration error'})
            }
        
        client_id = clients_response['UserPoolClients'][0]['ClientId']
        
        # Authenticate user
        response = cognito_client.admin_initiate_auth(
            UserPoolId=user_pool_id,
            ClientId=client_id,
            AuthFlow='ADMIN_NO_SRP_AUTH',
            AuthParameters={
                'USERNAME': email,
                'PASSWORD': password
            }
        )
        
        # Extract tokens
        auth_result = response['AuthenticationResult']
        access_token = auth_result['AccessToken']
        id_token = auth_result['IdToken']
        refresh_token = auth_result['RefreshToken']
        
        # Get user attributes
        user_response = cognito_client.admin_get_user(
            UserPoolId=user_pool_id,
            Username=email
        )
        
        user_attributes = {attr['Name']: attr['Value'] for attr in user_response['UserAttributes']}
        
        return {
            'statusCode': 200,
            'headers': cors_headers,
            'body': json.dumps({
                'message': 'Login successful',
                'tokens': {
                    'access_token': access_token,
                    'id_token': id_token,
                    'refresh_token': refresh_token
                },
                'user': {
                    'email': user_attributes.get('email'),
                    'tenant_id': user_attributes.get('custom:tenant_id'),
                    'role': user_attributes.get('custom:role', 'tenant_admin'),
                    'tier': user_attributes.get('custom:tier', tenant['tier'])
                }
            })
        }
        
    except cognito_client.exceptions.NotAuthorizedException:
        return {
            'statusCode': 401,
            'headers': cors_headers,
            'body': json.dumps({'error': 'Invalid email or password'})
        }
    except Exception as e:
        print(f"Tenant authentication error: {str(e)}")
        return {
            'statusCode': 401,
            'headers': cors_headers,
            'body': json.dumps({'error': 'Authentication failed'})
        }
