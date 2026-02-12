"""
Interrupt Manager - Global interrupt callback registration and task interrupt management.

This module provides a mechanism to interrupt long-running PFC simulations
via itasca.set_callback(). The callback checks interrupt flags each cycle
and raises InterruptedError to stop execution.

Key constraints:
- PFC callback looks up function by name in __main__ namespace
- Functions defined in exec() context are not visible to PFC
- Must register global function in __main__ before use

Architecture:
- WebSocket thread: calls request_interrupt(task_id) when user cancels
- Main thread: script execution with set_current_task()/clear_current_task()
- PFC callback: _pfc_interrupt_check() checks flag each cycle

Python 3.6 compatible implementation.
"""

import threading
import logging
from typing import Any, Optional

# Module logger
logger = logging.getLogger("PFC-Server")


# =============================================================================
# Interrupt Flag Management (Thread-safe)
# =============================================================================

# Interrupt flags: set of task IDs with pending interrupt requests
_interrupt_flags = set()  # type: set
_flags_lock = threading.Lock()


def request_interrupt(task_id):
    # type: (str) -> bool
    """
    Request interrupt for a running task.

    Called from WebSocket handler thread when user requests cancellation.

    Args:
        task_id: Task ID to interrupt

    Returns:
        bool: True if request registered, False if task_id empty
    """
    if not task_id:
        return False

    with _flags_lock:
        _interrupt_flags.add(task_id)

    logger.info("Interrupt requested: %s", task_id)
    return True


def check_interrupt(task_id):
    # type: (str) -> bool
    """
    Check if interrupt requested for a task.

    Called from PFC callback during cycle execution.
    Must be fast - runs every cycle during simulation.

    Args:
        task_id: Task ID to check

    Returns:
        bool: True if interrupt requested, False otherwise
    """
    # Fast path: set membership is atomic in CPython due to GIL
    return task_id in _interrupt_flags


def clear_interrupt(task_id):
    # type: (str) -> None
    """
    Clear interrupt flag for a task.

    Called after task completion or interruption to clean up.

    Args:
        task_id: Task ID to clear
    """
    with _flags_lock:
        if task_id in _interrupt_flags:
            _interrupt_flags.discard(task_id)
            logger.debug("Cleared interrupt flag: %s", task_id)


# =============================================================================
# Current Task Tracking (Main Thread Only)
# =============================================================================

# Current task being executed in main thread
_current_task_id = None  # type: Optional[str]


def set_current_task(task_id):
    # type: (str) -> None
    """
    Set current task ID before script execution.

    Called in main thread before exec() to enable interrupt checking.

    Args:
        task_id: Task ID being executed
    """
    global _current_task_id
    _current_task_id = task_id
    logger.debug("Current task set: %s", task_id)


def clear_current_task():
    # type: () -> None
    """
    Clear current task ID after script execution.

    Called in main thread after exec() completes (success or failure).
    """
    global _current_task_id
    prev_task = _current_task_id
    _current_task_id = None
    if prev_task:
        logger.debug("Current task cleared: %s", prev_task)


# =============================================================================
# Global Interrupt Check Function (Registered with PFC)
# =============================================================================

def _pfc_interrupt_check():
    # type: () -> None
    """
    Global function called by PFC each cycle.

    Checks if current task has interrupt request and raises InterruptedError.
    This function is injected into __main__ namespace and registered with PFC.

    Note:
        Must be fast - runs every cycle during simulation.
        Only checks current task's flag, no locking needed (GIL atomic read).

    Raises:
        InterruptedError: If current task has pending interrupt request
    """
    task_id = _current_task_id
    if task_id and check_interrupt(task_id):
        logger.info("Interrupting task: %s", task_id)
        raise InterruptedError("Task {} interrupted by user".format(task_id))


# =============================================================================
# PFC Callback Registration
# =============================================================================

def _re_register_callback(itasca_module, position=50.0):
    # type: (Any, float) -> None
    """
    Re-register interrupt callback with PFC.

    Called after model new/restore commands which clear PFC's callback registry.
    Also re-registers diagnostic callback if it was registered.
    """
    import __main__
    __main__._pfc_interrupt_check = _pfc_interrupt_check  # type: ignore[attr-defined]
    itasca_module.set_callback("_pfc_interrupt_check", position)
    logger.debug("Interrupt callback re-registered after model reset")

    # Also re-register diagnostic callback if it was registered
    try:
        from .diagnostic import _pfc_diagnostic_callback, is_callback_registered
        if is_callback_registered():
            __main__._pfc_diagnostic_callback = _pfc_diagnostic_callback  # type: ignore[attr-defined]
            itasca_module.set_callback("_pfc_diagnostic_callback", 51.0)
            logger.debug("Diagnostic callback re-registered after model reset")
    except ImportError:
        pass  # diagnostic_executor not available


# Commands that clear PFC's callback registry
_MODEL_RESET_COMMANDS = ("model new", "model restore")


def register_interrupt_callback(itasca_module, position=50.0):
    # type: (Any, float) -> bool
    """
    Register interrupt callback with PFC.

    Must be called once during server startup. This function:
    1. Injects _pfc_interrupt_check into __main__ namespace
    2. Registers callback with itasca.set_callback()
    3. Wraps itasca.command to auto-re-register after model new/restore

    Args:
        itasca_module: The itasca module (imported in PFC environment)
        position: Cycle execution position (50.0 = after cycle completion)
            - Negative values: before cycle starts
            - 0.0: timestep calculation
            - 10.0: kinematics
            - 20.0: time accumulation
            - 45.0+: after cycle completion

    Returns:
        bool: True if registered successfully
    """
    try:
        # Inject function into __main__ namespace (required for PFC lookup)
        import __main__
        __main__._pfc_interrupt_check = _pfc_interrupt_check  # type: ignore[attr-defined]

        # Register with PFC
        itasca_module.set_callback("_pfc_interrupt_check", position)

        # Wrap itasca.command to auto-re-register callback after model new/restore
        # These commands clear PFC's internal callback registry
        _original_command = itasca_module.command

        def _wrapped_command(cmd):
            result = _original_command(cmd)
            # Check if command resets model (clears callback registry)
            cmd_lower = cmd.strip().lower()
            for reset_cmd in _MODEL_RESET_COMMANDS:
                if cmd_lower.startswith(reset_cmd):
                    _re_register_callback(itasca_module, position)
                    break
            return result

        itasca_module.command = _wrapped_command

        logger.info("Interrupt callback registered (position=%.1f)", position)
        return True

    except Exception as e:
        logger.error("Failed to register interrupt callback: %s", e)
        return False
