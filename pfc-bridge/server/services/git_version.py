"""
Git Version Manager - Manages execution snapshots on pfc-executions branch.

This module provides git-based version tracking for PFC script executions,
creating commits on a dedicated branch without affecting the working directory.

Python 3.6 compatible implementation.

TODO: Consider auto-initializing git repository on pfc-bridge startup
      if the PFC project directory is not yet a git repository.
"""

import logging
import os
import subprocess
from typing import Dict, Optional, Any

# Module logger
logger = logging.getLogger("PFC-Server")

# Constants
EXECUTION_BRANCH = "pfc-executions"


class GitVersionManager:
    """
    Manage git-based version snapshots for PFC executions.

    Creates commits on a dedicated 'pfc-executions' branch using git commit-tree,
    without switching branches or affecting the current working directory.
    """

    def __init__(self, workspace_dir=None):
        # type: (Optional[str]) -> None
        """
        Initialize GitVersionManager.

        Args:
            workspace_dir: Git repository root directory. If None, uses current directory.
        """
        self.workspace_dir = workspace_dir or os.getcwd()

    def _run_git(self, args, check=True):
        # type: (list, bool) -> subprocess.CompletedProcess
        """
        Run a git command in the workspace directory.

        Args:
            args: List of git command arguments (without 'git' prefix)
            check: If True, raise exception on non-zero exit code

        Returns:
            CompletedProcess with stdout, stderr, returncode
        """
        cmd = ["git"] + args
        try:
            # Python 3.6 compatible: use run with capture_output equivalent
            # Use CREATE_NO_WINDOW on Windows to hide CMD popup
            kwargs = {
                "cwd": self.workspace_dir,
                "stdout": subprocess.PIPE,
                "stderr": subprocess.PIPE,
                "universal_newlines": True  # Python 3.6 compatible (text=True in 3.7+)
            }
            # Windows: hide console window
            # CREATE_NO_WINDOW = 0x08000000 (Python 3.7+ has subprocess.CREATE_NO_WINDOW)
            if os.name == 'nt':
                CREATE_NO_WINDOW = 0x08000000
                kwargs["creationflags"] = CREATE_NO_WINDOW

            result = subprocess.run(cmd, **kwargs)
            if check and result.returncode != 0:
                logger.error("Git command failed: {} -> {}".format(" ".join(cmd), result.stderr))
            return result
        except Exception as e:
            logger.error("Git command error: {} -> {}".format(" ".join(cmd), str(e)))
            raise

    def is_git_available(self):
        # type: () -> bool
        """Check if git is available and we're in a git repository."""
        try:
            result = self._run_git(["rev-parse", "--git-dir"], check=False)
            return result.returncode == 0
        except Exception:
            return False

    def diagnose_git_status(self):
        # type: () -> Dict[str, Any]
        """
        Diagnose git availability and provide actionable guidance.

        Returns:
            Dict with:
                - available: bool - Whether git is fully functional
                - issue: Optional[str] - Issue type if not available
                - message: str - Human-readable status message
                - action: Optional[str] - Suggested action to fix
        """
        try:
            result = self._run_git(["rev-parse", "--git-dir"], check=False)

            if result.returncode == 0:
                return {
                    "available": True,
                    "issue": None,
                    "message": "Git repository detected",
                    "action": None
                }

            stderr = result.stderr.strip()

            # Check for common issues
            if "dubious ownership" in stderr:
                return {
                    "available": False,
                    "issue": "ownership",
                    "message": "Git detected dubious ownership (directory owned by different user)",
                    "action": "git config --global --add safe.directory {}".format(self.workspace_dir)
                }
            elif "not a git repository" in stderr:
                return {
                    "available": False,
                    "issue": "not_initialized",
                    "message": "Directory is not a git repository",
                    "action": "git init"
                }
            else:
                return {
                    "available": False,
                    "issue": "unknown",
                    "message": "Git error: {}".format(stderr),
                    "action": None
                }

        except FileNotFoundError:
            return {
                "available": False,
                "issue": "not_installed",
                "message": "Git is not installed or not in PATH",
                "action": "Install git and ensure it's in PATH"
            }
        except Exception as e:
            return {
                "available": False,
                "issue": "error",
                "message": "Git check failed: {}".format(str(e)),
                "action": None
            }

    def check_git_state(self):
        # type: () -> Dict[str, Any]
        """
        Check git repository state for potential issues.

        Returns:
            Dict with:
                - ok: bool - True if safe to proceed
                - error: Optional[str] - Error message if not ok
                - current_branch: str - Current branch name
        """
        if not self.is_git_available():
            return {
                "ok": False,
                "error": "Not in a git repository. Run 'git init' to initialize.",
                "current_branch": None
            }

        # Check for rebase/merge in progress
        git_dir = self._run_git(["rev-parse", "--git-dir"]).stdout.strip()
        git_dir_path = os.path.join(self.workspace_dir, git_dir)

        if os.path.exists(os.path.join(git_dir_path, "rebase-merge")) or \
           os.path.exists(os.path.join(git_dir_path, "rebase-apply")):
            return {
                "ok": False,
                "error": "Git rebase in progress. Please complete or abort the rebase first.",
                "current_branch": None
            }

        if os.path.exists(os.path.join(git_dir_path, "MERGE_HEAD")):
            return {
                "ok": False,
                "error": "Git merge in progress. Please complete or abort the merge first.",
                "current_branch": None
            }

        # Get current branch
        result = self._run_git(["branch", "--show-current"], check=False)
        current_branch = result.stdout.strip() if result.returncode == 0 else None

        # Check if on execution branch (not allowed)
        if current_branch == EXECUTION_BRANCH:
            return {
                "ok": False,
                "error": "Cannot execute from '{}' branch. Please switch to main or a feature branch.".format(EXECUTION_BRANCH),
                "current_branch": current_branch
            }

        return {
            "ok": True,
            "error": None,
            "current_branch": current_branch
        }

    def ensure_execution_branch_exists(self):
        # type: () -> bool
        """
        Ensure the pfc-executions branch exists.

        Creates an orphan branch if it doesn't exist.

        Returns:
            True if branch exists or was created, False on error
        """
        # Check if branch exists
        result = self._run_git(["rev-parse", "--verify", EXECUTION_BRANCH], check=False)

        if result.returncode == 0:
            # Branch already exists
            return True

        # Create orphan branch with initial empty commit
        # We need to do this carefully to not affect current working directory

        try:
            # Get current branch to restore later
            current_result = self._run_git(["branch", "--show-current"], check=False)
            current_branch = current_result.stdout.strip()

            if not current_branch:
                # Detached HEAD state - get commit hash instead
                head_result = self._run_git(["rev-parse", "HEAD"], check=False)
                current_branch = head_result.stdout.strip() if head_result.returncode == 0 else None

            if not current_branch:
                logger.error("Cannot determine current branch/commit - aborting branch creation")
                return False

            # Stash any changes
            stash_result = self._run_git(["stash", "push", "-m", "pfc-exec-temp"], check=False)
            stash_created = "No local changes" not in stash_result.stdout

            branch_created = False
            try:
                # Create orphan branch
                self._run_git(["checkout", "--orphan", EXECUTION_BRANCH])

                # Reset to remove staged files
                self._run_git(["reset", "--hard"], check=False)

                # Create initial empty commit
                self._run_git([
                    "commit", "--allow-empty",
                    "-m", "Initialize PFC execution tracking\n\nThis branch stores snapshots of code state at each PFC task execution."
                ])

                branch_created = True

            finally:
                # Always restore original branch - this is CRITICAL
                if current_branch:
                    checkout_result = self._run_git(["checkout", current_branch], check=False)
                    if checkout_result.returncode != 0:
                        # Checkout failed - try force checkout
                        logger.warning("Normal checkout failed, trying force checkout: {}".format(
                            checkout_result.stderr.strip()
                        ))
                        force_result = self._run_git(["checkout", "-f", current_branch], check=False)
                        if force_result.returncode != 0:
                            logger.error(
                                "CRITICAL: Failed to restore original branch '{}'. "
                                "Repository may be left on '{}' branch. "
                                "Please manually run: git checkout {}".format(
                                    current_branch, EXECUTION_BRANCH, current_branch
                                )
                            )
                            # Don't return False here - branch was created successfully
                            # User just needs to manually switch back

                # Restore stashed changes
                if stash_created:
                    self._run_git(["stash", "pop"], check=False)

            return branch_created

        except Exception as e:
            logger.error("Failed to create execution branch: {}".format(e))
            return False

    def create_execution_commit(self, task_id, description, entry_script=None):
        # type: (str, str, Optional[str]) -> Optional[str]
        """
        Create an execution snapshot commit on pfc-executions branch.

        Uses git write-tree and commit-tree to create commit without switching branches.

        Args:
            task_id: Task identifier for commit message
            description: Task description for commit message
            entry_script: Optional entry script path for commit message

        Returns:
            Commit hash if successful, None on error
        """
        # Check git state
        state = self.check_git_state()
        if not state["ok"]:
            logger.warning("Git state check failed: {}".format(state["error"]))
            return None

        # Ensure execution branch exists
        if not self.ensure_execution_branch_exists():
            logger.warning("Failed to ensure execution branch exists")
            return None

        try:
            # 1. Stage all files (including untracked) to create tree
            self._run_git(["add", "-A"])

            # 2. Create tree object from current index
            tree_result = self._run_git(["write-tree"])
            tree_hash = tree_result.stdout.strip()

            # 3. Reset index to not affect working directory
            self._run_git(["reset"], check=False)

            # 4. Get parent commit from execution branch
            parent_result = self._run_git(["rev-parse", EXECUTION_BRANCH])
            parent_hash = parent_result.stdout.strip()

            # 5. Build commit message
            entry_info = "Entry: {}".format(entry_script) if entry_script else ""
            commit_message = "[PFC-EXEC] {}: {}\n\n{}\nTask ID: {}".format(
                task_id[:8], description, entry_info, task_id
            )

            # 6. Create commit object directly (without switching branches)
            commit_result = self._run_git([
                "commit-tree", tree_hash,
                "-p", parent_hash,
                "-m", commit_message
            ])
            new_commit = commit_result.stdout.strip()

            # 7. Update execution branch ref to point to new commit
            self._run_git(["update-ref", "refs/heads/{}".format(EXECUTION_BRANCH), new_commit])


            return new_commit

        except Exception as e:
            logger.error("Failed to create execution commit: {}".format(e))
            # Try to reset index on failure
            self._run_git(["reset"], check=False)
            return None

    def get_current_commit(self):
        # type: () -> Optional[str]
        """Get current HEAD commit hash."""
        if not self.is_git_available():
            return None

        result = self._run_git(["rev-parse", "HEAD"], check=False)
        if result.returncode == 0:
            return result.stdout.strip()
        return None

    def is_dirty(self):
        # type: () -> bool
        """Check if working directory has uncommitted changes."""
        if not self.is_git_available():
            return False

        result = self._run_git(["status", "--porcelain"], check=False)
        return bool(result.stdout.strip())

    def reset_execution_branch(self):
        # type: () -> Dict[str, Any]
        """
        Delete and recreate the pfc-executions branch to clear execution history.

        This removes all execution snapshots, providing a clean slate for testing.

        Returns:
            Dict with:
                - success: bool
                - message: str
                - deleted_commits: int (approximate, if available)
        """
        if not self.is_git_available():
            return {
                "success": False,
                "message": "Git not available",
                "deleted_commits": 0
            }

        try:
            # Check if branch exists
            result = self._run_git(["rev-parse", "--verify", EXECUTION_BRANCH], check=False)
            if result.returncode != 0:
                return {
                    "success": True,
                    "message": "Branch '{}' does not exist, nothing to reset".format(EXECUTION_BRANCH),
                    "deleted_commits": 0
                }

            # Count commits on the branch (approximate)
            count_result = self._run_git([
                "rev-list", "--count", EXECUTION_BRANCH
            ], check=False)
            commit_count = int(count_result.stdout.strip()) if count_result.returncode == 0 else 0

            # Delete the branch
            delete_result = self._run_git(["branch", "-D", EXECUTION_BRANCH], check=False)
            if delete_result.returncode != 0:
                return {
                    "success": False,
                    "message": "Failed to delete branch: {}".format(delete_result.stderr.strip()),
                    "deleted_commits": 0
                }

            logger.info("Deleted '%s' branch (%d commits)", EXECUTION_BRANCH, commit_count)

            return {
                "success": True,
                "message": "Reset '{}' branch ({} execution snapshots removed)".format(
                    EXECUTION_BRANCH, commit_count
                ),
                "deleted_commits": commit_count
            }

        except Exception as e:
            logger.error("Failed to reset execution branch: {}".format(e))
            return {
                "success": False,
                "message": "Error: {}".format(str(e)),
                "deleted_commits": 0
            }


# Cache for git managers per repository root
_managers = {}  # type: Dict[str, GitVersionManager]


def find_git_root(start_path):
    # type: (str) -> Optional[str]
    """
    Find the git repository root directory starting from a given path.

    Walks up the directory tree to find the nearest .git directory.

    Args:
        start_path: Starting file or directory path

    Returns:
        Absolute path to git repository root, or None if not found
    """
    # Normalize and get absolute path
    current = os.path.abspath(start_path)

    # If start_path is a file, start from its directory
    if os.path.isfile(current):
        current = os.path.dirname(current)

    # Walk up the directory tree
    while current:
        git_dir = os.path.join(current, ".git")
        if os.path.exists(git_dir):
            return current

        parent = os.path.dirname(current)
        if parent == current:
            # Reached filesystem root
            break
        current = parent

    return None


def get_git_manager(workspace_dir=None):
    # type: (Optional[str]) -> GitVersionManager
    """
    Get or create a GitVersionManager for the specified workspace.

    Uses a cache keyed by resolved git repository root to support
    multiple projects with different git repositories.

    Args:
        workspace_dir: Git repository root directory, or a path within a git repository.
                       If a file or subdirectory path is provided, the git root will be
                       automatically discovered. If None, uses os.getcwd().

    Returns:
        GitVersionManager instance for the resolved repository root
    """
    global _managers

    # Determine the starting path
    start_path = workspace_dir or os.getcwd()

    # Find the actual git root
    git_root = find_git_root(start_path)

    # Use git_root if found, otherwise fall back to provided path or cwd
    resolved_dir = git_root or os.path.abspath(start_path)

    # Get or create manager for this repository
    if resolved_dir not in _managers:
        _managers[resolved_dir] = GitVersionManager(resolved_dir)

    return _managers[resolved_dir]
