"""Lightweight task tracking for MCP-side submitted jobs."""

from dataclasses import dataclass
from datetime import datetime
from threading import Lock
from typing import Dict, Optional
import uuid


@dataclass
class TaskRecord:
    task_id: str
    source: str
    entry_script: str
    description: str
    created_at: datetime
    status: str = "submitted"


class BridgeTaskManager:
    """Minimal in-memory task registry for generated task IDs."""

    def __init__(self) -> None:
        self._tasks: Dict[str, TaskRecord] = {}
        self._lock = Lock()

    def create_task(self, source: str, entry_script: str, description: str) -> str:
        task_id = uuid.uuid4().hex[:6]
        with self._lock:
            while task_id in self._tasks:
                task_id = uuid.uuid4().hex[:6]
            self._tasks[task_id] = TaskRecord(
                task_id=task_id,
                source=source,
                entry_script=entry_script,
                description=description,
                created_at=datetime.now(),
            )
        return task_id

    def update_status(self, task_id: str, status: str) -> None:
        with self._lock:
            task = self._tasks.get(task_id)
            if task is not None:
                task.status = status

    def get_task(self, task_id: str) -> Optional[TaskRecord]:
        with self._lock:
            return self._tasks.get(task_id)


_task_manager: Optional[BridgeTaskManager] = None


def get_task_manager() -> BridgeTaskManager:
    global _task_manager
    if _task_manager is None:
        _task_manager = BridgeTaskManager()
    return _task_manager
