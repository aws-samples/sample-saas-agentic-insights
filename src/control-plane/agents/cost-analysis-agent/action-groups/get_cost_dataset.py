import json
import boto3
import os
from decimal import Decimal
from collections import defaultdict

def handler(event, context):
    """
    Action Group: cost-dataset-fetcher
    Action: getCostPerTenantDataset
    
    Fetches CostPerTenant dataset and calculates averages per month per tier
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
        
        # Group data by month and tier for averaging
        grouped = defaultdict(lambda: {'costs': [], 'revenues': [], 'margins': []})
        
        for item in items:
            month = item.get('month', '')
            tier = item.get('tier', '')
            cost = float(item.get('cost', 0))
            revenue = float(item.get('revenue', 0))
            margin = float(item.get('margin', 0))
            
            key = (month, tier)
            grouped[key]['costs'].append(cost)
            grouped[key]['revenues'].append(revenue)
            grouped[key]['margins'].append(margin)
        
        # Calculate averages per month per tier
        averaged_data = []
        for (month, tier), values in grouped.items():
            avg_cost = sum(values['costs']) / len(values['costs'])
            avg_revenue = sum(values['revenues']) / len(values['revenues'])
            avg_margin = sum(values['margins']) / len(values['margins'])
            
            averaged_data.append({
                'month': month,
                'tier': tier,
                'cost': round(avg_cost, 1),
                'revenue': round(avg_revenue, 1),
                'margin': round(avg_margin, 1)
            })
        
        # Sort by month and tier
        averaged_data.sort(key=lambda x: (x['month'], x['tier']))
        
        result = {
            'total_records': len(items),
            'cost_per_tenant_averages': averaged_data
        }
        
        print(f"DEBUG: Processed {len(items)} records into {len(averaged_data)} averaged records")
        print("DEBUG: Averaged Dataset JSON:")
        print(json.dumps(averaged_data, indent=2))
        
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

def decimal_serializer(obj):
    """JSON serializer for Decimal objects"""
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
