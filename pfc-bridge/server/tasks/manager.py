"""
Task Manager - Registry and lifecycle management for long-running tasks.

This module provides the main TaskManager class that acts as a registry
for all tracked tasks, delegating type-specific behavior to Task objects.

Python 3.6 compatible implementation.
"""

import uuid
import logging
from typing import Any, Dict, Optional

from .task_base import Task
from .task_types import ScriptTask
from .persistence import TaskPersistence

# Module logger
logger = logging.getLogger("PFC-Server")


class TaskManager:
    """
    Manage long-running task tracking and status queries.

    This class is separate from ScriptRunner to maintain clear
    separation of concerns: runner runs scripts, task manager
    tracks their lifecycle.

    Tasks are represented as ScriptTask objects for Python script execution,
    enabling clean extension and type-specific behavior.
    """

    def __init__(self, enable_persistence=True):
        # type: (bool,) -> None
        """
        Initialize task manager with empty task registry.

        Args:
            enable_persistence: Enable task persistence to disk (default: True)
        """
        # Task registry: {task_id: Task}
        self.tasks = {}  # type: Dict[str, Task]

        # Persistence manager
        self.enable_persistence = enable_persistence
        if enable_persistence:
            self.persistence = TaskPersistence()
            # Load historical tasks from disk
            self._load_historical_tasks()
        else:
            self.persistence = None

        logger.info(
            "TaskManager initialized (persistence=%s)",
            "enabled" if enable_persistence else "disabled"
        )

    def _load_historical_tasks(self):
        # type: () -> None
        """Load historical tasks from disk on startup."""
        if not self.persistence:
            return

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

    def cleanup_completed_tasks(self, session_id=None):
        # type: (Optional[str]) -> int
        """
        Manually remove completed/failed/interrupted tasks from tracking.

        By default, completed, failed, and interrupted tasks are kept as historical context.
        Use this method to explicitly clean up old tasks when memory management
        is needed or when the task history becomes too large.

        Args:
            session_id: Optional session ID to clean up. If None, cleans all sessions.

        Returns:
            int: Number of tasks cleaned up
        """
        if session_id:
            # Clean up specific session (support both full UUID and 8-char prefix)
            tasks_to_remove = [
                task_id for task_id, task in self.tasks.items()
                if (task.session_id == session_id or task.session_id.startswith(session_id))
                and task.status in ["completed", "failed", "interrupted"]
            ]
        else:
            # Clean up all sessions
            tasks_to_remove = [
                task_id for task_id, task in self.tasks.items()
                if task.status in ["completed", "failed", "interrupted"]
            ]

        for task_id in tasks_to_remove:
            del self.tasks[task_id]

        if tasks_to_remove:
            logger.info("Cleaned up {} completed task(s) {}".format(
                len(tasks_to_remove),
                "for session {}".format(session_id) if session_id else "across all sessions"
            ))
            # Save changes to disk
            self._save_tasks()

        return len(tasks_to_remove)

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
        """Save current tasks to disk (if persistence enabled)."""
        if self.persistence:
            # Save asynchronously to avoid blocking
            self.persistence.save_tasks(self.tasks)

    def _on_task_status_change(self, task):
        # type: (Task) -> None
        """
        Callback invoked when a task's status changes (completion/failure).

        Automatically saves task state to disk for persistence.

        Args:
            task: Task that changed status
        """
        logger.debug("Task {} status changed to: {}".format(task.task_id, task.status))
        # Save tasks to disk
        self._save_tasks()

    def clear_all_tasks(self, session_id=None):
        # type: (Optional[str]) -> Dict[str, Any]
        """
        Clear all tasks from memory and disk storage.

        WARNING: This permanently deletes task history. Use for testing/reset only.

        Args:
            session_id: Optional session ID to clear. If None, clears ALL tasks.

        Returns:
            Dict with:
                - success: bool
                - message: str
                - cleared_count: int
        """
        import os
        import shutil

        try:
            if session_id:
                # Clear specific session (support both full UUID and 8-char prefix)
                tasks_to_remove = [
                    task_id for task_id, task in self.tasks.items()
                    if task.session_id == session_id or task.session_id.startswith(session_id)
                ]
                for task_id in tasks_to_remove:
                    del self.tasks[task_id]

                # Delete session directory from disk
                if self.persistence:
                    session_dir = os.path.join(self.persistence.sessions_dir, session_id)
                    if os.path.exists(session_dir):
                        shutil.rmtree(session_dir)

                logger.info(
                    "Cleared %d task(s) for session %s",
                    len(tasks_to_remove), session_id
                )

                return {
                    "success": True,
                    "message": "Cleared {} task(s) for session {}".format(
                        len(tasks_to_remove), session_id
                    ),
                    "cleared_count": len(tasks_to_remove)
                }

            else:
                # Clear ALL tasks
                cleared_count = len(self.tasks)
                self.tasks.clear()

                # Delete all session directories from disk
                if self.persistence and os.path.exists(self.persistence.sessions_dir):
                    for session_name in os.listdir(self.persistence.sessions_dir):
                        session_path = os.path.join(self.persistence.sessions_dir, session_name)
                        if os.path.isdir(session_path):
                            shutil.rmtree(session_path)

                logger.info("Cleared all %d task(s) across all sessions", cleared_count)

                return {
                    "success": True,
                    "message": "Cleared all {} task(s)".format(cleared_count),
                    "cleared_count": cleared_count
                }

        except Exception as e:
            logger.error("Failed to clear tasks: {}".format(e))
            return {
                "success": False,
                "message": "Error: {}".format(str(e)),
                "cleared_count": 0
            }
