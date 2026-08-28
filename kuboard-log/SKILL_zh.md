---
name: kuboard-log-api
description: 通过已认证的 Kuboard Kubernetes API 代理检查 Kubernetes Deployment、Pod、容器状态和有界容器日志。适用于故障排查确实需要 Kuboard 集群状态或 Pod 级日志，且用户已将目标集群纳入任务范围的场景。不适用于资源变更、通用 Kubernetes 管理，也不适用于更应由已批准集中式日志平台完成的长期历史日志搜索。
---

# Kuboard 日志 API

使用 Kuboard 的 `/k8s-api/{cluster}` 代理进行只读且有界的 Kubernetes 检查。明确区分实际观察到的集群状态与从抽样日志得出的结论。

本文档与 [SKILL.md](SKILL.md) 对应。修改任一版本时，应保持两者行为一致。

## 授权与凭据

本 Skill 只允许 GET 请求。它不授权创建、修改、删除、扩缩容、重启资源，也不授权进入容器执行命令、端口转发或其他 Kubernetes 变更。

必须使用执行环境中已经存在且经过批准的 Kuboard 认证来源。预期 Cookie 格式为：

```text
KuboardUsername=<username>; KuboardAccessKey=<access-key>
```

将完整值保存在 `KUBOARD_COOKIE`，或使用经过批准的浏览器认证会话。绝不在本 Skill、源代码、聊天、命令输出或提交的配置文件中写入用户名、访问密钥、Cookie 值或复制的浏览器凭据。不要提取浏览器 Cookie。处理凭据前关闭 Shell trace，并从诊断信息中清除认证头。

如果凭据曾经被提交或写入 Skill 指令，应将其视为已经泄露并在源系统中轮换；删除文本不会撤销凭据，也不会将其从历史记录中移除。

## 确认目标

从用户提供的 URL 或当前已批准配置中确定准确的主机、集群、命名空间、工作负载、Pod 和容器。不要仅根据应用名称推断目标。

该安装通常使用以下形式的工作负载 URL：

```text
https://<kuboard-host>/kubernetes/{cluster}/namespace/{namespace}/workload/view/Deployment/{deployment}
```

API 基础地址为：

```text
https://<kuboard-host>/k8s-api/{cluster}
```

环境映射属于可能变化的安装配置。用户提供 Kuboard URL 时，以 URL 中的集群和命名空间为准。否则应在查询前验证本地映射，生产或类生产目标尤其如此。

当前安装默认映射如下：

| 环境 | 主机 | 集群 | 命名空间 |
|---|---|---|---|
| Dev | `kuboard.tastetaiwan.com.tw` | `frch-aks-dev` | `default` |
| UAT | `kuboard.tastetaiwan.com.tw` | `frch-aks-uat` | `default` |
| RC | `kuboard.tastetaiwan.com.tw` | `frch-aks-uat` | `rc` |
| Prod | `kuboard.tastetaiwan.com.tw` | `frch-aks-prod` | `default` |

使用前，应根据用户提供的 URL 或已批准环境配置验证这些默认值。对于 UAT、RC 和 Prod 的历史或跨实例应用日志搜索，如果已有批准的 Azure Application Insights 流程，应优先使用该流程。只有在证据需要 Kubernetes 状态、特定 Pod 或容器、重启、滚动发布状态，或 Kubernetes 仍保留的日志时，才使用 Kuboard。

插入 URL 前验证 Kubernetes 资源路径段。命名空间、Deployment、Pod 和容器名称必须来自 Kubernetes 响应或可信用户输入，且不得包含 `/`、`?`、`#`、控制字符或 Shell 语法。查询值应使用 HTTP 客户端的参数编码功能。

## 传输约束

当前安装要求绕过代理时，应直接访问已配置的 Kuboard 主机。失败后不要静默切换主机、集群、代理、TLS 策略或凭据。

使用 `curl` 时，设置有界传输参数，并将最终 HTTP 状态与响应体分开保存：

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

通过 `--config -` 传入 Cookie，可以避免它出现在 `curl` 进程参数中。不要输出已经展开凭据的命令，并在不再需要时删除私有响应目录及其中的敏感内容。代理返回的 `200 Connection established` 只表示隧道建立，真正成功取决于最终 Kuboard/Kubernetes 响应状态。

不要使用无界 `watch=true` 或日志 `follow=true`。确实需要流式日志时，应设置较短客户端超时，并在收集到所需事件后停止。

## 检查流程

### 1. 读取 Deployment

```text
GET /apis/apps/v1/namespaces/{namespace}/deployments/{deployment}
```

读取：

- `spec.selector`，包括 `matchLabels` 和 `matchExpressions`；
- `spec.template.spec.containers[].name`，启动失败相关时也检查 init container；
- `metadata.generation`、`status.observedGeneration`、副本数量和 `status.conditions`。

不要假设选择器是 `app={deployment}`。列出 Pod 前，应按以下规则序列化完整 Kubernetes LabelSelector：

- `matchLabels`：`key=value`；
- `In`：`key in (value1,value2)`；
- `NotIn`：`key notin (value1,value2)`；
- `Exists`：`key`；
- `DoesNotExist`：`!key`。

使用逗号连接各项要求，再将完整 selector 作为单个查询值进行 URL 编码。如果无法确定转换是否正确，或出现不支持的 operator，应停止，而不是查询未过滤的整个命名空间。

### 2. 列出并分类相关 Pod

```text
GET /api/v1/namespaces/{namespace}/pods?labelSelector={encoded-selector}
```

使用查询参数编码器，例如 `curl --get --data-urlencode "labelSelector=${SELECTOR}"`。命名空间和选择器都应尽量精确。

选择日志前检查每个相关 Pod：

- phase、就绪条件、创建时间、删除时间和节点；
- owner references，避免在滚动发布期间混淆当前和旧 ReplicaSet；
- 普通容器和 init container 的状态、waiting/terminated 原因、退出码和重启次数。

不要只检查 `Running`/`Ready` Pod。`Pending`、`Failed`、正在终止、未就绪或反复重启的 Pod 往往包含关键证据。存在多个副本时，每项观察都必须保留 Pod 和容器身份。

### 3. 读取有界日志

```text
GET /api/v1/namespaces/{namespace}/pods/{pod}/log
    ?container={container}
    &sinceSeconds=1800
    &tailLines=200
    &timestamps=true
```

使用参数编码器构建查询。首先选择与报告事件相关的最小时间窗口，同时设置客户端超时和有界日志选项。可用控制包括：

- 使用 `sinceSeconds` 或已编码的 `sinceTime` 设置时间边界；
- 使用 `tailLines` 限制近期样本；
- 使用 `limitBytes` 进一步限制响应；
- 使用 `timestamps=true` 进行时间关联；
- 只有观察到重启且上一个容器实例与问题相关时，才使用 `previous=true`。

调查启动失败时，先检查 init container 和普通容器状态，再从 Pod 创建或失败时间窗口查询受影响容器。重启次数大于零并不能保证之前的日志仍然存在；Kubernetes 返回 `BadRequest` 或空结果时，应将其视为证据不可用。

首个样本不足时，每次只扩大一个维度：时间窗口、行数、相关 Pod 集合或上一个容器实例。将较大时间范围拆分为多个有界窗口。覆盖事件边界后停止；已删除 Pod 或需要更长保留时间时，改用集中式日志平台。

## 响应分类

解释响应体前，先分类最终响应：

- `200` 且资源端点返回预期 Kubernetes JSON，或日志端点返回日志文本：请求成功。
- `400`：选择器、查询选项、容器选择无效，或 previous 日志不可用；修正请求，不要原样重试。
- `401`：认证缺失或过期；停止，并通过已批准渠道更新凭据。
- `403` 且响应为 Kubernetes Status JSON：身份已经认证但权限不足，常见于 `pods/log`；不要绕过授权。
- `403` 或其他状态且响应为 HTML 网关页面：可能是路由或网络路径错误；确认主机和 no-proxy 规则后最多进行一次受控重试。
- `404`：核对集群、命名空间、资源名称、容器和代理路由。
- `429` 或 `5xx`：报告服务端压力或故障；避免快速重试，只有任务仍需要时才进行有界重试。

资源端点即使返回 `200`，如果响应是意外 HTML、登录页面或内容结构无效，也应判定失败。

## 结果报告

报告已验证目标、观察窗口、Deployment 状态、相关 Pod/容器状态和简洁日志证据。保留时间戳及 Pod/容器身份。清除 Cookie、访问密钥、Bearer token、连接字符串和无关敏感载荷。

明确说明抽样限制。不要声称有界 tail 是完整历史，也不要根据一个 Pod 中未出现事件就断言所有副本均不存在，更不要把 previous 日志缺失当作之前没有故障的证明。

## 维护要求

- 包中必须保留 `SKILL_zh.md` 和 `agents/openai.yaml`。
- 绝不添加示例凭据，即使它看起来已经过期或仅属于特定环境。
- 中英文版本的授权、传输和查询边界必须保持一致。
- 修改后运行官方 Skill 校验和凭据模式扫描。
