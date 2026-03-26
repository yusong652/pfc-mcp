"""
Script Executor - Callback-based script execution for PFC main thread.

This module provides a mechanism to execute scripts in the PFC main thread
even when it is blocked by cycle() computation. It uses PFC's callback
system to execute scripts in the gaps between cycles.

Key Design:
- Uses thread-safe queue for pending script requests
- Callback executes at position 51.0 (after interrupt check at 50.0)
- Batch execution: processes all pending scripts per callback invocation
- Supports concurrent script requests from agent

Architecture:
- WebSocket thread: calls submit_script(script_path) -> queued
- PFC callback: _pfc_executor_callback() batch executes all pending
- Results returned via Future objects

Python 3.6 compatible implementation.
"""

import logging
from concurrent.futures import Future
from typing import Any, Tuple

# Python 3.6 compatible queue import
try:
    from queue import Queue, Empty
except ImportError:
    from Queue import Queue, Empty  # type: ignore

# Module logger
logger = logging.getLogger("PFC-Server")


# =============================================================================
# Global State (Queue for pending script requests)
# =============================================================================

# Queue of pending scripts: (script_path, future) tuples
_pending_queue = Queue()  # type: Queue[Tuple[str, Future]]

# Maximum scripts to execute per callback (safety limit)
MAX_BATCH_SIZE = 10


# =============================================================================
# External Interface (Called from WebSocket thread)
# =============================================================================

def submit_script(script_path):
    # type: (str) -> Future
    """
    Submit script for callback execution.

    Called from WebSocket handler thread. The script will be queued and
    executed by PFC callback during next cycle gap. Multiple scripts
    can be queued and will be batch executed.

    Args:
        script_path: Absolute path to Python script file

    Returns:
        Future: Future object to await execution result

    Note:
        Thread-safe. Multiple concurrent calls are supported.
    """
    future = Future()
    _pending_queue.put((script_path, future))
    logger.debug("Script queued: %s (queue_size=%d)", script_path, _pending_queue.qsize())
    return future


# =============================================================================
# PFC Callback Function (Executed in main thread during cycle gaps)
# =============================================================================

def _execute_single_script(script_path, future):
    # type: (str, Future) -> None
    """
    Execute a single script.

    Args:
        script_path: Path to Python script
        future: Future to set result/exception on
    """
    import sys
    import os
    from io import StringIO

    try:
        import itasca  # type: ignore

        # Read script content
        with open(script_path, 'r', encoding='utf-8') as f:
            script_content = f.read()

        # Capture stdout into a buffer so print() output is returned to caller
        old_stdout = sys.stdout
        capture_buffer = StringIO()
        sys.stdout = capture_buffer

        try:
            # Execute in isolated namespace with itasca available
            exec_context = {"itasca": itasca}
            exec(script_content, exec_context, exec_context)
        finally:
            sys.stdout = old_stdout

        # Get result if script defined 'result' variable
        result = exec_context.get("result", None)
        output = capture_buffer.getvalue()

        future.set_result({
            "status": "success",
            "message": "Script executed via callback",
            "output": output,
            "result": result,
            "data": result,
        })

        logger.debug("Script completed: %s", os.path.basename(script_path))

    except Exception as e:
        logger.error("Script execution failed: %s - %s", script_path, e)
        future.set_exception(e)


def _pfc_executor_callback():
    # type: () -> None
    """
    PFC callback - Batch execute all pending scripts.

    This function is called by PFC after each cycle. It processes all
    pending script requests in the queue (up to MAX_BATCH_SIZE).

    No parameters - reads from global _pending_queue.

    Note:
        - Fast path when queue empty (just an empty check)
        - Batch execution reduces cycle gap overhead
        - Each script executes in PFC main thread
        - Results returned via Future.set_result()
    """
    # Fast path: no pending scripts (99% of the time)
    if _pending_queue.empty():
        return

    # Batch execute all pending scripts
    executed = 0
    while executed < MAX_BATCH_SIZE:
        try:
            script_path, future = _pending_queue.get_nowait()
        except Empty:
            break

        _execute_single_script(script_path, future)
        executed += 1

    if executed > 0:
        logger.info("Executed %d script(s) via callback", executed)


# =============================================================================
# Callback Registration
# =============================================================================

_callback_registered = False


def register_executor_callback(itasca_module, position=51.0):
    # type: (Any, float) -> bool
    """
    Register script executor callback with PFC.

    Must be called once during server startup. This function:
    1. Injects _pfc_executor_callback into __main__ namespace
    2. Registers callback with itasca.set_callback()

    Args:
        itasca_module: The itasca module (imported in PFC environment)
        position: Cycle execution position (default: 51.0)
            - 50.0: interrupt check callback
            - 51.0: script execution (after interrupt)

    Returns:
        bool: True if registered successfully, False if already registered
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
