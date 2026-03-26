"""
Script execution strategies.

Provides queue-based and callback-based execution strategies for running
scripts in the PFC main thread. Used by the execute_code handler.
"""

import asyncio
import concurrent.futures
import logging
from io import StringIO
from typing import Any, Dict, Optional, Tuple

from .context import ServerContext

logger = logging.getLogger("PFC-Server")


async def _execute_via_queue(
    ctx: ServerContext,
    script_path: str,
    script_content: str,
    output_buffer: StringIO,
    task_id: str,
    timeout: float
) -> Tuple[Optional[Dict[str, Any]], bool]:
    """
    Execute script via main thread queue.

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
    Execute script via cycle callback.

    Returns:
        (result, success): result dict if success, None otherwise
    """
    from ..signals import submit_script, is_executor_callback_registered

    if not is_executor_callback_registered():
        return None, False

    loop = asyncio.get_event_loop()
    future = submit_script(script_path)

    try:
        result = await asyncio.wait_for(
            loop.run_in_executor(None, future.result, timeout),
            timeout=timeout + 0.1
        )
        return result, True
    except (asyncio.TimeoutError, concurrent.futures.TimeoutError):
        return None, False


async def execute_script(
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
    Execute script with recursive strategy switching.

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
    return await execute_script(
        ctx=ctx,
        script_path=script_path,
        script_content=script_content,
        output_buffer=output_buffer,
        task_id=task_id,
        remaining_time_func=remaining_time_func,
        attempt=attempt + 1,
        max_attempts=max_attempts
    )
