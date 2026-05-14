"""
PFC Server Signals and Callbacks.

Inter-process communication mechanisms:
- Interrupt signals for task cancellation
- Cycle-gap snippet executor scheduling
"""

from .interrupt import (
    request_interrupt,
    check_interrupt,
    clear_interrupt,
    set_current_task,
    clear_current_task,
    register_interrupt_callback,
)
from .cycle_executor import (
    submit_snippet,
    is_executor_callback_registered,
    register_executor_callback,
)

__all__ = [
    # Interrupt signals
    "request_interrupt",
    "check_interrupt",
    "clear_interrupt",
    "set_current_task",
    "clear_current_task",
    "register_interrupt_callback",
    # Cycle-gap executor
    "submit_snippet",
    "is_executor_callback_registered",
    "register_executor_callback",
]
