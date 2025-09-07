import json
import boto3
import os
from typing import Dict, Any

cognito_client = boto3.client('cognito-idp')

BASIC_USER_POOL_ID = os.environ['BASIC_USER_POOL_ID']
BASIC_USER_POOL_CLIENT_ID = os.environ['BASIC_USER_POOL_CLIENT_ID']
PREMIUM_USER_POOL_ID = os.environ['PREMIUM_USER_POOL_ID']
PREMIUM_USER_POOL_CLIENT_ID = os.environ['PREMIUM_USER_POOL_CLIENT_ID']

# Global CORS headers
cors_headers = {
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization'
}

def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Handle user management operations"""
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
        tier = authorizer_context.get('tier', 'basic')
        
        if not tenant_id:
            return {
                'statusCode': 403,
                'headers': cors_headers,
                'body': json.dumps({'error': 'Missing tenant context'})
            }
        
        # Only tenant admins can manage users
        if user_role != 'tenant_admin':
            return {
                'statusCode': 403,
                'headers': cors_headers,
                'body': json.dumps({'error': 'Only tenant admins can manage users'})
            }
        
        # Get appropriate user pool based on tier
        user_pool_id, user_pool_client_id = get_user_pool_for_tier(tier)
        
        if http_method == 'GET':
            return list_users(tenant_id, user_pool_id)
        elif http_method == 'POST':
            return create_user(event, tenant_id, user_pool_id)
        elif http_method == 'PUT':
            user_id = path_parameters.get('user_id')
            if not user_id:
                return {
                    'statusCode': 400,
                    'headers': cors_headers,
                    'body': json.dumps({'error': 'user_id is required'})
                }
            return update_user(event, tenant_id, user_id, user_pool_id)
        elif http_method == 'DELETE':
            user_id = path_parameters.get('user_id')
            if not user_id:
                return {
                    'statusCode': 400,
                    'headers': cors_headers,
                    'body': json.dumps({'error': 'user_id is required'})
                }
            return delete_user(tenant_id, user_id, user_pool_id)
        else:
            return {
                'statusCode': 405,
                'headers': cors_headers,
                'body': json.dumps({'error': 'Method not allowed'})
            }
            
    except Exception as e:
        print(f"User service error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'error': 'Internal server error'})
        }

def get_user_pool_for_tier(tier: str) -> tuple:
    """Get user pool ID and client ID based on tier"""
    if tier == 'premium':
        return PREMIUM_USER_POOL_ID, PREMIUM_USER_POOL_CLIENT_ID
    else:
        return BASIC_USER_POOL_ID, BASIC_USER_POOL_CLIENT_ID

def list_users(tenant_id: str, user_pool_id: str) -> Dict[str, Any]:
    """List all users for a tenant"""
    try:
        # List all users (Cognito doesn't support filtering by custom attributes reliably)
        response = cognito_client.list_users(
            UserPoolId=user_pool_id,
            Limit=60
        )
        
        users = []
        for user in response['Users']:
            user_attributes = {attr['Name']: attr['Value'] for attr in user['Attributes']}
            
            # Filter by tenant_id in Python
            if user_attributes.get('custom:tenant_id') == tenant_id:
                users.append({
                    'user_id': user['Username'],
                    'email': user_attributes.get('email'),
                    'role': user_attributes.get('custom:role', 'tenant_user'),
                    'status': user['UserStatus'],
                    'created_at': user['UserCreateDate'].isoformat() if 'UserCreateDate' in user else None,
                    'enabled': user.get('Enabled', True)
                })
        
        return {
            'statusCode': 200,
            'headers': cors_headers,
            'body': json.dumps({'users': users})
        }
        
    except Exception as e:
        print(f"List users error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'error': 'Failed to list users'})
        }

def create_user(event: Dict[str, Any], tenant_id: str, user_pool_id: str) -> Dict[str, Any]:
    """Create a new tenant user"""
    try:
        body = json.loads(event['body']) if isinstance(event.get('body'), str) else event.get('body', {})
        
        # Validate required fields
        required_fields = ['email', 'password', 'role']
        for field in required_fields:
            if not body.get(field):
                return {
                    'statusCode': 400,
                    'headers': cors_headers,
                    'body': json.dumps({'error': f'Missing required field: {field}'})
                }
        
        # Validate role
        if body['role'] not in ['tenant_admin', 'tenant_user']:
            return {
                'statusCode': 400,
                'headers': cors_headers,
                'body': json.dumps({'error': 'Role must be either "tenant_admin" or "tenant_user"'})
            }
        
        # Validate email format
        email = body['email'].lower().strip()
        if '@' not in email:
            return {
                'statusCode': 400,
                'headers': cors_headers,
                'body': json.dumps({'error': 'Invalid email format'})
            }
        
        try:
            # Create Cognito user
            response = cognito_client.admin_create_user(
                UserPoolId=user_pool_id,
                Username=email,
                UserAttributes=[
                    {'Name': 'email', 'Value': email},
                    {'Name': 'email_verified', 'Value': 'true'},
                    {'Name': 'custom:tenant_id', 'Value': tenant_id},
                    {'Name': 'custom:role', 'Value': body['role']},
                    {'Name': 'custom:tier', 'Value': tier}
                ],
                TemporaryPassword=body['password'],
                MessageAction='SUPPRESS'
            )
            
            # Set permanent password
            cognito_client.admin_set_user_password(
                UserPoolId=user_pool_id,
                Username=email,
                Password=body['password'],
                Permanent=True
            )
            
            user_id = response['User']['Username']
            
            return {
                'statusCode': 201,
                'headers': cors_headers,
                'body': json.dumps({
                    'message': 'User created successfully',
                    'user_id': user_id,
                    'user': {
                        'user_id': user_id,
                        'email': email,
                        'role': body['role'],
                        'status': 'CONFIRMED'
                    }
                })
            }
            
        except cognito_client.exceptions.UsernameExistsException:
            return {
                'statusCode': 400,
                'headers': cors_headers,
                'body': json.dumps({'error': 'User with this email already exists'})
            }
        except cognito_client.exceptions.InvalidPasswordException as e:
            return {
                'statusCode': 400,
                'headers': cors_headers,
                'body': json.dumps({'error': f'Invalid password: {str(e)}'})
            }
        except Exception as e:
            print(f"Cognito create user error: {str(e)}")
            return {
                'statusCode': 400,
                'headers': cors_headers,
                'body': json.dumps({'error': f'Failed to create user: {str(e)}'})
            }
        
    except json.JSONDecodeError:
        return {
            'statusCode': 400,
            'headers': cors_headers,
            'body': json.dumps({'error': 'Invalid JSON in request body'})
        }
    except Exception as e:
        print(f"Create user error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'error': 'Failed to create user'})
        }

def update_user(event: Dict[str, Any], tenant_id: str, user_id: str, user_pool_id: str) -> Dict[str, Any]:
    """Update an existing user"""
    try:
        body = json.loads(event['body']) if isinstance(event.get('body'), str) else event.get('body', {})
        
        # Verify user belongs to tenant
        try:
            user_response = cognito_client.admin_get_user(
                UserPoolId=user_pool_id,
                Username=user_id
            )
            
            user_attributes = {attr['Name']: attr['Value'] for attr in user_response['UserAttributes']}
            if user_attributes.get('custom:tenant_id') != tenant_id:
                return {
                    'statusCode': 403,
                    'headers': cors_headers,
                    'body': json.dumps({'error': 'User not found in your tenant'})
                }
                
        except cognito_client.exceptions.UserNotFoundException:
            return {
                'statusCode': 404,
                'headers': cors_headers,
                'body': json.dumps({'error': 'User not found'})
            }
        
        # Update user attributes
        attributes_to_update = []
        
        if 'role' in body:
            if body['role'] not in ['tenant_admin', 'tenant_user']:
                return {
                    'statusCode': 400,
                    'headers': cors_headers,
                    'body': json.dumps({'error': 'Role must be either "tenant_admin" or "tenant_user"'})
                }
            attributes_to_update.append({'Name': 'custom:role', 'Value': body['role']})
        
        if attributes_to_update:
            cognito_client.admin_update_user_attributes(
                UserPoolId=user_pool_id,
                Username=user_id,
                UserAttributes=attributes_to_update
            )
        
        # Update password if provided
        if 'password' in body:
            try:
                cognito_client.admin_set_user_password(
                    UserPoolId=user_pool_id,
                    Username=user_id,
                    Password=body['password'],
                    Permanent=True
                )
            except cognito_client.exceptions.InvalidPasswordException as e:
                return {
                    'statusCode': 400,
                    'headers': cors_headers,
                    'body': json.dumps({'error': f'Invalid password: {str(e)}'})
                }
        
        return {
            'statusCode': 200,
            'headers': cors_headers,
            'body': json.dumps({
                'message': 'User updated successfully',
                'user_id': user_id
            })
        }
        
    except json.JSONDecodeError:
        return {
            'statusCode': 400,
            'headers': cors_headers,
            'body': json.dumps({'error': 'Invalid JSON in request body'})
        }
    except Exception as e:
        print(f"Update user error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'error': 'Failed to update user'})
        }

def delete_user(tenant_id: str, user_id: str, user_pool_id: str) -> Dict[str, Any]:
    """Delete a user"""
    try:
        # Verify user belongs to tenant
        try:
            user_response = cognito_client.admin_get_user(
                UserPoolId=user_pool_id,
                Username=user_id
            )
            
            user_attributes = {attr['Name']: attr['Value'] for attr in user_response['UserAttributes']}
            if user_attributes.get('custom:tenant_id') != tenant_id:
                return {
                    'statusCode': 403,
                    'headers': cors_headers,
                    'body': json.dumps({'error': 'User not found in your tenant'})
                }
                
        except cognito_client.exceptions.UserNotFoundException:
            return {
                'statusCode': 404,
                'headers': cors_headers,
                'body': json.dumps({'error': 'User not found'})
            }
        
        # Delete user
        cognito_client.admin_delete_user(
            UserPoolId=user_pool_id,
            Username=user_id
        )
        
        return {
            'statusCode': 200,
            'headers': cors_headers,
            'body': json.dumps({
                'message': 'User deleted successfully',
                'user_id': user_id
            })
        }
        
    except Exception as e:
        print(f"Delete user error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'error': 'Failed to delete user'})
        }
