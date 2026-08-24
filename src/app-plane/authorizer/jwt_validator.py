import json
import os
import time
import urllib.request
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urlparse

import jwt


jwks_cache = {}
jwks_cache_expiry = {}


def validateJWT(
    input_details: Dict[str, Any],
) -> Union[Dict[str, Any], bool]:
    """Validate a Cognito JWT and return its verified claims."""
    try:
        jwt_token = input_details["jwtToken"]
        header = jwt.get_unverified_header(jwt_token)

        kid = header.get("kid")
        if not kid:
            print("Missing key ID in token header")
            return False

        if header.get("alg") != "RS256":
            print(f"Unsupported algorithm: {header.get('alg')}")
            return False

        unverified_claims = jwt.decode(
            jwt_token,
            options={
                "verify_signature": False,
                "verify_exp": False,
                "verify_aud": False,
            },
        )
        trusted_config = resolve_trusted_config(unverified_claims)
        if not trusted_config:
            print("Token issuer is not trusted")
            return False

        signing_key = get_signing_key(trusted_config["jwks_url"], kid)
        if not signing_key:
            print("No matching signing key found")
            return False

        claims = jwt.decode(
            jwt_token,
            jwt.PyJWK.from_dict(signing_key).key,
            algorithms=["RS256"],
            issuer=trusted_config["issuer"],
            options={
                "verify_aud": False,
            },
        )

        if not validate_token_use_and_client(claims, trusted_config["client_ids"]):
            return False

        current_time = int(time.time())
        expiration = claims.get("exp")
        if not isinstance(expiration, (int, float)) or current_time >= expiration:
            print("Token has expired or is missing expiration")
            return False

        issued_at = claims.get("iat")
        if not isinstance(issued_at, (int, float)) or current_time < issued_at:
            print("Token used before issued")
            return False

        return claims
    except (
        jwt.InvalidTokenError,
        KeyError,
        TypeError,
        ValueError,
        json.JSONDecodeError,
    ) as error:
        print(f"JWT validation failed: {str(error)}")
        return False
    except Exception as error:
        print(f"JWT validation failed: {str(error)}")
        return False


def get_trusted_issuers() -> Dict[str, Dict[str, Any]]:
    """Build the issuer allowlist from deployment-controlled settings."""
    region = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION")
    if not region:
        print("AWS region is not configured")
        return {}

    trusted_issuers = {}
    for tier in ("BASIC", "PREMIUM"):
        user_pool_id = os.environ.get(f"{tier}_USER_POOL_ID")
        client_id = os.environ.get(f"{tier}_USER_POOL_CLIENT_ID")
        if not user_pool_id or not client_id:
            print(f"{tier} user pool or client ID is not configured")
            continue

        issuer = f"https://cognito-idp.{region}.amazonaws.com/{user_pool_id}"
        trusted_issuers[issuer] = {
            "client_ids": [client_id],
            "issuer": issuer,
            "jwks_url": f"{issuer}/.well-known/jwks.json",
        }

    return trusted_issuers


def resolve_trusted_config(claims: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Resolve static or tenant-specific trust without trusting token metadata."""
    issuer = claims.get("iss")
    static_config = get_trusted_issuers().get(issuer)
    if static_config:
        return static_config

    region = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION")
    tenant_id = claims.get("custom:tenant_id") or claims.get("custom:tenantId")
    tenants_table = os.environ.get("TENANTS_TABLE")
    if not region or not tenant_id or not tenants_table:
        return None

    tenant = get_tenant(tenants_table, tenant_id)
    if not tenant or tenant.get("tier") != "premium":
        return None

    user_pool_id = tenant.get("user_pool_id")
    expected_issuer = f"https://cognito-idp.{region}.amazonaws.com/{user_pool_id}"
    if not user_pool_id or issuer != expected_issuer:
        return None

    client_ids = get_user_pool_client_ids(user_pool_id)
    if not client_ids:
        return None

    return {
        "client_ids": client_ids,
        "issuer": expected_issuer,
        "jwks_url": f"{expected_issuer}/.well-known/jwks.json",
    }


def get_tenant(table_name: str, tenant_id: str) -> Optional[Dict[str, Any]]:
    """Read the deployment-owned tenant-to-user-pool mapping."""
    import boto3

    response = boto3.resource("dynamodb").Table(table_name).get_item(
        Key={"tenant_id": tenant_id},
        ConsistentRead=True,
        ProjectionExpression="#pool, #tier",
        ExpressionAttributeNames={
            "#pool": "user_pool_id",
            "#tier": "tier",
        },
    )
    return response.get("Item")


def get_user_pool_client_ids(user_pool_id: str) -> List[str]:
    """Return the app clients that belong to a trusted tenant user pool."""
    import boto3

    response = boto3.client("cognito-idp").list_user_pool_clients(
        UserPoolId=user_pool_id,
        MaxResults=60,
    )
    return [
        client["ClientId"]
        for client in response.get("UserPoolClients", [])
        if client.get("ClientId")
    ]


def get_signing_key(jwks_url: str, kid: str) -> Optional[Dict[str, Any]]:
    """Return the configured issuer's JWK matching the token key ID."""
    jwks = get_jwks(jwks_url)
    for key in jwks.get("keys", []):
        if key.get("kid") == kid and key.get("kty") == "RSA":
            return key
    return None


def validate_token_use_and_client(
    claims: Dict[str, Any], client_ids: List[str]
) -> bool:
    """Validate Cognito token type and its app client binding."""
    token_use = claims.get("token_use")
    if token_use == "access":
        if claims.get("client_id") not in client_ids:
            print("Access token client_id does not match")
            return False
        return True

    if token_use == "id":
        audience = claims.get("aud")
        if isinstance(audience, list):
            valid_audience = any(client_id in audience for client_id in client_ids)
        else:
            valid_audience = audience in client_ids

        if not valid_audience:
            print("ID token audience does not match")
            return False
        return True

    print(f"Invalid token_use: {token_use}")
    return False


def get_jwks(jwks_url: str) -> Dict[str, Any]:
    """Fetch and cache an issuer's JSON Web Key Set."""
    parsed_url = urlparse(jwks_url)
    if (
        parsed_url.scheme != "https"
        or not parsed_url.hostname
        or not parsed_url.hostname.startswith("cognito-idp.")
        or not parsed_url.hostname.endswith(".amazonaws.com")
    ):
        raise ValueError("JWKS URL must use a Cognito HTTPS endpoint")

    current_time = time.time()
    if (
        jwks_url in jwks_cache
        and jwks_url in jwks_cache_expiry
        and current_time < jwks_cache_expiry[jwks_url]
    ):
        return jwks_cache[jwks_url]

    try:
        # The URL scheme and Cognito hostname are constrained above.
        with urllib.request.urlopen(jwks_url, timeout=10) as response:  # nosec B310
            jwks = json.loads(response.read().decode("utf-8"))

        jwks_cache[jwks_url] = jwks
        jwks_cache_expiry[jwks_url] = current_time + 3600
        return jwks
    except Exception as error:
        print(f"Failed to fetch JWKS: {str(error)}")
        raise
