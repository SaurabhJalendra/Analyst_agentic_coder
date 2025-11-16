"""Database utility functions for cleanup and maintenance."""
import structlog
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import Session, Message, ToolCall

logger = structlog.get_logger()


async def delete_session(session_id: str, db: AsyncSession) -> dict:
    """Delete a session and all associated data.

    Args:
        session_id: Session ID to delete
        db: Database session

    Returns:
        Dict with status and message
    """
    try:
        # Check if session exists
        result = await db.execute(select(Session).where(Session.id == session_id))
        session = result.scalar_one_or_none()

        if not session:
            return {"success": False, "message": f"Session {session_id} not found"}

        # Delete session (cascades to messages and tool_calls)
        await db.delete(session)
        await db.commit()

        logger.info("session_deleted", session_id=session_id)
        return {
            "success": True,
            "message": f"Session {session_id} and all associated data deleted successfully"
        }

    except Exception as e:
        logger.error("session_deletion_failed", session_id=session_id, error=str(e))
        await db.rollback()
        return {"success": False, "message": f"Error deleting session: {str(e)}"}


async def list_sessions(db: AsyncSession) -> list:
    """List all sessions with basic info.

    Args:
        db: Database session

    Returns:
        List of session info dicts
    """
    try:
        result = await db.execute(select(Session))
        sessions = result.scalars().all()

        session_list = []
        for session in sessions:
            # Count messages
            msg_result = await db.execute(
                select(Message).where(Message.session_id == session.id)
            )
            messages = msg_result.scalars().all()

            session_list.append({
                "id": session.id,
                "created_at": session.created_at.isoformat(),
                "workspace_path": session.workspace_path,
                "active_repo": session.active_repo,
                "message_count": len(messages)
            })

        return session_list

    except Exception as e:
        logger.error("list_sessions_failed", error=str(e))
        return []


async def validate_session_messages(session_id: str, db: AsyncSession) -> dict:
    """Validate that a session's messages have proper tool_use/tool_result pairing.

    Args:
        session_id: Session ID to validate
        db: Database session

    Returns:
        Dict with validation results
    """
    try:
        # Get all messages for session
        result = await db.execute(
            select(Message)
            .where(Message.session_id == session_id)
            .order_by(Message.timestamp)
        )
        messages = result.scalars().all()

        issues = []

        for i, msg in enumerate(messages):
            if msg.role == "assistant":
                # Get tool calls
                tc_result = await db.execute(
                    select(ToolCall).where(ToolCall.message_id == msg.id)
                )
                tool_calls = tc_result.scalars().all()

                if tool_calls:
                    # Check if next message is user with tool_results
                    if i + 1 < len(messages):
                        next_msg = messages[i + 1]
                        if next_msg.role != "user":
                            issues.append({
                                "message_index": i,
                                "message_id": msg.id,
                                "issue": f"Assistant message with {len(tool_calls)} tool_use blocks not followed by user message"
                            })
                        elif not next_msg.content or not next_msg.content.startswith('['):
                            issues.append({
                                "message_index": i,
                                "message_id": msg.id,
                                "issue": f"Assistant message with {len(tool_calls)} tool_use blocks not followed by tool_result message"
                            })
                    else:
                        issues.append({
                            "message_index": i,
                            "message_id": msg.id,
                            "issue": f"Assistant message with {len(tool_calls)} tool_use blocks has no following message"
                        })

        return {
            "session_id": session_id,
            "total_messages": len(messages),
            "issues_found": len(issues),
            "is_valid": len(issues) == 0,
            "issues": issues
        }

    except Exception as e:
        logger.error("validation_failed", session_id=session_id, error=str(e))
        return {
            "session_id": session_id,
            "error": str(e),
            "is_valid": False
        }


async def cleanup_all_sessions(db: AsyncSession) -> dict:
    """Delete all sessions from database.

    Args:
        db: Database session

    Returns:
        Dict with cleanup results
    """
    try:
        result = await db.execute(select(Session))
        sessions = result.scalars().all()

        count = len(sessions)

        for session in sessions:
            await db.delete(session)

        await db.commit()

        logger.info("all_sessions_deleted", count=count)
        return {
            "success": True,
            "message": f"Deleted {count} sessions successfully"
        }

    except Exception as e:
        logger.error("cleanup_failed", error=str(e))
        await db.rollback()
        return {"success": False, "message": f"Error during cleanup: {str(e)}"}
