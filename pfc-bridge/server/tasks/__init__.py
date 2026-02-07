"""
PFC Task Lifecycle Management.

Task tracking, persistence, and status queries for long-running PFC scripts.

Public API:
    - TaskManager: Main task registry and management interface
    - Task: Abstract base class for task types (for type hints)
    - ScriptTask: Python script execution task type with real-time output capture

Python 3.6 compatible implementation.
"""

from .manager import TaskManager
from .task_base import Task
from .task_types import ScriptTask

__all__ = [
    "TaskManager",
    "Task",
    "ScriptTask",
]
