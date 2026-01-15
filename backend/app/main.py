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

from app.database import init_db, get_db, Session as DBSession, Message, ToolCall, User
from app.workspace_manager import workspace_manager, get_claude_instance, cleanup_claude_instance, cleanup_all_claude_instances
from app.db_utils import delete_session, list_sessions, validate_session_messages, cleanup_all_sessions
from app.progress_tracker import ProgressTracker
from app.git_utils import clone_repository
from app.auth import (
    UserCreate, UserLogin, Token, UserResponse,
    get_current_user, get_current_user_optional, get_current_admin_user,
    authenticate_user, create_user, get_user_by_username, get_user_by_email,
    create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES
)
from datetime import datetime, timedelta

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


def scan_workspace_for_files(workspace_path: str, recent_only: bool = False) -> dict:
    """Scan workspace for image and report files.

    This helps detect generated visualizations even if Claude didn't
    explicitly mention the file paths in its response.

    Args:
        workspace_path: Path to the session workspace
        recent_only: If True, only look at files from last 5 minutes

    Returns:
        Dictionary with 'images' and 'reports' lists containing relative paths
    """
    import os
    from datetime import datetime

    result = {"images": [], "reports": []}
    workspace = Path(workspace_path)

    if not workspace.exists():
        return result

    # Cutoff time for recent files (5 minutes ago)
    cutoff_time = datetime.now().timestamp() - 300 if recent_only else 0

    image_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.svg'}
    report_extensions = {'.html', '.pdf', '.xlsx'}
    # Note: Excluding .csv from reports to avoid showing data files as reports

    try:
        # Walk through workspace looking for relevant files
        for root, dirs, files in os.walk(workspace):
            # Skip hidden directories and common non-output directories
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', '__pycache__', 'venv', '.git', 'data', 'raw']]

            for file in files:
                file_path = Path(root) / file
                ext = file_path.suffix.lower()

                # Skip files not matching our extensions
                if ext not in image_extensions and ext not in report_extensions:
                    continue

                # Check modification time if filtering recent only
                if recent_only:
                    try:
                        mtime = file_path.stat().st_mtime
                        if mtime < cutoff_time:
                            continue
                    except:
                        continue

                # Get relative path from workspace/repo
                try:
                    if '/repo/' in str(file_path):
                        # Get path relative to repo directory
                        repo_idx = str(file_path).find('/repo/')
                        rel_path = str(file_path)[repo_idx + 6:]  # Skip '/repo/'
                    else:
                        rel_path = str(file_path.relative_to(workspace))
                except:
                    rel_path = file_path.name

                if ext in image_extensions:
                    result["images"].append((rel_path, file_path.stat().st_mtime))
                elif ext in report_extensions:
                    result["reports"].append((rel_path, file_path.stat().st_mtime))

        # Sort by modification time (most recent first) and extract just paths
        result["images"] = [path for path, _ in sorted(result["images"], key=lambda x: -x[1])]
        result["reports"] = [path for path, _ in sorted(result["reports"], key=lambda x: -x[1])]

    except Exception as e:
        logger.error("scan_workspace_error", error=str(e), workspace=workspace_path)

    return result


def get_new_files(before_files: dict, after_files: dict) -> dict:
    """Get files that are new (exist in after but not in before).

    Args:
        before_files: Files scanned before operation
        after_files: Files scanned after operation

    Returns:
        Dictionary with 'images' and 'reports' lists containing only NEW files
    """
    before_images = set(before_files.get("images", []))
    before_reports = set(before_files.get("reports", []))

    new_images = [f for f in after_files.get("images", []) if f not in before_images]
    new_reports = [f for f in after_files.get("reports", []) if f not in before_reports]

    return {"images": new_images, "reports": new_reports}


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

@app.get("/health")
async def health():
    """Health check endpoint for Docker and monitoring."""
    return {"status": "healthy", "service": "claude-code-chatbot-api"}


# ============== Authentication Endpoints ==============

@app.post("/api/auth/register", response_model=Token)
async def register(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    """Register a new user."""
    try:
        # Check if username already exists
        existing_user = await get_user_by_username(db, user_data.username)
        if existing_user:
            raise HTTPException(
                status_code=400,
                detail="Username already registered"
            )

        # Check if email already exists
        existing_email = await get_user_by_email(db, user_data.email)
        if existing_email:
            raise HTTPException(
                status_code=400,
                detail="Email already registered"
            )

        # Create user
        user = await create_user(db, user_data)

        # Create access token
        access_token = create_access_token(
            data={"sub": user.username, "user_id": user.id}
        )

        logger.info("user_registered", username=user.username)

        return Token(
            access_token=access_token,
            token_type="bearer",
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user={
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "is_admin": user.is_admin
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("register_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/auth/login", response_model=Token)
async def login(user_data: UserLogin, db: AsyncSession = Depends(get_db)):
    """Login and get access token."""
    try:
        user = await authenticate_user(db, user_data.username, user_data.password)

        if not user:
            raise HTTPException(
                status_code=401,
                detail="Incorrect username or password"
            )

        # Update last login
        user.last_login = datetime.utcnow()
        await db.commit()

        # Create access token
        access_token = create_access_token(
            data={"sub": user.username, "user_id": user.id}
        )

        logger.info("user_logged_in", username=user.username)

        return Token(
            access_token=access_token,
            token_type="bearer",
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user={
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "is_admin": user.is_admin
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("login_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/auth/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information."""
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        is_active=current_user.is_active,
        is_admin=current_user.is_admin,
        created_at=current_user.created_at
    )


@app.post("/api/auth/refresh", response_model=Token)
async def refresh_token(current_user: User = Depends(get_current_user)):
    """Refresh access token."""
    access_token = create_access_token(
        data={"sub": current_user.username, "user_id": current_user.id}
    )

    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user={
            "id": current_user.id,
            "username": current_user.username,
            "email": current_user.email,
            "is_admin": current_user.is_admin
        }
    )


# ============== Protected Chat Endpoints ==============

@app.post("/api/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
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
            # Verify session belongs to current user
            if session.user_id and session.user_id != current_user.id:
                raise HTTPException(status_code=403, detail="Access denied to this session")
        else:
            session_id = str(uuid.uuid4())
            workspace_path = workspace_manager.create_session_workspace(session_id)
            session = DBSession(
                id=session_id,
                user_id=current_user.id,
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
                    # Get GitHub credentials from environment
                    github_token = os.getenv("GITHUB_ACCESS_TOKEN")
                    git_credentials = None
                    if github_token:
                        git_credentials = {
                            "username": "git",  # GitHub uses 'git' as username with PAT
                            "token": github_token
                        }

                    # Clone the default repository
                    clone_result = await clone_repository(
                        url=default_repo_url,
                        destination=Path(session.workspace_path) / "repo",
                        branch=default_repo_branch,
                        credentials=git_credentials
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

        # Scan workspace BEFORE sending message to track existing files
        files_before = scan_workspace_for_files(session.workspace_path)

        claude_code_service = await get_claude_instance(session_id, workspace_path)

        # Send message to Claude Code CLI (it handles all tool execution autonomously)
        ProgressTracker.add_step(session_id, "💬 Sending to Claude Code", "Processing request...")

        claude_response = await claude_code_service.send_message(
            user_message=request.message,
            timeout=7200  # 2 hour timeout for very long-running tasks
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

        # Scan workspace AFTER response to find NEW files created during this interaction
        # This ensures each message only shows visualizations generated for THAT specific message
        files_after = scan_workspace_for_files(session.workspace_path)
        new_files = get_new_files(files_before, files_after)

        if new_files["images"] or new_files["reports"]:
            if new_files["images"]:
                response_text += "\n\n**Generated Visualizations:**\n"
                for img_path in new_files["images"]:
                    response_text += f"- `{img_path}`\n"
            if new_files["reports"]:
                response_text += "\n\n**Generated Reports:**\n"
                for report_path in new_files["reports"]:
                    response_text += f"- `{report_path}`\n"

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
    """Read a file from the filesystem.

    Note: For workspace files, prefer using /api/workspace/{session_id}/files/{path}
    which includes security checks.
    """
    try:
        file_path = Path(path)

        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found")

        if not file_path.is_file():
            raise HTTPException(status_code=400, detail="Path is not a file")

        # Read file content
        content = file_path.read_text(encoding='utf-8', errors='replace')

        return {
            "path": str(file_path),
            "content": content,
            "size": file_path.stat().st_size
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("read_file_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sessions")
async def get_sessions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all sessions for current user."""
    from sqlalchemy.orm import selectinload
    try:
        # Filter sessions by user_id, eagerly load messages for count
        result = await db.execute(
            select(DBSession)
            .options(selectinload(DBSession.messages))
            .where(DBSession.user_id == current_user.id)
            .order_by(DBSession.created_at.desc())
        )
        sessions = result.scalars().all()

        return {
            "sessions": [
                {
                    "id": s.id,
                    "created_at": s.created_at.isoformat() if s.created_at else None,
                    "workspace_path": s.workspace_path,
                    "active_repo": s.active_repo,
                    "message_count": len(s.messages) if s.messages else 0
                }
                for s in sessions
            ]
        }
    except Exception as e:
        logger.error("list_sessions_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/sessions/{session_id}")
async def delete_session_endpoint(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a specific session and all associated data, including Claude Code instance."""
    try:
        # Verify session belongs to current user
        result = await db.execute(select(DBSession).where(DBSession.id == session_id))
        session = result.scalar_one_or_none()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        if session.user_id and session.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied to this session")

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


@app.get("/api/workspace/{session_id}/visualizations")
async def get_session_visualizations(session_id: str, db: AsyncSession = Depends(get_db)):
    """Get all visualization files (images and reports) for a session.

    This endpoint returns all generated images and reports in the workspace,
    which can be displayed in the chat interface.
    """
    try:
        # Get session
        result = await db.execute(select(DBSession).where(DBSession.id == session_id))
        session = result.scalar_one_or_none()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        # Scan workspace for files (no time restriction)
        files = scan_workspace_for_files(session.workspace_path, recent_only=False)

        return {
            "session_id": session_id,
            "images": files["images"],
            "reports": files["reports"],
            "base_url": f"/api/workspace/{session_id}/files/repo"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_visualizations_error", error=str(e), session_id=session_id)
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
