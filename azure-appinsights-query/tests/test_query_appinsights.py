import argparse
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).parents[1] / "scripts" / "query_appinsights_via_237.py"
SPEC = importlib.util.spec_from_file_location("query_appinsights", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class QueryValidationTests(unittest.TestCase):
    def write_query(self, content):
        handle = tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False)
        self.addCleanup(Path(handle.name).unlink, missing_ok=True)
        handle.write(content)
        handle.close()
        return handle.name

    def test_empty_query_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "must not be empty"):
            MODULE.load_query(self.write_query("  \n"), 10)

    def test_control_command_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "control commands"):
            MODULE.load_query(self.write_query(".show tables"), 10)

    def test_broad_queries_are_rejected(self):
        for query in ("search *", "AppTraces | union *"):
            with self.subTest(query=query), self.assertRaises(ValueError):
                MODULE.load_query(self.write_query(query), 10)

    def test_query_gets_final_row_limit(self):
        query = MODULE.load_query(self.write_query("AppTraces | summarize count()"), 25)
        self.assertTrue(query.endswith("| take 25"))

    def test_timestamp_requires_timezone_and_normalizes_to_utc(self):
        with self.assertRaises(argparse.ArgumentTypeError):
            MODULE.utc_timestamp("2026-08-28T12:00:00")
        self.assertEqual(
            MODULE.utc_timestamp("2026-08-28T20:00:00+08:00"),
            "2026-08-28T12:00:00Z",
        )

    def test_ssh_option_injection_is_rejected(self):
        for host in ("-oProxyCommand=bad", "user@237", "237;whoami"):
            with self.subTest(host=host), self.assertRaises(argparse.ArgumentTypeError):
                MODULE.validated_host(host)


class CommandConstructionTests(unittest.TestCase):
    def setUp(self):
        handle = tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False)
        self.query_file = handle.name
        handle.write("AppTraces | summarize count()")
        handle.close()
        self.addCleanup(Path(self.query_file).unlink, missing_ok=True)

    def args(self):
        return argparse.Namespace(
            environment="prod",
            subscription="subscription-id",
            query_file=self.query_file,
            start_time="2026-08-27T16:00:00Z",
            end_time="2026-08-28T16:00:00Z",
            max_rows=50,
            timeout=60,
            ssh_host="server237",
            remote_az="/opt/homebrew/bin/az",
        )

    @mock.patch.object(MODULE.subprocess, "run")
    def test_ssh_is_bounded_and_config_contains_verified_scope(self, run_mock):
        run_mock.return_value = subprocess.CompletedProcess([], 0, '{"ok": true}\n', "")
        with mock.patch("builtins.print"):
            result = MODULE.run(self.args())
        self.assertEqual(result, 0)
        command = run_mock.call_args.args[0]
        self.assertEqual(command[0], "ssh")
        self.assertIn("BatchMode=yes", command)
        self.assertIn("ServerAliveCountMax=2", command)
        self.assertEqual(command[-3], "--")
        self.assertEqual(command[-2], "server237")
        self.assertIn("subscription-id", command[-1])
        self.assertIn("frch-rg-prod", command[-1])
        self.assertIn("frch-appinsights-prod", command[-1])
        self.assertEqual(run_mock.call_args.kwargs["timeout"], 75)

    @mock.patch.object(MODULE.subprocess, "run")
    def test_ssh_failure_returns_structured_error(self, run_mock):
        run_mock.return_value = subprocess.CompletedProcess([], 255, "", "connection refused")
        with mock.patch("builtins.print") as print_mock:
            result = MODULE.run(self.args())
        self.assertEqual(result, 255)
        envelope = json.loads(print_mock.call_args.args[0])
        self.assertEqual(envelope["error"]["category"], "ssh_error")

    def test_end_must_be_after_start(self):
        args = self.args()
        args.end_time = args.start_time
        with self.assertRaisesRegex(ValueError, "earlier"):
            MODULE.run(args)


class RemoteProtocolTests(unittest.TestCase):
    def run_remote(self, mode="workspace", authentication_error=False):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        fake_az = Path(directory.name) / "az"
        fake_az.write_text(
            """#!/usr/bin/env python3
import json
import os
import sys

args = sys.argv[1:]
if "--subscription" not in args:
    print("missing subscription", file=sys.stderr)
    raise SystemExit(2)
if os.environ.get("FAKE_AUTH_ERROR") == "1":
    print("Authentication expired; run az login", file=sys.stderr)
    raise SystemExit(1)
if args[:2] == ["account", "show"]:
    value = {"id": "sub-id", "name": "FAR-REACH", "state": "Enabled"}
elif args[:2] == ["resource", "show"]:
    resource_id = "/subscriptions/sub-id/resourceGroups/frch-rg-prod/providers/Microsoft.Insights/components/frch-appinsights-prod"
    properties = {}
    if os.environ.get("FAKE_MODE") == "workspace":
        properties["WorkspaceResourceId"] = "/subscriptions/sub-id/resourceGroups/logs/providers/Microsoft.OperationalInsights/workspaces/main"
    value = {"id": resource_id, "properties": properties}
elif args[:4] == ["monitor", "log-analytics", "workspace", "show"]:
    value = {"customerId": "workspace-customer-id"}
elif args[:3] in (["monitor", "log-analytics", "query"], ["monitor", "app-insights", "query"]):
    value = [{"message": "sample"}]
else:
    print("unexpected command", file=sys.stderr)
    raise SystemExit(3)
print(json.dumps(value))
""",
            encoding="utf-8",
        )
        fake_az.chmod(0o700)
        config = {
            "environment": "prod",
            "subscription": "sub-id",
            "resource_group": "frch-rg-prod",
            "app": "frch-appinsights-prod",
            "start_time": "2026-08-27T16:00:00Z",
            "end_time": "2026-08-28T16:00:00Z",
            "max_rows": 100,
            "command_timeout": 10,
            "max_cell_chars": 4000,
            "max_error_chars": 4000,
            "az_path": str(fake_az),
        }
        environment = os.environ.copy()
        environment["FAKE_MODE"] = mode
        environment["FAKE_AUTH_ERROR"] = "1" if authentication_error else "0"
        return subprocess.run(
            [sys.executable, "-c", MODULE.REMOTE_SCRIPT, json.dumps(config)],
            input="AppTraces | take 1",
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=environment,
            timeout=10,
        )

    def test_all_remote_azure_operations_bind_subscription(self):
        source = MODULE.REMOTE_SCRIPT
        self.assertIn('"account", "show", "--subscription"', source)
        self.assertGreaterEqual(source.count('"--subscription", subscription_id'), 4)
        self.assertNotIn('run_az(["login"', source)
        self.assertIn('AZURE_EXTENSION_USE_DYNAMIC_INSTALL"] = "no"', source)

    def test_workspace_and_classic_routes_exist(self):
        source = MODULE.REMOTE_SCRIPT
        self.assertIn('mode = "workspace"', source)
        self.assertIn('mode = "classic"', source)
        self.assertIn('"--timespan"', source)
        self.assertIn('"--start-time"', source)
        self.assertIn('"--end-time"', source)

    def test_workspace_route_returns_structured_result(self):
        result = self.run_remote("workspace")
        self.assertEqual(result.returncode, 0, result.stderr)
        envelope = json.loads(result.stdout)
        self.assertTrue(envelope["ok"])
        self.assertEqual(envelope["mode"], "workspace")
        self.assertEqual(envelope["subscription"]["id"], "sub-id")
        self.assertEqual(envelope["row_count"], 1)

    def test_classic_route_returns_structured_result(self):
        result = self.run_remote("classic")
        self.assertEqual(result.returncode, 0, result.stderr)
        envelope = json.loads(result.stdout)
        self.assertTrue(envelope["ok"])
        self.assertEqual(envelope["mode"], "classic")

    def test_authentication_failure_does_not_start_login(self):
        result = self.run_remote(authentication_error=True)
        self.assertEqual(result.returncode, 1)
        envelope = json.loads(result.stdout)
        self.assertFalse(envelope["ok"])
        self.assertEqual(envelope["error"]["category"], "authentication_required")


class PackagingTests(unittest.TestCase):
    def test_skill_metadata_and_chinese_document_exist(self):
        skill_root = SCRIPT.parents[1]
        self.assertTrue((skill_root / "SKILL_zh.md").is_file())
        metadata = (skill_root / "agents" / "openai.yaml").read_text(encoding="utf-8")
        self.assertIn("$azure-appinsights-query", metadata)
        self.assertIn("allow_implicit_invocation: true", metadata)


if __name__ == "__main__":
    unittest.main()
