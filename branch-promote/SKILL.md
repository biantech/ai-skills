---
name: branch-promote
description: Inspect and promote Git changes from an explicit source branch into an explicit target branch across one or more repositories, committing and publishing current source work first, refreshing the local target, validating the merge, and pushing only when authorized. Use when the user asks to compare, merge, or promote branches. Do not use to infer release targets or trigger deployments.
---

# Branch Promote

Use this Skill to make branch promotion deliberate and auditable. Read [references/workflow.md](references/workflow.md) before performing a promotion or handling diverged branches.

## Required Scope

Resolve these values before any merge:

- operation: inspect only, prepare a merge, or prepare and push;
- repositories in scope;
- execution host: current machine, or `server237` for `uat`/`rc` targets unless the request explicitly says local/current machine;
- source remote and target remote; do not assume one remote serves both branches;
- source branch, defaulting to the current named branch only after reporting that choice;
- target branch, which must always be explicitly provided by the user;
- whether a merge commit is allowed when branches have diverged;
- commit message for pending source changes, or permission to generate a concise message;
- validation required before push;
- whether pushing or creating the remote source branch is authorized;
- whether pushing the target branch is authorized.

Do not infer a target branch from names such as Dev, SIT, UAT, RC, or Prod. Permission to merge does not imply permission to push either branch, create a merge request, trigger Jenkins, or deploy. One user statement may authorize both source and target pushes only when it explicitly names or clearly covers both branches.

## Environment Remote and Host Rules

For this repository layout, use the following mapping unless the user explicitly overrides it:

- `sit` is read from and, when authorized, published to `origin` (the company GitLab remote).
- For the default `server237` workflow, `uat` and `rc` are read from and, when authorized, published to `github` (the GitHub remote).
- A default remote promotion from `sit` to `uat` or `rc` therefore compares `origin/sit` with `github/uat` or `github/rc`; never substitute `github/sit`, `origin/uat`, or `origin/rc`.
- For `uat` or `rc` targets, use `ssh server237` and `/Users/tender/Documents/git/yc/<repository>` by default. If the request explicitly says `local`, `本地`, `本机`, or `current machine`, use the current checkout, use `origin` for both source and target, and do not SSH.
- `server237` is an execution host choice, not permission to push. Source and target pushes still require separate authorization.

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
- Resolve the execution host and the source/target remotes before the first Git command. For remote execution, print the complete `ssh server237 'git -C /Users/tender/Documents/git/yc/<repository> ...'` command before running it.
- For merge operations, require the current named branch to be the source branch. Inspect and commit all non-ignored source changes before switching branches; do not stash or discard them.
- Show status and both staged and unstaged diffs before staging. Use `git add -A`, show the staged summary, and commit with the user-provided or generated message. If there are no pending changes, skip the commit.
- Refresh the source and target refs from their respective remotes after the source commit and compare local source with the configured source remote. If the local source has unpublished commits, obtain source-push authorization and push them before merging; without authorization, stop on the source branch. Never push when the remote source is ahead or diverged.
- After publishing, verify local source equals remote source and classify the fresh remote target against the fresh remote source.
- Switch the selected execution checkout to the target branch, update it from the configured target remote with `git pull --ff-only`, then merge the local source branch into it.
- For multiple repositories, inspect and commit every source and classify every local-source/remote-source relation before the first source push. After publishing all sources, classify every remote-source/remote-target relation before the first merge.
- Never interpret any difference as automatic permission to merge.
- Never force-push, rewrite history, auto-resolve conflicts, delete branches, or bypass protected-branch policy.
- If a target ref changes after preflight, stop and re-evaluate; do not retry a rejected push automatically.
- If the target branch is checked out in another worktree, its local branch has diverged from the remote, or switching would overwrite files, stop and report instead of resetting, stashing, or forcing the switch.

## Branch Relations

Classify `remote/target...remote/source` before acting, after the current source changes have been committed and the source branch has been published:

- identical: report a no-op;
- source ahead only: fast-forward promotion is allowed when requested;
- target ahead only: source is already contained, so do not merge backwards;
- diverged: require explicit permission for a merge commit;
- unrelated history or conflict: stop and report.

For inspect-only requests, report the relation, ahead/behind counts, commits, and changed-file summary, then stop without merging.

## Promotion Outcome

After an authorized source push succeeds, switch the current checkout to the target branch, fast-forward it from the fresh remote target, merge the local source according to the classified relation, and run repository-appropriate validation. Push the prepared target only with separate target-push authorization. Leave the checkout on the target branch and report that final state.

For multiple repositories, report that source and target pushes are not atomic across repositories. Stop after any failed push and identify which source or target branches were already updated.

Jenkins builds remain a separate operation. After a successful push, use `jenkins-api-build` only when the user has separately authorized the environment, projects, modules, and optional gateway build.

## Reporting

Report per repository:

- local and remote source, original remote target, and resulting target commit IDs;
- source commit message and source push result;
- branch relation and ahead/behind counts;
- merge strategy used;
- validation command and result;
- whether source and target pushes occurred and their resulting commits;
- final checked-out branch;
- conflicts, protected-branch rejection, concurrent updates, or remaining local changes.
