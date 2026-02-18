# pfc-mcp-bridge

[English](README.md) | [简体中文](README.zh-CN.md)

[![PyPI](https://img.shields.io/pypi/v/pfc-mcp-bridge)](https://pypi.org/project/pfc-mcp-bridge/)

Runtime bridge that runs inside a PFC process and enables execution tools for [pfc-mcp](https://pypi.org/project/pfc-mcp/).

## Quick Start

Install and run in PFC Python console:

```python
import subprocess
subprocess.run(["pip", "install", "pfc-mcp-bridge"])

import pfc_mcp_bridge
pfc_mcp_bridge.start()
```

The bridge auto-detects the runtime: Qt timer in GUI, blocking loop in console.

Expected output:

```text
============================================================
PFC Bridge Server
============================================================
  URL:         ws://localhost:9001
  Log:         /your-working-dir/.pfc-bridge/bridge.log
  Callbacks:   Interrupt, Diagnostic (registered)
============================================================
```

## Requirements

- Python >= 3.6 (PFC embedded Python)
- ITASCA PFC 7.0+
- `websockets==9.1` (installed automatically with `pfc-mcp-bridge`)

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Server won't start | In PFC Python, install/upgrade `pfc-mcp-bridge` (`pip install -U pfc-mcp-bridge`) |
| Port in use | Use `pfc_mcp_bridge.start(port=9002)` in PFC Python, then set MCP server env `PFC_MCP_BRIDGE_URL=ws://localhost:9002` |
| Connection failed | Check bridge is running, port is available, see `.pfc-bridge/bridge.log` |
| No task execution / cannot connect from MCP | If execution tools return `ok=false`, `error.code=bridge_unavailable`, and `error.details.reason=cannot connect to bridge service`, ensure bridge is running in PFC (`pfc_mcp_bridge.start()`) and `PFC_MCP_BRIDGE_URL` matches bridge URL |

For full MCP client setup, see [pfc-mcp](https://pypi.org/project/pfc-mcp/).

License: MIT ([LICENSE](https://github.com/yusong652/pfc-mcp/blob/main/LICENSE)).
