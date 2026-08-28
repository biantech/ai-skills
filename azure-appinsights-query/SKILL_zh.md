---
name: azure-appinsights-query
description: 通过主机 237 上已有认证的 Azure CLI，为 UAT、RC 或 Prod 执行有界、只读的 Azure Application Insights KQL 查询。适用于目标环境与订阅已知的终端日志排查；不用于 Dev 日志或 Azure 资源变更。
---

# Azure Application Insights 查询

通过 SSH 主机 `237` 上已有的 Azure CLI 会话查询 UAT、RC 和 Prod 日志。Dev 容器日志排查应转用 `$kuboard-log`。不得暴露访问令牌、密钥、Cookie 或一次性认证码。

## 必要范围

查询前取得环境、预期 Azure 订阅 ID 或名称、本地时间范围和排查问题。辅助脚本强制使用以下经审核的环境映射，并验证实时资源身份：

| 环境 | 资源组 | Application Insights 资源 |
|---|---|---|
| UAT | `frch-rg-uat` | `frch-appinsights-uat` |
| RC | `frch-rg-uat` | `frch-appinsights-rc` |
| Prod | `frch-rg-prod` | `frch-appinsights-prod` |

该表是当前安装的默认配置，不能证明资源实际存在。脚本会将每个 Azure CLI 命令绑定到指定订阅，并在资源身份不一致时停止；它不会修改活动订阅。

## 查询流程

1. 将用户的时间范围转换为预期的 UTC 半开区间 `[start, end)`。用户指定时区时使用该时区，否则使用工作区时区。KQL 中应使用对应模式的时间字段明确写出 `timestamp >= start and timestamp < end`；API 时间边界作为额外的外层限制。结果中同时报告原始时区和转换后的 UTC 起止时间。
2. 将最小可用的 KQL 写入私有 UTF-8 文件。不要让敏感标识符或 KQL 进入 shell 历史。脚本拒绝空文件、超过 64 KiB 的文件、Kusto 控制命令、宽泛 `search` 和 `union *`。
3. 在本 Skill 目录运行辅助脚本：

   ```bash
   python3 scripts/query_appinsights_via_237.py \
     --environment prod \
     --subscription '<预期订阅 ID 或名称>' \
     --start-time '<UTC ISO-8601 起始时间>' \
     --end-time '<UTC ISO-8601 结束时间>' \
     --max-rows 100 \
     --query-file '/private/path/query.kql'
   ```

辅助脚本会验证订阅和 Application Insights 资源，自动识别 workspace-based 或 classic 模式，应用 API 时间边界，并追加最终 `take` 限制。最终 `take` 只限制返回行数，不限制扫描数据量；应优先使用选择性过滤和聚合。JSON 结果会报告解析后的订阅、模式、时间范围、行数、是否达到上限、数据行或分类错误。

workspace-based 资源使用 `AppTraces` 及 `TimeGenerated`、`AppRoleName`、`OperationId`、`Message` 字段。classic 资源使用 `traces` 及 `timestamp`、`cloud_RoleName`、`operation_Id`、`message` 字段。模式在执行时才确定，因此可优先使用对模式差异不敏感的聚合；若因表结构不匹配而失败，根据返回的模式调整查询。

## 认证与失败处理

- 仅使用现有已认证的 Azure CLI 上下文。若返回 `authentication_required`，立即停止，并请用户或授权运维人员通过批准渠道恢复会话。
- 除非用户明确要求并授权变更共享主机状态，否则不得运行 `az login`、切换订阅、安装扩展或更新认证。不得转述或持久化 device code。
- SSH 失败时报告有界错误并停止。除非用户明确将其他主机纳入范围，否则不得改用其他主机。
- 资源不存在或身份不匹配时停止。不得搜索其他订阅，也不得替换为相似名称的资源。
- 查询无结果时，先报告准确环境、订阅、UTC 区间、数据表和过滤条件，再提出扩大范围的建议。
- 保持结果简洁。除非用户需要原始字段，否则截断或汇总长消息及大型 `customDimensions`。
- 使用 `[QUERY]` 标记查询证据，使用 `[LOGIC]` 标记基于代码的推理，使用 `[ASSUME]` 标记未验证假设。
