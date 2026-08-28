---
name: minimal-query-planner
description: Plan and run narrowly scoped, read-only queries against databases, caches, and search systems when runtime evidence is needed for debugging or investigation. Use to minimize query cost, data exposure, and production impact through explicit target selection, schema-aware filters, bounded retrieval, and incremental escalation. Do not use for ordinary code inspection or any write, repair, migration, or cleanup operation.
---

# Minimal Query Planner

Gather the smallest amount of runtime evidence that can answer the investigation question without treating a response limit as a scan-cost limit.

The Chinese version is maintained in [SKILL_zh.md](SKILL_zh.md). Keep both files behaviorally aligned.

## Establish the Boundary

Before querying, determine:

- the hypothesis and the observation that would confirm or reject it;
- the authoritative data source;
- the exact environment, cluster, database, index, table, or key namespace;
- the approved query mechanism and available read-only credentials.

Do not infer an environment from names such as `dev`, `local`, or `prod`. Follow workspace instructions and user-provided mappings. If the target remains ambiguous and querying the wrong system would matter, ask before execution.

Querying live data is authorized only when the user request and workspace policy place that data source in scope. This skill does not authorize production access, permission escalation, or use of credentials discovered in files.

## Plan by Cost, Not Only Output Size

Use this progression when each step is relevant:

1. Inspect existing code, schema definitions, mappings, or documented key shapes.
2. Inspect lightweight metadata needed to choose a selective access path.
3. Run a point lookup or highly selective bounded query.
4. Broaden one dimension at a time only when the previous result is inconclusive.

Estimate the expensive part of the operation: rows or documents examined, keys traversed, shards contacted, fields loaded, aggregation buckets, sorting, and lock or timeout risk. `LIMIT`, Elasticsearch `size`, and Redis `SCAN COUNT` bound returned batches or provide hints; they do not guarantee bounded server work.

Prefer a cheaper query plan even when two queries return the same number of records. Use an explain facility when it is non-executing and useful. Do not use `EXPLAIN ANALYZE` or an equivalent that executes the query unless its execution cost is understood and explicitly in scope.

## Read-Only Safety

Use only operations whose semantics are known to be read-only for the target system. Do not run:

- inserts, updates, deletes, DDL, repairs, cache invalidation, reindexing, or administrative changes;
- locking reads such as `FOR UPDATE`, explicit locks, or long-lived transactions;
- stored routines, user-defined functions, scripts, or commands that may have side effects;
- broad exports or retrieval of secrets, credentials, tokens, or unnecessary personal data.

Apply server-side timeouts or cancellation limits when supported. Select only fields needed for the hypothesis, redact sensitive values in reports, and never paste credentials into the query transcript.

## Data-Source Guidance

### SQL Databases

- Prefer equality or narrow range predicates on indexed columns, known primary keys, or selective composite-index prefixes.
- Inspect the access plan when predicate selectivity or index use is uncertain.
- Select named columns and add a deterministic order when result ordering matters.
- Use a small `LIMIT`, but reject a plan that still scans an unacceptably large relation.
- For pagination, prefer keyset predicates over a large `OFFSET`.
- Avoid leading-wildcard searches, functions or casts on indexed filter columns, unbounded joins, and unnecessary counts over large ranges.

### Redis and Similar Key-Value Stores

- Prefer exact keys. Check key type before choosing a read command; inspect TTL or memory size only when relevant.
- Do not use `KEYS` against a live shared instance.
- Use incremental `SCAN` only with a narrow pattern and a client-side stopping condition. Treat `COUNT` as a hint.
- Bound collection reads. Avoid potentially large `HGETALL`, `SMEMBERS`, `LRANGE 0 -1`, or equivalent whole-value retrieval until size is known and justified.

### Elasticsearch and Similar Search Systems

- Name the narrowest index or alias and use exact term/range filters where mappings support them.
- Request only required fields, set a small `size`, and set a timeout when supported.
- Disable or bound exact total-hit counting when the exact count is not evidence the investigation needs.
- Avoid broad wildcards, regexes, scripts, deep pagination, unrestricted multi-index searches, and high-cardinality aggregations without a cost justification.
- Check mappings before choosing `term`, full-text, sorting, or aggregation fields.

For another system, apply the same model: identify its unit of work, choose a selective access path, bound returned data, and add an execution guard where available.

## Incremental Escalation

If a query is inconclusive:

1. State what evidence is still missing.
2. Change one scope dimension, such as time range, identifier set, fields, index, or sample size.
3. Explain why the broader query is expected to resolve the ambiguity.
4. Stop when evidence is sufficient or the next query's cost is disproportionate.

Do not repeat an expensive query unchanged unless transient behavior makes the retry meaningful.

## Reporting

Keep the report proportional to the investigation. For each material query, retain enough detail to reproduce and evaluate it:

- target and environment, without secrets;
- hypothesis;
- exact read-only query or command;
- cost controls and relevant access-plan observation;
- result summary and conclusion: `confirmed`, `rejected`, or `inconclusive`;
- next smallest query, only when needed.

Use the query tool mandated by the current workspace. Otherwise prefer an existing project helper or purpose-built connector over inventing a new client. Do not hardcode machine-specific paths in reusable instructions.

## Maintenance

- Keep `SKILL_zh.md` and `agents/openai.yaml` in the package.
- Keep English and Chinese safety boundaries aligned.
- Validate the Skill after changing frontmatter or instructions.
