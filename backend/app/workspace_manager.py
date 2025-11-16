"""Workspace manager for handling per-session directories."""
import os
import shutil
import tempfile
import uuid
from pathlib import Path
from typing import Optional
import structlog

logger = structlog.get_logger()

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

# Global workspace manager instance
workspace_manager = WorkspaceManager(
    base_dir=os.getenv("WORKSPACE_BASE_DIR", None)
)
