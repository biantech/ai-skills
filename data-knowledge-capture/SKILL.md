---
name: data-knowledge-capture
description: Find and preserve reusable knowledge from completed data work, including sanitized SQL or scripts, data-flow and schema notes, business rules, validation steps, and operational risks. Use when the user asks to reuse prior data-task knowledge or explicitly save a completed data workflow for future use; do not trigger for every SQL, debugging, import, export, or data-analysis task.
---

# Data knowledge capture

Support two distinct operations: read-only discovery of relevant prior knowledge and explicitly authorized persistence of reusable knowledge. Invoking this Skill does not authorize unrelated data-system access, rerunning captured operations, or writing to a knowledge repository unless the user asked to save or update it.

## Resolve the knowledge repository

Use a repository path supplied by the user or established by the active workspace. The installation-specific candidate is `/Users/bianjq/data/data-knowledge`, but it may not exist and must not be assumed portable.

- For discovery, stop with a concise notice if the resolved directory does not exist. Do not create it as a side effect of searching.
- For persistence, a request merely to analyze, review, or summarize permits an in-chat summary only. Write files only when the user explicitly asks to save, capture, persist, or update reusable knowledge.
- If persistence is requested but no repository has been agreed, confirm the destination before creating a directory outside the current workspace.
- Inspect an existing task directory before editing it. Preserve unrelated and manually maintained content; update only the relevant artifacts and do not silently overwrite a name collision.

## Discover prior knowledge

Search only when the current request calls for prior-knowledge reuse. Start with filenames and focused terms from the business object, source system, transformation, and output. Read only the most relevant `summary.md`, `.sql`, or `.py` files rather than loading the whole repository.

Treat prior artifacts as leads, not current truth. Verify environment, schema, columns, dependencies, assumptions, and safety before adapting them. Report which artifact was reused and what changed. If nothing relevant exists, continue without creating placeholders.

## Decide what to retain

Persist an artifact only when it would materially reduce future work by preserving at least one of these:

- a repeatable import, export, cleaning, matching, mapping, or validation pattern;
- a parameterized SQL or script with stable inputs and outputs;
- a verified schema relationship, business rule, data flow, or execution order;
- preview, validation, idempotency, rollback, or operational safeguards;
- a recurring manual decision that suggests a grounded platform capability.

Skip persistence when the result is only a fixed one-time ID or value list, generated output reproducible from a retained upstream artifact, raw execution evidence, or narration without reusable logic. When persistence was explicitly requested but skipped, state the reason.

## Sanitize before persistence

Retain knowledge, not live data. Before writing or copying any artifact:

- remove credentials, tokens, cookies, private keys, connection strings, signed URLs, and secret-bearing commands;
- exclude raw database rows, production exports, logs, query-result dumps, and personal or confidential data; use synthetic or redacted examples;
- replace environment-specific IDs, paths, dates, hosts, indexes, and table targets with documented parameters when that preserves the pattern;
- review scripts for embedded secrets, implicit destructive defaults, network calls, and external side effects;
- do not preserve production mutation SQL as a ready-to-run command. Parameterize it, mark it unsafe by default, and document preview, validation, idempotency, and rollback expectations when known;
- record unknowns as unknown. Do not invent execution results, schemas, platform requirements, or rollback guarantees.

Copy or extract a script only when the repository copy is the useful reusable artifact. Record the original source path and, when available, its revision or capture date for provenance. Do not copy temporary scripts, dependencies, raw inputs, generated outputs, or multiple artifacts that express the same logic.

## Artifact layout

Use one short lowercase task slug and keep the directory small:

```text
<knowledge-root>/<task-slug>/
|-- summary.md
|-- reusable_script.py   # only when justified
`-- reusable_query.sql   # only when justified
```

Do not create placeholders. Prefer `summary.md` plus the smallest set of core artifacts.

The summary should cover only applicable sections:

```markdown
# Task name

## Purpose and reuse conditions
## Scope, provenance, and assumptions
## Inputs, schemas, and editable parameters
## Data flow and business rules
## Reusable scripts or SQL
## Usage and adaptation
## Validation and expected outputs
## Risks, idempotency, and rollback
## Platform opportunities
```

Platform opportunities are hypotheses grounded in repeated manual work, not approved architecture. Omit that section when the task provides no credible signal.

## Complete the capture

Compare the saved summary and reusable artifacts with the completed task. Run local syntax or dry-run validation when it is safe and meaningful, but do not reconnect to services or rerun external operations merely to validate the capture. Report the repository path, files created or updated, sanitization or generalization performed, validation completed, and any remaining assumptions.
