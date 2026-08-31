# Branch Promotion Workflow

Use this workflow after the user has explicitly named the target branch. Commands below illustrate the required checks; adapt paths and validation to the repository.

## Command Display Requirement

Immediately before each Git invocation, print the fully resolved command in Codex commentary. Use absolute paths with `git -C` and show each command in execution order. Do this for read-only inspection, merge preparation, cleanup, retries, and pushes. Never execute an undisclosed Git command or conceal Git calls in a loop or helper script.

For example, display:

```bash
git -C /absolute/repository/path fetch origin nacos-sit develop
git -C /absolute/repository/path rev-list --left-right --count origin/develop...origin/nacos-sit
```

Then execute those exact commands. If any argument changes, display the revised command first.

## 1. Resolve Scope

For each repository, record:

- absolute repository path;
- remote name;
- source branch;
- target branch;
- inspect, prepare, or push intent;
- merge-commit permission;
- validation command.

If source is omitted, resolve it with `git branch --show-current`. A detached HEAD cannot supply a default source branch. Never default the target branch.

Check `git status --short --branch`, configured remotes, and whether the source and target refs exist. Existing worktree changes belong to the user and must remain untouched.

## 2. Refresh and Compare

Fetch only the required branches where practical:

```bash
git -C <absolute-repository-path> fetch <remote> <source> <target>
```

Resolve immutable commits:

```bash
git -C <absolute-repository-path> rev-parse <remote>/<source>
git -C <absolute-repository-path> rev-parse <remote>/<target>
git -C <absolute-repository-path> merge-base <remote>/<target> <remote>/<source>
git -C <absolute-repository-path> rev-list --left-right --count <remote>/<target>...<remote>/<source>
```

For the last command, the left count is target-only commits and the right count is source-only commits.

| Left | Right | Relation | Action |
|---:|---:|---|---|
| 0 | 0 | Identical | No-op |
| 0 | N | Source ahead | Fast-forward target |
| N | 0 | Target ahead | No promotion needed |
| N | M | Diverged | Merge commit only with explicit permission |

Also inspect:

```bash
git -C <absolute-repository-path> log --oneline <remote>/<target>..<remote>/<source>
git -C <absolute-repository-path> diff --stat <remote>/<target>...<remote>/<source>
git -C <absolute-repository-path> diff --name-status <remote>/<target>...<remote>/<source>
```

Use three-dot diff for changes introduced from the merge base. If histories are unrelated, stop.

For multi-repository requests, complete this preflight for every repository before preparing any merge.

## 3. Prepare in an Isolated Worktree

Create a narrowly scoped temporary directory and attach a detached worktree at the fetched target commit:

```bash
promotion_dir=$(mktemp -d /tmp/branch-promote.XXXXXX)
git -C <absolute-repository-path> worktree add --detach <absolute-promotion-path> <remote>/<target>
```

Record the exact directory. Do not use the user's existing checkout for the merge.

For source-ahead-only branches:

```bash
git -C <absolute-promotion-path> merge --ff-only <remote>/<source>
```

For diverged branches, only after explicit merge-commit authorization:

```bash
git -C <absolute-promotion-path> merge --no-ff --no-edit <remote>/<source>
```

On conflict, abort the merge, report conflicted paths, and stop. Do not resolve conflicts automatically.

## 4. Validate

Run repository-specific tests or builds inside the temporary worktree. Inspect the prepared diff and commit graph. Verify the fetched target commit has not changed before push:

```bash
git -C <absolute-repository-path> fetch <remote> <target>
git -C <absolute-repository-path> rev-parse <remote>/<target>
```

If it differs from the recorded preflight target commit, stop and reclassify the branches.

## 5. Push Only When Authorized

Push the prepared commit without force:

```bash
git -C <absolute-promotion-path> push <remote> HEAD:refs/heads/<target>
```

If the push is rejected because the branch is protected or changed concurrently, stop. Create or update a merge request only when separately requested.

Multi-repository pushes are not atomic. Prepare and validate all repositories first, then report each successful push immediately so a later failure cannot hide partial completion.

## 6. Cleanup and Report

Remove only the recorded worktree and temporary directory after capturing results:

```bash
git -C <absolute-repository-path> worktree remove <absolute-promotion-path>
```

If ordinary removal fails, inspect the worktree before considering force removal. Never delete a broad directory or an unresolved path.

Report immutable source, original target, and resulting target commit IDs; relation counts; merge strategy; validation; push result; and any remaining blockers.
