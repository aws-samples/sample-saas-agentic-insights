import base64
import json
import os
import sys
import time
import unittest
from pathlib import Path
from unittest import mock

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


AUTHORIZER_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(AUTHORIZER_DIR))

import handler
import jwt_validator


def base64url_uint(value):
    size = (value.bit_length() + 7) // 8
    return base64.urlsafe_b64encode(value.to_bytes(size, "big")).rstrip(b"=").decode()


class AuthorizerTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        cls.private_key_pem = cls.private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        public_numbers = cls.private_key.public_key().public_numbers()
        cls.kid = "trusted-key"
        cls.jwks = {
            "keys": [
                {
                    "alg": "RS256",
                    "e": base64url_uint(public_numbers.e),
                    "kid": cls.kid,
                    "kty": "RSA",
                    "n": base64url_uint(public_numbers.n),
                    "use": "sig",
                }
            ]
        }

    def setUp(self):
        self.region = "ap-southeast-2"
        self.basic_pool = f"{self.region}_basic"
        self.premium_pool = f"{self.region}_premium"
        self.basic_client = "basic-client"
        self.premium_client = "premium-client"
        self.basic_issuer = (
            f"https://cognito-idp.{self.region}.amazonaws.com/{self.basic_pool}"
        )
        self.method_arn = (
            "arn:aws:execute-api:ap-southeast-2:123456789012:api-id/prod/GET/products"
        )
        self.env = mock.patch.dict(
            os.environ,
            {
                "AWS_REGION": self.region,
                "BASIC_USER_POOL_ID": self.basic_pool,
                "BASIC_USER_POOL_CLIENT_ID": self.basic_client,
                "PREMIUM_USER_POOL_ID": self.premium_pool,
                "PREMIUM_USER_POOL_CLIENT_ID": self.premium_client,
                "TENANTS_TABLE": "Tenants",
            },
            clear=True,
        )
        self.env.start()
        jwt_validator.jwks_cache.clear()
        jwt_validator.jwks_cache_expiry.clear()

    def tearDown(self):
        self.env.stop()

    def make_token(self, claims=None, issuer=None, client_id=None, token_use="access"):
        now = int(time.time())
        payload = {
            "client_id": client_id or self.basic_client,
            "custom:role": "tenant_admin",
            "custom:tenant_id": "victim-tenant-0001",
            "custom:tier": "basic",
            "exp": now + 300,
            "iat": now - 10,
            "iss": issuer or self.basic_issuer,
            "sub": "user-123",
            "token_use": token_use,
        }
        if token_use == "id":
            payload.pop("client_id")
            payload["aud"] = client_id or self.basic_client
        if claims:
            payload.update(claims)
        return jwt.encode(
            payload,
            self.private_key_pem,
            algorithm="RS256",
            headers={"kid": self.kid},
        )

    def validate(self, token):
        with mock.patch.object(jwt_validator, "get_jwks", return_value=self.jwks):
            return jwt_validator.validateJWT({"jwtToken": token})

    def test_accepts_valid_access_token_from_configured_pool_and_client(self):
        claims = self.validate(self.make_token())

        self.assertEqual(claims["sub"], "user-123")
        self.assertEqual(claims["custom:tenant_id"], "victim-tenant-0001")

    def test_accepts_valid_id_token_with_expected_audience(self):
        claims = self.validate(self.make_token(token_use="id"))

        self.assertEqual(claims["aud"], self.basic_client)

    def test_rejects_forged_signature_even_when_kid_matches(self):
        token = self.make_token()
        header, payload, _ = token.split(".")
        forged_token = f"{header}.{payload}.R0FSQkFHRV9OT1RfQV9SRUFMX1NJR05BVFVSRS"

        self.assertFalse(self.validate(forged_token))

    def test_rejects_validly_signed_token_from_unconfigured_issuer(self):
        foreign_issuer = (
            "https://cognito-idp.ap-southeast-2.amazonaws.com/"
            "ap-southeast-2_attacker"
        )
        with (
            mock.patch.object(jwt_validator, "get_jwks") as get_jwks,
            mock.patch.object(jwt_validator, "get_tenant", return_value=None),
        ):
            result = jwt_validator.validateJWT(
                {"jwtToken": self.make_token(issuer=foreign_issuer)}
            )

        self.assertFalse(result)
        get_jwks.assert_not_called()

    def test_accepts_dedicated_premium_pool_from_tenant_mapping(self):
        premium_pool = f"{self.region}_tenantpool"
        premium_client = "tenant-client"
        premium_issuer = (
            f"https://cognito-idp.{self.region}.amazonaws.com/{premium_pool}"
        )
        token = self.make_token(
            claims={"custom:tier": "premium"},
            issuer=premium_issuer,
            client_id=premium_client,
        )

        with (
            mock.patch.object(jwt_validator, "get_jwks", return_value=self.jwks),
            mock.patch.object(
                jwt_validator,
                "get_tenant",
                return_value={
                    "tier": "premium",
                    "user_pool_id": premium_pool,
                },
            ),
            mock.patch.object(
                jwt_validator,
                "get_user_pool_client_ids",
                return_value=[premium_client],
            ),
        ):
            claims = jwt_validator.validateJWT({"jwtToken": token})

        self.assertEqual(claims["custom:tier"], "premium")

    def test_rejects_dedicated_pool_not_mapped_to_claimed_tenant(self):
        attacker_pool = f"{self.region}_attacker"
        attacker_issuer = (
            f"https://cognito-idp.{self.region}.amazonaws.com/{attacker_pool}"
        )
        token = self.make_token(issuer=attacker_issuer)

        with (
            mock.patch.object(jwt_validator, "get_jwks") as get_jwks,
            mock.patch.object(
                jwt_validator,
                "get_tenant",
                return_value={
                    "tier": "premium",
                    "user_pool_id": f"{self.region}_realtenant",
                },
            ),
        ):
            result = jwt_validator.validateJWT({"jwtToken": token})

        self.assertFalse(result)
        get_jwks.assert_not_called()

    def test_rejects_access_token_for_wrong_client(self):
        self.assertFalse(self.validate(self.make_token(client_id="attacker-client")))

    def test_rejects_id_token_for_wrong_audience(self):
        self.assertFalse(
            self.validate(self.make_token(client_id="attacker-client", token_use="id"))
        )

    def test_rejects_token_without_expiration(self):
        self.assertFalse(self.validate(self.make_token(claims={"exp": None})))

    def test_rejects_token_issued_in_the_future(self):
        self.assertFalse(
            self.validate(self.make_token(claims={"iat": int(time.time()) + 300}))
        )

    def test_rejects_non_cognito_jwks_url(self):
        with self.assertRaises(ValueError):
            jwt_validator.get_jwks("file:///tmp/attacker-jwks.json")

    def test_handler_scopes_policy_to_requested_method_and_omits_raw_token(self):
        token = self.make_token()
        event = {
            "authorizationToken": f"Bearer {token}",
            "methodArn": self.method_arn,
        }

        with mock.patch.object(
            handler.jwt_validator,
            "validateJWT",
            return_value={
                "custom:role": "tenant_admin",
                "custom:tenant_id": "victim-tenant-0001",
                "custom:tier": "basic",
                "sub": "user-123",
            },
        ):
            policy = handler.handler(event, None)

        statement = policy["policyDocument"]["Statement"][0]
        self.assertEqual(statement["Effect"], "Allow")
        self.assertEqual(statement["Resource"], self.method_arn)
        self.assertNotIn("jwt_token", policy["context"])

    def test_handler_denies_malformed_bearer_header(self):
        policy = handler.handler(
            {"authorizationToken": "Bearer", "methodArn": self.method_arn},
            None,
        )

        self.assertEqual(
            policy["policyDocument"]["Statement"][0]["Effect"],
            "Deny",
        )


if __name__ == "__main__":
    unittest.main()
