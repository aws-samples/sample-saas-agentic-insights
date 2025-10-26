import json
import os
from typing import Dict, Any
import jwt_validator

def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Lambda authorizer with standard JWT validation but previous context structure"""
    try:
        # Extract token (following standard pattern)
        token = event['authorizationToken'].split(" ")
        if token[0] != 'Bearer':
            raise Exception('Authorization header should have a format Bearer <JWT> Token')
        
        jwt_bearer_token = token[1]
        method_arn = event['methodArn']
        
        print(f"Method ARN: {method_arn}")
        
        # Validate JWT using standard pattern
        input_details = {
            'jwtToken': jwt_bearer_token
        }
        
        response = jwt_validator.validateJWT(input_details)
        
        # Check validation result (following standard pattern)
        if response == False:
            print('Unauthorized')
            raise Exception('Unauthorized')
        
        print(f"Validated claims: {json.dumps(response, indent=2, default=str)}")
        
        # Extract claims (support both old and new field names)
        tenant_id = response.get("custom:tenant_id") or response.get("custom:tenantId")
        role = response.get("custom:role") or response.get("custom:userRole", "tenant_user")
        tier = response.get("custom:tier") or response.get("custom:tenantTier")
        user_id = response.get("sub", "unknown")
        
        print(f"Tenant ID: {tenant_id}, Role: {role}, Tier: {tier}")
        
        # Validate required fields
        if not tenant_id:
            raise Exception('Missing tenant_id in token')
        if not tier:
            raise Exception('Missing tier in token')
        
        # Generate allow policy with wildcard (same as before)
        if '/prod/' in method_arn:
            base_part, path_part = method_arn.split('/prod/', 1)
            path_segments = path_part.split('/', 1)
            if len(path_segments) >= 2:
                wildcard_arn = f"{base_part}/prod/*/{path_segments[1]}"
            else:
                wildcard_arn = f"{base_part}/prod/*"
        else:
            wildcard_arn = method_arn
        
        print(f"Wildcard ARN: {wildcard_arn}")
        
        # Use previous policy structure (not AuthPolicy class)
        policy = generate_policy(user_id, 'Allow', wildcard_arn, {
            'tenant_id': tenant_id,
            'role': role,
            'tier': tier,
            'user_id': user_id,
            'jwt_token': jwt_bearer_token  # Pass JWT token as before!
        })
        
        return policy
        
    except Exception as e:
        print(f"Authorization error: {str(e)}")
        # Return deny policy (same as before)
        return generate_policy('user', 'Deny', event['methodArn'])

def generate_policy(principal_id: str, effect: str, resource: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
    """Generate IAM policy for API Gateway (same as before)"""
    policy = {
        'principalId': principal_id,
        'policyDocument': {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Action': 'execute-api:Invoke',
                    'Effect': effect,
                    'Resource': resource
                }
            ]
        }
    }
    
    if context:
        policy['context'] = {k: str(v) for k, v in context.items()}
    
    return policy
