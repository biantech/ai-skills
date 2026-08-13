---
name: db-tools
description: "MANDATORY primary tool for querying live data across ALL services under `/Users/bianjq/yuanchuan/`. Invoking `db_query_helper.py` provides ground-truth data and eliminates guesswork — it MUST be used over inference whenever real records are involved."
---

## Description

**This skill is the MANDATORY primary tool for querying live data across all
services under `/Users/bianjq/yuanchuan/`**, covering:

`activity`, `authentication`, `common`, `content`, `file`, `finance`,
`gateway-app`, `location`, `marketing`, `merchant`, `note`, `order`, `push`,
`ranking`, `recommend`, `reservation`, `review`, `search`, `task`, `user`,
and any future modules.

Invoking `db_query_helper.py` provides ground-truth data and eliminates
guesswork — it **MUST** be used over inference whenever real records are
involved.

Direct `mysql` CLI is permitted only under the conditions defined in the
[Fallback: Direct MySQL CLI](#fallback-direct-mysql-cli) section. Outside
those conditions, `db_query_helper.py` is the **required** method.

This skill is **NOT** required for:
- Explaining SQL syntax or query patterns in the abstract
- Discussing table schema or field semantics conceptually
- Pure code logic analysis that does not depend on live data

---

## Trigger Scenarios

### 🔴 MUST Invoke — Real Data Required

#### Cross-Project / Universal

- Verifying any specific record by ID after a code change (any module/table)
- Validating an enum / status / `active` field matches code expectation
- Confirming presence/absence of a record when a query unexpectedly returns empty
- Verifying foreign key relationships (e.g. `shop_id` ↔ `merchant_id`)
- Confirming schema state after `ALTER TABLE` / new column / new index
- Validating MyBatis Mapper XML produces correct results against real data
- Confirming Repository persistence behavior in `*RepositoryImplTest` /
  `*MapperTest` execution
- Comparing `debug/*.json` snapshots with current DB state

#### `push` / `notification` — Messaging

- Verifying `userId` / `userPersonId` / `businessAccountId` mapping
- Confirming a notification message was actually saved or delivered
- Checking `notification_template.channels` matches code routing
  (e.g. `["push"]` vs `["sms"]`)
- Validating `notification_template_channel.content` placeholders
  (e.g. `{tiny_url}`, `{orderNo}`)
- Confirming `notification_template.active` / `open_status` / channel `active`
- Inspecting `notification_delivery_record` status & `error_message`

#### `merchant` — Merchant & Shop

- Confirming `merchant_operation_account` ↔ business account ↔ shop mapping
- Verifying shop assignments to groups, regions, categories
- Checking `merchant_shop.active` after batch updates
- Validating shop tag / label / category code references

#### `ranking` — Ranking System

- Verifying `dp_rank_detail` records by `rank_type` (`GOOD`, `POPULAR`,
  `S500WAN`, `S500PAN`, `S500TIAN`)
- Confirming `dp_rank_precomputed_scores` consistency vs `dp_rank_detail`
- Checking `MIN(id)` / `MAX(id)` per `rank_type` before cleanup operations
- Validating S500-series data is NOT touched by maintenance tasks
- Inspecting `sub_category_code` (year) distribution per shop

#### `order` / `reservation` / `finance` — Transactional

- Confirming order / payment / refund state for a specific `orderNo`
- Verifying reservation slot availability and `active` state
- Checking finance ledger entries match expected business operations

#### `activity` / `marketing` — Campaigns

- Verifying campaign / coupon / voucher `active`, `start_at`, `end_at`
- Confirming user participation records and reward issuance
- Checking marketing rule / segment / audience definitions

#### `user` / `authentication` — Identity

- Verifying user account state, role assignments, permission grants
- Confirming OAuth / session / token records
- Checking user group membership and tenant binding

#### `content` / `note` / `review` / `search` / `recommend`

- Confirming content publish state, visibility, moderation status
- Verifying review / note `active` and association with shop / user
- Checking search/recommend index source data matches DB state

### 🟡 STRONGLY RECOMMENDED — Ambiguity Exists

- User asks "should this ID be X or Y?" → query instead of inferring
- Code was just modified → check DB state before/after
- User mentions a specific ID (userId, shopId, groupId, messageId, orderNo)
- Conversation contains: `@env devdb`, `@env dev001`, `查資料庫`,
  `資料庫確認`, `驗證數據`, `對齊快照`, `debug/*.json`

### 🟢 NO Invocation Needed — Answer Directly

- "What does the `business_module` field mean?" — semantic explanation
- "How do I write a JOIN between these tables?" — SQL pattern question
- "Why does MyBatis use TypeHandler for enums?" — framework knowledge
- Reviewing code logic without referencing specific record IDs

---

## Environment Specification

| Group  | Aliases                              | Host                     | Schema       |
|--------|--------------------------------------|--------------------------|--------------|
| LOCAL  | `local`, `devdb`, `db191`            | `57.155.71.191:33336`    | `yuanchuan3` |
| DEV001 | `dev001`, `dev236`, `db236`, `236`   | `192.168.110.236:3306`   | `yuanchuan3` |

### Environment Inference Rules

| Conversation Signal                                              | Resolved Env |
|------------------------------------------------------------------|--------------|
| `@env local`, `@env devdb`, `@env db191`, 本地環境, local 環境   | `local`      |
| `@env dev001`, `@env dev236`, `@env 236`, DEV001, 236環境        | `dev001`     |
| _(no mention)_                                                   | `local` (default) |

> ⚠️ **Anti-confusion warning**: `devdb` and `db191` are aliases for
> **local (191 external)**, NOT for `dev001` (236 internal). Do not conflate
> them despite the `dev` / `191` substrings.

---

## Parameters

### `--env` _(optional, default: `local`)_
Infer from conversation context using the table above.

### `--sql` _(required)_
- Always add `LIMIT` (recommended `<= 50`) unless doing `COUNT` / aggregation
- Prefer explicit column names over `SELECT *`
- **Read-only only** — never `INSERT` / `UPDATE` / `DELETE`

### `--format` _(optional, default: `markdown`)_
- `markdown` — human-readable table output (default)
- `json` — structured data; use only when parsing programmatically

---

## Invocation

### Standard Form (Required Default)

Resolve `<skill-dir>` to the directory containing this `SKILL.md`. Resolve the
helper relative to that directory; do not assume the current working directory
is the skill directory and do not substitute a copied helper from another
location.

```bash
python3 <skill-dir>/db_query_helper.py \
  --env {env} \
  --sql "{sql}" \
  --format {format}
```

### Pre-flight Checklist

- [ ] `--env` resolved from conversation context (default `local`)
- [ ] `--sql` uses explicit columns and includes `LIMIT` (unless aggregating)
- [ ] `--format` set to `markdown` for analysis, `json` for parsing
- [ ] Query is **read-only** (`SELECT` only)

### Mandatory Pre-Query Declaration

When the query relates to **SQL analysis, Mapper/XML generation, Repository
code, unit tests, schema changes, or snapshot validation**, output the
environment declaration at the top of the reply:

```
> 🗄️ 環境：[local|dev001] | 項目：[project-name] | 配置：[relative path] | 數據源：[JDBC URL]
```

---

## Fallback: Direct MySQL CLI

Direct terminal `mysql` commands are permitted **only when ALL** of the
following conditions are met:

1. `db_query_helper.py` fails to execute (Python runtime error, missing
   dependency, script crash) — **attach the error output as evidence**
2. The query is read-only (`SELECT` only)
3. The response includes a fallback notice in this **exact** format:

   ```
   > [FALLBACK] db_query_helper.py unavailable — reason: {error summary}
   > Direct CLI used for env: {local|dev001}
   ```

### Credential Handling in Fallback Mode

- Never embed passwords in plain shell arguments (avoid `-p{password}`)
- Use `--defaults-extra-file` or prompt interactively (`-p` with no value)
- Do not log or display the connection string in the response

---

## Output Handling

After receiving script output:

1. **Preserve the metadata header verbatim** — the
   `> **Env** | **Rows** | **Time** | **At**` line **MUST** appear in the
   analysis response. Never omit or summarize it.
2. **Display the Markdown table as-is** — do not reformat or condense it.
3. **Analyze results in context of the current task**:
   - Verifying mapping → compare actual vs expected; state match/mismatch
   - Checking status → flag `active=0` or missing records and explain impact
   - Schema validation → confirm columns / types / indexes match migration
   - 0 rows returned → state "No records found"; verify env / filter correctness
4. **If the query fails (non-zero exit)** → report the error; suggest
   correcting SQL or switching env.

### Expected Output Format (Metadata Header Mandatory)

```
> **Env**: local | **Rows**: 2 | **Time**: 1.2s | **At**: 2026-05-14 15:00:00

| id  | user_id | business_module | active |
| --- | ------- | --------------- | ------ |
| 101 | 2764    | RESERVATION     | 1      |
```

---

## Common Query Templates

### Universal — Schema & Metadata

```sql
-- Inspect column definitions for any table
SELECT column_name, column_type, is_nullable, column_default, column_comment
FROM information_schema.columns
WHERE table_schema = 'yuanchuan3' AND table_name = '{table_name}'
ORDER BY ordinal_position;

-- List indexes on a table
SELECT index_name, column_name, non_unique
FROM information_schema.statistics
WHERE table_schema = 'yuanchuan3' AND table_name = '{table_name}'
ORDER BY index_name, seq_in_index;
```

### `push` / `notification`

```sql
-- Verify userId / userPersonId mapping
SELECT id AS business_account_id, user_person_id, name, phone
FROM merchant_operation_account WHERE id = {businessAccountId};

-- Check notification messages for a user
SELECT id, user_id, business_module, active, created_at
FROM notification_message
WHERE user_id = {userId} ORDER BY created_at DESC LIMIT 20;

-- Verify notification template channel config
SELECT template_code, channels, active, open_status
FROM notification_template
WHERE template_code = '{templateCode}' LIMIT 5;

-- Inspect channel content and placeholders
SELECT id, template_code, channel_type, channel_template_code,
       title, content, link, active
FROM notification_template_channel
WHERE template_code = '{templateCode}'
ORDER BY channel_type LIMIT 20;

-- Check delivery record status
SELECT id, message_id, channel_type, status, error_message, created_at
FROM notification_delivery_record WHERE message_id = {messageId};
```

### `ranking`

```sql
-- Count and ID range per rank_type
SELECT rank_type, COUNT(*) AS cnt, MIN(id) AS min_id, MAX(id) AS max_id
FROM dp_rank_detail
WHERE rank_type IN ('GOOD', 'POPULAR', 'S500WAN', 'S500PAN', 'S500TIAN')
GROUP BY rank_type ORDER BY rank_type;

-- S500 distribution by year
SELECT rank_type, sub_category_code, COUNT(*) AS cnt
FROM dp_rank_detail
WHERE rank_type LIKE 'S500%'
GROUP BY rank_type, sub_category_code
ORDER BY rank_type, sub_category_code DESC LIMIT 20;
```

### `merchant`

```sql
-- Inspect shop core fields
SELECT id, shop_name, city_id, district_id, main_category_code, active
FROM merchant_shop WHERE id = {shopId};

-- Inspect user group definition
SELECT id, group_name, active FROM user_group_list WHERE id = {groupId};
```

### `order` / `reservation`

```sql
-- Order status by order number
SELECT id, order_no, user_id, shop_id, status, payment_status, created_at
FROM order_main WHERE order_no = '{orderNo}' LIMIT 5;

-- Reservation slot availability
SELECT id, shop_id, slot_date, slot_time, capacity, booked, active
FROM reservation_slot WHERE shop_id = {shopId} AND slot_date = '{date}' LIMIT 20;
```

### `activity` / `marketing`

```sql
-- Active campaign window check
SELECT id, name, start_at, end_at, active
FROM activity_campaign WHERE id = {campaignId} LIMIT 5;
```

### `user` / `authentication`

```sql
-- Account state and tenant binding
SELECT id, phone, email, status, tenant_id, active, created_at
FROM user_account WHERE id = {userId} LIMIT 5;
```

---

## Cross-Reference

- Use the environment aliases and safeguards defined in this skill as the
  authoritative database-query instructions.
- Use the active global and project `AGENTS.md` files for project conventions.
