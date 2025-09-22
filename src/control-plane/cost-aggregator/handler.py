import json
import boto3
import os
from datetime import datetime
from decimal import Decimal

dynamodb = boto3.resource('dynamodb')
cost_per_tenant_table = dynamodb.Table(os.environ['COST_PER_TENANT_TABLE_NAME'])

def handler(event, context):
    """Process MetricsAggregation DynamoDB stream to update CostPerTenant table"""
    
    for record in event['Records']:
        if record['eventName'] in ['INSERT', 'MODIFY']:
            process_metrics_record(record)
    
    return {'statusCode': 200, 'body': 'Processed successfully'}

def process_metrics_record(record):
    """Process a single metrics aggregation record"""
    
    try:
        new_image = record['dynamodb']['NewImage']
        
        # Extract required fields - throw error if missing
        tenant_id = new_image['tenant_id']['S']
        month = new_image['month']['S']
        tier_name = new_image['tier_name']['S']
        
        # Calculate cost difference based on event type
        if record['eventName'] == 'INSERT':
            cost_to_add = float(new_image['estimated_cost']['N'])
        elif record['eventName'] == 'MODIFY':
            old_image = record['dynamodb']['OldImage']
            new_cost = float(new_image['estimated_cost']['N'])
            old_cost = float(old_image['estimated_cost']['N'])
            cost_to_add = new_cost - old_cost
        
    except KeyError as e:
        error_msg = f"Missing required field in record: {str(e)}"
        print(error_msg)
        raise Exception(error_msg)
    
    # Skip if no cost to add
    if cost_to_add == 0:
        return
    
    # Calculate revenue based on tier_name
    revenue = 29.00 if tier_name == 'basic' else 99.00
    
    try:
        # Check if row exists
        response = cost_per_tenant_table.get_item(
            Key={'tenant_id': tenant_id, 'month': month}
        )
        
        if 'Item' in response:
            # Row exists - get current cost and add cost difference
            current_cost = float(response['Item']['cost'])
            new_total_cost = current_cost + cost_to_add
        else:
            # Row doesn't exist - use cost_to_add as initial cost
            new_total_cost = cost_to_add
        
        # Calculate margin and margin_percentage
        margin = revenue - new_total_cost
        margin_percentage = (margin / revenue) * 100
        
        # Update or create row
        cost_per_tenant_table.put_item(
            Item={
                'tenant_id': tenant_id,
                'month': month,
                'tier': tier_name,
                'cost': Decimal(str(new_total_cost)),
                'revenue': Decimal(str(revenue)),
                'margin': Decimal(str(margin)),
                'margin_percentage': Decimal(str(margin_percentage)),
                'updated_at': datetime.utcnow().isoformat()
            }
        )
        
        print(f"Updated CostPerTenant: {tenant_id} {month} - Added: ${cost_to_add:.6f}, Total Cost: ${new_total_cost:.6f}, Revenue: ${revenue:.2f}, Margin: ${margin:.6f} ({margin_percentage:.2f}%)")
        
    except Exception as e:
        error_msg = f"Error updating CostPerTenant for {tenant_id} {month}: {str(e)}"
        print(error_msg)
        raise Exception(error_msg)
