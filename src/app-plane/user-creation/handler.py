import json
import boto3
import os
import logging
from typing import Dict, Any

# Configure structured logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

cognito_client = boto3.client('cognito-idp')
dynamodb = boto3.resource('dynamodb')

BASIC_USER_POOL_ID = os.environ['BASIC_USER_POOL_ID']
PREMIUM_USER_POOL_ID = os.environ['PREMIUM_USER_POOL_ID']
TENANTS_TABLE = 'Tenants'

def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Handle user creation events from EventBridge"""
    request_id = context.aws_request_id
    
    logger.info(json.dumps({
        "event": "user_creation_started",
        "request_id": request_id,
        "raw_event": event
    }))
    
    try:
        # Parse EventBridge event
        detail = event.get('detail', {})
        tenant_id = detail.get('tenant_id')
        tier = detail.get('tier')
        admin_email = detail.get('admin_email')
        admin_password = detail.get('admin_password')
        role = detail.get('role', 'tenant_admin')
        
        logger.info(json.dumps({
            "event": "parsed_event_data",
            "request_id": request_id,
            "tenant_id": tenant_id,
            "tier": tier,
            "admin_email": admin_email,
            "role": role,
            "has_password": bool(admin_password)
        }))
        
        if not all([tenant_id, tier, admin_email, admin_password]):
            logger.error(json.dumps({
                "event": "validation_failed",
                "request_id": request_id,
                "missing_fields": {
                    "tenant_id": not bool(tenant_id),
                    "tier": not bool(tier),
                    "admin_email": not bool(admin_email),
                    "admin_password": not bool(admin_password)
                }
            }))
            return {'statusCode': 400, 'body': 'Invalid event data'}
        
        # Determine user pool based on tier
        if tier == 'premium':
            # Get dedicated user pool ID from tenant record
            try:
                tenants_table = dynamodb.Table(TENANTS_TABLE)
                tenant_response = tenants_table.get_item(Key={'tenant_id': tenant_id})
                
                if 'Item' not in tenant_response or not tenant_response['Item'].get('user_pool_id'):
                    logger.error(json.dumps({
                        "event": "premium_user_pool_not_found",
                        "request_id": request_id,
                        "tenant_id": tenant_id,
                        "error": "Premium tenant user pool ID not found in Tenants table"
                    }))
                    return {'statusCode': 500, 'body': 'Premium tenant user pool not provisioned'}
                
                user_pool_id = tenant_response['Item']['user_pool_id']
                
                logger.info(json.dumps({
                    "event": "premium_user_pool_retrieved",
                    "request_id": request_id,
                    "tenant_id": tenant_id,
                    "user_pool_id": user_pool_id
                }))
                
            except Exception as e:
                logger.error(json.dumps({
                    "event": "tenant_lookup_failed",
                    "request_id": request_id,
                    "tenant_id": tenant_id,
                    "error": str(e)
                }))
                return {'statusCode': 500, 'body': 'Failed to lookup tenant user pool'}
        else:
            # Use shared Basic pool
            user_pool_id = BASIC_USER_POOL_ID
        
        logger.info(json.dumps({
            "event": "user_pool_selected",
            "request_id": request_id,
            "tenant_id": tenant_id,
            "tier": tier,
            "user_pool_id": user_pool_id,
            "admin_email": admin_email
        }))
        
        try:
            # Create Cognito user
            logger.info(json.dumps({
                "event": "creating_cognito_user",
                "request_id": request_id,
                "tenant_id": tenant_id,
                "user_pool_id": user_pool_id,
                "admin_email": admin_email
            }))
            
            cognito_client.admin_create_user(
                UserPoolId=user_pool_id,
                Username=admin_email,
                UserAttributes=[
                    {'Name': 'email', 'Value': admin_email},
                    {'Name': 'email_verified', 'Value': 'true'},
                    {'Name': 'custom:tenant_id', 'Value': tenant_id},
                    {'Name': 'custom:role', 'Value': role},
                    {'Name': 'custom:tier', 'Value': tier}
                ],
                TemporaryPassword=admin_password
            )
            
            logger.info(json.dumps({
                "event": "cognito_user_created",
                "request_id": request_id,
                "tenant_id": tenant_id,
                "admin_email": admin_email
            }))
            
            # Set permanent password
            logger.info(json.dumps({
                "event": "setting_permanent_password",
                "request_id": request_id,
                "tenant_id": tenant_id,
                "admin_email": admin_email
            }))
            
            cognito_client.admin_set_user_password(
                UserPoolId=user_pool_id,
                Username=admin_email,
                Password=admin_password,
                Permanent=True
            )
            
            logger.info(json.dumps({
                "event": "permanent_password_set",
                "request_id": request_id,
                "tenant_id": tenant_id,
                "admin_email": admin_email
            }))
            
            # Confirm user signup to set status to CONFIRMED
            logger.info(json.dumps({
                "event": "confirming_user_signup",
                "request_id": request_id,
                "tenant_id": tenant_id,
                "admin_email": admin_email
            }))
            
            cognito_client.admin_confirm_sign_up(
                UserPoolId=user_pool_id,
                Username=admin_email
            )
            
            logger.info(json.dumps({
                "event": "user_creation_completed",
                "request_id": request_id,
                "tenant_id": tenant_id,
                "admin_email": admin_email,
                "tier": tier,
                "user_pool_id": user_pool_id
            }))
            
            return {'statusCode': 200, 'body': 'User created successfully'}
            
        except cognito_client.exceptions.UsernameExistsException as e:
            logger.warning(json.dumps({
                "event": "user_already_exists",
                "request_id": request_id,
                "tenant_id": tenant_id,
                "admin_email": admin_email,
                "error": str(e)
            }))
            return {'statusCode': 200, 'body': 'User already exists'}
        except Exception as e:
            logger.error(json.dumps({
                "event": "cognito_operation_failed",
                "request_id": request_id,
                "tenant_id": tenant_id,
                "admin_email": admin_email,
                "user_pool_id": user_pool_id,
                "error": str(e),
                "error_type": type(e).__name__
            }))
            return {'statusCode': 500, 'body': f'User creation failed: {str(e)}'}
            
    except Exception as e:
        logger.error(json.dumps({
            "event": "user_creation_error",
            "request_id": request_id,
            "error": str(e),
            "error_type": type(e).__name__
        }))
        return {'statusCode': 500, 'body': 'Internal server error'}
