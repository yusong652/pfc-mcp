# pfc-mcp-bridge

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
- `websockets==9.1`

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Server won't start | `pip install websockets==9.1` in PFC Python |
| Port in use | Use `pfc_mcp_bridge.start(port=9002)` or `pfc-mcp-bridge --port 9002` |
| Connection failed | Check bridge is running, port is available, see `.pfc-bridge/bridge.log` |
| No task execution | Ensure `pfc_mcp_bridge.start()` is running in PFC |

For full MCP client setup, see [pfc-mcp](https://pypi.org/project/pfc-mcp/).

License: MIT ([LICENSE](https://github.com/yusong652/pfc-mcp/blob/main/LICENSE)).
