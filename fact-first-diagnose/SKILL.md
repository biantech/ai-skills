---
name: fact-first-diagnose
description: Diagnose bugs and anomalous behavior by separating conclusions provable from code, specifications, or focused tests from claims that require runtime evidence. Use when debugging may depend on records, cache or index contents, effective configuration, feature flags, traffic shape, or other live state; do not use for ordinary code explanation or implementation-only requests.
---

# Fact-first diagnosis

Build the diagnosis from evidence and keep its boundary visible. A diagnosis request authorizes read-only inspection needed to identify the cause; it does not by itself authorize code changes, data changes, cache eviction, restarts, configuration changes, or other remediation.

## Classify claims

Treat a claim as logic-provable only when the available code, specification, mathematics, compiler output, or focused test demonstrates it without assuming live state. Typical examples include syntax and type errors, an unconditional null dereference, a deterministic boundary error, or documented API misuse. A test supports only the behavior and inputs it actually covers.

Treat a claim as runtime-dependent when its truth can change without a code change. Examples include:

- whether a record exists or has a particular value;
- effective configuration, feature flags, routing, or deployed version;
- cache contents, expiry, hit state, or consistency with the source of truth;
- search-index contents or lag;
- ranking output, data distribution, traffic volume, or observed latency;
- the state and timing of an external dependency.

Do not infer runtime state from code defaults, migrations, fixtures, snapshots, or intended configuration. Conversely, a runtime observation alone does not prove which code path caused it; connect the observation to the relevant logic before assigning causality.

## Investigation workflow

1. Establish the observed and expected behavior, environment, time window, identifiers, and recent changes. Do not silently substitute another environment.
2. Trace the smallest relevant code path and record what it proves. Identify each remaining assumption that depends on runtime state.
3. Turn the leading assumptions into falsifiable hypotheses. Choose the least invasive evidence that can distinguish them.
4. Inspect live state only when it is necessary, available, and within the user's scope. Start with metadata or health checks, then a bounded sample or aggregate, then one focused verification. Avoid broad scans.
5. Stop when the evidence supports a cause at the confidence stated. If evidence is unavailable or conflicting, report the unresolved assumption and the minimal next check instead of presenting certainty.

Prefer existing logs, traces, metrics, and read-only queries. Preserve the original time zone and report converted boundaries when correlating systems. Redact credentials, tokens, personal data, and unrelated payload fields from commands and results.

## Runtime evidence routing

- For real MySQL records or schema under `/Users/bianjq/yuanchuan/`, invoke `$db-tools` and follow its environment, read-only SQL, limit, and output requirements. Resolve its helper relative to that Skill rather than assuming a working directory or copying the helper elsewhere.
- For Redis, Elasticsearch, configuration services, logs, traces, or metrics, use a source-specific read-only tool only when it is available and the target system and environment are in scope. `$db-tools` is not evidence for these systems.
- Do not access Production merely because it would provide stronger evidence. Use it only when the user has placed it in scope and the applicable tool or project policy permits the read-only inspection.
- Do not write data, flush caches, rebuild indexes, change flags, restart services, or generate diagnostic traffic unless the user separately requests and authorizes that action.
- If no approved route exists, provide the exact minimal query or observation needed, with placeholders instead of secrets, and leave the claim unverified.

## Report the diagnosis

Lead with the most consequential supported finding. For each conclusion, state the evidence source and distinguish what is demonstrated from what remains inferred. Include the relevant environment and time window for runtime evidence, and include reproducible commands actually used when they are safe to share.

When the cause is not established, say so directly. Rank remaining hypotheses by the evidence already available and name the smallest next check that could change the diagnosis. Do not bury contradictory evidence or turn the absence of evidence into evidence of absence.
