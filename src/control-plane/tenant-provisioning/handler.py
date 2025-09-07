import json
import boto3
import os
from typing import Dict, Any

dynamodb = boto3.resource('dynamodb')
dynamodb_client = boto3.client('dynamodb')
lambda_client = boto3.client('lambda')

TENANTS_TABLE = os.environ['TENANTS_TABLE']

def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Handle tenant provisioning events from EventBridge"""
    try:
        # Parse EventBridge event
        detail = event.get('detail', {})
        tenant_id = detail.get('tenant_id')
        tier = detail.get('tier')
        tenant_name = detail.get('tenant_name')
        
        if not tenant_id or not tier:
            print(f"Invalid event data: {event}")
            return {'statusCode': 400, 'body': 'Invalid event data'}
        
        print(f"Provisioning tenant {tenant_id} with tier {tier}")
        
        # Update tenant status to active for basic tier
        if tier == 'basic':
            update_tenant_status(tenant_id, 'active')
            print(f"Basic tier tenant {tenant_id} provisioned successfully")
            return {'statusCode': 200, 'body': 'Basic tenant provisioned'}
        
        # For premium tier, create dedicated DynamoDB table
        elif tier == 'premium':
            table_name = f"Orders-{tenant_id}"
            
            try:
                # Create dedicated DynamoDB table for premium tenant
                create_premium_order_table(table_name, tenant_id)
                
                # Update Order Service Lambda environment variables
                update_order_service_env_vars(tenant_id, table_name)
                
                # Update tenant status to active
                update_tenant_status(tenant_id, 'active')
                
                print(f"Premium tier tenant {tenant_id} provisioned successfully with table {table_name}")
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
