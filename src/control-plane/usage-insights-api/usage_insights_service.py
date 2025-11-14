"""
Usage Insights Service Lambda Function

This Lambda function provides AI-powered advanced usage insights for the Agentic Insights SaaS platform.
It integrates with Strands Bedrock agents to analyze usage patterns and provide insights including:
- Time to Value (TTV) calculations
- Customer Lifetime Value (CLTV) projections
- Feature adoption rate analysis
- User engagement scoring
- At-risk feature identification
"""

import json
import os
import logging
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import boto3
from botocore.exceptions import ClientError

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Ensure boto3 logging is also enabled for debugging
logging.getLogger('boto3').setLevel(logging.INFO)
logging.getLogger('botocore').setLevel(logging.INFO)


class StrandsBedrockClient:
    """Strands Bedrock client for agent invocation with retry logic and timeout handling"""
    
    def __init__(self, agent_id: str, agent_alias_id: str, timeout: int = 60):
        """
        Initialize Strands Bedrock client
        
        Args:
            agent_id: Bedrock agent ID
            agent_alias_id: Bedrock agent alias ID
            timeout: Request timeout in seconds
        """
        self.bedrock_agent_runtime = boto3.client('bedrock-agent-runtime')
        self.agent_id = agent_id
        self.agent_alias_id = agent_alias_id
        self.timeout = timeout
    
    def invoke_agent(self, input_text: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Invoke Bedrock agent with enhanced retry logic and timeout handling
        
        Implements exponential backoff retry strategy with max 3 retries.
        Classifies errors as retryable vs non-retryable for intelligent retry logic.
        
        Args:
            input_text: Input text for the agent
            session_id: Optional session ID for stateless operation
        
        Returns:
            Agent response
        
        Raises:
            BedrockAgentError: If agent invocation fails after retries
        """
        if not session_id:
            # Generate stateless session ID for cost efficiency
            session_id = f"usage-insights-{uuid.uuid4().hex[:8]}-{int(time.time())}"
        
        # Retry configuration
        max_tries = 3
        max_time = 60
        overall_start_time = time.time()
        
        for attempt in range(max_tries):
            if time.time() - overall_start_time > max_time:
                raise BedrockAgentError(
                    f"Overall timeout exceeded after {max_time} seconds",
                    error_code='TIMEOUT',
                    retryable=False
                )
            
            start_time = time.time()
            
            try:
                # Validate input before sending to agent
                if not input_text or len(input_text.strip()) == 0:
                    raise BedrockAgentError(
                        "Empty input text provided", 
                        error_code='INVALID_INPUT',
                        retryable=False
                    )
                
                if len(input_text) > 25000:  # Bedrock input limit
                    raise BedrockAgentError(
                        "Input text too long", 
                        details={'input_length': len(input_text), 'max_length': 25000},
                        error_code='INPUT_TOO_LONG',
                        retryable=False
                    )
                
                # PERFORMANCE OPTIMIZATION: Disable trace in production for faster responses
                # Set enableTrace=True only for debugging
                enable_trace = os.environ.get('ENABLE_BEDROCK_TRACE', 'false').lower() == 'true'
                
                # Invoke Bedrock agent
                response = self.bedrock_agent_runtime.invoke_agent(
                    agentId=self.agent_id,
                    agentAliasId=self.agent_alias_id,
                    sessionId=session_id,
                    inputText=input_text,
                    enableTrace=enable_trace  # Disabled by default for performance
                )
                
                elapsed_time = time.time() - start_time
                
                # Check for timeout
                if elapsed_time > self.timeout:
                    raise BedrockAgentError(
                        f"Agent invocation timed out after {elapsed_time:.2f} seconds",
                        details={'elapsed_time': elapsed_time, 'timeout': self.timeout},
                        error_code='TIMEOUT',
                        retryable=True
                    )
                
                # Log successful invocation
                logger.info(
                    "bedrock_agent_invoked",
                    extra={
                        'agent_id': self.agent_id,
                        'session_id': session_id,
                        'response_time_ms': int(elapsed_time * 1000),
                        'input_length': len(input_text),
                        'attempt': attempt + 1,
                        'success': True
                    }
                )
                
                return response
            
            except ClientError as e:
                error_code = e.response['Error']['Code']
                error_message = e.response['Error'].get('Message', '')
                elapsed_time = time.time() - start_time
                
                # Log error with structured logging
                logger.error(
                    "bedrock_agent_error",
                    extra={
                        'agent_id': self.agent_id,
                        'session_id': session_id,
                        'error_code': error_code,
                        'error_message': error_message,
                        'response_time_ms': int(elapsed_time * 1000),
                        'attempt': attempt + 1,
                        'success': False
                    }
                )
                
                # Classify errors as retryable or non-retryable
                non_retryable_errors = ['ValidationException', 'AccessDeniedException', 'ResourceNotFoundException']
                
                if error_code in non_retryable_errors:
                    # Non-retryable errors - fail immediately
                    if error_code == 'ValidationException':
                        raise BedrockAgentError(
                            "Invalid request parameters",
                            details={'aws_message': error_message},
                            error_code=error_code,
                            retryable=False
                        )
                    elif error_code == 'AccessDeniedException':
                        raise BedrockAgentError(
                            "Access denied to Bedrock agent",
                            details={'aws_message': error_message},
                            error_code=error_code,
                            retryable=False
                        )
                    elif error_code == 'ResourceNotFoundException':
                        raise BedrockAgentError(
                            "Bedrock agent not found or not available",
                            details={'agent_id': self.agent_id, 'alias_id': self.agent_alias_id},
                            error_code=error_code,
                            retryable=False
                        )
                
                # If this is the last attempt, raise the error
                if attempt == max_tries - 1:
                    if error_code == 'ThrottlingException':
                        raise BedrockAgentError(
                            "Service temporarily overloaded, please try again",
                            details={'retry_after_seconds': 30},
                            error_code=error_code,
                            retryable=True
                        )
                    elif error_code == 'ServiceUnavailableException':
                        raise BedrockAgentError(
                            "Bedrock service temporarily unavailable",
                            details={'retry_after_seconds': 60},
                            error_code=error_code,
                            retryable=True
                        )
                    elif error_code == 'InternalServerException':
                        raise BedrockAgentError(
                            "Internal service error occurred",
                            details={'aws_message': error_message},
                            error_code=error_code,
                            retryable=True
                        )
                    else:
                        raise BedrockAgentError(
                            f"Agent service error: {error_code}",
                            details={'aws_message': error_message, 'error_code': error_code},
                            error_code=error_code,
                            retryable=True
                        )
                
                # Wait before retrying with exponential backoff
                wait_time = min(2 ** attempt, 8)  # Cap at 8 seconds
                logger.info(f"Retrying after {wait_time} seconds (attempt {attempt + 1}/{max_tries})")
                time.sleep(wait_time)
                continue
            
            except Exception as e:
                elapsed_time = time.time() - start_time
                logger.error(
                    "bedrock_agent_unexpected_error",
                    extra={
                        'agent_id': self.agent_id,
                        'session_id': session_id,
                        'error_type': type(e).__name__,
                        'error_message': str(e),
                        'response_time_ms': int(elapsed_time * 1000),
                        'attempt': attempt + 1,
                        'success': False
                    }
                )
                
                # Check if error is retryable
                if isinstance(e, BedrockAgentError) and not e.retryable:
                    raise e
                
                # If this is the last attempt, raise the error
                if attempt == max_tries - 1:
                    raise BedrockAgentError(
                        f"Unexpected error during agent invocation: {str(e)}",
                        details={'error_type': type(e).__name__},
                        error_code='UNEXPECTED_ERROR',
                        retryable=True
                    )
                
                # Wait before retrying with exponential backoff
                wait_time = min(2 ** attempt, 8)  # Cap at 8 seconds
                logger.info(f"Retrying after {wait_time} seconds (attempt {attempt + 1}/{max_tries})")
                time.sleep(wait_time)
                continue
        
        # This should never be reached, but just in case
        raise BedrockAgentError(
            "All retry attempts failed",
            error_code='MAX_RETRIES_EXCEEDED',
            retryable=False
        )


# Custom exception classes
class ValidationError(Exception):
    """Raised when request validation fails"""
    def __init__(self, message, details=None, field=None):
        super().__init__(message)
        self.details = details or {}
        self.field = field


class AuthorizationError(Exception):
    """Raised when authorization fails"""
    def __init__(self, message, details=None, required_role=None):
        super().__init__(message)
        self.details = details or {}
        self.required_role = required_role


class BedrockAgentError(Exception):
    """Raised when Bedrock agent operations fail"""
    def __init__(self, message, details=None, error_code=None, retryable=False):
        super().__init__(message)
        self.details = details or {}
        self.error_code = error_code
        self.retryable = retryable


class DataNotFoundError(Exception):
    """Raised when requested data is not found"""
    def __init__(self, message, details=None, resource_type=None):
        super().__init__(message)
        self.details = details or {}
        self.resource_type = resource_type



class UsageInsightsService:
    """Main service class for usage insights analysis operations"""
    
    def __init__(self):
        """Initialize the service with required AWS clients and configuration"""
        self.dynamodb = boto3.resource('dynamodb')
        
        # Environment variables
        self.agent_id = os.environ.get('BEDROCK_AGENT_ID')
        self.agent_alias_id = os.environ.get('BEDROCK_AGENT_ALIAS_ID')
        self.metrics_table_name = os.environ.get('USAGE_METRICS_TABLE_NAME')
        self.tenants_table_name = os.environ.get('TENANTS_TABLE_NAME')
        
        # Validate required environment variables
        if not all([self.agent_id, self.agent_alias_id, self.metrics_table_name, self.tenants_table_name]):
            raise ValueError("Missing required environment variables")
        
        # Initialize Strands Bedrock client with 60-second timeout
        self.strands_client = StrandsBedrockClient(
            agent_id=self.agent_id,
            agent_alias_id=self.agent_alias_id,
            timeout=60
        )
        
        # Initialize DynamoDB tables
        self.metrics_table = self.dynamodb.Table(self.metrics_table_name)
        self.tenants_table = self.dynamodb.Table(self.tenants_table_name)
    
    def analyze_insights(self, request_data: Dict[str, Any], user_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main method to analyze usage insights using Strands Bedrock agent
        
        Args:
            request_data: Request payload with analysis parameters
            user_context: User context from JWT (tenant_id, role, user_id)
        
        Returns:
            Analysis results with AI insights and structured data
        """
        start_time = time.time()
        request_id = str(uuid.uuid4())
        
        # Log incoming request
        logger.info(f"Request ID: {request_id} - Incoming request_data: {json.dumps(request_data, default=str)}")
        logger.info(f"Request ID: {request_id} - User context: {json.dumps(user_context, default=str)}")
        
        try:
            logger.info(f"[{request_id}] Starting usage insights analysis")
            
            # Validate request parameters
            logger.info(f"[{request_id}] Validating request parameters")
            validated_request = self._validate_request(request_data, user_context)
            logger.info(f"[{request_id}] Request validated successfully")
            
            # Apply role-based access control and data filtering
            logger.info(f"[{request_id}] Applying RBAC filtering")
            filtered_request = self._apply_rbac_filtering(validated_request, user_context)
            logger.info(f"[{request_id}] RBAC filtering applied. Scope: {filtered_request.get('scope')}")
            
            # Get basic tenant info
            logger.info(f"[{request_id}] Getting tenant info for: {user_context['tenant_id']}")
            tenant_info = self._get_tenant_info(user_context['tenant_id'])
            logger.info(f"[{request_id}] Tenant info retrieved: {tenant_info}")
            
            # Invoke Strands Bedrock agent
            logger.info(f"[{request_id}] Invoking Bedrock agent")
            agent_response = self._invoke_strands_agent(filtered_request)
            logger.info(f"[{request_id}] Agent response received")
            
            # Extract AI-generated insights from agent response
            logger.info(f"[{request_id}] Extracting AI insights")
            ai_insights = self._extract_ai_insights(agent_response)
            logger.info(f"[{request_id}] Extracted {len(ai_insights)} insights")
            
            # Process and format response
            logger.info(f"[{request_id}] Formatting response")
            formatted_response = self._format_response(
                agent_response, ai_insights, tenant_info, user_context
            )
            logger.info(f"[{request_id}] Response formatted successfully")
            
            # Calculate response time
            response_time_ms = int((time.time() - start_time) * 1000)
            
            # Log successful analysis
            self._log_analysis_completion(
                validated_request, user_context, response_time_ms, request_id, success=True
            )
            
            return formatted_response
            
        except ValidationError as e:
            response_time_ms = int((time.time() - start_time) * 1000)
            logger.error(f"[{request_id}] ValidationError: {str(e)}")
            self._log_analysis_completion(
                request_data, user_context, response_time_ms, request_id, success=False, error=str(e)
            )
            return self._create_error_response(
                "VALIDATION_ERROR", 
                str(e), 
                400,
                details=getattr(e, 'details', {}),
                request_id=request_id
            )
        except AuthorizationError as e:
            response_time_ms = int((time.time() - start_time) * 1000)
            logger.error(f"[{request_id}] AuthorizationError: {str(e)}")
            self._log_analysis_completion(
                request_data, user_context, response_time_ms, request_id, success=False, error=str(e)
            )
            return self._create_error_response(
                "AUTHORIZATION_ERROR", 
                str(e), 
                403,
                details=getattr(e, 'details', {}),
                request_id=request_id
            )
        except DataNotFoundError as e:
            response_time_ms = int((time.time() - start_time) * 1000)
            logger.error(f"[{request_id}] DataNotFoundError: {str(e)}")
            self._log_analysis_completion(
                request_data, user_context, response_time_ms, request_id, success=False, error=str(e)
            )
            return self._create_error_response(
                "DATA_NOT_FOUND", 
                str(e), 
                404,
                details=getattr(e, 'details', {}),
                request_id=request_id
            )
        except BedrockAgentError as e:
            response_time_ms = int((time.time() - start_time) * 1000)
            logger.error(f"[{request_id}] BedrockAgentError: {str(e)}")
            self._log_analysis_completion(
                request_data, user_context, response_time_ms, request_id, success=False, error=str(e)
            )
            
            # Provide user-friendly message based on error type
            if getattr(e, 'retryable', False):
                user_message = "Analysis service is temporarily busy. Please try again in a moment."
            else:
                user_message = "Analysis service temporarily unavailable. Please try again later."
            
            return self._create_error_response(
                "AGENT_ERROR", 
                user_message, 
                500,
                details={
                    'error_code': getattr(e, 'error_code', 'UNKNOWN'),
                    'retryable': getattr(e, 'retryable', False),
                    **getattr(e, 'details', {})
                },
                request_id=request_id
            )
        except ClientError as e:
            response_time_ms = int((time.time() - start_time) * 1000)
            error_code = e.response.get('Error', {}).get('Code', 'UNKNOWN')
            error_message = e.response.get('Error', {}).get('Message', '')
            
            logger.error(f"[{request_id}] AWS ClientError: {error_code}")
            logger.error(f"[{request_id}] AWS Error Message: {error_message}")
            
            # Handle specific AWS service errors
            if error_code == 'ThrottlingException':
                user_message = "Service is temporarily overloaded. Please try again in a moment."
                status_code = 429
                error_type = "RATE_LIMIT_ERROR"
            elif error_code == 'AccessDeniedException':
                user_message = "Access denied to required services."
                status_code = 403
                error_type = "ACCESS_DENIED"
            else:
                user_message = "A service error occurred. Please try again later."
                status_code = 500
                error_type = "SERVICE_ERROR"
            
            self._log_analysis_completion(
                request_data, user_context, response_time_ms, request_id, success=False, error=f"AWS Error: {error_code}"
            )
            
            return self._create_error_response(
                error_type,
                user_message,
                status_code,
                details={'aws_error_code': error_code},
                request_id=request_id
            )
        except Exception as e:
            response_time_ms = int((time.time() - start_time) * 1000)
            logger.error(f"[{request_id}] Unexpected error: {str(e)}", exc_info=True)
            self._log_analysis_completion(
                request_data, user_context, response_time_ms, request_id, success=False, error=str(e)
            )
            return self._create_error_response(
                "INTERNAL_ERROR", 
                "An unexpected error occurred. Please try again later.", 
                500,
                details={'error_type': type(e).__name__},
                request_id=request_id
            )
    
    def _validate_request(self, request_data: Dict[str, Any], user_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and sanitize request parameters to prevent prompt injection attacks
        
        Args:
            request_data: Raw request data
            user_context: User context from JWT
        
        Returns:
            Validated and sanitized request data
        
        Raises:
            ValidationError: If validation fails
        """
        # Required fields validation
        analysis_type = request_data.get('analysis_type')
        if not analysis_type:
            raise ValidationError(
                "analysis_type is required", 
                details={'valid_types': ['ttv', 'cltv', 'feature_adoption', 'engagement', 'at_risk']},
                field='analysis_type'
            )
        
        # Sanitize and validate analysis_type
        analysis_type = self._sanitize_string_input(analysis_type)
        valid_analysis_types = ['ttv', 'cltv', 'feature_adoption', 'engagement', 'at_risk']
        if analysis_type not in valid_analysis_types:
            raise ValidationError(
                f"Invalid analysis_type: {analysis_type}", 
                details={'valid_types': valid_analysis_types, 'provided': analysis_type},
                field='analysis_type'
            )
        
        # Validate date_range if provided
        date_range = request_data.get('date_range')
        if date_range:
            date_range = self._validate_and_sanitize_date_range(date_range)
        else:
            # Default to last 120 days for insights analysis
            current_date = datetime.now()
            start_date = (current_date - timedelta(days=120)).strftime('%Y-%m-%d')
            end_date = current_date.strftime('%Y-%m-%d')
            date_range = {'start_date': start_date, 'end_date': end_date}
        
        # Validate and sanitize filters
        filters = request_data.get('filters', {})
        if not isinstance(filters, dict):
            raise ValidationError(
                "filters must be a dictionary", 
                details={'provided_type': type(filters).__name__},
                field='filters'
            )
        
        # Sanitize filter values to prevent prompt injection
        sanitized_filters = self._sanitize_filters(filters)
        
        return {
            'analysis_type': analysis_type,
            'date_range': date_range,
            'filters': sanitized_filters,
            'tenant_id': user_context['tenant_id'],
            'user_role': user_context['role'],
            'user_id': user_context.get('user_id')
        }
    
    def _sanitize_string_input(self, input_str: str, max_length: int = 100) -> str:
        """
        Sanitize string input to prevent prompt injection attacks
        
        Args:
            input_str: Input string to sanitize
            max_length: Maximum allowed length
        
        Returns:
            Sanitized string
        
        Raises:
            ValidationError: If input is invalid
        """
        if not isinstance(input_str, str):
            raise ValidationError(
                "Input must be a string", 
                details={'provided_type': type(input_str).__name__}
            )
        
        # Remove potentially dangerous characters and patterns
        import re
        
        # Remove control characters and excessive whitespace
        sanitized = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', input_str)
        sanitized = re.sub(r'\s+', ' ', sanitized).strip()
        
        # Check length
        if len(sanitized) > max_length:
            raise ValidationError(
                f"Input too long (max {max_length} characters)", 
                details={'length': len(sanitized), 'max_length': max_length}
            )
        
        # Check for prompt injection patterns
        dangerous_patterns = [
            r'(?i)(ignore|forget|disregard).*(previous|above|instruction)',
            r'(?i)(system|assistant|user):\s*',
            r'(?i)act\s+as\s+',
            r'(?i)pretend\s+to\s+be',
            r'(?i)role\s*[:=]\s*',
            r'(?i)prompt\s*[:=]\s*',
            r'(?i)\\n\\n',
            r'(?i)```',
            r'(?i)<\s*script',
            r'(?i)javascript:',
            r'(?i)data:',
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, sanitized):
                raise ValidationError(
                    "Input contains potentially dangerous content", 
                    details={'pattern_detected': True, 'input_length': len(sanitized)}
                )
        
        return sanitized
    
    def _sanitize_filters(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize filter values to prevent prompt injection
        
        Args:
            filters: Filter dictionary
        
        Returns:
            Sanitized filters
        """
        sanitized = {}
        allowed_filter_keys = [
            'projection_months', 'time_period_days', 'analysis_period_days', 'user_specific'
        ]
        
        for key, value in filters.items():
            # Only allow known filter keys
            if key not in allowed_filter_keys:
                logger.warning(f"Unknown filter key ignored: {key}")
                continue
            
            # Sanitize based on expected type
            if key in ['projection_months', 'time_period_days', 'analysis_period_days']:
                # Integer filters
                if isinstance(value, int):
                    sanitized[key] = max(1, min(value, 365))  # Clamp between 1 and 365
                elif isinstance(value, str):
                    try:
                        sanitized[key] = max(1, min(int(value), 365))
                    except ValueError:
                        logger.warning(f"Invalid integer value for {key}, using default")
            
            elif key == 'user_specific':
                # Boolean filter
                if isinstance(value, bool):
                    sanitized[key] = value
                elif isinstance(value, str):
                    sanitized[key] = value.lower() in ['true', '1', 'yes']
                else:
                    sanitized[key] = bool(value)
            
            else:
                # For any other filters, apply string sanitization if it's a string
                if isinstance(value, str):
                    try:
                        sanitized[key] = self._sanitize_string_input(value, max_length=50)
                    except ValidationError:
                        logger.warning(f"Filter value for {key} failed sanitization, skipping")
                else:
                    sanitized[key] = value
        
        return sanitized
    
    def _validate_and_sanitize_date_range(self, date_range: Dict[str, str]) -> Dict[str, str]:
        """
        Validate and sanitize date range format and logic
        
        Args:
            date_range: Dictionary with start_date and end_date
        
        Returns:
            Validated and sanitized date range
        
        Raises:
            ValidationError: If date range is invalid
        """
        if not isinstance(date_range, dict):
            raise ValidationError(
                "date_range must be a dictionary", 
                details={'provided_type': type(date_range).__name__},
                field='date_range'
            )
        
        start_date = date_range.get('start_date')
        end_date = date_range.get('end_date')
        
        if not start_date or not end_date:
            raise ValidationError(
                "date_range must include both start_date and end_date",
                details={'has_start_date': bool(start_date), 'has_end_date': bool(end_date)},
                field='date_range'
            )
        
        # Sanitize date strings
        start_date = self._sanitize_string_input(start_date, max_length=10)
        end_date = self._sanitize_string_input(end_date, max_length=10)
        
        # Validate date format
        try:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        except ValueError as e:
            raise ValidationError(
                "Dates must be in YYYY-MM-DD format",
                details={'start_date': start_date, 'end_date': end_date, 'error': str(e)},
                field='date_range'
            )
        
        # Validate date logic
        if start_dt > end_dt:
            raise ValidationError(
                "start_date must be before or equal to end_date",
                details={'start_date': start_date, 'end_date': end_date},
                field='date_range'
            )
        
        # Check if dates are not too far in the future
        now = datetime.now()
        if start_dt > now:
            raise ValidationError(
                "start_date cannot be in the future",
                details={'start_date': start_date, 'current_date': now.strftime('%Y-%m-%d')},
                field='date_range'
            )
        
        # Limit date range to prevent excessive data processing
        days_diff = (end_dt - start_dt).days
        if days_diff > 365:
            raise ValidationError(
                "Date range cannot exceed 365 days",
                details={'requested_days': days_diff, 'max_days': 365},
                field='date_range'
            )
        
        return {'start_date': start_date, 'end_date': end_date}
    
    def _apply_rbac_filtering(self, request_data: Dict[str, Any], user_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply role-based access control and data filtering based on role and tenant_id
        
        Args:
            request_data: Validated request data
            user_context: User context from JWT
        
        Returns:
            Filtered request data based on user role
        
        Raises:
            AuthorizationError: If user lacks required permissions
        """
        user_role = user_context['role']
        tenant_id = user_context['tenant_id']
        
        # Apply role-specific filtering
        filtered_request = request_data.copy()
        
        # Platform Admin Access
        if user_role == 'platform_admin':
            if tenant_id == 'all':
                # Platform-wide analysis across all tenants
                filtered_request['scope'] = 'platform'
                filtered_request['data_filter'] = {
                    'access_level': 'all_tenants',
                    'cross_tenant_access': True
                }
                filtered_request['tenant_id'] = 'all'
            else:
                # Platform admin viewing specific tenant
                if not self._validate_tenant_access(tenant_id, user_role):
                    raise AuthorizationError("Access denied to specified tenant")
                
                filtered_request['scope'] = 'tenant'
                filtered_request['tenant_id'] = tenant_id
                filtered_request['data_filter'] = {
                    'tenant_id': tenant_id,
                    'access_level': 'full_tenant',
                    'admin_view': True
                }
        
        # Tenant Admin Access
        elif user_role == 'tenant_admin':
            # Validate tenant access
            if not self._validate_tenant_access(tenant_id, user_role):
                raise AuthorizationError("Access denied to specified tenant")
            
            # Prevent cross-tenant access for tenant admins
            if tenant_id == 'all':
                raise AuthorizationError("Cross-tenant access not allowed for tenant admins")
            
            # Tenant admins can access full tenant data
            filtered_request['scope'] = 'tenant'
            filtered_request['tenant_id'] = tenant_id
            filtered_request['data_filter'] = {
                'tenant_id': tenant_id,
                'access_level': 'full_tenant'
            }
        
        # Tenant User Access
        elif user_role == 'tenant_user':
            # Validate tenant access
            if not self._validate_tenant_access(tenant_id, user_role):
                raise AuthorizationError("Access denied to specified tenant")
            
            # Prevent cross-tenant access for tenant users
            if tenant_id == 'all':
                raise AuthorizationError("Cross-tenant access not allowed for tenant users")
            
            # Tenant users can only access their own data
            filtered_request['scope'] = 'user'
            filtered_request['tenant_id'] = tenant_id
            filtered_request['user_id'] = user_context['user_id']
            filtered_request['data_filter'] = {
                'tenant_id': tenant_id,
                'user_id': user_context['user_id'],
                'access_level': 'user_only'
            }
        
        # Invalid role
        else:
            raise AuthorizationError(f"Invalid role: {user_role}")
        
        # Log RBAC filtering
        logger.info(
            "rbac_filtering_applied",
            extra={
                'tenant_id': tenant_id,
                'user_role': user_role,
                'scope': filtered_request['scope']
            }
        )
        
        return filtered_request
    
    def _validate_tenant_access(self, tenant_id: str, user_role: str) -> bool:
        """
        Validate that user has access to the specified tenant
        
        Args:
            tenant_id: Target tenant ID ('all' for platform-wide access)
            user_role: User's role
        
        Returns:
            True if access is allowed
        
        Raises:
            DataNotFoundError: If tenant is not found
            AuthorizationError: If access is denied
        """
        try:
            # Platform admins have access to all tenants
            if user_role == 'platform_admin':
                if tenant_id == 'all':
                    return True
            
            # Skip validation for cross-tenant requests
            if tenant_id == 'all':
                raise AuthorizationError(
                    "Cross-tenant access not allowed for this role",
                    details={'user_role': user_role, 'required_role': 'platform_admin'}
                )
            
            # Verify tenant exists and is active
            response = self.tenants_table.get_item(Key={'tenant_id': tenant_id})
            if 'Item' not in response:
                raise DataNotFoundError(
                    f"Tenant not found: {tenant_id}",
                    details={'tenant_id': tenant_id},
                    resource_type='tenant'
                )
            
            tenant = response['Item']
            tenant_status = tenant.get('status', 'unknown')
            
            if tenant_status != 'active':
                raise AuthorizationError(
                    f"Tenant is not active: {tenant_status}",
                    details={'tenant_id': tenant_id, 'status': tenant_status}
                )
            
            return True
            
        except (DataNotFoundError, AuthorizationError):
            raise
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'UNKNOWN')
            logger.error(f"AWS error validating tenant access: {error_code}")
            
            if error_code == 'ResourceNotFoundException':
                raise DataNotFoundError(
                    f"Tenant table not found",
                    details={'tenant_id': tenant_id, 'aws_error': error_code},
                    resource_type='tenant_table'
                )
            else:
                raise AuthorizationError(
                    "Unable to validate tenant access due to service error",
                    details={'tenant_id': tenant_id, 'aws_error': error_code}
                )
        except Exception as e:
            logger.error(f"Unexpected error validating tenant access: {str(e)}")
            raise AuthorizationError(
                "Unable to validate tenant access",
                details={'tenant_id': tenant_id, 'error_type': type(e).__name__}
            )
    
    def _invoke_strands_agent(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Invoke Strands Bedrock agent with validated input
        
        Args:
            request_data: Processed request data with query parameters
        
        Returns:
            Agent response data with calculated metrics and insights
        
        Raises:
            BedrockAgentError: If agent invocation fails
        """
        try:
            # Prepare agent input
            agent_input = self._prepare_agent_input(request_data)
            
            # Generate stateless session ID
            session_id = f"usage-insights-{uuid.uuid4().hex[:8]}-{int(time.time())}"
            
            # Log agent request
            logger.info(f"=== AGENT REQUEST START ===")
            logger.info(f"Session ID: {session_id}")
            logger.info(f"Agent Input: {json.dumps(agent_input, indent=2, default=str)}")
            logger.info(f"=== AGENT REQUEST END ===")
            
            # Invoke Strands Bedrock agent
            response = self.strands_client.invoke_agent(
                input_text=json.dumps(agent_input),
                session_id=session_id
            )
            
            # Process streaming response
            agent_response = self._process_agent_response(response, session_id, agent_input)
            
            logger.info(f"=== AGENT RESPONSE START ===")
            logger.info(f"Response keys: {list(agent_response.keys()) if isinstance(agent_response, dict) else 'Not a dict'}")
            logger.info(f"=== AGENT RESPONSE END ===")
            
            return agent_response
            
        except BedrockAgentError:
            raise
        except Exception as e:
            logger.error(f"Unexpected agent error: {str(e)}", exc_info=True)
            raise BedrockAgentError(f"Unexpected agent error: {str(e)}")
    
    def _prepare_agent_input(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare input for Strands Bedrock agent based on analysis type
        
        Args:
            request_data: Processed request data
        
        Returns:
            Agent input structure with query parameters
        """
        analysis_type = request_data['analysis_type']
        
        # Base input with DynamoDB table names for agent to query
        base_input = {
            'special_instruction': "IMPORTANT: Respond ONLY valid JSON Format as per instructions. Also make sure you MUST respond within 10 seconds",
            'tenant_id': request_data['tenant_id'],
            'date_range': request_data['date_range'],
            'user_role': request_data['user_role'],
            'scope': request_data['scope'],
            'data_filter': request_data.get('data_filter', {})
        }
        
        if analysis_type == 'ttv':
            return {
                'action': 'calculate_time_to_value'
                # TODO: Uncomment the 'instructions' key below to provide analysis requirements and JSON structure guidance to the agent
                ,'instructions': '''TIME TO VALUE (TTV) ANALYSIS

                ANALYSIS REQUIREMENTS:
                - Compare each tenant's TTV vs platform benchmarks
                - Identify best/worst performers
                - Segment by tier
                - Flag tenants with no interaction
                - Calculate standard deviations from mean
                - Use percentile rankings

                "Response JSON": Return ONLY a JSON object in this exact format.
                {
                  "analysis_type": "time_to_value",
                  "timestamp": "ISO 8601 string",
                  "summary": {
                    "requested_tenant_id": "string",
                    "tenants_analyzed": number,
                    "platform_benchmark": {
                      "mean_ttv_days": number,
                      "median_ttv_days": number,
                      "percentile_25": number,
                      "percentile_75": number,
                      "percentile_90": number
                    }
                  },
                  "tenant_analysis": [
                    {
                      "tenant_id": "string",
                      "tenant_name": "string",
                      "tier": "string",
                      "ttv_days": number,
                      "performance_vs_platform": "above_average|below_average|average",
                      "percentile_rank": number,
                      "comparison_to_mean": "string",
                      "comparison_to_tier": "string",
                      "status": "string",
                      "insights": ["string"]
                    }
                  ],
                  "tier_breakdown": {
                    "basic": {"count": number, "mean_ttv": number, "median_ttv": number},
                    "premium": {"count": number, "mean_ttv": number, "median_ttv": number}
                  },
                  "key_findings": ["string"],
                  "recommendations": [
                    {
                      "priority": "critical|high|medium|low",
                      "target": "string",
                      "action": "string",
                      "rationale": "string",
                      "expected_impact": "string",
                      "timeline": "string"
                    }
                  ]
                }
                '''
                ,**base_input

            }
        
        elif analysis_type == 'cltv':
            projection_months = request_data.get('filters', {}).get('projection_months', 12)
            return {
                'action': 'project_customer_lifetime_value'
                # TODO: Uncomment the 'instructions' key below to provide analysis requirements and JSON structure guidance to the agent
                ,'instructions': '''CUSTOMER LIFETIME VALUE (CLTV) ANALYSIS

                CALCULATION APPROACH:
                - Project revenue over 12-month horizon
                - Use cohort analysis by tier and onboarding period
                - Factor in historical retention metrics
                - Calculate confidence intervals for projections
                
                ANALYSIS REQUIREMENTS:
                - Calculate projected CLTV for each tenant
                - Segment by tier (Basic vs Premium)
                - Identify high-value customer segments
                - Compare actual vs projected performance
                - Rank tenants by CLTV potential
                - Generate retention recommendations
                - Ensure insights and recommendations are not more than 3, and within 10 tokens each
               
                "Response JSON": Return ONLY a JSON object in this exact format.
                {
                  "analysis_type": "customer_lifetime_value",
                  "timestamp": "ISO 8601 string",
                  "tenant_id": "string",
                  "data": {
                    "tenant_projections": [
                      {
                        "tenant_name": "string",
                        "tier": "basic|premium|enterprise|unknown",
                        "retention_rate": number,
                        "projected_cltv_12m": number,
                        "segment": "high_value|medium_value|at_risk"
                      }
                    ],
                    "segments": {
                      "high_value": {"count": number, "avg_cltv": number},
                      "medium_value": {"count": number, "avg_cltv": number},
                      "at_risk": {"count": number, "avg_cltv": number}
                    }
                  },
                  "recommendations": [
                    {
                      "priority": "critical|high|medium|low",
                      "action": "string",
                      "rationale": "string"
                    }
                  ]
                }
                ''',
                **base_input,
                'projection_months': projection_months
            }
        
        elif analysis_type == 'feature_adoption':
            time_period_days = request_data.get('filters', {}).get('time_period_days', 30)
            return {
                'action': 'analyze_feature_adoption_rates'
                # TODO: Uncomment the 'instructions' key below to provide analysis requirements and JSON structure guidance to the agent
                ,'instructions': '''FEATURE ADOPTION ANALYSIS
                
                FEATURE ADOPTION RATE CALCULATION:
                - adoption_rate = (unique_users_using_feature / total_active_users) * 100
                - Segment by tier (Basic vs Premium)
                - Compare adoption across features
                
                ANALYSIS REQUIREMENTS:
                - Calculate adoption rate for each feature
                - Identify features with highest and lowest adoption
                - Compare adoption between Basic and Premium tiers
                - Analyze adoption trends over time
                - Identify correlation between feature adoption and tenant success
                - Generate recommendations for improving adoption

                "Response JSON": Return ONLY a JSON object in this exact format.
                {
                  "analysis_type": "feature_adoption",
                  "timestamp": "ISO 8601 string",
                  "tenant_id": "string",
                  "data": {
                    "features": [
                      {
                        "feature_name": "string",
                        "adoption_rate": number,
                        "feature_users": number,
                        "active_users": number
                      }
                    ]
                  },
                  "recommendations": [
                    {
                      "priority": "critical|high|medium|low",
                      "action": "string",
                      "rationale": "string"
                    }
                  ]
                }
                ''',
                **base_input,
                'time_period_days': time_period_days
            }
        
        elif analysis_type == 'engagement':
            return {
                'action': 'calculate_engagement_scores'
                # TODO: Uncomment the 'instructions' key below to provide analysis requirements and JSON structure guidance to the agent
                ,'instructions': '''USER ENGAGEMENT ANALYSIS
               
                SCORING FORMULA:
                engagement_score = (activity_frequency * 0.40) + (feature_diversity * 0.40) + (request_volume_score * 0.20)
                where request_volume_score = min(avg_requests_per_day / 100 * 100, 100)
                
                TIERS:
                - high: score > 70
                - medium: 40 ≤ score ≤ 70
                - low: score < 40
                
                ANALYSIS REQUIREMENTS:
                - Calculate engagement score for each tenant
                - Calculate platform benchmarks from all scores
                - Compare each tenant to benchmarks
                - Generate percentile rankings

                "Response JSON": Return ONLY a JSON object in this exact format.
                {
                  "analysis_type": "user_engagement",
                  "timestamp": "ISO 8601 string",
                  "summary": {
                    "platform_benchmark": {
                      "mean_engagement_score": number,
                      "median_engagement_score": number
                    }
                  },
                  "tenant_analysis": [
                    {
                      "tenant_id": "string",
                      "tenant_name": "string",
                      "tier": "string",
                      "engagement_score": number,
                      "performance_vs_platform": "above_average|below_average|average|no_activity",
                      "percentile_rank": number,
                      "comparison_to_mean": "string",
                      "comparison_to_tier": "string",
                      "status": "active|no_activity",
                      "metrics": {
                        "total_requests": number,
                        "unique_users": number,
                        "unique_days_active": number,
                        "activity_frequency": number,
                        "feature_diversity": number,
                        "avg_requests_per_day": number,
                        "features_list": ["string"]
                      },
                      "insights": ["string"]
                    }
                  ],
                  "recommendations": [
                    {
                      "priority": "critical|high|medium|low",
                      "action": "string",
                      "rationale": "string"
                    }
                  ]
                }
                ''',
                **base_input,
                'user_id': request_data.get('user_id')
            }
        
        elif analysis_type == 'at_risk':
            analysis_period_days = request_data.get('filters', {}).get('analysis_period_days', 120)
            return {
                'action': 'identify_at_risk_features'
                # TODO: Uncomment the 'instructions' key below to provide analysis requirements and JSON structure guidance to the agent
                ,'instructions': '''AT-RISK FEATURES ANALYSIS

                CLASSIFICATION:
                - AT-RISK: decline_rate < -25% OR adoption_rate < 15%
                - CRITICAL: both conditions met
                - MODERATE: one condition met
                
                ANALYSIS REQUIREMENTS:
                - Calculate decline_rate and adoption_rate
                - Analyze monthly breakdown for trend patterns
                - Identify specific months with steepest decline
                - Rank by severity
                - DO NOT return any feature analysis raw data

                "Response JSON": Return ONLY a JSON object in this exact format.
                {
                  "analysis_type": "at_risk_features",
                  "timestamp": "ISO 8601 string",
                  "summary": {
                    "total_features_analyzed": number,
                    "at_risk_features_count": number,
                    "critical_risk_count": number,
                    "moderate_risk_count": number
                  },
                  "recommendations": [
                    {
                      "feature_name": "string",
                      "priority": "critical|high|medium|low",
                      "action": "string",
                      "rationale": "string",
                      "expected_impact": "string",
                      "timeline": "string"
                    }
                  ]
                }
               ''',
                **base_input,
                'analysis_period_days': analysis_period_days
            }
        
        else:
            raise ValidationError(f"Unsupported analysis type: {analysis_type}")
    
    def _retry_agent_with_json_instruction(
        self, session_id: str, agent_input: Dict[str, Any], retry_count: int
    ) -> Dict[str, Any]:
        """
        Retry agent invocation with special JSON formatting instructions
        
        Args:
            session_id: Session ID to maintain conversation context
            agent_input: Original agent input
            retry_count: Current retry attempt count
        
        Returns:
            Processed response from retry attempt
        
        Raises:
            BedrockAgentError: If retry fails
        """
        logger.warning(
            f"Retrying agent invocation with JSON format instructions (attempt {retry_count + 1}/1)"
        )
        
        # Add special instruction to return JSON without invoking tools
        retry_input = {}
        retry_input['special_instruction'] = (
            "IMPORTANT: Your previous response could not be parsed as JSON. "
            "Please respond with ONLY valid JSON in the previously specified format. "
            "Do NOT invoke any tools. Do NOT include any text outside the JSON object. "
            "Do NOT wrap the response in markdown code blocks."
        )
        
        # Invoke agent again with same session
        logger.info(f"=== RETRY AGENT REQUEST START ===")
        logger.info(f"Session ID: {session_id}")
        logger.info(f"Retry Input: {json.dumps(retry_input, indent=2, default=str)}")
        logger.info(f"=== RETRY AGENT REQUEST END ===")
        
        retry_response = self.strands_client.invoke_agent(
            input_text=json.dumps(retry_input), session_id=session_id
        )
        
        # Process retry response recursively with incremented retry count
        return self._process_agent_response(
            retry_response, session_id, agent_input, retry_count + 1
        )

    def _process_agent_response(
        self,
        response,
        session_id: str = None,
        agent_input: Dict[str, Any] = None,
        retry_count: int = 0,
    ) -> Dict[str, Any]:
        """
        Process streaming response from Bedrock agent with retry logic for JSON decode errors
        
        Args:
            response: Bedrock agent response stream
            session_id: Session ID for retry attempts
            agent_input: Original agent input for retry attempts
            retry_count: Current retry attempt count
        
        Returns:
            Processed response data
        """
        completion = ""
        chunk_count = 0
        json_format_detected = None
        
        try:
            # Process streaming response - Bedrock returns EventStream
            if 'completion' in response:
                event_stream = response['completion']
                
                for event in event_stream:
                    # Handle different event types
                    if 'chunk' in event:
                        chunk = event['chunk']
                        if 'bytes' in chunk:
                            chunk_text = chunk['bytes'].decode('utf-8')
                            completion += chunk_text
                            chunk_count += 1
                            
                            # Early detection: Check if response starts as JSON in first 2 chunks
                            if chunk_count <= 2 and json_format_detected is None:
                                stripped_completion = completion.strip()
                                
                                # Check for JSON start patterns
                                if stripped_completion.startswith('{'):
                                    json_format_detected = True
                                    logger.info(
                                        f"✓ JSON format detected at chunk {chunk_count} - "
                                        f"Response starts with '{{'"
                                    )
                                elif stripped_completion.startswith('```json'):
                                    json_format_detected = True
                                    logger.info(
                                        f"✓ JSON format detected at chunk {chunk_count} - "
                                        f"Response starts with markdown JSON block"
                                    )
                                elif len(stripped_completion) > 10:
                                    # If we have enough content and it doesn't start with JSON
                                    json_format_detected = False
                                    logger.warning(
                                        f"✗ Non-JSON format detected at chunk {chunk_count} - "
                                        f"Response starts with: '{stripped_completion[:50]}...'"
                                    )
                                    
                                    # Early retry if non-JSON detected and this is first attempt
                                    if retry_count == 0 and session_id and agent_input:
                                        logger.warning(
                                            "Triggering early retry due to non-JSON format detection"
                                        )
                                        # Stop processing current stream and retry immediately
                                        return self._retry_agent_with_json_instruction(
                                            session_id, agent_input, retry_count
                                        )
                    
                    elif 'trace' in event:
                        # Log trace events for debugging
                        trace = event['trace']
                        if isinstance(trace, dict) and 'orchestrationTrace' in trace:
                            orch_trace = trace['orchestrationTrace']
                            logger.debug(
                                f"Orchestration trace: {json.dumps(orch_trace, indent=2, default=str)}"
                            )
            
            # Check if completion is empty
            if not completion or len(completion.strip()) == 0:
                logger.error("Agent returned empty completion")
                raise BedrockAgentError("Agent returned empty response")
            
            # Clean up completion - remove markdown code blocks if present
            cleaned_completion = completion.strip()
            if cleaned_completion.startswith('```json'):
                cleaned_completion = cleaned_completion[7:]
            if cleaned_completion.startswith('```'):
                cleaned_completion = cleaned_completion[3:]
            if cleaned_completion.endswith('```'):
                cleaned_completion = cleaned_completion[:-3]
            cleaned_completion = cleaned_completion.strip()
            
            # Parse agent response
            try:
                logger.info(f"cleaned response: {cleaned_completion}")
                parsed_response = json.loads(cleaned_completion)
                logger.info("Successfully parsed agent response as JSON")
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error: {str(e)}")
                
                # Retry once with special instructions if this is the first attempt
                if retry_count == 0 and session_id and agent_input:
                    return self._retry_agent_with_json_instruction(
                        session_id, agent_input, retry_count
                    )
                
                # If retry failed or this was already a retry, raise error
                logger.error(f"Failed to parse JSON after {retry_count + 1} attempt(s)")
                raise BedrockAgentError(f"Agent response is not valid JSON: {str(e)}")
            
            return parsed_response
            
        except BedrockAgentError:
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error processing agent response: {str(e)}", exc_info=True
            )
            raise BedrockAgentError(f"Error processing agent response: {str(e)}")
    
    def _extract_ai_insights(self, agent_response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract AI-generated insights from Strands agent response
        
        Args:
            agent_response: Raw agent response
        
        Returns:
            List of structured AI insights
        """
        try:
            # Extract recommendations from agent response
            recommendations = agent_response.get('recommendations', [])
            
            # Structure insights
            ai_insights = []
            
            for recommendation in recommendations:
                if isinstance(recommendation, dict):
                    ai_insights.append({
                        'type': 'recommendation',
                        'priority': recommendation.get('priority', 'medium'),
                        'action': recommendation.get('action', ''),
                        'rationale': recommendation.get('rationale', ''),
                        'impact': recommendation.get('impact', 'medium'),
                        'source': 'ai_analysis'
                    })
            
            return ai_insights
            
        except Exception as e:
            logger.warning(f"Failed to extract AI insights: {str(e)}")
            return []
    
    def _get_tenant_info(self, tenant_id: str) -> Dict[str, Any]:
        """
        Get basic tenant information for context
        
        Args:
            tenant_id: Tenant ID
        
        Returns:
            Tenant information
        """
        try:
            if tenant_id == 'all':
                return {'tenant_id': 'all', 'tier': 'platform', 'status': 'active'}
            
            response = self.tenants_table.get_item(Key={'tenant_id': tenant_id})
            if 'Item' in response:
                tenant = response['Item']
                return {
                    'tenant_id': tenant_id,
                    'tier': tenant.get('tier', 'basic'),
                    'status': tenant.get('status', 'active'),
                    'created_date': tenant.get('created_date', '')
                }
        except Exception as e:
            logger.warning(f"Failed to get tenant info: {str(e)}")
        
        return {'tenant_id': tenant_id, 'tier': 'basic', 'status': 'active'}
    
    def _format_response(self, agent_response: Dict[str, Any], ai_insights: List[Dict[str, Any]], 
                        tenant_info: Dict[str, Any], user_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format agent response for API consumption
        
        Args:
            agent_response: Raw agent response with metrics and analysis
            ai_insights: Extracted AI insights
            tenant_info: Basic tenant information
            user_context: User context for response customization
        
        Returns:
            Formatted API response
        """
        return {
            'analysis_type': agent_response.get('analysis_type', 'unknown'),
            'timestamp': agent_response.get('timestamp', datetime.now().isoformat()),
            'tenant_id': user_context['tenant_id'],
            'data': agent_response.get('data', {}),
            'summary': agent_response.get('summary', {}),
            'insights': ai_insights,
            'tenant_analysis': agent_response.get('tenant_analysis', []),
            'recommendations': agent_response.get('recommendations', []),
            'metadata': {
                'analysis_timestamp': datetime.now().isoformat(),
                'user_role': user_context['role'],
                'agent_id': self.agent_id,
                'tenant_info': tenant_info
            },
            'status': 'success'
        }
    
    def _log_analysis_completion(self, request_data: Dict[str, Any], user_context: Dict[str, Any], 
                                 response_time_ms: int, request_id: str, success: bool, error: str = None):
        """
        Log analysis completion with structured logging
        
        Args:
            request_data: Request data
            user_context: User context
            response_time_ms: Response time in milliseconds
            request_id: Request ID
            success: Whether analysis succeeded
            error: Error message if failed
        """
        logger.info(
            "analysis_completed",
            extra={
                'request_id': request_id,
                'analysis_type': request_data.get('analysis_type'),
                'tenant_id': user_context.get('tenant_id'),
                'user_role': user_context.get('role'),
                'response_time_ms': response_time_ms,
                'success': success,
                'error': error
            }
        )
    
    def _create_error_response(self, error_code: str, message: str, status_code: int, 
                              details: Dict[str, Any] = None, request_id: str = None) -> Dict[str, Any]:
        """
        Create structured error response conforming to JSON RFC 8259
        
        All error responses are valid JSON with proper character escaping.
        
        Args:
            error_code: Error code identifier
            message: User-friendly error message
            status_code: HTTP status code
            details: Additional error details
            request_id: Unique request identifier for tracking
        
        Returns:
            Formatted error response with valid JSON structure
        """
        # Escape special characters in message to ensure JSON validity
        escaped_message = self._escape_json_string(message)
        
        # Build error response with required top-level fields
        error_response = {
            'error': {
                'code': error_code,
                'message': escaped_message,
                'details': details or {},
                'timestamp': datetime.now().isoformat(),
                'request_id': request_id or str(uuid.uuid4())
            },
            'status': 'error',
            'status_code': status_code
        }
        
        # Validate JSON structure before returning
        try:
            # Ensure response can be serialized to JSON
            json.dumps(error_response)
        except (TypeError, ValueError) as e:
            logger.error(f"Error response is not valid JSON: {str(e)}")
            # Return a minimal valid JSON error response
            error_response = {
                'error': {
                    'code': 'JSON_SERIALIZATION_ERROR',
                    'message': 'An error occurred while formatting the error response',
                    'timestamp': datetime.now().isoformat(),
                    'request_id': request_id or str(uuid.uuid4())
                },
                'status': 'error',
                'status_code': 500
            }
        
        return error_response
    
    def _escape_json_string(self, text: str) -> str:
        """
        Escape special characters in string values to maintain JSON validity
        
        Args:
            text: String to escape
        
        Returns:
            Escaped string safe for JSON
        """
        if not isinstance(text, str):
            return str(text)
        
        # Replace special characters that need escaping in JSON
        replacements = {
            '\\': '\\\\',  # Backslash
            '"': '\\"',    # Double quote
            '\n': '\\n',   # Newline
            '\r': '\\r',   # Carriage return
            '\t': '\\t',   # Tab
            '\b': '\\b',   # Backspace
            '\f': '\\f',   # Form feed
        }
        
        for old, new in replacements.items():
            text = text.replace(old, new)
        
        return text



def lambda_handler(event, context):
    """
    AWS Lambda handler function for usage insights API
    
    Handles API Gateway requests with JWT authentication and role-based access control.
    
    Args:
        event: Lambda event object from API Gateway
        context: Lambda context object
    
    Returns:
        HTTP response with analysis results or error
    """
    # CORS headers to be used in all responses
    cors_headers = {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization, tenant-id, tier-name'
    }
    
    try:
        # Initialize service
        service = UsageInsightsService()
        
        # Extract request data
        http_method = event.get('httpMethod', 'POST')
        
        if http_method == 'GET':
            # For GET requests, extract parameters from query string
            query_params = event.get('queryStringParameters') or {}
            request_data = {
                'analysis_type': query_params.get('analysis_type', 'ttv'),
                'date_range': None,  # Use default
                'filters': {}
            }
        else:
            # For POST requests, extract from body
            body = event.get('body', '{}')
            if isinstance(body, str):
                request_data = json.loads(body)
            else:
                request_data = body
        
        # Extract and validate user context from JWT (via authorizer)
        user_context = _extract_user_context(event)
        
        # Check if this is a test/integration environment (no authorizer)
        request_context = event.get('requestContext', {})
        authorizer_context = request_context.get('authorizer', {})
        
        # Skip authentication for integration testing when no authorizer is present
        if not authorizer_context and not user_context.get('tenant_id'):
            # Set default context for integration testing
            user_context = {
                'tenant_id': 'all',
                'role': 'platform_admin',
                'user_id': 'integration_test',
                'tier_name': 'premium'
            }
            logger.info("Using integration testing context (no authorizer detected)")
        else:
            # Validate authentication and authorization
            auth_validation = _validate_authentication(user_context)
            if auth_validation['error']:
                return _create_auth_error_response(
                    auth_validation['error'], 
                    auth_validation['status_code'],
                    auth_validation.get('message')
                )
        
        # Process analysis request
        enhanced_user_context = {
            **user_context,
            'request_id': str(uuid.uuid4())
        }
        
        result = service.analyze_insights(request_data, enhanced_user_context)
        
        # Return response with proper HTTP status code
        status_code = result.get('status_code', 200)
        return {
            'statusCode': status_code,
            'headers': cors_headers,
            'body': json.dumps(result)
        }
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {str(e)}")
        return {
            'statusCode': 400,
            'headers': cors_headers,
            'body': json.dumps({
                'error': {
                    'code': 'INVALID_JSON',
                    'message': 'Invalid JSON in request body',
                    'details': {'error': str(e)},
                    'timestamp': datetime.now().isoformat()
                },
                'status': 'error'
            })
        }
    except Exception as e:
        logger.error(f"Unexpected error in lambda_handler: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({
                'error': {
                    'code': 'INTERNAL_ERROR',
                    'message': 'An unexpected error occurred',
                    'details': {'error': str(e), 'type': type(e).__name__},
                    'timestamp': datetime.now().isoformat()
                },
                'status': 'error'
            })
        }



def _extract_user_context(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract user context from JWT request context
    
    Args:
        event: Lambda event object
    
    Returns:
        User context dictionary with tenant_id, role, user_id, tier_name
    """
    # Extract from authorizer context (JWT validation results)
    request_context = event.get('requestContext', {})
    authorizer_context = request_context.get('authorizer', {})
    
    # Extract from headers (for explicit tenant context)
    headers = event.get('headers', {})
    
    # Build user context with default values for admin panel
    user_context = {
        'tenant_id': headers.get('tenant-id') or headers.get('tenant_id') or authorizer_context.get('tenant_id') or 'all',
        'role': authorizer_context.get('role') or 'platform_admin',
        'user_id': authorizer_context.get('user_id') or 'integration_test',
        'tier_name': headers.get('tier-name') or headers.get('tier_name') or authorizer_context.get('tier') or 'premium'
    }
    
    # For platform admins, allow cross-tenant access via 'all' tenant_id
    if user_context['role'] == 'platform_admin':
        if headers.get('tenant-id') == 'all' or headers.get('tenant_id') == 'all':
            user_context['tenant_id'] = 'all'
    
    return user_context



def _validate_authentication(user_context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate authentication and authorization based on user role
    
    Args:
        user_context: User context from JWT
    
    Returns:
        Dictionary with 'error', 'status_code', and 'message' keys
    """
    role = user_context.get('role')
    tenant_id = user_context.get('tenant_id')
    
    # Validate required fields
    if not role:
        return {'error': 'MISSING_ROLE', 'status_code': 401, 'message': 'User role is required'}
    
    if not tenant_id:
        return {'error': 'MISSING_TENANT_ID', 'status_code': 400, 'message': 'tenant_id is required'}
    
    # Validate role is one of the allowed roles
    valid_roles = ['platform_admin', 'tenant_admin', 'tenant_user']
    if role not in valid_roles:
        return {
            'error': 'INVALID_ROLE',
            'status_code': 403,
            'message': f'Invalid role: {role}. Must be one of: {", ".join(valid_roles)}'
        }
    
    # Platform admin validation
    if role == 'platform_admin':
        # Platform admins can access cross-tenant data or specific tenants
        if tenant_id == 'all':
            pass  # Valid for platform-wide analysis
        elif not tenant_id or tenant_id == '':
            return {
                'error': 'INVALID_TENANT_ID', 
                'status_code': 400, 
                'message': 'Valid tenant_id or "all" required for platform_admin'
            }
    
    # Tenant admin validation
    elif role == 'tenant_admin':
        # Tenant admins require specific tenant ID (no cross-tenant access)
        if not tenant_id or tenant_id == 'all':
            return {
                'error': 'TENANT_ISOLATION_VIOLATION', 
                'status_code': 403, 
                'message': 'Tenant admins require specific tenant_id'
            }
    
    # Tenant user validation
    elif role == 'tenant_user':
        # Tenant users require specific tenant ID (no cross-tenant access)
        if not tenant_id or tenant_id == 'all':
            return {
                'error': 'TENANT_ISOLATION_VIOLATION', 
                'status_code': 403, 
                'message': 'Tenant users require specific tenant_id'
            }
        
        # Tenant users need user_id for data filtering
        if not user_context.get('user_id'):
            return {
                'error': 'MISSING_USER_ID', 
                'status_code': 400, 
                'message': 'user_id is required for tenant_user role'
            }
    
    # No errors
    return {'error': None, 'status_code': 200}


def _create_auth_error_response(error_code: str, status_code: int, message: str = None, 
                              details: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Create standardized authentication/authorization error response
    
    Args:
        error_code: Error code identifier
        status_code: HTTP status code
        message: Optional custom error message
        details: Additional error details
    
    Returns:
        Formatted error response
    """
    error_messages = {
        'MISSING_ROLE': 'User role is required in JWT token',
        'MISSING_TENANT_ID': 'tenant_id is required in headers or JWT context',
        'MISSING_USER_ID': 'user_id is required for tenant_user role',
        'INVALID_ROLE': 'Invalid user role',
        'TENANT_ISOLATION_VIOLATION': 'Cross-tenant access not allowed for this role',
        'INVALID_TENANT_ID': 'Invalid tenant_id format',
        'INVALID_JSON': 'Invalid JSON in request body',
        'INTERNAL_ERROR': 'An unexpected error occurred'
    }
    
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization, tenant-id, tier-name'
        },
        'body': json.dumps({
            'error': {
                'code': error_code,
                'message': message or error_messages.get(error_code, 'Authentication error'),
                'details': details or {},
                'timestamp': datetime.now().isoformat(),
                'request_id': str(uuid.uuid4())
            },
            'status': 'error'
        })
    }
