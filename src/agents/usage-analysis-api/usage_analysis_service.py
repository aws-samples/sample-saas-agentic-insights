import json
import boto3
import os
import time
from datetime import datetime
from botocore.exceptions import ClientError
from typing import Dict, Any, Optional


class UsageAnalysisService:
    """Usage Analysis Service using Strands SDK and Bedrock AgentCore"""
    
    def __init__(self):
        self.bedrock_agent_runtime = boto3.client('bedrock-agent-runtime')
        self.agent_id = os.environ['BEDROCK_AGENT_ID']
        self.agent_alias_id = os.environ['BEDROCK_AGENT_ALIAS_ID']
        self.metrics_table = os.environ['METRICS_AGGREGATION_TABLE_NAME']
        self.tenants_table = os.environ['TENANTS_TABLE_NAME']
    
    def analyze_usage(self, analysis_type: str, tenant_id: str, user_role: str, 
                     user_id: Optional[str] = None, filters: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Main usage analysis method with role-based access control
        
        Args:
            analysis_type: Type of analysis to perform
            tenant_id: Target tenant ID (or 'all' for platform admin)
            user_role: Role of requesting user
            user_id: User ID for tenant_user role filtering
            filters: Additional filters for analysis
        
        Returns:
            Analysis results with insights and recommendations
        """
        
        try:
            # Role-based access control and API plane detection
            if user_role == "tenant_user" and not user_id:
                return self._error_response(400, "User ID required for tenant_user role")
            
            # Validate tenant access for non-platform admin users
            if user_role != "platform_admin" and tenant_id == "all":
                return self._error_response(403, "Only platform admins can access cross-tenant data")
            
            # Prepare agent input based on analysis type
            agent_input = self._prepare_agent_input(analysis_type, tenant_id, user_role, user_id, filters)
            
            # Invoke Strands agent via Bedrock AgentCore
            agent_response = self._invoke_strands_agent(agent_input)
            
            # Process and format response
            formatted_response = self._format_response(agent_response, user_role)
            
            # Log usage for audit trail
            self._log_usage_analysis(tenant_id, analysis_type, user_role, user_id)
            
            return formatted_response
            
        except Exception as e:
            print(f"Usage analysis error: {str(e)}")
            return self._error_response(500, "Internal server error during analysis")
    
    def _prepare_agent_input(self, analysis_type: str, tenant_id: str, user_role: str, 
                           user_id: Optional[str], filters: Optional[Dict]) -> Dict[str, Any]:
        """Prepare input for Strands agent based on analysis type"""
        
        # Base input with common parameters
        base_input = {
            "tenant_id": tenant_id,
            "user_role": user_role,
            "date_range": filters.get("date_range") if filters else None
        }
        
        # Add user_id for tenant_user role
        if user_role == "tenant_user" and user_id:
            base_input["user_id"] = user_id
        
        # Route to appropriate agent tool based on analysis type
        if analysis_type in ["tenant_usage", "overview", "usage_summary"]:
            return {
                "tool": "analyze_tenant_usage",
                "input": base_input
            }
        elif analysis_type in ["feature_adoption", "features", "adoption"]:
            scope = "platform" if user_role == "platform_admin" else "tenant" if user_role == "tenant_admin" else "user"
            return {
                "tool": "analyze_feature_adoption",
                "input": {
                    **base_input,
                    "scope": scope
                }
            }
        elif analysis_type in ["performance", "performance_metrics", "optimization"]:
            return {
                "tool": "analyze_performance_metrics",
                "input": {
                    **base_input,
                    "metrics_type": filters.get("metrics_type") if filters else None
                }
            }
        elif analysis_type in ["ai_usage", "ai", "ai_analysis"]:
            return {
                "tool": "analyze_ai_usage",
                "input": {
                    **base_input,
                    "include_cost_analysis": filters.get("include_cost_analysis", True) if filters else True
                }
            }
        else:
            # Default to tenant usage analysis
            return {
                "tool": "analyze_tenant_usage",
                "input": base_input
            }
    
    def _invoke_strands_agent(self, agent_input: Dict[str, Any]) -> Dict[str, Any]:
        """Invoke Strands agent via Bedrock AgentCore with retry logic"""
        
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                print(f"Invoking Strands agent (attempt {attempt + 1})")
                
                # Create session ID for this analysis request
                session_id = f"usage-analysis-{int(time.time())}"
                
                # Prepare the input text for the agent
                input_text = self._format_agent_input_text(agent_input)
                
                # Invoke the agent
                response = self.bedrock_agent_runtime.invoke_agent(
                    agentId=self.agent_id,
                    agentAliasId=self.agent_alias_id,
                    sessionId=session_id,
                    inputText=input_text
                )
                
                # Process streaming response
                result_text = ""
                for event_chunk in response['completion']:
                    if 'chunk' in event_chunk:
                        chunk_data = event_chunk['chunk']
                        if 'bytes' in chunk_data:
                            result_text += chunk_data['bytes'].decode('utf-8')
                
                print(f"Agent invocation successful on attempt {attempt + 1}")
                
                # Parse the agent response
                return self._parse_agent_response(result_text, agent_input)
                
            except ClientError as e:
                error_code = e.response['Error']['Code']
                print(f"Attempt {attempt + 1} failed with error: {error_code}")
                
                if error_code == 'ThrottlingException' and attempt < max_retries - 1:
                    print(f"Throttling detected, retrying in {retry_delay} seconds")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                    continue
                else:
                    raise e
        
        raise Exception("Max retries exceeded for agent invocation")
    
    def _format_agent_input_text(self, agent_input: Dict[str, Any]) -> str:
        """Format agent input as text for Bedrock AgentCore"""
        
        tool = agent_input["tool"]
        input_params = agent_input["input"]
        
        # Create a natural language request for the agent
        if tool == "analyze_tenant_usage":
            if input_params.get("tenant_id") == "all":
                text = f"Analyze platform-wide usage metrics for all tenants. User role: {input_params['user_role']}"
            else:
                text = f"Analyze usage metrics for tenant {input_params['tenant_id']}. User role: {input_params['user_role']}"
            
            if input_params.get("date_range"):
                text += f" Date range: {input_params['date_range']['start_date']} to {input_params['date_range']['end_date']}"
            
            if input_params.get("user_id"):
                text += f" Filter for user: {input_params['user_id']}"
        
        elif tool == "analyze_feature_adoption":
            text = f"Analyze feature adoption for tenant {input_params['tenant_id']} with scope: {input_params['scope']}"
        
        elif tool == "analyze_performance_metrics":
            text = f"Analyze performance metrics for tenant {input_params['tenant_id']}"
            if input_params.get("metrics_type"):
                text += f" Focus on: {', '.join(input_params['metrics_type'])}"
        
        elif tool == "analyze_ai_usage":
            text = f"Analyze AI usage patterns for tenant {input_params['tenant_id']}"
            if input_params.get("include_cost_analysis"):
                text += " Include cost optimization analysis"
        
        else:
            text = f"Perform {tool} analysis for tenant {input_params['tenant_id']}"
        
        return text
    
    def _parse_agent_response(self, response_text: str, agent_input: Dict[str, Any]) -> Dict[str, Any]:
        """Parse agent response text into structured data"""
        
        # For now, return the raw response text
        # In a production system, you might parse structured data from the agent
        return {
            "analysis": response_text,
            "tool_used": agent_input["tool"],
            "input_parameters": agent_input["input"],
            "timestamp": datetime.now().isoformat()
        }
    
    def _format_response(self, agent_response: Dict[str, Any], user_role: str) -> Dict[str, Any]:
        """Format response based on user role and add metadata"""
        
        return {
            "status": "success",
            "analysis": agent_response["analysis"],
            "metadata": {
                "tool_used": agent_response["tool_used"],
                "user_role": user_role,
                "timestamp": agent_response["timestamp"],
                "agent_id": self.agent_id
            }
        }
    
    def _log_usage_analysis(self, tenant_id: str, analysis_type: str, user_role: str, user_id: Optional[str]):
        """Log usage analysis for audit trail"""
        
        try:
            print(json.dumps({
                "event": "usage_analysis_completed",
                "tenant_id": tenant_id,
                "analysis_type": analysis_type,
                "user_role": user_role,
                "user_id": user_id,
                "timestamp": datetime.now().isoformat(),
                "agent_id": self.agent_id
            }))
        except Exception as e:
            print(f"Failed to log usage analysis: {str(e)}")
    
    def _error_response(self, status_code: int, message: str) -> Dict[str, Any]:
        """Create standardized error response"""
        
        return {
            "status": "error",
            "error": {
                "code": status_code,
                "message": message,
                "timestamp": datetime.now().isoformat()
            }
        }


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Lambda handler for usage analysis requests"""
    
    # CORS headers
    cors_headers = {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization, tenant-id, tier-name'
    }
    
    try:
        # Handle OPTIONS preflight requests
        if event['httpMethod'] == 'OPTIONS':
            return {
                'statusCode': 200,
                'headers': cors_headers,
                'body': ''
            }
        
        # Extract request context and authentication info
        request_context = event.get('requestContext', {})
        authorizer_context = request_context.get('authorizer', {})
        
        # Determine user role and context based on API plane
        api_id = request_context.get('apiId', '')
        
        # Extract user context from authorizer
        tenant_id = authorizer_context.get('tenant_id')
        user_role = authorizer_context.get('role', 'tenant_user')
        user_id = authorizer_context.get('user_id')
        tier_name = authorizer_context.get('tier')
        
        # For Control Plane API (platform admin), handle differently
        if not tenant_id and user_role in ['saas_admin', 'admin']:
            # Platform admin access via Control Plane
            user_role = 'platform_admin'
            tenant_id = 'all'  # Default to all tenants for platform admin
        
        # Validate required context
        if not tenant_id and user_role != 'platform_admin':
            return {
                'statusCode': 403,
                'headers': cors_headers,
                'body': json.dumps({'error': 'Missing tenant context'})
            }
        
        # Parse request body
        if event['httpMethod'] == 'POST':
            body = json.loads(event['body']) if event.get('body') else {}
        else:
            # GET request - use query parameters
            query_params = event.get('queryStringParameters') or {}
            body = {
                'analysis_type': query_params.get('type', 'tenant_usage'),
                'filters': {}
            }
            
            # Add date range if provided
            if query_params.get('start_date') and query_params.get('end_date'):
                body['filters']['date_range'] = {
                    'start_date': query_params['start_date'],
                    'end_date': query_params['end_date']
                }
        
        # Extract analysis parameters
        analysis_type = body.get('analysis_type', 'tenant_usage')
        filters = body.get('filters', {})
        
        # Override tenant_id if provided in request (for platform admin)
        if user_role == 'platform_admin' and body.get('tenant_id'):
            tenant_id = body['tenant_id']
        
        # Initialize usage analysis service
        usage_service = UsageAnalysisService()
        
        # Perform analysis
        result = usage_service.analyze_usage(
            analysis_type=analysis_type,
            tenant_id=tenant_id,
            user_role=user_role,
            user_id=user_id,
            filters=filters
        )
        
        # Return appropriate status code based on result
        if result.get('status') == 'error':
            error_code = result.get('error', {}).get('code', 500)
            return {
                'statusCode': error_code,
                'headers': cors_headers,
                'body': json.dumps(result)
            }
        else:
            return {
                'statusCode': 200,
                'headers': cors_headers,
                'body': json.dumps(result)
            }
        
    except json.JSONDecodeError:
        return {
            'statusCode': 400,
            'headers': cors_headers,
            'body': json.dumps({'error': 'Invalid JSON in request body'})
        }
    except Exception as e:
        print(f"Usage analysis API error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'error': 'Internal server error'})
        }