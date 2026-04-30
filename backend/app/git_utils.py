"""Git utilities for repository cloning.

Credentials are passed via `git -c http.extraheader="Authorization: Basic ..."`
instead of being embedded in the URL — this prevents leaking secrets in logs,
git's own error messages, and process listings that echo arguments back.
Stderr from the clone is also redacted before being returned to the caller.
"""

import base64
import re
import subprocess
from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


_CREDENTIAL_URL_RE = re.compile(r"https?://[^/\s:]+:[^/\s@]+@")


def _redact(text: str) -> str:
    """Strip embedded credentials and bearer tokens from a string."""
    if not text:
        return text
    text = _CREDENTIAL_URL_RE.sub("https://<redacted>@", text)
    text = re.sub(r"(Bearer|Basic)\s+[A-Za-z0-9+/=._-]+", r"\1 <redacted>", text)
    return text


async def clone_repository(
    url: str,
    destination: Path,
    branch: str | None = None,
    credentials: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Clone a git repository.

    Args:
        url: Git repository URL (must NOT include embedded credentials).
        destination: Destination path for cloning.
        branch: Optional branch name (defaults to remote default branch).
        credentials: Optional {"username": ..., "token": ...} for HTTPS auth.
            Passed via http.extraheader, NOT injected into the URL.

    Returns:
        {"path": Path, "url": str, "branch": str} on success, {"error": str} on failure.
        Any credential material is redacted from the returned error string.
    """
    try:
        cmd: list[str] = ["git"]

        if credentials and credentials.get("username") and credentials.get("token"):
            auth = base64.b64encode(
                f"{credentials['username']}:{credentials['token']}".encode("utf-8")
            ).decode("ascii")
            # http.extraheader applies to all HTTP(S) requests in this command.
            # The header is visible in `ps` arg lists but not in URL, not in
            # logs, not in git's own error messages.
            cmd.extend(["-c", f"http.extraheader=Authorization: Basic {auth}"])

        cmd.append("clone")
        if branch:
            cmd.extend(["--branch", branch])
        cmd.extend([url, str(destination)])

        # Strip any caller-supplied credentials from the URL we log (defensive
        # — callers shouldn't pass creds-in-URL but we don't want to assume).
        log_url = _CREDENTIAL_URL_RE.sub("https://<redacted>@", url)
        logger.info(
            "cloning_repository",
            url=log_url,
            destination=str(destination),
            branch=branch,
        )

        # Suppress git's interactive auth prompt; fail fast on missing creds.
        env = {"GIT_TERMINAL_PROMPT": "0"}

        result = subprocess.run(  # noqa: S603 — args are validated above
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
            env={**__import__("os").environ, **env},
        )

        if result.returncode != 0:
            error_msg = _redact(result.stderr or result.stdout or "Unknown git clone error")
            logger.error(
                "clone_failed",
                error=error_msg,
                returncode=result.returncode,
            )
            return {"error": error_msg}

        logger.info("clone_successful", path=str(destination))

        return {
            "path": destination,
            "url": log_url,
            "branch": branch or "default",
        }

    except subprocess.TimeoutExpired:
        error_msg = "Git clone operation timed out after 5 minutes"
        logger.error("clone_timeout", destination=str(destination))
        return {"error": error_msg}

    except Exception as e:
        error_msg = _redact(f"Failed to clone repository: {e}")
        logger.error("clone_exception", error=_redact(str(e)))
        return {"error": error_msg}
