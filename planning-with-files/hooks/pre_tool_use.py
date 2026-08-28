#!/usr/bin/env python3
from __future__ import annotations

import codex_hook_adapter as adapter


def main() -> None:
    payload = adapter.load_payload()
    root = adapter.effective_plan_root(adapter.cwd_from_payload(payload))
    if root is None:
        return  # broken PWF_PLAN_ROOT pin fails closed (issue #212); notice is userprompt-only

    session_id = adapter.session_id_from_payload(payload)
    if not adapter.is_session_attached(root, session_id):
        return

    stdout, _ = adapter.run_skill_script(
        "inject-plan.sh",
        root,
        "--context=pretool",
        session_id=session_id,
    )
    if stdout:
        adapter.emit_json({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "additionalContext": stdout,
            }
        })


if __name__ == "__main__":
    raise SystemExit(adapter.main_guard(main))
