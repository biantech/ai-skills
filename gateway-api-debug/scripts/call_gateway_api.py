#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import ssl
import stat
import sys
from pathlib import Path
from typing import NoReturn
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit, urlunsplit
from urllib.request import HTTPRedirectHandler, HTTPSHandler, ProxyHandler, Request, build_opener


SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
ENVIRONMENTS = {"dev", "uat", "rc", "prod"}
TRACE_HEADERS = (
    "trace-id",
    "x-trace-id",
    "x-request-id",
    "request-id",
    "traceparent",
)


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        return None


def fail(message: str, exit_code: int = 1) -> NoReturn:
    print(f"[gateway-api-debug] {message}", file=sys.stderr)
    raise SystemExit(exit_code)


def bounded_int(name: str, value: str, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except ValueError:
        fail(f"{name} must be an integer")
    if not minimum <= parsed <= maximum:
        fail(f"{name} must be between {minimum} and {maximum}")
    return parsed


def validate_endpoint(path: str, profile: str) -> str:
    if any(ord(char) < 32 or ord(char) == 127 for char in path):
        fail("path contains a control character")
    if "?" in path or "#" in path:
        fail("use --query for query parameters")
    if not path.startswith("/") or "//" in path:
        fail("path must be a normalized absolute API path")
    if re.search(r"%(?:2f|5c|2e|3f|23)", path, flags=re.IGNORECASE):
        fail("encoded path separators, traversal, query, and fragment markers are not allowed")
    segments = path.split("/")
    if any(segment in {".", ".."} for segment in segments):
        fail("path traversal segments are not allowed")
    expected_prefix = "/api/" if profile == "customer" else "/admin-api/"
    if not path.startswith(expected_prefix):
        fail(f"{profile} profile requires a path under {expected_prefix}")
    return path


def validate_base_url(value: str, environment: str, allow_loopback_http: bool) -> str:
    parsed = urlsplit(value)
    try:
        parsed.port
    except ValueError:
        fail("base URL contains an invalid port")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        fail("base URL must not include credentials, query, or fragment")
    if not parsed.hostname or parsed.scheme not in {"http", "https"}:
        fail("base URL must be an absolute HTTP(S) URL")
    if parsed.scheme != "https":
        loopback = parsed.hostname in {"127.0.0.1", "::1", "localhost"}
        if environment == "prod" or not (allow_loopback_http and loopback):
            fail("HTTPS is required; HTTP is allowed only for explicit loopback tests")
    base_path = parsed.path.rstrip("/")
    if any(segment in {".", ".."} for segment in base_path.split("/")):
        fail("base URL path must not contain traversal segments")
    return urlunsplit((parsed.scheme, parsed.netloc, base_path, "", ""))


def load_token(environment: str, token_file: str | None) -> str:
    env_name = f"GATEWAY_{environment.upper()}_TOKEN"
    token = os.environ.pop(env_name, "")
    if token_file:
        if token:
            fail(f"configure either {env_name} or --token-file, not both")
        path = Path(token_file)
        if not path.is_file():
            fail("token file does not exist")
        if os.name != "nt" and stat.S_IMODE(path.stat().st_mode) & 0o077:
            fail("token file must not be accessible by group or other users")
        token = path.read_text(encoding="utf-8")
    token = token.strip()
    if not token:
        fail(f"bearer auth requires {env_name} or --token-file")
    if "\r" in token or "\n" in token:
        fail("token must be a single line")
    return token


def load_payload(payload_file: str | None, max_bytes: int) -> bytes | None:
    if not payload_file:
        return None
    path = Path(payload_file)
    if not path.is_file():
        fail("payload file does not exist")
    size = path.stat().st_size
    if size > max_bytes:
        fail(f"payload exceeds the {max_bytes}-byte limit")
    return path.read_bytes()


def parse_query(values: list[str]) -> str:
    pairs: list[tuple[str, str]] = []
    for value in values:
        if "=" not in value:
            fail("each --query value must use key=value")
        key, item = value.split("=", 1)
        if not key or any(ord(char) < 32 for char in key + item):
            fail("query parameters must be non-empty and contain no control characters")
        pairs.append((key, item))
    return urlencode(pairs)


def validate_content_type(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.+-]*/[A-Za-z0-9][A-Za-z0-9.+-]*", value):
        fail("content type must be a simple media type such as application/json")
    return value


def response_document(status: int, headers, body: bytes, truncated: bool) -> dict[str, object]:  # noqa: ANN001
    content_type = headers.get("Content-Type", "") if headers else ""
    trace = {
        name: headers.get(name)
        for name in TRACE_HEADERS
        if headers and headers.get(name)
    }
    text = body.decode("utf-8", errors="replace")
    parsed_body: object = text
    if "json" in content_type.lower() and text:
        try:
            parsed_body = json.loads(text)
        except json.JSONDecodeError:
            parsed_body = text
    return {
        "status": status,
        "contentType": content_type,
        "trace": trace,
        "truncated": truncated,
        "body": parsed_body,
    }


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Call an approved gateway API endpoint safely.")
    result.add_argument("--env", required=True, choices=sorted(ENVIRONMENTS))
    result.add_argument("--profile", required=True, choices=("customer", "admin"))
    result.add_argument("--method", default="GET", choices=sorted(SAFE_METHODS | WRITE_METHODS))
    result.add_argument("--path", required=True)
    result.add_argument("--auth", required=True, choices=("no-token", "guest", "bearer"))
    result.add_argument("--query", action="append", default=[], metavar="KEY=VALUE")
    result.add_argument("--payload-file")
    result.add_argument("--content-type", default="application/json")
    result.add_argument("--token-file")
    result.add_argument("--allow-write", action="store_true")
    result.add_argument("--allow-production", action="store_true")
    result.add_argument("--allow-loopback-http", action="store_true", help=argparse.SUPPRESS)
    result.add_argument("--timeout", default="30")
    result.add_argument("--max-payload-bytes", default="1048576")
    result.add_argument("--max-response-bytes", default="1048576")
    return result


def main() -> int:
    args = parser().parse_args()
    method = args.method.upper()
    if args.env == "prod" and not args.allow_production:
        fail("production calls require --allow-production after exact user authorization")
    if method in WRITE_METHODS and not args.allow_write:
        fail(f"{method} requires --allow-write after exact user authorization")
    if method in SAFE_METHODS and args.payload_file:
        fail(f"{method} does not accept --payload-file")
    if args.auth != "bearer" and args.token_file:
        fail("--token-file is valid only with --auth bearer")

    timeout = bounded_int("timeout", args.timeout, 1, 120)
    max_payload = bounded_int("max-payload-bytes", args.max_payload_bytes, 1, 10 * 1024 * 1024)
    max_response = bounded_int("max-response-bytes", args.max_response_bytes, 1, 10 * 1024 * 1024)
    path = validate_endpoint(args.path, args.profile)

    base_env = f"GATEWAY_{args.env.upper()}_BASE_URL"
    base_value = os.environ.get(base_env, "")
    if not base_value:
        fail(f"set the approved target in {base_env}")
    base_url = validate_base_url(base_value, args.env, args.allow_loopback_http)
    query = parse_query(args.query)
    url = f"{base_url}{path}"
    if query:
        url = f"{url}?{query}"

    headers = {"Accept": "application/json"}
    if args.auth == "guest":
        headers["X-Guest-Mode"] = "1"
    elif args.auth == "bearer":
        headers["Authorization"] = f"Bearer {load_token(args.env, args.token_file)}"

    payload = load_payload(args.payload_file, max_payload)
    if payload is not None:
        headers["Content-Type"] = validate_content_type(args.content_type)

    request = Request(url, data=payload, headers=headers, method=method)
    opener = build_opener(NoRedirect(), ProxyHandler({}), HTTPSHandler(context=ssl.create_default_context()))

    status = 0
    response_headers = None
    body = b""
    try:
        with opener.open(request, timeout=timeout) as response:
            status = response.status
            response_headers = response.headers
            body = response.read(max_response + 1)
    except HTTPError as error:
        status = error.code
        response_headers = error.headers
        body = error.read(max_response + 1)
    except (URLError, TimeoutError, OSError) as error:
        fail(f"request failed: {error}", 2)

    truncated = len(body) > max_response
    if truncated:
        body = body[:max_response]
    print(json.dumps(response_document(status, response_headers, body, truncated), ensure_ascii=False))
    return 0 if 200 <= status < 300 else 3


if __name__ == "__main__":
    raise SystemExit(main())
