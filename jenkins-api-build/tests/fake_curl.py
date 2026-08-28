#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path


args = sys.argv[1:]
config = sys.stdin.read()
token = os.environ.get("FAKE_EXPECTED_TOKEN", "test-token")

if token in " ".join(args):
    raise SystemExit("credential leaked through curl arguments")
if os.environ.get("JENKINS_DEV_TOKEN") or os.environ.get("JENKINS_UAT_RC_TOKEN"):
    raise SystemExit("credential leaked through curl environment")
if f":{token}" not in config:
    raise SystemExit("credential was not supplied through curl config stdin")

url = next((arg for arg in reversed(args) if arg.startswith("https://")), "")
if not url:
    raise SystemExit("missing URL")

state_path = Path(os.environ["FAKE_JENKINS_STATE"])
if state_path.exists():
    state = json.loads(state_path.read_text())
else:
    state = {"next_queue": 101, "queues": {}, "posts": []}


def save() -> None:
    state_path.write_text(json.dumps(state))


if "/crumbIssuer/api/json" in url:
    print(json.dumps({"crumbRequestField": "Jenkins-Crumb", "crumb": "crumb-123"}))
    raise SystemExit(0)

job_match = re.search(r"/job/([^/]+)", url)
job = job_match.group(1) if job_match else ""

if "--request" in args and "POST" in args:
    queue_id = state["next_queue"]
    state["next_queue"] += 1
    number = queue_id + 1000
    state["queues"][str(queue_id)] = {"job": job, "number": number}
    state["posts"].append(job)
    save()
    if os.environ.get("FAKE_CROSS_ORIGIN") == "1":
        location = f"https://example.invalid/queue/item/{queue_id}/"
    else:
        location = f"https://jenkins-dev.goldenmilestech.net/queue/item/{queue_id}/"
    print("HTTP/1.1 201 Created\r")
    print(f"Location: {location}\r")
    print("\r")
    raise SystemExit(0)

queue_match = re.search(r"/queue/item/(\d+)/api/json", url)
if queue_match:
    queue_id = queue_match.group(1)
    item = state["queues"][queue_id]
    print(json.dumps({
        "id": int(queue_id),
        "cancelled": False,
        "why": None,
        "blocked": False,
        "stuck": False,
        "task": {"name": item["job"], "url": f"https://jenkins-dev.goldenmilestech.net/job/{item['job']}/"},
        "executable": {
            "number": item["number"],
            "url": f"https://jenkins-dev.goldenmilestech.net/job/{item['job']}/{item['number']}/",
        },
    }))
    raise SystemExit(0)

build_match = re.search(r"/job/([^/]+)/(\d+)/api/json", url)
if build_match:
    build_job, number = build_match.groups()
    print(json.dumps({
        "number": int(number),
        "building": False,
        "result": "SUCCESS",
        "timestamp": 1,
        "duration": 10,
        "estimatedDuration": 10,
        "url": f"https://jenkins-dev.goldenmilestech.net/job/{build_job}/{number}/",
        "displayName": f"#{number}",
    }))
    raise SystemExit(0)

if job and "/api/json" in url:
    print(json.dumps({
        "name": job,
        "fullName": job,
        "buildable": True,
        "inQueue": False,
        "lastBuild": {"number": 10, "result": "SUCCESS", "building": False},
        "property": [{
            "parameterDefinitions": [
                {"name": "search", "type": "BooleanParameterDefinition"},
                {"name": "user", "type": "BooleanParameterDefinition"},
            ]
        }],
    }))
    raise SystemExit(0)

raise SystemExit(f"unhandled fake curl URL: {url}")
