---
name: azure-appinsights-query
description: Run bounded, read-only Azure Application Insights KQL queries for UAT, RC, or Prod through the authenticated Azure CLI session on host 237. Use for terminal-based log investigation when the target environment and subscription are known; do not use for Dev logs or Azure resource changes.
---

# Azure Application Insights query

Query UAT, RC, and Prod logs through the existing Azure CLI session on SSH host `237`. Route Dev container-log investigations to `$kuboard-log`. Never expose tokens, secrets, cookies, or one-time authentication codes.

## Required scope

Obtain the environment, expected Azure subscription ID or name, local time range, and investigation question before querying. The helper enforces this reviewed environment mapping and verifies the live resource identity:

| Environment | Resource group | Application Insights resource |
|---|---|---|
| UAT | `frch-rg-uat` | `frch-appinsights-uat` |
| RC | `frch-rg-uat` | `frch-appinsights-rc` |
| Prod | `frch-rg-prod` | `frch-appinsights-prod` |

Treat the table as installation defaults, not evidence that the resource exists. The script binds every Azure CLI call to the requested subscription and stops on any identity mismatch. It never changes the active subscription.

## Query workflow

1. Convert the user's time range to an intended UTC half-open interval `[start, end)`. Use the task timezone when supplied; otherwise use the workspace timezone. Include `timestamp >= start and timestamp < end` with the mode-appropriate timestamp field in KQL; the API bounds are an additional outer limit. Report both the source timezone and converted UTC bounds.
2. Put the smallest useful KQL in a private UTF-8 file. Do not place sensitive identifiers or KQL in shell history. The script rejects empty files, files over 64 KiB, Kusto control commands, broad `search`, and `union *`.
3. Run the helper from this skill directory:

   ```bash
   python3 scripts/query_appinsights_via_237.py \
     --environment prod \
     --subscription '<expected-subscription-id-or-name>' \
     --start-time '<start-utc-iso8601>' \
     --end-time '<end-utc-iso8601>' \
     --max-rows 100 \
     --query-file '/private/path/query.kql'
   ```

The helper verifies the subscription and Application Insights resource, detects workspace-based versus classic mode, applies the API time bounds, and appends a final `take` limit. A final `take` bounds returned rows, not scanned data; keep filters selective and aggregate first when possible. The JSON result reports the resolved subscription, mode, time scope, row count, whether the limit was reached, rows, or a categorized error.

Use `AppTraces` with `TimeGenerated`, `AppRoleName`, `OperationId`, and `Message` for workspace-based resources. Use `traces` with `timestamp`, `cloud_RoleName`, `operation_Id`, and `message` for classic resources. Because mode is discovered at execution time, begin with schema-neutral aggregation where practical; if a table mismatch fails, use the reported mode to revise the query.

## Authentication and failures

- Use only the existing authenticated Azure CLI context. If the result is `authentication_required`, stop and ask the user or an authorized operator to restore the session through the approved channel.
- Do not run `az login`, select a subscription, install extensions, or update shared host authentication unless the user explicitly requests and authorizes that state change. Never relay or persist a device code.
- If SSH fails, report the bounded error and stop. Do not redirect the query to another host unless the user explicitly places it in scope.
- If the resource is absent or mismatched, stop. Do not search other subscriptions or substitute a similarly named resource.
- If no rows are returned, report the exact environment, subscription, UTC interval, table, and filters before proposing a broader query.
- Keep results concise. Truncate or summarize long messages and large `customDimensions` unless the user needs the raw field.
- Label conclusions as `[QUERY]` for returned evidence, `[LOGIC]` for code-based reasoning, and `[ASSUME]` for unverified assumptions.
