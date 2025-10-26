import json
import boto3
import os
from typing import Dict, Any

# Get the tenant management function name from environment
TENANT_MANAGEMENT_FUNCTION = os.environ.get('TENANT_MANAGEMENT_FUNCTION', 'AgenticInsightsControlPlane-TenantManagementFunction')
lambda_client = boto3.client('lambda')

def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Handle tenant registration requests by calling tenant management service"""
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
        
        # Validate required fields for registration
        required_fields = ['tenant_name', 'admin_email', 'admin_password', 'tier']
        for field in required_fields:
            if not body.get(field):
                return {
                    'statusCode': 400,
                    'headers': cors_headers,
                    'body': json.dumps({'error': f'Missing required field: {field}'})
                }
        
        # Call tenant management service for centralized onboarding
        tenant_mgmt_event = {
            'httpMethod': 'POST',
            'body': json.dumps(body)
        }
        
        try:
            response = lambda_client.invoke(
                FunctionName=TENANT_MANAGEMENT_FUNCTION,
                InvocationType='RequestResponse',
                Payload=json.dumps(tenant_mgmt_event)
            )
            
            result = json.loads(response['Payload'].read())
            
            # Return the response from tenant management service
            return {
                'statusCode': result.get('statusCode', 500),
                'headers': cors_headers,
                'body': result.get('body', json.dumps({'error': 'Unknown error'}))
            }
            
        except Exception as e:
            print(f"Failed to call tenant management service: {str(e)}")
            return {
                'statusCode': 500,
                'headers': cors_headers,
                'body': json.dumps({'error': 'Failed to process registration'})
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
