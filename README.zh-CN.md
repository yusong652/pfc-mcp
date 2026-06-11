<p align="center">
  <img src="https://raw.githubusercontent.com/yusong652/pfc-mcp/assets/header.gif" alt="pfc-mcp" width="70%">
</p>

# pfc-mcp

[English](https://github.com/yusong652/pfc-mcp/blob/main/README.md) | [简体中文](https://github.com/yusong652/pfc-mcp/blob/main/README.zh-CN.md)

[![PyPI](https://img.shields.io/pypi/v/pfc-mcp)](https://pypi.org/project/pfc-mcp/)
[![Downloads](https://static.pepy.tech/badge/pfc-mcp)](https://pepy.tech/project/pfc-mcp)
[![GitHub stars](https://img.shields.io/github/stars/yusong652/pfc-mcp)](https://github.com/yusong652/pfc-mcp/stargazers)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)

`pfc3d>model new ;now, with LLM.`

**pfc-mcp** 通过 [Model Context Protocol](https://modelcontextprotocol.io/) 将 AI 智能体连接到 [ITASCA PFC](https://www.itascacg.com/software/pfc) —— Itasca 的离散元方法（DEM）软件。通过自然语言对话即可浏览文档、运行仿真和执行代码。

`pfc3d>model solve ;LLM solves.`

![pfc-mcp demo](https://raw.githubusercontent.com/yusong652/pfc-mcp/assets/pfc-mcp.gif)

## 工具（10）

**5 个文档工具** — 浏览和搜索 PFC 命令、Python API 及参考文档。无需 bridge。

**5 个执行工具** — 交互式 REPL、任务提交、进度监控、中断和历史浏览。需要 bridge。

## 首次启动配置

### 前置条件

- 已安装 **ITASCA PFC 6.0、7.0 或 9.0**
- 已安装 **[uv](https://docs.astral.sh/uv/getting-started/installation/)**（用于 `uvx`）

### 智能体自动配置（推荐）

将以下文本复制给你的 AI 智能体，让它自动完成配置：

```text
请全程用中文与我交流。然后获取并完整按照这份引导指南执行（指南为英文，照其步骤操作即可）：
https://raw.githubusercontent.com/yusong652/pfc-mcp/main/docs/agentic/pfc-mcp-bootstrap.md
```

### 手动配置

**1. 在客户端配置中注册 MCP 服务：**

```json
{
  "mcpServers": {
    "pfc-mcp": {
      "command": "uvx",
      "args": ["pfc-mcp"]
    }
  }
}
```

**2. 在 PFC 中启动 bridge：**

下载 [`addon.py`](addon.py)，然后在 PFC 中任选一种方式执行：

- 把这个文件的内容复制到 PFC 的 IPython 控制台里运行
- 或者先把这个文件下载到本地，再在 PFC GUI 里执行它

<img src="https://raw.githubusercontent.com/yusong652/pfc-mcp/assets/addon.gif" alt="addon.py 演示" width="60%">

### 验证

重启你的 AI 智能体（Claude Code、Codex CLI、Gemini CLI 等），让它调用 `pfc_execute_code` 来验证连接是否正常。

## 日常启动

完成首次配置之后，每次启动 PFC 只需要在 IPython 控制台里运行下面两行，bridge 起来后就可以继续用了：

```python
import itasca_mcp_bridge
itasca_mcp_bridge.start()
```

`start()` 会先检查 PyPI 上是否有新版 bridge，有则自动升级再启动。MCP 客户端配置会一直保留。

## 功能亮点

- **多版本 PFC 支持** — 通过 `version` 参数查阅 PFC 6.0、7.0、9.0 的命令文档
- **层级式文档浏览** — 智能体沿着 PFC 命令树自主发现能力与边界，减少幻觉命令
- **增强的 plot 文档** — 在官方文档基础上补充了 plot items 参考文档
- **交互式 REPL** — 正式编写脚本前快速试错，智能体可以快速迭代验证
- **任务全生命周期管理** — 提交长时仿真、监控进度、中止运行中的任务、浏览历史任务
- **多客户端兼容** — 支持 Claude Code、Codex CLI、Gemini CLI、GitHub Copilot CLI、OpenCode、toyoura-nagisa 等 MCP 客户端

## 故障排查

详见 bootstrap 指南中的[故障排查章节](docs/agentic/pfc-mcp-bootstrap.md#troubleshooting)。

## 开发

详见 [开发者指南：从源码安装与运行](docs/development/source-install.zh-CN.md)。

<a href="https://glama.ai/mcp/servers/yusong652/pfc-mcp">
  <img width="200" height="105" src="https://glama.ai/mcp/servers/yusong652/pfc-mcp/badge" alt="pfc-mcp MCP server" />
</a>

## 贡献

欢迎提交 PR 和 Issue！参见[开发者指南](docs/development/source-install.zh-CN.md)了解如何开始。

## 许可证

MIT，详见 [LICENSE](LICENSE)。
