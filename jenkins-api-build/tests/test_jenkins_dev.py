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

    def test_common_build_uses_parameterized_default_version(self) -> None:
        result = self.run_script("build", "dev", "common", check=True)
        self.assertEqual("3rd-common-jar-dev", json.loads(result.stdout)["job"])
        state = json.loads(self.state_file.read_text())
        self.assertEqual(["3rd-common-jar-dev"], state["posts"])
        self.assertIn("TARGET_VERSION=1.0.0-SNAPSHOT", state["post_arguments"][0])

    def test_supported_aliases_resolve_to_expected_jobs(self) -> None:
        expected_jobs = {
            "authentication": "authentication-jar-dev",
            "authentication-content-starter": "3rd-authentication-content-starter-jar-dev",
            "push": "push-jar-dev",
            "common": "3rd-common-jar-dev",
            "content": "content-jar-dev",
            "file": "file-jar-dev",
            "finance": "finance-jar-dev",
            "gateway-app": "gateway-app-jar-dev",
            "justauth-spring-boot-starter": "3rd-justauth-spring-boot-starter-jar-dev",
            "location": "location-jar-dev",
            "marketing": "marketing-jar-dev",
            "merchant": "merchant-jar-dev",
            "note": "note-jar-dev",
            "order": "order-jar-dev",
            "ranking": "ranking-jar-dev",
            "recommend": "recommend-jar-dev",
            "reservation": "reservation-jar-dev",
            "review": "review-jar-dev",
            "search": "search-jar-dev",
            "task": "task-jar-dev",
            "user": "user-jar-dev",
        }
        for alias, expected_job in expected_jobs.items():
            with self.subTest(alias=alias):
                result = self.run_script("inspect", "dev", alias, check=True)
                self.assertEqual(expected_job, json.loads(result.stdout)["name"])

    def test_authentication_content_starter_uses_parameterized_default_version(self) -> None:
        result = self.run_script("build", "dev", "authentication-content-starter", check=True)
        self.assertEqual("3rd-authentication-content-starter-jar-dev", json.loads(result.stdout)["job"])
        state = json.loads(self.state_file.read_text())
        self.assertIn("TARGET_VERSION=1.0.0-SNAPSHOT", state["post_arguments"][0])

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
