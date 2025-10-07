import json
import boto3
import os
from decimal import Decimal

def handler(event, context):
    """
    Action Group: cost-dataset-fetcher
    Action: getCostPerTenantDataset
    
    Fetches complete CostPerTenant dataset for agent analysis
    """
    
    try:
        # Get CostPerTenant table
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table(os.environ['COST_PER_TENANT_TABLE_NAME'])
        
        # Scan entire table
        response = table.scan()
        items = response['Items']
        
        # Handle pagination if needed
        while 'LastEvaluatedKey' in response:
            response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
            items.extend(response['Items'])
        
        # Format dataset for agent (exclude updated_at)
        dataset = []
        for item in items:
            record = {
                'tenant_id': item.get('tenant_id', ''),
                'month': item.get('month', ''),
                'tier': item.get('tier', ''),
                'cost': float(item.get('cost', 0)),
                'revenue': float(item.get('revenue', 0)),
                'margin': float(item.get('margin', 0)),
                'margin_percentage': float(item.get('margin_percentage', 0))
            }
            dataset.append(record)
        
        result = {
            'dataset_size': len(dataset),
            'cost_per_tenant_data': dataset
        }
        
        print(f"DEBUG: Returning dataset with {len(dataset)} records")
        
        return {
            'messageVersion': '1.0',
            'response': {
                'actionGroup': 'cost-dataset-fetcher',
                'apiPath': '/getCostPerTenantDataset',
                'httpMethod': 'GET',
                'httpStatusCode': 200,
                'responseBody': {
                    'application/json': {
                        'body': json.dumps(result, default=decimal_serializer)
                    }
                }
            }
        }
        
    except Exception as e:
        print(f"Error fetching dataset: {str(e)}")
        return {
            'messageVersion': '1.0',
            'response': {
                'actionGroup': 'cost-dataset-fetcher',
                'apiPath': '/getCostPerTenantDataset',
                'httpMethod': 'GET',
                'httpStatusCode': 500,
                'responseBody': {
                    'application/json': {
                        'body': json.dumps({
                            'error': str(e),
                            'error_type': 'dataset_fetch_error'
                        })
                    }
                }
            }
        }

def decimal_serializer(obj):
    """JSON serializer for Decimal objects"""
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
