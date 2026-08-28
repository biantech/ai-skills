#!/bin/sh
# planning-with-files: PreToolUse compatibility entry point.

[ "${PLANNING_DISABLED:-}" = "1" ] && exit 0

HOOK_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" 2>/dev/null && pwd)" || exit 0
for candidate in \
    "${PWF_SCRIPT_DIR:-}/inject-plan.sh" \
    "${HOOK_DIR}/../scripts/inject-plan.sh" \
    "${HOOK_DIR}/../skills/planning-with-files/scripts/inject-plan.sh" \
    "${HOME:-}/.codex/skills/planning-with-files/scripts/inject-plan.sh"
do
    [ -f "$candidate" ] || continue
    exec sh "$candidate" --context=pretool
done
exit 0
