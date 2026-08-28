---
name: playwright
description: 当任务需要在终端通过 `playwright-cli` 或随附 wrapper 操作真实浏览器时使用，包括导航、表单填写、快照、截图、数据提取和 UI 流程调试。除非用户明确要求，不用于通用 Playwright 测试编写。
---

# Playwright CLI Skill

使用 `playwright-cli` 在终端驱动真实浏览器。优先使用随附的 wrapper，即使系统没有全局安装 CLI 也可以运行。本 Skill 以 CLI 自动化为主；除非用户明确要求测试文件，否则不要切换到 `@playwright/test`。

## 前置检查

提出命令前必须确认 `npx`、Node.js 和 npm 可用：

```bash
command -v npx >/dev/null 2>&1
node --version
npm --version
```

wrapper 需要通过 npm 获取 `@playwright/cli`，因此还要确认 registry 或代理可访问。没有 Node.js/npm 时，先安装后再执行：

```bash
npm install -g @playwright/cli@latest
playwright-cli --help
```

## Skill 路径

```bash
CODEX_ROOT="${CODEX_HOME:-$HOME/.codex}"
export PWCLI="$CODEX_ROOT/skills/playwright/scripts/playwright_cli.sh"
```

如果直接使用本仓库，应将 `PWCLI` 设置为 `playwright/scripts/playwright_cli.sh` 的绝对路径，不要假设它已经安装到 `$CODEX_HOME`。

为了保证可复现，可以固定 CLI 包版本：

```bash
export PLAYWRIGHT_CLI_PACKAGE="@playwright/cli@<verified-version>"
```

## 快速开始

```bash
"$PWCLI" open https://playwright.dev --headed
"$PWCLI" snapshot
"$PWCLI" click e15
"$PWCLI" type "Playwright"
"$PWCLI" press Enter
"$PWCLI" screenshot
```

## 核心流程

1. 打开页面。
2. 执行 snapshot 获取稳定的元素引用。
3. 使用最新 snapshot 中的引用进行交互。
4. 导航或页面发生重大变化后重新 snapshot。
5. 必要时保存截图、PDF 或 trace。

```bash
"$PWCLI" open https://example.com
"$PWCLI" snapshot
"$PWCLI" click e3
"$PWCLI" snapshot
```

元素引用在导航、显著 DOM 变化、弹窗或菜单变化、标签页切换后可能失效。引用失败时重新执行 snapshot，不要猜测旧引用。

## 推荐模式

### 填写表单

```bash
"$PWCLI" open https://example.com/form
"$PWCLI" snapshot
"$PWCLI" fill e1 "user@example.com"
"$PWCLI" fill e2 "$TEST_PASSWORD"
"$PWCLI" click e3
"$PWCLI" snapshot
```

### 调试流程

```bash
"$PWCLI" open https://example.com --headed
"$PWCLI" tracing-start
# 执行交互
"$PWCLI" tracing-stop
"$PWCLI" requests
```

### 多标签页

```bash
"$PWCLI" tab-new https://example.com
"$PWCLI" tab-list
"$PWCLI" tab-select 0
"$PWCLI" snapshot
```

## Wrapper

wrapper 使用 `npx --package` 启动 CLI，无需全局安装。可通过 `PLAYWRIGHT_CLI_PACKAGE` 固定版本；当没有显式提供 `--session`、`-s`、`--session=...` 或 `-s=...` 时，才会注入 `PLAYWRIGHT_CLI_SESSION`。

```bash
"$PWCLI" --help
```

## 参考文档

按需阅读：

- CLI 命令参考：`references/cli.md`
- 实用流程与故障排查：`references/workflows.md`
- 高级命令、存储、请求 mock 和测试调试：阅读已安装 Playwright CLI 包中的对应 reference。

## 安全边界

- 在引用 `e12` 等元素 ID 前必须先执行 snapshot。
- 优先使用明确的 CLI 命令；只有无法表达时才使用 `eval` 或 `run-code`。
- `eval` 和 `run-code` 等同于在页面上下文执行任意代码，执行前确认页面和数据范围。
- 密码、token、Cookie 和 Authorization header 使用环境变量或测试账号，不要写入命令、脚本或日志。
- snapshot、trace、video、PDF、storage state、Cookie 和 network log 可能包含敏感数据，不要提交到版本库。
- 本仓库的产物放入 `output/playwright/`，不要创建新的顶层产物目录。
- 默认使用 CLI 工作流，不生成 Playwright Test spec，除非用户明确要求。
