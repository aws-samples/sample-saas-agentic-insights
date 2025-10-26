import json
import boto3
import os
from typing import Dict, Any

cognito_client = boto3.client('cognito-idp')
dynamodb = boto3.resource('dynamodb')

BASIC_USER_POOL_ID = os.environ['BASIC_USER_POOL_ID']
PREMIUM_USER_POOL_ID = os.environ['PREMIUM_USER_POOL_ID']
TENANTS_TABLE = 'Tenants'

def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Handle tenant admin user creation events from EventBridge during tenant onboarding"""
    try:
        # Parse EventBridge event
        detail = event.get('detail', {})
        tenant_id = detail.get('tenant_id')
        tier = detail.get('tier')
        admin_email = detail.get('admin_email')
        admin_password = detail.get('admin_password')
        
        if not all([tenant_id, tier, admin_email, admin_password]):
            print(f"Missing required fields for tenant {tenant_id}")
            return {'statusCode': 400, 'body': 'Invalid event data'}
        
        # Determine user pool based on tier
        if tier == 'premium':
            # Get dedicated user pool ID from tenant record
            tenants_table = dynamodb.Table(TENANTS_TABLE)
            tenant_response = tenants_table.get_item(Key={'tenant_id': tenant_id})
            
            if 'Item' not in tenant_response or not tenant_response['Item'].get('user_pool_id'):
                print(f"Premium user pool not found for tenant {tenant_id}")
                return {'statusCode': 500, 'body': 'Premium tenant user pool not provisioned'}
            
            user_pool_id = tenant_response['Item']['user_pool_id']
        else:
            user_pool_id = BASIC_USER_POOL_ID
        
        # Create Cognito user
        try:
            cognito_client.admin_create_user(
                UserPoolId=user_pool_id,
                Username=admin_email,
                UserAttributes=[
                    {'Name': 'email', 'Value': admin_email},
                    {'Name': 'email_verified', 'Value': 'true'},
                    {'Name': 'custom:tenant_id', 'Value': tenant_id},
                    {'Name': 'custom:role', 'Value': 'tenant_admin'},
                    {'Name': 'custom:tier', 'Value': tier}
                ],
                TemporaryPassword=admin_password
            )
            
            # Set permanent password and confirm user
            cognito_client.admin_set_user_password(
                UserPoolId=user_pool_id,
                Username=admin_email,
                Password=admin_password,
                Permanent=True
            )
            
            cognito_client.admin_confirm_sign_up(
                UserPoolId=user_pool_id,
                Username=admin_email
            )
            
            print(f"Created tenant admin user {admin_email} for tenant {tenant_id} in {tier} tier")
            return {'statusCode': 200, 'body': 'User created successfully'}
            
        except cognito_client.exceptions.UsernameExistsException:
            print(f"User {admin_email} already exists for tenant {tenant_id}")
            return {'statusCode': 200, 'body': 'User already exists'}
        except Exception as e:
            print(f"Failed to create user {admin_email} for tenant {tenant_id}: {str(e)}")
            return {'statusCode': 500, 'body': f'User creation failed: {str(e)}'}
            
    except Exception as e:
        print(f"Tenant admin creation error: {str(e)}")
        return {'statusCode': 500, 'body': 'Internal server error'}
