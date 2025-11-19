"""Streamlit chatbot interface for Claude Code."""
import streamlit as st
import requests
from pathlib import Path
import json
from components.repo_browser import render_repo_browser

# Configuration
API_BASE_URL = "http://localhost:8000"

# Page config
st.set_page_config(
    page_title="Cool Bot",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main {
        padding-top: 1rem;
    }
    .stChatMessage {
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 0.5rem;
    }
    .tool-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
        border-left: 4px solid #1f77b4;
    }
    .success-box {
        background-color: #d4edda;
        border-color: #c3e6cb;
        color: #155724;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    .error-box {
        background-color: #f8d7da;
        border-color: #f5c6cb;
        color: #721c24;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if "session_id" not in st.session_state:
    st.session_state.session_id = None
if "messages" not in st.session_state:
    st.session_state.messages = []
if "workspace_path" not in st.session_state:
    st.session_state.workspace_path = None
if "selected_repo" not in st.session_state:
    st.session_state.selected_repo = None

# Sidebar
with st.sidebar:
    st.title("🤖 Cool Bot")
    st.markdown("---")

    # Session info with debugging
    if st.session_state.session_id:
        st.success(f"✅ Active Session: {st.session_state.session_id[:8]}...")
        # Debug info
        with st.expander("🔍 Debug Info"):
            st.code(f"Full ID: {st.session_state.session_id}")
            st.code(f"Workspace: {st.session_state.workspace_path}")
            st.code(f"Selected Repo: {st.session_state.selected_repo}")
            st.code(f"Messages: {len(st.session_state.messages)}")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("New Session"):
                st.session_state.session_id = None
                st.session_state.messages = []
                st.session_state.workspace_path = None
                st.session_state.selected_repo = None
                st.rerun()

        with col2:
            if st.button("Delete Session"):
                try:
                    response = requests.delete(
                        f"{API_BASE_URL}/api/sessions/{st.session_state.session_id}"
                    )
                    if response.status_code == 200:
                        st.success("Session deleted!")
                        st.session_state.session_id = None
                        st.session_state.messages = []
                        st.session_state.workspace_path = None
                        st.session_state.selected_repo = None
                        st.rerun()
                    else:
                        st.error(f"Delete failed: {response.json().get('detail', 'Unknown error')}")
                except Exception as e:
                    st.error(f"Error: {str(e)}")

        # Session validation
        with st.expander("🔍 Session Info"):
            if st.button("Validate Session"):
                try:
                    response = requests.get(
                        f"{API_BASE_URL}/api/sessions/{st.session_state.session_id}/validate"
                    )
                    if response.status_code == 200:
                        data = response.json()
                        st.write(f"**Total Messages:** {data.get('total_messages', 0)}")
                        st.write(f"**Issues Found:** {data.get('issues_found', 0)}")

                        if data.get('is_valid'):
                            st.success("✅ Session is valid!")
                        else:
                            st.error("❌ Session has validation issues!")
                            if data.get('issues'):
                                st.json(data['issues'])
                            st.warning("Consider deleting this session and starting a new one.")
                    else:
                        st.error("Validation failed")
                except Exception as e:
                    st.error(f"Error: {str(e)}")
    else:
        st.info("No active session")

    st.markdown("---")

    # Repository section
    st.subheader("📁 Repository")

    repo_option = st.radio(
        "Repository source:",
        ["Browse Local", "Clone from URL", "Current Workspace"]
    )

    if repo_option == "Browse Local":
        if st.session_state.selected_repo:
            st.success(f"Selected: {Path(st.session_state.selected_repo).name}")
            if st.button("Change Repository"):
                st.session_state.selected_repo = None
                st.rerun()
        else:
            with st.expander("Browse Directories", expanded=True):
                st.session_state.selected_repo = render_repo_browser()

    elif repo_option == "Clone from URL":
        with st.form("clone_form"):
            git_url = st.text_input("Git URL:")
            branch = st.text_input("Branch (optional):")

            with st.expander("Authentication (for private repos)"):
                username = st.text_input("Username:")
                token = st.text_input("Token/Password:", type="password")

            if st.form_submit_button("Clone Repository"):
                if git_url:
                    with st.spinner("Cloning repository..."):
                        try:
                            payload = {
                                "url": git_url,
                                "session_id": st.session_state.session_id or "temp",
                                "branch": branch if branch else None,
                                "username": username if username else None,
                                "token": token if token else None
                            }
                            response = requests.post(
                                f"{API_BASE_URL}/api/repos/clone",
                                json=payload
                            )
                            if response.status_code == 200:
                                result = response.json()
                                st.session_state.selected_repo = result["path"]
                                st.session_state.session_id = payload["session_id"]
                                st.success(f"Cloned to: {result['path']}")
                                st.rerun()
                            else:
                                st.error(f"Clone failed: {response.json().get('detail', 'Unknown error')}")
                        except Exception as e:
                            st.error(f"Error: {str(e)}")
                else:
                    st.warning("Please enter a Git URL")

    else:  # Current Workspace
        if st.session_state.workspace_path:
            st.info(f"Using workspace: {st.session_state.workspace_path}")
        else:
            st.info("No workspace yet - send a message to create one")

    st.markdown("---")

    # Session Management
    with st.expander("🗂️ All Sessions"):
        if st.button("List All Sessions"):
            try:
                response = requests.get(f"{API_BASE_URL}/api/sessions")
                if response.status_code == 200:
                    data = response.json()
                    sessions = data.get("sessions", [])

                    if sessions:
                        st.write(f"**Total Sessions:** {len(sessions)}")
                        for session in sessions:
                            with st.container():
                                st.markdown(f"**ID:** `{session['id'][:16]}...`")
                                st.write(f"Created: {session['created_at']}")
                                st.write(f"Messages: {session['message_count']}")
                                if session.get('active_repo'):
                                    st.write(f"Repo: {session['active_repo']}")
                                st.markdown("---")
                    else:
                        st.info("No sessions found")
                else:
                    st.error("Failed to list sessions")
            except Exception as e:
                st.error(f"Error: {str(e)}")

        if st.button("🗑️ Delete All Sessions", type="secondary"):
            if st.button("⚠️ Confirm Delete All", type="primary"):
                try:
                    response = requests.delete(f"{API_BASE_URL}/api/sessions")
                    if response.status_code == 200:
                        st.success("All sessions deleted!")
                        st.session_state.session_id = None
                        st.session_state.messages = []
                        st.session_state.workspace_path = None
                        st.session_state.selected_repo = None
                        st.rerun()
                    else:
                        st.error("Delete failed")
                except Exception as e:
                    st.error(f"Error: {str(e)}")

    st.markdown("---")

    # About
    with st.expander("ℹ️ About"):
        st.markdown("""
        **Cool Bot**

        This AI-powered bot helps you:
        - Read and analyze code
        - Edit and create files
        - Search codebases
        - Run commands
        - Perform git operations
        - Generate reports and visualizations

        All operations are executed automatically to help you work faster.
        """)

# Main content area
st.title("💬 Chat with Cool Bot")

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

        # Display tool calls if present
        if "tool_calls" in message and message["tool_calls"]:
            with st.expander(f"🔧 {len(message['tool_calls'])} tool(s) used"):
                for tool in message["tool_calls"]:
                    st.code(f"{tool['name']}({json.dumps(tool['input'], indent=2)})", language="json")

        # Display images if present (for graphs and reports)
        if "images" in message and message["images"]:
            for img_path in message["images"]:
                if Path(img_path).exists():
                    st.image(img_path)

# Chat input
if prompt := st.chat_input("Ask me anything about your code..."):
    # Add user message to chat
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("user"):
        st.markdown(prompt)

    # Send to API with real-time progress
    with st.chat_message("assistant"):
        import threading
        import time

        # Placeholder for progress
        progress_placeholder = st.empty()
        steps_placeholder = st.empty()

        # Flag to stop polling
        stop_polling = threading.Event()
        final_response = {"data": None, "error": None}

        def make_request():
            """Make the API request in a separate thread."""
            try:
                # Get session info from session state
                current_session_id = st.session_state.get("session_id")
                current_workspace = st.session_state.get("selected_repo") or st.session_state.get("workspace_path")

                payload = {
                    "message": prompt,
                    "session_id": current_session_id,
                    "workspace_path": current_workspace
                }

                # Log what we're sending (for debugging)
                import sys
                print(f"[FRONTEND] Sending message with session_id: {current_session_id}", file=sys.stderr)
                print(f"[FRONTEND] Workspace: {current_workspace}", file=sys.stderr)

                response = requests.post(
                    f"{API_BASE_URL}/api/chat",
                    json=payload,
                    timeout=900
                )

                if response.status_code == 200:
                    final_response["data"] = response.json()
                else:
                    final_response["error"] = f"Error: {response.json().get('detail', 'Unknown error')}"

            except requests.Timeout:
                final_response["error"] = "Request timed out. The operation may still be running in the background."
            except Exception as e:
                final_response["error"] = f"Connection error: {str(e)}"
            finally:
                stop_polling.set()

        # Start request thread
        request_thread = threading.Thread(target=make_request, daemon=True)
        request_thread.start()

        # Poll for progress
        try:
            while not stop_polling.is_set():
                try:
                    # Get progress
                    if "session_id" in st.session_state and st.session_state.session_id:
                        progress_response = requests.get(
                            f"{API_BASE_URL}/api/progress/{st.session_state.session_id}",
                            timeout=5
                        )

                        if progress_response.status_code == 200:
                            progress_data = progress_response.json()

                            if progress_data.get("status") != "not_found":
                                # Show current step
                                current_step = progress_data.get("current_step", "Processing...")
                                iteration = progress_data.get("iteration", 0)
                                max_iter = progress_data.get("max_iterations", 0)

                                if iteration > 0 and max_iter > 0:
                                    progress_placeholder.info(f"**Step {iteration}/{max_iter}:** {current_step}")
                                else:
                                    progress_placeholder.info(f"**Status:** {current_step}")

                                # Show step history
                                steps = progress_data.get("steps", [])
                                if steps:
                                    with steps_placeholder.expander(f"📋 Execution Steps ({len(steps)} completed)", expanded=False):
                                        for step in steps[-10:]:  # Show last 10 steps
                                            step_text = step.get("step", "")
                                            details = step.get("details", "")
                                            if details:
                                                st.text(f"{step_text}\n  {details}")
                                            else:
                                                st.text(step_text)

                except Exception:
                    pass  # Ignore progress fetch errors

                time.sleep(1)  # Poll every second

            # Wait for request to complete
            request_thread.join(timeout=1)

            # Clear progress
            progress_placeholder.empty()
            steps_placeholder.empty()

            # Handle response
            if final_response["data"]:
                data = final_response["data"]

                # CRITICAL: Update session state IMMEDIATELY before any other operations
                # This ensures session continuity for the next message
                new_session_id = data["session_id"]
                st.session_state.session_id = new_session_id

                # Update workspace path if provided
                if data.get("workspace_path"):
                    st.session_state.workspace_path = data["workspace_path"]

                # Also update selected_repo to match the current workspace
                if data.get("workspace_path") and not st.session_state.selected_repo:
                    st.session_state.selected_repo = data.get("workspace_path")

                # Display response
                st.markdown(data["response"])

                # Add assistant message
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": data["response"],
                    "tool_calls": data.get("tool_calls", [])
                })

                # Log for debugging
                logger_msg = f"Session updated: {new_session_id[:8]}... | Workspace: {st.session_state.workspace_path}"

                # Refresh to show the message
                st.rerun()

            elif final_response["error"]:
                st.error(final_response["error"])
                if "Connection error" in final_response["error"]:
                    st.info("Make sure the FastAPI backend is running on http://localhost:8080")

        except Exception as e:
            st.error(f"Error during processing: {str(e)}")

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; padding: 1rem;'>
    <small>Powered by AI | Built with FastAPI & Streamlit</small>
</div>
""", unsafe_allow_html=True)
