"""FastAPI main application."""
import asyncio
import os
import sqlite3
import uuid
import traceback
from io import BytesIO
from datetime import datetime, UTC
from pathlib import Path
from typing import Any, Callable, List, Optional
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
import structlog
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(Path(__file__).parent.parent.parent / ".env")

from app.artifact_store import get_artifact
from app.audit_logger import AuditLogger
from app.database import init_db, get_db, Session as DBSession, Message, ToolCall
from app.workspace_manager import workspace_manager, get_claude_instance, cleanup_claude_instance, cleanup_all_claude_instances
from app.db_utils import delete_session, list_sessions, validate_session_messages, cleanup_all_sessions
from app.git_utils import clone_repository
from app.event_broker import EventBroker
from app.event_schema import DoneEvent

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
app = FastAPI(title="Quant Agent API")

# Rate limiter — keyed on remote IP. Limits are conservative defaults; in
# production, mount per-session-id keying once the auth layer lands.
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS middleware — explicit allowlist (was "*"; tightened for security)
_cors_origins_env = os.environ.get("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000")
_cors_origins = [o.strip() for o in _cors_origins_env.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "Last-Event-ID"],
)

# Initialize Claude service (API-based - kept for backwards compatibility)
# claude_service = ClaudeService()
# Note: Now using Claude Code CLI instances managed per-session

# Operator identity — used as client_slug in audit rows.
# Override via OPERATOR_NAME env var in production deployments.
OPERATOR: str = os.environ.get("OPERATOR_NAME", "local")

# Module-level SSE event broker (injectable for testing)
_broker = EventBroker()


def get_broker() -> EventBroker:
    """Dependency: returns the module-level EventBroker."""
    return _broker


# Path to the audit/artifacts SQLite DB — declared here so get_audit_logger()
# and the Phase 3 endpoints share the same reference. Tests monkeypatch this.
# (The duplicate declaration further down is removed below.)
_audit_db_path: Path = Path(__file__).parent.parent / "chatbot.db"

# Module-level audit logger (injectable for testing via get_audit_logger dep).
_audit_logger: AuditLogger = AuditLogger(_audit_db_path)


def get_audit_logger() -> AuditLogger:
    """Dependency: returns the module-level AuditLogger."""
    return _audit_logger


def get_claude_factory() -> Callable[..., Any]:
    """Dependency-injectable factory; tests override this to inject a mock-CLI service."""
    from app.claude_code_service import ClaudeCodeService

    def factory(*, workspace_path: Path, session_id: str) -> ClaudeCodeService:
        return ClaudeCodeService(
            workspace_path=workspace_path,
            session_id=session_id,
            broker=_broker,
            audit_logger=_audit_logger,
            operator=OPERATOR,
            artifacts_db_path=_audit_db_path,
        )
    return factory

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


# ---------------------------------------------------------------------------
# Phase 3 – Pydantic models
# ---------------------------------------------------------------------------

class AuditRow(BaseModel):
    id: int
    ts: str
    event_type: str
    audit_id: str
    data: dict


class AuditLogResponse(BaseModel):
    session_id: str
    rows: List[AuditRow]
    next_before_id: int | None = None


class PDFExportRequest(BaseModel):
    session_id: str
    artifact_ids: list[str] | None = None
    narrative: str | None = None


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

    _chart_example = (
        '{"title": "Price", "data": [{"type": "scatter", "x": [1, 2], '
        '"y": [10, 20], "mode": "lines"}], '
        '"layout": {"xaxis": {"title": "Day"}, "yaxis": {"title": "USD"}}}'
    )
    system_prompt += (
        "Use the available tools to help the user. When you need to perform operations, "
        "use the appropriate tools. You can use multiple tools in sequence to complete tasks.\n\n"
        "REMEMBER: You are working in the active repository shown above. "
        "All git commands will automatically target this repository unless you specify otherwise.\n\n"
        "CHART CONVENTION:\n"
        "To produce a chart that renders in the UI, write a file named "
        "artifacts/<name>.chart.json in the workspace root. "
        'The file must be a valid Plotly payload: {"title": str, "data": [traces], "layout": {}}. '
        "Example (a 2-point scatter): "
        + _chart_example + "\n"
        "Create the artifacts/ directory if it does not exist before writing.\n\n"
        "MARKET DATA:\n"
        "You may use yfinance to pull equity OHLCV data. Save it as "
        "data/<ticker>.parquet in the workspace for backtests and analysis. "
        "Example: import yfinance as yf; yf.download('SPY', period='1y').to_parquet('data/SPY.parquet')."
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
    return {"message": "Quant Agent API", "status": "running"}

@app.get("/health")
async def health():
    """Health check endpoint for Docker and monitoring."""
    return {"status": "healthy", "service": "claude-code-chatbot-api"}

@app.post("/api/chat", status_code=202)
@limiter.limit("20/minute")
async def chat(
    request: Request,  # noqa: F811 — slowapi requires Request as first arg
    chat_request: ChatRequest,
    db: AsyncSession = Depends(get_db),
    broker: EventBroker = Depends(get_broker),
    claude_factory=Depends(get_claude_factory),
    audit: AuditLogger = Depends(get_audit_logger),
):
    """Handle chat message — fires Claude Code in the background and returns 202 immediately."""
    session_id = None
    try:
        # Get or create session
        if chat_request.session_id:
            session_id = chat_request.session_id
            result = await db.execute(select(DBSession).where(DBSession.id == session_id))
            session = result.scalar_one_or_none()
            if not session:
                # Session not in DB — create workspace + record so streaming can proceed
                workspace_path = workspace_manager.create_session_workspace(session_id)
                session = DBSession(
                    id=session_id,
                    workspace_path=str(workspace_path),
                    active_repo=None,
                )
                db.add(session)
                await db.commit()
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

        # Save user message to DB before returning 202
        user_message_record = Message(
            session_id=session_id,
            role="user",
            content=chat_request.message
        )
        db.add(user_message_record)
        await db.commit()

        # Audit the user prompt — failure must NOT fail the chat request.
        try:
            await audit.append_event(
                session_id,
                "user.prompt",
                {"text": chat_request.message},
                OPERATOR,
            )
        except Exception as _audit_exc:
            logger.warning("audit_user_prompt_failed", error=str(_audit_exc), session_id=session_id)

        # Determine working directory for Claude Code
        workspace_path = Path(session.active_repo) if session.active_repo else Path(session.workspace_path)

        # Get or create ClaudeCodeService for this session
        service = workspace_manager.get_or_create_service(
            session_id=session_id,
            factory=lambda: claude_factory(workspace_path=workspace_path, session_id=session_id),
        )

        # Fire and forget — SSE stream carries progress to the frontend
        asyncio.create_task(service.send_message(chat_request.message))

        return {
            "session_id": session_id,
            "event_stream_url": f"/api/chat/stream/{session_id}",
        }

    except HTTPException:
        raise
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
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/chat/stream/{session_id}")
async def chat_stream(
    session_id: str,
    request: Request,
    broker: EventBroker = Depends(get_broker),
) -> EventSourceResponse:
    """SSE endpoint — streams events from the per-session EventBroker."""
    last_event_id_header = request.headers.get("Last-Event-ID", "0")
    try:
        last_event_id = int(last_event_id_header)
    except ValueError:
        last_event_id = 0

    from collections.abc import AsyncGenerator

    async def event_source() -> AsyncGenerator[bytes, None]:
        sub = await broker.subscribe(session_id, last_event_id=last_event_id)
        async for buffered in sub:
            # Emit data before event so clients that break on "event: done"
            # still receive the done payload in the preceding data line.
            sep = "\r\n"
            yield (
                f"id: {buffered.id}{sep}"
                f"data: {buffered.event.model_dump_json()}{sep}"
                f"event: {buffered.event.type}{sep}"
                f"{sep}"
            ).encode()
            if isinstance(buffered.event, DoneEvent):
                return

    return EventSourceResponse(event_source())

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

# NOTE: /api/files/{path:path} was REMOVED — it was an unguarded path-traversal
# hole that read any file the backend process could access. Use the
# workspace-scoped /api/workspace/{session_id}/files/{path:path} instead.

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

# NOTE: /api/progress/{session_id} was REMOVED — replaced by SSE
# /api/chat/stream/{session_id}. Progress is now streamed live as typed events.

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

        # Security: prevent path traversal AND symlink-escape. We resolve both
        # paths (following symlinks) and require the full_path to be a
        # descendant of workspace_resolved. Using `relative_to` raises
        # ValueError on escape — safer than string startswith which can be
        # fooled by sibling directories sharing a prefix (e.g. `/ws-evil`
        # passes `startswith("/ws")`).
        try:
            full_path = full_path.resolve(strict=False)
            workspace_resolved = workspace_path.resolve(strict=False)
            full_path.relative_to(workspace_resolved)  # raises if outside
        except (ValueError, OSError):
            raise HTTPException(status_code=403, detail="Access denied: path outside workspace")

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

        # Security: prevent path traversal AND symlink-escape. Resolve both
        # paths (following symlinks); require full_path to be a descendant of
        # workspace_resolved. relative_to() raises ValueError on escape —
        # safer than str.startswith(), which a sibling dir sharing a prefix
        # (e.g. workspace `/ws` vs `/ws-evil`) would defeat.
        try:
            full_path = full_path.resolve(strict=False)
            workspace_resolved = workspace_path.resolve(strict=False)
            full_path.relative_to(workspace_resolved)  # raises if outside
        except (ValueError, OSError):
            raise HTTPException(status_code=403, detail="Access denied: path outside workspace")

        if not full_path.exists():
            raise HTTPException(status_code=404, detail="Directory not found")

        if not full_path.is_dir():
            raise HTTPException(status_code=400, detail="Path is not a directory")

        # List files (use resolved workspace for relative_to since iterdir returns
        # paths under the resolved full_path)
        files = []
        for item in full_path.iterdir():
            rel_path = item.relative_to(workspace_resolved)
            files.append({
                "name": item.name,
                "path": str(rel_path).replace("\\", "/"),
                "is_dir": item.is_dir(),
                "size": item.stat().st_size if item.is_file() else None,
                "download_url": f"/api/workspace/{session_id}/files/{str(rel_path).replace(chr(92), '/')}" if item.is_file() else None
            })

        return {
            "session_id": session_id,
            "directory": directory_path or ".",
            "items": sorted(files, key=lambda x: (not x["is_dir"], x["name"])),
            "files": sorted(files, key=lambda x: (not x["is_dir"], x["name"])),  # kept for frontend compat
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("list_workspace_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Phase 3 endpoints
# ---------------------------------------------------------------------------

@app.get("/api/audit/{session_id}", response_model=AuditLogResponse)
async def get_audit_log(
    session_id: str,
    limit: int = 50,
    before_id: int | None = None,
) -> AuditLogResponse:
    """Return paginated audit log rows for a session (most-recent first)."""
    try:
        conn = sqlite3.connect(_audit_db_path)
        try:
            if before_id is not None:
                cur = conn.execute(
                    "SELECT id, ts, event_type, audit_id, data_json "
                    "FROM audit_log "
                    "WHERE session_id = ? AND id < ? "
                    "ORDER BY id DESC LIMIT ?",
                    (session_id, before_id, limit),
                )
            else:
                cur = conn.execute(
                    "SELECT id, ts, event_type, audit_id, data_json "
                    "FROM audit_log "
                    "WHERE session_id = ? "
                    "ORDER BY id DESC LIMIT ?",
                    (session_id, limit),
                )
            db_rows = cur.fetchall()
        finally:
            conn.close()
    except Exception as e:
        logger.error("audit_log_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e

    import json as _json

    rows = [
        AuditRow(
            id=r[0],
            ts=r[1],
            event_type=r[2],
            audit_id=r[3],
            data=_json.loads(r[4]),
        )
        for r in db_rows
    ]
    next_before_id = rows[-1].id if len(rows) == limit else None
    return AuditLogResponse(session_id=session_id, rows=rows, next_before_id=next_before_id)


@app.get("/api/artifacts/{artifact_id}/methodology")
async def get_artifact_methodology(artifact_id: str) -> dict[str, object]:  # noqa: PLR0912
    """Return a structured methodology summary for how an artifact was produced."""
    import json as _json

    art_row: tuple[str, ...] | None = None
    audit_rows: list[tuple[str, ...]] = []
    try:
        conn = sqlite3.connect(_audit_db_path)
        try:
            # Fetch the artifact record
            art_row = conn.execute(
                "SELECT id, session_id, kind, title, source_attribution, "
                "methodology_id, file_path, created_at "
                "FROM artifacts WHERE id = ?",
                (artifact_id,),
            ).fetchone()

            if art_row is not None:
                _art_session_id = art_row[1]
                # Walk the audit log for the same session to collect context
                audit_rows = conn.execute(
                    "SELECT id, ts, event_type, data_json FROM audit_log "
                    "WHERE session_id = ? ORDER BY id ASC",
                    (_art_session_id,),
                ).fetchall()
        finally:
            conn.close()
    except Exception as e:
        logger.error("methodology_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e

    if art_row is None:
        raise HTTPException(status_code=404, detail=f"Artifact '{artifact_id}' not found")

    (
        art_id, session_id, kind, title,
        source_attribution, methodology_id, file_path, created_at,
    ) = art_row

    # Parse audit rows into structured data
    tool_calls: list[dict[str, Any]] = []
    sources: list[dict[str, Any]] = []
    agents: set[str] = set()

    for _row_id, _ts, event_type, data_json in audit_rows:
        try:
            data = _json.loads(data_json)
        except _json.JSONDecodeError:
            continue

        if event_type == "tool.start":
            tool_calls.append({
                "tool": data.get("tool", "unknown"),
                "args_redacted": data.get("args_redacted", {}),
                "duration_ms": None,
            })
            if agent_id := data.get("agent_id"):
                agents.add(agent_id)
        elif event_type == "tool.done":
            # Backfill duration on last tool.start with matching call_id
            call_id = data.get("call_id")
            for tc in reversed(tool_calls):
                if tc.get("_call_id") == call_id and tc["duration_ms"] is None:
                    tc["duration_ms"] = data.get("duration_ms")
                    break
        elif event_type == "source":
            source_name = data.get("source", "unknown")
            existing = next((s for s in sources if s["source"] == source_name), None)
            if existing:
                existing["count"] = existing.get("count", 0) + 1
            else:
                sources.append({
                    "source": source_name,
                    "operation": data.get("operation", ""),
                    "count": 1,
                })
        elif event_type in ("subagent.spawn", "subagent.done"):
            if agent_id := data.get("agent_id"):
                agents.add(agent_id)

    # Build narrative (templated, no LLM)
    tool_names: list[str] = list({str(tc["tool"]) for tc in tool_calls})
    source_names: list[str] = [str(s["source"]) for s in sources]
    agents_list = sorted(agents) or ["main"]

    tool_names_str = ", ".join(tool_names) if tool_names else "none"
    source_names_str = ", ".join(source_names) if source_names else "none"
    agents_str = "`, `".join(agents_list)
    narrative = (
        f"Generated by agent(s) `{agents_str}` using {len(tool_calls)} tool call(s) "
        f"({tool_names_str}). "
        f"Accessed {len(sources)} data source(s) ({source_names_str}).\n\n"
        f"This artifact was produced during session `{session_id}`. "
        f"The audit trail above captures every tool invocation and source access that "
        f"occurred in that session and may have contributed to this artifact."
    )

    return {
        "artifact_id": art_id,
        "title": title,
        "source_attribution": source_attribution,
        "created_at": created_at,
        "methodology": {
            "tool_calls": tool_calls,
            "sources": sources,
            "agents_involved": agents_list,
            "narrative": narrative,
        },
    }


@app.get("/api/artifacts/{artifact_id}/payload")
async def get_artifact_payload(artifact_id: str) -> dict[str, object]:
    """Return the stored payload for a chart artifact.

    For kind='chart': reads the on-disk *.chart.json and returns
    ``{"artifact_id", "kind", "title", "payload": {"data", "layout"}}``.
    Returns 404 for unknown artifact IDs, missing files, or non-chart kinds.
    """
    import json as _json

    row = get_artifact(_audit_db_path, artifact_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Artifact '{artifact_id}' not found")

    if row["kind"] != "chart":
        raise HTTPException(
            status_code=404,
            detail=f"No payload for artifact kind '{row['kind']}' — only charts have payloads",
        )

    file_path = row.get("file_path")
    if not file_path:
        raise HTTPException(
            status_code=404,
            detail="Artifact has no associated file",
        )

    chart_file = Path(file_path)
    if not chart_file.is_file():
        raise HTTPException(
            status_code=404,
            detail=f"Chart file not found on disk: {file_path}",
        )

    try:
        payload = _json.loads(chart_file.read_text(encoding="utf-8"))
    except (OSError, _json.JSONDecodeError) as exc:
        logger.error("artifact_payload_read_error", error=str(exc), artifact_id=artifact_id)
        raise HTTPException(status_code=500, detail="Failed to read chart file") from exc

    return {
        "artifact_id": artifact_id,
        "kind": "chart",
        "title": row["title"],
        "payload": {
            "data": payload.get("data", []),
            "layout": payload.get("layout", {}),
        },
    }


@app.post("/api/export/pdf")
async def export_pdf(body: PDFExportRequest) -> StreamingResponse:  # noqa: PLR0915
    """Generate a branded PDF report for one or more artifacts."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, PageBreak, HRFlowable,
    )

    session_id = body.session_id

    # Fetch artifacts from DB.
    # If artifact_ids is explicitly set to an empty list, skip the DB entirely.
    art_rows: list[tuple[str, ...]] = []
    if body.artifact_ids is None or len(body.artifact_ids) > 0:
        try:
            conn = sqlite3.connect(_audit_db_path)
            try:
                if body.artifact_ids:
                    placeholders = ",".join("?" * len(body.artifact_ids))
                    art_rows = conn.execute(
                        f"SELECT id, title, source_attribution, file_path, created_at "  # noqa: S608
                        f"FROM artifacts WHERE session_id = ? AND id IN ({placeholders})",
                        [session_id, *body.artifact_ids],
                    ).fetchall()
                else:
                    # artifact_ids is None: export all for this session
                    art_rows = conn.execute(
                        "SELECT id, title, source_attribution, file_path, created_at "
                        "FROM artifacts WHERE session_id = ?",
                        (session_id,),
                    ).fetchall()
            finally:
                conn.close()
        except Exception as e:
            logger.error("pdf_export_db_error", error=str(e))
            raise HTTPException(status_code=500, detail=str(e)) from e

    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2.5 * cm,
        bottomMargin=2.5 * cm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "QCTitle",
        parent=styles["Title"],
        fontSize=28,
        spaceAfter=12,
        textColor=colors.HexColor("#1a1a2e"),
    )
    heading_style = ParagraphStyle(
        "QCHeading",
        parent=styles["Heading1"],
        fontSize=16,
        spaceBefore=18,
        spaceAfter=6,
        textColor=colors.HexColor("#16213e"),
    )
    subheading_style = ParagraphStyle(
        "QCSubheading",
        parent=styles["Heading2"],
        fontSize=12,
        spaceBefore=10,
        spaceAfter=4,
        textColor=colors.HexColor("#0f3460"),
    )
    body_style = styles["BodyText"]
    small_style = ParagraphStyle(
        "QCSmall",
        parent=styles["BodyText"],
        fontSize=8,
        textColor=colors.grey,
    )

    story = []

    # --- Cover page ---
    story.append(Spacer(1, 3 * cm))
    story.append(Paragraph("Quant Agent", title_style))
    story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#1a1a2e")))
    story.append(Spacer(1, 0.5 * cm))
    story.append(Paragraph(f"Session: <b>{session_id}</b>", body_style))
    report_date = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    story.append(Paragraph(f"Report Date: <b>{report_date}</b>", body_style))
    story.append(Paragraph(f"Artifacts: <b>{len(art_rows)}</b>", body_style))
    story.append(PageBreak())

    # --- One section per artifact ---
    for art_id, art_title, source_attr, file_path, created_at in art_rows:
        story.append(Paragraph(art_title or "Untitled Artifact", heading_style))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#0f3460")))
        story.append(Paragraph(f"Artifact ID: {art_id}", small_style))
        story.append(Paragraph(f"Created: {created_at}", small_style))
        story.append(Spacer(1, 0.3 * cm))
        story.append(Paragraph(f"<b>Source Attribution:</b> {source_attr}", body_style))

        if file_path:
            story.append(Spacer(1, 0.2 * cm))
            story.append(Paragraph(f"See attached file: <i>{file_path}</i>", small_style))

        story.append(Spacer(1, 0.5 * cm))
        story.append(Paragraph("How this was made", subheading_style))
        methodology_text = (
            f"Methodology details are available via the "
            f"<b>/api/artifacts/{art_id}/methodology</b> endpoint. "
            "The full audit trail records every tool call, source access, "
            "and agent activity that contributed to this artifact."
        )
        story.append(Paragraph(methodology_text, body_style))
        story.append(PageBreak())

    # --- Optional narrative ---
    if body.narrative:
        story.append(Paragraph("Additional Notes", heading_style))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#0f3460")))
        story.append(Spacer(1, 0.3 * cm))
        for line in body.narrative.splitlines():
            story.append(Paragraph(line or "&nbsp;", body_style))
        story.append(PageBreak())

    # --- Disclosures page ---
    story.append(Paragraph("Disclosures", heading_style))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.grey))
    story.append(Spacer(1, 0.3 * cm))
    disclosures = (
        "This report was generated automatically by Quant Agent. "
        "The information contained herein is derived from automated analysis and "
        "should not be construed as financial or investment advice. "
        "All data sources are attributed within each artifact section. "
        "Past performance is not indicative of future results. "
        "Recipients should conduct their own due diligence before acting on any "
        "information presented in this report. "
        "Quant Agent and its operators make no representations or warranties "
        "regarding the accuracy or completeness of the data presented."
    )
    story.append(Paragraph(disclosures, body_style))

    doc.build(story)
    buf.seek(0)

    filename = f"quant_console_{session_id[:8]}_{datetime.now(UTC).strftime('%Y%m%d')}.pdf"
    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
