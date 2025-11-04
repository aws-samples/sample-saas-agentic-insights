"""
Metrics Aggregation Lambda Function

Processes CloudWatch Logs subscription events from API Gateway access logs,
aggregates metrics by tenant, feature, and time period, and stores them in
the AgenticInsights-UsageMetrics DynamoDB table.
"""

import json
import gzip
import base64
import boto3
import os
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Any, Optional
from collections import defaultdict
import traceback

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
table = None

def lambda_handler(event, context):
    """
    Process CloudWatch Logs subscription event
    
    Args:
        event: CloudWatch Logs subscription event with base64-encoded gzipped data
        context: Lambda context object
        
    Returns:
        dict: Processing summary with counts
    """
    global table
    
    # Initialize DynamoDB table
    table_name = os.environ.get('USAGE_METRICS_TABLE_NAME', 'AgenticInsights-UsageMetrics')
    table = dynamodb.Table(table_name)
    
    try:
        # Parse CloudWatch Logs event
        log_entries = parse_cloudwatch_logs_event(event)
        print(f"Parsed {len(log_entries)} log entries")
        
        if not log_entries:
            return {
                'statusCode': 200,
                'body': json.dumps({'message': 'No log entries to process'})
            }
        
        # Aggregate metrics from log entries
        aggregated_metrics = aggregate_metrics(log_entries)
        print(f"Generated {len(aggregated_metrics)} aggregated metrics")
        
        # Batch write metrics to DynamoDB
        write_results = batch_write_metrics(aggregated_metrics)
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'processed_logs': len(log_entries),
                'generated_metrics': len(aggregated_metrics),
                'written_metrics': write_results['success_count'],
                'failed_metrics': write_results['failed_count']
            })
        }
        
    except Exception as e:
        print(f"Error processing CloudWatch Logs event: {str(e)}")
        print(traceback.format_exc())
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }


def parse_cloudwatch_logs_event(event: Dict) -> List[Dict]:
    """
    Parse CloudWatch Logs subscription event format
    
    Decodes and decompresses base64-encoded gzipped log data,
    then extracts JSON log entries.
    
    Args:
        event: CloudWatch Logs subscription event
        
    Returns:
        List of parsed log entry dictionaries
    """
    log_entries = []
    
    try:
        # Extract and decode the log data
        if 'awslogs' not in event:
            print("Warning: No 'awslogs' field in event")
            return log_entries
        
        # Decode base64
        compressed_data = base64.b64decode(event['awslogs']['data'])
        
        # Decompress gzip
        decompressed_data = gzip.decompress(compressed_data)
        
        # Parse JSON
        log_data = json.loads(decompressed_data)
        
        # Extract log events
        if 'logEvents' not in log_data:
            print("Warning: No 'logEvents' field in log data")
            return log_entries
        
        # Parse each log event
        for log_event in log_data['logEvents']:
            try:
                message = log_event.get('message', '')
                
                # Skip empty messages
                if not message or message.strip() == '':
                    continue
                
                # Parse JSON log message
                log_entry = json.loads(message)
                
                # Add timestamp from CloudWatch if not present
                if 'timestamp' not in log_entry and 'timestamp' in log_event:
                    log_entry['timestamp'] = log_event['timestamp']
                
                log_entries.append(log_entry)
                
            except json.JSONDecodeError as e:
                print(f"Warning: Failed to parse log message as JSON: {message[:100]}")
                print(f"Error: {str(e)}")
                continue
            except Exception as e:
                print(f"Warning: Error processing log event: {str(e)}")
                continue
        
    except Exception as e:
        print(f"Error parsing CloudWatch Logs event: {str(e)}")
        print(traceback.format_exc())
    
    return log_entries


def aggregate_metrics(log_entries: List[Dict]) -> List[Dict]:
    """
    Aggregate metrics from log entries
    
    Groups logs by tenant_id, feature_name, and time period,
    then calculates various metrics.
    
    Args:
        log_entries: List of parsed log entries
        
    Returns:
        List of aggregated metric dictionaries
    """
    # Import aggregation functions
    from aggregation_logic import (
        aggregate_feature_metrics,
        aggregate_performance_metrics,
        aggregate_ai_metrics
    )
    from trend_calculator import enrich_metrics_with_trends
    
    aggregated_metrics = []
    
    try:
        # Determine time period (hourly aggregation)
        time_period = os.environ.get('AGGREGATION_INTERVAL', 'hourly')
        
        # Aggregate feature usage metrics
        feature_metrics = aggregate_feature_metrics(log_entries, time_period)
        aggregated_metrics.extend(feature_metrics)
        
        # Aggregate performance metrics
        performance_metrics = aggregate_performance_metrics(log_entries, time_period)
        aggregated_metrics.extend(performance_metrics)
        
        # Aggregate AI usage metrics
        ai_metrics = aggregate_ai_metrics(log_entries, time_period)
        aggregated_metrics.extend(ai_metrics)
        
        # Enrich metrics with trend data
        table_name = os.environ.get('USAGE_METRICS_TABLE_NAME', 'AgenticInsights-UsageMetrics')
        aggregated_metrics = enrich_metrics_with_trends(table_name, aggregated_metrics, time_period)
        
    except Exception as e:
        print(f"Error aggregating metrics: {str(e)}")
        print(traceback.format_exc())
    
    return aggregated_metrics


def batch_write_metrics(metrics: List[Dict]) -> Dict:
    """
    Batch write aggregated metrics to DynamoDB with error handling
    
    Writes metrics in batches of 25 (DynamoDB limit) with exponential backoff
    and retry logic for throttling errors.
    
    Args:
        metrics: List of aggregated metric dictionaries
        
    Returns:
        dict: Write results with success and failure counts
    """
    import time
    import random
    from botocore.exceptions import ClientError
    
    success_count = 0
    failed_count = 0
    failed_items = []
    
    # Process in batches of 25 (DynamoDB batch write limit)
    batch_size = int(os.environ.get('BATCH_SIZE', '25'))
    max_retries = 3
    
    for i in range(0, len(metrics), batch_size):
        batch = metrics[i:i + batch_size]
        
        # Retry logic with exponential backoff
        for retry in range(max_retries):
            try:
                # Convert batch to DynamoDB format
                request_items = []
                for metric in batch:
                    # Convert floats to Decimal for DynamoDB
                    metric_item = convert_floats_to_decimal(metric)
                    request_items.append({
                        'PutRequest': {
                            'Item': metric_item
                        }
                    })
                
                # Batch write to DynamoDB
                response = table.meta.client.batch_write_item(
                    RequestItems={
                        table.name: request_items
                    }
                )
                
                # Check for unprocessed items
                unprocessed = response.get('UnprocessedItems', {})
                
                if unprocessed and table.name in unprocessed:
                    unprocessed_count = len(unprocessed[table.name])
                    print(f"Warning: {unprocessed_count} items were not processed, will retry")
                    
                    # Retry unprocessed items
                    if retry < max_retries - 1:
                        # Exponential backoff with jitter
                        wait_time = (2 ** retry) + random.uniform(0, 1)
                        print(f"Waiting {wait_time:.2f} seconds before retry {retry + 1}")
                        time.sleep(wait_time)
                        
                        # Update batch to only include unprocessed items
                        batch = []
                        for item in unprocessed[table.name]:
                            if 'PutRequest' in item:
                                batch.append(item['PutRequest']['Item'])
                        continue
                    else:
                        # Max retries reached, log failed items
                        failed_count += unprocessed_count
                        failed_items.extend([item['PutRequest']['Item'] for item in unprocessed[table.name]])
                        print(f"Error: Failed to write {unprocessed_count} items after {max_retries} retries")
                
                # Success
                success_count += len(batch)
                break
                
            except ClientError as e:
                error_code = e.response['Error']['Code']
                
                if error_code == 'ProvisionedThroughputExceededException':
                    print(f"Warning: Throttled by DynamoDB, retry {retry + 1}/{max_retries}")
                    
                    if retry < max_retries - 1:
                        # Exponential backoff with jitter
                        wait_time = (2 ** retry) + random.uniform(0, 1)
                        print(f"Waiting {wait_time:.2f} seconds before retry")
                        time.sleep(wait_time)
                        continue
                    else:
                        print(f"Error: Failed to write batch after {max_retries} retries due to throttling")
                        failed_count += len(batch)
                        failed_items.extend(batch)
                        break
                else:
                    print(f"Error writing batch to DynamoDB: {error_code} - {str(e)}")
                    print(traceback.format_exc())
                    failed_count += len(batch)
                    failed_items.extend(batch)
                    break
                    
            except Exception as e:
                print(f"Error writing batch to DynamoDB: {str(e)}")
                print(traceback.format_exc())
                
                if retry < max_retries - 1:
                    # Retry on generic errors
                    wait_time = (2 ** retry) + random.uniform(0, 1)
                    print(f"Waiting {wait_time:.2f} seconds before retry {retry + 1}")
                    time.sleep(wait_time)
                    continue
                else:
                    failed_count += len(batch)
                    failed_items.extend(batch)
                    break
    
    # Log failed items for manual investigation
    if failed_items:
        print(f"Failed to write {len(failed_items)} items:")
        for item in failed_items[:5]:  # Log first 5 failed items
            print(f"  PK: {item.get('PK')}, SK: {item.get('SK')}")
    
    return {
        'success_count': success_count,
        'failed_count': failed_count,
        'failed_items': failed_items
    }


def convert_floats_to_decimal(obj: Any) -> Any:
    """
    Recursively convert float values to Decimal for DynamoDB
    
    Args:
        obj: Object to convert (dict, list, or primitive)
        
    Returns:
        Converted object with Decimals instead of floats
    """
    if isinstance(obj, dict):
        return {k: convert_floats_to_decimal(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_floats_to_decimal(item) for item in obj]
    elif isinstance(obj, float):
        return Decimal(str(obj))
    else:
        return obj
