"""
PFC Server Signals and Callbacks.

Inter-process communication mechanisms:
- Interrupt signals for task cancellation
- Script executor callback scheduling for cycle-gap execution
"""

from .interrupt import (
    request_interrupt,
    check_interrupt,
    clear_interrupt,
    set_current_task,
    clear_current_task,
    register_interrupt_callback,
)
from .script_executor import (
    submit_script,
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
    # Script executor callback
    "submit_script",
    "is_executor_callback_registered",
    "register_executor_callback",
]
