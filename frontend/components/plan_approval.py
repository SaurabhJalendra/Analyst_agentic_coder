"""Plan approval component."""
import streamlit as st
import requests
import json

def render_plan_approval(tool_calls: list, api_base_url: str):
    """Render the plan approval interface.

    Args:
        tool_calls: List of tool calls to approve
        api_base_url: Base URL for API
    """
    st.markdown("---")
    st.subheader("🔧 Claude wants to perform these operations:")

    # Display each tool call
    for idx, tool in enumerate(tool_calls, 1):
        with st.container():
            st.markdown(f"""
            <div class="tool-card">
                <strong>{idx}. {tool['name']}</strong>
            </div>
            """, unsafe_allow_html=True)

            # Show tool parameters
            with st.expander(f"View parameters for {tool['name']}"):
                st.json(tool['input'])

            # Show description based on tool name
            description = get_tool_description(tool['name'], tool['input'])
            if description:
                st.info(description)

    # Approval buttons
    col1, col2, col3 = st.columns([1, 1, 2])

    with col1:
        if st.button("✅ Approve & Execute", type="primary", use_container_width=True):
            execute_tools(tool_calls, api_base_url)

    with col2:
        if st.button("❌ Reject", use_container_width=True):
            st.session_state.pending_tools = []
            st.info("Operations rejected. You can continue chatting.")
            st.rerun()

    st.markdown("---")

def execute_tools(tool_calls: list, api_base_url: str):
    """Execute approved tool calls.

    Args:
        tool_calls: List of tool calls to execute
        api_base_url: Base URL for API
    """
    with st.spinner("Executing operations..."):
        try:
            payload = {
                "session_id": st.session_state.session_id,
                "tool_calls": tool_calls
            }

            response = requests.post(
                f"{api_base_url}/api/execute",
                json=payload
            )

            if response.status_code == 200:
                data = response.json()

                # Display results
                st.success("✅ Operations completed successfully!")

                # Show results
                with st.expander("📋 Execution Results", expanded=True):
                    for result in data["results"]:
                        st.markdown(f"**{result['tool_name']}:**")
                        st.json(result['result'])

                # Add Claude's summary to chat
                if data.get("response"):
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": data["response"]
                    })

                # Clear pending tools
                st.session_state.pending_tools = []

                # Rerun to update chat
                st.rerun()

            else:
                st.error(f"Execution failed: {response.json().get('detail', 'Unknown error')}")

        except Exception as e:
            st.error(f"Error executing tools: {str(e)}")

def get_tool_description(tool_name: str, tool_input: dict) -> str:
    """Get a human-readable description of what a tool will do.

    Args:
        tool_name: Name of the tool
        tool_input: Tool input parameters

    Returns:
        Human-readable description
    """
    descriptions = {
        "read_file": f"📖 Read file: `{tool_input.get('file_path', 'unknown')}`",
        "write_file": f"✍️ Write to file: `{tool_input.get('file_path', 'unknown')}` ({len(tool_input.get('content', ''))} characters)",
        "edit_file": f"✏️ Edit file: `{tool_input.get('file_path', 'unknown')}` (replace text)",
        "glob_pattern": f"🔍 Find files matching: `{tool_input.get('pattern', 'unknown')}`",
        "grep": f"🔎 Search for: `{tool_input.get('pattern', 'unknown')}` in files",
        "bash": f"💻 Run command: `{tool_input.get('command', 'unknown')}`",
        "git_clone": f"📥 Clone repository: `{tool_input.get('url', 'unknown')}`",
        "git_status": f"📊 Check git status in: `{tool_input.get('repo_path', 'workspace')}`",
        "git_diff": f"📝 View git diff in: `{tool_input.get('repo_path', 'workspace')}`",
        "git_commit": f"💾 Create commit: `{tool_input.get('message', 'unknown')}`",
        "git_push": f"📤 Push to remote: `{tool_input.get('remote', 'origin')}`",
        "git_pull": f"📥 Pull from remote: `{tool_input.get('remote', 'origin')}`",
    }

    return descriptions.get(tool_name, f"Execute: {tool_name}")
