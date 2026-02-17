import asyncio

from pfc_mcp.formatting import build_bridge_error
from pfc_mcp.server import mcp
from pfc_mcp.tools.task_formatting import normalize_status, paginate_output
from pfc_mcp.utils import validate_script_path


def test_phase2_tools_registered() -> None:
    tools = asyncio.run(mcp._tool_manager.get_tools())
    expected = {
        "pfc_execute_task",
        "pfc_check_task_status",
        "pfc_list_tasks",
        "pfc_interrupt_task",
    }
    assert expected.issubset(set(tools.keys()))
    assert "pfc_execute_code" not in tools


def test_status_mapping_and_pagination() -> None:
    assert normalize_status("success") == "completed"
    assert normalize_status("error") == "failed"

    text, page = paginate_output(
        output="a\nb\nc\nd",
        skip_newest=0,
        limit=2,
        filter_text=None,
    )

    assert text == "c\nd"
    assert page["line_range"] == "3-4"
    assert page["has_older"] is True
    assert page["has_newer"] is False


def test_validate_script_path_requires_absolute() -> None:
    assert validate_script_path("/tmp/run.py") == "/tmp/run.py"

    try:
        validate_script_path("relative/run.py")
    except ValueError as exc:
        assert "absolute path" in str(exc)
    else:
        raise AssertionError("relative path should raise ValueError")


def test_bridge_error_message_is_friendly() -> None:
    err = OSError("Multiple exceptions: [Errno 61] Connect call failed")
    envelope = build_bridge_error(err)

    assert envelope["ok"] is False
    error = envelope["error"]
    assert error["code"] == "bridge_unavailable"
    assert error["message"] == "PFC bridge unavailable"
    assert error["details"]["reason"] == "cannot connect to bridge service"
    assert error["details"]["action"] == "start pfc-bridge in PFC GUI, then retry"
