# WARP.md

Guidance for coding agents working in the `pfc-mcp` repository.

## Project Overview

`pfc-mcp` provides an MCP server for ITASCA PFC workflows plus a bridge runtime that runs inside PFC GUI.

This repository intentionally has two runtime contexts:

- `src/pfc_mcp/` (Python >= 3.10): MCP server package used by clients/tooling
- `pfc-bridge/` (PFC embedded Python, often 3.6): WebSocket bridge running inside PFC GUI

Treat these as separate deployment targets even though they live in one repository.

## Core Architecture

### MCP side (`src/pfc_mcp`)

- Exposes documentation tools and execution tools through FastMCP
- Communicates with bridge via WebSocket client (`pfc_mcp.bridge.client`)
- Returns a unified tool envelope: `ok`, `data`, `error`
- Uses script-first execution model (`pfc_execute_task` + `pfc_check_task_status`)

### Bridge side (`pfc-bridge`)

- Runs in PFC GUI process
- Owns thread-safe interaction with ITASCA SDK
- Handles long-running tasks and diagnostics
- Must be started from PFC GUI (for example with `%run .../pfc-bridge/start_bridge.py`)

## Repository Layout

```text
pfc-mcp/
├── src/pfc_mcp/
│   ├── bridge/          # MCP-side bridge client/task manager
│   ├── docs/            # command/API/reference search system
│   ├── tools/           # MCP tool implementations
│   ├── scripts/         # generated script helpers (plot capture, etc.)
│   ├── formatting.py    # shared response formatting
│   └── server.py        # MCP server entrypoint
├── pfc-bridge/          # runtime executed inside PFC GUI
└── tests/               # MCP/tool contract tests
```

## Development Commands

Run from repository root.

```bash
uv sync
uv sync --group dev
uv run pfc-mcp
uv run pytest tests/test_phase2_tools.py
uv run pytest tests/test_phase3_capture_plot.py
uv run pytest tests/test_tool_contracts.py
```

## Engineering Rules

1. Keep MCP and bridge concerns separate.
   - Do not couple MCP logic to PFC GUI internals.
   - Do not introduce application/session policy into bridge runtime.

2. Preserve script-only execution semantics.
   - `pfc_execute_task` submits scripts and returns quickly.
   - Progress/result retrieval goes through `pfc_check_task_status`.

3. Maintain structured tool contracts.
   - Prefer stable machine-readable keys over ad-hoc text parsing.
   - Use the unified envelope for all tool business payloads:
     - success: `{"ok": true, "data": ...}`
     - error: `{"ok": false, "error": {"code": str, "message": str, "details"?: object}}`
   - Enforce coherence: `ok=true` must not include `error`; `ok=false` must include `error`.
   - Do not require duplicate presentation fields (for example, `display`) when they mirror structured data.
   - Let clients render human-facing formatting from structured fields.
   - Documentation tools must keep `data` consistent as:
     - `source`: `"commands" | "python_api" | "reference"`
     - `action`: `"browse" | "query"`
     - `entries`: `list[object]`
     - `summary`: `object` (counts/hints/context)
   - Keep query/path/input echo minimal; prefer putting necessary context in `summary` or `error.details.input`.

4. Keep compatibility when practical.
   - If moving shared helpers, keep thin compatibility re-exports when tests or downstream code rely on old import paths.

5. Respect runtime constraints.
   - MCP package uses modern deps (`websockets>=15`).
   - Bridge side may require legacy-compatible deps (`websockets==9.1`) in PFC Python.

## Testing Expectations

- For tool/contract changes, run:
  - `tests/test_phase2_tools.py`
  - `tests/test_tool_contracts.py`
- For plot/diagnostic changes, also run:
  - `tests/test_phase3_capture_plot.py`

Mock bridge based tests are preferred for deterministic CI.

## Documentation Sources

PFC searchable docs live under:

- `src/pfc_mcp/docs/resources/command_docs/`
- `src/pfc_mcp/docs/resources/python_sdk_docs/`
- `src/pfc_mcp/docs/resources/references/`

When changing schema/content shape, verify browse/query tool behavior remains consistent.

## Commit Style

Use conventional prefixes seen in repository history, for example:

- `feat: ...`
- `fix: ...`
- `refactor: ...`
- `test: ...`
- `docs: ...`

Keep commit messages focused on why the change was needed.
