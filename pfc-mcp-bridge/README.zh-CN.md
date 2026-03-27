# pfc-mcp-bridge

[English](https://github.com/yusong652/pfc-mcp/blob/main/pfc-mcp-bridge/README.md) | [简体中文](https://github.com/yusong652/pfc-mcp/blob/main/pfc-mcp-bridge/README.zh-CN.md)

[![PyPI](https://img.shields.io/pypi/v/pfc-mcp-bridge)](https://pypi.org/project/pfc-mcp-bridge/)

运行在 PFC 进程内的 bridge，为 [pfc-mcp](https://pypi.org/project/pfc-mcp/) 提供执行类工具能力。

## 快速开始

在 PFC Python 控制台中安装并启动：

```python
import sys

if sys.version_info < (3, 10):
    import pip

    pip.main(["install", "--user", "-U", "pfc-mcp-bridge"])
else:
    from pip._internal.cli.main import main as pip_main

    pip_main(["install", "--user", "-U", "pfc-mcp-bridge"])

import pfc_mcp_bridge
pfc_mcp_bridge.start()
```

Bridge 会自动检测运行环境：GUI 使用 Qt 定时器，控制台使用阻塞循环。
在 PFC 的 IPython 控制台里安装 `pfc-mcp-bridge` 时，也会自动安装匹配的 `websockets` 版本：PFC 6/7 使用 `9.1`，PFC 9 使用 `16.0`。这段安装代码会在 PFC 6/7 中调用 `pip.main(...)`，在 PFC 9 中调用 `pip._internal.cli.main.main(...)`。

预期输出：

```text
============================================================
PFC Bridge Server
============================================================
  URL:         ws://localhost:9001
  Log:         /your-working-dir/.pfc-mcp-bridge/bridge.log
  Callbacks:   Interrupt, Diagnostic (registered)
============================================================
```

## 运行要求

- Python >= 3.6（PFC 6/7 使用 Python 3.6，PFC 9 使用 Python 3.10）
- ITASCA PFC 6.0、7.0 或 9.0
- `pfc-mcp-bridge` 会自动安装匹配的 `websockets` 依赖：Python 3.6 使用 `websockets==9.1`，Python 3.10 使用 `websockets==16.0`

## 故障排查

| 现象 | 处理方式 |
|---------|-----|
| 服务无法启动 | 在 PFC Python/IPython 控制台中重新执行上面的按版本安装片段（PFC 6/7 用 `pip.main(...)`，PFC 9 用 `pip._internal.cli.main.main(...)`） |
| PFC 9 中 `websockets` 版本不匹配 | 在 PFC 9 的 IPython 控制台中执行 `from pip._internal.cli.main import main as pip_main; pip_main(["install", "--user", "websockets==16.0"])` |
| 端口被占用 | 在 PFC Python 中使用 `pfc_mcp_bridge.start(port=9002)`，并将 MCP 服务端环境变量设为 `PFC_MCP_BRIDGE_URL=ws://localhost:9002` |
| 连接失败 | 确认 bridge 正在运行且端口可用，查看 `.pfc-mcp-bridge/bridge.log` |
| 无法执行任务 / MCP 无法连接 | 若执行工具返回 `ok=false`、`error.code=bridge_unavailable`、`error.details.reason=cannot connect to bridge service`，请确认已在 PFC 中运行 `pfc_mcp_bridge.start()`，并检查 `PFC_MCP_BRIDGE_URL` 是否与 bridge 地址一致 |

## 开发

完整本地源码开发流程请参考 [开发者指南：从源码安装与运行](../docs/development/source-install.zh-CN.md)。

从本地源码启动 bridge（无需从 PyPI 安装），在 PFC IPython 控制台中使用 `%run`：

```python
%run C:/path/to/pfc-mcp/pfc-mcp-bridge/start_bridge.py
```

> **注意：** 路径使用正斜杠，不要加引号。

效果与 PyPI 安装方式相同，但直接加载源码，修改代码后重启即可生效。

完整 MCP 客户端配置请参考 [pfc-mcp](https://pypi.org/project/pfc-mcp/)。

许可证：MIT（[LICENSE](https://github.com/yusong652/pfc-mcp/blob/main/LICENSE)）。
