# PFC Bridge Server

> **Independent WebSocket service for ITASCA PFC integration**
> Runs inside PFC GUI's IPython environment, exposing PFC Python SDK as remote API

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python: 3.6+](https://img.shields.io/badge/Python-3.6%2B-blue.svg)](https://www.python.org/downloads/)

---

## What is this?

**PFC Bridge Server** is a standalone service that enables remote control of [ITASCA PFC](https://www.itascacg.com/software/pfc) (Particle Flow Code) discrete element simulations through WebSocket communication.

### Key Characteristics

- **Independent Service**: Runs in PFC's Python environment (not part of client applications)
- **External Dependency**: Similar to PostgreSQL or Redis for client applications
- **Production-Grade**: Non-blocking task management, auto-reconnect, thread-safe execution
- **Script-Only Workflow**: All PFC operations via Python scripts using `itasca.command()`
- **Git Version Tracking**: Automatic code snapshots on dedicated `pfc-executions` branch

### Architecture Position

```
+-------------------+     WebSocket      +------------------+     API       +------------+
|  Client Apps      | <----------------- |  PFC Server      | <------------ | ITASCA SDK |
| (toyoura-nagisa)  |     ws://9001      |  (This Project)  |   itasca.*    |   (PFC)    |
+-------------------+                    +------------------+               +------------+
     Python 3.11+                             Python 3.6+                    Main Thread
     Any machine                              PFC GUI Process                Thread-Sensitive
```

**Not part of toyoura-nagisa runtime** - This server is an external dependency that happens to be distributed with toyoura-nagisa for convenience.

---

## Quick Start

### Prerequisites

- ITASCA PFC 7.0+ with Python support
- Python 3.6+ (PFC's embedded Python)
- `websockets` library (version 9.1 for PFC compatibility)

### Installation

**Step 1: Install websockets in PFC Python**

In PFC GUI Python Console:
```python
import subprocess
subprocess.run(["pip", "install", "websockets==9.1"])
```

**Step 2: Start the server**

Choose one of the following methods:

**Method 1: Ask Agent (Recommended)**

If using toyoura-nagisa, simply ask the agent:
> "Start PFC server" or "Connect to PFC"

The agent will automatically set up the environment, generate startup scripts, and launch PFC with pfc-bridge.

**Method 2: Manual %run**
```python
# In PFC GUI IPython console
# replace /path/to/pfc-mcp with your pfc-mcp root path
%run /path/to/pfc-mcp/pfc-bridge/start_bridge.py
```

If your path contains spaces, wrap it once with double quotes:

```python
%run "/path/to/pfc-mcp with spaces/pfc-bridge/start_bridge.py"
```

Avoid nested quotes from copy/paste. For example, this will fail because the quote
characters become part of the filename:

```python
%run '"/path/to/pfc-mcp/pfc-bridge/start_bridge.py"'
```

You'll see:
```
============================================================
PFC Bridge Server
============================================================
  URL:       ws://localhost:9001
  Log:       C:\PFC\project\.nagisa\server.log
  Features:  PFC, Interrupt, Diagnostic, Git
------------------------------------------------------------
Commands:  server_status()  run_task_loop()
============================================================
```

> **Note**: The IPython prompt may appear blocked (no `>>>` prompt) because the main thread is running the task loop. This is normal and does not affect WebSocket communication.

**Step 3: Connect from client**

```python
import asyncio
import websockets
import json

async def test_connection():
    async with websockets.connect("ws://localhost:9001") as ws:
        # Execute a Python script
        await ws.send(json.dumps({
            "type": "pfc_task",
            "request_id": "test-001",
            "task_id": "abc123",
            "session_id": "session-001",
            "script_path": "/path/to/simulation.py",
            "description": "Run particle generation",
            "run_in_background": True
        }))

        # Receive result
        result = json.loads(await ws.recv())
        print(result)

asyncio.run(test_connection())
```

---

## Architecture

### Component Overview

```
+-----------------------------------------------------------------------+
|                   PFC Bridge Server (in PFC Process)                  |
|                                                                       |
|  +---------------------------------------------------------------+   |
|  |  WebSocket Server (Background Thread)                         |   |
|  |  - Accept connections, non-blocking message handling          |   |
|  |  - Concurrent message processing per connection               |   |
|  +--------------------+----------------------+--------------------+   |
|                       |                      |                        |
|  +--------------------v------+  +------------v------------------+    |
|  |  Handlers (handlers/)     |  |  Services (services/)         |    |
|  |  - task_handlers          |  |  - git_version (snapshots)    |    |
|  |  - console_handlers       |  |  - user_console (> commands)  |    |
|  |  - diagnostic_handlers    |  +-------------------------------+    |
|  |  - workspace_handlers     |                                       |
|  |  - utility_handlers       |  +-------------------------------+    |
|  +--------------------+------+  |  Signals (signals/)           |    |
|                       |         |  - interrupt (task control)   |    |
|                       |         |  - diagnostic (callbacks)     |    |
|                       |         +-------------------------------+    |
|  +--------------------v------------------------------------------+   |
|  |  Execution (execution/)                                       |   |
|  |  - MainThreadExecutor: Queue-based main thread execution      |   |
|  |  - ScriptRunner: Python script execution with output capture  |   |
|  +--------------------+------------------------------------------+   |
|                       |                                              |
|  +--------------------v------------------------------------------+   |
|  |  Tasks (tasks/)                                               |   |
|  |  - Task registry and lifecycle tracking                       |   |
|  |  - Task persistence to disk                                   |   |
|  |  - Status queries with pagination                             |   |
|  +--------------------+------------------------------------------+   |
|                       |                                              |
|  +--------------------v------------------------------------------+   |
|  |  ITASCA PFC SDK (itasca module) - MAIN THREAD ONLY            |   |
|  +---------------------------------------------------------------+   |
+-----------------------------------------------------------------------+
```

### Key Design Decisions

1. **Hybrid Threading**: WebSocket server runs in background thread, PFC commands execute in main thread
2. **Script-Only Execution**: All PFC operations via Python scripts using `itasca.command()` pattern
3. **Non-blocking**: Long tasks return task_id immediately, query progress separately
4. **Thread Safety**: All PFC SDK calls go through main thread queue
5. **Git Snapshots**: Each execution creates a version snapshot on `pfc-executions` branch
6. **Dual Execution Path**: Queue execution for idle PFC, callback execution for diagnostics/interrupt during cycles

---

## API Reference

### Message Types

#### 1. Execute PFC Task (`pfc_task`)

Execute a Python script file with PFC commands.

**Request**:
```json
{
  "type": "pfc_task",
  "request_id": "unique-id",
  "task_id": "abc123",
  "session_id": "session-001",
  "script_path": "/absolute/path/to/script.py",
  "description": "Task description from agent",
  "timeout_ms": 30000,
  "run_in_background": true,
  "source": "agent"
}
```

| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| `type` | Yes | - | Must be `"pfc_task"` |
| `request_id` | No | `"unknown"` | Request identifier for response matching |
| `task_id` | Yes | - | Backend-generated task ID (6-char hex) |
| `session_id` | No | `"default"` | Session identifier for task isolation |
| `script_path` | Yes | - | Absolute path to Python script |
| `description` | No | `""` | Task description (shown in task list) |
| `timeout_ms` | No | `null` | Timeout in milliseconds |
| `run_in_background` | No | `true` | If true, returns immediately with task_id |
| `source` | No | `"agent"` | Task source: `"agent"` or `"user_console"` |

**Response (Background Task)**:
```json
{
  "type": "result",
  "request_id": "unique-id",
  "status": "pending",
  "message": "Task submitted for background execution",
  "data": {
    "task_id": "abc123",
    "script_name": "simulation.py",
    "git_commit": "a1b2c3d4"
  }
}
```

**Response (Foreground Task)**:
```json
{
  "type": "result",
  "request_id": "unique-id",
  "status": "success",
  "message": "Script executed successfully",
  "data": {
    "task_id": "abc123",
    "output": "Cycle 1000: unbalanced=1.2e-5\n..."
  }
}
```

#### 2. User Console (`user_console`)

Execute Python code from user console (> prefix commands).

**Request**:
```json
{
  "type": "user_console",
  "request_id": "unique-id",
  "task_id": "def456",
  "session_id": "session-001",
  "workspace_path": "/absolute/path/to/workspace",
  "code": "print(ball.count())",
  "timeout_ms": 30000,
  "run_in_background": false
}
```

| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| `workspace_path` | Yes | - | Absolute path to PFC workspace |
| `code` | Yes | - | Python code to execute |
| `run_in_background` | No | `false` | If true, supports ctrl+b backgrounding |

**Response**:
```json
{
  "type": "user_console_result",
  "request_id": "unique-id",
  "status": "success",
  "message": "Executed: print(ball.count())",
  "data": {
    "output": "1000\n",
    "code_preview": "print(ball.count())"
  }
}
```

#### 3. Diagnostic Execute (`diagnostic_execute`)

Execute diagnostic scripts (e.g., plot capture) with smart execution path selection.

**Request**:
```json
{
  "type": "diagnostic_execute",
  "request_id": "unique-id",
  "script_path": "/path/to/capture_plot.py",
  "timeout_ms": 30000
}
```

**Response**:
```json
{
  "type": "diagnostic_result",
  "request_id": "unique-id",
  "status": "success",
  "execution_path": "queue",
  "message": "Diagnostic completed",
  "data": {
    "output_path": "/path/to/exported_plot.png"
  }
}
```

**Execution Strategy**:
1. Try queue execution first (8s timeout) - works when PFC is idle
2. If queue blocked, use callback execution - works during cycle

#### 4. Check Task Status (`check_task_status`)

Query the status of a running or completed task.

**Request**:
```json
{
  "type": "check_task_status",
  "request_id": "unique-id",
  "task_id": "abc123"
}
```

**Response**:
```json
{
  "type": "result",
  "request_id": "unique-id",
  "status": "running",
  "message": "Task executing (elapsed 15.23s)",
  "data": {
    "task_id": "abc123",
    "elapsed_time": 15.23,
    "output": "Cycle 10000: unbalanced=1.2e-5\n..."
  }
}
```

**Status Values**: `"pending"`, `"running"`, `"completed"`, `"failed"`, `"interrupted"`, `"not_found"`

#### 5. List Tasks (`list_tasks`)

List tracked tasks with optional filtering and pagination.

**Request**:
```json
{
  "type": "list_tasks",
  "request_id": "unique-id",
  "session_id": "session-001",
  "source": "agent",
  "offset": 0,
  "limit": 10
}
```

**Response**:
```json
{
  "type": "result",
  "request_id": "unique-id",
  "status": "success",
  "message": "Found 5 tracked task(s) for session session-001",
  "data": [
    {
      "task_id": "abc123",
      "status": "completed",
      "script_name": "simulation.py",
      "description": "Run gravity settling",
      "start_time": "2025-01-11T10:30:00",
      "elapsed_time": 45.2,
      "git_commit": "a1b2c3d4"
    }
  ],
  "pagination": {
    "total_count": 5,
    "displayed_count": 5,
    "offset": 0,
    "limit": 10,
    "has_more": false
  }
}
```

#### 6. Mark Task Notified (`mark_task_notified`)

Mark a task as notified (prevents repeated completion notifications).

**Request**:
```json
{
  "type": "mark_task_notified",
  "request_id": "unique-id",
  "task_id": "abc123"
}
```

#### 7. Interrupt Task (`interrupt_task`)

Request interruption of a running task.

**Request**:
```json
{
  "type": "interrupt_task",
  "request_id": "unique-id",
  "task_id": "abc123"
}
```

#### 8. Workspace Operations

**Get Working Directory**:
```json
{
  "type": "get_working_directory",
  "request_id": "unique-id"
}
```

**Reset Workspace** (clears git execution branch):
```json
{
  "type": "reset_workspace",
  "request_id": "unique-id"
}
```

#### 9. Ping (`ping`)

Health check / keepalive.

**Request**:
```json
{
  "type": "ping",
  "request_id": "unique-id"
}
```

**Response**:
```json
{
  "type": "pong",
  "request_id": "unique-id"
}
```

---

## Configuration

Create `config.py` from `config_example.py`:

```python
# WebSocket Server Configuration
WEBSOCKET_HOST = "localhost"
WEBSOCKET_PORT = 9001

# Ping Configuration (for long-running tasks)
PING_INTERVAL = 120  # seconds (2 minutes)
PING_TIMEOUT = 300   # seconds (5 minutes)

# Task Processing Configuration
AUTO_START_TASK_LOOP = True  # Auto-start continuous task loop on startup
```

| Setting | Default | Description |
|---------|---------|-------------|
| `WEBSOCKET_HOST` | `"localhost"` | Server host address |
| `WEBSOCKET_PORT` | `9001` | Server port number |
| `PING_INTERVAL` | `120` | Interval between ping frames (seconds) |
| `PING_TIMEOUT` | `300` | Timeout for pong response (seconds) |
| `AUTO_START_TASK_LOOP` | `True` | Auto-start `run_task_loop()` on startup |

---

## Project Structure

```
pfc-bridge/
├── server/                           # Server implementation
│   ├── server.py                     # WebSocket server + handler routing
│   ├── execution/                    # Execution engines
│   │   ├── main_thread.py            # Queue-based main thread execution
│   │   └── script.py                 # Python script execution
│   ├── tasks/                        # Task lifecycle management
│   │   ├── manager.py                # Task registry
│   │   ├── persistence.py            # Task persistence to disk
│   │   ├── task_base.py              # Task base class
│   │   └── task_types.py             # ScriptTask implementation
│   ├── signals/                      # Inter-process communication
│   │   ├── interrupt.py              # Task interruption control + callback
│   │   └── diagnostic.py             # Callback-based diagnostic execution
│   ├── services/                     # Business services
│   │   ├── git_version.py            # Git snapshot management
│   │   └── user_console.py           # User console script management
│   ├── handlers/                     # Message handlers
│   │   ├── context.py                # Server context (shared state)
│   │   ├── task_handlers.py          # pfc_task, check_task_status, list_tasks
│   │   ├── console_handlers.py       # user_console execution
│   │   ├── diagnostic_handlers.py    # diagnostic_execute
│   │   ├── workspace_handlers.py     # reset_workspace, get_working_directory
│   │   ├── utility_handlers.py       # ping, interrupt_task
│   │   └── helpers.py                # Handler utilities
│   └── utils/                        # Common utilities
│       ├── file_buffer.py            # File-backed output buffer
│       ├── path_utils.py             # Path utilities
│       └── response.py               # Response formatting
├── workspace_template/               # Template for new PFC workspaces
│   ├── .gitignore                    # Default gitignore for PFC projects
│   └── README.md                     # Workspace documentation
├── start_bridge.py                   # Startup script
├── config_example.py                 # Configuration template
├── pyproject.toml                    # Dependencies
└── README.md                         # This file
```

---

## Features

### Git Version Tracking

Each `pfc_task` execution (from agent) creates a git snapshot on the `pfc-executions` branch:

- **Automatic**: No manual git commands needed
- **Non-disruptive**: Uses `git commit-tree` to avoid branch switching
- **Traceable**: Each task includes `git_commit` in response

**Important**: Never checkout or work on the `pfc-executions` branch directly. This branch is automatically managed by the server.

### Task Interruption

Tasks can be interrupted during execution:

1. Send `interrupt_task` message with `task_id`
2. Interrupt callback fires at next PFC cycle boundary
3. Task status changes to `"interrupted"`

### Diagnostic Execution (Cycle-Safe)

Diagnostic scripts (e.g., plot capture) use smart execution path selection:

1. **Queue path**: Used when PFC is idle (most cases)
2. **Callback path**: Used during active `model cycle` - executes at cycle boundary

This enables capturing plots even while simulations are running.

### Task Persistence

Tasks are persisted to disk in `.nagisa/tasks/` directory:

- Survives server restarts
- Includes output logs
- Historical tasks loaded on startup

---

## Troubleshooting

### Server won't start

```python
# Install websockets in PFC Python
>>> import subprocess
>>> subprocess.run(["pip", "install", "websockets==9.1"])
```

If you see an error like:

```
File `'"C:\\...\\start_bridge.py"'.py'` not found
```

Your `%run` path is over-quoted. Use:

```python
%run /path/to/pfc-mcp/pfc-bridge/start_bridge.py
```

### Tasks not processing

```python
# Check if task loop is running
>>> server_status()

# Start task loop manually (if AUTO_START_TASK_LOOP=False)
>>> run_task_loop()

# Check queue size
>>> get_queue_size()
```

### Git snapshots not working

Check server startup log for git status:
```
  Features:  PFC, Interrupt, Diagnostic, Git  # Git should be listed
```

If git is not listed:
```python
# Initialize git in your PFC workspace
>>> !git init
>>> !git add -A
>>> !git commit -m "Initial commit"
```

### Connection failed

- Check server is running: `server_status()`
- Check port 9001 is free
- Check firewall allows localhost:9001
- Check log file: `.nagisa/server.log`

### Task timeout

Long-running tasks should use `run_in_background=True`:
```json
{
  "type": "pfc_task",
  "run_in_background": true,
  ...
}
```

Then poll with `check_task_status`.

---

## Testing

If using with toyoura-nagisa, verify integration with a minimal tool workflow:

```bash
# 1) pfc_list_tasks        (connectivity and task store)
# 2) pfc_execute_task      (small foreground/background script)
# 3) pfc_check_task_status (progress and completion states)
```

Tests: script execution, background tasks, status queries, WebSocket responsiveness, task completion, git snapshots.

---

## Best Practices

### DO

- Use `run_in_background=True` for long simulations
- Query task status instead of blocking
- Use script files for all PFC operations
- Let server auto-initialize git in workspaces
- Use `task_id` generated by backend for tracking

### DON'T

- Execute raw PFC commands directly (use scripts)
- Wait indefinitely for long tasks (use task_id + check_status)
- Work on the `pfc-executions` branch manually
- Generate `task_id` on the server side

---

## Additional Resources

- **[ITASCA PFC Documentation](https://www.itascacg.com/software/pfc)**: Official PFC docs
- **Client Implementation**: If using toyoura-nagisa, see `packages/backend/infrastructure/pfc/` for WebSocket client
- **PFC MCP Tools**: See `pfc-mcp/src/pfc_mcp/tools/` for MCP tool implementations

---

## License

Same as parent toyoura-nagisa project - see LICENSE file in repository root.

---

## Acknowledgments

**Architecture & Design**: Nagisa Toyoura
**Implementation**: Claude (Anthropic)
**ITASCA SDK**: ITASCA Consulting Group, Inc.

---

**This is an independent service, not a module of toyoura-nagisa.**
It runs in PFC GUI's Python environment and can be used by any WebSocket client.
