#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import io
import json
import os
import sys
import tempfile
import unittest
from email.message import Message
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError


SKILL_ROOT = Path(__file__).resolve().parents[1]
CLIENT = SKILL_ROOT / "scripts" / "call_gateway_api.py"
SPEC = importlib.util.spec_from_file_location("gateway_api_client", CLIENT)
assert SPEC and SPEC.loader
CLIENT_MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CLIENT_MODULE)


def headers(**values: str) -> Message:
    result = Message()
    for name, value in values.items():
        result[name.replace("_", "-")] = value
    return result


class FakeResponse:
    def __init__(self, status: int, body: bytes, response_headers: Message) -> None:
        self.status = status
        self.body = body
        self.headers = response_headers

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self, limit: int = -1) -> bytes:
        return self.body if limit < 0 else self.body[:limit]


class FakeOpener:
    def __init__(self, *, redirect: bool = False) -> None:
        self.requests = []
        self.redirect = redirect

    def open(self, request, timeout: int):  # noqa: ANN001
        self.requests.append((request, timeout))
        if self.redirect:
            raise HTTPError(
                request.full_url,
                302,
                "Found",
                headers(Location="https://other.example/api/final"),
                io.BytesIO(b"redirect refused"),
            )
        body = json.dumps({"path": request.full_url}).encode()
        return FakeResponse(
            200,
            body,
            headers(Content_Type="application/json", X_Trace_Id="trace-123"),
        )


class GatewayClientTest(unittest.TestCase):
    def setUp(self) -> None:
        self.opener = FakeOpener()
        self.environment = {
            "GATEWAY_DEV_BASE_URL": "https://dev.gateway.example",
            "GATEWAY_PROD_BASE_URL": "https://prod.gateway.example",
        }

    def run_client(self, *arguments: str, opener: FakeOpener | None = None):  # noqa: ANN201
        active_opener = opener or self.opener
        stdout = io.StringIO()
        stderr = io.StringIO()
        argv = [str(CLIENT), *arguments]
        with (
            patch.dict(os.environ, self.environment, clear=True),
            patch.object(sys, "argv", argv),
            patch.object(CLIENT_MODULE, "build_opener", return_value=active_opener),
            patch("sys.stdout", stdout),
            patch("sys.stderr", stderr),
        ):
            try:
                return_code = CLIENT_MODULE.main()
            except SystemExit as error:
                return_code = int(error.code or 0)
        return return_code, stdout.getvalue(), stderr.getvalue(), active_opener

    def common(self) -> tuple[str, ...]:
        return (
            "--env", "dev",
            "--profile", "customer",
            "--path", "/api/test",
        )

    def test_guest_call_has_guest_header_and_encoded_query(self) -> None:
        code, stdout, stderr, opener = self.run_client(
            *self.common(), "--auth", "guest", "--query", "q=a b"
        )
        self.assertEqual(0, code, stderr)
        output = json.loads(stdout)
        self.assertEqual(200, output["status"])
        self.assertEqual({"x-trace-id": "trace-123"}, output["trace"])
        request, timeout = opener.requests[0]
        self.assertEqual("https://dev.gateway.example/api/test?q=a+b", request.full_url)
        self.assertEqual("1", request.get_header("X-guest-mode"))
        self.assertIsNone(request.get_header("Authorization"))
        self.assertEqual(30, timeout)

    def test_bearer_token_is_loaded_from_environment(self) -> None:
        self.environment["GATEWAY_DEV_TOKEN"] = "secret-token"
        code, stdout, stderr, opener = self.run_client(*self.common(), "--auth", "bearer")
        self.assertEqual(0, code, stderr)
        request, _ = opener.requests[0]
        self.assertEqual("Bearer secret-token", request.get_header("Authorization"))
        self.assertNotIn("secret-token", stdout)
        self.assertNotIn("secret-token", stderr)

    def test_write_requires_explicit_flag_before_request(self) -> None:
        code, _, stderr, opener = self.run_client(
            *self.common(), "--auth", "no-token", "--method", "POST"
        )
        self.assertNotEqual(0, code)
        self.assertIn("--allow-write", stderr)
        self.assertEqual([], opener.requests)

    def test_production_requires_explicit_flag_before_request(self) -> None:
        arguments = list(self.common())
        arguments[1] = "prod"
        code, _, stderr, opener = self.run_client(*arguments, "--auth", "no-token")
        self.assertNotEqual(0, code)
        self.assertIn("--allow-production", stderr)
        self.assertEqual([], opener.requests)

    def test_redirect_response_is_reported_without_second_request(self) -> None:
        arguments = list(self.common())
        arguments[5] = "/api/redirect"
        redirecting = FakeOpener(redirect=True)
        code, stdout, _, opener = self.run_client(
            *arguments, "--auth", "no-token", opener=redirecting
        )
        self.assertEqual(3, code)
        self.assertEqual(302, json.loads(stdout)["status"])
        self.assertEqual(1, len(opener.requests))

    def test_profile_path_mismatch_is_rejected_before_request(self) -> None:
        code, _, stderr, opener = self.run_client(
            "--env", "dev",
            "--profile", "admin",
            "--path", "/api/customer-only",
            "--auth", "no-token",
        )
        self.assertNotEqual(0, code)
        self.assertIn("admin profile", stderr)
        self.assertEqual([], opener.requests)

    def test_encoded_path_traversal_is_rejected_before_request(self) -> None:
        arguments = list(self.common())
        arguments[5] = "/api/%2e%2e/admin-api/secret"
        code, _, stderr, opener = self.run_client(*arguments, "--auth", "no-token")
        self.assertNotEqual(0, code)
        self.assertIn("encoded path", stderr)
        self.assertEqual([], opener.requests)

    def test_insecure_token_file_is_rejected_before_request(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            token_file = Path(directory) / "token"
            token_file.write_text("secret-token")
            token_file.chmod(0o644)
            code, _, stderr, opener = self.run_client(
                *self.common(), "--auth", "bearer", "--token-file", str(token_file)
            )
        self.assertNotEqual(0, code)
        self.assertIn("group or other", stderr)
        self.assertEqual([], opener.requests)

    def test_package_contains_localized_and_ui_metadata(self) -> None:
        self.assertTrue((SKILL_ROOT / "SKILL_zh.md").is_file())
        self.assertTrue((SKILL_ROOT / "agents" / "openai.yaml").is_file())


if __name__ == "__main__":
    unittest.main()
