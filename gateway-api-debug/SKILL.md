---
name: gateway-api-debug
description: Debug and validate customer or admin gateway APIs by confirming the route, HTTP method, request shape, and authentication decision from gateway and controller code, then making a bounded live call to an explicitly selected Dev, UAT, RC, or authorized production target. Use for end-to-end gateway behavior and response verification. Do not use to infer permission for mutations, discover unrelated production data, or bypass authentication and environment controls.
---

# Gateway API Debug

Separate what code proves from what a live gateway response verifies. Use the bundled client for live calls; it does not implement application login or token caching.

The Chinese version is maintained in [SKILL_zh.md](SKILL_zh.md). Keep both files behaviorally aligned.

## Establish the Request Contract

Before any live call, inspect the relevant gateway filter/route and target controller to identify:

- exact path and HTTP method;
- customer `/api/...` or admin `/admin-api/...` profile;
- path variables, query parameters, headers, and body schema;
- whether the operation is read-only or mutating;
- the exact authentication branch and any role or tenant context.

Do not infer guest or anonymous eligibility from the path prefix. Confirm the exact filter decision and guest-path matching behavior from current code or approved runtime configuration.

When reporting, distinguish:

- `[LOGIC]`: derived from current code, specification, or configuration;
- `[QUERY]`: observed from the live request and response;
- `[ASSUME]`: still unverified.

This evidence convention is self-contained and does not require another Skill.

## Authorization Boundary

A debugging request may justify a narrowly scoped read-only call to the environment the user selected or the workspace explicitly maps. It does not authorize writes.

For `POST`, `PUT`, `PATCH`, or `DELETE`, require the current user request to clearly authorize the exact environment, endpoint, method, and intended change. The client additionally requires `--allow-write`. Do not infer write authorization from code changes, a token, access to a lower environment, a previous request, or permission for another endpoint.

Production calls require the user to explicitly name production and authorize the exact call in the current task. The client additionally requires `--allow-production`; production mutations require both `--allow-production` and `--allow-write`.

Do not broaden an authorized action into exploratory production queries, login attempts, unrelated endpoints, alternate writes, retries, or another environment. Stop on an unexpected target, ambiguous record, validation mismatch, redirect, non-success response, or failed mutation read-back.

## Environment Configuration

Set only the environments that have been approved for the current workspace:

```bash
export GATEWAY_DEV_BASE_URL='https://approved-dev-gateway.example'
export GATEWAY_UAT_BASE_URL='https://approved-uat-gateway.example'
export GATEWAY_RC_BASE_URL='https://approved-rc-gateway.example'
export GATEWAY_PROD_BASE_URL='https://user-confirmed-prod-gateway.example'
```

Do not hardcode personal filesystem paths or reusable environment URLs in the Skill. Do not infer one environment's URL from another. The client requires HTTPS and rejects base URLs containing credentials, query strings, or fragments.

Resolve the installed client without assuming a personal home directory:

```bash
GATEWAY_SKILL_DIR="${CODEX_HOME:-$HOME/.codex}/skills/gateway-api-debug"
GATEWAY_CLIENT="$GATEWAY_SKILL_DIR/scripts/call_gateway_api.py"
```

## Authentication Modes

Choose exactly one mode based on the confirmed gateway decision:

- `--auth no-token`: public or anonymous-optional request; sends neither bearer token nor guest header.
- `--auth guest`: confirmed guest-eligible path; sends `X-Guest-Mode: 1` and no bearer token.
- `--auth bearer`: required or user-context request; reads a token from an environment-specific variable or explicit private token file.

Token sources:

```bash
export GATEWAY_DEV_TOKEN='...'
export GATEWAY_UAT_TOKEN='...'
export GATEWAY_RC_TOKEN='...'
export GATEWAY_PROD_TOKEN='...'

# Alternative for one call
python3 "$GATEWAY_CLIENT" ... --auth bearer --token-file /approved/private/token
```

Never pass a token as a command argument, embed it in an `Authorization` command-line header, paste it into chat, or save it in this Skill, payload files, shared caches, or committed configuration. Do not extract browser credentials. If login is needed, use an existing approved login mechanism outside this Skill, then supply only its resulting token through an approved secret source.

On Unix-like systems, a token file must be private to its owner, such as mode `600`; the client rejects group- or world-accessible token files.

## Read-Only Calls

Customer guest request:

```bash
python3 "$GATEWAY_CLIENT" \
  --env dev \
  --profile customer \
  --method GET \
  --path /api/example \
  --auth guest \
  --query 'q=example'
```

Admin bearer request:

```bash
python3 "$GATEWAY_CLIENT" \
  --env uat \
  --profile admin \
  --method GET \
  --path /admin-api/example/123 \
  --auth bearer
```

Use repeated `--query key=value` arguments so the client encodes query values. Do not put query strings in `--path`. The profile and path prefix must match.

## Mutating Calls

After exact authorization, construct the smallest payload in a private temporary directory. For replace-style APIs, first read the current state and preserve all required fields.

```bash
PAYLOAD_DIR="$(mktemp -d)"
chmod 700 "$PAYLOAD_DIR"
PAYLOAD_FILE="$PAYLOAD_DIR/request.json"

python3 "$GATEWAY_CLIENT" \
  --env rc \
  --profile admin \
  --method PATCH \
  --path /admin-api/example/123 \
  --auth bearer \
  --payload-file "$PAYLOAD_FILE" \
  --allow-write
```

For an explicitly authorized production mutation, add `--allow-production`. Submit at most once unless the user explicitly authorizes a retry after the failure mode is understood. Read the resource back through the narrowest read-only endpoint and compare the intended fields. Remove sensitive temporary payloads when no longer needed.

## Client Guarantees and Limits

The bundled client:

- accepts only `GET`, `HEAD`, `OPTIONS`, `POST`, `PUT`, `PATCH`, and `DELETE`;
- requires explicit write and production gates;
- validates profile/path alignment and blocks path traversal;
- encodes query parameters separately;
- bounds timeout, payload size, and response size;
- uses verified TLS, bypasses ambient HTTP proxy settings, and never follows redirects;
- emits a JSON envelope with HTTP status, content type, selected trace headers, truncation state, and parsed JSON or text body;
- exits `3` for HTTP non-success responses and `2` for transport failures.

It does not prove that a request is semantically read-only, perform business login, select an environment, authorize a mutation, or retry requests. Those decisions remain part of the code inspection and user authorization boundary.

## Response Interpretation

- Confirm that the response status and content type match the endpoint contract before interpreting the body.
- Treat `401` as missing/invalid authentication and `403` as insufficient authorization unless current evidence proves another gateway behavior.
- Treat `3xx` as a stopped redirect, not permission to resend credentials to another URL.
- Treat `429` and `5xx` as server pressure/failure; do not rapidly retry or retry writes automatically.
- A business error inside HTTP `200` is still a failed business outcome when the API contract says so.
- A truncated response is a bounded sample, not a complete payload.

Report environment, profile, method, path, auth mode, whether bearer or guest headers were sent, HTTP/business result, relevant response fields, and trace ID. Redact tokens, cookies, credentials, personal data unrelated to the issue, and sensitive payload fields.

## Runtime Data and Logs

A gateway response may show symptoms without proving the downstream cause. Query databases, caches, centralized logs, or Kubernetes logs only when the user request and workspace policy place those systems in scope. Use the mandated workspace tool for each source, keep queries read-only and bounded, and do not treat access to the gateway as authorization for another system.

## Maintenance

- Keep `SKILL_zh.md`, `agents/openai.yaml`, the client, and integration tests in the package.
- Never restore machine-specific helper paths, token arguments, or shared token caches.
- Keep English and Chinese authorization, authentication, and production boundaries aligned.
- Run the official Skill validator, Python compile checks, integration tests, and a secret-pattern scan after changes.
