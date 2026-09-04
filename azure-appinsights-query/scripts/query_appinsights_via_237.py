#!/usr/bin/env python3
"""Run a bounded, read-only Azure Application Insights query through SSH."""

import argparse
import base64
import json
import os
import re
import shlex
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


ENVIRONMENTS = {
    "uat": {"resource_group": "frch-rg-uat", "app": "frch-appinsights-uat"},
    "rc": {"resource_group": "frch-rg-uat", "app": "frch-appinsights-rc"},
    "prod": {"resource_group": "frch-rg-prod", "app": "frch-appinsights-prod"},
}
MAX_QUERY_BYTES = 64 * 1024
MAX_ERROR_CHARS = 4000
HOST_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,252}$")
AZ_PATH_PATTERN = re.compile(r"^/[A-Za-z0-9._/+\-]+$")
CONTROL_COMMAND_PATTERN = re.compile(r"^\s*\.", re.MULTILINE)
UNBOUNDED_UNION_PATTERN = re.compile(r"\bunion\s+\*", re.IGNORECASE)
SEARCH_PATTERN = re.compile(r"(^|\|)\s*search\b", re.IGNORECASE)


REMOTE_SCRIPT = r'''import json
import os
import subprocess
import sys

config = json.loads(sys.argv[1])
query = sys.stdin.read()
environment = os.environ.copy()
az = config["az_path"]
environment["PATH"] = os.path.dirname(az) + ":" + environment.get("PATH", "")
environment["AZURE_EXTENSION_USE_DYNAMIC_INSTALL"] = "no"
environment["AZURE_CORE_DISABLE_CONFIRM_PROMPT"] = "true"
environment["AZURE_CORE_COLLECT_TELEMETRY"] = "no"


class AzureCommandError(Exception):
    def __init__(self, command, returncode, stderr):
        super().__init__(stderr)
        self.command = command
        self.returncode = returncode
        self.stderr = stderr


def run_az(arguments):
    command = [az, *arguments, "--only-show-errors"]
    try:
        result = subprocess.run(
            command,
            env=environment,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=config["command_timeout"],
        )
    except subprocess.TimeoutExpired as exc:
        raise AzureCommandError(command, 124, "Azure CLI command timed out") from exc
    if result.returncode:
        raise AzureCommandError(command, result.returncode, result.stderr.strip())
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise AzureCommandError(command, 1, "Azure CLI returned invalid JSON") from exc


def category_for(message):
    lowered = message.lower()
    if "az login" in lowered or "authentication" in lowered or "expired" in lowered:
        return "authentication_required"
    if "could not be found" in lowered or "not found" in lowered:
        return "resource_not_found"
    if "timed out" in lowered:
        return "timeout"
    return "azure_cli_error"


def truncate(value):
    if isinstance(value, str) and len(value) > config["max_cell_chars"]:
        return value[:config["max_cell_chars"]] + "...[truncated]"
    if isinstance(value, list):
        return [truncate(item) for item in value]
    if isinstance(value, dict):
        return {key: truncate(item) for key, item in value.items()}
    return value


envelope = {
    "ok": False,
    "environment": config["environment"],
    "subscription": {"requested": config["subscription"]},
    "resource_group": config["resource_group"],
    "app": config["app"],
    "timespan": {"start": config["start_time"], "end": config["end_time"]},
    "max_rows": config["max_rows"],
}

try:
    subscription = run_az([
        "account", "show", "--subscription", config["subscription"], "-o", "json"
    ])
    if subscription.get("state") != "Enabled":
        raise AzureCommandError([], 1, "Requested subscription is not enabled")
    subscription_id = subscription.get("id", "")
    if not subscription_id:
        raise AzureCommandError([], 1, "Requested subscription has no resource ID")
    envelope["subscription"] = {
        "requested": config["subscription"],
        "id": subscription_id,
        "name": subscription.get("name"),
    }

    resource = run_az([
        "resource", "show",
        "--subscription", subscription_id,
        "--resource-group", config["resource_group"],
        "--name", config["app"],
        "--resource-type", "Microsoft.Insights/components",
        "-o", "json",
    ])
    resource_id = resource.get("id", "")
    expected_prefix = "/subscriptions/{}/resourceGroups/{}/providers/Microsoft.Insights/components/{}".format(
        subscription_id, config["resource_group"], config["app"]
    )
    if resource_id.lower() != expected_prefix.lower():
        raise AzureCommandError([], 1, "Resolved Application Insights resource does not match the requested scope")

    workspace_id = (resource.get("properties") or {}).get("WorkspaceResourceId")
    if workspace_id:
        expected_workspace_prefix = "/subscriptions/{}/resourceGroups/".format(subscription_id)
        if (
            not workspace_id.lower().startswith(expected_workspace_prefix.lower())
            or "/providers/microsoft.operationalinsights/workspaces/" not in workspace_id.lower()
        ):
            raise AzureCommandError([], 1, "Workspace belongs to a different subscription")
        workspace = run_az([
            "monitor", "log-analytics", "workspace", "show",
            "--subscription", subscription_id,
            "--ids", workspace_id,
            "-o", "json",
        ])
        workspace_customer_id = workspace.get("customerId")
        if not workspace_customer_id:
            raise AzureCommandError([], 1, "Workspace customerId is missing")
        mode = "workspace"
        rows = run_az([
            "monitor", "log-analytics", "query",
            "--subscription", subscription_id,
            "--workspace", workspace_customer_id,
            "--analytics-query", query,
            "--timespan", config["start_time"] + "/" + config["end_time"],
            "-o", "json",
        ])
        envelope["workspace_resource_id"] = workspace_id
    else:
        mode = "classic"
        rows = run_az([
            "monitor", "app-insights", "query",
            "--subscription", subscription_id,
            "--resource-group", config["resource_group"],
            "--app", config["app"],
            "--analytics-query", query,
            "--start-time", config["start_time"],
            "--end-time", config["end_time"],
            "-o", "json",
        ])

    row_count = len(rows) if isinstance(rows, list) else None
    envelope.update({
        "ok": True,
        "mode": mode,
        "rows": truncate(rows),
        "row_count": row_count,
        "limit_reached": row_count is not None and row_count >= config["max_rows"],
    })
except FileNotFoundError:
    envelope["error"] = {"category": "azure_cli_missing", "message": "Azure CLI executable was not found"}
except AzureCommandError as exc:
    message = (exc.stderr or "Azure CLI command failed")[:config["max_error_chars"]]
    envelope["error"] = {"category": category_for(message), "message": message, "exit_status": exc.returncode}
except Exception as exc:
    envelope["error"] = {"category": "unexpected_error", "message": str(exc)[:config["max_error_chars"]]}

print(json.dumps(envelope, ensure_ascii=True))
raise SystemExit(0 if envelope["ok"] else 1)
'''


def utc_timestamp(value: str) -> str:
    """Normalize an ISO-8601 timestamp and require an explicit timezone."""
    candidate = value.strip()
    if candidate.endswith("Z"):
        candidate = candidate[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid ISO-8601 timestamp: {value}") from exc
    if parsed.tzinfo is None:
        raise argparse.ArgumentTypeError("timestamp must include Z or a UTC offset")
    return parsed.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def validated_host(value: str) -> str:
    if not HOST_PATTERN.fullmatch(value):
        raise argparse.ArgumentTypeError("SSH host must be a host name or configured SSH alias")
    return value


def validated_az_path(value: str) -> str:
    if not AZ_PATH_PATTERN.fullmatch(value):
        raise argparse.ArgumentTypeError("remote Azure CLI path must be an absolute executable path")
    return value


def bounded_int(minimum: int, maximum: int):
    def parse(value: str) -> int:
        try:
            number = int(value)
        except ValueError as exc:
            raise argparse.ArgumentTypeError("value must be an integer") from exc
        if not minimum <= number <= maximum:
            raise argparse.ArgumentTypeError(f"value must be between {minimum} and {maximum}")
        return number

    return parse


def load_query(path: str, max_rows: int) -> str:
    query_path = Path(path)
    try:
        size = query_path.stat().st_size
    except OSError as exc:
        raise ValueError(f"cannot read query file: {exc}") from exc
    if size > MAX_QUERY_BYTES:
        raise ValueError(f"query file exceeds {MAX_QUERY_BYTES} bytes")
    try:
        query = query_path.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeError) as exc:
        raise ValueError(f"cannot read UTF-8 query file: {exc}") from exc
    if not query:
        raise ValueError("query must not be empty")
    if CONTROL_COMMAND_PATTERN.search(query):
        raise ValueError("Kusto control commands are not allowed")
    if UNBOUNDED_UNION_PATTERN.search(query) or SEARCH_PATTERN.search(query):
        raise ValueError("broad search and 'union *' queries are not allowed")
    query = query.rstrip().rstrip(";").rstrip()
    return f"{query}\n| take {max_rows}"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run a bounded, read-only Application Insights query through server237."
    )
    parser.add_argument("--environment", choices=sorted(ENVIRONMENTS), required=True)
    parser.add_argument("--subscription", required=True, help="Expected Azure subscription ID or name")
    parser.add_argument("--query-file", required=True, help="UTF-8 KQL file; inline KQL is not accepted")
    parser.add_argument("--start-time", required=True, type=utc_timestamp)
    parser.add_argument("--end-time", required=True, type=utc_timestamp)
    parser.add_argument("--max-rows", type=bounded_int(1, 200), default=100)
    parser.add_argument("--timeout", type=bounded_int(10, 300), default=60)
    parser.add_argument(
        "--ssh-host",
        type=validated_host,
        default=os.environ.get("AZURE_QUERY_SSH_HOST", "server237"),
    )
    parser.add_argument(
        "--remote-az",
        type=validated_az_path,
        default=os.environ.get("AZURE_QUERY_AZ_PATH", "/opt/homebrew/bin/az"),
    )
    return parser


def make_config(args: argparse.Namespace) -> dict:
    scope = ENVIRONMENTS[args.environment]
    return {
        "environment": args.environment,
        "subscription": args.subscription,
        "resource_group": scope["resource_group"],
        "app": scope["app"],
        "start_time": args.start_time,
        "end_time": args.end_time,
        "max_rows": args.max_rows,
        "command_timeout": args.timeout,
        "max_cell_chars": 4000,
        "max_error_chars": MAX_ERROR_CHARS,
        "az_path": args.remote_az,
    }


def run(args: argparse.Namespace) -> int:
    start = datetime.fromisoformat(args.start_time.replace("Z", "+00:00"))
    end = datetime.fromisoformat(args.end_time.replace("Z", "+00:00"))
    if start >= end:
        raise ValueError("start time must be earlier than end time")
    query = load_query(args.query_file, args.max_rows)
    config = make_config(args)
    encoded_script = base64.b64encode(REMOTE_SCRIPT.encode()).decode()
    remote_code = f"import base64;exec(base64.b64decode('{encoded_script}'))"
    remote_command = " ".join(
        ["python3", "-c", shlex.quote(remote_code), shlex.quote(json.dumps(config))]
    )
    command = [
        "ssh",
        "-o", "BatchMode=yes",
        "-o", "ConnectTimeout=8",
        "-o", "ServerAliveInterval=15",
        "-o", "ServerAliveCountMax=2",
        "--",
        args.ssh_host,
        remote_command,
    ]
    try:
        result = subprocess.run(
            command,
            input=query,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=args.timeout + 15,
        )
    except subprocess.TimeoutExpired:
        print(json.dumps({"ok": False, "error": {"category": "ssh_timeout", "message": "SSH query timed out"}}))
        return 124

    if result.stdout.strip():
        try:
            envelope = json.loads(result.stdout)
            if not isinstance(envelope, dict) or "ok" not in envelope:
                raise ValueError
        except (json.JSONDecodeError, ValueError):
            message = (result.stderr.strip() or "Remote helper returned invalid JSON")[:MAX_ERROR_CHARS]
            print(json.dumps({"ok": False, "error": {"category": "remote_protocol_error", "message": message}}))
            return result.returncode or 1
        print(json.dumps(envelope, ensure_ascii=True))
    else:
        message = (result.stderr.strip() or "SSH command failed")[:MAX_ERROR_CHARS]
        print(json.dumps({"ok": False, "error": {"category": "ssh_error", "message": message}}))
    return result.returncode


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return run(args)
    except ValueError as exc:
        parser.error(str(exc))
    return 2


if __name__ == "__main__":
    sys.exit(main())
