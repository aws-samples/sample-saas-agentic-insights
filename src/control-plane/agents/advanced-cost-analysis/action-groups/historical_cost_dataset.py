import json
import boto3
from decimal import Decimal

def handler(event, context):
    """
    Action Group: historical-cost-dataset
    Action: get-historical-cost-dataset
    
    Description: Retrieves the entire historical cost dataset from CostPerTenant table.
    Returns all records with all columns: tenant_id | month | tier | cost | revenue | margin | margin_percentage
    
    The agent uses this complete dataset for cost analysis and dashboard generation.
    """
    
    try:
        # Get entire dataset
        dataset = get_entire_cost_dataset()
        
        return {
            'messageVersion': '1.0',
            'response': {
                'actionGroup': 'historical-cost-dataset',
                'apiPath': '/get-historical-cost-dataset',
                'httpMethod': 'POST',
                'httpStatusCode': 200,
                'responseBody': {
                    'application/json': {
                        'body': json.dumps(dataset, default=decimal_serializer)
                    }
                }
            }
        }
        
    except Exception as e:
        print(f"Error retrieving cost dataset: {str(e)}")
        return {
            'messageVersion': '1.0',
            'response': {
                'actionGroup': 'historical-cost-dataset',
                'apiPath': '/get-historical-cost-dataset',
                'httpMethod': 'POST',
                'httpStatusCode': 500,
                'responseBody': {
                    'application/json': {
                        'body': json.dumps({'error': str(e)})
                    }
                }
            }
        }

def get_entire_cost_dataset():
    """Scan entire CostPerTenant table and return all records as-is"""
    
    dynamodb = boto3.resource('dynamodb')
    cost_table = dynamodb.Table('AgenticInsights-CostPerTenant')
    
    try:
        # Scan entire table
        response = cost_table.scan()
        all_records = response['Items']
        
        # Handle pagination
        while 'LastEvaluatedKey' in response:
            response = cost_table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
            all_records.extend(response['Items'])
        
        print(f"DEBUG: Retrieved {len(all_records)} records from CostPerTenant table")
        print(f"DEBUG: Sample records: {all_records[:3] if all_records else 'No records found'}")
        
        print(f"Returning {len(all_records)} total cost records")
        return {'historical_cost_dataset': all_records}
        
    except Exception as e:
        print(f"Error scanning CostPerTenant table: {str(e)}")
        return {'historical_cost_dataset': []}

def decimal_serializer(obj):
    """JSON serializer for Decimal objects"""
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
