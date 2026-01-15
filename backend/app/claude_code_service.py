"""
Claude Code CLI Service - Using --print mode for reliable non-interactive operation

Uses subprocess with --print mode instead of terminal emulation for reliability.
Includes automatic OAuth token refresh to prevent authentication failures.
"""

import asyncio
import subprocess
import json
import os
import time
import httpx
from pathlib import Path
from typing import Optional, Dict, Any, List
import structlog

logger = structlog.get_logger(__name__)

# Anthropic OAuth token refresh endpoint
ANTHROPIC_TOKEN_REFRESH_URL = "https://console.anthropic.com/v1/oauth/token"


class ClaudeCodeService:
    """
    Manages Claude Code CLI interactions using --print mode for reliability.

    Uses subprocess to run `claude -p "message"` for each request.
    This is more reliable than terminal emulation.
    """

    def __init__(self, workspace_path: str, session_id: str, claude_executable: str = None):
        """
        Initialize Claude Code service

        Args:
            workspace_path: Path to workspace directory where Claude Code will operate
            session_id: Unique session identifier
            claude_executable: Path to claude executable (default: auto-detect)
        """
        self.workspace_path = Path(workspace_path)
        self.session_id = session_id
        self.claude_executable = claude_executable or self._find_claude_executable()
        self.is_ready = False
        self.conversation_history: List[Dict] = []
        # Store Claude Code's internal session ID for conversation continuity
        self.claude_session_id: Optional[str] = None

        logger.info(
            "Initialized Claude Code service",
            session_id=session_id,
            workspace=str(workspace_path)
        )

    def _find_claude_executable(self) -> str:
        """Find the Claude CLI executable path"""
        import shutil

        # Try to find claude in PATH
        claude_path = shutil.which("claude")
        if claude_path:
            return claude_path

        # Common installation locations
        common_paths = [
            "/usr/local/bin/claude",
            "/usr/bin/claude",
            os.path.expanduser("~/.local/bin/claude"),
            "/home/appuser/.local/bin/claude",
        ]

        for path in common_paths:
            if os.path.isfile(path) and os.access(path, os.X_OK):
                return path

        # Default fallback
        return "claude"

    async def refresh_oauth_token(self) -> bool:
        """
        Refresh the OAuth access token using the refresh token.

        Returns:
            True if refresh was successful, False otherwise
        """
        refresh_token = os.getenv("CLAUDE_CODE_REFRESH_TOKEN")
        if not refresh_token:
            logger.error("No refresh token available", session_id=self.session_id)
            return False

        logger.info("Attempting to refresh OAuth token", session_id=self.session_id)

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    ANTHROPIC_TOKEN_REFRESH_URL,
                    data={
                        "grant_type": "refresh_token",
                        "refresh_token": refresh_token,
                    },
                    headers={
                        "Content-Type": "application/x-www-form-urlencoded",
                    },
                    timeout=30.0
                )

                if response.status_code == 200:
                    token_data = response.json()
                    new_access_token = token_data.get("access_token")
                    new_refresh_token = token_data.get("refresh_token", refresh_token)
                    expires_in = token_data.get("expires_in", 3600)

                    if new_access_token:
                        # Update environment variables
                        os.environ["CLAUDE_CODE_ACCESS_TOKEN"] = new_access_token
                        if new_refresh_token != refresh_token:
                            os.environ["CLAUDE_CODE_REFRESH_TOKEN"] = new_refresh_token

                        # Update credentials in workspace
                        self._update_credentials(new_access_token, new_refresh_token, expires_in)

                        logger.info(
                            "OAuth token refreshed successfully",
                            session_id=self.session_id,
                            expires_in=expires_in
                        )
                        return True
                    else:
                        logger.error(
                            "Token refresh response missing access_token",
                            session_id=self.session_id
                        )
                        return False
                else:
                    logger.error(
                        "Token refresh failed",
                        session_id=self.session_id,
                        status_code=response.status_code,
                        response=response.text[:500]
                    )
                    return False

        except Exception as e:
            logger.error(
                "Token refresh error",
                session_id=self.session_id,
                error=str(e)
            )
            return False

    def _update_credentials(self, access_token: str, refresh_token: str, expires_in: int = 3600):
        """
        Update credentials file with new tokens
        """
        claude_dir = self.workspace_path / ".claude"
        claude_dir.mkdir(parents=True, exist_ok=True)

        # Calculate expiration timestamp (current time + expires_in seconds, converted to milliseconds)
        expires_at = int((time.time() + expires_in) * 1000)

        auth_config = {
            "claudeAiOauth": {
                "accessToken": access_token,
                "refreshToken": refresh_token,
                "expiresAt": expires_at,
                "scopes": ["user:inference", "user:profile", "user:sessions:claude_code"],
                "subscriptionType": "max",
                "rateLimitTier": "default_claude_max_5x"
            }
        }

        credentials_file = claude_dir / ".credentials.json"
        try:
            credentials_file.write_text(json.dumps(auth_config, indent=2))
            logger.info(
                "Updated credentials file",
                session_id=self.session_id,
                expires_at=expires_at
            )
        except Exception as e:
            logger.error(
                "Failed to update credentials file",
                session_id=self.session_id,
                error=str(e)
            )

    def _is_auth_error(self, stderr: str, stdout: str) -> bool:
        """
        Check if the error is an authentication/token expiration error
        """
        error_indicators = [
            "authentication_error",
            "OAuth token has expired",
            "token has expired",
            "Please obtain a new token",
            "Please run /login",
            "401",
            "Unauthorized"
        ]
        combined = (stderr or "") + (stdout or "")
        return any(indicator in combined for indicator in error_indicators)

    async def start(self):
        """
        Initialize the service (setup permissions and verify Claude is available)
        """
        if self.is_ready:
            logger.warning("Claude Code service already started", session_id=self.session_id)
            return

        logger.info("Starting Claude Code service", session_id=self.session_id)

        # Setup autonomous permissions
        self._setup_autonomous_permissions()

        # Ensure workspace exists
        self.workspace_path.mkdir(parents=True, exist_ok=True)

        # Verify Claude CLI is accessible
        try:
            result = await asyncio.to_thread(
                subprocess.run,
                [self.claude_executable, "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                logger.info(
                    "Claude Code CLI verified",
                    session_id=self.session_id,
                    version=result.stdout.strip()
                )
            else:
                logger.warning(
                    "Claude CLI version check returned non-zero",
                    session_id=self.session_id,
                    stderr=result.stderr
                )
        except FileNotFoundError:
            logger.error(
                "Claude CLI not found",
                session_id=self.session_id,
                path=self.claude_executable
            )
            raise RuntimeError(f"Claude CLI not found at {self.claude_executable}")
        except subprocess.TimeoutExpired:
            logger.warning("Claude CLI version check timed out", session_id=self.session_id)

        self.is_ready = True
        logger.info("Claude Code service ready", session_id=self.session_id)

    async def send_message(self, user_message: str, timeout: int = 300, _retry_count: int = 0) -> Dict[str, Any]:
        """
        Send message to Claude Code using --print mode

        Args:
            user_message: User's message/request
            timeout: Maximum time to wait for response (seconds)
            _retry_count: Internal retry counter for auth refresh (do not set manually)

        Returns:
            Structured response with text, tool calls, outputs, etc.
        """
        if not self.is_ready:
            raise RuntimeError(f"Claude Code service not started for session {self.session_id}")

        logger.info(
            "Sending message to Claude Code",
            session_id=self.session_id,
            message_preview=user_message[:100],
            retry_count=_retry_count
        )

        try:
            # Build command with --print mode for non-interactive operation
            # -p runs in print mode (non-interactive)
            # --output-format json gives structured output
            cmd = [
                self.claude_executable,
                "-p", user_message,
                "--output-format", "json",
                "--dangerously-skip-permissions"  # Since we setup permissions ourselves
            ]

            # Add conversation continuation using --resume flag if we have a previous session
            if self.claude_session_id:
                cmd.extend(["--resume", self.claude_session_id])
                logger.info(
                    "Resuming Claude Code session",
                    session_id=self.session_id,
                    claude_session_id=self.claude_session_id
                )

            logger.debug(
                "Running Claude command",
                session_id=self.session_id,
                cwd=str(self.workspace_path),
                cmd=" ".join(cmd[:5]) + "..."  # Log first few args
            )

            # Setup environment with Claude config directory
            claude_env = {**os.environ}
            # Use credentials from home directory (mounted from host via docker-compose)
            # This allows auto-sync when `claude /login` is run on the host
            home_claude_dir = Path.home() / ".claude"
            if home_claude_dir.exists():
                claude_env["CLAUDE_CONFIG_DIR"] = str(home_claude_dir)
            else:
                # Fallback to workspace's .claude directory
                claude_env["CLAUDE_CONFIG_DIR"] = str(self.workspace_path / ".claude")

            # Run Claude Code
            result = await asyncio.to_thread(
                subprocess.run,
                cmd,
                cwd=str(self.workspace_path),
                capture_output=True,
                text=True,
                timeout=timeout,
                env=claude_env
            )

            # Log output for debugging
            logger.debug(
                "Claude Code raw output",
                session_id=self.session_id,
                stdout_len=len(result.stdout) if result.stdout else 0,
                stderr_len=len(result.stderr) if result.stderr else 0,
                returncode=result.returncode
            )

            # Check for authentication errors and retry with token refresh
            if result.returncode != 0 and self._is_auth_error(result.stderr, result.stdout):
                if _retry_count < 1:  # Only retry once
                    logger.warning(
                        "Authentication error detected, attempting token refresh",
                        session_id=self.session_id
                    )
                    refresh_success = await self.refresh_oauth_token()
                    if refresh_success:
                        # Re-setup credentials and retry
                        self._setup_autonomous_permissions()
                        logger.info(
                            "Token refreshed, retrying request",
                            session_id=self.session_id
                        )
                        return await self.send_message(user_message, timeout, _retry_count + 1)
                    else:
                        logger.error(
                            "Token refresh failed, cannot retry",
                            session_id=self.session_id
                        )

            # Parse response
            response = self._parse_response(result.stdout, result.stderr, result.returncode)

            # Store in history
            self.conversation_history.append({
                "role": "user",
                "content": user_message
            })
            self.conversation_history.append({
                "role": "assistant",
                "content": response.get("content", [])
            })

            logger.info(
                "Received response from Claude Code",
                session_id=self.session_id,
                response_length=len(result.stdout) if result.stdout else 0,
                has_errors=bool(response.get("errors"))
            )

            return response

        except subprocess.TimeoutExpired:
            logger.error(
                "Claude Code response timeout",
                session_id=self.session_id,
                timeout=timeout
            )
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Request timed out after {timeout} seconds. Claude Code may still be processing."
                    }
                ],
                "errors": [f"Timeout after {timeout}s"],
                "stop_reason": "timeout"
            }

        except Exception as e:
            logger.error(
                "Error running Claude Code",
                session_id=self.session_id,
                error=str(e)
            )
            raise

    def _parse_response(self, stdout: str, stderr: str, returncode: int) -> Dict[str, Any]:
        """
        Parse Claude Code output into structured response

        Args:
            stdout: Standard output from Claude
            stderr: Standard error from Claude
            returncode: Process return code

        Returns:
            Structured response dict
        """
        errors = []
        tool_calls = []
        files_created = []
        files_modified = []

        # Check for errors
        if returncode != 0:
            if stderr:
                errors.append(f"Claude exited with code {returncode}")
                # Include stderr details but don't duplicate
                if "Errors:" not in stderr:
                    errors.append(stderr)
            else:
                errors.append(f"Claude exited with code {returncode}")

        # Try to parse JSON output
        if stdout:
            try:
                # --output-format json should give us structured output
                parsed = json.loads(stdout)

                # Extract session ID for conversation continuity
                if isinstance(parsed, dict):
                    session_id = parsed.get("session_id") or parsed.get("sessionId")
                    if session_id:
                        self.claude_session_id = session_id
                        logger.info(
                            "Captured Claude session ID for continuity",
                            session_id=self.session_id,
                            claude_session_id=session_id
                        )

                # Extract text content and tool information
                text_content = ""
                if isinstance(parsed, dict):
                    # Handle various JSON structures Claude might return
                    if "result" in parsed:
                        text_content = parsed["result"]
                    elif "content" in parsed:
                        content = parsed["content"]
                        if isinstance(content, list):
                            text_parts = []
                            for c in content:
                                if isinstance(c, dict):
                                    if c.get("type") == "text":
                                        text_parts.append(c.get("text", ""))
                                    elif c.get("type") == "tool_use":
                                        tool_calls.append({
                                            "id": c.get("id"),
                                            "name": c.get("name"),
                                            "input": c.get("input", {})
                                        })
                                    elif c.get("type") == "tool_result":
                                        # Include tool results in text
                                        result = c.get("content", "")
                                        if result:
                                            text_parts.append(f"\n**Tool Result:**\n{result}")
                            text_content = "\n".join(text_parts)
                        else:
                            text_content = str(content)
                    elif "message" in parsed:
                        text_content = parsed["message"]
                    else:
                        # Try to extract meaningful text from the response
                        text_content = parsed.get("text", "") or json.dumps(parsed, indent=2)

                    # Extract tool calls if present at top level
                    if "tool_calls" in parsed:
                        tool_calls.extend(parsed["tool_calls"])

                    # Extract file operations
                    files_created = parsed.get("files_created", [])
                    files_modified = parsed.get("files_modified", [])

                elif isinstance(parsed, str):
                    text_content = parsed
                else:
                    text_content = str(parsed)

                return {
                    "content": [
                        {
                            "type": "text",
                            "text": text_content
                        }
                    ],
                    "tool_calls": tool_calls,
                    "files_created": files_created,
                    "files_modified": files_modified,
                    "stop_reason": "end_turn",
                    "errors": errors,
                    "raw_output": stdout,
                    "claude_session_id": self.claude_session_id
                }

            except json.JSONDecodeError:
                # Not JSON, treat as plain text - still might contain useful output
                # Try to extract session ID from text if present
                import re
                session_match = re.search(r'session[_-]?id["\s:]+([a-f0-9-]{36})', stdout, re.IGNORECASE)
                if session_match:
                    self.claude_session_id = session_match.group(1)

                return {
                    "content": [
                        {
                            "type": "text",
                            "text": stdout.strip()
                        }
                    ],
                    "tool_calls": [],
                    "files_created": [],
                    "files_modified": [],
                    "stop_reason": "end_turn",
                    "errors": errors,
                    "raw_output": stdout,
                    "claude_session_id": self.claude_session_id
                }

        # No stdout
        if stderr:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Error: {stderr}"
                    }
                ],
                "errors": errors or [stderr],
                "stop_reason": "error",
                "claude_session_id": self.claude_session_id
            }

        return {
            "content": [
                {
                    "type": "text",
                    "text": "No response received from Claude Code"
                }
            ],
            "errors": errors or ["No output"],
            "stop_reason": "error",
            "claude_session_id": self.claude_session_id
        }

    async def stop(self):
        """
        Stop the service (cleanup)
        """
        logger.info(
            "Stopping Claude Code service",
            session_id=self.session_id
        )
        self.is_ready = False
        self.conversation_history = []
        logger.info(
            "Claude Code service stopped",
            session_id=self.session_id
        )

    def _setup_autonomous_permissions(self):
        """
        Configure Claude Code for fully autonomous operation

        Creates .claude/settings.local.json with:
        - allow: ["*"] - Auto-approve all operations
        """
        claude_dir = self.workspace_path / ".claude"
        claude_dir.mkdir(parents=True, exist_ok=True)

        # Setup permissions for autonomous operation
        settings = {
            "permissions": {
                "allow": ["*"],
                "deny": [],
                "ask": []
            }
        }

        settings_file = claude_dir / "settings.local.json"

        try:
            settings_file.write_text(json.dumps(settings, indent=2))
            logger.info(
                "Configured autonomous permissions",
                session_id=self.session_id,
                settings_file=str(settings_file)
            )
        except Exception as e:
            logger.error(
                "Failed to setup permissions",
                session_id=self.session_id,
                error=str(e)
            )
            raise

        # Create credentials from environment variables
        access_token = os.getenv("CLAUDE_CODE_ACCESS_TOKEN")
        refresh_token = os.getenv("CLAUDE_CODE_REFRESH_TOKEN")

        if access_token and refresh_token:
            auth_config = {
                "claudeAiOauth": {
                    "accessToken": access_token,
                    "refreshToken": refresh_token,
                    "expiresAt": 1864430294792,
                    "scopes": ["user:inference", "user:profile", "user:sessions:claude_code"],
                    "subscriptionType": "max",
                    "rateLimitTier": "default_claude_max_5x"
                }
            }

            credentials_file = claude_dir / ".credentials.json"
            try:
                credentials_file.write_text(json.dumps(auth_config, indent=2))
                logger.info(
                    "Created Claude credentials from environment",
                    session_id=self.session_id,
                    config_file=str(credentials_file)
                )
            except Exception as e:
                logger.error(
                    "Failed to setup authentication",
                    session_id=self.session_id,
                    error=str(e)
                )
        else:
            logger.warning(
                "No Claude Code credentials found in environment",
                session_id=self.session_id
            )

    def is_alive(self) -> bool:
        """Check if service is ready"""
        return self.is_ready

    async def restart_if_needed(self):
        """Restart service if needed"""
        if not self.is_ready:
            logger.warning(
                "Claude Code service not ready, starting",
                session_id=self.session_id
            )
            await self.start()
