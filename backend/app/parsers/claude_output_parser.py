"""
Parser for Claude Code CLI output

Extracts structured data from Claude Code's terminal output including:
- Text responses
- Tool executions
- Script outputs
- File changes
- Errors
"""

import re
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class ParsedResponse:
    """Structured representation of Claude Code output"""
    text_response: str
    tool_calls: List[Dict[str, Any]]
    script_outputs: List[str]
    files_created: List[str]
    files_modified: List[str]
    errors: List[str]
    raw_output: str


class ClaudeOutputParser:
    """
    Parses Claude Code CLI output into structured data

    Handles:
    - ANSI color code stripping
    - Tool execution detection
    - Script output extraction
    - File operation tracking
    - Error detection
    """

    # ANSI escape sequence pattern
    ANSI_PATTERN = re.compile(r'\x1b\[[0-9;]*m')

    # Common Claude Code output patterns
    TOOL_EXECUTION_PATTERNS = [
        r'Executing command[:\s]+(.+)',
        r'Running[:\s]+(.+)',
        r'\$ (.+)',
    ]

    FILE_CREATED_PATTERNS = [
        r'Created file[:\s]+(.+)',
        r'Writing to[:\s]+(.+)',
        r'Wrote[:\s]+(.+)',
    ]

    FILE_MODIFIED_PATTERNS = [
        r'Modified[:\s]+(.+)',
        r'Updated[:\s]+(.+)',
        r'Edited[:\s]+(.+)',
    ]

    ERROR_PATTERNS = [
        r'Error[:\s]+(.+)',
        r'Failed[:\s]+(.+)',
        r'Exception[:\s]+(.+)',
        r'Traceback',
    ]

    def __init__(self):
        self.tool_patterns = [re.compile(p, re.IGNORECASE) for p in self.TOOL_EXECUTION_PATTERNS]
        self.file_created_patterns = [re.compile(p, re.IGNORECASE) for p in self.FILE_CREATED_PATTERNS]
        self.file_modified_patterns = [re.compile(p, re.IGNORECASE) for p in self.FILE_MODIFIED_PATTERNS]
        self.error_patterns = [re.compile(p, re.IGNORECASE) for p in self.ERROR_PATTERNS]

    def parse(self, raw_output: str) -> ParsedResponse:
        """
        Parse Claude Code CLI output into structured response

        Args:
            raw_output: Raw text output from Claude Code CLI

        Returns:
            ParsedResponse with extracted structured data
        """
        # Strip ANSI codes first
        clean_output = self._strip_ansi(raw_output)

        # Extract different components
        text_response = self._extract_text_response(clean_output)
        tool_calls = self._extract_tool_calls(clean_output)
        script_outputs = self._extract_script_outputs(clean_output)
        files_created = self._extract_files_created(clean_output)
        files_modified = self._extract_files_modified(clean_output)
        errors = self._extract_errors(clean_output)

        logger.debug(
            "Parsed Claude Code output",
            text_length=len(text_response),
            tool_calls=len(tool_calls),
            script_outputs=len(script_outputs),
            files_created=len(files_created),
            files_modified=len(files_modified),
            errors=len(errors)
        )

        return ParsedResponse(
            text_response=text_response,
            tool_calls=tool_calls,
            script_outputs=script_outputs,
            files_created=files_created,
            files_modified=files_modified,
            errors=errors,
            raw_output=raw_output
        )

    def _strip_ansi(self, text: str) -> str:
        """Remove ANSI color codes and escape sequences"""
        return self.ANSI_PATTERN.sub('', text)

    def _extract_text_response(self, text: str) -> str:
        """
        Extract Claude's text response (what Claude says to the user)

        This is the main response text, excluding tool execution details
        """
        # Remove lines that look like tool execution or system output
        lines = text.split('\n')
        response_lines = []

        for line in lines:
            # Skip lines that match tool/system patterns
            is_system_line = False

            # Check if line matches tool execution patterns
            for pattern in self.tool_patterns:
                if pattern.search(line):
                    is_system_line = True
                    break

            # Check if line matches file operation patterns
            if not is_system_line:
                for pattern in self.file_created_patterns + self.file_modified_patterns:
                    if pattern.search(line):
                        is_system_line = True
                        break

            # Include line if it's not a system line
            if not is_system_line and line.strip():
                response_lines.append(line)

        return '\n'.join(response_lines).strip()

    def _extract_tool_calls(self, text: str) -> List[Dict[str, Any]]:
        """Extract tool executions from output"""
        tool_calls = []

        for pattern in self.tool_patterns:
            for match in pattern.finditer(text):
                command = match.group(1).strip()
                tool_calls.append({
                    "type": "bash",
                    "command": command
                })

        return tool_calls

    def _extract_script_outputs(self, text: str) -> List[str]:
        """
        Extract script execution outputs

        Looks for output sections after command execution
        """
        outputs = []
        lines = text.split('\n')

        # Look for output sections after tool executions
        in_output_section = False
        current_output = []

        for line in lines:
            # Check if this line starts a tool execution
            is_tool_line = any(p.search(line) for p in self.tool_patterns)

            if is_tool_line:
                # Save previous output if any
                if current_output:
                    outputs.append('\n'.join(current_output).strip())
                    current_output = []
                in_output_section = True
            elif in_output_section:
                # Collect output lines
                current_output.append(line)

        # Add final output
        if current_output:
            outputs.append('\n'.join(current_output).strip())

        return [o for o in outputs if o]  # Filter empty

    def _extract_files_created(self, text: str) -> List[str]:
        """Extract file creation operations"""
        files = []

        for pattern in self.file_created_patterns:
            for match in pattern.finditer(text):
                filename = match.group(1).strip()
                files.append(filename)

        return files

    def _extract_files_modified(self, text: str) -> List[str]:
        """Extract file modification operations"""
        files = []

        for pattern in self.file_modified_patterns:
            for match in pattern.finditer(text):
                filename = match.group(1).strip()
                files.append(filename)

        return files

    def _extract_errors(self, text: str) -> List[str]:
        """Extract error messages"""
        errors = []
        lines = text.split('\n')

        for i, line in enumerate(lines):
            for pattern in self.error_patterns:
                if pattern.search(line):
                    # Include the error line and a few context lines
                    context_start = max(0, i - 1)
                    context_end = min(len(lines), i + 3)
                    error_context = '\n'.join(lines[context_start:context_end])
                    errors.append(error_context.strip())
                    break

        return errors

    def is_response_complete(self, text: str) -> bool:
        """
        Determine if Claude Code has finished responding

        Heuristics:
        - Ends with a question or statement
        - No pending tool executions
        - No truncated output
        """
        clean_text = self._strip_ansi(text).strip()

        if not clean_text:
            return False

        # Check if ends with typical completion markers
        completion_markers = [
            '?',  # Question
            '.',  # Statement
            '!',  # Exclamation
            ')',  # Closing paren
            '"',  # Closing quote
        ]

        return any(clean_text.endswith(marker) for marker in completion_markers)
