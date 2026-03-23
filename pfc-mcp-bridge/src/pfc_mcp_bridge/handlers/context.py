"""
Server Context for Handler Dependency Injection.

Provides a centralized context object containing all dependencies
that handlers need to perform their operations.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..tasks import TaskManager
    from ..execution import ScriptRunner, MainThreadExecutor


class ServerContext:
    """
    Context object providing access to server dependencies for handlers.

    This class serves as a dependency injection container, allowing handlers
    to access shared resources without tight coupling to the server class.

    Attributes:
        task_manager: Manages task lifecycle and status tracking
        script_runner: Runs PFC Python scripts via main thread queue
        main_executor: Queue-based main thread execution
        runtime_mode: Active bridge runtime mode ("gui" or "console")
    """

    def __init__(
        self,
        task_manager,  # type: TaskManager
        script_runner,  # type: ScriptRunner
        main_executor,  # type: MainThreadExecutor
        runtime_mode="unknown",  # type: str
    ):
        # type: (...) -> None
        self.task_manager = task_manager
        self.script_runner = script_runner
        self.main_executor = main_executor
        self.runtime_mode = runtime_mode
