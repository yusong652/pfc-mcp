"""
Server Context for Handler Dependency Injection.

Provides a centralized context object containing all dependencies
that handlers need to perform their operations.
"""

from typing import TYPE_CHECKING, Dict

if TYPE_CHECKING:
    from ..tasks import TaskManager
    from ..execution import ScriptRunner, MainThreadExecutor
    from ..services import UserConsoleManager


class ServerContext:
    """
    Context object providing access to server dependencies for handlers.

    This class serves as a dependency injection container, allowing handlers
    to access shared resources without tight coupling to the server class.

    Attributes:
        task_manager: Manages task lifecycle and status tracking
        script_runner: Runs PFC Python scripts via main thread queue
        main_executor: Queue-based main thread execution
        user_console_managers: Cache of UserConsoleManager per workspace
    """

    def __init__(
        self,
        task_manager,  # type: TaskManager
        script_runner,  # type: ScriptRunner
        main_executor,  # type: MainThreadExecutor
        user_console_managers,  # type: Dict[str, UserConsoleManager]
    ):
        # type: (...) -> None
        """
        Initialize server context with required dependencies.

        Args:
            task_manager: Task lifecycle manager
            script_runner: Script runner for PFC Python scripts
            main_executor: Main thread executor for queue-based execution
            user_console_managers: Dict mapping workspace paths to UserConsoleManager
        """
        self.task_manager = task_manager
        self.script_runner = script_runner
        self.main_executor = main_executor
        self.user_console_managers = user_console_managers

    def get_user_console_manager(self, workspace_path):
        # type: (str) -> UserConsoleManager
        """
        Get or create UserConsoleManager for a workspace.

        Args:
            workspace_path: Absolute path to the PFC workspace directory

        Returns:
            UserConsoleManager instance for the workspace
        """
        from ..services import UserConsoleManager

        if workspace_path not in self.user_console_managers:
            self.user_console_managers[workspace_path] = UserConsoleManager(workspace_path)
        return self.user_console_managers[workspace_path]
