import json
import boto3
import os
import uuid
from datetime import datetime
from decimal import Decimal

def convert_floats_to_decimal(obj):
    """Recursively convert float values to Decimal for DynamoDB compatibility"""
    if isinstance(obj, float):
        return Decimal(str(obj))
    elif isinstance(obj, dict):
        return {k: convert_floats_to_decimal(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_floats_to_decimal(item) for item in obj]
    else:
        return obj

def handler(event, context):
    """Process metrics events from EventBridge and store in DynamoDB"""
    
    dynamodb = boto3.resource('dynamodb')
    metrics_table = dynamodb.Table(os.environ['METRICS_TABLE_NAME'])
    
    processed_count = 0
    failed_count = 0
    
    # Handle both EventBridge events and direct invocation
    records = event.get('Records', [event]) if 'Records' in event else [event]
    
    for record in records:
        try:
            # Parse event detail
            if 'detail' in record:
                detail = record['detail']
            else:
                detail = record
            
            # Create metrics record with 90-day TTL
            ttl_timestamp = int(datetime.now().timestamp() + (90 * 24 * 60 * 60))  # 90 days
            
            metrics_record = {
                'tenant_id': detail['tenant_id'],
                'timestamp_event': f"{detail['timestamp']}#{detail['event_type']}#{str(uuid.uuid4())}",
                'tier_name': detail['tier_name'],
                'service_name': detail['service_name'],
                'event_type': detail['event_type'],
                'timestamp': detail['timestamp'],
                'user_id': detail.get('user_id'),
                'metadata': convert_floats_to_decimal(detail.get('metadata', {})),
                'performance': convert_floats_to_decimal(detail.get('performance', {})),
                'ttl': ttl_timestamp
            }
            
            # Store in DynamoDB
            metrics_table.put_item(Item=metrics_record)
            processed_count += 1
            
        except Exception as e:
            print(f"Failed to process metrics record: {str(e)}")
            failed_count += 1
    
    return {
        'statusCode': 200,
        'body': json.dumps({
            'processed': processed_count,
            'failed': failed_count
        })
    }
