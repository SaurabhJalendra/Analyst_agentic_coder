"""FastAPI main application."""
import os
import uuid
from pathlib import Path
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import structlog
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(Path(__file__).parent.parent.parent / ".env")

from app.database import init_db, get_db, Session as DBSession, Message, ToolCall
from app.workspace_manager import workspace_manager
from app.claude_service import ClaudeService
from app.tool_executor import ToolExecutor
from app.db_utils import delete_session, list_sessions, validate_session_messages, cleanup_all_sessions
from app.progress_tracker import ProgressTracker

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

# Initialize Claude service
claude_service = ClaudeService()

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

class ExecuteToolsRequest(BaseModel):
    session_id: str
    tool_calls: List[dict]

class ExecuteToolsResponse(BaseModel):
    results: List[dict]
    response: Optional[str] = None

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
    """Initialize database on startup."""
    await init_db()
    logger.info("application_started")

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
    """Handle chat message with automatic tool execution."""
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
                active_repo=request.workspace_path
            )
            db.add(session)
            await db.commit()

        # Save user message
        user_message = Message(
            session_id=session_id,
            role="user",
            content=request.message
        )
        db.add(user_message)
        await db.commit()

        # Get conversation history
        result = await db.execute(
            select(Message)
            .where(Message.session_id == session_id)
            .order_by(Message.timestamp)
        )
        history = result.scalars().all()

        # Build messages for Claude
        messages = await _build_message_history(history, db)

        # Add system context about workspace
        import platform
        os_type = platform.system()

        system_prompt = (
            f"You are a helpful coding assistant with access to file and git operations. "
            f"Current workspace: {session.workspace_path}\n"
            f"Active repository: {session.active_repo or 'None'}\n"
            f"Operating System: {os_type}\n\n"
            "IMPORTANT: "
        )

        if os_type == "Windows":
            system_prompt += (
                "The system is running on Windows. Use Windows-compatible commands:\n"
                "- Use 'dir' instead of 'ls'\n"
                "- Use 'type' instead of 'cat'\n"
                "- Use PowerShell commands when needed (e.g., Get-ChildItem, Get-Content)\n"
                "- Python commands work normally (python, pip, etc.)\n"
                "- Git commands work normally\n\n"
            )

        system_prompt += (
            "Use the available tools to help the user. When you need to perform operations, "
            "use the appropriate tools. You can use multiple tools in sequence to complete tasks."
        )

        # Start progress tracking
        ProgressTracker.start_operation(session_id, request.message)
        ProgressTracker.add_step(session_id, "📝 Message received", f"User: {request.message[:100]}...")

        # Initialize tool executor
        executor = ToolExecutor(Path(session.workspace_path))

        # Auto-execution loop: keep calling Claude and executing tools until done
        max_iterations = 25  # Allow complex multi-step operations to complete
        iteration = 0
        final_response_text = ""
        all_tool_calls_executed = []

        while iteration < max_iterations:
            iteration += 1
            logger.info("claude_iteration", iteration=iteration, messages=len(messages))

            # Update progress
            ProgressTracker.update_iteration(session_id, iteration, max_iterations, f"Iteration {iteration}/{max_iterations}")
            ProgressTracker.add_step(session_id, f"🔄 Iteration {iteration}/{max_iterations}", "Calling Claude API...")

            # Get Claude's response
            claude_response = await claude_service.send_message(
                messages=messages,
                system_prompt=system_prompt
            )

            # Extract text and tool calls
            response_text = ""
            tool_calls = []

            for block in claude_response["content"]:
                if block["type"] == "text":
                    response_text += block["text"]
                elif block["type"] == "tool_use":
                    tool_calls.append({
                        "id": block["id"],
                        "name": block["name"],
                        "input": block["input"]
                    })

            # Track Claude response
            ProgressTracker.add_claude_response(session_id, len(tool_calls) > 0, len(tool_calls))

            # Save assistant message
            assistant_message = Message(
                session_id=session_id,
                role="assistant",
                content=response_text
            )
            db.add(assistant_message)
            await db.commit()

            # Save tool calls
            import json
            for tool_call in tool_calls:
                tc = ToolCall(
                    message_id=assistant_message.id,
                    claude_tool_id=tool_call["id"],
                    tool_name=tool_call["name"],
                    arguments=json.dumps(tool_call["input"]),
                    status="executed"
                )
                db.add(tc)
            await db.commit()

            # If no tools, we're done
            if not tool_calls:
                final_response_text = response_text
                break

            # Execute tools automatically
            logger.info("executing_tools", count=len(tool_calls))

            # Track each tool execution
            for tool_call in tool_calls:
                ProgressTracker.add_tool_execution(session_id, tool_call["name"], tool_call["input"])

            results = await executor.execute_tools(tool_calls)
            all_tool_calls_executed.extend(tool_calls)

            # Add assistant message with tool_use blocks to messages
            content = []
            if response_text:
                content.append({"type": "text", "text": response_text})
            for tool_call in tool_calls:
                content.append({
                    "type": "tool_use",
                    "id": tool_call["id"],
                    "name": tool_call["name"],
                    "input": tool_call["input"]
                })

            messages.append({
                "role": "assistant",
                "content": content
            })

            # Add tool results
            tool_result_content = []
            for result_item in results:
                tool_result_content.append({
                    "type": "tool_result",
                    "tool_use_id": result_item["tool_call_id"],
                    "content": str(result_item["result"])
                })

            messages.append({
                "role": "user",
                "content": tool_result_content
            })

            # Save tool results to database as a user message
            tool_result_message = Message(
                session_id=session_id,
                role="user",
                content=json.dumps(tool_result_content)  # Store as JSON string
            )
            db.add(tool_result_message)
            await db.commit()

        if iteration >= max_iterations:
            final_response_text += "\n\n(Maximum iteration limit reached)"
            ProgressTracker.add_step(session_id, "⚠️ Max iterations reached", f"Completed {max_iterations} iterations")

        # Mark as complete
        ProgressTracker.complete_operation(session_id, success=True)

        return ChatResponse(
            session_id=session_id,
            response=final_response_text,
            tool_calls=all_tool_calls_executed,
            requires_approval=False,
            workspace_path=str(session.workspace_path)  # Return workspace path for continuity
        )

    except Exception as e:
        logger.error("chat_error", error=str(e))
        # Mark as failed
        ProgressTracker.complete_operation(session_id, success=False, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/execute", response_model=ExecuteToolsResponse)
async def execute_tools(request: ExecuteToolsRequest, db: AsyncSession = Depends(get_db)):
    """Execute approved tool calls."""
    try:
        # Get session
        result = await db.execute(select(DBSession).where(DBSession.id == request.session_id))
        session = result.scalar_one_or_none()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        # Initialize tool executor
        executor = ToolExecutor(Path(session.workspace_path))

        # Execute tools
        results = await executor.execute_tools(request.tool_calls)

        # Get conversation history
        result = await db.execute(
            select(Message)
            .where(Message.session_id == request.session_id)
            .order_by(Message.timestamp)
        )
        history = result.scalars().all()

        # Build messages for Claude including tool results
        messages = []
        last_tool_use_blocks = []

        for msg in history:
            if msg.role == "assistant":
                # Get tool calls for this message
                result = await db.execute(
                    select(ToolCall).where(ToolCall.message_id == msg.id)
                )
                tool_calls = result.scalars().all()

                # Build content with text and tool_use blocks
                content = []
                if msg.content:
                    content.append({"type": "text", "text": msg.content})

                for tc in tool_calls:
                    import json
                    content.append({
                        "type": "tool_use",
                        "id": tc.claude_tool_id,
                        "name": tc.tool_name,
                        "input": json.loads(tc.arguments)
                    })
                    last_tool_use_blocks.append(tc.claude_tool_id)

                messages.append({
                    "role": msg.role,
                    "content": content if len(content) > 1 else msg.content
                })
            else:
                messages.append({
                    "role": msg.role,
                    "content": msg.content
                })

        # Add tool results
        tool_result_content = []
        for result_item in results:
            tool_result_content.append({
                "type": "tool_result",
                "tool_use_id": result_item["tool_call_id"],
                "content": str(result_item["result"])
            })

        messages.append({
            "role": "user",
            "content": tool_result_content
        })

        # Get Claude's follow-up response
        system_prompt = (
            f"You are a helpful coding assistant. "
            f"Current workspace: {session.workspace_path}\n"
            "The tools have been executed. Summarize the results for the user."
        )

        claude_response = await claude_service.send_message(
            messages=messages,
            system_prompt=system_prompt
        )

        # Extract response text
        response_text = ""
        for block in claude_response["content"]:
            if block["type"] == "text":
                response_text += block["text"]

        # Save assistant message
        assistant_message = Message(
            session_id=request.session_id,
            role="assistant",
            content=response_text
        )
        db.add(assistant_message)
        await db.commit()

        return ExecuteToolsResponse(
            results=results,
            response=response_text
        )

    except Exception as e:
        logger.error("execute_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/session/{session_id}/history")
async def get_history(session_id: str, db: AsyncSession = Depends(get_db)):
    """Get chat history for a session."""
    try:
        result = await db.execute(
            select(Message)
            .where(Message.session_id == session_id)
            .order_by(Message.timestamp)
        )
        messages = result.scalars().all()

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
async def clone_repository(request: CloneRequest, db: AsyncSession = Depends(get_db)):
    """Clone a git repository."""
    try:
        # Get session
        result = await db.execute(select(DBSession).where(DBSession.id == request.session_id))
        session = result.scalar_one_or_none()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        # Initialize tool executor
        executor = ToolExecutor(Path(session.workspace_path))

        # Clone repo
        credentials = None
        if request.username and request.token:
            credentials = {
                "username": request.username,
                "token": request.token
            }

        result = await executor.git_ops.clone_repository(
            url=request.url,
            destination=Path(session.workspace_path) / "repo",
            branch=request.branch,
            credentials=credentials
        )

        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])

        # Update session
        session.active_repo = str(result["path"])
        await db.commit()

        return result

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
    """Delete a specific session and all associated data."""
    try:
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
    """Delete all sessions (cleanup database)."""
    try:
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
