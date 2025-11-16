"""File operation tools: Read, Write, Edit, Glob."""
import os
from pathlib import Path
from typing import Optional
import glob as glob_module
import structlog

logger = structlog.get_logger()

class FileOperations:
    """File operation tools."""

    @staticmethod
    async def read_file(file_path: str, offset: int = 0, limit: int = 2000) -> dict:
        """Read a file with optional line offset and limit.

        Args:
            file_path: Absolute path to file
            offset: Line number to start from (0-indexed)
            limit: Maximum number of lines to read

        Returns:
            Dict with file contents and metadata
        """
        try:
            path = Path(file_path)
            if not path.exists():
                return {"error": f"File not found: {file_path}"}

            if not path.is_file():
                return {"error": f"Path is not a file: {file_path}"}

            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()

            total_lines = len(lines)
            selected_lines = lines[offset:offset + limit]

            # Format with line numbers (1-indexed)
            numbered_lines = []
            for i, line in enumerate(selected_lines, start=offset + 1):
                # Truncate long lines
                if len(line) > 2000:
                    line = line[:2000] + "... (truncated)\n"
                numbered_lines.append(f"{i}\t{line.rstrip()}")

            result = {
                "path": str(path),
                "total_lines": total_lines,
                "offset": offset,
                "lines_returned": len(selected_lines),
                "content": "\n".join(numbered_lines)
            }

            logger.info("file_read", path=file_path, lines=len(selected_lines))
            return result

        except Exception as e:
            logger.error("file_read_failed", path=file_path, error=str(e))
            return {"error": f"Failed to read file: {str(e)}"}

    @staticmethod
    async def write_file(file_path: str, content: str) -> dict:
        """Write content to a file (creates or overwrites).

        Args:
            file_path: Absolute path to file
            content: Content to write

        Returns:
            Dict with success status
        """
        try:
            path = Path(file_path)
            path.parent.mkdir(parents=True, exist_ok=True)

            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)

            logger.info("file_written", path=file_path, size=len(content))
            return {
                "success": True,
                "path": str(path),
                "bytes_written": len(content.encode('utf-8'))
            }

        except Exception as e:
            logger.error("file_write_failed", path=file_path, error=str(e))
            return {"error": f"Failed to write file: {str(e)}"}

    @staticmethod
    async def edit_file(file_path: str, old_string: str, new_string: str, replace_all: bool = False) -> dict:
        """Edit a file by replacing exact string match.

        Args:
            file_path: Absolute path to file
            old_string: String to replace
            new_string: Replacement string
            replace_all: If True, replace all occurrences

        Returns:
            Dict with success status and details
        """
        try:
            path = Path(file_path)
            if not path.exists():
                return {"error": f"File not found: {file_path}"}

            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Check if old_string exists
            if old_string not in content:
                return {"error": f"String not found in file: {old_string[:100]}..."}

            # Check if unique (unless replace_all)
            if not replace_all and content.count(old_string) > 1:
                return {
                    "error": f"String appears {content.count(old_string)} times. "
                             "Provide more context or use replace_all=true"
                }

            # Perform replacement
            if replace_all:
                new_content = content.replace(old_string, new_string)
                replacements = content.count(old_string)
            else:
                new_content = content.replace(old_string, new_string, 1)
                replacements = 1

            with open(path, 'w', encoding='utf-8') as f:
                f.write(new_content)

            logger.info("file_edited", path=file_path, replacements=replacements)
            return {
                "success": True,
                "path": str(path),
                "replacements": replacements
            }

        except Exception as e:
            logger.error("file_edit_failed", path=file_path, error=str(e))
            return {"error": f"Failed to edit file: {str(e)}"}

    @staticmethod
    async def glob_pattern(pattern: str, path: Optional[str] = None) -> dict:
        """Find files matching a glob pattern.

        Args:
            pattern: Glob pattern (e.g., "**/*.py")
            path: Directory to search in (default: current directory)

        Returns:
            Dict with matching file paths
        """
        try:
            search_path = Path(path) if path else Path.cwd()
            if not search_path.exists():
                return {"error": f"Directory not found: {path}"}

            # Use Path.glob for pattern matching
            matches = list(search_path.glob(pattern))
            file_paths = [str(p) for p in matches if p.is_file()]

            # Sort by modification time (most recent first)
            file_paths.sort(key=lambda p: Path(p).stat().st_mtime, reverse=True)

            logger.info("glob_search", pattern=pattern, matches=len(file_paths))
            return {
                "pattern": pattern,
                "search_path": str(search_path),
                "matches": len(file_paths),
                "files": file_paths
            }

        except Exception as e:
            logger.error("glob_failed", pattern=pattern, error=str(e))
            return {"error": f"Glob search failed: {str(e)}"}
