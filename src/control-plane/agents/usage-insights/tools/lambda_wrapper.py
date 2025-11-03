"""
Lambda Wrapper for Bedrock Agent Tools

This module provides Lambda handlers that wrap the tool functions
for use with Bedrock Agent action groups.
"""

import json
import logging
from typing import Dict, Any

# Import tool functions
from tools.ttv_calculator import calculate_time_to_value
from tools.cltv_projector import project_customer_lifetime_value
from tools.feature_adoption_analyzer import analyze_feature_adoption_rates
from tools.engagement_calculator import calculate_engagement_scores
from tools.at_risk_identifier import identify_at_risk_features

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Generic Lambda handler for Bedrock Agent action group invocations.
    
    The event structure from Bedrock Agent:
    {
        "messageVersion": "1.0",
        "agent": {...},
        "inputText": "...",
        "sessionId": "...",
        "actionGroup": "action-group-name",
        "apiPath": "/tool-name",
        "httpMethod": "POST",
        "parameters": [
            {"name": "param1", "type": "string", "value": "value1"},
            ...
        ],
        "requestBody": {
            "content": {
                "application/json": {
                    "properties": [
                        {"name": "param1", "type": "string", "value": "value1"},
                        ...
                    ]
                }
            }
        }
    }
    """
    
    logger.info(f"Received event: {json.dumps(event)}")
    
    try:
        # Extract action group and function name
        # For function schema, Bedrock sends "function" field instead of "apiPath"
        action_group = event.get('actionGroup', '')
        function_name = event.get('function', '')
        api_path = event.get('apiPath', '')  # May be empty for function schema
        
        # Determine if this is function schema (has 'function' field) or API schema (has 'apiPath')
        is_function_schema = 'function' in event
        
        logger.info(f"Extracted - Action Group: '{action_group}', Function: '{function_name}', API Path: '{api_path}', Is Function Schema: {is_function_schema}")
        
        # Extract parameters from request body (supports both OpenAPI and function schema formats)
        parameters = {}
        
        # Try extracting from requestBody.content (OpenAPI format)
        request_body = event.get('requestBody', {})
        content = request_body.get('content', {})
        app_json = content.get('application/json', {})
        properties = app_json.get('properties', [])
        
        for prop in properties:
            param_name = prop.get('name')
            param_value = prop.get('value')
            if param_name and param_value is not None:
                parameters[param_name] = param_value
        
        # Also try extracting from top-level parameters array (function schema format)
        if not parameters and 'parameters' in event:
            for param in event.get('parameters', []):
                param_name = param.get('name')
                param_value = param.get('value')
                if param_name and param_value is not None:
                    parameters[param_name] = param_value
        
        logger.info(f"Action group: {action_group}, API path: {api_path}")
        logger.info(f"Extracted parameters: {json.dumps(parameters)}")
        
        # Route to appropriate tool function
        result = None
        
        if 'calculate_time_to_value' in action_group or 'calculate_time_to_value' in api_path:
            # Reconstruct date_range from flattened parameters
            date_range = None
            if parameters.get('start_date') and parameters.get('end_date'):
                date_range = {
                    'start_date': parameters.get('start_date'),
                    'end_date': parameters.get('end_date')
                }
            result = calculate_time_to_value(
                tenant_id=parameters.get('tenant_id'),
                date_range=date_range
            )
        
        elif 'project_customer_lifetime_value' in action_group or 'project_customer_lifetime_value' in api_path:
            result = project_customer_lifetime_value(
                tenant_id=parameters.get('tenant_id'),
                projection_months=parameters.get('projection_months', 12)
            )
        
        elif 'analyze_feature_adoption_rates' in action_group or 'analyze_feature_adoption_rates' in api_path:
            result = analyze_feature_adoption_rates(
                tenant_id=parameters.get('tenant_id'),
                time_period_days=parameters.get('time_period_days', 30)
            )
        
        elif 'calculate_engagement_scores' in action_group or 'calculate_engagement_scores' in api_path:
            result = calculate_engagement_scores(
                tenant_id=parameters.get('tenant_id'),
                user_id=parameters.get('user_id')
            )
        
        elif 'identify_at_risk_features' in action_group or 'identify_at_risk_features' in api_path:
            result = identify_at_risk_features(
                tenant_id=parameters.get('tenant_id'),
                analysis_period_days=parameters.get('analysis_period_days', 90)
            )
        
        else:
            result = {
                "error": True,
                "error_code": "UNKNOWN_ACTION",
                "error_message": f"Unknown action group: {action_group}, API path: {api_path}"
            }
        
        # Format response for Bedrock Agent
        # Different response format for function schema vs API schema
        if is_function_schema:
            # Function schema response format
            response = {
                "messageVersion": "1.0",
                "response": {
                    "actionGroup": action_group,
                    "function": function_name,  # Return the function name, not apiPath
                    "functionResponse": {
                        "responseBody": {
                            "TEXT": {
                                "body": json.dumps(result)
                            }
                        }
                    }
                }
            }
        else:
            # API schema response format
            response = {
                "messageVersion": "1.0",
                "response": {
                    "actionGroup": action_group,
                    "apiPath": api_path if api_path else "",
                    "httpMethod": event.get('httpMethod', 'POST'),
                    "httpStatusCode": 200 if not result.get('error') else 400,
                    "responseBody": {
                        "application/json": {
                            "body": json.dumps(result)
                        }
                    }
                }
            }
        
        logger.info(f"Returning response: {json.dumps(response)}")
        return response
        
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}", exc_info=True)
        
        # Return error response
        error_response = {
            "messageVersion": "1.0",
            "response": {
                "actionGroup": event.get('actionGroup', ''),
                "apiPath": event.get('apiPath', ''),
                "httpMethod": event.get('httpMethod', 'POST'),
                "httpStatusCode": 500,
                "responseBody": {
                    "application/json": {
                        "body": json.dumps({
                            "error": True,
                            "error_code": "INTERNAL_ERROR",
                            "error_message": str(e)
                        })
                    }
                }
            }
        }
        
        return error_response
