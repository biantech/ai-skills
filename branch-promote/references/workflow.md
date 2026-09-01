# Branch Promotion Workflow

Use this workflow after the user has explicitly named the target branch. Commands below illustrate the required checks; adapt paths and validation to the repository.

## Remote and Execution Selection

Resolve these values before any Git invocation:

- source branch `sit`: source remote is `origin`;
- target branch `uat` or `rc`: target remote is `github` when using the default `server237` workflow;
- target `uat` or `rc`: execute on `server237` in `/Users/tender/Documents/git/yc/<repository>` unless the request explicitly says `local`, `本地`, `本机`, or `current machine`;
- explicit local requests use the current checkout and `origin` for both source and target, so `sit -> uat/rc` compares `origin/sit` with `origin/uat` or `origin/rc` and does not SSH.

For the default `server237` workflow, `sit -> uat` or `sit -> rc` compares `origin/sit` with `github/uat` or `github/rc`. For an explicit local workflow, compare `origin/sit` with `origin/uat` or `origin/rc`. Do not use `github/sit`.

## Command Display Requirement

Immediately before each Git invocation, print the fully resolved command in Codex commentary. Use absolute paths with `git -C` and show each command in execution order. Do this for read-only inspection, merge preparation, cleanup, retries, and pushes. Never execute an undisclosed Git command or conceal Git calls in a loop or helper script.

For example, for a `sit -> uat` promotion on `server237`, display:

```bash
ssh server237 'git -C /Users/tender/Documents/git/yc/review fetch origin sit'
ssh server237 'git -C /Users/tender/Documents/git/yc/review fetch github uat'
ssh server237 'git -C /Users/tender/Documents/git/yc/review rev-list --left-right --count github/uat...origin/sit'
```

Then execute those exact commands. If any argument changes, display the revised command first.

## 1. Resolve Scope

For each repository, record:

- absolute repository path;
- source remote and target remote;
- execution host and absolute repository path;
- source branch;
- target branch;
- inspect, prepare, or push intent;
- merge-commit permission;
- source-change commit message, or permission to generate one;
- source-push authorization;
- target-push authorization;
- validation command.

If source is omitted, resolve it with `git branch --show-current`. A detached HEAD cannot supply a default source branch. Never default the target branch.

Check `git status --short --branch`, configured remotes, and whether the source and target refs exist on their configured remotes. For a merge operation, the selected checkout's current named branch must be the source branch. A different current branch is a blocker; do not move its pending changes to the requested source.

## 2. Commit Current Source Changes

Skip this section for inspect-only requests. Before switching away from the source branch, inspect all pending changes:

```bash
git -C <absolute-repository-path> status --short --branch
git -C <absolute-repository-path> diff --stat
git -C <absolute-repository-path> diff --cached --stat
git -C <absolute-repository-path> diff --name-status
git -C <absolute-repository-path> diff --cached --name-status
```

If there are tracked or untracked changes, stage all non-ignored changes, show exactly what will be committed, and create one source commit:

```bash
git -C <absolute-repository-path> add -A
git -C <absolute-repository-path> status --short
git -C <absolute-repository-path> diff --cached --stat
git -C <absolute-repository-path> commit -m "<resolved-commit-message>"
```

Use the user's commit message when provided. Otherwise generate a concise message from the staged change. Do not commit ignored files, empty commits, conflict markers, known credentials, or files that are clearly unrelated to the requested work; stop and report when the pending change set is unsafe or ambiguous. Do not amend an existing commit.

Record the resulting local source commit.

For multiple repositories, complete source inspection, commit preparation, and local-source/remote-source classification for every repository before the first source push. Do not begin publishing while another repository may still reveal a source conflict or unsafe pending change set.

## 3. Refresh and Publish the Source

Fetch the source and target from their respective remotes:

```bash
git -C <absolute-repository-path> fetch <source-remote> <source>
git -C <absolute-repository-path> fetch <target-remote> <target>
```

Compare the local source with the fresh remote source:

```bash
git -C <absolute-repository-path> rev-parse <source>
git -C <absolute-repository-path> rev-parse <source-remote>/<source>
git -C <absolute-repository-path> rev-list --left-right --count <source-remote>/<source>...<source>
```

For the last command, the left count is remote-only and the right count is local-only:

- `0 0`: source is already published; no source push is needed.
- `0 N`: local source is ahead; source-push authorization is required.
- `N 0`: local source is behind; stop and report.
- `N M`: local and remote source diverged; stop and report.

When the remote source does not exist, treat it as unpublished and require explicit authorization to create it. Do not infer source-push authorization from permission to commit, merge, or push the target.

After source-push authorization, publish without force:

```bash
git -C <absolute-repository-path> push <source-remote> <source>:refs/heads/<source>
```

If source push is required but not authorized, stop on the source branch and request authorization. If the push is rejected, stop; do not retry by force or rewrite history.

Refresh both branches and verify the source was published exactly:

```bash
git -C <absolute-repository-path> fetch <source-remote> <source>
git -C <absolute-repository-path> fetch <target-remote> <target>
git -C <absolute-repository-path> rev-parse <source>
git -C <absolute-repository-path> rev-parse <source-remote>/<source>
```

The local and remote source commit IDs must match before proceeding.

## 4. Compare the Published Source and Target

Resolve immutable remote commits:

```bash
git -C <absolute-repository-path> rev-parse <source-remote>/<source>
git -C <absolute-repository-path> rev-parse <target-remote>/<target>
git -C <absolute-repository-path> merge-base <target-remote>/<target> <source-remote>/<source>
git -C <absolute-repository-path> rev-list --left-right --count <target-remote>/<target>...<source-remote>/<source>
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
git -C <absolute-repository-path> log --oneline <target-remote>/<target>..<source-remote>/<source>
git -C <absolute-repository-path> diff --stat <target-remote>/<target>...<source-remote>/<source>
git -C <absolute-repository-path> diff --name-status <target-remote>/<target>...<source-remote>/<source>
```

Use three-dot diff for changes introduced from the merge base. If histories are unrelated, stop.

For multi-repository requests, complete this published-source/target comparison for every repository before preparing any merge.

## 5. Switch to and Refresh the Target

The source worktree must now be clean. Switch this checkout to the local target branch. If it does not exist, create it to track the fresh remote target:

```bash
git -C <absolute-repository-path> switch <target>
```

or:

```bash
git -C <absolute-repository-path> switch --track -c <target> <target-remote>/<target>
```

Pull the remote target into the local target without creating a pull merge commit:

```bash
git -C <absolute-repository-path> pull --ff-only <target-remote> <target>
```

If switching fails because the target is checked out in another worktree, or the pull cannot fast-forward because the local target diverged, stop. Do not reset, stash, delete, or force anything.

Verify the checked-out target equals the remote target recorded during preflight before merging.

## 6. Merge the Local Source into the Target

For source-ahead-only branches:

```bash
git -C <absolute-repository-path> merge --ff-only <source>
```

For diverged branches, only after explicit merge-commit authorization:

```bash
git -C <absolute-repository-path> merge --no-ff --no-edit <source>
```

If the user explicitly requires a merge commit even when fast-forward is possible, use `merge --no-ff --no-edit <source>` only after recording that choice. On conflict, show status, abort the merge, report conflicted paths, and stop. Do not resolve conflicts automatically.

## 7. Validate

Run repository-specific tests or builds on the checked-out target. Inspect the prepared diff and commit graph. Verify the remote target has not changed before push:

```bash
git -C <absolute-repository-path> fetch <target-remote> <target>
git -C <absolute-repository-path> rev-parse <target-remote>/<target>
```

If it differs from the recorded preflight target commit, stop and reclassify the branches.

## 8. Push the Target Only When Authorized

Push the prepared commit without force:

```bash
git -C <absolute-repository-path> push <target-remote> HEAD:refs/heads/<target>
```

If the push is rejected because the branch is protected or changed concurrently, stop. Create or update a merge request only when separately requested.

Multi-repository pushes are not atomic. Report each successful source and target push immediately so a later failure cannot hide partial completion. Prepare and validate every target before the first target push.

Target-push authorization is independent of source-push authorization. If target push is not authorized, leave the validated merge on the local target branch and report that it is pending authorization.

## 9. Report

Leave the repository checked out on the target branch. Report the local and remote source commits, original remote target, resulting local target, and pushed target commit IDs; relation counts; source commit message; both push authorizations and results; merge strategy; validation; final current branch; and any remaining blockers.
