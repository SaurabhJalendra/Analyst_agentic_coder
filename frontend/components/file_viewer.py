"""File viewer component with syntax highlighting."""
import streamlit as st
import requests
from pygments import highlight
from pygments.lexers import get_lexer_for_filename, TextLexer
from pygments.formatters import HtmlFormatter
from pathlib import Path

def render_file_viewer(file_path: str, api_base_url: str):
    """Render file viewer with syntax highlighting.

    Args:
        file_path: Path to file to view
        api_base_url: Base URL for API
    """
    try:
        # Fetch file content
        response = requests.get(f"{api_base_url}/api/files/{file_path}")

        if response.status_code == 200:
            data = response.json()

            # Display file info
            st.markdown(f"**File:** `{file_path}`")
            st.markdown(f"**Lines:** {data['total_lines']}")

            # Get file extension for syntax highlighting
            try:
                lexer = get_lexer_for_filename(file_path)
            except:
                lexer = TextLexer()

            # Display content with line numbers
            st.code(data['content'], language=lexer.name.lower() if hasattr(lexer, 'name') else 'text')

        else:
            st.error(f"Failed to load file: {response.json().get('detail', 'Unknown error')}")

    except Exception as e:
        st.error(f"Error loading file: {str(e)}")

def render_diff_viewer(diff_text: str):
    """Render a git diff.

    Args:
        diff_text: Diff text to display
    """
    if not diff_text:
        st.info("No changes to display")
        return

    st.code(diff_text, language="diff")

def preview_file_changes(old_content: str, new_content: str, file_path: str):
    """Preview changes to a file.

    Args:
        old_content: Original file content
        new_content: Modified file content
        file_path: Path to file
    """
    st.subheader(f"Preview: {Path(file_path).name}")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Before:**")
        st.code(old_content, language=get_language_from_path(file_path))

    with col2:
        st.markdown("**After:**")
        st.code(new_content, language=get_language_from_path(file_path))

def get_language_from_path(file_path: str) -> str:
    """Get language name from file path for syntax highlighting.

    Args:
        file_path: Path to file

    Returns:
        Language name for syntax highlighting
    """
    ext_map = {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".jsx": "javascript",
        ".tsx": "typescript",
        ".java": "java",
        ".go": "go",
        ".rs": "rust",
        ".c": "c",
        ".cpp": "cpp",
        ".h": "c",
        ".hpp": "cpp",
        ".md": "markdown",
        ".json": "json",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".xml": "xml",
        ".html": "html",
        ".css": "css",
        ".sql": "sql",
        ".sh": "bash",
    }

    ext = Path(file_path).suffix.lower()
    return ext_map.get(ext, "text")
