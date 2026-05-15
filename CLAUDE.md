# CLAUDE.md

Guidance for coding agents working in the `pfc-mcp` repository.

## Project Overview

`pfc-mcp` provides an MCP server for ITASCA PFC workflows plus a bridge runtime that runs inside PFC GUI.

This repository intentionally has two runtime contexts:

- `src/pfc_mcp/` (Python >= 3.10): MCP server package used by clients/tooling
- `pfc-mcp-bridge/` (PFC embedded Python, often 3.6): WebSocket bridge running inside PFC GUI

Treat these as separate deployment targets even though they live in one repository.

## Core Architecture

### MCP side (`src/pfc_mcp`)

- Exposes documentation tools and execution tools through FastMCP
- Communicates with bridge via WebSocket client (`pfc_mcp.bridge.client`)
- Returns a unified tool envelope: `ok`, `data`, `error`
- Dual execution model: synchronous REPL (`pfc_execute_code`) for quick queries, script-first async (`pfc_execute_task` + `pfc_check_task_status`) for long-running simulations

### Bridge side (`pfc-mcp-bridge`)

- Runs in PFC GUI process
- Owns thread-safe interaction with ITASCA SDK
- Handles long-running tasks and diagnostics
- Must be started from PFC GUI (for example with `%run .../pfc-mcp-bridge/start_bridge.py`)

## Repository Layout

```text
pfc-mcp/
├── src/pfc_mcp/
│   ├── bridge/          # MCP-side bridge client/task manager
│   ├── knowledge/       # command/API/reference search system
│   ├── tools/           # MCP tool implementations
│   ├── formatting.py    # shared response formatting
│   └── server.py        # MCP server entrypoint
├── pfc-mcp-bridge/      # runtime executed inside PFC GUI
└── tests/               # MCP/tool contract tests
```

## Development Commands

Run from repository root.

```bash
uv sync
uv sync --group dev
uv run pfc-mcp
uv run pytest tests/test_phase2_tools.py
uv run pytest tests/test_tool_contracts.py
```

## Engineering Rules

1. Keep MCP and bridge concerns separate.
   - Do not couple MCP logic to PFC GUI internals.
   - Do not introduce application/session policy into bridge runtime.

2. Preserve execution semantics for each model.
   - `pfc_execute_code` runs synchronous snippets and returns stdout/result immediately.
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
Mock bridge based tests are preferred for deterministic CI.

## Documentation Sources

PFC searchable docs live under:

- `src/pfc_mcp/knowledge/resources/command_docs/`
- `src/pfc_mcp/knowledge/resources/python_sdk_docs/`
- `src/pfc_mcp/knowledge/resources/references/`

When changing schema/content shape, verify browse/query tool behavior remains consistent.

## Release Process

Both packages are published to PyPI via GitHub Actions, triggered by pushing Git tags.

| Package | Tag pattern | Workflow | Version file | PyPI environment |
|---------|-------------|----------|--------------|------------------|
| `pfc-mcp` | `v*` (e.g. `v0.3.5`) | `.github/workflows/publish.yml` | `pyproject.toml` | `pypi` |
| `pfc-mcp-bridge` | `bridge-v*` (e.g. `bridge-v0.2.3`) | `.github/workflows/publish-bridge.yml` | `pfc-mcp-bridge/src/pfc_mcp_bridge/__init__.py` | `pypi-bridge` |

Steps to release:

1. Bump `__version__` in the corresponding `__init__.py` (both packages use hatch dynamic versioning, so `__init__.py` is the single source of truth).
2. In `CHANGELOG.md`, rename `## [Unreleased]` to `## [x.y.z] - YYYY-MM-DD` and start a fresh empty `## [Unreleased]`. The `pfc-mcp` publish workflow extracts the section whose header matches the tag version exactly and fails if it is missing.
3. Commit and push to `main`.
4. Tag the commit: `git tag v0.x.x` or `git tag bridge-v0.x.x`.
5. Push the tag: `git push origin <tag>`.

The `pfc-mcp` publish workflow runs tests before publishing; the bridge workflow publishes directly.

**Important**: the tag version and the `__version__` in `__init__.py` must match. PyPI rejects uploads for versions that already exist.

CI also runs on every push/PR to `main` (`.github/workflows/test.yml`): ruff check, ruff format, mypy, and pytest with coverage.

## Commit Style

Use conventional prefixes seen in repository history, for example:

- `feat: ...`
- `fix: ...`
- `refactor: ...`
- `test: ...`
- `docs: ...`

Keep commit messages focused on why the change was needed.

Documentation is first-class for this project -- agents rely on the docs and
the agentic install guides to understand and operate pfc-mcp. Any notable
change to behaviour, tools, or user/agent-facing documentation or install
flow must add a `## [Unreleased]` entry in `CHANGELOG.md` in the same commit
(see the convention comment at the top of that file). Trivial doc fixes
(typos, formatting) and internal-only refactors/tests/CI are exempt.
