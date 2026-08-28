#!/usr/bin/env python3
from __future__ import annotations

import json

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
        "check-complete.sh",
        root,
        "--gate",
        input_text=json.dumps(payload),
        session_id=session_id,
    )
    result = adapter.parse_json(stdout)
    if result.get("decision") == "block":
        adapter.emit_json(result)
        return

    if not stdout:
        return
    adapter.emit_json({"systemMessage": stdout})


if __name__ == "__main__":
    raise SystemExit(adapter.main_guard(main))
