"""
Simple Git utilities for repository cloning

Replaces the complex tool executor for basic git operations
"""

import subprocess
from pathlib import Path
from typing import Dict, Any, Optional
import structlog

logger = structlog.get_logger(__name__)


async def clone_repository(
    url: str,
    destination: Path,
    branch: Optional[str] = None,
    credentials: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Clone a git repository

    Args:
        url: Git repository URL
        destination: Destination path for cloning
        branch: Optional branch name (defaults to default branch)
        credentials: Optional dict with 'username' and 'token' keys

    Returns:
        Dict with 'path' on success or 'error' on failure
    """
    try:
        # Prepare clone command
        cmd = ["git", "clone"]

        # Add branch if specified
        if branch:
            cmd.extend(["--branch", branch])

        # Add credentials to URL if provided
        if credentials and credentials.get("username") and credentials.get("token"):
            # Parse URL to inject credentials
            if url.startswith("https://"):
                url = url.replace(
                    "https://",
                    f"https://{credentials['username']}:{credentials['token']}@"
                )

        cmd.extend([url, str(destination)])

        # Execute git clone
        logger.info(
            "cloning_repository",
            url=url.split("@")[-1] if "@" in url else url,  # Hide credentials
            destination=str(destination),
            branch=branch
        )

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )

        if result.returncode != 0:
            error_msg = result.stderr or result.stdout or "Unknown git clone error"
            logger.error(
                "clone_failed",
                error=error_msg,
                returncode=result.returncode
            )
            return {"error": error_msg}

        logger.info(
            "clone_successful",
            path=str(destination)
        )

        return {
            "path": destination,
            "url": url.split("@")[-1] if "@" in url else url,
            "branch": branch or "default"
        }

    except subprocess.TimeoutExpired:
        error_msg = "Git clone operation timed out after 5 minutes"
        logger.error("clone_timeout", destination=str(destination))
        return {"error": error_msg}

    except Exception as e:
        error_msg = f"Failed to clone repository: {str(e)}"
        logger.error("clone_exception", error=str(e))
        return {"error": error_msg}
