# pfc-mcp-bridge

[English](https://github.com/yusong652/pfc-mcp/blob/main/pfc-mcp-bridge/README.md) | [简体中文](https://github.com/yusong652/pfc-mcp/blob/main/pfc-mcp-bridge/README.zh-CN.md)

[![PyPI](https://img.shields.io/pypi/v/pfc-mcp-bridge)](https://pypi.org/project/pfc-mcp-bridge/)

> **⚠️ 已弃用。** 本包已被 [`itasca-mcp-bridge`](https://pypi.org/project/itasca-mcp-bridge/) 取代——后者是 PFC 与 FLAC3D 共用的产品中立 bridge。新修复（包括 multi-line `it.command()` 死锁修复）只在新包发布，老包不再维护。请改装 `itasca-mcp-bridge` 并下载新的 [`addon.py`](https://github.com/yusong652/pfc-mcp/blob/main/addon.py)。

运行在 PFC 进程内的 bridge，为 [pfc-mcp](https://pypi.org/project/pfc-mcp/) 提供执行类工具能力。

## 快速开始

### 一步式引导

下载 [`addon.py`](../addon.py)，然后在 PFC 中任选一种方式执行：

- 把文件内容复制到 IPython 控制台里运行
- 或者先把文件下载到本地，再在 PFC GUI 里执行它

它会这样工作：

- 如果当前还没有安装 `pfc-mcp-bridge`，会先安装最新版本再启动
- 如果已经安装，会先显示当前版本，并让用户选择是否在启动前升级到最新版
- 随后在当前 PFC Python 环境里直接启动 bridge

Bridge 会自动检测运行环境：GUI 使用 Qt 定时器，控制台使用阻塞循环。
bootstrap 脚本也会自动安装匹配的 `websockets` 版本：PFC 6/7 使用 `9.1`，PFC 9 使用 `16.0`。

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
| 服务无法启动 | 重新获取 bootstrap 脚本后，在 PFC 中再次运行它：可以把内容重新粘贴到 IPython 控制台，或直接在 PFC GUI 中执行下载好的脚本文件 |
| PFC 9 中 `websockets` 版本不匹配 | 在 PFC 9 的 IPython 控制台中执行 `from pip._internal.cli.main import main as pip_main; pip_main(["install", "--user", "websockets==16.0"])` |
| 端口被占用 | 在 PFC Python 中使用 `pfc_mcp_bridge.start(port=9002)`，并将 MCP 服务端环境变量设为 `PFC_MCP_BRIDGE_URL=ws://localhost:9002` |
| 连接失败 | 确认 bridge 正在运行且端口可用，查看 `.pfc-mcp-bridge/bridge.log` |
| 无法执行任务 / MCP 无法连接 | 若执行工具返回 `ok=false`、`error.code=bridge_unavailable`、`error.details.reason=cannot connect to bridge service`，请确认已在 PFC 中运行 `pfc_mcp_bridge.start()`，并检查 `PFC_MCP_BRIDGE_URL` 是否与 bridge 地址一致 |

## 开发

完整本地源码开发流程请参考 [开发者指南：从源码安装与运行](../docs/development/source-install.zh-CN.md)。

如果只是想直接从本地源码启动 bridge，而不先从 PyPI 安装，在 PFC IPython 控制台中使用 `%run`：

```python
%run C:/path/to/pfc-mcp/pfc-mcp-bridge/start_bridge.py
```

> **注意：** 路径使用正斜杠，不要加引号。

效果与 PyPI 安装方式相同，但直接加载源码，修改代码后重启即可生效。

完整 MCP 客户端配置请参考 [pfc-mcp](https://pypi.org/project/pfc-mcp/)。

许可证：MIT（[LICENSE](https://github.com/yusong652/pfc-mcp/blob/main/LICENSE)）。
