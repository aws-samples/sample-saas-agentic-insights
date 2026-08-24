from typing import Any, Dict

import jwt_validator


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Validate a bearer token and scope access to the requested API method."""
    try:
        token = event['authorizationToken'].split()
        if len(token) != 2 or token[0] != 'Bearer':
            raise Exception('Authorization header should have a format Bearer <JWT> Token')
        
        jwt_bearer_token = token[1]
        method_arn = event['methodArn']
        
        print(f"Method ARN: {method_arn}")
        
        input_details = {
            'jwtToken': jwt_bearer_token
        }
        
        response = jwt_validator.validateJWT(input_details)
        
        if response is False:
            print('Unauthorized')
            raise Exception('Unauthorized')
        
        tenant_id = response.get("custom:tenant_id") or response.get("custom:tenantId")
        role = response.get("custom:role") or response.get("custom:userRole", "tenant_user")
        tier = response.get("custom:tier") or response.get("custom:tenantTier")
        user_id = response.get("sub", "unknown")
        
        print(f"Authorized user {user_id} for tenant {tenant_id}")
        
        if not tenant_id:
            raise Exception('Missing tenant_id in token')
        if not tier:
            raise Exception('Missing tier in token')
        
        return generate_policy(user_id, 'Allow', method_arn, {
            'tenant_id': tenant_id,
            'role': role,
            'tier': tier,
            'user_id': user_id
        })
    except Exception as e:
        print(f"Authorization error: {str(e)}")
        return generate_policy('user', 'Deny', event.get('methodArn', '*'))


def generate_policy(
    principal_id: str,
    effect: str,
    resource: str,
    context: Dict[str, Any] = None
) -> Dict[str, Any]:
    """Generate an API Gateway IAM authorizer policy."""
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
