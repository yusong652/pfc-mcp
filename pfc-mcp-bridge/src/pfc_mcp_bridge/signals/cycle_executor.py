"""
Cycle-gap executor for execute_code snippets.

When PFC's main thread is busy running a tracked task (its main
``task_queue`` is blocked by a long script), short execute_code
snippets still need to land. This module registers a PFC callback that
fires at cycle boundaries and drains a pending-snippet queue, letting
execute_code requests slip through gaps in the running task.

Only used while a task occupies the queue; idle execute_code goes
through ``MainThreadExecutor`` directly.

Architecture:
- WebSocket thread: calls ``submit_snippet(code, request_id)`` -> queued
- PFC callback:     ``_pfc_executor_callback()`` batch-executes pending
- Results returned via ``Future`` objects

Python 3.6 compatible implementation.
"""

import logging
from concurrent.futures import Future
from io import StringIO
from typing import Any, Tuple

# Python 3.6 compatible queue import
try:
    from queue import Queue, Empty
except ImportError:
    from Queue import Queue, Empty  # type: ignore

# Module logger
logger = logging.getLogger("PFC-Server")


# =============================================================================
# Global State (Queue for pending snippet requests)
# =============================================================================

# Queue of pending snippets: (code, request_id, future) tuples
_pending_queue = Queue()  # type: Queue[Tuple[str, str, Future]]

# Maximum snippets to execute per callback (safety limit)
MAX_BATCH_SIZE = 10


# =============================================================================
# External Interface (Called from WebSocket thread)
# =============================================================================

def submit_snippet(code, request_id):
    # type: (str, str) -> Future
    """
    Queue a code snippet for execution at the next PFC cycle gap.

    Called from the WebSocket handler thread when the main task queue is
    blocked by a running task. The snippet is queued; the PFC callback
    batch-executes pending snippets at the next cycle boundary.

    Args:
        code: Python source to evaluate against the PFC ``__main__`` namespace.
        request_id: Identifier carried through for downstream cancellation
            (used by future interrupt-injection logic; currently opaque).

    Returns:
        Future: resolves with a result dict from
        ``execution.snippet.run_snippet``.

    Note:
        Thread-safe. Multiple concurrent calls are supported.
    """
    future = Future()
    _pending_queue.put((code, request_id, future))
    logger.debug(
        "Snippet queued: request_id=%s (queue_size=%d)",
        request_id, _pending_queue.qsize()
    )
    return future


# =============================================================================
# PFC Callback Function (Executed in main thread during cycle gaps)
# =============================================================================

def _run_pending_snippet(code, request_id, future):
    # type: (str, str, Future) -> None
    """
    Run a single pending snippet and resolve its future.

    Delegates execution to ``execution.snippet.run_snippet`` so the
    callback path and the queue path share identical semantics.
    """
    from ..execution.snippet import run_snippet

    try:
        result = run_snippet(code, StringIO())
        future.set_result(result)
    except BaseException as e:
        # ``run_snippet`` catches BaseException internally; this is
        # defence-in-depth so a future change that lets one slip
        # doesn't strand the future.
        logger.error("Snippet callback execution failed: %s", e)
        future.set_exception(e)


def _pfc_executor_callback():
    # type: () -> None
    """
    PFC callback - batch-execute pending snippets.

    Called by PFC after each cycle. Processes up to ``MAX_BATCH_SIZE``
    pending snippet requests in the queue.

    No parameters - reads from global ``_pending_queue``.

    Note:
        - Fast path when queue empty (just an empty check)
        - Each snippet executes in PFC main thread
        - Results returned via ``Future.set_result()``
    """
    # Fast path: no pending snippets (99% of the time)
    if _pending_queue.empty():
        return

    # Batch-execute all pending snippets
    executed = 0
    while executed < MAX_BATCH_SIZE:
        try:
            code, request_id, future = _pending_queue.get_nowait()
        except Empty:
            break

        _run_pending_snippet(code, request_id, future)
        executed += 1

    if executed > 0:
        logger.info("Executed %d snippet(s) via callback", executed)


# =============================================================================
# Callback Registration
# =============================================================================

_callback_registered = False


def register_executor_callback(itasca_module, position=51.0):
    # type: (Any, float) -> bool
    """
    Register the snippet-batching callback with PFC.

    Must be called once during server startup. This function:
    1. Injects ``_pfc_executor_callback`` into ``__main__`` namespace
    2. Registers callback with ``itasca.set_callback()``

    Args:
        itasca_module: The itasca module (imported in PFC environment).
        position: Cycle execution position (default: 51.0)
            - 50.0: interrupt check callback
            - 51.0: snippet execution (after interrupt)

    Returns:
        bool: True if registered successfully, False if already registered.
    """
    global _callback_registered

    if _callback_registered:
        logger.warning("Executor callback already registered")
        return False

    try:
        # Inject function into __main__ namespace (required for PFC lookup)
        import __main__
        __main__._pfc_executor_callback = _pfc_executor_callback  # type: ignore[attr-defined]

        # Register with PFC
        itasca_module.set_callback("_pfc_executor_callback", position)

        _callback_registered = True
        logger.info("Executor callback registered (position=%.1f)", position)
        return True

    except Exception as e:
        logger.error("Failed to register executor callback: %s", e)
        return False


def is_executor_callback_registered():
    # type: () -> bool
    """Check if executor callback is registered."""
    return _callback_registered
