---
name: jenkins-api-build
description: Inspect, trigger, and track configured Jenkins Dev, UAT, and RC jobs through the Jenkins Remote Access API, including validated parameterized module builds and dependency-aware build chains. Use when the user explicitly requests a Jenkins build or asks for queue/build status on a supported job. Do not use to infer deployment intent, trigger unspecified environments or parameters, alter job configuration, or perform Jenkins administration.
---

# Jenkins API Build

Use the bundled client for the configured Jenkins controller. Treat every build POST as an external side effect; inspection and status requests are read-only.

The Chinese version is maintained in [SKILL_zh.md](SKILL_zh.md). Keep both files behaviorally aligned.

## Authorization Boundary

Before triggering a build, require the user to specify or clearly confirm:

- environment: `dev`, `uat`, or `rc`;
- project or Job;
- API module parameters, when applicable;
- whether the gateway build is required.

Do not infer a build request from code changes, a debugging request, or permission to inspect Jenkins. Do not silently add modules, `--gateway`, another environment, or a retry. A failed or unstable build does not authorize rerunning it.

The client refuses duplicate queue/build activity by default. Set `JENKINS_ALLOW_DUPLICATE=1` only when the user explicitly requests an additional build despite an existing queued or running instance.

## Configured Targets

Default controller:

```text
https://jenkins-dev.goldenmilestech.net
```

| Environment | Jenkins view | Default user | Job suffix |
|---|---|---|---|
| Dev | `view/dev` | `bianjq` | `-dev` |
| UAT | `view/uat` | `tengxq` | `-uat` |
| RC | `view/rc` | `tengxq` | `-rc` |

Supported project aliases:

- `search` -> `search-jar-<environment>`
- `3rd-modules` -> `3rd-modules-<environment>`
- `gateway` -> `gateway-app-jar-<environment>`

API names such as `search` and `user` are Boolean parameters on `3rd-modules-<environment>`. The client reads live parameter definitions and rejects names that are not defined Boolean parameters.

The controller and usernames may be overridden only through approved environment configuration. `JENKINS_BASE_URL` must remain a single HTTPS origin without a path.

## Credentials

Never store Jenkins API tokens in this Skill, the script, source files, chat, command output, or a committed configuration file. If a token has previously appeared in any of those locations, treat it as compromised and rotate it in Jenkins; removing current text does not revoke it or erase history.

Configure one of these approved sources:

```bash
# Direct environment variables supplied by a secret manager or private shell setup
export JENKINS_DEV_TOKEN='...'
export JENKINS_UAT_RC_TOKEN='...'

# Or explicit private single-line token files
export JENKINS_DEV_TOKEN_FILE='/approved/private/dev-token'
export JENKINS_UAT_RC_TOKEN_FILE='/approved/private/uat-rc-token'
```

Optional username overrides are `JENKINS_DEV_USER` and `JENKINS_UAT_RC_USER`.

Do not ask the user to paste a token into chat. Disable shell tracing while handling credentials. The client passes Basic Auth through `curl --config -` and removes token variables from the child `curl` environment so the token is not placed in its argument list.

## Client Setup

Resolve the installed Skill path without hardcoding a personal home directory:

```bash
JENKINS_SKILL_DIR="${CODEX_HOME:-$HOME/.codex}/skills/jenkins-api-build"
JENKINS_CLIENT="$JENKINS_SKILL_DIR/scripts/jenkins-dev.sh"
```

The client requires `zsh`, `curl`, and `jq`.

## Read-Only Inspection

Inspect the resolved Job before a build or when the user asks about configuration:

```bash
"$JENKINS_CLIENT" inspect uat search
```

The result includes buildability, queue state, the last build, and parameter definitions. Confirm that the resolved Job and environment match the request.

Query a known queue item or build:

```bash
"$JENKINS_CLIENT" queue-status uat 1234
"$JENKINS_CLIENT" status uat search 237
```

Queue IDs and build numbers must be decimal integers. The client validates queue and executable URLs against the configured Jenkins origin and expected Job before reusing credentials.

## Trigger Builds

Trigger one target Job:

```bash
"$JENKINS_CLIENT" build rc search
```

Trigger one or more validated module parameters:

```bash
"$JENKINS_CLIENT" build-modules dev search user
```

Each POST requests a fresh CSRF crumb immediately before enqueueing. A successful POST returns a same-origin queue ID and URL; it does not yet prove that a build started or succeeded.

## Dependency-Aware Chain

For a supported API change, use:

```bash
"$JENKINS_CLIENT" build-api uat search
"$JENKINS_CLIENT" build-api rc search --gateway
```

`build-api` performs a preflight before the first side effect, then executes this state machine:

1. Trigger the selected `3rd-modules` parameter.
2. Wait for its queue item to resolve to the expected build.
3. Wait for that build to finish with `SUCCESS`.
4. Trigger and wait for the target Job.
5. Only after target `SUCCESS`, optionally trigger and wait for gateway.

If any step is cancelled, times out, or finishes with another result, downstream Jobs are not queued. Do not replace this dependency check with immediate enqueue order; separate Jenkins Jobs are not guaranteed to serialize into a successful dependency chain merely because POST requests were sent in sequence.

## Bounded Waiting

Use the explicit wait commands when tracking a previously returned ID:

```bash
"$JENKINS_CLIENT" wait-queue uat search 1234
"$JENKINS_CLIENT" wait-build uat search 237
```

Defaults:

- `JENKINS_QUEUE_TIMEOUT_SECONDS=300`
- `JENKINS_BUILD_TIMEOUT_SECONDS=1800`
- `JENKINS_POLL_INTERVAL_SECONDS=5`

The script validates bounded ranges for these values. Increase a timeout only when the user still wants the current operation monitored; do not create unbounded polling or automatic rebuild loops.

## Failure Handling and Reporting

- `401` or `403`: stop; renew credentials or permissions through the approved channel.
- Missing/invalid crumb: stop; do not POST without the installation's expected CSRF protection.
- Cross-origin or malformed queue `Location`: stop; never send Jenkins credentials to it.
- Already queued/running: report the existing activity; do not duplicate it without explicit authorization.
- Non-`SUCCESS` result: report it and stop the dependency chain.
- Timeout: report the last known queue/build identity; timeout does not mean cancellation or failure.

Report the environment, resolved Job, requested Boolean parameters, queue ID, build number, `building`, and final `result`. Label live API observations clearly. Fetch console logs only when the user asks for failure diagnosis or logs, keep excerpts bounded, and redact credentials and unrelated sensitive output.

## Maintenance

- Keep `SKILL_zh.md`, `agents/openai.yaml`, and the integration tests in the package.
- Never add example or fallback tokens, even if they appear expired.
- Keep one canonical client for authentication, crumb handling, queue validation, and dependency ordering.
- Run the official Skill validator, `zsh -n`, the Python integration tests, and a secret-pattern scan after changes.
