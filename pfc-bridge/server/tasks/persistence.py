"""
Task Persistence - Save and load task history to/from disk.

This module provides persistent storage for task history, enabling
task tracking across server restarts.

Python 3.6 compatible implementation.
"""

import json
import os
import logging
from typing import Dict, List, Any, Optional

# Module logger
logger = logging.getLogger("PFC-Server")


class TaskPersistence:
    """
    Manage persistent storage of task data.

    Tasks are saved to JSON files organized by session:
        .nagisa/sessions/{session_id}/tasks.json

    Each session has its own directory for clean isolation.
    On server restart, historical tasks are loaded as read-only records.
    """

    def __init__(self, data_dir=".nagisa"):
        # type: (str,) -> None
        """
        Initialize persistence manager.

        Args:
            data_dir: Base directory for task data (hidden directory in workspace)
        """
        self.data_dir = data_dir
        self.sessions_dir = os.path.join(data_dir, "sessions")
        self.filename = "tasks.json"  # Consistent filename per session

        # Ensure base directories exist
        self._ensure_data_dir()

        logger.info("TaskPersistence initialized (sessions_dir=%s)", self.sessions_dir)

    def _ensure_data_dir(self):
        # type: () -> None
        """Create base data directories if they don't exist."""
        if not os.path.exists(self.sessions_dir):
            os.makedirs(self.sessions_dir)
            logger.info("Created sessions directory: {}".format(self.sessions_dir))

    def _get_session_filepath(self, session_id):
        # type: (str) -> str
        """
        Get filepath for a session's tasks.json.

        Args:
            session_id: Session identifier

        Returns:
            str: Full path to session's tasks.json
        """
        session_dir = os.path.join(self.sessions_dir, session_id)
        # Ensure session directory exists
        if not os.path.exists(session_dir):
            os.makedirs(session_dir)
        return os.path.join(session_dir, self.filename)

    def serialize_task(self, task):
        # type: (Any) -> Dict[str, Any]
        """
        Serialize a Task object to JSON-compatible dict.

        Args:
            task: Task object (ScriptTask)

        Returns:
            Dict with serializable task data
        """
        # Common fields
        task_data = {
            "task_id": task.task_id,
            "session_id": task.session_id,  # Add session ID
            "task_type": task.task_type,
            "source": getattr(task, "source", "agent"),  # Task source (default: agent)
            "description": task.description,
            "status": task.status,
            "start_time": task.start_time,
            "end_time": task.end_time,
            "notified": getattr(task, "notified", False)  # Notification status (default: False)
        }

        # Script task fields
        task_data["script_name"] = task.script_name
        task_data["entry_script"] = task.entry_script  # Unified field name
        task_data["git_commit"] = getattr(task, "git_commit", None)  # Git version snapshot
        # Save log file path (output is read from file on demand)
        task_data["log_path"] = getattr(task, "log_path", None)
        # Save error message (for failed tasks)
        task_data["error"] = getattr(task, "error", None)

        return task_data

    def save_tasks(self, tasks):
        # type: (Dict[str, Any]) -> bool
        """
        Save all tasks to disk, organized by session.

        Args:
            tasks: Dict of {task_id: Task} from TaskManager

        Returns:
            bool: True if all sessions saved successfully, False otherwise
        """
        try:
            # Group tasks by session_id
            tasks_by_session = {}  # type: Dict[str, List[Dict[str, Any]]]
            for task in tasks.values():
                session_id = task.session_id
                if session_id not in tasks_by_session:
                    tasks_by_session[session_id] = []
                tasks_by_session[session_id].append(self.serialize_task(task))

            # Save each session's tasks to its own file
            all_success = True
            for session_id, session_tasks in tasks_by_session.items():
                if not self._save_session_tasks(session_id, session_tasks):
                    all_success = False

            return all_success

        except Exception as e:
            logger.error("Failed to save tasks: {}".format(e))
            return False

    def _save_session_tasks(self, session_id, tasks_data):
        # type: (str, List[Dict[str, Any]]) -> bool
        """
        Save tasks for a specific session.

        Args:
            session_id: Session identifier
            tasks_data: List of serialized task dicts

        Returns:
            bool: True if save successful, False otherwise
        """
        try:
            filepath = self._get_session_filepath(session_id)

            # Atomic write: write to temp file, then rename
            temp_filepath = filepath + ".tmp"
            with open(temp_filepath, 'w') as f:
                json.dump(tasks_data, f, indent=2)

            # Atomic rename (overwrites existing file)
            os.replace(temp_filepath, filepath)

            logger.debug("Saved {} task(s) for session {} to {}".format(
                len(tasks_data), session_id, filepath
            ))
            return True

        except Exception as e:
            logger.error("Failed to save session {} tasks: {}".format(session_id, e))
            return False

    def load_tasks(self, session_id=None):
        # type: (Optional[str]) -> List[Dict[str, Any]]
        """
        Load task history from disk.

        Args:
            session_id: Optional session ID to load. If None, loads all sessions.

        Returns:
            List of task data dicts (empty list if no history found or error)
        """
        if session_id:
            # Load specific session
            return self._load_session_tasks(session_id)
        else:
            # Load all sessions
            return self._load_all_sessions()

    def _load_session_tasks(self, session_id):
        # type: (str) -> List[Dict[str, Any]]
        """
        Load tasks for a specific session.

        Args:
            session_id: Session identifier

        Returns:
            List of task data dicts for this session
        """
        filepath = self._get_session_filepath(session_id)

        if not os.path.exists(filepath):
            logger.debug("No task history found for session {}".format(session_id))
            return []

        try:
            with open(filepath, 'r') as f:
                tasks_data = json.load(f)

            logger.info(
                "Loaded %d task(s) for session %s",
                len(tasks_data), session_id
            )
            return tasks_data

        except Exception as e:
            logger.error("Failed to load session {} tasks: {}".format(session_id, e))
            return []

    def _load_all_sessions(self):
        # type: () -> List[Dict[str, Any]]
        """
        Load tasks from all sessions.

        Returns:
            List of all task data dicts across all sessions
        """
        if not os.path.exists(self.sessions_dir):
            logger.info("No existing task history found")
            return []

        all_tasks = []  # type: List[Dict[str, Any]]

        try:
            # Iterate through all session directories
            for session_id in os.listdir(self.sessions_dir):
                session_dir = os.path.join(self.sessions_dir, session_id)
                if not os.path.isdir(session_dir):
                    continue

                # Load this session's tasks
                session_tasks = self._load_session_tasks(session_id)
                all_tasks.extend(session_tasks)

            logger.info(
                "Loaded %d task(s) from %d session(s)",
                len(all_tasks), len(os.listdir(self.sessions_dir))
            )
            return all_tasks

        except Exception as e:
            logger.error("Failed to load tasks from all sessions: {}".format(e))
            return []

    def restore_task_as_historical(self, task_data):
        # type: (Dict[str, Any]) -> Optional[Any]
        """
        Restore a task from persisted data as a historical (read-only) record.

        Running tasks are marked as 'failed' since they can't be resumed.

        Args:
            task_data: Serialized task data dict

        Returns:
            HistoricalTask object or None if restoration failed
        """
        try:
            # Mark running tasks as failed (can't resume)
            if task_data.get("status") == "running":
                task_data["status"] = "failed"
                logger.warning(
                    "Marked previously running task {} as failed (cannot resume)".format(
                        task_data.get("task_id")
                    )
                )

            # Create historical task wrapper
            return HistoricalTask(task_data)

        except Exception as e:
            logger.error("Failed to restore task {}: {}".format(
                task_data.get("task_id"), e
            ))
            return None


class HistoricalTask:
    """
    Read-only wrapper for historical tasks loaded from disk.

    Implements same interface as Task for compatibility with TaskManager,
    but without Future or output buffer (no active execution).
    Output is read from log file on demand.
    """

    def __init__(self, task_data):
        # type: (Dict[str, Any]) -> None
        """
        Initialize from serialized data.

        Args:
            task_data: Dict with task fields from persistence
        """
        # Restore common fields
        self.task_id = task_data["task_id"]
        self.session_id = task_data.get("session_id", "default")  # Session ID with default fallback
        self.task_type = task_data["task_type"]
        self.source = task_data.get("source", "agent")  # Task source (default: agent)
        self.description = task_data["description"]
        self.status = task_data["status"]
        self.start_time = task_data["start_time"]
        self.end_time = task_data.get("end_time")  # Optional
        self.notified = task_data.get("notified", False)  # Notification status (default: False)

        # Restore script task fields
        self.script_name = task_data.get("script_name", "")
        # Support both new (entry_script) and old (script_path) field names
        self.entry_script = task_data.get("entry_script") or task_data.get("script_path") or ""  # type: str
        self.git_commit = task_data.get("git_commit")  # Git version snapshot
        self.log_path = task_data.get("log_path")  # Path to output log file
        # Backward compatibility: support old format with inline output
        self._output_snapshot = task_data.get("output", "")
        self.error = task_data.get("error")  # Error message (for failed tasks)

        # No Future or output_buffer for historical tasks
        self.future = None
        self.output_buffer = None

    def get_elapsed_time(self):
        # type: () -> float
        """Calculate elapsed time (historical)."""
        if self.end_time is not None:
            return self.end_time - self.start_time
        # For incomplete tasks (shouldn't happen after restoration)
        return 0.0

    def get_current_output(self):
        # type: () -> Optional[str]
        """
        Read output from log file.

        Falls back to inline snapshot for backward compatibility with old format.
        """
        # Try reading from log file first
        if self.log_path:
            try:
                import os
                if os.path.exists(self.log_path):
                    with open(self.log_path, 'r', encoding='utf-8') as f:
                        return f.read()
            except Exception as e:
                logger.warning("Failed to read log file {}: {}".format(self.log_path, e))

        # Fallback to inline snapshot (backward compatibility)
        return self._output_snapshot if self._output_snapshot else None

    def get_status_response(self):
        # type: () -> Dict[str, Any]
        """Get historical task status response."""
        elapsed_time = self.get_elapsed_time()
        output = self.get_current_output()

        if self.status == "completed":
            message = "[Historical] Script completed: {}\nElapsed time: {:.2f}s".format(
                self.script_name, elapsed_time
            )
            if output:
                message += "\n\n=== Script Output (Snapshot) ===\n{}".format(output)

            return {
                "status": "success",
                "message": message,
                "data": {
                    "task_id": self.task_id,
                    "task_type": self.task_type,
                    "source": self.source,
                    "script_name": self.script_name,
                    "entry_script": self.entry_script,
                    "description": self.description,
                    "elapsed_time": elapsed_time,
                    "start_time": self.start_time,
                    "end_time": self.end_time,
                    "output": output if output else "",
                    "git_commit": self.git_commit,
                    "historical": True
                }
            }
        elif self.status == "interrupted":
            message = "[Historical] Script interrupted: {}\nElapsed time: {:.2f}s".format(
                self.script_name, elapsed_time
            )
            if output:
                message += "\n\n=== Partial Output (Snapshot) ===\n{}".format(output)

            return {
                "status": "interrupted",
                "message": message,
                "data": {
                    "task_id": self.task_id,
                    "task_type": self.task_type,
                    "source": self.source,
                    "script_name": self.script_name,
                    "entry_script": self.entry_script,
                    "description": self.description,
                    "elapsed_time": elapsed_time,
                    "start_time": self.start_time,
                    "end_time": self.end_time,
                    "output": output if output else "",
                    "git_commit": self.git_commit,
                    "historical": True
                }
            }
        else:  # failed
            error_msg = self.error or "Task execution failed"
            message = "[Historical] Script failed: {}\nElapsed time: {:.2f}s\nError: {}".format(
                self.script_name, elapsed_time, error_msg
            )
            if output:
                message += "\n\n=== Partial Output (Snapshot) ===\n{}".format(output)

            return {
                "status": "error",
                "message": message,
                "data": {
                    "task_id": self.task_id,
                    "task_type": self.task_type,
                    "source": self.source,
                    "script_name": self.script_name,
                    "entry_script": self.entry_script,
                    "description": self.description,
                    "elapsed_time": elapsed_time,
                    "start_time": self.start_time,
                    "end_time": self.end_time,
                    "output": output if output else "",
                    "error": error_msg,
                    "git_commit": self.git_commit,
                    "historical": True
                }
            }

    def get_task_info(self):
        # type: () -> Dict[str, Any]
        """Get task summary for listing (historical)."""
        info = {
            "task_id": self.task_id,
            "session_id": self.session_id,
            "task_type": self.task_type,
            "source": self.source,  # Task source: "agent" or "user_console"
            "description": self.description,
            "status": self.status,
            "elapsed_time": self.get_elapsed_time(),
            "start_time": self.start_time,
            "notified": self.notified,
            "historical": True,
            # Script task fields
            "name": self.script_name,
            "entry_script": self.entry_script,
            "git_commit": self.git_commit
        }

        # Add end_time if available
        if self.end_time is not None:
            info["end_time"] = self.end_time

        # Add error for failed tasks
        if self.status == "failed" and self.error:
            info["error"] = self.error

        return info
