# pfc-mcp

MCP server for ITASCA PFC simulation control and documentation.

## Components

- `src/pfc_mcp/`: MCP server package (docs + execution tools)
- `pfc-bridge/`: bridge runtime for PFC GUI environment (`websockets==9.1`)

`pfc-bridge/` is intentionally not under `src/` because it runs in a different Python environment than the MCP server.

## Tools

- Documentation: `pfc_browse_commands`, `pfc_browse_python_api`, `pfc_browse_reference`, `pfc_query_command`, `pfc_query_python_api`
- Execution: `pfc_execute_task`, `pfc_check_task_status`, `pfc_list_tasks`, `pfc_interrupt_task`, `pfc_capture_plot`

User console execution should use backend-side polling on top of `pfc_execute_task` + `pfc_check_task_status`.

`pfc_capture_plot` saves the image to `output_path` and returns it for visual inspection (via MCP `ImageContent` when the file is locally readable).

## Configuration

Environment variables:

- `PFC_MCP_BRIDGE_URL` (default: `ws://localhost:9001`)
- `PFC_MCP_WORKSPACE_PATH` (optional)
- `PFC_MCP_REQUEST_TIMEOUT_S` (default: `10.0`)
- `PFC_MCP_MAX_RETRIES` (default: `2`)
- `PFC_MCP_AUTO_RECONNECT` (default: `true`)
- `PFC_MCP_DIAGNOSTIC_TIMEOUT_MS` (default: `30000`)

## Run

From this repository root:

```bash
uv run python -m pfc_mcp.server
```

Or via script entry point:

```bash
uv run pfc-mcp
```

## Test

```bash
uv run pytest pfc-mcp/tests/test_phase2_tools.py --no-cov
uv run pytest pfc-mcp/tests/test_phase3_capture_plot.py --no-cov
```
