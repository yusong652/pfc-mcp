# pfc-mcp-bridge

[English](README.md) | [简体中文](README.zh-CN.md)

[![PyPI](https://img.shields.io/pypi/v/pfc-mcp-bridge)](https://pypi.org/project/pfc-mcp-bridge/)

运行在 PFC 进程内的 bridge，为 [pfc-mcp](https://pypi.org/project/pfc-mcp/) 提供执行类工具能力。

## 快速开始

在 PFC Python 控制台中安装并启动：

```python
import subprocess
subprocess.run(["pip", "install", "pfc-mcp-bridge"])

import pfc_mcp_bridge
pfc_mcp_bridge.start()
```

Bridge 会自动检测运行环境：GUI 使用 Qt 定时器，控制台使用阻塞循环。

预期输出：

```text
============================================================
PFC Bridge Server
============================================================
  URL:         ws://localhost:9001
  Log:         /your-working-dir/.pfc-bridge/bridge.log
  Callbacks:   Interrupt, Diagnostic (registered)
============================================================
```

## 运行要求

- Python >= 3.6（PFC 内嵌 Python）
- ITASCA PFC 7.0+
- `websockets==9.1`（随 `pfc-mcp-bridge` 自动安装）

## 故障排查

| 现象 | 处理方式 |
|---------|-----|
| 服务无法启动 | 在 PFC Python 中安装/升级 `pfc-mcp-bridge`（`pip install -U pfc-mcp-bridge`） |
| 端口被占用 | 在 PFC Python 中使用 `pfc_mcp_bridge.start(port=9002)`，并将 MCP 服务端环境变量设为 `PFC_MCP_BRIDGE_URL=ws://localhost:9002` |
| 连接失败 | 确认 bridge 正在运行且端口可用，查看 `.pfc-bridge/bridge.log` |
| 无法执行任务 / MCP 无法连接 | 若执行工具返回 `ok=false`、`error.code=bridge_unavailable`、`error.details.reason=cannot connect to bridge service`，请确认已在 PFC 中运行 `pfc_mcp_bridge.start()`，并检查 `PFC_MCP_BRIDGE_URL` 是否与 bridge 地址一致 |

完整 MCP 客户端配置请参考 [pfc-mcp](https://pypi.org/project/pfc-mcp/)。

许可证：MIT（[LICENSE](https://github.com/yusong652/pfc-mcp/blob/main/LICENSE)）。
