"""Tool executor for executing Claude's tool calls."""
from pathlib import Path
from typing import Any, Dict, List
import structlog

from app.tools.file_ops import FileOperations
from app.tools.search import SearchOperations
from app.tools.bash import BashOperations
from app.tools.git_ops import GitOperations

logger = structlog.get_logger()

class ToolExecutor:
    """Executes tool calls from Claude API."""

    def __init__(self, workspace_path: Path, active_repo_path: Path = None):
        """Initialize tool executor.

        Args:
            workspace_path: Path to session workspace
            active_repo_path: Path to active git repository (if any)
        """
        self.workspace_path = workspace_path
        self.active_repo_path = active_repo_path or workspace_path
        self.file_ops = FileOperations(workspace_path)
        self.search_ops = SearchOperations()
        self.bash_ops = BashOperations()
        self.git_ops = GitOperations()

    async def execute_tool(self, tool_name: str, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single tool.

        Args:
            tool_name: Name of the tool to execute
            tool_input: Tool input parameters

        Returns:
            Tool execution result
        """
        try:
            logger.info("executing_tool", tool=tool_name, input=tool_input)

            # Route to appropriate tool
            if tool_name == "read_file":
                result = await self.file_ops.read_file(
                    file_path=tool_input.get("file_path"),
                    offset=tool_input.get("offset", 0),
                    limit=tool_input.get("limit", 2000)
                )
            elif tool_name == "write_file":
                result = await self.file_ops.write_file(
                    file_path=tool_input.get("file_path"),
                    content=tool_input.get("content")
                )
            elif tool_name == "edit_file":
                result = await self.file_ops.edit_file(
                    file_path=tool_input.get("file_path"),
                    old_string=tool_input.get("old_string"),
                    new_string=tool_input.get("new_string"),
                    replace_all=tool_input.get("replace_all", False)
                )
            elif tool_name == "glob_pattern":
                result = await self.file_ops.glob_pattern(
                    pattern=tool_input.get("pattern"),
                    path=tool_input.get("path")
                )
            elif tool_name == "grep":
                result = await self.search_ops.grep(
                    pattern=tool_input.get("pattern"),
                    path=tool_input.get("path"),
                    glob=tool_input.get("glob"),
                    file_type=tool_input.get("type"),
                    case_insensitive=tool_input.get("-i", False),
                    output_mode=tool_input.get("output_mode", "files_with_matches"),
                    context_before=tool_input.get("-B", 0),
                    context_after=tool_input.get("-A", 0),
                    head_limit=tool_input.get("head_limit", 100)
                )
            elif tool_name == "bash":
                result = await self.bash_ops.execute_command(
                    command=tool_input.get("command"),
                    cwd=tool_input.get("cwd", str(self.workspace_path)),
                    timeout=tool_input.get("timeout", 120)
                )
            elif tool_name == "git_clone":
                result = await self.git_ops.clone_repository(
                    url=tool_input.get("url"),
                    destination=self.workspace_path / tool_input.get("directory", "repo"),
                    branch=tool_input.get("branch"),
                    credentials=tool_input.get("credentials")
                )
            elif tool_name == "git_status":
                result = await self.git_ops.git_status(
                    repo_path=Path(tool_input.get("repo_path", self.active_repo_path))
                )
            elif tool_name == "git_diff":
                result = await self.git_ops.git_diff(
                    repo_path=Path(tool_input.get("repo_path", self.active_repo_path)),
                    file_path=tool_input.get("file_path")
                )
            elif tool_name == "git_commit":
                result = await self.git_ops.git_commit(
                    repo_path=Path(tool_input.get("repo_path", self.active_repo_path)),
                    message=tool_input.get("message"),
                    files=tool_input.get("files")
                )
            elif tool_name == "git_push":
                result = await self.git_ops.git_push(
                    repo_path=Path(tool_input.get("repo_path", self.active_repo_path)),
                    remote=tool_input.get("remote", "origin"),
                    branch=tool_input.get("branch")
                )
            elif tool_name == "git_pull":
                result = await self.git_ops.git_pull(
                    repo_path=Path(tool_input.get("repo_path", self.active_repo_path)),
                    remote=tool_input.get("remote", "origin"),
                    branch=tool_input.get("branch")
                )
            else:
                result = {"error": f"Unknown tool: {tool_name}"}

            logger.info("tool_executed", tool=tool_name, success="error" not in result)
            return result

        except Exception as e:
            logger.error("tool_execution_failed", tool=tool_name, error=str(e))
            return {"error": f"Tool execution failed: {str(e)}"}

    async def execute_tools(self, tool_calls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Execute multiple tool calls.

        Args:
            tool_calls: List of tool calls from Claude

        Returns:
            List of tool execution results
        """
        results = []
        for tool_call in tool_calls:
            result = await self.execute_tool(
                tool_name=tool_call.get("name"),
                tool_input=tool_call.get("input", {})
            )
            results.append({
                "tool_call_id": tool_call.get("id"),
                "tool_name": tool_call.get("name"),
                "result": result
            })
        return results
