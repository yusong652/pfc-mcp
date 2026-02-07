import asyncio
import base64
import json
import os
import re
from pathlib import Path

import pytest
import websockets
from mcp.types import ImageContent

from pfc_mcp.bridge.client import close_bridge_client
from pfc_mcp.scripts.plot_capture import DEFAULT_IMAGE_SIZE, generate_plot_capture_script, normalize_ball_color_by
from pfc_mcp.server import mcp


_PNG_1X1_BASE64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGNgYAAAAAMAASsJTYQAAAAASUVORK5CYII="
)


def test_generate_plot_script_has_export_command() -> None:
    script = generate_plot_capture_script(
        output_path="/tmp/capture.png",
        plot_name="NagisaDiag",
        size=DEFAULT_IMAGE_SIZE,
        view_settings=None,
        include_ball=True,
        include_wall=True,
        include_contact=False,
        include_axes=True,
        wall_transparency=70,
        ball_shape="sphere",
        ball_color_by=normalize_ball_color_by("force_contact"),
        ball_color_by_quantity="mag",
        wall_color_by=None,
        wall_color_by_quantity="mag",
        contact_color_by="force",
        contact_color_by_quantity="mag",
        contact_scale_by_force=True,
        ball_cut=None,
        wall_cut=None,
        contact_cut=None,
    )
    assert 'plot item create ball active on' in script
    assert 'plot "{plot_name}" export bitmap' in script


@pytest.mark.asyncio
async def test_capture_plot_end_to_end_with_mock_bridge(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)

    async def _handler(websocket):
        async for raw in websocket:
            req = json.loads(raw)
            req_id = req.get("request_id", "unknown")

            if req.get("type") == "get_working_directory":
                resp = {
                    "type": "result",
                    "request_id": req_id,
                    "status": "success",
                    "message": "ok",
                    "data": {"working_directory": str(workspace)},
                }
            elif req.get("type") == "diagnostic_execute":
                script_path = Path(req["script_path"])
                script_text = script_path.read_text(encoding="utf-8")
                match = re.search(r'output_path = r"(.+?)"', script_text)
                assert match is not None
                out_path = Path(match.group(1))
                out_path.parent.mkdir(parents=True, exist_ok=True)
                out_path.write_bytes(base64.b64decode(_PNG_1X1_BASE64))

                resp = {
                    "type": "diagnostic_result",
                    "request_id": req_id,
                    "status": "success",
                    "message": "diagnostic complete",
                    "data": {"output_path": str(out_path)},
                }
            else:
                resp = {
                    "type": "result",
                    "request_id": req_id,
                    "status": "error",
                    "message": f"unsupported: {req.get('type')}",
                    "data": None,
                }

            await websocket.send(json.dumps(resp))

    server = await websockets.serve(_handler, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]

    env_keys = [
        "PFC_MCP_BRIDGE_URL",
        "PFC_MCP_WORKSPACE_PATH",
        "PFC_MCP_DIAGNOSTIC_FILE_WAIT_S",
    ]
    prev = {k: os.environ.get(k) for k in env_keys}

    os.environ["PFC_MCP_BRIDGE_URL"] = f"ws://127.0.0.1:{port}"
    os.environ["PFC_MCP_WORKSPACE_PATH"] = str(workspace)
    os.environ["PFC_MCP_DIAGNOSTIC_FILE_WAIT_S"] = "1.0"

    await close_bridge_client()

    try:
        output_path = tmp_path / "captures" / "phase3.png"
        result = await mcp._tool_manager.call_tool(
            "pfc_capture_plot",
            {
                "output_path": str(output_path),
                "include_contact": False,
            },
        )

        assert output_path.exists()
        assert any(isinstance(item, ImageContent) for item in result.content)
    finally:
        await close_bridge_client()
        for key, value in prev.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        server.close()
        await server.wait_closed()
