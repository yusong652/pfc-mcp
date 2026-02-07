import asyncio

from pfc_mcp.server import mcp
from pfc_mcp.tools.task_formatting import normalize_status, paginate_output
from pfc_mcp.utils import validate_script_path


def test_phase2_tools_registered() -> None:
    tools = asyncio.run(mcp._tool_manager.get_tools())
    expected = {
        "pfc_execute_task",
        "pfc_execute_code",
        "pfc_check_task_status",
        "pfc_list_tasks",
        "pfc_interrupt_task",
    }
    assert expected.issubset(set(tools.keys()))


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
