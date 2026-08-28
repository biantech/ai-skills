#!/usr/bin/env bash
set -euo pipefail

if ! command -v npx >/dev/null 2>&1; then
  echo "Error: npx is required but not found on PATH." >&2
  exit 1
fi

has_session_flag="false"
for arg in "$@"; do
  case "$arg" in
    --session|--session=*|-s|-s=*)
      has_session_flag="true"
      break
      ;;
  esac
done

cli_package="${PLAYWRIGHT_CLI_PACKAGE:-@playwright/cli}"
cmd=(npx --yes --package "${cli_package}" playwright-cli)
if [[ "${has_session_flag}" != "true" && -n "${PLAYWRIGHT_CLI_SESSION:-}" ]]; then
  cmd+=(--session "${PLAYWRIGHT_CLI_SESSION}")
fi
cmd+=("$@")

exec "${cmd[@]}"
