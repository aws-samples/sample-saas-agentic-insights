import importlib.util
import io
import json
import sys
import tempfile
import types
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MIGRATION_PATH = (
    PROJECT_ROOT
    / "scripts"
    / "migrations"
    / "restrict_cognito_client_write_attributes.py"
)


def load_migration(cognito_client):
    if not MIGRATION_PATH.is_file():
        raise AssertionError(
            "Expected migration script at "
            "scripts/migrations/restrict_cognito_client_write_attributes.py"
        )

    fake_boto3 = types.ModuleType("boto3")
    fake_boto3.client = mock.Mock(return_value=cognito_client)

    module_name = "restrict_cognito_client_write_attributes_under_test"
    spec = importlib.util.spec_from_file_location(module_name, MIGRATION_PATH)
    module = importlib.util.module_from_spec(spec)

    with mock.patch.dict(
        sys.modules,
        {"boto3": fake_boto3, module_name: module},
    ):
        spec.loader.exec_module(module)

    return module, fake_boto3


class CognitoClientMigrationTestCase(unittest.TestCase):
    maxDiff = None

    def setUp(self):
        self.cognito = mock.Mock()
        self.target = {
            "user_pool_id": "ap-southeast-2_example",
            "client_id": "client-example-123",
        }
        self.described_client = {
            "UserPoolId": self.target["user_pool_id"],
            "ClientId": self.target["client_id"],
            "ClientName": "tenant-app",
            "RefreshTokenValidity": 30,
            "AccessTokenValidity": 60,
            "IdTokenValidity": 60,
            "TokenValidityUnits": {
                "AccessToken": "minutes",
                "IdToken": "minutes",
                "RefreshToken": "days",
            },
            "ReadAttributes": ["email", "custom:tenant_id"],
            "WriteAttributes": [
                "email",
                "custom:role",
                "custom:tenant_id",
                "custom:tier",
            ],
            "ExplicitAuthFlows": [
                "ALLOW_USER_SRP_AUTH",
                "ALLOW_REFRESH_TOKEN_AUTH",
            ],
            "SupportedIdentityProviders": ["COGNITO"],
            "CallbackURLs": ["https://example.test/callback"],
            "LogoutURLs": ["https://example.test/logout"],
            "DefaultRedirectURI": "https://example.test/callback",
            "AllowedOAuthFlows": ["code"],
            "AllowedOAuthScopes": ["email", "openid"],
            "AllowedOAuthFlowsUserPoolClient": True,
            "AnalyticsConfiguration": {
                "ApplicationArn": (
                    "arn:aws:mobiletargeting:ap-southeast-2:123456789012:"
                    "apps/example"
                ),
                "RoleArn": "arn:aws:iam::123456789012:role/cognito-analytics",
                "UserDataShared": False,
            },
            "PreventUserExistenceErrors": "ENABLED",
            "EnableTokenRevocation": True,
            "EnablePropagateAdditionalUserContextData": False,
            "AuthSessionValidity": 5,
            "RefreshTokenRotation": {
                "Feature": "ENABLED",
                "RetryGracePeriodSeconds": 10,
            },
            "ClientSecret": "never-print-client-secret",
            "CreationDate": datetime(2025, 1, 1, tzinfo=timezone.utc),
            "LastModifiedDate": datetime(2026, 1, 1, tzinfo=timezone.utc),
        }
        self.cognito.describe_user_pool_client.return_value = {
            "UserPoolClient": self.described_client
        }
        self.cognito.update_user_pool_client.return_value = {
            "UserPoolClient": {
                **self.described_client,
                "WriteAttributes": ["email"],
                "AccessToken": "never-print-access-token",
                "IdToken": "never-print-id-token",
                "RefreshToken": "never-print-refresh-token",
            }
        }

    def write_input(self, payload):
        temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(temporary_directory.cleanup)
        input_path = Path(temporary_directory.name) / "targets.json"
        input_path.write_text(json.dumps(payload), encoding="utf-8")
        return input_path

    def run_main(self, arguments):
        migration, fake_boto3 = load_migration(self.cognito)
        stdout = io.StringIO()
        stderr = io.StringIO()

        with redirect_stdout(stdout), redirect_stderr(stderr):
            result = migration.main(arguments)

        return result, stdout.getvalue(), stderr.getvalue(), fake_boto3

    def test_dry_run_is_default_and_describes_only_explicit_targets(self):
        input_path = self.write_input({"targets": [self.target]})

        result, output, errors, _ = self.run_main(["--input", str(input_path)])

        self.assertEqual(result, 0)
        self.cognito.describe_user_pool_client.assert_called_once_with(
            UserPoolId=self.target["user_pool_id"],
            ClientId=self.target["client_id"],
        )
        self.cognito.update_user_pool_client.assert_not_called()
        self.assertIn("dry-run", output.lower())
        self.assertEqual(errors, "")

    def test_apply_preserves_supported_settings_and_sets_only_email_writable(self):
        input_path = self.write_input({"targets": [self.target]})

        result, _, _, _ = self.run_main(
            ["--input", str(input_path), "--apply"]
        )

        self.assertEqual(result, 0)
        self.cognito.update_user_pool_client.assert_called_once_with(
            UserPoolId=self.target["user_pool_id"],
            ClientId=self.target["client_id"],
            ClientName="tenant-app",
            RefreshTokenValidity=30,
            AccessTokenValidity=60,
            IdTokenValidity=60,
            TokenValidityUnits={
                "AccessToken": "minutes",
                "IdToken": "minutes",
                "RefreshToken": "days",
            },
            ReadAttributes=["email", "custom:tenant_id"],
            WriteAttributes=["email"],
            ExplicitAuthFlows=[
                "ALLOW_USER_SRP_AUTH",
                "ALLOW_REFRESH_TOKEN_AUTH",
            ],
            SupportedIdentityProviders=["COGNITO"],
            CallbackURLs=["https://example.test/callback"],
            LogoutURLs=["https://example.test/logout"],
            DefaultRedirectURI="https://example.test/callback",
            AllowedOAuthFlows=["code"],
            AllowedOAuthScopes=["email", "openid"],
            AllowedOAuthFlowsUserPoolClient=True,
            AnalyticsConfiguration={
                "ApplicationArn": (
                    "arn:aws:mobiletargeting:ap-southeast-2:123456789012:"
                    "apps/example"
                ),
                "RoleArn": "arn:aws:iam::123456789012:role/cognito-analytics",
                "UserDataShared": False,
            },
            PreventUserExistenceErrors="ENABLED",
            EnableTokenRevocation=True,
            EnablePropagateAdditionalUserContextData=False,
            AuthSessionValidity=5,
            RefreshTokenRotation={
                "Feature": "ENABLED",
                "RetryGracePeriodSeconds": 10,
            },
        )

    def test_apply_processes_each_target_from_the_input_file(self):
        second_target = {
            "user_pool_id": "ap-southeast-2_second",
            "client_id": "client-second-456",
        }
        self.cognito.describe_user_pool_client.side_effect = [
            {"UserPoolClient": self.described_client},
            {
                "UserPoolClient": {
                    **self.described_client,
                    "UserPoolId": second_target["user_pool_id"],
                    "ClientId": second_target["client_id"],
                }
            },
        ]
        input_path = self.write_input(
            {"targets": [self.target, second_target]}
        )

        result, _, _, _ = self.run_main(
            ["--input", str(input_path), "--apply"]
        )

        self.assertEqual(result, 0)
        self.assertEqual(self.cognito.describe_user_pool_client.call_count, 2)
        self.assertEqual(self.cognito.update_user_pool_client.call_count, 2)
        described_targets = {
            (
                call.kwargs["UserPoolId"],
                call.kwargs["ClientId"],
            )
            for call in self.cognito.describe_user_pool_client.call_args_list
        }
        self.assertEqual(
            described_targets,
            {
                (
                    self.target["user_pool_id"],
                    self.target["client_id"],
                ),
                (
                    second_target["user_pool_id"],
                    second_target["client_id"],
                ),
            },
        )

    def test_region_is_forwarded_to_the_cognito_client(self):
        input_path = self.write_input({"targets": [self.target]})

        result, _, _, fake_boto3 = self.run_main(
            [
                "--input",
                str(input_path),
                "--region",
                "ap-southeast-2",
            ]
        )

        self.assertEqual(result, 0)
        fake_boto3.client.assert_called_once_with(
            "cognito-idp",
            region_name="ap-southeast-2",
        )

    def test_output_never_contains_secrets_or_tokens_in_any_mode(self):
        sensitive_values = {
            "never-print-client-secret",
            "never-print-access-token",
            "never-print-id-token",
            "never-print-refresh-token",
        }

        for apply_arguments in ([], ["--apply"]):
            with self.subTest(apply=bool(apply_arguments)):
                self.cognito.reset_mock()
                self.cognito.describe_user_pool_client.return_value = {
                    "UserPoolClient": self.described_client
                }
                input_path = self.write_input({"targets": [self.target]})

                _, output, errors, _ = self.run_main(
                    ["--input", str(input_path), *apply_arguments]
                )

                combined_output = output + errors
                for sensitive_value in sensitive_values:
                    self.assertNotIn(sensitive_value, combined_output)
                for sensitive_key in (
                    "ClientSecret",
                    "AccessToken",
                    "IdToken",
                    "RefreshToken",
                ):
                    self.assertNotIn(sensitive_key, combined_output)

    def test_rejects_an_empty_target_list_without_calling_aws(self):
        input_path = self.write_input({"targets": []})

        result, _, errors, _ = self.run_main(["--input", str(input_path)])

        self.assertNotEqual(result, 0)
        self.assertIn("target", errors.lower())
        self.cognito.describe_user_pool_client.assert_not_called()
        self.cognito.update_user_pool_client.assert_not_called()

    def test_rejects_targets_missing_required_identifiers(self):
        invalid_targets = (
            {"client_id": self.target["client_id"]},
            {"user_pool_id": self.target["user_pool_id"]},
            {},
        )

        for invalid_target in invalid_targets:
            with self.subTest(target=invalid_target):
                self.cognito.reset_mock()
                input_path = self.write_input({"targets": [invalid_target]})

                result, _, errors, _ = self.run_main(
                    ["--input", str(input_path)]
                )

                self.assertNotEqual(result, 0)
                self.assertIn("target", errors.lower())
                self.cognito.describe_user_pool_client.assert_not_called()
                self.cognito.update_user_pool_client.assert_not_called()

    def test_rejects_invalid_json_without_calling_aws(self):
        temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(temporary_directory.cleanup)
        input_path = Path(temporary_directory.name) / "targets.json"
        input_path.write_text("{not-json", encoding="utf-8")

        result, _, errors, _ = self.run_main(["--input", str(input_path)])

        self.assertNotEqual(result, 0)
        self.assertIn("json", errors.lower())
        self.cognito.describe_user_pool_client.assert_not_called()
        self.cognito.update_user_pool_client.assert_not_called()


if __name__ == "__main__":
    unittest.main()
