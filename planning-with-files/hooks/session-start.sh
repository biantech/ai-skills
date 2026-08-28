#!/bin/sh
# planning-with-files: SessionStart hook for Codex
# Runs session catchup, then reuses the same prompt context hook as UserPromptSubmit.

# issue #195: per-invocation opt-out for one-shot/CI sessions (e.g. codex exec)
# that share a cwd with a plan but never opted into it.
[ "${PLANNING_DISABLED:-}" = "1" ] && exit 0

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
PYTHON_BIN="${PYTHON_BIN:-$(command -v python3 || command -v python)}"

for candidate in \
    "${PWF_SCRIPT_DIR:-}/session-catchup.py" \
    "${SCRIPT_DIR}/../scripts/session-catchup.py" \
    "${SCRIPT_DIR}/../skills/planning-with-files/scripts/session-catchup.py" \
    "${HOME:-}/.codex/skills/planning-with-files/scripts/session-catchup.py"
do
    if [ -n "$PYTHON_BIN" ] && [ -f "$candidate" ]; then
        "$PYTHON_BIN" "$candidate" "$(pwd)"
        break
    fi
done

sh "$SCRIPT_DIR/user-prompt-submit.sh"
exit 0
