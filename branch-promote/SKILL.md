---
name: branch-promote
description: Inspect and promote committed Git changes from an explicit source branch into an explicit target branch across one or more repositories, with fresh remote-state checks, branch-relation classification, isolated worktrees, validation, and separately authorized pushes. Use when the user asks to compare, merge, or promote branches. Do not use to infer release targets or trigger deployments.
---

# Branch Promote

Use this Skill to make branch promotion deliberate and auditable. Read [references/workflow.md](references/workflow.md) before performing a promotion or handling diverged branches.

## Required Scope

Resolve these values before any merge:

- operation: inspect only, prepare a merge, or prepare and push;
- repositories in scope;
- remote, defaulting to `origin` only when it exists;
- source branch, defaulting to the current named branch only after reporting that choice;
- target branch, which must always be explicitly provided by the user;
- whether a merge commit is allowed when branches have diverged;
- validation required before push;
- whether pushing the target branch is authorized.

Do not infer a target branch from names such as Dev, SIT, UAT, RC, or Prod. Permission to merge does not imply permission to push, create a merge request, trigger Jenkins, or deploy.

## Git Command Transparency

Before executing every agent-initiated Git command, print the exact command in Codex commentary. This applies to read-only and mutating commands, including status, fetch, rev parsing, diff, log, worktree, merge, push, cleanup, and any retry.

- Show resolved repository paths, remotes, branches, refs, and arguments; do not leave placeholders or hidden shell variables in the displayed command.
- Prefer `git -C <absolute-repository-path> ...` so the execution context is visible in the command itself.
- When several Git commands are ready, they may be shown together in one shell block in their exact execution order, one command per line.
- Execute only the commands that were displayed. If a command changes, print the revised command before running it.
- Do not hide Git invocations inside scripts, shell functions, loops, aliases, command substitutions, or pipelines unless every fully expanded Git command is printed first.
- Never print credential-bearing URLs or secrets. Use configured remote names and secure credential mechanisms; if an exact command would expose a secret, do not run it in that form.

## Safety Rules

- Read repository instructions and inspect status before fetching or merging.
- Preserve dirty worktrees. Perform promotion in a temporary Git worktree based on the fresh remote target branch.
- Compare remote refs after `git fetch`; do not promote stale local refs.
- Promote committed, pushed source changes. Report local-only commits or uncommitted changes instead of silently including them.
- Preflight every requested repository before the first merge or push.
- Never interpret any difference as automatic permission to merge.
- Never force-push, rewrite history, auto-resolve conflicts, delete branches, or bypass protected-branch policy.
- If a target ref changes after preflight, stop and re-evaluate; do not retry a rejected push automatically.
- Remove only the exact temporary worktree created for the operation.

## Branch Relations

Classify `remote/target...remote/source` before acting:

- identical: report a no-op;
- source ahead only: fast-forward promotion is allowed when requested;
- target ahead only: source is already contained, so do not merge backwards;
- diverged: require explicit permission for a merge commit;
- unrelated history or conflict: stop and report.

For inspect-only requests, report the relation, ahead/behind counts, commits, and changed-file summary, then stop without merging.

## Promotion Outcome

Prepare the target in an isolated worktree, merge according to the classified relation, and run repository-appropriate validation before any push. Push only the prepared commit to the explicitly named target branch and only with user authorization.

For multiple repositories, report that pushes are not atomic across repositories. Stop after any failed push and identify which targets were already updated.

Jenkins builds remain a separate operation. After a successful push, use `jenkins-api-build` only when the user has separately authorized the environment, projects, modules, and optional gateway build.

## Reporting

Report per repository:

- source and target remote refs and commit IDs;
- branch relation and ahead/behind counts;
- merge strategy used;
- validation command and result;
- whether a target push occurred and its resulting commit;
- conflicts, protected-branch rejection, concurrent updates, or remaining local changes.
