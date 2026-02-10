"""
Task Manager - Registry and lifecycle management for long-running tasks.

This module provides the main TaskManager class that acts as a registry
for all tracked tasks, delegating type-specific behavior to Task objects.

Python 3.6 compatible implementation.
"""

import uuid
import logging
from typing import Any, Dict, Optional

from .task import ScriptTask
from .persistence import TaskPersistence

# Module logger
logger = logging.getLogger("PFC-Server")


class TaskManager:
    """
    Manage long-running task tracking and status queries.

    This class is separate from ScriptRunner to maintain clear
    separation of concerns: runner runs scripts, task manager
    tracks their lifecycle.

    Tasks are represented as ScriptTask objects for Python script execution.
    """

    def __init__(self):
        # type: () -> None
        """Initialize task manager with empty task registry."""
        # Task registry: {task_id: Task}
        self.tasks = {}  # type: Dict[str, ScriptTask]

        # Persistence manager
        self.persistence = TaskPersistence()
        self._load_historical_tasks()

        logger.info("TaskManager initialized")

    def _load_historical_tasks(self):
        # type: () -> None
        """Load historical tasks from disk on startup."""
        try:
            tasks_data = self.persistence.load_tasks()
            for task_data in tasks_data:
                historical_task = self.persistence.restore_task_as_historical(task_data)
                if historical_task:
                    self.tasks[historical_task.task_id] = historical_task

            logger.info("Loaded %d historical task(s)", len(tasks_data))
        except Exception as e:
            logger.error("Failed to load historical tasks: {}".format(e))

    def create_script_task(self, session_id, future, script_name, entry_script, output_buffer=None, description=None, task_id=None):
        # type: (str, Any, str, str, Any, Optional[str], Optional[str]) -> str
        """
        Register a new long-running Python script task.

        Args:
            session_id: Session identifier for task isolation
            future: asyncio Future object for the task
            script_name: Name of the script file (e.g., "main.py")
            entry_script: Full path to entry script
            output_buffer: Optional FileBuffer for output capture (writes to disk)
            description: Task description from PFC agent (LLM-provided)
            task_id: Optional pre-generated task ID (if None, generates new one)

        Returns:
            str: Unique task ID for tracking
        """
        if task_id is None:
            task_id = uuid.uuid4().hex[:8]
        # Pass save callback for automatic persistence on status change
        task = ScriptTask(
            task_id, session_id, future, script_name, entry_script,
            output_buffer, description, on_status_change=self._on_task_status_change,
        )
        self.tasks[task_id] = task

        # Save to disk immediately
        self._save_tasks()

        return task_id

    def has_running_tasks(self):
        # type: () -> bool
        """
        Check if any task is currently running.

        Used to determine execution path for diagnostic scripts:
        - If tasks are running: queue is blocked, use callback execution
        - If no tasks running: queue is available, use queue execution

        Returns:
            bool: True if at least one task has status "running"
        """
        for task in self.tasks.values():
            if task.status == "running":
                return True
        return False

    def get_task_status(self, task_id):
        # type: (str) -> Dict[str, Any]
        """
        Query task status (non-blocking).

        Delegates to polymorphic task objects for type-specific handling.

        Args:
            task_id: Task ID to query

        Returns:
            Dict with status information (format depends on task type)
        """
        task = self.tasks.get(task_id)

        if not task:
            return {
                "status": "not_found",
                "message": "Task ID not found: {}".format(task_id),
                "data": None
            }

        return task.get_status_response()

    def list_all_tasks(self, session_id=None, offset=0, limit=None):
        # type: (Optional[str], int, Optional[int]) -> Dict[str, Any]
        """
        List currently tracked tasks, optionally filtered by session with pagination.

        Args:
            session_id: Optional session ID to filter tasks
            offset: Skip N most recent tasks (0 = most recent, default: 0)
            limit: Maximum tasks to return (None = all tasks, default: None)

        Returns:
            Dict with task list:
                - status: "success"
                - message: Summary message
                - data: List of task info dictionaries (paginated)
                - pagination: Pagination metadata
        """
        # Filter tasks by session if specified
        # Support both full UUID and 8-char prefix matching for session_id
        filtered_tasks = list(self.tasks.values())

        # Apply session filter
        if session_id:
            filtered_tasks = [
                task for task in filtered_tasks
                if task.session_id == session_id or task.session_id.startswith(session_id)
            ]

        # Sort by start_time descending (most recent first)
        sorted_tasks = sorted(
            filtered_tasks,
            key=lambda t: t.start_time,
            reverse=True
        )

        # Apply pagination
        total_count = len(sorted_tasks)
        start_idx = offset
        end_idx = start_idx + limit if limit else total_count

        paginated_tasks = sorted_tasks[start_idx:end_idx]
        tasks_info = [task.get_task_info() for task in paginated_tasks]

        # Build message
        if session_id:
            message = "Found {} tracked task(s) for session {} (showing {} of {})".format(
                len(tasks_info), session_id, len(tasks_info), total_count
            )
        else:
            message = "Found {} tracked task(s) across all sessions (showing {} of {})".format(
                total_count, len(tasks_info), total_count
            )

        # Pagination metadata
        pagination = {
            "total_count": total_count,
            "displayed_count": len(tasks_info),
            "offset": offset,
            "limit": limit,
            "has_more": end_idx < total_count
        }

        return {
            "status": "success",
            "message": message,
            "data": tasks_info,
            "pagination": pagination
        }

    def mark_task_notified(self, task_id):
        # type: (str) -> Dict[str, Any]
        """
        Mark a task as notified (completion notification sent to LLM).

        This prevents repeated notifications for the same task completion.
        The notified flag is persisted across server restarts.

        Args:
            task_id: Task ID to mark as notified

        Returns:
            Dict with operation status:
                - status: "success" or "not_found"
                - message: Result message
        """
        task = self.tasks.get(task_id)

        if not task:
            return {
                "status": "not_found",
                "message": "Task ID not found: {}".format(task_id)
            }

        # Mark as notified
        task.notified = True

        # Save to disk
        self._save_tasks()

        return {
            "status": "success",
            "message": "Task {} marked as notified".format(task_id)
        }

    def _save_tasks(self):
        # type: () -> None
        """Save current tasks to disk."""
        self.persistence.save_tasks(self.tasks)

    def _on_task_status_change(self, task):
        # type: (ScriptTask) -> None
        """
        Callback invoked when a task's status changes (completion/failure).

        Automatically saves task state to disk for persistence.

        Args:
            task: Task that changed status
        """
        logger.debug("Task {} status changed to: {}".format(task.task_id, task.status))
        # Save tasks to disk
        self._save_tasks()

    def clear_all_tasks(self):
        # type: () -> int
        """
        Clear all tasks from memory and disk storage.

        WARNING: This permanently deletes task history. Use for testing/reset only.

        Returns:
            int: Number of tasks cleared
        """
        import os
        import shutil

        cleared_count = len(self.tasks)
        self.tasks.clear()

        # Delete all session directories from disk
        if os.path.exists(self.persistence.sessions_dir):
            for session_name in os.listdir(self.persistence.sessions_dir):
                session_path = os.path.join(self.persistence.sessions_dir, session_name)
                if os.path.isdir(session_path):
                    shutil.rmtree(session_path)

        logger.info("Cleared all %d task(s)", cleared_count)
        return cleared_count
