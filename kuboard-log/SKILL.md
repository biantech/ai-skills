---
name: kuboard-log
description: Inspect Kubernetes Deployments, Pods, container status, and bounded container logs through an authenticated Kuboard Kubernetes API proxy. Use when troubleshooting requires Kuboard-specific cluster state or Pod-level logs and the user has placed the target cluster in scope. Do not use for resource mutation, general Kubernetes administration, or centralized historical log searches better served by an approved logging platform.
---

# Kuboard Log API

Use Kuboard's `/k8s-api/{cluster}` proxy for read-only, bounded Kubernetes inspection. Preserve the distinction between observed cluster state and conclusions drawn from sampled logs.

The Chinese version is maintained in [SKILL_zh.md](SKILL_zh.md). Keep both files behaviorally aligned.

## Authorization and Secrets

This Skill is GET-only. It does not authorize creating, patching, deleting, scaling, restarting, executing in containers, port forwarding, or changing Kubernetes resources.

Require an approved Kuboard authentication source already available in the execution environment. The expected Cookie format is:

```text
KuboardUsername=<username>; KuboardAccessKey=<access-key>
```

Store the complete value in `KUBOARD_COOKIE` or use an approved authenticated browser/session mechanism. Never place a username, access key, Cookie value, or copied browser credential in this Skill, source files, chat, command output, or a committed configuration file. Do not extract browser cookies. Disable shell tracing before handling secrets, and redact authentication headers from diagnostics.

If a credential has ever been committed or included in Skill instructions, treat it as compromised and rotate it at the source; deleting the text does not revoke it or remove it from history.

## Resolve the Target

Determine the exact host, cluster, namespace, workload, Pod, and container from the user's URL or current approved configuration. Do not infer a target from the application name alone.

The installation commonly uses workload URLs shaped as:

```text
https://<kuboard-host>/kubernetes/{cluster}/namespace/{namespace}/workload/view/Deployment/{deployment}
```

The API base is:

```text
https://<kuboard-host>/k8s-api/{cluster}
```

Treat environment mappings as installation configuration that may change. If the user supplies a Kuboard URL, its cluster and namespace take precedence. Otherwise verify any local mapping before querying, especially for production-like targets.

Current installation defaults are:

| Environment | Host | Cluster | Namespace |
|---|---|---|---|
| Dev | `kuboard.tastetaiwan.com.tw` | `frch-aks-dev` | `default` |
| UAT | `kuboard.tastetaiwan.com.tw` | `frch-aks-uat` | `default` |
| RC | `kuboard.tastetaiwan.com.tw` | `frch-aks-uat` | `rc` |
| Prod | `kuboard.tastetaiwan.com.tw` | `frch-aks-prod` | `default` |

Verify these defaults against the supplied URL or approved environment configuration before use. For UAT, RC, and Prod historical or cross-instance application-log searches, prefer the approved Azure Application Insights workflow when available. Use Kuboard when the evidence requires Kubernetes state, a specific Pod or container, restarts, rollout state, or logs still retained by Kubernetes.

Validate Kubernetes resource path segments before interpolation. Namespace, Deployment, Pod, and container names must come from Kubernetes responses or trusted user input and must not contain `/`, `?`, `#`, control characters, or shell syntax. Encode query values with the HTTP client's query-parameter facility.

## Transport Contract

Use the configured Kuboard host directly when this installation requires proxy bypass. Do not silently switch hosts, clusters, proxies, TLS policy, or credentials after a failure.

For `curl`, apply bounded transport settings and retain the final HTTP status separately from the response body:

```bash
: "${KUBOARD_HOST:?Set the approved Kuboard host}"
: "${KUBOARD_COOKIE:?Set the approved Kuboard Cookie}"
: "${CLUSTER:?Set the verified cluster ID}"

KUBOARD_BASE="https://${KUBOARD_HOST}/k8s-api/${CLUSTER}"
RESPONSE_DIR="$(mktemp -d)"
chmod 700 "${RESPONSE_DIR}"
RESPONSE_FILE="${RESPONSE_DIR}/body"

HTTP_STATUS="$(printf 'header = "Cookie: %s"\n' "${KUBOARD_COOKIE}" | curl --config - \
  --silent --show-error \
  --noproxy "${KUBOARD_HOST}" \
  --connect-timeout 10 --max-time 30 \
  --output "${RESPONSE_FILE}" \
  --write-out '%{http_code}' \
  "${KUBOARD_BASE}/...")"
```

Passing the Cookie through `--config -` keeps it out of the `curl` argument list. Do not print commands with expanded secrets. Remove the private response directory and its sensitive output when no longer needed. A proxy line such as `200 Connection established` is only tunnel establishment; success is the final Kuboard/Kubernetes response status.

Do not use unbounded `watch=true` or log `follow=true`. If streaming is explicitly needed, add a short client timeout and stop after collecting the required event.

## Inspection Workflow

### 1. Read the Deployment

```text
GET /apis/apps/v1/namespaces/{namespace}/deployments/{deployment}
```

Read:

- `spec.selector`, including both `matchLabels` and `matchExpressions`;
- `spec.template.spec.containers[].name` and init containers when startup failure is relevant;
- `metadata.generation`, `status.observedGeneration`, replica counts, and `status.conditions`.

Do not assume the selector is `app={deployment}`. Serialize the complete Kubernetes LabelSelector before listing Pods:

- `matchLabels`: `key=value`;
- `In`: `key in (value1,value2)`;
- `NotIn`: `key notin (value1,value2)`;
- `Exists`: `key`;
- `DoesNotExist`: `!key`.

Join requirements with commas, then URL-encode the complete selector as one query value. If conversion is uncertain or an operator is unsupported, stop rather than querying an unfiltered namespace.

### 2. List and Classify Relevant Pods

```text
GET /api/v1/namespaces/{namespace}/pods?labelSelector={encoded-selector}
```

Use a query encoder, for example `curl --get --data-urlencode "labelSelector=${SELECTOR}"`. Keep the namespace and selector narrow.

Inspect every relevant returned Pod before choosing logs:

- phase, readiness conditions, creation timestamp, deletion timestamp, and node;
- owner references, so current and old ReplicaSets during a rollout are not confused;
- regular and init container states, waiting/terminated reasons, exit codes, and restart counts.

Do not restrict investigation to `Running`/`Ready` Pods. `Pending`, `Failed`, terminating, unready, and restarting Pods may contain the evidence. When replicas exist, retain the Pod and container identity with every observation.

### 3. Read Bounded Logs

```text
GET /api/v1/namespaces/{namespace}/pods/{pod}/log
    ?container={container}
    &sinceSeconds=1800
    &tailLines=200
    &timestamps=true
```

Build query parameters with an encoder. Start with the smallest window relevant to the reported event and set both a client timeout and bounded log options. Useful controls include:

- `sinceSeconds` or encoded `sinceTime` for the time boundary;
- `tailLines` for a bounded recent sample;
- `limitBytes` as an additional response bound;
- `timestamps=true` for correlation;
- `previous=true` only after a restart is observed and the prior container instance is relevant.

For startup failures, inspect init-container and regular-container status first, then query the affected container from the Pod creation or failure window. A positive restart count does not guarantee previous logs are still available; handle a Kubernetes `BadRequest` or empty result as unavailable evidence.

If the first sample is inconclusive, widen one dimension at a time: time window, line count, relevant Pod set, or previous instance. Split large time ranges into bounded windows. Stop when the event boundary is covered or centralized logging is required for deleted Pods and longer retention.

## Response Classification

Classify the final response before interpreting the body:

- `200` with expected Kubernetes JSON for resources or log text for the log endpoint: request succeeded.
- `400`: invalid selector, query option, container selection, or unavailable previous logs; correct the request, do not retry unchanged.
- `401`: authentication is missing or expired; stop and request credential renewal through the approved channel.
- `403` with Kubernetes Status JSON: authenticated identity lacks permission, commonly `pods/log`; do not bypass authorization.
- `403` or another status with an HTML gateway page: likely wrong route or network path; verify the configured host and no-proxy rule before one controlled retry.
- `404`: verify cluster, namespace, resource name, container, and proxy route.
- `429` or `5xx`: report server pressure or failure; avoid rapid retries and use only a bounded retry when the user task still requires it.

Reject a nominal `200` when a resource endpoint returns an unexpected HTML/login page or an invalid content shape.

## Reporting

Report the verified target, observation window, Deployment status, relevant Pod/container states, and concise log evidence. Preserve timestamps and Pod/container identity. Redact cookies, access keys, bearer tokens, connection strings, and unrelated sensitive payloads.

State sampling limits explicitly. Do not claim that a bounded tail is complete history, that absence in one Pod proves absence across replicas, or that missing previous logs prove no prior failure.

## Maintenance

- Keep `SKILL_zh.md` and `agents/openai.yaml` in the package.
- Never add example credentials, even if they appear expired or environment-specific.
- Keep English and Chinese authorization, transport, and query-boundary rules aligned.
- Run the official Skill validator and a secret-pattern scan after changes.
