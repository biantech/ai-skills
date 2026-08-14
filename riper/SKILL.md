---
name: riper
description: "Apply the RIPER five-phase workflow to complex engineering tasks that need disciplined research, option analysis, planning, implementation, and review. Use only when the user explicitly invokes $riper or asks for a RIPER or RIPER-5 workflow. Do not trigger for ordinary coding tasks."
---

# RIPER5 Software Workflow

Use five visible phases to keep complex engineering work grounded in evidence and aligned with the user's request.

For a Chinese reference summary of the original Augment guidelines, see [skill-zh.md](skill-zh.md).

## Usage


```text
$riper 帮我分析并实现这个需求：...
$riper 只分析这个问题，不修改代码：...
$riper 审查当前改动并按严重程度报告问题。
```

## Core Rules

- Follow the user's request and every active `AGENTS.md` instruction.
- Match effort to task complexity. Keep each phase concise for narrow changes.
- State the current phase as `[RIPER: PHASE]` in progress updates.
- Report findings and decisions without exposing private chain-of-thought.
- Preserve existing user changes and avoid unrelated refactoring.
- Do not create branches, task files, commits, or pushes unless the user explicitly requests them.
- Treat phase boundaries as checkpoints, not permission gates. If the user requests implementation, continue through the phases without requiring special transition commands.
- Stop at the phase implied by the request. Analysis stops after Research or Innovate, planning stops after Plan, and review does not modify code unless the user also requests fixes.

## Phase 1: Research

Label the phase `[RIPER: RESEARCH]`.

Build an evidence-based understanding before proposing or changing anything.

1. Read the relevant instructions, implementation, call chain, configuration, and tests.
2. Inspect repository status and preserve existing uncommitted work.
3. Identify the requested behavior, current behavior, constraints, dependencies, and unknowns.
4. Use authoritative tools or live data when the task requires them; do not infer facts that can be verified.
5. Ask a question only when missing information would materially change the result and cannot be discovered locally.

Do not edit files during this phase.

## Phase 2: Innovate

Label the phase `[RIPER: INNOVATE]`.

Explore viable approaches when the solution is not obvious.

1. Compare the smallest credible options.
2. Evaluate correctness, compatibility, maintainability, risk, and verification cost.
3. Prefer existing project patterns and dependencies.
4. Recommend one approach and state the important tradeoffs.

Skip this phase when there is only one straightforward implementation. Do not edit files during this phase.

## Phase 3: Plan

Label the phase `[RIPER: PLAN]`.

Turn the selected approach into an executable plan.

1. Define the files and components in scope.
2. Describe behavioral and contract changes.
3. Include error handling, migration, and compatibility work when relevant.
4. Define verification that matches the change's risk.
5. Keep the plan ordered, concrete, and limited to necessary work.

For substantial tasks, present the plan before editing. For narrow tasks, keep the plan in a short progress update and continue.

## Phase 4: Execute

Label the phase `[RIPER: EXECUTE]`.

Implement only when the user's request authorizes changes.

1. Apply the planned changes using the repository's established style.
2. Keep every changed line traceable to the requested outcome.
3. Add comments only where they clarify non-obvious logic.
4. Avoid placeholders, incomplete paths, speculative features, and unverified dependencies.
5. Run focused checks as changes are completed.
6. If evidence invalidates the plan, explain the change and return briefly to Research or Plan before continuing.

Do not stage, commit, or push unless explicitly requested.

## Phase 5: Review

Label the phase `[RIPER: REVIEW]`.

Verify the result against both the request and repository standards.

1. Inspect the final diff and confirm no unrelated files changed.
2. Check behavior, edge cases, error handling, compatibility, and security implications.
3. Run the tests, linting, builds, or targeted commands appropriate to the change.
4. Report failures honestly and distinguish implementation defects from environment limitations.
5. Confirm whether the requested outcome is complete.

When the user asks for a code review, lead with findings ordered by severity and include file and line references.

## Final Response

Summarize the outcome, important files changed, and verification performed. Mention remaining risks or unrun checks. Keep the response proportional to the work and do not require the user to read earlier progress updates.
