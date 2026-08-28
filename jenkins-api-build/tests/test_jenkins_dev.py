#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = SKILL_ROOT / "scripts" / "jenkins-dev.sh"
FAKE_CURL = SKILL_ROOT / "tests" / "fake_curl.py"


class JenkinsDevScriptTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory(prefix="jenkins-api-build-")
        self.root = Path(self.temp_dir.name)
        self.bin_dir = self.root / "bin"
        self.bin_dir.mkdir()
        (self.bin_dir / "curl").symlink_to(FAKE_CURL)
        self.state_file = self.root / "state.json"
        self.env = os.environ.copy()
        self.env.update({
            "PATH": f"{self.bin_dir}:{self.env['PATH']}",
            "JENKINS_DEV_TOKEN": "test-token",
            "FAKE_EXPECTED_TOKEN": "test-token",
            "FAKE_JENKINS_STATE": str(self.state_file),
            "JENKINS_POLL_INTERVAL_SECONDS": "1",
        })

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def run_script(self, *args: str, check: bool = False) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["zsh", str(SCRIPT), *args],
            env=self.env,
            capture_output=True,
            text=True,
            check=check,
        )

    def test_build_api_waits_for_each_success_before_next_post(self) -> None:
        result = self.run_script("build-api", "dev", "search", "--gateway", check=True)
        output = json.loads(result.stdout)
        self.assertEqual(["3rd-modules", "target", "gateway"], [step["name"] for step in output["steps"]])
        state = json.loads(self.state_file.read_text())
        self.assertEqual(
            ["3rd-modules-dev", "search-jar-dev", "gateway-app-jar-dev"],
            state["posts"],
        )

    def test_unknown_module_is_rejected_before_post(self) -> None:
        result = self.run_script("build-modules", "dev", "unknown")
        self.assertNotEqual(0, result.returncode)
        self.assertIn("no Boolean parameter", result.stderr)
        if self.state_file.exists():
            self.assertEqual([], json.loads(self.state_file.read_text())["posts"])

    def test_cross_origin_queue_location_is_rejected(self) -> None:
        self.env["FAKE_CROSS_ORIGIN"] = "1"
        result = self.run_script("build", "dev", "search")
        self.assertNotEqual(0, result.returncode)
        self.assertIn("cross-origin queue Location", result.stderr)

    def test_path_like_build_number_is_rejected_before_network(self) -> None:
        result = self.run_script("status", "dev", "search", "../config.xml")
        self.assertNotEqual(0, result.returncode)
        self.assertIn("build number", result.stderr)
        self.assertFalse(self.state_file.exists())

    def test_zero_queue_id_is_rejected_before_network(self) -> None:
        result = self.run_script("queue-status", "dev", "0")
        self.assertNotEqual(0, result.returncode)
        self.assertIn("greater than zero", result.stderr)
        self.assertFalse(self.state_file.exists())

    def test_package_contains_localized_and_ui_metadata(self) -> None:
        self.assertTrue((SKILL_ROOT / "SKILL_zh.md").is_file())
        self.assertTrue((SKILL_ROOT / "agents" / "openai.yaml").is_file())


if __name__ == "__main__":
    unittest.main()
