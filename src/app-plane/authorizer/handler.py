import json
import base64
import os
from typing import Dict, Any

# Updated: Fixed JWT import issue
def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Simple Lambda authorizer for API Gateway"""
    try:
        # Extract token from Authorization header
        token = event['authorizationToken']
        if token.startswith('Bearer '):
            token = token[7:]
        
        # Extract method ARN for policy generation
        method_arn = event['methodArn']
        
        print(f"Method ARN: {method_arn}")
        
        # Simple token validation - decode JWT payload without verification for demo
        # In production, you should properly verify the JWT signature
        try:
            # Split JWT token
            parts = token.split('.')
            if len(parts) != 3:
                raise Exception('Invalid token format')
            
            # Decode payload (add padding if needed)
            payload = parts[1]
            # Add padding if needed for base64 decoding
            missing_padding = len(payload) % 4
            if missing_padding:
                payload += '=' * (4 - missing_padding)
            
            decoded_payload = base64.urlsafe_b64decode(payload)
            claims = json.loads(decoded_payload.decode('utf-8'))
            
            # Extract tenant context
            tenant_id = claims.get('custom:tenant_id')
            role = claims.get('custom:role', 'tenant_user')
            
            print(f"Tenant ID: {tenant_id}, Role: {role}")
            
            if not tenant_id:
                raise Exception('Missing tenant_id in token')
            
            # Determine tier from issuer
            issuer = claims.get('iss', '')
            tier = 'premium' if 'yFhMg8tON' in issuer else 'basic'  # Premium pool ID check
            
            # Generate allow policy with wildcard for all HTTP methods
            # Convert specific method ARN to wildcard pattern
            # From: arn:aws:execute-api:region:account:api-id/stage/METHOD/resource/path
            # To:   arn:aws:execute-api:region:account:api-id/stage/*/resource/path
            
            # Split ARN into base and path parts
            if '/prod/' in method_arn:
                base_part, path_part = method_arn.split('/prod/', 1)
                # path_part is now: METHOD/resource/path
                path_segments = path_part.split('/', 1)
                if len(path_segments) >= 2:
                    # Replace METHOD with *
                    wildcard_arn = f"{base_part}/prod/*/{path_segments[1]}"
                else:
                    wildcard_arn = f"{base_part}/prod/*"
            else:
                wildcard_arn = method_arn
            
            print(f"Wildcard ARN: {wildcard_arn}")
            
            policy = generate_policy(claims.get('sub', 'user'), 'Allow', wildcard_arn, {
                'tenant_id': tenant_id,
                'role': role,
                'tier': tier,
                'user_id': claims.get('sub', 'unknown')
            })
            
            return policy
            
        except Exception as e:
            print(f"Token parsing error: {str(e)}")
            raise Exception('Invalid token')
        
    except Exception as e:
        print(f"Authorization error: {str(e)}")
        # Return deny policy
        return generate_policy('user', 'Deny', event['methodArn'])

def generate_policy(principal_id: str, effect: str, resource: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
    """Generate IAM policy for API Gateway"""
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
