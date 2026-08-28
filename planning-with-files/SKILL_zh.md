---
name: planning-with-files
description: 使用持久化 Markdown 计划文件协调需要跨越多个依赖阶段、上下文压缩或会话交接的实现与研究任务。适用于用户明确要求书面计划，或任务确实需要持久保存发现和进度的场景。不适用于简单问答、快速查询或无需持续协调的小范围修改。
allowed-tools: "Read Write Edit Bash Glob Grep"
metadata:
  version: "3.11.3"
---

# 使用文件进行规划

将复杂任务的持久状态保存在 Markdown 文件中，不只依赖上下文窗口。

本文档与 [SKILL.md](SKILL.md) 对应。修改任一版本时，应同步更新另一版本。

## 选择存储模式

使用满足任务需要的最简单模式：

- 根目录模式：在项目根目录保存 `task_plan.md`、`findings.md` 和 `progress.md`，适合单个会话中的单项任务。
- 隔离模式：使用 `.planning/<plan-id>/` 和 `.planning/.active_plan`，适合并行任务或不希望在根目录放置计划文件的场景。
- 自主模式：在根目录或隔离模式基础上增加计划认证、nonce 边界和 ledger 摘要。
- 门控模式：在自主模式基础上，当阶段明确为 `in_progress` 时启用有界 Stop 门控。

使用随附脚本初始化：

```bash
PWF_SKILL_DIR="${CODEX_HOME:-$HOME/.codex}/skills/planning-with-files"

# 根目录模式
sh "$PWF_SKILL_DIR/scripts/init-session.sh"

# 隔离模式
sh "$PWF_SKILL_DIR/scripts/init-session.sh" "Backend Refactor"

# 自主或门控模式
sh "$PWF_SKILL_DIR/scripts/init-session.sh" --autonomous "Long Run"
sh "$PWF_SKILL_DIR/scripts/init-session.sh" --gated "Gated Run"
```

Windows 使用对应的 PowerShell 脚本。

## 核心文件

| 文件 | 持久内容 | 更新时机 |
|------|----------|----------|
| `task_plan.md` | 目标、阶段、当前状态和决策 | 阶段或方案发生变化时 |
| `findings.md` | 需求、研究结果和发现 | 某项发现会影响后续工作时 |
| `progress.md` | 已执行操作、验证结果和相关失败 | 完成有意义的工作单元时 |

只记录有助于恢复任务或多人协调的信息。不要机械记录每次工具调用、瞬时错误或上下文中已经清晰可见的细节。

## 工作流程

1. 创建文件前先检查现有计划状态。已有计划时默认继续执行，除非用户要求新建计划。
2. 写明简洁目标，并只拆分当前任务需要的阶段。条件允许时保持一个活动阶段。
3. 在重大决策前或上下文丢失后重读计划，不要在每次操作前机械读取。
4. 在有意义的检查点更新发现和进度，使计划与实现和测试结果一致。
5. 结束前验证交付结果并准确更新阶段状态。存在未来待办阶段，不代表当前工作已经完成。

上下文重置或会话交接后，如果历史中可能存在未同步工作，运行：

```bash
python3 "$PWF_SKILL_DIR/scripts/session-catchup.py" "$(pwd)"
```

然后结合当前计划文件和仓库 diff 核对恢复结果。

## 多计划与会话

计划解析顺序如下：

1. `PWF_PLAN_ROOT` 指定的项目根目录
2. `.planning/` 下由 `PLAN_ID` 指定的计划
3. `.planning/.active_plan`
4. 最新的有效 `.planning/<plan-id>/`
5. 根目录 `task_plan.md`

存在多个计划时设置 `PLAN_ID`。进程工作目录是多个项目的共同父目录时，将 `PWF_PLAN_ROOT` 设置为项目绝对路径。

存在 `.planning/sessions/` 时，Hook 只向已附加的会话注入上下文。适配器会将 Hook payload 中的 session ID 作为 `PWF_SESSION_ID` 传递，对应标记为 `.planning/sessions/<session-id>.attached`。

一次性命令或 CI 不应读取附近计划时，设置 `PLANNING_DISABLED=1`。

## 计划认证与门控

自主模式和门控模式必须认证计划。初始化脚本会自动认证初始计划。主动修改已认证计划后，应先审核内容，再重新认证：

```bash
sh "$PWF_SKILL_DIR/scripts/attest-plan.sh"
```

UserPromptSubmit、PreToolUse 和 PreCompact Hook 必须统一调用 `scripts/inject-plan.sh`。不要新增直接读取并注入 `task_plan.md` 的实现，否则会绕过认证、模式、nonce 和歧义检查。

门控 Stop 路径必须调用 `scripts/check-complete.sh --gate`，并通过标准输入转发原始 Stop payload。门控受递归、停滞和阻塞次数上限保护，不会扩大任务授权，也不会覆盖用户指令。

## Hook 安装

`hooks.json` 描述 Codex Hook 注册方式，其命令期望适配器位于：

- `<project>/.codex/hooks/`
- `$HOME/.codex/hooks/`

适配器期望 Skill 位于对应的 `skills/planning-with-files/`，也可以通过 `PWF_SCRIPT_DIR` 指向本 Skill 的 `scripts/`。只安装 `SKILL.md` 不会自动安装全局 Hook。

Hook 行为异常时，在项目根目录运行：

```bash
sh "$PWF_SKILL_DIR/scripts/plan-doctor.sh"
```

## 辅助资源

- [templates/task_plan.md](templates/task_plan.md)、[templates/findings.md](templates/findings.md) 和 [templates/progress.md](templates/progress.md) 是起始结构，不是强制格式。
- 需要查看完整填写示例时，读取 [references/examples.md](references/examples.md)。
- 只有在背景原则会影响当前任务时，才读取 [references/reference.md](references/reference.md)。

## 维护约束

- 包中必须保留 `SKILL_zh.md` 和 `agents/openai.yaml`。
- 中英文说明必须保持行为一致。
- 计划解析、注入和完成门控分别只能保留一套权威实现。
- 修改 Hook 或脚本后，运行官方 Skill 校验、语法检查和 `tests/test_hook_integration.py`。
- https://github.com/OthmanAdi/planning-with-files/ 