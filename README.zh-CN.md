# pfc-mcp

[English](README.md) | [简体中文](README.zh-CN.md)

[![PyPI](https://img.shields.io/pypi/v/pfc-mcp)](https://pypi.org/project/pfc-mcp/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)

**一个为 [ITASCA PFC](https://www.itascacg.com/software/pfc) 提供完整能力的 MCP 服务器：可浏览文档、运行仿真、抓取图像，并通过自然语言交互完成操作。**

基于 [Model Context Protocol](https://modelcontextprotocol.io/) 构建，`pfc-mcp` 可以把任何兼容 MCP 的 AI 客户端（Claude Code、Codex CLI、Gemini CLI、OpenCode、toyoura-nagisa 等）变成 PFC 协作助手：查询命令、执行脚本、监控长时仿真、抓取可视化结果。

![pfc-mcp demo](https://raw.githubusercontent.com/yusong652/pfc-mcp/assets/pfc-mcp.gif)

## 工具（10）

### 文档类（5）- 无需 bridge

- 浏览 PFC 命令树、Python SDK 参考、参考文档（接触模型、range 元素）
- 基于关键词搜索命令和 Python API（BM25 排序）

### 执行类（5）- 需要在运行中的 PFC 进程中启动 bridge

- 提交 Python 脚本并实时轮询状态/输出
- 跨会话列出和管理任务
- 中断运行中的仿真
- 抓取 PFC 图像（支持相机、着色、切面等配置）

## 快速开始

### 前置条件

- 已安装 **ITASCA PFC 7.0**（`pfc2d700_gui.exe` 或 `pfc3d700_gui.exe`）
- 已安装 **[uv](https://docs.astral.sh/uv/getting-started/installation/)**（用于 `uvx`）

### 智能体自动配置（推荐）

将以下文本复制给你的 AI 智能体，让它自动完成配置：

```text
Fetch and follow this bootstrap guide end-to-end:
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

**2. 安装依赖：**

```python
import subprocess
subprocess.run(["pip", "install", "pfc-mcp-bridge"])
```

### 启动 Bridge 并验证

```python
import pfc_mcp_bridge
pfc_mcp_bridge.start()
```

![PFC GUI Python console](https://raw.githubusercontent.com/yusong652/pfc-mcp/assets/init.png)

**验证方法**：重连 MCP 客户端后，让智能体调用 `pfc_list_tasks`，确认 MCP 与 bridge 连接均正常。

## 设计亮点

- **以文档为边界地图**：浏览与搜索工具帮助智能体明确 PFC 能力边界，减少“幻觉命令”
- **实时状态的任务队列**：脚本按顺序排队执行，智能体可实时轮询输出和状态
- **基于回调的控制**：可优雅中断长时间 `cycle()`，并在仿真进行中抓取图像

## 运行时模型

| 组件 | PyPI | Python | 角色 |
|------|------|--------|------|
| **pfc-mcp** | [![PyPI](https://img.shields.io/pypi/v/pfc-mcp)](https://pypi.org/project/pfc-mcp/) | >= 3.10 | MCP 服务器（文档工具 + 执行客户端） |
| **pfc-mcp-bridge** | [![PyPI](https://img.shields.io/pypi/v/pfc-mcp-bridge)](https://pypi.org/project/pfc-mcp-bridge/) | >= 3.6 | PFC 进程内 WebSocket bridge（GUI 或控制台） |

文档工具可独立使用；执行工具依赖已运行的 bridge。

## 故障排查

| 现象 | 处理方式 |
|---------|-----|
| 找不到 `uvx` | [安装 uv](https://docs.astral.sh/uv/getting-started/installation/)，或将客户端 MCP 配置改为 `command: "uv"`、`args: ["tool", "run", "pfc-mcp"]` |
| Bridge 启动失败 | 在 PFC Python 中安装/升级 `pfc-mcp-bridge`（`pip install -U pfc-mcp-bridge`） |
| 任务不执行 / 无法连接 | 若执行工具返回 `ok=false`、`error.code=bridge_unavailable`、`error.details.reason=cannot connect to bridge service`，请在 PFC 中启动 bridge（`pfc_mcp_bridge.start()`），并确认 `PFC_MCP_BRIDGE_URL` 与 bridge 实际地址一致 |
| `pfc_capture_plot` 不可用 | 图像抓取仅支持 PFC GUI，控制台模式不支持 |
| Bridge 使用自定义端口 | 将 MCP 服务端环境变量设为 `PFC_MCP_BRIDGE_URL=ws://localhost:<bridge-port>`（例如 `ws://localhost:9002`） |
| 连接失败 | 检查 bridge 是否运行、目标端口是否可用，查看 `.pfc-bridge/bridge.log` |

## 开发

```bash
uv sync --group dev    # 安装开发依赖
uv run pytest          # 运行测试
uv run pfc-mcp         # 本地启动服务
```

## 许可证

MIT，详见 [LICENSE](LICENSE)。
