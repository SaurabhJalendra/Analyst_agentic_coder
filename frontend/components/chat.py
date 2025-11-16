"""Chat interface component."""
import streamlit as st

def render_chat_interface():
    """Render the chat interface."""
    # This is a placeholder - the main chat logic is in streamlit_app.py
    pass

def format_message(message: dict) -> str:
    """Format a message for display.

    Args:
        message: Message dict with role and content

    Returns:
        Formatted message string
    """
    if message["role"] == "user":
        return f"**You:** {message['content']}"
    else:
        return f"**Claude:** {message['content']}"
