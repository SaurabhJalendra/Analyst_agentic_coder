"""Claude API service for chatbot integration."""
import os
from typing import List, Dict, Any, Optional
from anthropic import Anthropic
import structlog

logger = structlog.get_logger()

# Tool definitions for Claude API
TOOL_DEFINITIONS = [
    {
        "name": "read_file",
        "description": "Read a file from the filesystem with optional line offset and limit.",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Absolute path to the file to read"
                },
                "offset": {
                    "type": "integer",
                    "description": "Line number to start from (0-indexed)",
                    "default": 0
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of lines to read",
                    "default": 2000
                }
            },
            "required": ["file_path"]
        }
    },
    {
        "name": "write_file",
        "description": "Write content to a file (creates or overwrites).",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Absolute path to the file to write"
                },
                "content": {
                    "type": "string",
                    "description": "Content to write to the file"
                }
            },
            "required": ["file_path", "content"]
        }
    },
    {
        "name": "edit_file",
        "description": "Edit a file by replacing exact string match.",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Absolute path to the file to edit"
                },
                "old_string": {
                    "type": "string",
                    "description": "String to replace"
                },
                "new_string": {
                    "type": "string",
                    "description": "Replacement string"
                },
                "replace_all": {
                    "type": "boolean",
                    "description": "If true, replace all occurrences",
                    "default": False
                }
            },
            "required": ["file_path", "old_string", "new_string"]
        }
    },
    {
        "name": "glob_pattern",
        "description": "Find files matching a glob pattern.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Glob pattern (e.g., '**/*.py')"
                },
                "path": {
                    "type": "string",
                    "description": "Directory to search in (optional)"
                }
            },
            "required": ["pattern"]
        }
    },
    {
        "name": "grep",
        "description": "Search for pattern in files using regex.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Regex pattern to search for"
                },
                "path": {
                    "type": "string",
                    "description": "Directory or file to search in"
                },
                "glob": {
                    "type": "string",
                    "description": "Glob pattern to filter files (e.g., '*.py')"
                },
                "type": {
                    "type": "string",
                    "description": "File type filter (e.g., 'py', 'js')"
                },
                "-i": {
                    "type": "boolean",
                    "description": "Case insensitive search",
                    "default": False
                },
                "output_mode": {
                    "type": "string",
                    "enum": ["content", "files_with_matches", "count"],
                    "description": "Output mode",
                    "default": "files_with_matches"
                },
                "-B": {
                    "type": "integer",
                    "description": "Lines of context before match",
                    "default": 0
                },
                "-A": {
                    "type": "integer",
                    "description": "Lines of context after match",
                    "default": 0
                },
                "head_limit": {
                    "type": "integer",
                    "description": "Maximum results to return",
                    "default": 100
                }
            },
            "required": ["pattern"]
        }
    },
    {
        "name": "bash",
        "description": "Execute a shell command.",
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "Shell command to execute"
                },
                "cwd": {
                    "type": "string",
                    "description": "Working directory for command"
                },
                "timeout": {
                    "type": "integer",
                    "description": "Timeout in seconds",
                    "default": 120
                }
            },
            "required": ["command"]
        }
    },
    {
        "name": "git_clone",
        "description": "Clone a git repository.",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "Repository URL to clone"
                },
                "directory": {
                    "type": "string",
                    "description": "Directory name for cloned repo"
                },
                "branch": {
                    "type": "string",
                    "description": "Specific branch to clone"
                },
                "credentials": {
                    "type": "object",
                    "description": "Authentication credentials (username, token)",
                    "properties": {
                        "username": {"type": "string"},
                        "token": {"type": "string"}
                    }
                }
            },
            "required": ["url"]
        }
    },
    {
        "name": "git_status",
        "description": "Get git status for a repository.",
        "input_schema": {
            "type": "object",
            "properties": {
                "repo_path": {
                    "type": "string",
                    "description": "Path to git repository"
                }
            }
        }
    },
    {
        "name": "git_diff",
        "description": "Get git diff.",
        "input_schema": {
            "type": "object",
            "properties": {
                "repo_path": {
                    "type": "string",
                    "description": "Path to git repository"
                },
                "file_path": {
                    "type": "string",
                    "description": "Specific file to diff"
                }
            }
        }
    },
    {
        "name": "git_commit",
        "description": "Create a git commit.",
        "input_schema": {
            "type": "object",
            "properties": {
                "repo_path": {
                    "type": "string",
                    "description": "Path to git repository"
                },
                "message": {
                    "type": "string",
                    "description": "Commit message"
                },
                "files": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Files to commit (null for all)"
                }
            },
            "required": ["message"]
        }
    },
    {
        "name": "git_push",
        "description": "Push commits to remote.",
        "input_schema": {
            "type": "object",
            "properties": {
                "repo_path": {
                    "type": "string",
                    "description": "Path to git repository"
                },
                "remote": {
                    "type": "string",
                    "description": "Remote name",
                    "default": "origin"
                },
                "branch": {
                    "type": "string",
                    "description": "Branch to push"
                }
            }
        }
    },
    {
        "name": "git_pull",
        "description": "Pull commits from remote.",
        "input_schema": {
            "type": "object",
            "properties": {
                "repo_path": {
                    "type": "string",
                    "description": "Path to git repository"
                },
                "remote": {
                    "type": "string",
                    "description": "Remote name",
                    "default": "origin"
                },
                "branch": {
                    "type": "string",
                    "description": "Branch to pull"
                }
            }
        }
    }
]

class ClaudeService:
    """Service for interacting with Claude API."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """Initialize Claude service.

        Args:
            api_key: Claude API key (defaults to env var)
            model: Claude model to use (defaults to env var or Sonnet 3.5)
        """
        self.api_key = api_key or os.getenv("CLAUDE_API_KEY")
        if not self.api_key:
            raise ValueError("Claude API key not provided")

        self.model = model or os.getenv("CLAUDE_MODEL", "claude-3-5-sonnet-20241022")
        self.client = Anthropic(api_key=self.api_key)

        logger.info("claude_service_initialized", model=self.model)

    async def send_message(
        self,
        messages: List[Dict[str, Any]],
        system_prompt: Optional[str] = None,
        max_tokens: int = 4096
    ) -> Dict[str, Any]:
        """Send a message to Claude and get response.

        Args:
            messages: List of message dicts with 'role' and 'content'
            system_prompt: Optional system prompt
            max_tokens: Maximum tokens in response

        Returns:
            Claude's response including any tool calls
        """
        try:
            logger.info("sending_message_to_claude", messages=len(messages))

            # Default system prompt
            if not system_prompt:
                system_prompt = (
                    "You are a helpful coding assistant that can perform various operations on codebases. "
                    "You have access to tools for reading, writing, editing files, searching code, running "
                    "commands, and git operations. When the user asks you to do something, plan out your "
                    "approach and use the appropriate tools to accomplish the task."
                )

            # Make API call
            response = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=system_prompt,
                messages=messages,
                tools=TOOL_DEFINITIONS
            )

            # Parse response
            result = {
                "id": response.id,
                "role": response.role,
                "content": [],
                "stop_reason": response.stop_reason,
                "usage": {
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens
                }
            }

            # Extract content blocks
            for content_block in response.content:
                if content_block.type == "text":
                    result["content"].append({
                        "type": "text",
                        "text": content_block.text
                    })
                elif content_block.type == "tool_use":
                    result["content"].append({
                        "type": "tool_use",
                        "id": content_block.id,
                        "name": content_block.name,
                        "input": content_block.input
                    })

            logger.info(
                "claude_response_received",
                stop_reason=result["stop_reason"],
                content_blocks=len(result["content"])
            )

            return result

        except Exception as e:
            logger.error("claude_api_error", error=str(e))
            raise
