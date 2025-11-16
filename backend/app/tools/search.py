"""Search tool: Grep for content searching."""
import re
import subprocess
from pathlib import Path
from typing import Optional
import structlog

logger = structlog.get_logger()

class SearchOperations:
    """Search operation tools."""

    @staticmethod
    async def grep(
        pattern: str,
        path: Optional[str] = None,
        glob: Optional[str] = None,
        file_type: Optional[str] = None,
        case_insensitive: bool = False,
        output_mode: str = "files_with_matches",
        context_before: int = 0,
        context_after: int = 0,
        head_limit: int = 100
    ) -> dict:
        """Search for pattern in files using ripgrep-like functionality.

        Args:
            pattern: Regex pattern to search for
            path: Directory or file to search in
            glob: Glob pattern to filter files (e.g., "*.py")
            file_type: File type filter (e.g., "py", "js")
            case_insensitive: Case insensitive search
            output_mode: "content", "files_with_matches", or "count"
            context_before: Lines of context before match
            context_after: Lines of context after match
            head_limit: Maximum results to return

        Returns:
            Dict with search results
        """
        try:
            search_path = Path(path) if path else Path.cwd()
            if not search_path.exists():
                return {"error": f"Path not found: {path}"}

            results = []
            matches_count = 0

            # Compile regex pattern
            flags = re.IGNORECASE if case_insensitive else 0
            try:
                regex = re.compile(pattern, flags)
            except re.error as e:
                return {"error": f"Invalid regex pattern: {str(e)}"}

            # Get list of files to search
            files_to_search = []
            if search_path.is_file():
                files_to_search = [search_path]
            else:
                # Build file list based on filters
                if glob:
                    files_to_search = list(search_path.glob(f"**/{glob}"))
                elif file_type:
                    # Common file extensions
                    ext_map = {
                        "py": "*.py", "js": "*.js", "ts": "*.ts", "jsx": "*.jsx", "tsx": "*.tsx",
                        "java": "*.java", "go": "*.go", "rs": "*.rs", "c": "*.c", "cpp": "*.cpp",
                        "h": "*.h", "hpp": "*.hpp", "md": "*.md", "txt": "*.txt", "json": "*.json",
                        "yaml": "*.yaml", "yml": "*.yml", "xml": "*.xml", "html": "*.html", "css": "*.css"
                    }
                    pattern_ext = ext_map.get(file_type, f"*.{file_type}")
                    files_to_search = list(search_path.glob(f"**/{pattern_ext}"))
                else:
                    # Search all text files
                    files_to_search = [f for f in search_path.rglob("*") if f.is_file()]

            # Limit files to search
            files_to_search = [f for f in files_to_search if f.is_file()][:1000]

            # Search through files
            for file_path in files_to_search:
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        lines = f.readlines()

                    file_matches = []
                    for line_num, line in enumerate(lines, 1):
                        if regex.search(line):
                            matches_count += 1
                            file_matches.append({
                                "line_number": line_num,
                                "content": line.rstrip(),
                                "context_before": lines[max(0, line_num-1-context_before):line_num-1] if context_before > 0 else [],
                                "context_after": lines[line_num:min(len(lines), line_num+context_after)] if context_after > 0 else []
                            })

                            # Check head limit
                            if len(results) + len(file_matches) >= head_limit:
                                break

                    if file_matches:
                        results.append({
                            "file": str(file_path),
                            "matches": len(file_matches),
                            "lines": file_matches if output_mode == "content" else []
                        })

                    # Check head limit
                    if len(results) >= head_limit:
                        break

                except Exception as e:
                    logger.debug("file_search_skipped", file=str(file_path), error=str(e))
                    continue

            # Format output based on mode
            if output_mode == "files_with_matches":
                output = {
                    "pattern": pattern,
                    "files_with_matches": [r["file"] for r in results],
                    "total_matches": matches_count,
                    "files_searched": len(files_to_search)
                }
            elif output_mode == "count":
                output = {
                    "pattern": pattern,
                    "match_counts": {r["file"]: r["matches"] for r in results},
                    "total_matches": matches_count,
                    "files_searched": len(files_to_search)
                }
            else:  # content mode
                output = {
                    "pattern": pattern,
                    "results": results,
                    "total_matches": matches_count,
                    "files_searched": len(files_to_search)
                }

            logger.info("grep_search", pattern=pattern, matches=matches_count, files=len(results))
            return output

        except Exception as e:
            logger.error("grep_failed", pattern=pattern, error=str(e))
            return {"error": f"Grep search failed: {str(e)}"}
