"""
Task Manager - Registry, lifecycle, and persistence for long-running tasks.

Provides the TaskManager class that acts as a registry for all tracked tasks,
with disk persistence organized by session.

Persistence layout:
    .nagisa/sessions/{session_id}/tasks.json

Python 3.6 compatible implementation.
"""

import json
import os
import uuid
import shutil
import logging
from typing import Any, Dict, List, Optional

from .task import ScriptTask

# Module logger
logger = logging.getLogger("PFC-Server")

# Persistence constants
DATA_DIR = ".nagisa"
SESSIONS_DIR = os.path.join(DATA_DIR, "sessions")
TASKS_FILENAME = "tasks.json"


class TaskManager:
    """
    Manage long-running task tracking, status queries, and disk persistence.

    Tasks are represented as ScriptTask objects for Python script execution.
    Task history is persisted to disk organized by session for crash recovery.
    """

    def __init__(self):
        # type: () -> None
        """Initialize task manager, load historical tasks from disk."""
        self.tasks = {}  # type: Dict[str, ScriptTask]

        # Ensure persistence directory exists
        if not os.path.exists(SESSIONS_DIR):
            os.makedirs(SESSIONS_DIR)

        self._load_historical_tasks()
        logger.info("TaskManager initialized")

    # ── Task lifecycle ──────────────────────────────────────────

    def create_script_task(self, session_id, future, script_name, entry_script, output_buffer=None, description=None, task_id=None):
        # type: (str, Any, str, str, Any, Optional[str], Optional[str]) -> str
        """Register a new long-running Python script task.

        Returns:
            str: Unique task ID for tracking
        """
        if task_id is None:
            task_id = uuid.uuid4().hex[:8]
        task = ScriptTask(
            task_id, session_id, future, script_name, entry_script,
            output_buffer, description, on_status_change=self._on_task_status_change,
        )
        self.tasks[task_id] = task
        self._save_tasks()
        return task_id

    def has_running_tasks(self):
        # type: () -> bool
        """Check if any task is currently running."""
        for task in self.tasks.values():
            self._refresh_runtime_status(task)
            if task.status == "running":
                return True
        return False

    def get_task_status(self, task_id):
        # type: (str) -> Dict[str, Any]
        """Query task status (non-blocking)."""
        task = self.tasks.get(task_id)
        if not task:
            return {
                "status": "not_found",
                "message": "Task ID not found: {}".format(task_id),
                "data": None
            }
        self._refresh_runtime_status(task)
        return task.get_status_response()

    def list_all_tasks(self, session_id=None, offset=0, limit=None):
        # type: (Optional[str], int, Optional[int]) -> Dict[str, Any]
        """List tracked tasks, optionally filtered by session with pagination."""
        for task in self.tasks.values():
            self._refresh_runtime_status(task)

        filtered_tasks = list(self.tasks.values())

        if session_id:
            filtered_tasks = [
                task for task in filtered_tasks
                if task.session_id == session_id or task.session_id.startswith(session_id)
            ]

        sorted_tasks = sorted(filtered_tasks, key=lambda t: t.start_time, reverse=True)

        total_count = len(sorted_tasks)
        end_idx = offset + limit if limit else total_count
        paginated_tasks = sorted_tasks[offset:end_idx]
        tasks_info = [task.get_task_info() for task in paginated_tasks]

        if session_id:
            message = "Found {} tracked task(s) for session {} (showing {} of {})".format(
                len(tasks_info), session_id, len(tasks_info), total_count
            )
        else:
            message = "Found {} tracked task(s) across all sessions (showing {} of {})".format(
                total_count, len(tasks_info), total_count
            )

        return {
            "status": "success",
            "message": message,
            "data": tasks_info,
            "pagination": {
                "total_count": total_count,
                "displayed_count": len(tasks_info),
                "offset": offset,
                "limit": limit,
                "has_more": end_idx < total_count
            }
        }

    def _refresh_runtime_status(self, task):
        # type: (ScriptTask) -> None
        """Promote pending task to running when Future already started.

        Race condition scenario:
        - main thread starts executing a submitted future
        - ScriptTask has not yet observed running state
        - status remains pending even though output is already produced
        """
        if task.status != "pending":
            return
        future = getattr(task, "future", None)
        if future is None:
            return
        try:
            if future.running():
                task.status = "running"
                if task.on_status_change:
                    task.on_status_change(task)
        except Exception:
            # Best-effort status refresh; ignore transient future state errors.
            return

    def clear_all_tasks(self):
        # type: () -> int
        """Clear all tasks from memory and disk. Returns count cleared."""
        cleared_count = len(self.tasks)
        self.tasks.clear()

        if os.path.exists(SESSIONS_DIR):
            for name in os.listdir(SESSIONS_DIR):
                path = os.path.join(SESSIONS_DIR, name)
                if os.path.isdir(path):
                    shutil.rmtree(path)

        logger.info("Cleared all %d task(s)", cleared_count)
        return cleared_count

    # ── Persistence ─────────────────────────────────────────────

    def _on_task_status_change(self, task):
        # type: (ScriptTask) -> None
        """Callback invoked when a task's status changes."""
        logger.debug("Task {} status changed to: {}".format(task.task_id, task.status))
        self._save_tasks()

    def _save_tasks(self):
        # type: () -> None
        """Save all tasks to disk, grouped by session."""
        try:
            tasks_by_session = {}  # type: Dict[str, List[Dict[str, Any]]]
            for task in self.tasks.values():
                sid = task.session_id
                if sid not in tasks_by_session:
                    tasks_by_session[sid] = []
                tasks_by_session[sid].append(self._serialize_task(task))

            for sid, session_tasks in tasks_by_session.items():
                self._save_session(sid, session_tasks)

        except Exception as e:
            logger.error("Failed to save tasks: {}".format(e))

    def _load_historical_tasks(self):
        # type: () -> None
        """Load historical tasks from disk on startup."""
        try:
            all_data = self._load_all_sessions()
            for task_data in all_data:
                task = self._restore_task(task_data)
                if task:
                    self.tasks[task.task_id] = task
            logger.info("Loaded %d historical task(s)", len(all_data))
        except Exception as e:
            logger.error("Failed to load historical tasks: {}".format(e))

    @staticmethod
    def _serialize_task(task):
        # type: (ScriptTask) -> Dict[str, Any]
        """Serialize a ScriptTask to JSON-compatible dict."""
        return {
            "task_id": task.task_id,
            "session_id": task.session_id,
            "task_type": "script",
            "description": task.description,
            "status": task.status,
            "start_time": task.start_time,
            "end_time": task.end_time,
            "script_name": task.script_name,
            "entry_script": task.entry_script,
            "log_path": task.log_path,
            "error": task.error,
        }

    @staticmethod
    def _restore_task(task_data):
        # type: (Dict[str, Any]) -> Optional[ScriptTask]
        """Restore a ScriptTask from persisted data.

        Running tasks are marked as failed since they can't be resumed.
        """
        try:
            if task_data.get("status") == "running":
                task_data["status"] = "failed"
                logger.warning(
                    "Marked previously running task {} as failed (cannot resume)".format(
                        task_data.get("task_id")
                    )
                )
            return ScriptTask.from_persisted(task_data)
        except Exception as e:
            logger.error("Failed to restore task {}: {}".format(
                task_data.get("task_id"), e
            ))
            return None

    # ── Disk I/O helpers ────────────────────────────────────────

    @staticmethod
    def _session_filepath(session_id):
        # type: (str) -> str
        """Get filepath for a session's tasks.json, creating dir if needed."""
        session_dir = os.path.join(SESSIONS_DIR, session_id)
        if not os.path.exists(session_dir):
            os.makedirs(session_dir)
        return os.path.join(session_dir, TASKS_FILENAME)

    @staticmethod
    def _save_session(session_id, tasks_data):
        # type: (str, List[Dict[str, Any]]) -> None
        """Atomically save tasks for a session."""
        filepath = TaskManager._session_filepath(session_id)
        temp = filepath + ".tmp"
        try:
            with open(temp, 'w') as f:
                json.dump(tasks_data, f, indent=2)
            os.replace(temp, filepath)
        except Exception as e:
            logger.error("Failed to save session {} tasks: {}".format(session_id, e))

    @staticmethod
    def _load_session(session_id):
        # type: (str) -> List[Dict[str, Any]]
        """Load tasks for a single session."""
        filepath = TaskManager._session_filepath(session_id)
        if not os.path.exists(filepath):
            return []
        try:
            with open(filepath, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error("Failed to load session {} tasks: {}".format(session_id, e))
            return []

    @staticmethod
    def _load_all_sessions():
        # type: () -> List[Dict[str, Any]]
        """Load tasks from all sessions."""
        if not os.path.exists(SESSIONS_DIR):
            return []

        all_tasks = []  # type: List[Dict[str, Any]]
        try:
            for name in os.listdir(SESSIONS_DIR):
                session_dir = os.path.join(SESSIONS_DIR, name)
                if os.path.isdir(session_dir):
                    all_tasks.extend(TaskManager._load_session(name))
            logger.info("Loaded %d task(s) from disk", len(all_tasks))
        except Exception as e:
            logger.error("Failed to load tasks: {}".format(e))
        return all_tasks
