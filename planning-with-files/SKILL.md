---
name: planning-with-files
description: Use persistent Markdown planning files to coordinate substantial multi-step implementation or research that must survive context compaction or session handoff. Use when the user asks for a written plan, the work spans several dependent phases, or durable findings and progress records are materially useful. Do not use for simple questions, quick lookups, or narrow edits that do not need persistent coordination.
allowed-tools: "Read Write Edit Bash Glob Grep"
metadata:
  version: "3.11.3"
---

# Planning with Files

Keep the durable state of a substantial task in Markdown files instead of relying only on the context window.

Chinese documentation is maintained in [SKILL_zh.md](SKILL_zh.md). Keep it aligned whenever this file changes.

## Choose a Storage Mode

Use the least complex mode that fits the task:

- Root mode: `task_plan.md`, `findings.md`, and `progress.md` in the project root. Use for one active task in one session.
- Isolated mode: `.planning/<plan-id>/` with `.planning/.active_plan`. Use for concurrent tasks or when root-level planning files would be intrusive.
- Autonomous mode: isolated or root mode with an attested plan, nonce framing, and ledger summary.
- Gated mode: autonomous mode plus a bounded Stop gate while a phase is explicitly `in_progress`.

Initialize with the bundled script:

```bash
PWF_SKILL_DIR="${CODEX_HOME:-$HOME/.codex}/skills/planning-with-files"

# Root mode
sh "$PWF_SKILL_DIR/scripts/init-session.sh"

# Isolated mode
sh "$PWF_SKILL_DIR/scripts/init-session.sh" "Backend Refactor"

# Autonomous or gated mode
sh "$PWF_SKILL_DIR/scripts/init-session.sh" --autonomous "Long Run"
sh "$PWF_SKILL_DIR/scripts/init-session.sh" --gated "Gated Run"
```

Use the PowerShell equivalents on Windows.

## Core Files

| File | Durable content | Update when |
|------|-----------------|-------------|
| `task_plan.md` | Goal, phases, current status, decisions | Phase or approach changes |
| `findings.md` | Requirements, research, discoveries | A finding will affect later work |
| `progress.md` | Actions, verification, relevant failures | A meaningful unit of work completes |

Record information because it will help resume or coordinate the task. Do not log every tool call, transient error, or already-visible detail.

## Workflow

1. Inspect existing planning state before creating files. If a plan already exists, resume it unless the user requests a new one.
2. Write a concise goal and only the phases needed for the current task. Keep exactly one active phase when practical.
3. Re-read the plan before a major decision or after context loss, not mechanically before every action.
4. Update findings and progress at meaningful checkpoints. Keep the plan consistent with the implementation and test results.
5. Before finishing, verify the deliverable and mark completed phases accurately. A pending future phase is not a reason to claim current work is complete.

After a context reset or handoff, run the recovery helper when session history may contain unsynchronized work:

```bash
python3 "$PWF_SKILL_DIR/scripts/session-catchup.py" "$(pwd)"
```

Then reconcile its report with the current files and repository diff.

## Multiple Plans and Sessions

Plan resolution order is:

1. `PWF_PLAN_ROOT` project-root pin
2. `PLAN_ID` under `.planning/`
3. `.planning/.active_plan`
4. Newest valid `.planning/<plan-id>/`
5. Root-level `task_plan.md`

Set `PLAN_ID` when multiple plans exist. Set `PWF_PLAN_ROOT` to an absolute project directory when the process working directory is a shared parent.

When `.planning/sessions/` exists, hooks inject context only for an attached session. The adapter passes the hook payload session ID as `PWF_SESSION_ID`; the matching sentinel is `.planning/sessions/<session-id>.attached`.

Set `PLANNING_DISABLED=1` for one-shot or CI invocations that must not consume nearby planning state.

## Attestation and Gated Mode

Autonomous and gated plans must be attested. Initialization attests the initial plan automatically. After intentionally editing an attested plan, review it and re-attest:

```bash
sh "$PWF_SKILL_DIR/scripts/attest-plan.sh"
```

Hooks must use `scripts/inject-plan.sh` for UserPromptSubmit, PreToolUse, and PreCompact. Do not add another implementation that reads and injects `task_plan.md` directly, because that bypasses attestation, mode, nonce, and ambiguity checks.

The gated Stop path must call `scripts/check-complete.sh --gate` and forward the original Stop payload on stdin. The gate is bounded by recursion, stall, and block-count guards; it does not authorize unrelated work or override user instructions.

## Hook Installation

`hooks.json` describes the Codex hook registration. Its commands expect hook adapters in either:

- `<project>/.codex/hooks/`
- `$HOME/.codex/hooks/`

The adapters expect this skill under the corresponding `skills/planning-with-files/` directory, or `PWF_SCRIPT_DIR` may point to its `scripts/` directory. Installing only `SKILL.md` does not install global hooks automatically.

Run the diagnostic from a project root when hook behavior is unclear:

```bash
sh "$PWF_SKILL_DIR/scripts/plan-doctor.sh"
```

## Supporting Resources

- Use [templates/task_plan.md](templates/task_plan.md), [templates/findings.md](templates/findings.md), and [templates/progress.md](templates/progress.md) as starting shapes, not mandatory forms.
- Read [references/examples.md](references/examples.md) when a concrete filled example would help.
- Read [references/reference.md](references/reference.md) only when the background principles are relevant.

## Maintenance Invariants

- Keep `SKILL_zh.md` and `agents/openai.yaml` in the package.
- Keep English and Chinese instructions behaviorally aligned.
- Keep one canonical implementation for plan resolution, injection, and completion gating.
- Run the official Skill validator, syntax checks, and `tests/test_hook_integration.py` after changing hooks or scripts.
