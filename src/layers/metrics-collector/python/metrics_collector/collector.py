import boto3
import json
import os
from datetime import datetime
from typing import Dict, Any, Optional
from .constants import EventTypes, EventSources, DetailTypes, ServiceNames, Pricing

class MetricsCollector:
    def __init__(self, service_name: str, tenant_id: str, tier_name: str):
        self.service_name = service_name
        self.tenant_id = tenant_id
        self.tier_name = tier_name
        self.eventbridge = boto3.client('events')
        self.event_bus_name = os.environ.get('METRICS_EVENT_BUS_NAME', 'tenant-provisioning-bus')
        
        # AWS pricing constants using centralized constants
        self.pricing = {
            'api_gateway_requests': Pricing.API_GATEWAY_REQUESTS,
            'lambda_gb_second': Pricing.LAMBDA_GB_SECOND,
            'lambda_request': Pricing.LAMBDA_REQUEST,
            'dynamodb_wcu': Pricing.DYNAMODB_WCU,
            'dynamodb_rcu': Pricing.DYNAMODB_RCU,
            'claude_sonnet_input_token': Pricing.CLAUDE_SONNET_INPUT_TOKEN,
            'claude_sonnet_output_token': Pricing.CLAUDE_SONNET_OUTPUT_TOKEN,
        }
    
    def track_api_request(self, endpoint: str, method: str, status_code: int,
                         response_time_ms: float, user_id: Optional[str] = None):
        """Track API Gateway request with cost calculation"""
        cost = self.pricing['api_gateway_requests']
        
        self._publish_event(EventTypes.API_REQUEST, {
            "endpoint": endpoint,
            "method": method,
            "status_code": status_code,
            "response_time_ms": response_time_ms,
            "estimated_cost": cost
        }, user_id)
    
    def track_lambda_execution(self, function_name: str, memory_mb: int, duration_ms: float):
        """Track Lambda execution with cost calculation"""
        memory_gb = memory_mb / 1024
        duration_seconds = duration_ms / 1000
        
        compute_cost = self.pricing['lambda_gb_second'] * memory_gb * duration_seconds
        request_cost = self.pricing['lambda_request']
        total_cost = compute_cost + request_cost
        
        self._publish_event(EventTypes.LAMBDA_EXECUTION, {
            "function_name": function_name,
            "memory_allocated_mb": memory_mb,
            "execution_duration_ms": duration_ms,
            "estimated_cost": total_cost
        })
    
    def track_dynamodb_operation(self, table_name: str, operation: str,
                                consumed_rcu: float = 0, consumed_wcu: float = 0):
        """Track DynamoDB operation with cost calculation"""
        read_cost = consumed_rcu * self.pricing['dynamodb_rcu']
        write_cost = consumed_wcu * self.pricing['dynamodb_wcu']
        total_cost = read_cost + write_cost
        
        self._publish_event(EventTypes.DYNAMODB_OPERATION, {
            "table_name": table_name,
            "operation": operation,
            "consumed_read_capacity": consumed_rcu,
            "consumed_write_capacity": consumed_wcu,
            "estimated_cost": total_cost
        })
    
    def track_bedrock_invocation(self, model_id: str, input_tokens: int, output_tokens: int,
                                user_id: Optional[str] = None):
        """Track Bedrock AI usage with Claude Sonnet 4.5 cost calculation"""
        input_cost = input_tokens * self.pricing['claude_sonnet_input_token']
        output_cost = output_tokens * self.pricing['claude_sonnet_output_token']
        total_cost = input_cost + output_cost
        
        self._publish_event(EventTypes.BEDROCK_INVOCATION, {
            "model_id": model_id,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "estimated_cost": total_cost
        }, user_id)
    
    def track_s3_operation(self, bucket_name: str, operation: str, object_size_bytes: int = 0):
        """Track S3 operation with cost calculation"""
        request_cost = Pricing.S3_REQUESTS / 1000  # Per request
        storage_gb = object_size_bytes / (1024**3)
        hourly_storage_cost = (storage_gb * Pricing.S3_STORAGE_GB_MONTH) / (30 * 24)
        
        self._publish_event(EventTypes.S3_OPERATION, {
            "bucket_name": bucket_name,
            "operation": operation,
            "object_size_bytes": object_size_bytes,
            "estimated_cost": request_cost,
            "hourly_storage_cost": hourly_storage_cost
        })
    
    def _publish_event(self, event_type: str, metadata: Dict[str, Any],
                      user_id: Optional[str] = None):
        """Internal method to publish events to EventBridge"""
        try:
            event_detail = {
                "tenant_id": self.tenant_id,
                "tier_name": self.tier_name,
                "service_name": self.service_name,
                "event_type": event_type,
                "timestamp": datetime.now().isoformat(),
                "user_id": user_id,
                "metadata": metadata
            }
            
            self.eventbridge.put_events(
                Entries=[{
                    'Source': EventSources.METRICS,
                    'DetailType': DetailTypes.TENANT_METRIC_EVENT,
                    'Detail': json.dumps(event_detail),
                    'EventBusName': self.event_bus_name
                }]
            )
        except Exception as e:
            print(f"Metrics collection failed: {str(e)}")
