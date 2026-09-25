#!/usr/bin/env python3
"""Restrict selected tenant-facing Cognito clients to writing email."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Sequence

import boto3


SUPPORTED_UPDATE_SETTINGS = (
    "ClientName",
    "RefreshTokenValidity",
    "AccessTokenValidity",
    "IdTokenValidity",
    "TokenValidityUnits",
    "ReadAttributes",
    "ExplicitAuthFlows",
    "SupportedIdentityProviders",
    "CallbackURLs",
    "LogoutURLs",
    "DefaultRedirectURI",
    "AllowedOAuthFlows",
    "AllowedOAuthScopes",
    "AllowedOAuthFlowsUserPoolClient",
    "AnalyticsConfiguration",
    "PreventUserExistenceErrors",
    "EnableTokenRevocation",
    "EnablePropagateAdditionalUserContextData",
    "AuthSessionValidity",
    "RefreshTokenRotation",
)

IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")


class InputError(ValueError):
    """Raised when the migration target file is invalid."""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Set WriteAttributes to email for explicitly listed Cognito clients."
        )
    )
    parser.add_argument(
        "--input",
        required=True,
        type=Path,
        help="Path to a JSON file containing a non-empty targets list.",
    )
    parser.add_argument(
        "--region",
        help="AWS region for the Cognito API client.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply updates. Without this flag, the migration is a dry-run.",
    )
    return parser


def validate_identifier(value: Any, field_name: str, target_number: int) -> str:
    if not isinstance(value, str) or not value:
        raise InputError(
            f"Target {target_number} requires a non-empty {field_name} string."
        )
    if value != value.strip() or not IDENTIFIER_PATTERN.fullmatch(value):
        raise InputError(
            f"Target {target_number} has an invalid {field_name}."
        )
    return value


def load_targets(input_path: Path) -> list[dict[str, str]]:
    if not input_path.is_file():
        raise InputError(f"Input JSON file does not exist: {input_path}")

    try:
        payload = json.loads(input_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError) as error:
        raise InputError(f"Could not read input JSON file: {error}") from error
    except json.JSONDecodeError as error:
        raise InputError(
            f"Invalid JSON in input file at line {error.lineno}, "
            f"column {error.colno}."
        ) from error

    if not isinstance(payload, dict):
        raise InputError("Input JSON must be an object with a targets list.")

    raw_targets = payload.get("targets")
    if not isinstance(raw_targets, list) or not raw_targets:
        raise InputError("Input JSON must contain a non-empty targets list.")

    targets: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for target_number, raw_target in enumerate(raw_targets, start=1):
        if not isinstance(raw_target, dict):
            raise InputError(f"Target {target_number} must be an object.")

        user_pool_id = validate_identifier(
            raw_target.get("user_pool_id"),
            "user_pool_id",
            target_number,
        )
        client_id = validate_identifier(
            raw_target.get("client_id"),
            "client_id",
            target_number,
        )
        target_key = (user_pool_id, client_id)
        if target_key in seen:
            raise InputError(f"Target {target_number} duplicates an earlier target.")

        seen.add(target_key)
        targets.append(
            {
                "user_pool_id": user_pool_id,
                "client_id": client_id,
            }
        )

    return targets


def update_parameters(
    target: dict[str, str],
    described_client: dict[str, Any],
) -> dict[str, Any]:
    parameters: dict[str, Any] = {
        "UserPoolId": target["user_pool_id"],
        "ClientId": target["client_id"],
    }
    for setting in SUPPORTED_UPDATE_SETTINGS:
        if setting in described_client:
            parameters[setting] = described_client[setting]
    parameters["WriteAttributes"] = ["email"]
    return parameters


def main(arguments: Sequence[str] | None = None) -> int:
    parser = build_parser()
    try:
        options = parser.parse_args(arguments)
        targets = load_targets(options.input)
    except InputError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2
    except SystemExit as error:
        return int(error.code)

    mode = "apply" if options.apply else "dry-run"
    client_options = {}
    if options.region:
        client_options["region_name"] = options.region
    cognito = boto3.client("cognito-idp", **client_options)

    print(f"Mode: {mode}; targets: {len(targets)}")
    try:
        for target in targets:
            user_pool_id = target["user_pool_id"]
            client_id = target["client_id"]
            response = cognito.describe_user_pool_client(
                UserPoolId=user_pool_id,
                ClientId=client_id,
            )
            described_client = response.get("UserPoolClient")
            if not isinstance(described_client, dict):
                raise RuntimeError("describe response did not contain a client")

            if options.apply:
                cognito.update_user_pool_client(
                    **update_parameters(target, described_client)
                )
                status = "updated"
            else:
                status = "would update"
            print(f"{user_pool_id}/{client_id}: {status}")
    except Exception as error:
        print(
            f"Error processing {user_pool_id}/{client_id}: "
            f"{type(error).__name__}",
            file=sys.stderr,
        )
        return 1

    print(f"Completed: {len(targets)} target(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
