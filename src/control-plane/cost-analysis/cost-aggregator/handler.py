import json
import boto3
import os
from datetime import datetime
from decimal import Decimal

def handler(event, context):
    """Process DynamoDB Stream events and aggregate metrics"""
    
    processed_count = 0
    failed_count = 0
    
    for record in event['Records']:
        try:
            if record['eventName'] in ['INSERT', 'MODIFY']:
                metrics_item = record['dynamodb']['NewImage']
                
                tenant_id = metrics_item['tenant_id']['S']
                event_type = metrics_item['event_type']['S']
                timestamp = metrics_item['timestamp']['S']
                tier_name = metrics_item['tier_name']['S']
                date = extract_date(timestamp)
                
                # Parse metadata from DynamoDB Map format
                metadata = parse_dynamodb_map(metrics_item.get('metadata', {'M': {}}))
                
                # Aggregate usage metrics by type
                aggregate_usage_metrics(tenant_id, date, event_type, metadata, tier_name)
                processed_count += 1
                
        except Exception as e:
            print(f"Failed to process metrics aggregation: {str(e)}")
            failed_count += 1
    
    return {
        'statusCode': 200,
        'body': json.dumps({
            'processed': processed_count,
            'failed': failed_count
        })
    }

def parse_dynamodb_map(dynamodb_map):
    """Convert DynamoDB Map format to Python dict"""
    if 'M' not in dynamodb_map:
        return {}
    
    result = {}
    for key, value in dynamodb_map['M'].items():
        if 'S' in value:
            result[key] = value['S']
        elif 'N' in value:
            result[key] = float(value['N'])
        elif 'BOOL' in value:
            result[key] = value['BOOL']
        elif 'M' in value:
            result[key] = parse_dynamodb_map(value)
    
    return result

def aggregate_usage_metrics(tenant_id, date, event_type, metadata, tier_name):
    """Aggregate usage metrics by type for AI Agent processing"""
    
    aggregation_table = boto3.resource('dynamodb').Table(os.environ['COST_AGGREGATION_TABLE_NAME'])
    
    # Get estimated cost from metadata
    estimated_cost = metadata.get('estimated_cost', 0)
    
    if event_type == 'api.request':
        update_metric_sum(aggregation_table, tenant_id, date, 'api_gateway_requests', 1, estimated_cost, tier_name)
        
    elif event_type == 'lambda.execution':
        memory_mb = metadata.get('memory_allocated_mb', 0)
        duration_ms = metadata.get('execution_duration_ms', 0)
        memory_gb = memory_mb / 1024
        duration_seconds = duration_ms / 1000
        gb_seconds = memory_gb * duration_seconds
        
        update_metric_sum(aggregation_table, tenant_id, date, 'lambda_gb_seconds', gb_seconds, estimated_cost, tier_name)
        update_metric_sum(aggregation_table, tenant_id, date, 'lambda_requests', 1, 0, tier_name)  # Cost already counted in gb_seconds
        
    elif event_type == 'dynamodb.operation':
        rcu = metadata.get('consumed_read_capacity', 0)
        wcu = metadata.get('consumed_write_capacity', 0)
        
        update_metric_sum(aggregation_table, tenant_id, date, 'dynamodb_rcu_consumed', rcu, estimated_cost if rcu > 0 else 0, tier_name)
        update_metric_sum(aggregation_table, tenant_id, date, 'dynamodb_wcu_consumed', wcu, estimated_cost if wcu > 0 else 0, tier_name)
        
    elif event_type == 'bedrock.invocation':
        input_tokens = metadata.get('input_tokens', 0)
        output_tokens = metadata.get('output_tokens', 0)
        
        # Use actual Claude Sonnet 4.5 pricing to split costs
        CLAUDE_SONNET_INPUT_TOKEN_PRICE = 0.000003  # $3.00 per million
        CLAUDE_SONNET_OUTPUT_TOKEN_PRICE = 0.000015  # $15.00 per million
        
        input_cost = input_tokens * CLAUDE_SONNET_INPUT_TOKEN_PRICE
        output_cost = output_tokens * CLAUDE_SONNET_OUTPUT_TOKEN_PRICE
        
        update_metric_sum(aggregation_table, tenant_id, date, 'bedrock_input_tokens', input_tokens, input_cost, tier_name)
        update_metric_sum(aggregation_table, tenant_id, date, 'bedrock_output_tokens', output_tokens, output_cost, tier_name)
        
    elif event_type == 's3.operation':
        requests = 1
        object_size_bytes = metadata.get('object_size_bytes', 0)
        storage_gb_hours = (object_size_bytes / (1024**3)) * 1  # 1 hour
        
        update_metric_sum(aggregation_table, tenant_id, date, 's3_requests', requests, estimated_cost, tier_name)
        update_metric_sum(aggregation_table, tenant_id, date, 's3_storage_gb_hours', storage_gb_hours, 0, tier_name)  # Cost already counted in requests

def update_metric_sum(table, tenant_id, date, metric_name, value, cost=0, tier_name='basic'):
    """Atomically update monthly metric aggregation using new schema"""
    
    # Extract month from date (2025-08-15 -> 2025-08)
    month = date[:7]
    
    table.update_item(
        Key={
            'tenant_id': tenant_id,
            'metric_date_type': f"{month}#{metric_name}"
        },
        UpdateExpression='ADD #total_count :value, #cost :cost SET #month = :month, #metric_name = :metric_name, #tier_name = :tier_name, #last_updated = :timestamp',
        ExpressionAttributeNames={
            '#total_count': 'total_count',
            '#cost': 'estimated_cost',
            '#month': 'month', 
            '#metric_name': 'metric_name',
            '#tier_name': 'tier_name',
            '#last_updated': 'last_updated'
        },
        ExpressionAttributeValues={
            ':value': Decimal(str(value)),
            ':cost': Decimal(str(cost)),
            ':month': month,
            ':metric_name': metric_name,
            ':tier_name': tier_name,
            ':timestamp': datetime.utcnow().isoformat() + 'Z'
        }
    )

def extract_date(timestamp_str):
    """Extract date from ISO timestamp"""
    return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00')).strftime('%Y-%m-%d')
