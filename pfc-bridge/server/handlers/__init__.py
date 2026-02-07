"""
PFC WebSocket Server Message Handlers.

This module provides modular message handlers for the PFC WebSocket server.
Each handler module focuses on a specific domain of functionality.
"""

from .context import ServerContext
from .task_handlers import (
    handle_pfc_task,
    handle_check_task_status,
    handle_list_tasks,
    handle_mark_task_notified,
)
from .console_handlers import handle_user_console
from .diagnostic_handlers import handle_diagnostic_execute
from .workspace_handlers import (
    handle_reset_workspace,
    handle_get_working_directory,
)
from .utility_handlers import (
    handle_ping,
    handle_interrupt_task,
)

__all__ = [
    # Context
    "ServerContext",
    # Task handlers
    "handle_pfc_task",
    "handle_check_task_status",
    "handle_list_tasks",
    "handle_mark_task_notified",
    # Console handlers
    "handle_user_console",
    # Diagnostic handlers
    "handle_diagnostic_execute",
    # Workspace handlers
    "handle_reset_workspace",
    "handle_get_working_directory",
    # Utility handlers
    "handle_ping",
    "handle_interrupt_task",
]
