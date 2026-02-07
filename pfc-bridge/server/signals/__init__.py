"""
PFC Server Signals and Callbacks.

Inter-process communication mechanisms:
- Interrupt signals for task cancellation
- Diagnostic callback scheduling for cycle-gap execution
"""

from .interrupt import (
    request_interrupt,
    check_interrupt,
    clear_interrupt,
    cleanup_stale_flags,
    get_pending_interrupts,
    set_current_task,
    clear_current_task,
    get_current_task,
    register_interrupt_callback,
    unregister_interrupt_callback,
    is_callback_registered as is_interrupt_callback_registered,
)
from .diagnostic import (
    submit_diagnostic,
    is_diagnostic_pending,
    get_pending_count,
    clear_pending_diagnostics,
    is_callback_registered as is_diagnostic_callback_registered,
    register_diagnostic_callback,
    unregister_diagnostic_callback,
)

__all__ = [
    # Interrupt signals
    "request_interrupt",
    "check_interrupt",
    "clear_interrupt",
    "cleanup_stale_flags",
    "get_pending_interrupts",
    "set_current_task",
    "clear_current_task",
    "get_current_task",
    "register_interrupt_callback",
    "unregister_interrupt_callback",
    "is_interrupt_callback_registered",
    # Diagnostic callback
    "submit_diagnostic",
    "is_diagnostic_pending",
    "get_pending_count",
    "clear_pending_diagnostics",
    "is_diagnostic_callback_registered",
    "register_diagnostic_callback",
    "unregister_diagnostic_callback",
]
