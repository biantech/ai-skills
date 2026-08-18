---
name: azure-appinsights-terminal-query
description: Run read-only Azure Application Insights KQL queries from terminal through an authenticated Azure CLI session on host 237, including device-code login, subscription and resource discovery, non-interactive PATH handling, timezone conversion, and concise sampled results. Use when UI access is unavailable or the user asks to inspect Prod, UAT, or RC logs from terminal.
---

# Azure Application Insights terminal query

Use this skill for read-only log investigation for UAT, RC, and Prod through the Azure CLI session on `237`. Dev logs use the Kuboard log skill. Do not expose access tokens, client secrets, cookies, or one-time device codes.

## Environment routing

Use Azure Application Insights for UAT, RC, and Prod. Confirm the live Application Insights resource before querying:

| Environment | Application Insights resource |
|---|---|
| UAT | `frch-appinsights-uat` |
| RC | `frch-appinsights-rc` |
| Prod | `frch-appinsights-prod` |

Do not use this skill for Dev. Query Dev container logs through the Kuboard log skill instead.

## Workflow

1. Confirm the SSH connection and Azure context:

   ```bash
   ssh -o BatchMode=yes -o ConnectTimeout=8 237 'zsh -lc "PATH=/opt/homebrew/bin:$PATH az account show --query \"{subscription:name,tenant:tenantId,user:user.name}\" -o json"'
   ```

2. If the Azure context is expired, start device-code login on `237`:

   ```bash
   ssh -tt 237 'zsh -lc "PATH=/opt/homebrew/bin:$PATH az login --use-device-code"'
   ```

   Tell the user to open the URL printed by Azure and enter the one-time code shown in that same terminal. Never copy the code into a response or persist it. Select the intended subscription after login.

3. Verify Application Insights access without printing the token:

   ```bash
   ssh 237 'zsh -lc "PATH=/opt/homebrew/bin:$PATH az account get-access-token --resource https://api.applicationinsights.io/ --query tokenType -o tsv"'
   ```

4. Discover the actual Application Insights resource and resource group. Do not infer the environment from the app name alone:

   ```bash
   ssh 237 'zsh -lc "PATH=/opt/homebrew/bin:$PATH az resource list --resource-type Microsoft.Insights/components --query \"[].{name:name,resourceGroup:resourceGroup,location:location}\" -o table"'
   ```

   Known resources in the FAR-REACH subscription have included:

   - Prod: `frch-appinsights-prod` / `frch-rg-prod`
   - UAT: `frch-appinsights-uat` / `frch-rg-uat`
   - RC: `frch-appinsights-rc` / `frch-rg-uat`

   Recheck the live resource list before querying.

5. Query with the smallest useful KQL. The bundled script detects whether the Application Insights component is workspace-based. For workspace-based resources it queries the bound Log Analytics workspace; otherwise it uses the Application Insights component API:

   ```bash
   python3 scripts/query_appinsights_via_237.py \
     --resource-group frch-rg-prod \
     --app frch-appinsights-prod \
     --query-file /path/to/query.kql
   ```

   The script sets `/opt/homebrew/bin` in the remote `PATH`; this is required because Azure CLI may invoke `az` internally when loading the Application Insights command extension. It resolves `properties.WorkspaceResourceId` and the workspace `customerId` read-only before choosing the query command.

## KQL practices

- Treat Application Insights timestamps as UTC. For a Beijing day, convert `00:00` to the previous day at `16:00Z`; state the conversion in the result.
- Always bound the time range.
- Prefer `summarize count()` or `take 5` before returning message bodies.
- For workspace-based resources, query `AppTraces` and project `TimeGenerated`, `AppRoleName`, `OperationId`, and `Message`.
- For classic Application Insights resources, query `traces` and project `timestamp`, `cloud_RoleName`, `operation_Id`, and `message`.
- Order samples explicitly, usually by the table's timestamp field descending.
- Avoid dumping full Elasticsearch DSL or large `customDimensions` unless the user specifically needs it; truncate or summarize long messages.
- Separate `[QUERY]` evidence from `[LOGIC]` code conclusions and `[ASSUME]` unverified assumptions.

Useful minimal queries:

```kusto
AppTraces
| where AppRoleName == "search"
| where TimeGenerated between (datetime(2026-08-06 16:00:00) .. datetime(2026-08-07 16:00:00))
| summarize logCount=count() by bin(TimeGenerated, 1h)
| order by TimeGenerated desc
```

```kusto
AppTraces
| where AppRoleName == "search"
| where TimeGenerated between (datetime(2026-08-06 16:00:00) .. datetime(2026-08-07 16:00:00))
| project TimeGenerated, OperationId, Message
| order by TimeGenerated desc
| take 5
```

When querying a classic Application Insights resource, use the equivalent `traces` schema instead. Do not mix `traces` field names with `AppTraces` queries: the tables use different field names and are served by different Azure CLI query commands.

## Failure handling

- If SSH fails, stop and report the connection failure.
- If Azure login is required, pause for the user to complete device-code login.
- If the resource is missing, list resources and stop; do not guess another subscription or environment.
- If KQL returns no rows, report the exact scope and query assumptions before expanding the time range.
- Keep all operations read-only; do not create, update, delete, or reconfigure Azure resources.
