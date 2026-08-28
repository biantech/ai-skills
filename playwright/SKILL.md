---
name: "playwright"
description: "Use when the task requires automating a real browser from the terminal for navigation, form filling, snapshots, screenshots, extraction, or UI-flow debugging via `playwright-cli` or the bundled wrapper. Do not use for generic Playwright test authoring unless requested."
---


# Playwright CLI Skill

Drive a real browser from the terminal using `playwright-cli`. Prefer the bundled wrapper script so the CLI works even when it is not globally installed.
Treat this skill as CLI-first automation. Do not pivot to `@playwright/test` unless the user explicitly asks for test files.

## Prerequisite check (required)

Before proposing commands, check whether `npx` is available (the wrapper depends on it):

```bash
command -v npx >/dev/null 2>&1
node --version
npm --version
```

If it is not available, pause and ask the user to install Node.js/npm (which provides `npx`). Provide these steps verbatim:

```bash
# Verify Node/npm are installed
node --version
npm --version

# If missing, install Node.js/npm, then:
npm install -g @playwright/cli@latest
playwright-cli --help
```

Once `npx`, Node, and npm are present, run the wrapper. The wrapper downloads `@playwright/cli` through npm, so verify registry/proxy access before a network-dependent run. A global install is optional.

## Skill path (set once)

```bash
CODEX_ROOT="${CODEX_HOME:-$HOME/.codex}"
export PWCLI="$CODEX_ROOT/skills/playwright/scripts/playwright_cli.sh"
```

User-scoped skills install under `$CODEX_HOME/skills` (default: `~/.codex/skills`).
When using this checkout directly, set `PWCLI` to the absolute path of `playwright/scripts/playwright_cli.sh` instead of assuming it is installed under `$CODEX_HOME`.

For reproducible runs, pin the package version:

```bash
export PLAYWRIGHT_CLI_PACKAGE="@playwright/cli@<verified-version>"
```

## Quick start

Use the wrapper script:

```bash
"$PWCLI" open https://playwright.dev --headed
"$PWCLI" snapshot
"$PWCLI" click e15
"$PWCLI" type "Playwright"
"$PWCLI" press Enter
"$PWCLI" screenshot
```

If the user prefers a global install, this is also valid:

```bash
npm install -g @playwright/cli@latest
playwright-cli --help
```

## Core workflow

1. Open the page.
2. Snapshot to get stable element refs.
3. Interact using refs from the latest snapshot.
4. Re-snapshot after navigation or significant DOM changes.
5. Capture artifacts (screenshot, pdf, traces) when useful.

Minimal loop:

```bash
"$PWCLI" open https://example.com
"$PWCLI" snapshot
"$PWCLI" click e3
"$PWCLI" snapshot
```

## When to snapshot again

Snapshot again after:

- navigation
- clicking elements that change the UI substantially
- opening/closing modals or menus
- tab switches

Refs can go stale. When a command fails due to a missing ref, snapshot again.

## Recommended patterns

### Form fill and submit

```bash
"$PWCLI" open https://example.com/form
"$PWCLI" snapshot
"$PWCLI" fill e1 "user@example.com"
"$PWCLI" fill e2 "$TEST_PASSWORD"
"$PWCLI" click e3
"$PWCLI" snapshot
```

### Debug a UI flow with traces

```bash
"$PWCLI" open https://example.com --headed
"$PWCLI" tracing-start
# ...interactions...
"$PWCLI" tracing-stop
```

### Multi-tab work

```bash
"$PWCLI" tab-new https://example.com
"$PWCLI" tab-list
"$PWCLI" tab-select 0
"$PWCLI" snapshot
```

## Wrapper script

The wrapper script uses `npx --package @playwright/cli playwright-cli` so the CLI can run without a global install. Set `PLAYWRIGHT_CLI_PACKAGE` to pin a version. It forwards all arguments and only injects `PLAYWRIGHT_CLI_SESSION` when no `--session`, `-s`, or equivalent value was supplied:

```bash
"$PWCLI" --help
```

Prefer the wrapper unless the repository already standardizes on a global install.

## References

Open only what you need:

- CLI command reference: `references/cli.md`
- Practical workflows and troubleshooting: `references/workflows.md`
- Advanced commands, storage, mocking, and test debugging: read the matching reference under the installed Playwright CLI package when needed.

## Guardrails

- Always snapshot before referencing element ids like `e12`.
- Re-snapshot when refs seem stale.
- Prefer explicit commands over `eval` and `run-code` unless needed.
- When you do not have a fresh snapshot, use placeholder refs like `eX` and say why; do not bypass refs with `run-code`.
- Use `--headed` when a visual check will help.
- When capturing artifacts in this repo, use `output/playwright/` and avoid introducing new top-level artifact folders.
- Keep snapshots, traces, videos, PDFs, storage state, cookies, headers, and network logs out of version control when they may contain credentials or personal data. Use environment variables and test accounts for secrets.
- Treat `eval` and `run-code` as arbitrary page-code execution. Use them only when an explicit CLI command cannot express the operation, and review the target page and data scope first.
- Default to CLI commands and workflows, not Playwright test specs.
