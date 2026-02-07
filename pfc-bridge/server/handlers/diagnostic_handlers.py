"""
Diagnostic message handlers.

Handles diagnostic script execution for agent tools (e.g., pfc_capture_plot).
"""

import asyncio
import concurrent.futures
import logging
import os
from io import StringIO
from typing import Any, Callable, Dict, Optional, Tuple

from .context import ServerContext
from .helpers import require_field

logger = logging.getLogger("PFC-Server")


async def _wait_for_file(
    result: Dict[str, Any],
    timeout: float = 30.0,
    interval: float = 0.2
) -> Dict[str, Any]:
    """Wait for export file to exist, return updated result."""
    data = result.get("data")
    if not isinstance(data, dict):
        return result

    output_path = data.get("output_path")
    if not output_path:
        return result

    elapsed = 0.0
    while not os.path.exists(output_path) and elapsed < timeout:
        await asyncio.sleep(interval)
        elapsed += interval

    if not os.path.exists(output_path):
        return {
            **result,
            "status": "error",
            "message": "Export timeout: file not created after {}s".format(timeout)
        }

    return result


async def _execute_via_queue(
    ctx: ServerContext,
    script_path: str,
    script_content: str,
    output_buffer: StringIO,
    task_id: str,
    timeout: float
) -> Tuple[Optional[Dict[str, Any]], bool]:
    """
    Execute diagnostic via main thread queue.

    Returns:
        (result, success): result dict if success, None otherwise
    """
    loop = asyncio.get_event_loop()

    future = ctx.main_executor.submit(
        ctx.script_runner._execute,
        script_path,
        script_content,
        output_buffer,
        task_id
    )

    try:
        result = await asyncio.wait_for(
            loop.run_in_executor(None, future.result, timeout),
            timeout=timeout + 0.1
        )
        return result, True
    except (asyncio.TimeoutError, concurrent.futures.TimeoutError):
        # Try to cancel; if failed, task already started - wait for it
        if not future.cancel():
            try:
                result = await asyncio.wait_for(
                    loop.run_in_executor(None, future.result, timeout * 2),
                    timeout=timeout * 2 + 0.1
                )
                return result, True
            except (asyncio.TimeoutError, concurrent.futures.TimeoutError):
                pass
        return None, False


async def _execute_via_callback(script_path: str, timeout: float) -> Tuple[Optional[Dict[str, Any]], bool]:
    """
    Execute diagnostic via cycle callback.

    Returns:
        (result, success): result dict if success, None otherwise
    """
    from ..signals import submit_diagnostic, is_diagnostic_callback_registered

    if not is_diagnostic_callback_registered():
        return None, False

    loop = asyncio.get_event_loop()
    future = submit_diagnostic(script_path)

    try:
        result = await asyncio.wait_for(
            loop.run_in_executor(None, future.result, timeout),
            timeout=timeout + 0.1
        )
        return result, True
    except (asyncio.TimeoutError, concurrent.futures.TimeoutError):
        return None, False


async def _execute_diagnostic(
    ctx: ServerContext,
    script_path: str,
    script_content: str,
    output_buffer: StringIO,
    task_id: str,
    remaining_time_func,
    attempt: int = 0,
    max_attempts: int = 2
) -> Tuple[Optional[Dict[str, Any]], str]:
    """
    Execute diagnostic script with recursive strategy switching.

    Each attempt:
    1. Check current state (has_running_tasks)
    2. Choose strategy based on state
    3. If timeout, recurse with attempt + 1 (re-evaluates state)

    Args:
        remaining_time_func: Function returning remaining time budget
        attempt: Current attempt number (0-indexed)
        max_attempts: Maximum attempts before giving up

    Returns:
        (result, execution_path) or (None, "timeout")
    """
    # Base case: exhausted attempts or time
    if attempt >= max_attempts:
        return None, "max_attempts"

    remaining = remaining_time_func()
    if remaining < 0.5:
        return None, "timeout"

    # Dynamic strategy selection based on current state
    has_running = ctx.task_manager.has_running_tasks()
    timeout = remaining * 0.4  # Use 40% of remaining time per attempt

    if has_running:
        # Tasks running → try callback (queue is blocked)
        result, success = await _execute_via_callback(script_path, timeout)
        if success:
            return result, "callback"
    else:
        # No tasks → try queue (faster path)
        result, success = await _execute_via_queue(
            ctx, script_path, script_content, output_buffer, task_id, timeout
        )
        if success:
            return result, "queue"

    # Strategy failed → recurse (state may have changed)
    return await _execute_diagnostic(
        ctx=ctx,
        script_path=script_path,
        script_content=script_content,
        output_buffer=output_buffer,
        task_id=task_id,
        remaining_time_func=remaining_time_func,
        attempt=attempt + 1,
        max_attempts=max_attempts
    )


async def handle_diagnostic_execute(ctx, data):
    # type: (ServerContext, Dict[str, Any]) -> Dict[str, Any]
    """
    Handle diagnostic_execute message.

    Strategy selection based on task state:
    - Tasks running: callback first, then queue
    - No tasks: queue first, then callback
    """
    import time as time_module
    import uuid

    request_id = data.get("request_id", "unknown")

    script_path, err = require_field(data, "script_path", request_id, "diagnostic_result")
    if err:
        return err

    timeout_ms = data.get("timeout_ms", 30000)
    start_time = time_module.time()
    total_timeout = timeout_ms / 1000.0

    def remaining():
        return max(total_timeout - (time_module.time() - start_time), 0.5)

    try:
        with open(script_path, 'r', encoding='utf-8') as f:
            script_content = f.read()

        task_id = uuid.uuid4().hex[:8]
        output_buffer = StringIO()

        # Execute with recursive strategy switching
        result, path = await _execute_diagnostic(
            ctx=ctx,
            script_path=script_path,
            script_content=script_content,
            output_buffer=output_buffer,
            task_id=task_id,
            remaining_time_func=remaining,
            attempt=0,
            max_attempts=2
        )

        if result is not None:
            result = await _wait_for_file(result, timeout=remaining())
            return {
                "type": "diagnostic_result",
                "request_id": request_id,
                "execution_path": path,
                **result
            }

        return {
            "type": "diagnostic_result",
            "request_id": request_id,
            "status": "timeout",
            "message": "Diagnostic timed out after {}ms".format(timeout_ms),
            "data": None
        }

    except Exception as e:
        logger.error("Diagnostic execution failed: {}".format(e))
        return {
            "type": "diagnostic_result",
            "request_id": request_id,
            "status": "error",
            "message": str(e),
            "data": None
        }
