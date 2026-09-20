---
name: azure-aca-db-ops
description: Run authorized database queries or operations through an Azure Container Apps Job on host 237, using a one-off Python execution with UAT-first routing, secret-safe configuration, and execution-log verification. Use when the user asks to query a configured Azure DB through this Job without rebuilding the repository.
---

# Azure ACA DB Operations

Use this skill when the user wants to execute or verify a database operation through the `frch-aca-batch` Azure Container Apps (ACA) Job from host `237`. The normal application is a batch entrypoint with a hard-coded query; ad-hoc SQL should run as a separate one-off Python execution.

## Authorization and target

- Default to UAT. The verified UAT resource is `frch-aca-batch-uat` in `frch-rg-uat`.
- RC uses the UAT ACA Job and UAT execution resources, but its ad-hoc DB target is `yuanchuan3_rc`.
- UAT and RC permit read and write database operations when the current request identifies the exact operation and target. For UAT or RC writes, inspect the smallest required current state first, execute once, and read back the final state.
- Prod is strictly read-only under this skill. Refuse Prod `INSERT`, `UPDATE`, `DELETE`, DDL, stored procedures, and other mutations even when the user asks for them.
- Default to read-only when the requested operation is not explicit. Do not infer Prod authorization from an available Azure login or a screenshot.
- A Job execution is an external state change even when its SQL is read-only. Start one only when the user has requested the test or operation.
- Do not broaden a UAT or RC write into exploratory changes or additional statements.
- Never retrieve, print, paste, or persist passwords, access tokens, secret values, or connection strings.

## What the repository does

The image contains Python 3.11 and `mysql-connector-python`. The normal entrypoint is `python -m app.main`; it runs the repository's fixed query and then writes Blob logs and, when configured, a Report DB row. It is not a generic SQL endpoint.

For an ad-hoc query, override the execution command to a short Python script. This bypasses `app.main`, so the ad-hoc run does not perform the normal Blob or Report DB writes unless the temporary script explicitly does so.

The repository's optional `DB_NAME_RC=yuanchuan3_rc` setting is used by the normal entrypoint only for its separate `SELECT 1` RC connectivity check. It does not redirect the main query. For an ad-hoc RC query, use the UAT Job and set the temporary runner's `DB_NAME` to `yuanchuan3_rc`.

Use this verified target map directly by default; do not query Azure configuration before every execution:

| Environment | Job / resource group | Container / image | DB host / database | DB user / secret | Resources |
|---|---|---|---|---|---|
| UAT | `frch-aca-batch-uat` / `frch-rg-uat` | `frch-aca-batch-uat` / `frchacrshared.azurecr.io/frch-aca-batch:uat-177642` | `frch-db-mysql-uat.mysql.database.azure.com` / `yuanchuan3` | `frchsys` / `db-password` | 2 CPU, 4Gi |
| RC | `frch-aca-batch-uat` / `frch-rg-uat` | `frch-aca-batch-uat` / the verified UAT image | `frch-db-mysql-uat.mysql.database.azure.com` / `yuanchuan3_rc` | `frchsys` / `db-password` | 2 CPU, 4Gi |
| Prod | `frch-aca-batch-prod` / `frch-rg-prod` | `frch-aca-batch-prod` / `frchacrshared.azurecr.io/frch-aca-batch:prod-177645` | `frch-db-mysql-replica-prod.mysql.database.azure.com` / `yuanchuan3` | `frchsys` / `db-password` | 2 CPU, 4Gi |

These are verified baseline mappings, not secret values. Re-read the target Job configuration only when the user selects a different target, the stored mapping is suspected to have drifted, the image or secret reference is rejected, authentication fails, an execution setup fails, or an Azure response contradicts the map. Do not turn every normal query into a configuration discovery step.

Verified Azure context on `237`:

- Subscription: `c933afc7-a12a-4fc9-806d-637276545e3e`
- Tenant: `46f383c3-307b-4b11-9106-ef278b3c252d`
- Repo, when source inspection is needed: `/Users/tender/Documents/git/yc/frch-aca-batch`

Reuse this context without an account/resource preflight when the current target matches. Inspect it again only after an authentication error, subscription mismatch, or target change.

## Read-only preflight

When the target is unclear or a stored mapping needs verification, run Azure CLI on `237` with `/opt/homebrew/bin` in `PATH`:

```bash
ssh 237 'zsh -lc "PATH=/opt/homebrew/bin:$PATH az containerapp job show -n frch-aca-batch-uat -g frch-rg-uat"'
```

Inspect only the fields needed for the operation: current image, container name, command, resources, non-secret environment values, secret reference names, `triggerType`, and `manualTriggerConfig`. Do not print secret values. If the target or subscription is unclear, inspect the Azure account and resource mapping before starting; do not guess another environment.

The execution template does not reliably inherit the Job's environment when using a custom command. Include the required non-secret environment entries and the actual secret reference from the current Job configuration. Do not copy an internal or transformed secret reference from an execution response without checking the Job's `properties.configuration.secrets`.

The `containerapp` CLI extension is required for execution logs. If it is missing, pause for approval before installing or changing Azure CLI configuration on `237`.

As of verification, `237` has the preview `containerapp` extension installed. Do not reinstall or upgrade it on every query.

## Build and start a temporary Python execution

Use the current image and the Job's container name and resource settings. Prefer explicit columns and a bounded query, for example:

```sql
SELECT id FROM shop LIMIT 100
```

Avoid `SELECT *` unless the user explicitly needs every column. Do not interpolate untrusted values into SQL. Print only a row count and safe identifiers; do not print PII or full rows. A `LIMIT` without `ORDER BY` does not guarantee a stable row order.

Use an execution template, not the normal application entrypoint. A generic template shape is:

```yaml
containers:
- name: <current-container-name>
  image: <current-image>
  command:
  - python
  args:
  - -c
  - "import base64;exec(base64.b64decode('<base64-encoded-script>'))"
  env:
  - name: DB_HOST
    value: <current-non-secret-host>
  - name: DB_NAME
    value: <current-database>
  - name: DB_USER
    value: <current-user>
  - name: DB_PASSWORD
    secretRef: <current-secret-name>
  resources:
    cpu: <current-cpu>
    memory: <current-memory>
```

Submit the YAML to the authorized Job as a one-off execution, using `/dev/stdin` or a task-scoped temporary file. Keep the script and generated YAML out of the repository, and remove temporary files after use. The script should use SSL and a bounded connection timeout, for example `mysql.connector.connect(..., ssl_disabled=False, connection_timeout=15)`.

Use this minimal runner shape for a read-only query; replace only the explicit SQL and safe output fields:

```python
import os
import mysql.connector

connection = mysql.connector.connect(
    host=os.environ["DB_HOST"],
    port=int(os.getenv("DB_PORT", "3306")),
    database=os.environ["DB_NAME"],
    user=os.environ["DB_USER"],
    password=os.environ["DB_PASSWORD"],
    ssl_disabled=False,
    connection_timeout=15,
)
cursor = connection.cursor()
try:
    cursor.execute("SELECT id FROM shop LIMIT 100")
    rows = cursor.fetchall()
    print("row_count=%d" % len(rows))
    print("ids=%s" % [row[0] for row in rows])
finally:
    cursor.close()
    connection.close()
```

When the user requests several queries against the same environment, prefer one temporary Python execution that opens one DB connection and runs the queries sequentially. This avoids paying the ACA Job startup and connection setup cost for every query. Label every result with a stable query number or name, print only the requested bounded output, and keep each SQL statement separate so one result cannot be mistaken for another. Do not batch different target environments in one execution. For UAT or RC writes, batch only the explicitly authorized statements and retain the required preflight/read-back; Prod remains read-only.

The Azure CLI parser may treat `-c` as its own option, and a custom start without an explicit image does not reliably apply the command override. Use the YAML execution-template path with the current image and `/dev/stdin`; do not spend retries changing `--args` quoting.

Do not use the repository's normal `app.main` for an ad-hoc SQL test: its query is fixed and it has additional Blob/Report DB side effects.

## Efficient execution flow

Optimize the workflow at the Job-execution level, not by weakening verification:

1. Group all queries for one environment into one temporary Python runner and reuse one DB connection. Keep UAT and RC in separate executions because they target different databases.
2. For read-only queries, use the verified target map directly. Do not create a separate schema-inspection execution unless the query requires it or the target mapping is uncertain.
3. For an authorized UAT or RC write, put the required preflight, mutation, read-back, and cleanup in the same execution. Do not pay for a separate preflight Job execution.
4. Start one execution and retain the returned execution name. Keep the synchronous start path by default so the execution can be tracked unambiguously; do not use `--no-wait` when it would require guessing the latest execution in a concurrent environment.
5. Check execution status with bounded backoff and stop when it reaches a terminal state. Do not poll in a tight loop or repeat a status request while the previous request is still in flight. Once terminal, read logs once. If the execution remains running after the bounded checks, report that it is still running instead of starting a duplicate execution.

## Verify the execution

Record the returned execution name. Poll its status:

```bash
az containerapp job execution show \
  --name <job-name> \
  --resource-group <resource-group> \
  --job-execution-name <execution-name> \
  --query properties.status -o tsv
```

After a replica exists, read its logs:

```bash
az containerapp job logs show \
  --name <job-name> \
  --resource-group <resource-group> \
  --execution <execution-name> \
  --container <container-name> \
  --tail 100
```

Report the exact environment, image, execution name, SQL scope, status, row count, and relevant error. If no replica exists, inspect the execution template and status; do not claim the SQL ran. Distinguish a failed execution setup from a database or SQL error.

## Concurrency and safety

`manualTriggerConfig.parallelism=1` means one replica per execution; it does not prove that separate manual executions are globally serialized. Each concurrent execution can open its own MySQL connection and consume ACA and database capacity. Keep ad-hoc queries bounded and avoid concurrent heavy scans.

This mechanism does not enforce read-only SQL. Anyone allowed to start the Job can potentially run code with the Job's DB permissions. Use it only for trusted, explicitly authorized operations; for recurring multi-user use, provide a constrained runner with a read-only DB account and an SQL allowlist.

Stop on an unexpected resource, image, secret reference, authentication result, SQL error, or target environment. Do not retry by changing the query, credentials, or environment without resolving the mismatch.

## remark 
Azure Container Apps = ACA
