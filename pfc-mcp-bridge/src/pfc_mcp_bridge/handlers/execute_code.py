"""
Execute code message handler.

Handles synchronous code snippet execution for ``pfc_execute_code``.
Routes through the queue/callback strategy in
``handlers.exec_strategy.execute_snippet``.
"""

import logging
import time as time_module
from io import StringIO
from typing import Any, Dict

from .context import ServerContext
from .exec_strategy import execute_snippet
from .helpers import require_field
from ..utils.response import _truncate_output

logger = logging.getLogger("PFC-Server")


async def handle_execute_code(ctx, data):
    # type: (ServerContext, Dict[str, Any]) -> Dict[str, Any]
    """
    Handle ``execute_code`` message.

    Runs a code snippet synchronously in the PFC main thread and returns
    captured stdout plus any ``result`` value. Path selection (queue vs
    callback) is handled by ``execute_snippet``.
    """
    request_id = data.get("request_id", "unknown")

    code, err = require_field(data, "code", request_id, "execute_code_result")
    if err:
        return err

    timeout_ms = data.get("timeout_ms", 10000)
    start_time = time_module.time()
    total_timeout = timeout_ms / 1000.0

    def remaining():
        return total_timeout - (time_module.time() - start_time)

    try:
        output_buffer = StringIO()

        result, path = await execute_snippet(
            ctx=ctx,
            code=code,
            request_id=request_id,
            output_buffer=output_buffer,
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
                    "output": _truncate_output(result.get("output", "")),
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
