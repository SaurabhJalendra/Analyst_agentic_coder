"""Workspace manager for handling per-session directories."""
import os
import shutil
import tempfile
import uuid
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import structlog
import git

logger = structlog.get_logger()

# Global registry for active Claude Code instances
# session_id -> ClaudeCodeService instance
_active_claude_instances: Dict[str, Any] = {}

class WorkspaceManager:
    """Manages session-specific workspaces."""

    def __init__(self, base_dir: Optional[str] = None):
        """Initialize workspace manager.

        Args:
            base_dir: Base directory for workspaces. If None, uses system temp.
        """
        if base_dir:
            self.base_dir = Path(base_dir)
            self.base_dir.mkdir(parents=True, exist_ok=True)
        else:
            self.base_dir = Path(tempfile.gettempdir()) / "analyst_coder_workspaces"
            self.base_dir.mkdir(parents=True, exist_ok=True)

        logger.info("workspace_manager_initialized", base_dir=str(self.base_dir))

    def create_session_workspace(self, session_id: str) -> Path:
        """Create a new workspace for a session.

        Args:
            session_id: Unique session identifier

        Returns:
            Path to the session workspace
        """
        workspace_path = self.base_dir / session_id
        workspace_path.mkdir(parents=True, exist_ok=True)
        logger.info("session_workspace_created", session_id=session_id, path=str(workspace_path))
        return workspace_path

    def get_workspace_path(self, session_id: str) -> Optional[Path]:
        """Get workspace path for a session.

        Args:
            session_id: Session identifier

        Returns:
            Path if workspace exists, None otherwise
        """
        workspace_path = self.base_dir / session_id
        if workspace_path.exists():
            return workspace_path
        return None

    def cleanup_workspace(self, session_id: str) -> bool:
        """Clean up workspace for a session.

        Args:
            session_id: Session identifier

        Returns:
            True if cleaned up successfully
        """
        workspace_path = self.base_dir / session_id
        if workspace_path.exists():
            try:
                shutil.rmtree(workspace_path)
                logger.info("workspace_cleaned_up", session_id=session_id)
                return True
            except Exception as e:
                logger.error("workspace_cleanup_failed", session_id=session_id, error=str(e))
                return False
        return False

    def list_directory(self, path: Path) -> list[dict]:
        """List contents of a directory.

        Args:
            path: Directory path to list

        Returns:
            List of file/directory information dicts
        """
        try:
            items = []
            for item in path.iterdir():
                items.append({
                    "name": item.name,
                    "path": str(item),
                    "is_dir": item.is_dir(),
                    "size": item.stat().st_size if item.is_file() else 0,
                })
            return sorted(items, key=lambda x: (not x["is_dir"], x["name"]))
        except Exception as e:
            logger.error("directory_list_failed", path=str(path), error=str(e))
            return []

    def is_git_repo(self, path: Path) -> bool:
        """Check if a path is a git repository.

        Args:
            path: Path to check

        Returns:
            True if path is a git repo
        """
        return (path / ".git").exists()

    def get_git_context(self, path: Path) -> Dict[str, Any]:
        """Get comprehensive git repository context.

        Args:
            path: Path to git repository

        Returns:
            Dict with git repository information including:
            - is_git_repo: bool
            - current_branch: str (if applicable)
            - is_dirty: bool (uncommitted changes)
            - remote_url: str (if remote exists)
            - untracked_files_count: int
            - modified_files_count: int
            - staged_files_count: int
            - recent_commits: list of dicts
        """
        context = {"is_git_repo": False}

        if not self.is_git_repo(path):
            return context

        try:
            repo = git.Repo(path)
            context["is_git_repo"] = True

            # Get current branch
            try:
                context["current_branch"] = repo.active_branch.name
            except Exception:
                context["current_branch"] = "detached HEAD"

            # Check if there are uncommitted changes
            context["is_dirty"] = repo.is_dirty()

            # Get remote URL
            try:
                if repo.remotes:
                    context["remote_url"] = repo.remotes.origin.url
                else:
                    context["remote_url"] = None
            except Exception:
                context["remote_url"] = None

            # Count untracked, modified, and staged files
            context["untracked_files_count"] = len(repo.untracked_files)

            # Modified files (not staged)
            modified_files = [item.a_path for item in repo.index.diff(None)]
            context["modified_files_count"] = len(modified_files)

            # Staged files
            staged_files = [item.a_path for item in repo.index.diff("HEAD")]
            context["staged_files_count"] = len(staged_files)

            # Get recent commits (last 3)
            context["recent_commits"] = []
            try:
                for commit in list(repo.iter_commits(max_count=3)):
                    context["recent_commits"].append({
                        "hash": commit.hexsha[:8],
                        "message": commit.message.strip().split('\n')[0][:60],
                        "author": commit.author.name
                    })
            except Exception:
                pass

            logger.info("git_context_retrieved", path=str(path), branch=context.get("current_branch"))
            return context

        except Exception as e:
            logger.error("git_context_failed", path=str(path), error=str(e))
            return {"is_git_repo": False, "error": str(e)}

    def cleanup_old_workspaces(self, max_age_days: int = 7) -> Dict[str, int]:
        """Clean up workspaces older than specified days.

        Args:
            max_age_days: Maximum age in days before cleanup

        Returns:
            Dict with cleanup statistics
        """
        try:
            cutoff_time = datetime.now() - timedelta(days=max_age_days)
            cleaned = 0
            failed = 0
            total_size = 0

            if not self.base_dir.exists():
                return {"cleaned": 0, "failed": 0, "total_size_mb": 0}

            for workspace_dir in self.base_dir.iterdir():
                if not workspace_dir.is_dir():
                    continue

                try:
                    # Get last modified time
                    mtime = datetime.fromtimestamp(workspace_dir.stat().st_mtime)

                    if mtime < cutoff_time:
                        # Calculate size before deletion
                        size = sum(f.stat().st_size for f in workspace_dir.rglob('*') if f.is_file())
                        total_size += size

                        # Delete old workspace
                        shutil.rmtree(workspace_dir)
                        cleaned += 1
                        logger.info(
                            "workspace_cleaned",
                            path=str(workspace_dir),
                            age_days=(datetime.now() - mtime).days,
                            size_mb=size / (1024 * 1024)
                        )
                except Exception as e:
                    failed += 1
                    logger.error("workspace_cleanup_failed", path=str(workspace_dir), error=str(e))

            result = {
                "cleaned": cleaned,
                "failed": failed,
                "total_size_mb": round(total_size / (1024 * 1024), 2)
            }

            if cleaned > 0:
                logger.info("workspace_cleanup_complete", **result)

            return result

        except Exception as e:
            logger.error("cleanup_old_workspaces_failed", error=str(e))
            return {"cleaned": 0, "failed": 0, "total_size_mb": 0, "error": str(e)}

    def get_workspace_stats(self) -> Dict[str, Any]:
        """Get statistics about all workspaces.

        Returns:
            Dict with workspace statistics
        """
        try:
            if not self.base_dir.exists():
                return {"total_workspaces": 0, "total_size_mb": 0}

            workspaces = [d for d in self.base_dir.iterdir() if d.is_dir()]
            total_size = 0

            for workspace in workspaces:
                try:
                    total_size += sum(f.stat().st_size for f in workspace.rglob('*') if f.is_file())
                except Exception:
                    pass

            return {
                "total_workspaces": len(workspaces),
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "base_dir": str(self.base_dir)
            }

        except Exception as e:
            logger.error("get_workspace_stats_failed", error=str(e))
            return {"total_workspaces": 0, "total_size_mb": 0, "error": str(e)}

# Global workspace manager instance
workspace_manager = WorkspaceManager(
    base_dir=os.getenv("WORKSPACE_BASE_DIR", None)
)


async def get_claude_instance(session_id: str, workspace_path: str):
    """
    Get or create Claude Code instance for a session

    One instance per session - persistent across multiple messages

    Args:
        session_id: Unique session identifier
        workspace_path: Path to workspace directory

    Returns:
        ClaudeCodeService instance for this session
    """
    from .claude_code_service import ClaudeCodeService

    if session_id not in _active_claude_instances:
        logger.info(
            "Creating new Claude Code instance",
            session_id=session_id,
            workspace=workspace_path
        )

        # Create new instance
        service = ClaudeCodeService(workspace_path, session_id)

        # Start the process
        await service.start()

        # Register in global registry
        _active_claude_instances[session_id] = service

        logger.info(
            "Claude Code instance registered",
            session_id=session_id,
            total_instances=len(_active_claude_instances)
        )
    else:
        service = _active_claude_instances[session_id]

        # Check if process is still alive, restart if needed
        await service.restart_if_needed()

    return _active_claude_instances[session_id]


async def cleanup_claude_instance(session_id: str):
    """
    Stop and remove Claude Code instance for a session

    Called when session ends or needs cleanup

    Args:
        session_id: Session identifier
    """
    if session_id in _active_claude_instances:
        logger.info(
            "Cleaning up Claude Code instance",
            session_id=session_id
        )

        service = _active_claude_instances[session_id]

        # Stop the Claude Code process
        await service.stop()

        # Remove from registry
        del _active_claude_instances[session_id]

        logger.info(
            "Claude Code instance cleaned up",
            session_id=session_id,
            remaining_instances=len(_active_claude_instances)
        )


async def cleanup_all_claude_instances():
    """
    Stop all active Claude Code instances

    Called on server shutdown
    """
    logger.info(
        "Cleaning up all Claude Code instances",
        count=len(_active_claude_instances)
    )

    session_ids = list(_active_claude_instances.keys())

    for session_id in session_ids:
        try:
            await cleanup_claude_instance(session_id)
        except Exception as e:
            logger.error(
                "Failed to cleanup instance",
                session_id=session_id,
                error=str(e)
            )

    logger.info("All Claude Code instances cleaned up")


def get_active_instances_count() -> int:
    """Get count of active Claude Code instances"""
    return len(_active_claude_instances)


def get_active_sessions() -> list[str]:
    """Get list of session IDs with active Claude Code instances"""
    return list(_active_claude_instances.keys())
