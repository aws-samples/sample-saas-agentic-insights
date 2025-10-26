import json
import boto3
import os
from typing import Dict, Any

dynamodb = boto3.resource('dynamodb')
dynamodb_client = boto3.client('dynamodb')
lambda_client = boto3.client('lambda')
cognito_client = boto3.client('cognito-idp')
events_client = boto3.client('events')

TENANTS_TABLE = os.environ['TENANTS_TABLE']

def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Handle tenant provisioning events from EventBridge"""
    try:
        # Parse EventBridge event
        detail = event.get('detail', {})
        tenant_id = detail.get('tenant_id')
        tier = detail.get('tier')
        tenant_name = detail.get('tenant_name')
        admin_email = detail.get('admin_email')  # Get admin email from event
        admin_password = detail.get('admin_password')  # Get admin password from event
        
        if not tenant_id or not tier:
            print(f"Invalid event data: {event}")
            return {'statusCode': 400, 'body': 'Invalid event data'}
        
        print(f"Provisioning tenant {tenant_id} with tier {tier}")
        
        # Update tenant status to active for basic tier
        if tier == 'basic':
            # Fire user creation event for basic tier
            if admin_email and admin_password:
                fire_user_creation_event(tenant_id, tier, admin_email, admin_password)
            
            update_tenant_status(tenant_id, 'active')
            print(f"Basic tier tenant {tenant_id} provisioned successfully")
            return {'statusCode': 200, 'body': 'Basic tenant provisioned'}
        
        # For premium tier, create dedicated DynamoDB table and Cognito User Pool
        elif tier == 'premium':
            table_name = f"Orders-{tenant_id}"
            user_pool_name = f"premium-tenant-{tenant_id}"
            
            try:
                # Create dedicated DynamoDB table for premium tenant
                create_premium_order_table(table_name, tenant_id)
                
                # Create dedicated Cognito User Pool for premium tenant
                user_pool_id = create_premium_user_pool(user_pool_name, tenant_id)
                
                # Update tenant record with user_pool_id
                update_tenant_user_pool(tenant_id, user_pool_id)
                
                # Update Order Service Lambda environment variables
                update_order_service_env_vars(tenant_id, table_name)
                
                # Fire user creation event now that user pool is ready
                if admin_email and admin_password:
                    fire_user_creation_event(tenant_id, tier, admin_email, admin_password)
                
                # Update tenant status to active
                update_tenant_status(tenant_id, 'active')
                
                print(f"Premium tier tenant {tenant_id} provisioned successfully with table {table_name} and user pool {user_pool_id}")
                return {'statusCode': 200, 'body': 'Premium tenant provisioned'}
                
            except Exception as e:
                print(f"Failed to provision premium tenant {tenant_id}: {str(e)}")
                update_tenant_status(tenant_id, 'failed')
                return {'statusCode': 500, 'body': f'Provisioning failed: {str(e)}'}
        
        else:
            print(f"Unknown tier: {tier}")
            return {'statusCode': 400, 'body': 'Unknown tier'}
            
    except Exception as e:
        print(f"Tenant provisioning error: {str(e)}")
        return {'statusCode': 500, 'body': 'Internal server error'}

def create_premium_order_table(table_name: str, tenant_id: str) -> None:
    """Create dedicated DynamoDB table for premium tenant orders"""
    try:
        dynamodb_client.create_table(
            TableName=table_name,
            KeySchema=[
                {'AttributeName': 'tenant_id', 'KeyType': 'HASH'},
                {'AttributeName': 'order_id', 'KeyType': 'RANGE'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'tenant_id', 'AttributeType': 'S'},
                {'AttributeName': 'order_id', 'AttributeType': 'S'}
            ],
            BillingMode='PAY_PER_REQUEST',
            Tags=[
                {'Key': 'TenantId', 'Value': tenant_id},
                {'Key': 'Tier', 'Value': 'premium'},
                {'Key': 'Purpose', 'Value': 'orders'}
            ]
        )
        
        # Wait for table to be active
        waiter = dynamodb_client.get_waiter('table_exists')
        waiter.wait(TableName=table_name)
        
        print(f"Created DynamoDB table: {table_name}")
        
    except dynamodb_client.exceptions.ResourceInUseException:
        print(f"Table {table_name} already exists")
    except Exception as e:
        print(f"Failed to create table {table_name}: {str(e)}")
        raise

def update_order_service_env_vars(tenant_id: str, table_name: str) -> None:
    """Update Order Service Lambda environment variables with new table"""
    try:
        # Get current function configuration
        function_name = 'AgenticInsightsAppPlane-OrderFunction'  # This should match CDK construct name
        
        try:
            response = lambda_client.get_function_configuration(FunctionName=function_name)
            current_env = response.get('Environment', {}).get('Variables', {})
            
            # Add new table mapping
            premium_tables = current_env.get('PREMIUM_ORDER_TABLES', '{}')
            premium_tables_dict = json.loads(premium_tables) if premium_tables else {}
            premium_tables_dict[tenant_id] = table_name
            
            # Update environment variables
            updated_env = current_env.copy()
            updated_env['PREMIUM_ORDER_TABLES'] = json.dumps(premium_tables_dict)
            
            lambda_client.update_function_configuration(
                FunctionName=function_name,
                Environment={'Variables': updated_env}
            )
            
            print(f"Updated Order Service environment variables for tenant {tenant_id}")
            
        except lambda_client.exceptions.ResourceNotFoundException:
            print(f"Order Service Lambda function not found: {function_name}")
            # This is not critical for provisioning, continue
            
    except Exception as e:
        print(f"Failed to update Order Service environment variables: {str(e)}")
        # This is not critical for provisioning, continue

def update_tenant_status(tenant_id: str, status: str) -> None:
    """Update tenant status in DynamoDB"""
    try:
        table = dynamodb.Table(TENANTS_TABLE)
        table.update_item(
            Key={'tenant_id': tenant_id},
            UpdateExpression='SET #status = :status',
            ExpressionAttributeNames={'#status': 'status'},
            ExpressionAttributeValues={':status': status}
        )
        print(f"Updated tenant {tenant_id} status to {status}")
        
    except Exception as e:
        print(f"Failed to update tenant status: {str(e)}")
        raise

def create_premium_user_pool(pool_name: str, tenant_id: str) -> str:
    """Create dedicated Cognito User Pool for Premium tenant"""
    try:
        response = cognito_client.create_user_pool(
            PoolName=pool_name,
            Policies={
                'PasswordPolicy': {
                    'MinimumLength': 6,
                    'RequireUppercase': False,
                    'RequireLowercase': False,
                    'RequireNumbers': False,
                    'RequireSymbols': False
                }
            },
            AutoVerifiedAttributes=['email'],
            UsernameAttributes=['email'],
            Schema=[
                {
                    'Name': 'email',
                    'AttributeDataType': 'String',
                    'Required': True,
                    'Mutable': True
                },
                {
                    'Name': 'tenant_id',
                    'AttributeDataType': 'String',
                    'Required': False,
                    'Mutable': False
                },
                {
                    'Name': 'role',
                    'AttributeDataType': 'String',
                    'Required': False,
                    'Mutable': True
                },
                {
                    'Name': 'tier',
                    'AttributeDataType': 'String',
                    'Required': False,
                    'Mutable': True
                }
            ],
            UserPoolTags={
                'TenantId': tenant_id,
                'Tier': 'premium',
                'Purpose': 'tenant-users'
            }
        )
        
        user_pool_id = response['UserPool']['Id']
        
        # Create user pool client
        client_response = cognito_client.create_user_pool_client(
            UserPoolId=user_pool_id,
            ClientName=f"{pool_name}-client",
            GenerateSecret=False,
            ExplicitAuthFlows=[
                'ALLOW_ADMIN_USER_PASSWORD_AUTH',
                'ALLOW_USER_PASSWORD_AUTH',
                'ALLOW_USER_SRP_AUTH',
                'ALLOW_REFRESH_TOKEN_AUTH'
            ]
        )
        
        print(f"Created Cognito User Pool: {user_pool_id} for tenant {tenant_id}")
        return user_pool_id
        
    except Exception as e:
        print(f"Failed to create user pool for tenant {tenant_id}: {str(e)}")
        raise

def update_tenant_user_pool(tenant_id: str, user_pool_id: str) -> None:
    """Update tenant record with dedicated user pool ID"""
    try:
        table = dynamodb.Table(TENANTS_TABLE)
        table.update_item(
            Key={'tenant_id': tenant_id},
            UpdateExpression='SET user_pool_id = :pool_id',
            ExpressionAttributeValues={':pool_id': user_pool_id}
        )
        print(f"Updated tenant {tenant_id} with user_pool_id {user_pool_id}")
        
    except Exception as e:
        print(f"Failed to update tenant user pool: {str(e)}")
        raise

def fire_user_creation_event(tenant_id: str, tier: str, admin_email: str, admin_password: str) -> None:
    """Fire user creation event after Premium tenant provisioning is complete"""
    try:
        event = {
            'Source': 'tenant.service',
            'DetailType': 'Admin User Creation Requested',
            'Detail': json.dumps({
                'tenant_id': tenant_id,
                'tier': tier,
                'admin_email': admin_email,
                'admin_password': admin_password,
                'role': 'tenant_admin'
            }),
            'EventBusName': 'tenant-provisioning-bus'
        }
        
        events_client.put_events(Entries=[event])
        print(f"Fired user creation event for tenant {tenant_id}")
        
    except Exception as e:
        print(f"Failed to fire user creation event: {str(e)}")
        raise
