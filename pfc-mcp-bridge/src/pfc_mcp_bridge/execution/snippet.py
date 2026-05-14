"""
Snippet executor for pfc_execute_code.

Both execute_code paths — the idle MainThreadExecutor queue path and the
busy cycle-gap callback path — funnel through ``run_snippet`` so the
caller sees identical behaviour regardless of which scheduler delivers
the code to PFC's main thread.

Distinct from ``execution.script.ScriptRunner``, which serves tracked
pfc_task scripts (file-backed, registered with TaskManager).

Python 3.6 compatible implementation.
"""

import logging
import os
import sys
import traceback
from typing import Any, Dict

from ..utils import TeeBuffer, capture_pfc_console

logger = logging.getLogger("PFC-Server")

# Synthetic filename used for compile()/traceback so error frames render
# as ``<execute_code>`` instead of an internal temp path.
SNIPPET_LABEL = "<execute_code>"


def run_snippet(code, output_buffer):
    # type: (str, Any) -> Dict[str, Any]
    """
    Compile and execute ``code`` against the PFC ``__main__`` namespace.

    Captures stdout (both Python ``print`` and PFC console output) into
    ``output_buffer``. Always returns a result dict; never raises for
    user-code errors (they become ``status="error"`` entries).

    Args:
        code: Python source. Tried as an expression first; falls back to
            ``exec`` on SyntaxError, in which case a top-level ``result``
            variable is picked up as the return value.
        output_buffer: A stream-like buffer (StringIO or FileBuffer).
            ``run_snippet`` writes captured output into it and also
            reads its contents to populate the response.

    Returns:
        Dict with ``status`` (``"success"`` / ``"error"``), ``message``,
        ``output``, and ``result``.
    """
    old_stdout = sys.stdout
    terminal = sys.__stdout__ if sys.__stdout__ is not None else old_stdout
    sys.stdout = TeeBuffer(terminal, output_buffer)

    try:
        import __main__

        exec_globals = __main__.__dict__
        # Don't let a prior snippet's `result` leak into this one.
        exec_globals.pop("result", None)

        cmdlog_dir = os.path.join(".pfc-mcp", "logs")
        with capture_pfc_console(sys.stdout, cmdlog_dir):
            try:
                code_obj = compile(code, SNIPPET_LABEL, "eval")
                result = eval(code_obj, exec_globals, exec_globals)
            except SyntaxError:
                code_obj = compile(code, SNIPPET_LABEL, "exec")
                exec(code_obj, exec_globals, exec_globals)
                result = exec_globals.get("result", None)

        return {
            "status": "success",
            "message": "Code executed successfully",
            "output": output_buffer.getvalue(),
            "result": _serialize(result),
        }

    except BaseException as e:
        output_text = output_buffer.getvalue()
        logger.error("Snippet execution failed:\n%s", traceback.format_exc())

        # Filter traceback to user frames only (filename == SNIPPET_LABEL)
        # so internal bridge frames don't leak into the user response.
        tb = sys.exc_info()[2]
        user_frames = []
        while tb is not None:
            filename = tb.tb_frame.f_code.co_filename
            if filename == SNIPPET_LABEL:
                user_frames.append(
                    (filename, tb.tb_lineno, tb.tb_frame.f_code.co_name)
                )
            tb = tb.tb_next

        if user_frames:
            parts = ["Code execution failed:\n"]
            for filename, lineno, name in user_frames:
                parts.append(
                    '  File "{}", line {}, in {}\n'.format(filename, lineno, name)
                )
            parts.append("{}: {}".format(type(e).__name__, str(e)))
            error_message = "".join(parts)
        else:
            error_message = "Code execution failed: {}: {}".format(
                type(e).__name__, str(e)
            )

        return {
            "status": "error",
            "message": error_message,
            "output": output_text,
            "result": None,
        }
    finally:
        sys.stdout = old_stdout


def _serialize(result):
    # type: (Any) -> Any
    """Convert PFC SDK objects into JSON-serialisable values."""
    if result is None or isinstance(result, (str, int, float, bool)):
        return result
    if isinstance(result, (list, tuple)):
        return [_serialize(item) for item in result]
    if isinstance(result, dict):
        return {k: _serialize(v) for k, v in result.items()}
    return str(result)
