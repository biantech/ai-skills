#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]


class HookIntegrationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory(prefix="pwf-hook-test-")
        self.root = Path(self.temp_dir.name)
        self.project = self.root / "project"
        self.project.mkdir()
        self.home = self.root / "home"
        self.home.mkdir()
        self.cache = self.root / "cache"
        self.cache.mkdir()

        codex_dir = self.root / "install" / ".codex"
        self.hook_dir = codex_dir / "hooks"
        self.skill_dir = codex_dir / "skills" / "planning-with-files"
        shutil.copytree(SKILL_ROOT / "hooks", self.hook_dir)
        shutil.copytree(SKILL_ROOT / "scripts", self.skill_dir / "scripts")
        shutil.copytree(SKILL_ROOT / "templates", self.skill_dir / "templates")

        self.env = os.environ.copy()
        self.env.update({
            "HOME": str(self.home),
            "XDG_CACHE_HOME": str(self.cache),
        })
        subprocess.run(
            ["sh", str(self.skill_dir / "scripts" / "init-session.sh"), "--gated", "Hook Test"],
            cwd=self.project,
            env=self.env,
            check=True,
            capture_output=True,
            text=True,
        )
        plan_id = (self.project / ".planning" / ".active_plan").read_text().strip()
        self.plan_dir = self.project / ".planning" / plan_id

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def run_hook(self, script: str, payload: dict[str, object]) -> dict[str, object]:
        result = subprocess.run(
            [sys.executable, str(self.hook_dir / script)],
            cwd=self.project,
            env=self.env,
            input=json.dumps(payload),
            check=True,
            capture_output=True,
            text=True,
        )
        return json.loads(result.stdout) if result.stdout.strip() else {}

    def test_tampered_gated_plan_is_not_injected(self) -> None:
        plan = self.plan_dir / "task_plan.md"
        plan.write_text(plan.read_text() + "\nSECRET_TAMPERED_INSTRUCTION\n")

        result = subprocess.run(
            [sys.executable, str(self.hook_dir / "run_sh.py"), "user-prompt-submit.sh"],
            cwd=self.project,
            env=self.env,
            input=json.dumps({"cwd": str(self.project), "session_id": "session-a"}),
            check=True,
            capture_output=True,
            text=True,
        )
        prompt = json.loads(result.stdout)
        context = prompt["hookSpecificOutput"]["additionalContext"]
        self.assertIn("PLAN TAMPERED", context)
        self.assertNotIn("SECRET_TAMPERED_INSTRUCTION", context)

        pretool = self.run_hook(
            "pre_tool_use.py",
            {"cwd": str(self.project), "session_id": "session-a"},
        )
        self.assertNotIn("SECRET_TAMPERED_INSTRUCTION", json.dumps(pretool))

    def test_attached_session_id_reaches_shell_injection(self) -> None:
        sessions = self.project / ".planning" / "sessions"
        sessions.mkdir()
        (sessions / "session-a.attached").touch()

        result = subprocess.run(
            [sys.executable, str(self.hook_dir / "run_sh.py"), "user-prompt-submit.sh"],
            cwd=self.project,
            env=self.env,
            input=json.dumps({"cwd": str(self.project), "session_id": "session-a"}),
            check=True,
            capture_output=True,
            text=True,
        )
        context = json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"]
        self.assertIn("ACTIVE PLAN", context)
        self.assertNotIn("not attached", context)

    def test_unattached_session_gets_turn_scoped_notice(self) -> None:
        sessions = self.project / ".planning" / "sessions"
        sessions.mkdir()

        result = subprocess.run(
            [sys.executable, str(self.hook_dir / "run_sh.py"), "user-prompt-submit.sh"],
            cwd=self.project,
            env=self.env,
            input=json.dumps({"cwd": str(self.project), "session_id": "session-a"}),
            check=True,
            capture_output=True,
            text=True,
        )
        context = json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"]
        self.assertIn("not attached", context)
        self.assertNotIn("ACTIVE PLAN", context)

    def test_gated_stop_emits_block_decision(self) -> None:
        result = self.run_hook(
            "stop.py",
            {
                "cwd": str(self.project),
                "session_id": "session-a",
                "stop_hook_active": False,
            },
        )
        self.assertEqual("block", result.get("decision"))
        self.assertIn("Gated plan incomplete", str(result.get("reason")))

    def test_recursive_stop_is_not_blocked(self) -> None:
        result = self.run_hook(
            "stop.py",
            {
                "cwd": str(self.project),
                "session_id": "session-a",
                "stop_hook_active": True,
            },
        )
        self.assertNotEqual("block", result.get("decision"))
        self.assertIn("systemMessage", result)

    def test_required_localized_and_ui_files_are_packaged(self) -> None:
        self.assertTrue((SKILL_ROOT / "SKILL_zh.md").is_file())
        self.assertTrue((SKILL_ROOT / "agents" / "openai.yaml").is_file())


if __name__ == "__main__":
    unittest.main()
