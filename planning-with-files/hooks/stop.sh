#!/bin/sh
# planning-with-files: Stop compatibility entry point.

[ "${PLANNING_DISABLED:-}" = "1" ] && exit 0

HOOK_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" 2>/dev/null && pwd)" || exit 0
for candidate in \
    "${PWF_SCRIPT_DIR:-}/check-complete.sh" \
    "${HOOK_DIR}/../scripts/check-complete.sh" \
    "${HOOK_DIR}/../skills/planning-with-files/scripts/check-complete.sh" \
    "${HOME:-}/.codex/skills/planning-with-files/scripts/check-complete.sh"
do
    [ -f "$candidate" ] || continue
    exec sh "$candidate" --gate
done
exit 0
