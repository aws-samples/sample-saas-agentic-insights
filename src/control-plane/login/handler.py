import json
import boto3
import os
from typing import Dict, Any

cognito_client = boto3.client('cognito-idp')

ADMIN_USER_POOL_ID = os.environ['ADMIN_USER_POOL_ID']
ADMIN_USER_POOL_CLIENT_ID = os.environ['ADMIN_USER_POOL_CLIENT_ID']

def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Handle login requests for both admin and tenant users"""
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
        
        # Get user pool IDs from environment or CloudFormation exports
        try:
            # Get Basic and Premium user pool IDs from CloudFormation exports
            cf_client = boto3.client('cloudformation')
            
            # Get Basic tier user pool ID
            basic_response = cf_client.describe_stacks(StackName='AgenticInsightsAppPlane')
            basic_user_pool_id = None
            premium_user_pool_id = None
            
            for output in basic_response['Stacks'][0]['Outputs']:
                if output['OutputKey'] == 'BasicTierUserPoolId':
                    basic_user_pool_id = output['OutputValue']
                elif output['OutputKey'] == 'PremiumTierUserPoolId':
                    premium_user_pool_id = output['OutputValue']
            
            # Try authentication against different user pools
            user_pools_to_try = [
                {'pool_id': ADMIN_USER_POOL_ID, 'client_id': ADMIN_USER_POOL_CLIENT_ID, 'type': 'admin'},
                {'pool_id': basic_user_pool_id, 'client_id': None, 'type': 'basic'},
                {'pool_id': premium_user_pool_id, 'client_id': None, 'type': 'premium'}
            ]
            
            for pool_info in user_pools_to_try:
                if not pool_info['pool_id']:
                    continue
                    
                try:
                    # For admin pool, use the client ID; for tenant pools, we need to get the client ID
                    if pool_info['type'] == 'admin':
                        client_id = pool_info['client_id']
                    else:
                        # Get the first client for tenant user pools
                        clients_response = cognito_client.list_user_pool_clients(
                            UserPoolId=pool_info['pool_id'],
                            MaxResults=1
                        )
                        if not clients_response['UserPoolClients']:
                            continue
                        client_id = clients_response['UserPoolClients'][0]['ClientId']
                    
                    # Authenticate user with Cognito
                    response = cognito_client.admin_initiate_auth(
                        UserPoolId=pool_info['pool_id'],
                        ClientId=client_id,
                        AuthFlow='ADMIN_NO_SRP_AUTH',
                        AuthParameters={
                            'USERNAME': body['email'],
                            'PASSWORD': body['password']
                        }
                    )
                    
                    # Extract tokens
                    auth_result = response['AuthenticationResult']
                    access_token = auth_result['AccessToken']
                    id_token = auth_result['IdToken']
                    refresh_token = auth_result['RefreshToken']
                    
                    # Get user attributes
                    user_response = cognito_client.admin_get_user(
                        UserPoolId=pool_info['pool_id'],
                        Username=body['email']
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
                                'role': user_attributes.get('custom:role', 'saas_admin' if pool_info['type'] == 'admin' else 'tenant_admin'),
                                'tier': pool_info['type']
                            }
                        })
                    }
                    
                except cognito_client.exceptions.NotAuthorizedException:
                    continue  # Try next user pool
                except cognito_client.exceptions.UserNotFoundException:
                    continue  # Try next user pool
                except Exception as e:
                    print(f"Error trying pool {pool_info['pool_id']}: {str(e)}")
                    continue  # Try next user pool
            
            # If we get here, authentication failed in all pools
            return {
                'statusCode': 401,
                'headers': cors_headers,
                'body': json.dumps({'error': 'Invalid email or password'})
            }
            
        except Exception as e:
            print(f"Cognito authentication error: {str(e)}")
            return {
                'statusCode': 401,
                'headers': cors_headers,
                'body': json.dumps({'error': 'Authentication failed'})
            }
        
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
