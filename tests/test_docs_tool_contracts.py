"""Contract tests for documentation tool response structures."""

import json

import pytest

from pfc_mcp.server import mcp


def _parse_tool_payload(result) -> dict:
    assert result is not None
    assert len(result.content) > 0
    text = result.content[0].text
    assert text.startswith("{")
    return json.loads(text)


@pytest.mark.asyncio
async def test_browse_commands_root_contract() -> None:
    result = await mcp._tool_manager.call_tool("pfc_browse_commands", {})
    payload = _parse_tool_payload(result)
    data = payload["data"]

    assert payload["ok"] is True
    assert payload.get("error") is None
    assert data["source"] == "commands"
    assert data["action"] == "browse"
    assert isinstance(data["entries"], list)
    assert data["summary"]["count"] >= 1
    assert data["summary"]["total_commands"] >= 1


@pytest.mark.asyncio
async def test_browse_commands_not_found_contract() -> None:
    result = await mcp._tool_manager.call_tool(
        "pfc_browse_commands",
        {"command": "ball not_a_real_command"},
    )
    payload = _parse_tool_payload(result)

    assert payload["ok"] is False
    assert payload["error"]["code"] == "command_not_found"
    details = payload["error"].get("details") or {}
    assert details["source"] == "commands"
    assert details["input"]["category"] == "ball"
    assert details["input"]["command"] == "not_a_real_command"
    assert isinstance(details.get("available_commands"), list)


@pytest.mark.asyncio
async def test_query_command_contract() -> None:
    result = await mcp._tool_manager.call_tool(
        "pfc_query_command",
        {"query": "ball create", "limit": 5},
    )
    payload = _parse_tool_payload(result)
    data = payload["data"]

    assert payload["ok"] is True
    assert data["source"] == "commands"
    assert data["action"] == "query"
    assert data["summary"]["count"] >= 1
    assert isinstance(data["entries"], list)
    assert len(data["entries"]) >= 1


@pytest.mark.asyncio
async def test_browse_python_api_root_contract() -> None:
    result = await mcp._tool_manager.call_tool("pfc_browse_python_api", {})
    payload = _parse_tool_payload(result)
    data = payload["data"]

    assert payload["ok"] is True
    assert data["source"] == "python_api"
    assert data["action"] == "browse"
    assert isinstance(data["entries"], list)
    assert data["summary"]["total_modules"] >= 1
    assert data["summary"]["total_objects"] >= 1


@pytest.mark.asyncio
async def test_query_python_api_no_results_contract() -> None:
    result = await mcp._tool_manager.call_tool(
        "pfc_query_python_api",
        {"query": "definitelynonexistentkeyword", "limit": 5},
    )
    payload = _parse_tool_payload(result)
    data = payload["data"]

    assert payload["ok"] is True
    assert data["source"] == "python_api"
    assert data["action"] == "query"
    assert data["summary"]["count"] == 0
    assert data["entries"] == []


@pytest.mark.asyncio
async def test_browse_reference_root_contract() -> None:
    result = await mcp._tool_manager.call_tool("pfc_browse_reference", {})
    payload = _parse_tool_payload(result)
    data = payload["data"]

    assert payload["ok"] is True
    assert data["source"] == "reference"
    assert data["action"] == "browse"
    assert data["summary"]["count"] >= 1
    assert isinstance(data["entries"], list)
