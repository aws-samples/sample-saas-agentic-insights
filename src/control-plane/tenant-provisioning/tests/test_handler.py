import importlib.util
import os
import sys
import types
import unittest
from pathlib import Path
from unittest import mock


HANDLER_PATH = Path(__file__).resolve().parents[1] / "handler.py"


def load_handler(cognito_client):
    fake_boto3 = types.ModuleType("boto3")
    fake_boto3.resource = mock.Mock(return_value=mock.Mock())
    fake_boto3.client = mock.Mock(
        side_effect=lambda service_name: (
            cognito_client if service_name == "cognito-idp" else mock.Mock()
        )
    )

    module_name = "tenant_provisioning_handler_under_test"
    spec = importlib.util.spec_from_file_location(module_name, HANDLER_PATH)
    module = importlib.util.module_from_spec(spec)

    with (
        mock.patch.dict(sys.modules, {"boto3": fake_boto3, module_name: module}),
        mock.patch.dict(os.environ, {"TENANTS_TABLE": "Tenants"}),
    ):
        spec.loader.exec_module(module)

    return module


class PremiumUserPoolProvisioningTestCase(unittest.TestCase):
    def test_user_pool_client_allows_email_but_not_tenant_control_attributes(self):
        cognito_client = mock.Mock()
        cognito_client.create_user_pool.return_value = {
            "UserPool": {"Id": "ap-southeast-2_testpool"}
        }
        handler = load_handler(cognito_client)

        handler.create_premium_user_pool("premium-tenant-test", "tenant-test")

        client_config = cognito_client.create_user_pool_client.call_args.kwargs
        self.assertIn("WriteAttributes", client_config)

        write_attributes = client_config["WriteAttributes"]
        self.assertIn("email", write_attributes)
        for protected_attribute in (
            "custom:role",
            "custom:tier",
            "custom:tenant_id",
        ):
            with self.subTest(protected_attribute=protected_attribute):
                self.assertNotIn(protected_attribute, write_attributes)


if __name__ == "__main__":
    unittest.main()
