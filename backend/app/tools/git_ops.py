"""Git operations tool."""
import os
from pathlib import Path
from typing import Optional
import git
from git.exc import GitCommandError
import structlog

logger = structlog.get_logger()

class GitOperations:
    """Git repository operations."""

    @staticmethod
    async def clone_repository(
        url: str,
        destination: Path,
        branch: Optional[str] = None,
        credentials: Optional[dict] = None
    ) -> dict:
        """Clone a git repository.

        Args:
            url: Repository URL
            destination: Local path to clone to
            branch: Specific branch to clone
            credentials: Dict with 'username' and 'token' for authentication

        Returns:
            Dict with clone result
        """
        try:
            # Add credentials to URL if provided
            if credentials and 'username' in credentials and 'token' in credentials:
                # Parse URL and inject credentials
                if url.startswith('https://'):
                    url_parts = url[8:].split('/', 1)
                    url = f"https://{credentials['username']}:{credentials['token']}@{url_parts[0]}/{url_parts[1]}"

            # Clone repository
            if branch:
                repo = git.Repo.clone_from(url, str(destination), branch=branch)
            else:
                repo = git.Repo.clone_from(url, str(destination))

            logger.info("repository_cloned", url=url, destination=str(destination))
            return {
                "success": True,
                "path": str(destination),
                "branch": repo.active_branch.name,
                "remote": url
            }

        except GitCommandError as e:
            logger.error("clone_failed", url=url, error=str(e))
            return {"error": f"Failed to clone repository: {str(e)}"}
        except Exception as e:
            logger.error("clone_failed", url=url, error=str(e))
            return {"error": f"Failed to clone repository: {str(e)}"}

    @staticmethod
    async def git_status(repo_path: Path) -> dict:
        """Get git status for a repository.

        Args:
            repo_path: Path to git repository

        Returns:
            Dict with status information
        """
        try:
            repo = git.Repo(repo_path)

            # Get status
            changed_files = [item.a_path for item in repo.index.diff(None)]
            staged_files = [item.a_path for item in repo.index.diff('HEAD')]
            untracked_files = repo.untracked_files

            result = {
                "success": True,
                "branch": repo.active_branch.name,
                "changed_files": changed_files,
                "staged_files": staged_files,
                "untracked_files": untracked_files,
                "is_dirty": repo.is_dirty()
            }

            logger.info("git_status", repo=str(repo_path), is_dirty=result["is_dirty"])
            return result

        except Exception as e:
            logger.error("git_status_failed", repo=str(repo_path), error=str(e))
            return {"error": f"Failed to get git status: {str(e)}"}

    @staticmethod
    async def git_diff(repo_path: Path, file_path: Optional[str] = None) -> dict:
        """Get git diff.

        Args:
            repo_path: Path to git repository
            file_path: Specific file to diff (optional)

        Returns:
            Dict with diff content
        """
        try:
            repo = git.Repo(repo_path)

            if file_path:
                diff = repo.git.diff(file_path)
            else:
                diff = repo.git.diff()

            result = {
                "success": True,
                "diff": diff
            }

            logger.info("git_diff", repo=str(repo_path), file=file_path)
            return result

        except Exception as e:
            logger.error("git_diff_failed", repo=str(repo_path), error=str(e))
            return {"error": f"Failed to get git diff: {str(e)}"}

    @staticmethod
    async def git_commit(
        repo_path: Path,
        message: str,
        files: Optional[list[str]] = None
    ) -> dict:
        """Create a git commit.

        Args:
            repo_path: Path to git repository
            message: Commit message
            files: List of files to commit (None for all)

        Returns:
            Dict with commit result
        """
        try:
            repo = git.Repo(repo_path)

            # Add files
            if files:
                repo.index.add(files)
            else:
                repo.git.add(A=True)

            # Commit
            commit = repo.index.commit(message)

            result = {
                "success": True,
                "commit_hash": commit.hexsha[:8],
                "message": message,
                "files_changed": len(commit.stats.files)
            }

            logger.info("git_commit", repo=str(repo_path), hash=result["commit_hash"])
            return result

        except Exception as e:
            logger.error("git_commit_failed", repo=str(repo_path), error=str(e))
            return {"error": f"Failed to commit: {str(e)}"}

    @staticmethod
    async def git_push(repo_path: Path, remote: str = "origin", branch: Optional[str] = None) -> dict:
        """Push commits to remote.

        Args:
            repo_path: Path to git repository
            remote: Remote name (default: origin)
            branch: Branch to push (default: current branch)

        Returns:
            Dict with push result
        """
        try:
            repo = git.Repo(repo_path)

            if not branch:
                branch = repo.active_branch.name

            # Push
            origin = repo.remote(remote)
            origin.push(branch)

            result = {
                "success": True,
                "remote": remote,
                "branch": branch
            }

            logger.info("git_push", repo=str(repo_path), remote=remote, branch=branch)
            return result

        except Exception as e:
            logger.error("git_push_failed", repo=str(repo_path), error=str(e))
            return {"error": f"Failed to push: {str(e)}"}

    @staticmethod
    async def git_pull(repo_path: Path, remote: str = "origin", branch: Optional[str] = None) -> dict:
        """Pull commits from remote.

        Args:
            repo_path: Path to git repository
            remote: Remote name (default: origin)
            branch: Branch to pull (default: current branch)

        Returns:
            Dict with pull result
        """
        try:
            repo = git.Repo(repo_path)

            if not branch:
                branch = repo.active_branch.name

            # Pull
            origin = repo.remote(remote)
            origin.pull(branch)

            result = {
                "success": True,
                "remote": remote,
                "branch": branch
            }

            logger.info("git_pull", repo=str(repo_path), remote=remote, branch=branch)
            return result

        except Exception as e:
            logger.error("git_pull_failed", repo=str(repo_path), error=str(e))
            return {"error": f"Failed to pull: {str(e)}"}
