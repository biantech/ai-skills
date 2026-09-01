---
name: jenkins-api-build
description: 通过 Jenkins Remote Access API 检查、触发并跟踪已配置的 Jenkins Dev、UAT 和 RC Job，包括经过验证的参数化模块构建和依赖感知构建链。适用于用户明确要求 Jenkins 构建，或查询受支持 Job 的队列及构建状态。不适用于推断部署意图、触发未指定环境或参数、修改 Job 配置或执行 Jenkins 管理操作。
---

# Jenkins API 构建

使用 `scripts/jenkins-api-build.sh` 作为已配置 Jenkins 控制器的稳定入口。默认执行 `scripts/jenkins-dev.py`；设置 `JENKINS_CLIENT_IMPL=shell` 时执行原始 Shell 实现 `scripts/jenkins-dev.sh`。每个构建 POST 都是外部副作用；检查和状态查询属于只读操作。

本文档与 [SKILL.md](SKILL.md) 对应。修改任一版本时，应保持两者行为一致。

## 授权边界

触发构建前，要求用户明确指定或确认：

- 环境：`dev`、`uat` 或 `rc`；
- 项目或 Job；
- 需要时明确 API 模块参数；
- 是否需要 gateway 构建。

不要根据代码变化、调试请求或 Jenkins 检查权限推断构建意图。不要静默增加模块、`--gateway`、其他环境或重试。构建失败或状态不稳定不代表已经授权重新构建。

客户端默认拒绝重复排队或构建。只有用户明确要求在已有队列或运行实例之外增加一次构建时，才能设置 `JENKINS_ALLOW_DUPLICATE=1`。

## 已配置目标

默认控制器：

```text
https://jenkins-dev.goldenmilestech.net
```

| 环境 | Jenkins 视图 | 默认用户 | Job 后缀 |
|---|---|---|---|
| Dev | `view/dev` | `bianjq` | `-dev` |
| UAT | `view/uat` | `tengxq` | `-uat` |
| RC | `view/rc` | `tengxq` | `-rc` |

支援的專案別名：

| 別名 | 對應 Job |
|---|---|
| `authentication` | `authentication-jar-<environment>` |
| `authentication-content-starter` | `3rd-authentication-content-starter-jar-<environment>` |
| `push` | `push-jar-<environment>` |
| `common` | `3rd-common-jar-<environment>` |
| `content` | `content-jar-<environment>` |
| `file` | `file-jar-<environment>` |
| `finance` | `finance-jar-<environment>` |
| `gateway-app` 或 `gateway` | `gateway-app-jar-<environment>` |
| `justauth-spring-boot-starter` | `3rd-justauth-spring-boot-starter-jar-<environment>` |
| `location` | `location-jar-<environment>` |
| `marketing` | `marketing-jar-<environment>` |
| `merchant` | `merchant-jar-<environment>` |
| `note` | `note-jar-<environment>` |
| `order` | `order-jar-<environment>` |
| `ranking` | `ranking-jar-<environment>` |
| `recommend` | `recommend-jar-<environment>` |
| `reservation` | `reservation-jar-<environment>` |
| `review` | `review-jar-<environment>` |
| `search` | `search-jar-<environment>` |
| `task` | `task-jar-<environment>` |
| `user` | `user-jar-<environment>` |
| `3rd-modules` | `3rd-modules-<environment>` |

`search`、`user` 等 API 名稱是 `3rd-modules-<environment>` 的 Boolean 參數。客戶端會讀取即時參數定義，並拒絕不是已定義 Boolean 參數的名稱。`common` 與 `authentication-content-starter` 使用 `TARGET_VERSION`，預設為 `1.0.0-SNAPSHOT`；可透過 `JENKINS_TARGET_VERSION` 同時覆蓋，或以相容變數 `JENKINS_COMMON_TARGET_VERSION` 僅覆蓋 `common`。

只有经过批准的环境配置才能覆盖控制器和用户名。`JENKINS_BASE_URL` 必须是一个不含路径的 HTTPS origin。

## 凭据

绝不在本 Skill、脚本、源代码、聊天、命令输出或提交的配置文件中保存 Jenkins API token。如果 token 曾经出现在这些位置，应将其视为已经泄露并在 Jenkins 中轮换；删除当前文本不会撤销 token，也不会清除历史记录。

配置以下任一经过批准的来源：

```bash
# 由秘密管理器或私有 Shell 配置提供的环境变量
export JENKINS_DEV_TOKEN='...'
export JENKINS_UAT_RC_TOKEN='...'

# 或明确指定的私有单行 token 文件
export JENKINS_DEV_TOKEN_FILE='/approved/private/dev-token'
export JENKINS_UAT_RC_TOKEN_FILE='/approved/private/uat-rc-token'
```

可选用户名覆盖变量为 `JENKINS_DEV_USER` 和 `JENKINS_UAT_RC_USER`。

不要要求用户在聊天中粘贴 token。处理凭据时关闭 Shell trace。客户端通过 `curl --config -` 传递 Basic Auth，并从子 `curl` 环境中删除 token 变量，因此 token 不会出现在进程参数中。

## 客户端设置

解析已安装 Skill 路径，不要硬编码个人主目录：

```bash
JENKINS_SKILL_DIR="${CODEX_HOME:-$HOME/.codex}/skills/jenkins-api-build"
JENKINS_CLIENT="$JENKINS_SKILL_DIR/scripts/jenkins-api-build.sh"
```

兼容入口依赖 `zsh` 和 `python3`；Python 客户端依赖 `curl` 和 `jq`。

临时使用原始 Shell 实现：

```bash
JENKINS_CLIENT_IMPL=shell "$JENKINS_CLIENT" inspect dev note
```

默认使用 Python 实现，也可以显式设置 `JENKINS_CLIENT_IMPL=python`。

## 只读检查

构建前，或用户询问配置时，检查解析后的 Job：

```bash
"$JENKINS_CLIENT" inspect uat search
```

结果包括是否可构建、队列状态、上次构建和参数定义。确认解析后的 Job 与环境和用户请求一致。

查询已知队列项或构建：

```bash
"$JENKINS_CLIENT" queue-status uat 1234
"$JENKINS_CLIENT" status uat search 237
```

Queue ID 和构建号必须是十进制整数。复用凭据前，客户端会根据已配置 Jenkins origin 和预期 Job 验证队列及 executable URL。

## 触发构建

触发单个目标 Job：

```bash
"$JENKINS_CLIENT" build rc search
```

触发一个或多个经过验证的模块参数：

```bash
"$JENKINS_CLIENT" build-modules dev search user
```

每次 POST 都会在入队前重新获取 CSRF crumb。POST 成功只表示获得同源 Queue ID 和 URL，并不证明构建已经开始或成功。

## 依赖感知构建链

对于受支持的 API 变化，使用：

```bash
"$JENKINS_CLIENT" build-api uat search
"$JENKINS_CLIENT" build-api rc search --gateway
```

`build-api` 会在第一次副作用前完成预检，然后执行以下状态机：

1. 触发所选 `3rd-modules` 参数。
2. 等待 Queue item 解析为预期构建。
3. 等待该构建以 `SUCCESS` 结束。
4. 触发并等待目标 Job。
5. 只有目标构建 `SUCCESS` 后，才按需触发并等待 gateway。

任何阶段被取消、超时或返回其他结果时，都不会触发下游 Job。不要用立即入队顺序替代依赖验证；不同 Jenkins Job 不会仅因为 POST 按顺序发送，就自动形成成功的依赖链。

## 有界等待

跟踪之前返回的 ID 时，使用明确的等待命令：

```bash
"$JENKINS_CLIENT" wait-queue uat search 1234
"$JENKINS_CLIENT" wait-build uat search 237
```

默认值：

- `JENKINS_QUEUE_TIMEOUT_SECONDS=300`
- `JENKINS_BUILD_TIMEOUT_SECONDS=1800`
- `JENKINS_POLL_INTERVAL_SECONDS=5`

脚本会验证这些值处于有界范围内。只有用户仍希望监控当前操作时才能增加超时；不要建立无界轮询或自动重新构建循环。

## 失败处理与报告

- `401` 或 `403`：停止，通过批准渠道更新凭据或权限。
- crumb 缺失或无效：停止，不要绕过当前安装要求的 CSRF 保护执行 POST。
- 跨域或格式错误的 Queue `Location`：停止，绝不向该地址发送 Jenkins 凭据。
- 已经排队或运行：报告现有活动，未经明确授权不要重复构建。
- 非 `SUCCESS` 结果：报告结果并停止依赖链。
- 超时：报告最后已知 Queue/构建身份；超时不等于取消或失败。

报告环境、解析后的 Job、请求的 Boolean 参数、Queue ID、构建号、`building` 和最终 `result`。清晰标注实时 API 观察结果。只有用户要求失败诊断或日志时才读取 console log，限制摘录范围，并清除凭据和无关敏感输出。

## 维护要求

- 包中必须保留 `SKILL_zh.md`、`agents/openai.yaml` 和集成测试。
- 绝不添加示例或回退 token，即使它看起来已经过期。
- 认证、crumb、队列验证和依赖顺序只保留一个权威客户端实现。
- `jenkins-api-build.sh` 负责选择实现，`jenkins-dev.py` 是 Python 实现，`jenkins-dev.sh` 保留原始 Shell 实现；不要在入口中重复实现 Jenkins 逻辑。
- 修改后运行官方 Skill 校验、`zsh -n scripts/jenkins-api-build.sh scripts/jenkins-dev.sh`、`PYTHONPYCACHEPREFIX=/tmp/jenkins-api-build-pycache python3 -m py_compile scripts/jenkins-dev.py`、Python 集成测试和凭据模式扫描。
