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
    set_current_task,
    clear_current_task,
    register_interrupt_callback,
)
from .diagnostic import (
    submit_diagnostic,
    is_callback_registered as is_diagnostic_callback_registered,
    register_diagnostic_callback,
)

__all__ = [
    # Interrupt signals
    "request_interrupt",
    "check_interrupt",
    "clear_interrupt",
    "set_current_task",
    "clear_current_task",
    "register_interrupt_callback",
    # Diagnostic callback
    "submit_diagnostic",
    "is_diagnostic_callback_registered",
    "register_diagnostic_callback",
]
