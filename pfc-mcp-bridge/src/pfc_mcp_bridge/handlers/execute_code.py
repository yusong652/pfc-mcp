"""
Execute code message handler.

Handles synchronous code snippet execution for pfc_execute_code tool.
Uses the script executor strategy (queue/callback switching).
"""

import asyncio
import logging
import os
import time
import uuid
from io import StringIO
from typing import Any, Dict, Tuple

from .context import ServerContext
from .script_executor import execute_script
from .helpers import require_field

logger = logging.getLogger("PFC-Server")


def _write_temp_script(working_dir, code):
    # type: (str, str) -> str
    """Write code snippet to a temp file and return the path."""
    exec_dir = os.path.join(working_dir, ".pfc-mcp-bridge", "execute_code")
    if not os.path.exists(exec_dir):
        os.makedirs(exec_dir)
    filename = "exec_{}.py".format(uuid.uuid4().hex[:8])
    path = os.path.join(exec_dir, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(code)
    return path


def _cleanup_temp_script(path):
    # type: (str) -> None
    """Remove temp script file."""
    try:
        os.remove(path)
    except Exception:
        pass


async def handle_execute_code(ctx, data):
    # type: (ServerContext, Dict[str, Any]) -> Dict[str, Any]
    """
    Handle execute_code message.

    Executes a code snippet synchronously and returns stdout.
    Uses the queue/callback script executor strategy.
    """
    import time as time_module

    request_id = data.get("request_id", "unknown")

    code, err = require_field(data, "code", request_id, "execute_code_result")
    if err:
        return err

    timeout_ms = data.get("timeout_ms", 10000)
    start_time = time_module.time()
    total_timeout = timeout_ms / 1000.0

    def remaining():
        return max(total_timeout - (time_module.time() - start_time), 0.5)

    script_path = None
    try:
        # Write code to temp file
        working_dir = os.getcwd()
        script_path = _write_temp_script(working_dir, code)

        task_id = uuid.uuid4().hex[:8]
        output_buffer = StringIO()

        # Execute with queue/callback strategy switching
        result, path = await execute_script(
            ctx=ctx,
            script_path=script_path,
            script_content=code,
            output_buffer=output_buffer,
            task_id=task_id,
            remaining_time_func=remaining,
            attempt=0,
            max_attempts=2,
        )

        if result is not None:
            return {
                "type": "execute_code_result",
                "request_id": request_id,
                "execution_path": path,
                "status": result.get("status", "unknown"),
                "message": result.get("message", ""),
                "data": {
                    "output": result.get("output", ""),
                    "result": result.get("result"),
                },
            }

        return {
            "type": "execute_code_result",
            "request_id": request_id,
            "status": "timeout",
            "message": "Execution timed out after {}ms".format(timeout_ms),
            "error": {
                "code": "timeout",
                "message": "Execution timed out after {}ms".format(timeout_ms),
            },
            "data": None,
        }

    except Exception as e:
        logger.error("Code execution failed: {}".format(e))
        return {
            "type": "execute_code_result",
            "request_id": request_id,
            "status": "error",
            "message": str(e),
            "error": {
                "code": "execute_code_failed",
                "message": str(e),
            },
            "data": None,
        }

    finally:
        if script_path:
            _cleanup_temp_script(script_path)
