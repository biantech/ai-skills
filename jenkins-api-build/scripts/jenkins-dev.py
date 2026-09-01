#!/usr/bin/env python3
"""Jenkins Remote Access API client used by the jenkins-api-build skill."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import quote

BASE_URL = os.environ.get("JENKINS_BASE_URL", "https://jenkins-dev.goldenmilestech.net")
USERS = {"dev": "bianjq", "uat": "tengxq", "rc": "tengxq"}
PROJECTS = {name: f"{name}-jar-{{env}}" for name in (
    "authentication", "push", "content", "file", "finance", "gateway-app", "location",
    "marketing", "merchant", "note", "order", "ranking", "recommend", "reservation",
    "review", "search", "task", "user")}
PROJECTS.update({
    "authentication-content-starter": "3rd-authentication-content-starter-jar-{env}",
    "common": "3rd-common-jar-{env}",
    "justauth-spring-boot-starter": "3rd-justauth-spring-boot-starter-jar-{env}",
    "3rd-modules": "3rd-modules-{env}", "gateway": "gateway-app-jar-{env}"})
UINT_RE = re.compile(r"^[0-9]+$")
TOKEN_RE = re.compile(r"^[A-Za-z0-9._~+/-]+$")
USER_RE = re.compile(r"^[A-Za-z0-9._@-]+$")


class ClientError(Exception):
    pass


def die(message: str) -> None:
    raise ClientError(message)


def require_environment(environment: str) -> None:
    if environment not in USERS:
        die(f"Unknown Jenkins environment: {environment}")


def user_for(environment: str) -> str:
    require_environment(environment)
    variable = "JENKINS_DEV_USER" if environment == "dev" else "JENKINS_UAT_RC_USER"
    user = os.environ.get(variable, USERS[environment])
    if not USER_RE.fullmatch(user):
        die("Jenkins username contains unsupported characters")
    return user


def token_for(environment: str) -> str:
    require_environment(environment)
    if environment == "dev":
        token, token_file = os.environ.get("JENKINS_DEV_TOKEN", ""), os.environ.get("JENKINS_DEV_TOKEN_FILE", "")
    else:
        token, token_file = os.environ.get("JENKINS_UAT_RC_TOKEN", ""), os.environ.get("JENKINS_UAT_RC_TOKEN_FILE", "")
    if not token and token_file:
        path = Path(token_file)
        if not path.is_file() or not os.access(path, os.R_OK):
            die("Configured Jenkins token file is not readable")
        token = path.read_text().rstrip("\n")
    if not token:
        die(f"No Jenkins token configured for {environment}")
    if "\n" in token or "\r" in token or not TOKEN_RE.fullmatch(token):
        die("Jenkins token contains unsupported characters")
    return token


def request(environment: str, url: str, *, post: bool = False, data: list[str] | None = None,
            crumb: tuple[str, str] | None = None, headers_only: bool = False) -> str:
    config = f'user = "{user_for(environment)}:{token_for(environment)}"\n'
    if crumb:
        config += f'header = "{crumb[0]}: {crumb[1]}"\n'
    command = ["curl", "--config", "-", "--silent", "--show-error", "--fail-with-body",
               "--globoff", "--connect-timeout", "10", "--max-time", "30"]
    if headers_only:
        command.extend(["--output", "/dev/null", "--dump-header", "-"])
    if post:
        command.extend(["--request", "POST"])
    for value in data or []:
        command.extend(["--data-urlencode", value])
    command.append(url)
    clean_env = os.environ.copy()
    for key in ("JENKINS_DEV_TOKEN", "JENKINS_UAT_RC_TOKEN", "JENKINS_DEV_TOKEN_FILE", "JENKINS_UAT_RC_TOKEN_FILE"):
        clean_env.pop(key, None)
    result = subprocess.run(command, input=config, text=True, capture_output=True, env=clean_env)
    if result.returncode:
        die(result.stderr.strip() or f"curl exited with status {result.returncode}")
    return result.stdout


def output(value: object) -> None:
    sys.stdout.write(json.dumps(value, separators=(",", ":"), ensure_ascii=False) + "\n")


def job_for(environment: str, project: str) -> str:
    require_environment(environment)
    if project not in PROJECTS:
        die(f"Unknown Jenkins project: {project}")
    return PROJECTS[project].format(env=environment)


def uint(name: str, value: str, positive: bool = False) -> int:
    if not UINT_RE.fullmatch(value):
        die(f"{name} must be a non-negative integer")
    number = int(value)
    if positive and number == 0:
        die(f"{name} must be greater than zero")
    return number


def state(environment: str, job: str) -> dict:
    url = f"{BASE_URL}/job/{quote(job, safe='')}/api/json?tree=name,fullName,buildable,inQueue,lastBuild[number,result,building],property[parameterDefinitions[name,type]]"
    return json.loads(request(environment, url))


def inspect_job(environment: str, job: str) -> None:
    value = state(environment, job)
    output({"name": value.get("name"), "fullName": value.get("fullName"), "buildable": value.get("buildable"),
            "inQueue": value.get("inQueue"), "lastBuild": value.get("lastBuild"),
            "parameters": [definition for prop in value.get("property", []) for definition in prop.get("parameterDefinitions", [])]})


def assert_queueable(environment: str, job: str) -> None:
    value = state(environment, job)
    if value.get("buildable") is not True:
        die(f"Job is not buildable: {job}")
    if os.environ.get("JENKINS_ALLOW_DUPLICATE", "0") != "1":
        if value.get("inQueue") is True:
            die(f"Job is already queued: {job}")
        if (value.get("lastBuild") or {}).get("building") is True:
            die(f"Job is already building: {job}")


def validate_modules(environment: str, job: str, modules: list[str]) -> None:
    if not modules:
        die("At least one API module is required")
    definitions = {item.get("name"): item.get("type", "") for prop in state(environment, job).get("property", []) for item in prop.get("parameterDefinitions", [])}
    for module in modules:
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]*", module):
            die(f"Invalid API module name: {module}")
        kind = definitions.get(module, "")
        if kind != "BooleanParameterDefinition" and not kind.endswith("BooleanParameterDefinition"):
            die(f"Job {job} has no Boolean parameter named {module}")


def fresh_crumb(environment: str) -> tuple[str, str]:
    value = json.loads(request(environment, f"{BASE_URL}/crumbIssuer/api/json"))
    field, crumb_value = value.get("crumbRequestField"), value.get("crumb")
    if not isinstance(field, str) or not re.fullmatch(r"[A-Za-z0-9-]+", field):
        die("Unsafe Jenkins crumb field")
    if not isinstance(crumb_value, str) or not TOKEN_RE.fullmatch(crumb_value):
        die("Unsafe Jenkins crumb value")
    return field, crumb_value


def queue_build(environment: str, job: str, url: str, data: list[str] | None = None) -> dict:
    assert_queueable(environment, job)
    headers = request(environment, url, post=True, data=data, crumb=fresh_crumb(environment), headers_only=True)
    location = next((line.split(":", 1)[1].strip() for line in headers.splitlines() if line.lower().startswith("location:")), "")
    if location.startswith("/"):
        location = BASE_URL + location
    prefix = f"{BASE_URL}/queue/item/"
    if not location.startswith(prefix) or not location.endswith("/"):
        die("Jenkins returned a cross-origin queue Location")
    queue_id = location[len(prefix):-1]
    uint("queue id", queue_id, positive=True)
    value = {"job": job, "queueId": int(queue_id), "queueUrl": location}
    return value


def build(environment: str, job: str) -> dict:
    if job in (f"3rd-common-jar-{environment}", f"3rd-authentication-content-starter-jar-{environment}"):
        version = os.environ.get("JENKINS_TARGET_VERSION", "1.0.0-SNAPSHOT")
        if job == f"3rd-common-jar-{environment}":
            version = os.environ.get("JENKINS_COMMON_TARGET_VERSION", version)
        return queue_build(environment, job, f"{BASE_URL}/job/{job}/buildWithParameters", [f"TARGET_VERSION={version}"])
    return queue_build(environment, job, f"{BASE_URL}/job/{job}/build")


def build_modules(environment: str, modules: list[str]) -> dict:
    job = job_for(environment, "3rd-modules")
    validate_modules(environment, job, modules)
    return queue_build(environment, job, f"{BASE_URL}/job/{job}/buildWithParameters", [f"{module}=true" for module in modules])


def queue_status(environment: str, queue_id: str) -> dict:
    number = uint("queue id", queue_id, positive=True)
    value = json.loads(request(environment, f"{BASE_URL}/queue/item/{number}/api/json?tree=id,cancelled,why,blocked,stuck,task[name,url],executable[number,url]"))
    return {"id": value.get("id"), "cancelled": value.get("cancelled"), "why": value.get("why"), "blocked": value.get("blocked"), "stuck": value.get("stuck"), "job": (value.get("task") or {}).get("name"), "executable": value.get("executable")}


def build_status(environment: str, job: str, number: str) -> dict:
    build_number = uint("build number", number, positive=True)
    return json.loads(request(environment, f"{BASE_URL}/job/{job}/{build_number}/api/json?tree=number,building,result,timestamp,duration,estimatedDuration,url,displayName"))


def bounded(name: str, value: str, minimum: int, maximum: int) -> int:
    number = uint(name, value)
    if not minimum <= number <= maximum:
        die(f"{name} must be between {minimum} and {maximum} seconds")
    return number


def wait_queue(environment: str, job: str, queue_id: str) -> dict:
    uint("queue id", queue_id, positive=True)
    timeout = bounded("JENKINS_QUEUE_TIMEOUT_SECONDS", os.environ.get("JENKINS_QUEUE_TIMEOUT_SECONDS", "300"), 1, 3600)
    interval = bounded("JENKINS_POLL_INTERVAL_SECONDS", os.environ.get("JENKINS_POLL_INTERVAL_SECONDS", "5"), 1, 60)
    deadline = time.monotonic() + timeout
    while True:
        value = queue_status(environment, queue_id)
        if value["cancelled"]:
            die(f"Jenkins queue item {queue_id} was cancelled")
        if value["job"] and value["job"] != job:
            die(f"Queue item {queue_id} belongs to unexpected Job {value['job']}")
        executable = value.get("executable")
        if executable:
            number = str(executable.get("number"))
            uint("build number", number, positive=True)
            if executable.get("url") != f"{BASE_URL}/job/{job}/{number}/":
                die("Queue item returned an unexpected build URL")
            return value
        if time.monotonic() >= deadline:
            die(f"Timed out waiting for queue item {queue_id}")
        time.sleep(interval)


def wait_build(environment: str, job: str, number: str) -> dict:
    uint("build number", number, positive=True)
    timeout = bounded("JENKINS_BUILD_TIMEOUT_SECONDS", os.environ.get("JENKINS_BUILD_TIMEOUT_SECONDS", "1800"), 1, 14400)
    interval = bounded("JENKINS_POLL_INTERVAL_SECONDS", os.environ.get("JENKINS_POLL_INTERVAL_SECONDS", "5"), 1, 60)
    deadline = time.monotonic() + timeout
    while True:
        value = build_status(environment, job, number)
        if value.get("building") is False and value.get("result"):
            return value
        if time.monotonic() >= deadline:
            die(f"Timed out waiting for build {job} #{number}")
        time.sleep(interval)


def wait_queued_build(environment: str, job: str, queued: dict) -> dict:
    queue = wait_queue(environment, job, str(queued["queueId"]))
    build_state = wait_build(environment, job, str((queue.get("executable") or {}).get("number")))
    return {"queued": queued, "queue": queue, "build": build_state}


def require_success(step: str, state_value: dict) -> None:
    result = (state_value.get("build") or {}).get("result")
    if result != "SUCCESS":
        output(state_value)
        die(f"{step} finished with result {result or 'unknown'}; downstream Jobs were not queued")


def build_api(environment: str, target: str, gateway: str | None) -> None:
    if target != "search":
        die("build-api currently supports only the search target")
    if gateway not in (None, "--gateway"):
        die(f"Unknown build-api option: {gateway}")
    api_job, target_job = job_for(environment, "3rd-modules"), job_for(environment, target)
    gateway_job = job_for(environment, "gateway") if gateway else None
    validate_modules(environment, api_job, [target])
    assert_queueable(environment, target_job)
    if gateway_job:
        assert_queueable(environment, gateway_job)
    api_state = wait_queued_build(environment, api_job, build_modules(environment, [target]))
    require_success("API module build", api_state)
    target_state = wait_queued_build(environment, target_job, build(environment, target_job))
    require_success("Target build", target_state)
    steps = [{"name": "3rd-modules", "state": api_state}, {"name": "target", "state": target_state}]
    if gateway_job:
        gateway_state = wait_queued_build(environment, gateway_job, build(environment, gateway_job))
        require_success("Gateway build", gateway_state)
        steps.append({"name": "gateway", "state": gateway_state})
    output({"steps": steps})


def usage() -> None:
    die("Usage: jenkins-dev.sh inspect|build <dev|uat|rc> <project>; build-modules <env> <api>...; build-api <env> search [--gateway]; queue-status <env> <queue-id>; wait-queue <env> <project> <queue-id>; status <env> <project> <build-number>; wait-build <env> <project> <build-number>")


def main(argv: list[str]) -> None:
    if not re.fullmatch(r"https://[A-Za-z0-9.-]+(?::[0-9]+)?", BASE_URL):
        die("JENKINS_BASE_URL must be an HTTPS origin without a path")
    if not argv:
        usage()
    command, args = argv[0], argv[1:]
    if command in ("inspect", "build") and len(args) == 2:
        environment, project = args
        job = job_for(environment, project)
        if command == "inspect":
            inspect_job(environment, job)
        else:
            output(build(environment, job))
    elif command == "build-modules" and len(args) >= 2:
        output(build_modules(args[0], args[1:]))
    elif command == "build-api" and len(args) in (2, 3):
        build_api(args[0], args[1], args[2] if len(args) == 3 else None)
    elif command == "queue-status" and len(args) == 2:
        output(queue_status(args[0], args[1]))
    elif command in ("wait-queue", "status", "wait-build") and len(args) == 3:
        job = job_for(args[0], args[1])
        if command == "wait-queue":
            output(wait_queue(args[0], job, args[2]))
        elif command == "status":
            output(build_status(args[0], job, args[2]))
        else:
            output(wait_build(args[0], job, args[2]))
    else:
        usage()


if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    except ClientError as error:
        sys.stderr.write(f"[jenkins-api-build] {error}\n")
        sys.exit(1)
