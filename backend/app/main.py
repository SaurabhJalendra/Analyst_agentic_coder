"""FastAPI main application."""
import os
import uuid
import traceback
from pathlib import Path
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import structlog
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(Path(__file__).parent.parent.parent / ".env")

from app.database import init_db, get_db, Session as DBSession, Message, ToolCall
from app.workspace_manager import workspace_manager, get_claude_instance, cleanup_claude_instance, cleanup_all_claude_instances
from app.db_utils import delete_session, list_sessions, validate_session_messages, cleanup_all_sessions
from app.progress_tracker import ProgressTracker
from app.git_utils import clone_repository

# Setup logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer()
    ]
)

logger = structlog.get_logger()

# Initialize FastAPI app
app = FastAPI(title="Claude Code Chatbot API")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Claude service (API-based - kept for backwards compatibility)
# claude_service = ClaudeService()
# Note: Now using Claude Code CLI instances managed per-session

# Pydantic models for API
class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    message: str
    workspace_path: Optional[str] = None

class ChatResponse(BaseModel):
    session_id: str
    response: str
    tool_calls: List[dict] = []
    requires_approval: bool = False
    workspace_path: Optional[str] = None  # Include workspace path for session continuity

# NOTE: ExecuteToolsRequest and ExecuteToolsResponse removed - not needed with Claude Code

class BrowseRequest(BaseModel):
    path: str

class CloneRequest(BaseModel):
    url: str
    session_id: str
    branch: Optional[str] = None
    username: Optional[str] = None
    token: Optional[str] = None

@app.on_event("startup")
async def startup():
    """Initialize database and perform maintenance on startup."""
    await init_db()
    logger.info("application_started")

    # Clean up old workspaces (older than 7 days)
    try:
        cleanup_result = workspace_manager.cleanup_old_workspaces(max_age_days=7)
        if cleanup_result["cleaned"] > 0:
            logger.info(
                "startup_cleanup_completed",
                workspaces_cleaned=cleanup_result["cleaned"],
                space_freed_mb=cleanup_result["total_size_mb"]
            )
    except Exception as e:
        logger.error("startup_cleanup_failed", error=str(e))

@app.on_event("shutdown")
async def shutdown():
    """Cleanup Claude Code instances on server shutdown."""
    logger.info("application_shutting_down")
    try:
        await cleanup_all_claude_instances()
        logger.info("all_claude_instances_cleaned_up")
    except Exception as e:
        logger.error("shutdown_cleanup_failed", error=str(e))

def _build_system_prompt(session: DBSession) -> str:
    """Build system prompt with current workspace and repository context.

    Args:
        session: Current database session

    Returns:
        System prompt string with current context
    """
    import platform
    from app.workspace_manager import workspace_manager

    os_type = platform.system()

    system_prompt = (
        f"You are a helpful coding assistant with access to file and git operations.\n\n"
        f"WORKSPACE CONTEXT:\n"
        f"- Workspace: {session.workspace_path}\n"
        f"- Active Repository: {session.active_repo or 'None'}\n"
        f"- Operating System: {os_type}\n"
    )

    # Add rich git repository context if available
    if session.active_repo:
        from pathlib import Path
        git_context = workspace_manager.get_git_context(Path(session.active_repo))

        if git_context.get("is_git_repo"):
            system_prompt += f"\nGIT REPOSITORY STATUS:\n"
            system_prompt += f"- Current Branch: {git_context.get('current_branch', 'unknown')}\n"
            system_prompt += f"- Has Uncommitted Changes: {git_context.get('is_dirty', False)}\n"

            if git_context.get("remote_url"):
                system_prompt += f"- Remote URL: {git_context['remote_url']}\n"

            # File status
            untracked = git_context.get('untracked_files_count', 0)
            modified = git_context.get('modified_files_count', 0)
            staged = git_context.get('staged_files_count', 0)

            if untracked > 0 or modified > 0 or staged > 0:
                system_prompt += f"- Files: {staged} staged, {modified} modified, {untracked} untracked\n"

            # Recent commits
            recent_commits = git_context.get('recent_commits', [])
            if recent_commits:
                system_prompt += f"- Recent Commits:\n"
                for commit in recent_commits[:2]:  # Show only 2 most recent
                    system_prompt += f"  - {commit['hash']}: {commit['message']}\n"

    system_prompt += "\n"

    if os_type == "Windows":
        system_prompt += (
            "IMPORTANT - Windows System:\n"
            "- Use 'dir' instead of 'ls'\n"
            "- Use 'type' instead of 'cat'\n"
            "- Use PowerShell commands when needed (e.g., Get-ChildItem, Get-Content)\n"
            "- Python commands work normally (python, pip, etc.)\n"
            "- Git commands work normally\n\n"
        )

    system_prompt += (
        "Use the available tools to help the user. When you need to perform operations, "
        "use the appropriate tools. You can use multiple tools in sequence to complete tasks.\n\n"
        "REMEMBER: You are working in the active repository shown above. "
        "All git commands will automatically target this repository unless you specify otherwise."
    )

    return system_prompt


async def _build_message_history(history, db: AsyncSession):
    """Build message history with proper tool_use blocks."""
    import json
    messages = []

    for msg in history:
        if msg.role == "assistant":
            # Get tool calls for this message
            result = await db.execute(
                select(ToolCall).where(ToolCall.message_id == msg.id)
            )
            tool_calls = result.scalars().all()

            # If there are tool calls, build structured content
            if tool_calls:
                content = []
                if msg.content:
                    content.append({"type": "text", "text": msg.content})

                for tc in tool_calls:
                    content.append({
                        "type": "tool_use",
                        "id": tc.claude_tool_id,
                        "name": tc.tool_name,
                        "input": json.loads(tc.arguments)
                    })

                messages.append({
                    "role": msg.role,
                    "content": content
                })
            else:
                # No tool calls, just text content
                messages.append({
                    "role": msg.role,
                    "content": msg.content
                })
        else:
            # User messages - check if it's tool results or regular text
            try:
                # Try to parse as JSON (tool results)
                if msg.content.startswith('['):
                    parsed_content = json.loads(msg.content)
                    messages.append({
                        "role": msg.role,
                        "content": parsed_content
                    })
                else:
                    # Regular text message
                    messages.append({
                        "role": msg.role,
                        "content": msg.content
                    })
            except (json.JSONDecodeError, AttributeError):
                # Not JSON, treat as regular text
                messages.append({
                    "role": msg.role,
                    "content": msg.content
                })

    return messages

@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Claude Code Chatbot API", "status": "running"}

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, db: AsyncSession = Depends(get_db)):
    """Handle chat message using Claude Code CLI with automatic tool execution."""
    session_id = None
    try:
        # Get or create session
        if request.session_id:
            session_id = request.session_id
            result = await db.execute(select(DBSession).where(DBSession.id == session_id))
            session = result.scalar_one_or_none()
            if not session:
                raise HTTPException(status_code=404, detail="Session not found")
        else:
            session_id = str(uuid.uuid4())
            workspace_path = workspace_manager.create_session_workspace(session_id)
            session = DBSession(
                id=session_id,
                workspace_path=str(workspace_path),
                active_repo=None  # Will be set after cloning default repo
            )
            db.add(session)
            await db.commit()

            # Auto-clone default repository if configured
            default_repo_url = os.getenv("DEFAULT_REPO_URL")
            default_repo_branch = os.getenv("DEFAULT_REPO_BRANCH", "main")

            if default_repo_url:
                logger.info(
                    "auto_cloning_default_repo",
                    session_id=session_id,
                    repo_url=default_repo_url,
                    branch=default_repo_branch
                )

                try:
                    # Clone the default repository
                    clone_result = await clone_repository(
                        url=default_repo_url,
                        destination=Path(session.workspace_path) / "repo",
                        branch=default_repo_branch,
                        credentials=None
                    )

                    if "error" not in clone_result:
                        # Update session with cloned repo path
                        session.active_repo = str(clone_result["path"])
                        await db.commit()
                        logger.info(
                            "default_repo_cloned",
                            session_id=session_id,
                            repo_path=session.active_repo
                        )
                    else:
                        logger.error(
                            "default_repo_clone_failed",
                            session_id=session_id,
                            error=clone_result["error"]
                        )
                except Exception as e:
                    logger.error(
                        "default_repo_clone_exception",
                        session_id=session_id,
                        error=str(e)
                    )
                    # Continue without repo - session can still be used

        # Save user message
        user_message_record = Message(
            session_id=session_id,
            role="user",
            content=request.message
        )
        db.add(user_message_record)
        await db.commit()

        # Start progress tracking
        ProgressTracker.start_operation(session_id, request.message)
        ProgressTracker.add_step(session_id, "📝 Message received", f"User: {request.message[:100]}...")

        # Show repo status in progress
        if session.active_repo:
            ProgressTracker.add_step(session_id, "📁 Repository ready", f"Working in: {Path(session.active_repo).name}")

        # Get or create persistent Claude Code instance for this session
        ProgressTracker.add_step(session_id, "🔧 Initializing Claude Code", "Getting Claude Code instance...")

        workspace_path = session.workspace_path
        # If active_repo exists, use it as the working directory
        if session.active_repo:
            workspace_path = session.active_repo

        claude_code_service = await get_claude_instance(session_id, workspace_path)

        # Send message to Claude Code CLI (it handles all tool execution autonomously)
        ProgressTracker.add_step(session_id, "💬 Sending to Claude Code", "Processing request...")

        claude_response = await claude_code_service.send_message(
            user_message=request.message,
            timeout=600  # 10 minute timeout for long-running tasks
        )

        # Extract response text
        response_text = ""
        for block in claude_response.get("content", []):
            if block.get("type") == "text":
                response_text += block.get("text", "")

        # Extract tool information from parsed output
        tool_calls_info = claude_response.get("tool_calls", [])
        script_outputs = claude_response.get("script_outputs", [])
        files_created = claude_response.get("files_created", [])
        files_modified = claude_response.get("files_modified", [])
        errors = claude_response.get("errors", [])

        # Log tool executions
        if tool_calls_info:
            for tool_call in tool_calls_info:
                ProgressTracker.add_tool_execution(
                    session_id,
                    tool_call.get("type", "unknown"),
                    {"command": tool_call.get("command", "")}
                )

        # Add context about what Claude Code did
        if script_outputs:
            response_text += "\n\n**Script Outputs:**\n" + "\n".join(script_outputs)

        if files_created:
            response_text += "\n\n**Files Created:**\n" + "\n".join(f"- {f}" for f in files_created)

        if files_modified:
            response_text += "\n\n**Files Modified:**\n" + "\n".join(f"- {f}" for f in files_modified)

        if errors:
            response_text += "\n\n**Errors:**\n" + "\n".join(errors)

        # Save assistant message
        assistant_message = Message(
            session_id=session_id,
            role="assistant",
            content=response_text
        )
        db.add(assistant_message)
        await db.commit()

        # Save tool calls to database for history
        import json
        for i, tool_call in enumerate(tool_calls_info):
            tc = ToolCall(
                message_id=assistant_message.id,
                claude_tool_id=f"claude_code_{i}",
                tool_name=tool_call.get("type", "bash"),
                arguments=json.dumps(tool_call),
                status="executed"
            )
            db.add(tc)
        await db.commit()

        # Check if git_clone was executed (look for cloned repo in workspace)
        # Update active_repo if a new repo was cloned
        if "git clone" in response_text.lower() or any("clone" in str(tc).lower() for tc in tool_calls_info):
            workspace_dir = Path(session.workspace_path)
            # Look for git repos in workspace
            for item in workspace_dir.iterdir():
                if item.is_dir() and (item / ".git").exists():
                    session.active_repo = str(item)
                    await db.commit()
                    logger.info("updated_active_repo", path=session.active_repo)
                    break

        # Mark as complete
        ProgressTracker.complete_operation(session_id, success=True)

        return ChatResponse(
            session_id=session_id,
            response=response_text,
            tool_calls=tool_calls_info,
            requires_approval=False,
            workspace_path=str(session.workspace_path)
        )

    except Exception as e:
        # Print full traceback to console for debugging
        print("=" * 80)
        print("CHAT ENDPOINT ERROR:")
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {str(e)}")
        print("\nFull traceback:")
        print(traceback.format_exc())
        print("=" * 80)

        logger.error("chat_error", error=str(e), session_id=session_id if session_id else 'unknown')
        # Mark as failed
        if session_id:
            ProgressTracker.complete_operation(session_id, success=False, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

# NOTE: /api/execute endpoint removed - Claude Code handles tool execution autonomously

@app.get("/api/session/{session_id}/history")
async def get_history(session_id: str, limit: int = 100, db: AsyncSession = Depends(get_db)):
    """Get chat history for a session.

    Args:
        session_id: Session identifier
        limit: Maximum number of messages to return (default: 100)
    """
    try:
        result = await db.execute(
            select(Message)
            .where(Message.session_id == session_id)
            .order_by(Message.timestamp.desc())
            .limit(limit)
        )
        messages = list(reversed(result.scalars().all()))

        return {
            "session_id": session_id,
            "messages": [
                {
                    "role": msg.role,
                    "content": msg.content,
                    "timestamp": msg.timestamp.isoformat()
                }
                for msg in messages
            ]
        }

    except Exception as e:
        logger.error("history_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/repos/browse")
async def browse_directory(request: BrowseRequest):
    """Browse a local directory."""
    try:
        path = Path(request.path)
        if not path.exists():
            raise HTTPException(status_code=404, detail="Path not found")

        items = workspace_manager.list_directory(path)
        is_git = workspace_manager.is_git_repo(path)

        return {
            "path": str(path),
            "items": items,
            "is_git_repo": is_git
        }

    except Exception as e:
        logger.error("browse_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/repos/clone")
async def clone_repository_endpoint(request: CloneRequest, db: AsyncSession = Depends(get_db)):
    """Clone a git repository."""
    try:
        # Get session
        result = await db.execute(select(DBSession).where(DBSession.id == request.session_id))
        session = result.scalar_one_or_none()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        # Prepare credentials
        credentials = None
        if request.username and request.token:
            credentials = {
                "username": request.username,
                "token": request.token
            }

        # Clone repository using git utils
        clone_result = await clone_repository(
            url=request.url,
            destination=Path(session.workspace_path) / "repo",
            branch=request.branch,
            credentials=credentials
        )

        if "error" in clone_result:
            raise HTTPException(status_code=400, detail=clone_result["error"])

        # Update session with cloned repo path
        session.active_repo = str(clone_result["path"])
        await db.commit()

        return clone_result

    except HTTPException:
        raise
    except Exception as e:
        logger.error("clone_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/files/{path:path}")
async def read_file(path: str):
    """Read a file."""
    try:
        file_ops = FileOperations()
        result = await file_ops.read_file(path)

        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error("read_file_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sessions")
async def get_sessions(db: AsyncSession = Depends(get_db)):
    """List all sessions."""
    try:
        sessions = await list_sessions(db)
        return {"sessions": sessions}
    except Exception as e:
        logger.error("list_sessions_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/sessions/{session_id}")
async def delete_session_endpoint(session_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a specific session and all associated data, including Claude Code instance."""
    try:
        # Cleanup Claude Code instance if running
        await cleanup_claude_instance(session_id)

        # Delete session from database
        result = await delete_session(session_id, db)
        if not result["success"]:
            raise HTTPException(status_code=404, detail=result["message"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error("delete_session_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sessions/{session_id}/validate")
async def validate_session_endpoint(session_id: str, db: AsyncSession = Depends(get_db)):
    """Validate a session's message structure."""
    try:
        result = await validate_session_messages(session_id, db)
        return result
    except Exception as e:
        logger.error("validate_session_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/sessions")
async def cleanup_sessions(db: AsyncSession = Depends(get_db)):
    """Delete all sessions (cleanup database and Claude Code instances)."""
    try:
        # Cleanup all Claude Code instances
        await cleanup_all_claude_instances()

        # Delete all sessions from database
        result = await cleanup_all_sessions(db)
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result["message"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error("cleanup_sessions_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/progress/{session_id}")
async def get_progress(session_id: str):
    """Get real-time progress for a session."""
    try:
        progress = ProgressTracker.get_progress(session_id)
        if not progress:
            return {"status": "not_found", "message": "No progress found for this session"}
        return progress
    except Exception as e:
        logger.error("get_progress_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/workspace/{session_id}/files/{file_path:path}")
async def serve_workspace_file(session_id: str, file_path: str, db: AsyncSession = Depends(get_db)):
    """Serve a file from a session's workspace for download.

    This allows the frontend to provide download links for generated reports, CSVs, etc.
    """
    try:
        # Get session to verify it exists and get workspace path
        result = await db.execute(select(DBSession).where(DBSession.id == session_id))
        session = result.scalar_one_or_none()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        # Construct full path and validate it's within workspace (security check)
        workspace_path = Path(session.workspace_path)
        full_path = workspace_path / file_path

        # Security: Prevent path traversal attacks
        try:
            full_path = full_path.resolve()
            workspace_resolved = workspace_path.resolve()
            if not str(full_path).startswith(str(workspace_resolved)):
                raise HTTPException(status_code=403, detail="Access denied: path outside workspace")
        except Exception:
            raise HTTPException(status_code=403, detail="Invalid path")

        if not full_path.exists():
            raise HTTPException(status_code=404, detail=f"File not found: {file_path}")

        if not full_path.is_file():
            raise HTTPException(status_code=400, detail="Path is not a file")

        # Determine media type based on extension
        extension = full_path.suffix.lower()
        media_types = {
            ".html": "text/html",
            ".csv": "text/csv",
            ".json": "application/json",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".pdf": "application/pdf",
            ".txt": "text/plain",
            ".md": "text/markdown",
        }
        media_type = media_types.get(extension, "application/octet-stream")

        return FileResponse(
            path=full_path,
            media_type=media_type,
            filename=full_path.name
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("serve_file_error", error=str(e), session_id=session_id, file_path=file_path)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/workspace/{session_id}/list/{directory_path:path}")
async def list_workspace_directory(session_id: str, directory_path: str = "", db: AsyncSession = Depends(get_db)):
    """List files in a workspace directory.

    Returns list of files that can be downloaded.
    """
    try:
        # Get session
        result = await db.execute(select(DBSession).where(DBSession.id == session_id))
        session = result.scalar_one_or_none()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        # Construct full path
        workspace_path = Path(session.workspace_path)
        if directory_path:
            full_path = workspace_path / directory_path
        else:
            full_path = workspace_path

        # Security check
        try:
            full_path = full_path.resolve()
            workspace_resolved = workspace_path.resolve()
            if not str(full_path).startswith(str(workspace_resolved)):
                raise HTTPException(status_code=403, detail="Access denied")
        except Exception:
            raise HTTPException(status_code=403, detail="Invalid path")

        if not full_path.exists():
            raise HTTPException(status_code=404, detail="Directory not found")

        if not full_path.is_dir():
            raise HTTPException(status_code=400, detail="Path is not a directory")

        # List files
        files = []
        for item in full_path.iterdir():
            rel_path = item.relative_to(workspace_path)
            files.append({
                "name": item.name,
                "path": str(rel_path),
                "is_dir": item.is_dir(),
                "size": item.stat().st_size if item.is_file() else None,
                "download_url": f"/api/workspace/{session_id}/files/{rel_path}" if item.is_file() else None
            })

        return {
            "session_id": session_id,
            "directory": directory_path or ".",
            "files": sorted(files, key=lambda x: (not x["is_dir"], x["name"]))
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("list_workspace_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
