# pfc-mcp-bridge

WebSocket bridge for [ITASCA PFC](https://www.itascacg.com/software/pfc) - runs inside PFC GUI to enable remote simulation control.

Pairs with [pfc-mcp](../README.md) to provide AI-driven PFC simulation workflows through the Model Context Protocol (MCP).

## Quick Start

### 1. Install in PFC Python

In PFC GUI Python console:

```python
import subprocess
subprocess.run(["pip", "install", "pfc-mcp-bridge"])
```

### 2. Start the bridge

```python
import pfc_mcp_bridge
pfc_mcp_bridge.start()
```

You'll see:

```
============================================================
PFC Bridge Server
============================================================
  URL:         ws://localhost:9001
  Running:     True
  Features:    PFC, Interrupt, Diagnostic
============================================================

Task loop running (Ctrl+C to stop)...
```

### Alternative: legacy script

If you prefer the `%run` approach:

```python
%run /path/to/pfc-mcp/pfc-bridge/start_bridge.py
```

## How It Works

```
+-------------------+    WebSocket     +------------------+      API       +------------+
|  pfc-mcp          | <--------------> |  pfc-mcp-bridge  | <------------ | ITASCA SDK |
|  (MCP server)     |   ws://9001      |  (this package)  |   itasca.*    |   (PFC)    |
+-------------------+                  +------------------+               +------------+
  Python 3.10+                           Python 3.6+                       Main Thread
  Any machine                            PFC GUI process                   Thread-Sensitive
```

PFC's Python SDK requires main-thread execution. This bridge solves that by:

1. Running a WebSocket server in a **background thread** (accepts connections)
2. Processing PFC commands in the **main thread** via a task queue (thread safety)
3. Providing **callback-based execution** for diagnostics during active simulation cycles

## API Reference

### Message Types

| Type | Description |
| ---- | ----------- |
| `pfc_task` | Execute a Python script in PFC |
| `check_task_status` | Query status and output of a task |
| `list_tasks` | List tracked tasks with pagination |
| `interrupt_task` | Request graceful task interruption |
| `diagnostic_execute` | Execute diagnostic script (cycle-safe) |
| `get_working_directory` | Get PFC working directory |
| `ping` | Health check |

### Execute Task (`pfc_task`)

```json
{
  "type": "pfc_task",
  "request_id": "unique-id",
  "task_id": "abc123",
  "session_id": "session-001",
  "script_path": "/path/to/simulation.py",
  "description": "Run particle generation"
}
```

All tasks are submitted for background execution and return immediately. Use `check_task_status` to poll for progress.

### Check Task Status (`check_task_status`)

```json
{
  "type": "check_task_status",
  "request_id": "unique-id",
  "task_id": "abc123"
}
```

Status values: `pending`, `running`, `completed`, `failed`, `interrupted`, `not_found`.

### Diagnostic Execute (`diagnostic_execute`)

Smart execution path selection: tries queue first (idle PFC), falls back to callback execution (during active cycles). Enables plot capture while simulations are running.

```json
{
  "type": "diagnostic_execute",
  "request_id": "unique-id",
  "script_path": "/path/to/capture_plot.py",
  "timeout_ms": 30000
}
```

## Configuration

`pfc_mcp_bridge.start()` accepts:

| Parameter | Default | Description |
| --------- | ------- | ----------- |
| `host` | `"localhost"` | Server host address |
| `port` | `9001` | Server port number |
| `ping_interval` | `120` | Seconds between ping frames |
| `ping_timeout` | `300` | Seconds to wait for pong |

## Project Structure

```
pfc-bridge/
├── src/pfc_mcp_bridge/              # Package source
│   ├── __init__.py                  # start() entry point
│   ├── __main__.py                  # python -m pfc_mcp_bridge
│   ├── server.py                    # WebSocket server + handler routing
│   ├── execution/                   # Queue-based main thread execution
│   ├── handlers/                    # Message handlers (tasks, diagnostics, etc.)
│   ├── signals/                     # Interrupt + diagnostic callbacks
│   ├── tasks/                       # Task lifecycle management + persistence
│   └── utils/                       # File buffer, path utils, response formatting
├── start_bridge.py                  # Legacy startup script
├── pyproject.toml                   # Package metadata
└── README.md                        # This file
```

## Features

### Task Interruption

Tasks can be interrupted during execution via `interrupt_task`. The interrupt callback fires at the next PFC cycle boundary, changing task status to `interrupted`.

### Diagnostic Execution (Cycle-Safe)

Diagnostic scripts use smart execution path selection:
- **Queue path**: When PFC is idle
- **Callback path**: During active `model cycle` - executes at cycle boundary

### Task Persistence

Tasks are persisted to `.pfc-bridge/tasks/` in the working directory. Survives server restarts.

## Troubleshooting

### Server won't start

```python
# Install websockets in PFC Python
import subprocess
subprocess.run(["pip", "install", "websockets==9.1"])
```

### Tasks not processing

The main thread task loop must be running. `pfc_mcp_bridge.start()` handles this automatically. If using the legacy script, ensure you pressed Enter to start the task loop.

### Connection failed

- Verify server is running (check console output)
- Check port 9001 is free
- Check firewall allows localhost:9001
- Check log: `.pfc-bridge/bridge.log`

## Requirements

- Python >= 3.6 (PFC's embedded Python)
- ITASCA PFC 7.0+ with Python support
- `websockets==9.1`

## License

MIT - see [LICENSE](../LICENSE).
