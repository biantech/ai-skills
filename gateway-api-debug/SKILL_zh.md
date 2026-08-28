---
name: gateway-api-debug
description: 通过检查网关和 Controller 代码确认路由、HTTP 方法、请求结构和认证决策，再向明确选择的 Dev、UAT、RC 或已授权生产环境发起有界实时调用，以调试和验证客户或管理端网关 API。适用于端到端网关行为和响应验证。不适用于推断写操作权限、探索无关生产数据，或绕过认证及环境控制。
---

# 网关 API 调试

明确区分代码能够证明的内容与实时网关响应验证的内容。实时调用使用随附客户端；该客户端不实现业务登录或 token 缓存。

本文档与 [SKILL.md](SKILL.md) 对应。修改任一版本时，应保持两者行为一致。

## 确认请求契约

进行任何实时调用前，检查相关网关过滤器、路由和目标 Controller，确定：

- 准确路径和 HTTP 方法；
- 客户端 `/api/...` 或管理端 `/admin-api/...` profile；
- 路径变量、查询参数、请求头和 body 结构；
- 操作属于只读还是写入；
- 准确认证分支，以及角色或租户上下文。

不要根据路径前缀推断 guest 或匿名访问资格。应通过当前代码或已批准运行时配置确认精确过滤决策和 guest path 匹配行为。

报告时区分：

- `[LOGIC]`：来自当前代码、规范或配置；
- `[QUERY]`：来自实时请求与响应；
- `[ASSUME]`：仍未验证。

该证据约定是自包含的，不依赖其他 Skill。

## 授权边界

调试请求可以支持向用户选择或工作区明确映射的环境发起范围精确的只读调用，但不授权写操作。

对于 `POST`、`PUT`、`PATCH` 或 `DELETE`，当前用户请求必须明确授权准确环境、端点、方法和预期变化。客户端还要求 `--allow-write`。不要根据代码变化、token、低环境访问权、历史请求或其他端点权限推断写授权。

生产调用要求用户在当前任务中明确指出生产环境并授权准确调用。客户端还要求 `--allow-production`；生产写操作同时需要 `--allow-production` 和 `--allow-write`。

不要将已授权操作扩大为探索性生产查询、登录尝试、无关端点、其他写法、重试或其他环境。遇到意外目标、重复记录歧义、校验不符、重定向、非成功响应或写后回读失败时停止。

## 环境配置

只设置当前工作区已批准的环境：

```bash
export GATEWAY_DEV_BASE_URL='https://approved-dev-gateway.example'
export GATEWAY_UAT_BASE_URL='https://approved-uat-gateway.example'
export GATEWAY_RC_BASE_URL='https://approved-rc-gateway.example'
export GATEWAY_PROD_BASE_URL='https://user-confirmed-prod-gateway.example'
```

不要在 Skill 中硬编码个人文件路径或可复用环境 URL。不要根据一个环境推断另一个环境的 URL。客户端要求 HTTPS，并拒绝包含凭据、查询字符串或 fragment 的基础 URL。

解析已安装客户端路径，不要假设个人主目录：

```bash
GATEWAY_SKILL_DIR="${CODEX_HOME:-$HOME/.codex}/skills/gateway-api-debug"
GATEWAY_CLIENT="$GATEWAY_SKILL_DIR/scripts/call_gateway_api.py"
```

## 认证模式

根据确认后的网关决策选择一种模式：

- `--auth no-token`：公开或允许匿名的请求；不发送 bearer token，也不发送 guest header。
- `--auth guest`：已确认允许 guest 的路径；发送 `X-Guest-Mode: 1`，不发送 bearer token。
- `--auth bearer`：要求认证或用户上下文的请求；从环境专属变量或明确私有 token 文件读取 token。

Token 来源：

```bash
export GATEWAY_DEV_TOKEN='...'
export GATEWAY_UAT_TOKEN='...'
export GATEWAY_RC_TOKEN='...'
export GATEWAY_PROD_TOKEN='...'

# 单次调用的替代方式
python3 "$GATEWAY_CLIENT" ... --auth bearer --token-file /approved/private/token
```

绝不把 token 作为命令参数传递，不在命令行 `Authorization` 请求头中嵌入 token，也不将 token 粘贴到聊天，或保存到本 Skill、payload、共享缓存和提交的配置中。不要提取浏览器凭据。如果需要登录，使用本 Skill 之外已有且经过批准的登录机制，再通过已批准秘密来源提供其 token。

在 Unix 类系统中，token 文件必须仅限所有者访问，例如权限 `600`；客户端会拒绝 group 或其他用户可访问的 token 文件。

## 只读调用

客户端 guest 请求：

```bash
python3 "$GATEWAY_CLIENT" \
  --env dev \
  --profile customer \
  --method GET \
  --path /api/example \
  --auth guest \
  --query 'q=example'
```

管理端 bearer 请求：

```bash
python3 "$GATEWAY_CLIENT" \
  --env uat \
  --profile admin \
  --method GET \
  --path /admin-api/example/123 \
  --auth bearer
```

重复使用 `--query key=value`，由客户端编码查询值。不要把查询字符串放进 `--path`。Profile 和路径前缀必须匹配。

## 写操作

获得准确授权后，在私有临时目录中构造最小 payload。对于 replace 风格 API，先读取当前状态并保留全部必需字段。

```bash
PAYLOAD_DIR="$(mktemp -d)"
chmod 700 "$PAYLOAD_DIR"
PAYLOAD_FILE="$PAYLOAD_DIR/request.json"

python3 "$GATEWAY_CLIENT" \
  --env rc \
  --profile admin \
  --method PATCH \
  --path /admin-api/example/123 \
  --auth bearer \
  --payload-file "$PAYLOAD_FILE" \
  --allow-write
```

明确授权的生产写操作还需增加 `--allow-production`。除非理解失败模式后用户明确授权重试，否则最多提交一次。通过范围最小的只读端点回读资源，并比较预期字段。不再需要时删除敏感临时 payload。

## 客户端保证和限制

随附客户端：

- 只接受 `GET`、`HEAD`、`OPTIONS`、`POST`、`PUT`、`PATCH` 和 `DELETE`；
- 要求明确的写入和生产开关；
- 验证 profile 与路径匹配，并阻止路径穿越；
- 独立编码查询参数；
- 限制超时、payload 大小和响应大小；
- 使用已验证 TLS、绕过环境 HTTP 代理，并且不跟随重定向；
- 输出 JSON envelope，包括 HTTP 状态、内容类型、选定 trace header、截断状态，以及解析后的 JSON 或文本 body；
- HTTP 非成功响应退出码为 `3`，传输失败退出码为 `2`。

它不会证明请求在业务语义上只读，不执行业务登录，不选择环境，不授权写操作，也不重试请求。这些决策仍属于代码检查和用户授权边界。

## 响应解释

- 解释 body 前，确认响应状态和内容类型符合端点契约。
- 除非当前证据能够证明其他网关行为，否则将 `401` 视为认证缺失或无效，将 `403` 视为权限不足。
- 将 `3xx` 视为已经停止的重定向，不得向另一个 URL 重发凭据。
- 将 `429` 和 `5xx` 视为服务压力或故障；不要快速重试，也不要自动重试写操作。
- 如果 API 契约规定 HTTP `200` 中的业务错误代表失败，则仍应判定业务失败。
- 截断响应只是有界样本，不是完整 payload。

报告环境、profile、方法、路径、认证模式、是否发送 bearer 或 guest header、HTTP/业务结果、相关响应字段和 trace ID。清除 token、Cookie、凭据、与问题无关的个人数据和敏感 payload 字段。

## 运行时数据与日志

网关响应可能只展示症状，不能证明下游原因。只有当用户请求和工作区策略将数据库、缓存、集中式日志或 Kubernetes 日志纳入范围时，才查询这些系统。对每个来源使用工作区强制指定的工具，保持查询只读且有界，不要将网关访问权视为其他系统的授权。

## 维护要求

- 包中必须保留 `SKILL_zh.md`、`agents/openai.yaml`、客户端和集成测试。
- 绝不恢复机器专属 helper 路径、token 命令参数或共享 token 缓存。
- 中英文版本的授权、认证和生产边界必须保持一致。
- 修改后运行官方 Skill 校验、Python 编译检查、集成测试和凭据模式扫描。
