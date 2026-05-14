"""
Execution-strategy router for execute_code snippets.

Decides between two paths based on bridge state:

* ``"queue"``    — main thread is idle; submit straight to
                   ``MainThreadExecutor``
* ``"callback"`` — main thread is busy with a tracked task; queue the
                   snippet for the PFC cycle-gap callback to drain

Both paths are MainThread-bound; this module only routes. Actual
snippet execution lives in ``execution.snippet.run_snippet``.
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
    code: str,
    request_id: str,
    output_buffer: StringIO,
    timeout: float,
    remaining_time_func,
) -> Tuple[Optional[Dict[str, Any]], bool]:
    """
    Submit snippet to ``MainThreadExecutor`` for direct execution.

    Returns:
        (result, success): result dict if completed, None otherwise.
    """
    from ..execution.snippet import run_snippet

    loop = asyncio.get_event_loop()

    future = ctx.main_executor.submit(run_snippet, code, output_buffer)

    try:
        result = await asyncio.wait_for(
            loop.run_in_executor(None, future.result, timeout),
            timeout=timeout + 0.1
        )
        return result, True
    except (asyncio.TimeoutError, concurrent.futures.TimeoutError):
        # Already running → wait out the rest of the total budget, not 2×timeout
        if not future.cancel():
            leftover = remaining_time_func()
            if leftover <= 0:
                return None, False
            try:
                result = await asyncio.wait_for(
                    loop.run_in_executor(None, future.result, leftover),
                    timeout=leftover + 0.1,
                )
                return result, True
            except (asyncio.TimeoutError, concurrent.futures.TimeoutError):
                pass
        return None, False


async def _execute_via_callback(
    code: str, request_id: str, timeout: float
) -> Tuple[Optional[Dict[str, Any]], bool]:
    """
    Queue snippet for PFC cycle-gap callback.

    Returns:
        (result, success): result dict if completed, None otherwise.
    """
    from ..signals import submit_snippet

    loop = asyncio.get_event_loop()
    future = submit_snippet(code, request_id)

    try:
        result = await asyncio.wait_for(
            loop.run_in_executor(None, future.result, timeout),
            timeout=timeout + 0.1
        )
        return result, True
    except (asyncio.TimeoutError, concurrent.futures.TimeoutError):
        return None, False


async def execute_snippet(
    ctx: ServerContext,
    code: str,
    request_id: str,
    output_buffer: StringIO,
    remaining_time_func,
    attempt: int = 0,
    max_attempts: int = 2,
) -> Tuple[Optional[Dict[str, Any]], str]:
    """
    Execute snippet, choosing path by bridge state.

    Each attempt:
    1. Check current state (``has_running_tasks``)
    2. Choose strategy based on state
    3. If timeout, recurse with ``attempt + 1`` (re-evaluates state)

    Args:
        remaining_time_func: Callable returning remaining time budget (s).
        attempt: Current attempt number (0-indexed).
        max_attempts: Maximum attempts before giving up.

    Returns:
        ``(result, execution_path)`` where ``execution_path`` is
        ``"queue"``, ``"callback"``, ``"timeout"``, or ``"max_attempts"``.
    """
    if attempt >= max_attempts:
        return None, "max_attempts"

    remaining = remaining_time_func()
    if remaining <= 0:
        return None, "timeout"

    has_running = ctx.task_manager.has_running_tasks()

    # Split remaining budget evenly across remaining attempts so the full
    # budget is used (attempt 0 of 2 → 50%, attempt 1 of 2 → 100% of what's left).
    # Floor at 0.5s so a single wait_for call doesn't get a near-zero timeout.
    attempts_left = max_attempts - attempt
    timeout = max(remaining / attempts_left, 0.5)

    if has_running:
        # Tasks running → try callback (queue is blocked)
        result, success = await _execute_via_callback(code, request_id, timeout)
        if success:
            return result, "callback"
    else:
        # No tasks → try queue (faster path)
        result, success = await _execute_via_queue(
            ctx, code, request_id, output_buffer, timeout, remaining_time_func,
        )
        if success:
            return result, "queue"

    # Strategy failed → recurse (state may have changed)
    return await execute_snippet(
        ctx=ctx,
        code=code,
        request_id=request_id,
        output_buffer=output_buffer,
        remaining_time_func=remaining_time_func,
        attempt=attempt + 1,
        max_attempts=max_attempts,
    )
