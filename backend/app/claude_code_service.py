"""
Claude Code CLI Service - Using --print mode for reliable non-interactive operation

Uses subprocess with --print mode instead of terminal emulation for reliability.
"""

import asyncio
import subprocess
import json
import os
from pathlib import Path
from typing import Optional, Dict, Any, List
import structlog

logger = structlog.get_logger(__name__)


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
        self.claude_executable = claude_executable or r"C:\Users\Saurabh\.local\bin\claude.exe"
        self.is_ready = False
        self.conversation_history: List[Dict] = []

        logger.info(
            "Initialized Claude Code service",
            session_id=session_id,
            workspace=str(workspace_path)
        )

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

    async def send_message(self, user_message: str, timeout: int = 300) -> Dict[str, Any]:
        """
        Send message to Claude Code using --print mode

        Args:
            user_message: User's message/request
            timeout: Maximum time to wait for response (seconds)

        Returns:
            Structured response with text, tool calls, outputs, etc.
        """
        if not self.is_ready:
            raise RuntimeError(f"Claude Code service not started for session {self.session_id}")

        logger.info(
            "Sending message to Claude Code",
            session_id=self.session_id,
            message_preview=user_message[:100]
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

            # Add conversation continuation if we have history
            # Note: Claude Code maintains context via its own session management

            logger.debug(
                "Running Claude command",
                session_id=self.session_id,
                cwd=str(self.workspace_path)
            )

            # Run Claude Code
            result = await asyncio.to_thread(
                subprocess.run,
                cmd,
                cwd=str(self.workspace_path),
                capture_output=True,
                text=True,
                timeout=timeout,
                env={**os.environ}  # Pass through environment including auth tokens
            )

            # Log output for debugging
            logger.debug(
                "Claude Code raw output",
                session_id=self.session_id,
                stdout_len=len(result.stdout) if result.stdout else 0,
                stderr_len=len(result.stderr) if result.stderr else 0,
                returncode=result.returncode
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

        # Check for errors
        if returncode != 0:
            if stderr:
                errors.append(f"Claude exited with code {returncode}: {stderr}")
            else:
                errors.append(f"Claude exited with code {returncode}")

        # Try to parse JSON output
        if stdout:
            try:
                # --output-format json should give us structured output
                parsed = json.loads(stdout)

                # Extract text content
                text_content = ""
                if isinstance(parsed, dict):
                    # Handle various JSON structures Claude might return
                    if "result" in parsed:
                        text_content = parsed["result"]
                    elif "content" in parsed:
                        content = parsed["content"]
                        if isinstance(content, list):
                            text_parts = [
                                c.get("text", str(c))
                                for c in content
                                if isinstance(c, dict)
                            ]
                            text_content = "\n".join(text_parts)
                        else:
                            text_content = str(content)
                    elif "message" in parsed:
                        text_content = parsed["message"]
                    else:
                        text_content = json.dumps(parsed, indent=2)
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
                    "tool_calls": parsed.get("tool_calls", []) if isinstance(parsed, dict) else [],
                    "stop_reason": "end_turn",
                    "errors": errors,
                    "raw_output": stdout
                }

            except json.JSONDecodeError:
                # Not JSON, treat as plain text
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": stdout.strip()
                        }
                    ],
                    "tool_calls": [],
                    "stop_reason": "end_turn",
                    "errors": errors,
                    "raw_output": stdout
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
                "stop_reason": "error"
            }

        return {
            "content": [
                {
                    "type": "text",
                    "text": "No response received from Claude Code"
                }
            ],
            "errors": errors or ["No output"],
            "stop_reason": "error"
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

        # Setup authentication credentials for this workspace
        access_token = os.getenv("CLAUDE_CODE_ACCESS_TOKEN")
        refresh_token = os.getenv("CLAUDE_CODE_REFRESH_TOKEN")

        if access_token and refresh_token:
            auth_config = {
                "claudeAiOauth": {
                    "accessToken": access_token,
                    "refreshToken": refresh_token,
                    "expiresAt": 1763987494015,
                    "scopes": ["user:inference", "user:profile", "user:sessions:claude_code"],
                    "subscriptionType": "max",
                    "rateLimitTier": "default_claude_max_5x"
                }
            }

            config_file = claude_dir / "config.json"

            try:
                config_file.write_text(json.dumps(auth_config, indent=2))
                logger.info(
                    "Configured Claude Code authentication",
                    session_id=self.session_id,
                    config_file=str(config_file)
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
