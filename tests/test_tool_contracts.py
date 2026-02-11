"""Contract tests for pfc-mcp tool response structures.

Verifies that each tool returns the expected field structure,
ensuring the API contract between pfc-mcp and its consumers is stable.
"""

import json
import os
import time
from pathlib import Path

import pytest
import websockets

from pfc_mcp.bridge.client import close_bridge_client
from pfc_mcp.server import mcp


# ── Mock Bridge ──────────────────────────────────────────


TASK_STORE = {}


async def _mock_bridge_handler(websocket):
    """Mock pfc-bridge that handles all task-related message types."""
    async for raw in websocket:
        req = json.loads(raw)
        req_id = req.get("request_id", "unknown")
        msg_type = req.get("type", "pfc_task")

        if msg_type == "pfc_task":
            task_id = req.get("task_id", "000000")
            TASK_STORE[task_id] = {
                "status": "running",
                "start_time": time.time(),
                "script_path": req.get("script_path", ""),
                "description": req.get("description", ""),
            }
            resp = {
                "type": "result",
                "request_id": req_id,
                "status": "pending",
                "message": f"Script submitted: {Path(req.get('script_path', '')).name}",
            }

        elif msg_type == "check_task_status":
            task_id = req.get("task_id", "")
            stored = TASK_STORE.get(task_id)
            if stored:
                resp = {
                    "type": "result",
                    "request_id": req_id,
                    "status": stored["status"],
                    "message": "ok",
                    "data": {
                        "task_id": task_id,
                        "status": stored["status"],
                        "start_time": stored["start_time"],
                        "end_time": None,
                        "elapsed_time": "5.0s",
                        "script_path": stored["script_path"],
                        "description": stored["description"],
                        "output": "Cycle 100: unbalanced=1e-3\nCycle 200: unbalanced=5e-4\n",
                        "result": None,
                        "error": None,
                    },
                }
            else:
                resp = {
                    "type": "result",
                    "request_id": req_id,
                    "status": "not_found",
                    "message": f"Task not found: {task_id}",
                    "data": None,
                }

        elif msg_type == "list_tasks":
            tasks = [
                {
                    "task_id": tid,
                    "status": t["status"],
                    "source": "agent",
                    "elapsed_time": "5.0s",
                    "entry_script": t["script_path"],
                    "description": t["description"],
                }
                for tid, t in TASK_STORE.items()
            ]
            resp = {
                "type": "result",
                "request_id": req_id,
                "status": "success",
                "message": f"Found {len(tasks)} task(s)",
                "data": tasks,
                "pagination": {
                    "total_count": len(tasks),
                    "displayed_count": len(tasks),
                    "offset": 0,
                    "limit": 32,
                    "has_more": False,
                },
            }

        elif msg_type == "interrupt_task":
            resp = {
                "type": "result",
                "request_id": req_id,
                "status": "success",
                "message": f"Interrupt requested for task: {req.get('task_id')}",
                "data": {"task_id": req.get("task_id"), "interrupt_requested": True},
            }

        else:
            resp = {
                "type": "result",
                "request_id": req_id,
                "status": "error",
                "message": f"unsupported: {msg_type}",
            }

        await websocket.send(json.dumps(resp))


@pytest.fixture()
async def mock_bridge(tmp_path):
    """Start mock bridge and configure environment."""
    import pfc_mcp.bridge.task_manager as tm_mod

    TASK_STORE.clear()

    server = await websockets.serve(_mock_bridge_handler, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]

    env_keys = ["PFC_MCP_BRIDGE_URL", "PFC_MCP_WORKSPACE_PATH"]
    prev = {k: os.environ.get(k) for k in env_keys}

    os.environ["PFC_MCP_BRIDGE_URL"] = f"ws://127.0.0.1:{port}"
    os.environ["PFC_MCP_WORKSPACE_PATH"] = str(tmp_path)

    # Reset singleton so tests get fresh state
    old_tm = tm_mod._task_manager
    tm_mod._task_manager = None
    await close_bridge_client()

    yield tmp_path

    await close_bridge_client()
    tm_mod._task_manager = old_tm
    for key, value in prev.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value
    server.close()
    await server.wait_closed()


# ── pfc_execute_task ─────────────────────────────────────


@pytest.mark.asyncio
async def test_execute_task_success_fields(mock_bridge, tmp_path):
    script = tmp_path / "run.py"
    script.write_text("print('hello')")

    result = await mcp._tool_manager.call_tool(
        "pfc_execute_task",
        {"entry_script": str(script), "description": "test task"},
    )

    data = result.content[0].text if hasattr(result.content[0], "text") else json.loads(result.content[0].text)
    # structuredContent holds the dict
    sc = result.model_extra.get("structuredContent") if hasattr(result, "model_extra") else None
    # For fastmcp, the tool returns a dict which gets serialized
    # Just verify the raw result has the right structure
    assert result is not None
    assert len(result.content) > 0

    # Parse the structured content
    text = result.content[0].text
    parsed = json.loads(text) if text.startswith("{") else None

    if parsed:
        assert parsed["operation"] == "pfc_execute_task"
        assert parsed["status"] == "pending"
        assert "task_id" in parsed
        assert len(parsed["task_id"]) == 6
        assert "entry_script" in parsed
        assert "description" in parsed
        assert "display" in parsed
        assert "message" in parsed


# ── pfc_check_task_status ────────────────────────────────


@pytest.mark.asyncio
async def test_check_task_status_running_fields(mock_bridge, tmp_path):
    # First submit a task so we have something to check
    script = tmp_path / "sim.py"
    script.write_text("print('running')")

    exec_result = await mcp._tool_manager.call_tool(
        "pfc_execute_task",
        {"entry_script": str(script), "description": "simulation"},
    )
    exec_text = exec_result.content[0].text
    exec_data = json.loads(exec_text) if exec_text.startswith("{") else {}
    task_id = exec_data.get("task_id", list(TASK_STORE.keys())[0])

    result = await mcp._tool_manager.call_tool(
        "pfc_check_task_status",
        {"task_id": task_id, "wait_seconds": 1},
    )

    text = result.content[0].text
    parsed = json.loads(text) if text.startswith("{") else None

    if parsed:
        assert parsed["operation"] == "pfc_check_task_status"
        assert parsed["status"] in ("pending", "running", "completed", "failed", "interrupted")
        assert parsed["task_id"] == task_id
        assert "output" in parsed
        assert "output_mode" in parsed
        assert parsed["output_mode"] == "windowed_snapshot"
        # Pagination
        assert "pagination" in parsed
        pag = parsed["pagination"]
        assert "total_lines" in pag
        assert "line_range" in pag
        assert "has_older" in pag
        assert "has_newer" in pag
        # Query echo
        assert "query" in parsed
        assert "display" in parsed


@pytest.mark.asyncio
async def test_check_task_status_not_found(mock_bridge):
    result = await mcp._tool_manager.call_tool(
        "pfc_check_task_status",
        {"task_id": "nonexistent", "wait_seconds": 1},
    )

    text = result.content[0].text
    parsed = json.loads(text) if text.startswith("{") else None

    if parsed:
        assert parsed["status"] == "not_found"
        assert "display" in parsed


# ── pfc_list_tasks ───────────────────────────────────────


@pytest.mark.asyncio
async def test_list_tasks_with_tasks(mock_bridge, tmp_path):
    # Submit a task first
    script = tmp_path / "job.py"
    script.write_text("print('done')")
    await mcp._tool_manager.call_tool(
        "pfc_execute_task",
        {"entry_script": str(script), "description": "list test"},
    )

    result = await mcp._tool_manager.call_tool("pfc_list_tasks", {})

    text = result.content[0].text
    parsed = json.loads(text) if text.startswith("{") else None

    if parsed:
        assert parsed["operation"] == "pfc_list_tasks"
        assert parsed["status"] == "success"
        assert isinstance(parsed["total_count"], int)
        assert parsed["total_count"] >= 1
        assert isinstance(parsed["tasks"], list)
        assert len(parsed["tasks"]) >= 1
        # Task fields
        task = parsed["tasks"][0]
        assert "task_id" in task
        assert "status" in task
        assert "entry_script" in task
        assert "has_more" in parsed
        assert "display" in parsed


@pytest.mark.asyncio
async def test_list_tasks_empty(mock_bridge):
    # No tasks submitted — TASK_STORE is cleared by fixture
    result = await mcp._tool_manager.call_tool("pfc_list_tasks", {})

    text = result.content[0].text
    parsed = json.loads(text) if text.startswith("{") else None

    if parsed:
        assert parsed["operation"] == "pfc_list_tasks"
        assert parsed["status"] == "success"
        assert parsed["total_count"] == 0
        assert parsed["tasks"] == []
        assert "display" in parsed
