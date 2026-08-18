#!/usr/bin/env python3
"""Run a read-only Application Insights or Log Analytics KQL query through Azure CLI on host 237."""

import argparse
import base64
import shlex
import subprocess
import sys


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--resource-group", required=True)
    parser.add_argument("--app", required=True)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--query")
    source.add_argument("--query-file")
    args = parser.parse_args()

    query = args.query
    if args.query_file:
        with open(args.query_file, encoding="utf-8") as query_file:
            query = query_file.read()

    remote_script = """import os
import subprocess
import sys

query = sys.stdin.read()
environment = os.environ.copy()
environment[\"PATH\"] = \"/opt/homebrew/bin:\" + environment.get(\"PATH\", \"\")
az = \"/opt/homebrew/bin/az\"


def run_az(arguments):
    return subprocess.run(
        [az, *arguments],
        env=environment,
        check=True,
        stdout=subprocess.PIPE,
        text=True,
    ).stdout.strip()


workspace_id = run_az([
    \"resource\",
    \"show\",
    \"--resource-group\",
    sys.argv[1],
    \"--name\",
    sys.argv[2],
    \"--resource-type\",
    \"Microsoft.Insights/components\",
    \"--query\",
    \"properties.WorkspaceResourceId\",
    \"-o\",
    \"tsv\",
])

if workspace_id:
    workspace_customer_id = run_az([
        \"monitor\",
        \"log-analytics\",
        \"workspace\",
        \"show\",
        \"--ids\",
        workspace_id,
        \"--query\",
        \"customerId\",
        \"-o\",
        \"tsv\",
    ])
    command = [
        az,
        \"monitor\",
        \"log-analytics\",
        \"query\",
        \"--workspace\",
        workspace_customer_id,
        \"--analytics-query\",
        query,
        \"--only-show-errors\",
    ]
else:
    command = [
        az,
        \"monitor\",
        \"app-insights\",
        \"query\",
        \"--resource-group\",
        sys.argv[1],
        \"--app\",
        sys.argv[2],
        \"--analytics-query\",
        query,
        \"--only-show-errors\",
    ]

raise SystemExit(subprocess.call(command, env=environment))
    """
    encoded_script = base64.b64encode(remote_script.encode()).decode()
    remote_code = f"import base64;exec(base64.b64decode('{encoded_script}'))"
    remote_command = " ".join(
        [
            "python3",
            "-c",
            shlex.quote(remote_code),
            shlex.quote(args.resource_group),
            shlex.quote(args.app),
        ]
    )
    command = [
        "ssh",
        "-o",
        "BatchMode=yes",
        "-o",
        "ConnectTimeout=8",
        "237",
        remote_command,
    ]
    result = subprocess.run(command, input=query, text=True)
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
