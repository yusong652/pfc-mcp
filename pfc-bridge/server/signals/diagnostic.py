"""
Diagnostic Executor - Callback-based script execution for diagnostic operations.

This module provides a mechanism to execute diagnostic scripts (like plot capture)
even when PFC main thread is blocked by cycle() computation. It uses PFC's
callback system to execute scripts in the gaps between cycles.

Key Design:
- Uses thread-safe queue for pending diagnostic requests
- Callback executes at position 51.0 (after interrupt check at 50.0)
- Batch execution: processes all pending diagnostics per callback invocation
- Supports concurrent diagnostic requests from agent

Architecture:
- WebSocket thread: calls submit_diagnostic(script_path) -> queued
- PFC callback: _pfc_diagnostic_callback() batch executes all pending
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
# Global State (Queue for pending diagnostic requests)
# =============================================================================

# Queue of pending diagnostics: (script_path, future) tuples
_pending_queue = Queue()  # type: Queue[Tuple[str, Future]]

# Maximum diagnostics to execute per callback (safety limit)
MAX_BATCH_SIZE = 10


# =============================================================================
# External Interface (Called from WebSocket thread)
# =============================================================================

def submit_diagnostic(script_path):
    # type: (str) -> Future
    """
    Submit diagnostic script for callback execution.

    Called from WebSocket handler thread. The script will be queued and
    executed by PFC callback during next cycle gap. Multiple diagnostics
    can be queued and will be batch executed.

    Args:
        script_path: Absolute path to Python script file

    Returns:
        Future: Future object to await execution result

    Example:
        future = submit_diagnostic("/path/to/capture_plot.py")
        result = future.result(timeout=30)  # Wait up to 30 seconds

    Note:
        Thread-safe. Multiple concurrent calls are supported.
    """
    future = Future()
    _pending_queue.put((script_path, future))
    logger.debug("Diagnostic queued: %s (queue_size=%d)", script_path, _pending_queue.qsize())
    return future


def get_pending_count():
    # type: () -> int
    """Get number of pending diagnostic requests."""
    return _pending_queue.qsize()


def is_diagnostic_pending():
    # type: () -> bool
    """Check if any diagnostic script is pending execution."""
    return not _pending_queue.empty()


def clear_pending_diagnostics():
    # type: () -> int
    """
    Clear all pending diagnostics (for cleanup/reset).

    Returns:
        int: Number of diagnostics cleared
    """
    cleared = 0
    while True:
        try:
            script_path, future = _pending_queue.get_nowait()
            if not future.done():
                future.set_exception(
                    RuntimeError("Diagnostic cleared before execution")
                )
            cleared += 1
        except Empty:
            break

    if cleared > 0:
        logger.info("Cleared %d pending diagnostic(s)", cleared)

    return cleared


# =============================================================================
# PFC Callback Function (Executed in main thread during cycle gaps)
# =============================================================================

def _execute_single_diagnostic(script_path, future):
    # type: (str, Future) -> None
    """
    Execute a single diagnostic script.

    Args:
        script_path: Path to diagnostic script
        future: Future to set result/exception on
    """
    import sys
    import os

    try:
        import itasca  # type: ignore

        # Read script content
        with open(script_path, 'r', encoding='utf-8') as f:
            script_content = f.read()

        # Temporarily restore original stdout to avoid mixing with main script output
        # When main script is running, sys.stdout points to its FileBuffer
        # Diagnostic output should go to original console, not main script's log
        old_stdout = sys.stdout
        sys.stdout = sys.__stdout__  # Python's original stdout

        try:
            # Execute in isolated namespace with itasca available
            exec_context = {"itasca": itasca}
            exec(script_content, exec_context, exec_context)
        finally:
            sys.stdout = old_stdout  # Restore (back to main script's buffer if running)

        # Get result if script defined 'result' variable
        result = exec_context.get("result", None)

        future.set_result({
            "status": "success",
            "message": "Diagnostic executed via callback",
            "data": result
        })

        logger.debug("Diagnostic completed: %s", os.path.basename(script_path))

    except Exception as e:
        logger.error("Diagnostic execution failed: %s - %s", script_path, e)
        future.set_exception(e)


def _pfc_diagnostic_callback():
    # type: () -> None
    """
    PFC callback - Batch execute all pending diagnostic scripts.

    This function is called by PFC after each cycle. It processes all
    pending diagnostic requests in the queue (up to MAX_BATCH_SIZE).

    No parameters - reads from global _pending_queue.

    Note:
        - Fast path when queue empty (just an empty check)
        - Batch execution reduces cycle gap overhead
        - Each script executes in PFC main thread
        - Results returned via Future.set_result()
    """
    # Fast path: no pending diagnostics (99% of the time)
    if _pending_queue.empty():
        return

    # Batch execute all pending diagnostics
    executed = 0
    while executed < MAX_BATCH_SIZE:
        try:
            script_path, future = _pending_queue.get_nowait()
        except Empty:
            break

        _execute_single_diagnostic(script_path, future)
        executed += 1

    if executed > 0:
        logger.info("Executed %d diagnostic(s) via callback", executed)


# =============================================================================
# Callback Registration
# =============================================================================

_callback_registered = False


def register_diagnostic_callback(itasca_module, position=51.0):
    # type: (Any, float) -> bool
    """
    Register diagnostic callback with PFC.

    Must be called once during server startup. This function:
    1. Injects _pfc_diagnostic_callback into __main__ namespace
    2. Registers callback with itasca.set_callback()

    Args:
        itasca_module: The itasca module (imported in PFC environment)
        position: Cycle execution position (default: 51.0)
            - 50.0: interrupt check callback
            - 51.0: diagnostic execution (after interrupt)

    Returns:
        bool: True if registered successfully, False if already registered
    """
    global _callback_registered

    if _callback_registered:
        logger.warning("Diagnostic callback already registered")
        return False

    try:
        # Inject function into __main__ namespace (required for PFC lookup)
        import __main__
        __main__._pfc_diagnostic_callback = _pfc_diagnostic_callback  # type: ignore[attr-defined]

        # Register with PFC
        itasca_module.set_callback("_pfc_diagnostic_callback", position)

        _callback_registered = True
        logger.info("Diagnostic callback registered (position=%.1f)", position)
        return True

    except Exception as e:
        logger.error("Failed to register diagnostic callback: %s", e)
        return False


def unregister_diagnostic_callback(itasca_module, position=51.0):
    # type: (Any, float) -> bool
    """
    Unregister diagnostic callback from PFC.

    Args:
        itasca_module: The itasca module
        position: Same position used in registration

    Returns:
        bool: True if unregistered successfully
    """
    global _callback_registered

    if not _callback_registered:
        return False

    try:
        itasca_module.remove_callback("_pfc_diagnostic_callback", position)
        _callback_registered = False
        logger.info("Diagnostic callback unregistered")
        return True

    except Exception as e:
        logger.error("Failed to unregister diagnostic callback: %s", e)
        return False


def is_callback_registered():
    # type: () -> bool
    """Check if diagnostic callback is registered."""
    return _callback_registered
