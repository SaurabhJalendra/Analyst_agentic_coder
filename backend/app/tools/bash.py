"""Bash tool for command execution."""
import asyncio
import subprocess
from pathlib import Path
from typing import Optional
import structlog

logger = structlog.get_logger()

class BashOperations:
    """Shell command execution."""

    @staticmethod
    async def execute_command(
        command: str,
        cwd: Optional[str] = None,
        timeout: int = 300,
        capture_output: bool = True
    ) -> dict:
        """Execute a shell command.

        Args:
            command: Command to execute
            cwd: Working directory for command
            timeout: Timeout in seconds (default 300 = 5 minutes)
            capture_output: Whether to capture stdout/stderr

        Returns:
            Dict with command result
        """
        try:
            working_dir = Path(cwd) if cwd else Path.cwd()
            if not working_dir.exists():
                return {"error": f"Working directory not found: {cwd}"}

            logger.info("executing_command", command=command, cwd=str(working_dir))

            # Execute command asynchronously
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE if capture_output else None,
                stderr=asyncio.subprocess.PIPE if capture_output else None,
                cwd=str(working_dir)
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                return {
                    "error": f"Command timed out after {timeout} seconds",
                    "command": command
                }

            result = {
                "command": command,
                "return_code": process.returncode,
                "stdout": stdout.decode('utf-8', errors='ignore') if stdout else "",
                "stderr": stderr.decode('utf-8', errors='ignore') if stderr else "",
                "success": process.returncode == 0
            }

            # Truncate very long output
            if len(result["stdout"]) > 30000:
                result["stdout"] = result["stdout"][:30000] + "\n... (output truncated)"
            if len(result["stderr"]) > 30000:
                result["stderr"] = result["stderr"][:30000] + "\n... (output truncated)"

            logger.info(
                "command_executed",
                command=command,
                return_code=process.returncode,
                success=result["success"]
            )

            return result

        except Exception as e:
            logger.error("command_execution_failed", command=command, error=str(e))
            return {
                "error": f"Command execution failed: {str(e)}",
                "command": command
            }
