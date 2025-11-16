"""Repository browser component."""
import streamlit as st
from pathlib import Path
import os

def render_repo_browser(start_path: str = None):
    """Render a directory browser for selecting repositories.

    Args:
        start_path: Starting directory path (defaults to home directory)

    Returns:
        Selected repository path or None
    """
    if start_path is None:
        start_path = str(Path.home())

    # Initialize current path in session state
    if "browser_current_path" not in st.session_state:
        st.session_state.browser_current_path = start_path

    current_path = Path(st.session_state.browser_current_path)

    # Display current path
    st.text_input(
        "Current Path:",
        value=str(current_path),
        key="path_display",
        disabled=True
    )

    # Parent directory button
    if current_path != current_path.parent:
        if st.button("⬆️ Parent Directory"):
            st.session_state.browser_current_path = str(current_path.parent)
            st.rerun()

    # List directories and files
    try:
        items = []
        for item in current_path.iterdir():
            if item.is_dir():
                # Check if it's a git repo
                is_git = (item / ".git").exists()
                items.append({
                    "name": item.name,
                    "path": str(item),
                    "is_dir": True,
                    "is_git": is_git
                })

        # Sort directories first
        items.sort(key=lambda x: x["name"].lower())

        # Display items
        st.markdown("**Directories:**")

        for item in items[:20]:  # Limit to 20 items for performance
            col1, col2, col3 = st.columns([3, 1, 1])

            with col1:
                icon = "📁"
                if item.get("is_git"):
                    icon = "📦"  # Git repo icon
                st.markdown(f"{icon} **{item['name']}**")

            with col2:
                if st.button("Open", key=f"open_{item['path']}"):
                    st.session_state.browser_current_path = item['path']
                    st.rerun()

            with col3:
                if st.button("Select", key=f"select_{item['path']}", type="primary" if item.get("is_git") else "secondary"):
                    return item['path']

        if len(items) > 20:
            st.info(f"Showing first 20 of {len(items)} directories")

    except PermissionError:
        st.error("Permission denied to access this directory")
    except Exception as e:
        st.error(f"Error browsing directory: {str(e)}")

    # Manual path entry
    st.markdown("---")
    manual_path = st.text_input("Or enter path directly:")
    if manual_path and st.button("Go to Path"):
        if Path(manual_path).exists():
            st.session_state.browser_current_path = manual_path
            st.rerun()
        else:
            st.error("Path does not exist")

    return None
