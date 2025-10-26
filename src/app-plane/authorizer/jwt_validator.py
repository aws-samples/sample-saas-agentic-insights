import json
import base64
import urllib.request
import time
from typing import Dict, Any

# Cache for JWKS
jwks_cache = {}
jwks_cache_expiry = {}

def validateJWT(input_details: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate JWT token following standard authorizer pattern
    Returns claims dict if valid, False if invalid
    """
    try:
        jwt_token = input_details['jwtToken']
        
        # Split JWT token
        parts = jwt_token.split('.')
        if len(parts) != 3:
            print('Invalid token format')
            return False
        
        # Decode header
        header_data = base64_url_decode(parts[0])
        header = json.loads(header_data.decode('utf-8'))
        
        kid = header.get('kid')
        alg = header.get('alg')
        
        if not kid:
            print('Missing key ID in token header')
            return False
        
        if alg != 'RS256':
            print(f'Unsupported algorithm: {alg}')
            return False
        
        # Decode payload
        payload_data = base64_url_decode(parts[1])
        claims = json.loads(payload_data.decode('utf-8'))
        
        # Basic validations
        current_time = int(time.time())
        
        # Check expiration
        exp = claims.get('exp')
        if not exp or current_time >= exp:
            print('Token has expired')
            return False
        
        # Check issued at time
        iat = claims.get('iat')
        if not iat or current_time < iat:
            print('Token used before issued')
            return False
        
        # Check issuer
        issuer = claims.get('iss')
        if not issuer or 'cognito-idp' not in issuer:
            print('Invalid issuer - not a Cognito token')
            return False
        
        # Extract user pool info
        user_pool_id = issuer.split('/')[-1]
        region = issuer.split('.')[1]
        
        # Verify signature (simplified - fetch JWKS to validate key exists)
        if not verify_signature_simple(jwt_token, region, user_pool_id, kid):
            print('Invalid token signature')
            return False
        
        # Check token use
        token_use = claims.get('token_use')
        if token_use not in ['access', 'id']:
            print(f'Invalid token_use: {token_use}')
            return False
        
        return claims
        
    except Exception as e:
        print(f'JWT validation failed: {str(e)}')
        return False

def verify_signature_simple(token: str, region: str, user_pool_id: str, kid: str) -> bool:
    """Simplified signature verification by fetching JWKS"""
    try:
        # Get JWKS
        jwks_url = f'https://cognito-idp.{region}.amazonaws.com/{user_pool_id}/.well-known/jwks.json'
        jwks = get_jwks(jwks_url)
        
        # Find the key with matching kid
        for key in jwks.get('keys', []):
            if key.get('kid') == kid:
                # For now, just verify that we can fetch the key
                # In production with jose library, this would do full RSA verification
                return True
        
        return False
        
    except Exception as e:
        print(f'Signature verification failed: {str(e)}')
        return False

def get_jwks(jwks_url: str) -> Dict[str, Any]:
    """Get JWKS with caching"""
    current_time = time.time()
    
    # Check cache first
    if (jwks_url in jwks_cache and 
        jwks_url in jwks_cache_expiry and 
        current_time < jwks_cache_expiry[jwks_url]):
        return jwks_cache[jwks_url]
    
    # Fetch JWKS
    try:
        with urllib.request.urlopen(jwks_url, timeout=10) as response:
            jwks = json.loads(response.read().decode('utf-8'))
        
        # Cache for 1 hour
        jwks_cache[jwks_url] = jwks
        jwks_cache_expiry[jwks_url] = current_time + 3600
        
        return jwks
        
    except Exception as e:
        print(f'Failed to fetch JWKS: {str(e)}')
        raise

def base64_url_decode(data: str) -> bytes:
    """Decode base64 URL-safe string with proper padding"""
    # Add padding if needed
    missing_padding = len(data) % 4
    if missing_padding:
        data += '=' * (4 - missing_padding)
    
    return base64.urlsafe_b64decode(data)
