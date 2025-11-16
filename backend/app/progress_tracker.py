"""Progress tracking for long-running operations."""
from datetime import datetime
from typing import Dict, List, Optional
import structlog

logger = structlog.get_logger()

# In-memory storage for progress (keyed by session_id)
_progress_store: Dict[str, Dict] = {}


class ProgressTracker:
    """Track progress of chat operations."""

    @staticmethod
    def start_operation(session_id: str, message: str):
        """Start tracking an operation."""
        _progress_store[session_id] = {
            "status": "processing",
            "started_at": datetime.utcnow().isoformat(),
            "message": message,
            "current_step": "Initializing...",
            "iteration": 0,
            "max_iterations": 0,
            "steps": [],
            "completed": False,
            "error": None
        }
        logger.info("progress_started", session_id=session_id)

    @staticmethod
    def update_iteration(session_id: str, iteration: int, max_iterations: int, step_description: str):
        """Update current iteration."""
        if session_id in _progress_store:
            _progress_store[session_id]["iteration"] = iteration
            _progress_store[session_id]["max_iterations"] = max_iterations
            _progress_store[session_id]["current_step"] = step_description
            logger.info("progress_iteration", session_id=session_id, iteration=iteration)

    @staticmethod
    def add_step(session_id: str, step: str, details: Optional[str] = None):
        """Add a completed step."""
        if session_id in _progress_store:
            step_data = {
                "step": step,
                "timestamp": datetime.utcnow().isoformat(),
                "details": details
            }
            _progress_store[session_id]["steps"].append(step_data)
            _progress_store[session_id]["current_step"] = step
            logger.info("progress_step_added", session_id=session_id, step=step)

    @staticmethod
    def add_tool_execution(session_id: str, tool_name: str, tool_input: dict):
        """Add a tool execution step."""
        if session_id in _progress_store:
            # Simplify input for display
            input_summary = str(tool_input)
            if len(input_summary) > 100:
                input_summary = input_summary[:97] + "..."

            step = f"🔧 {tool_name}"
            details = input_summary

            ProgressTracker.add_step(session_id, step, details)

    @staticmethod
    def add_claude_response(session_id: str, has_tool_calls: bool, tool_count: int = 0):
        """Add Claude API response step."""
        if session_id in _progress_store:
            if has_tool_calls:
                step = f"🤖 Claude responded with {tool_count} tool(s) to execute"
            else:
                step = "🤖 Claude provided final response"

            ProgressTracker.add_step(session_id, step)

    @staticmethod
    def complete_operation(session_id: str, success: bool = True, error: Optional[str] = None):
        """Mark operation as complete."""
        if session_id in _progress_store:
            _progress_store[session_id]["completed"] = True
            _progress_store[session_id]["status"] = "completed" if success else "failed"
            _progress_store[session_id]["error"] = error
            _progress_store[session_id]["completed_at"] = datetime.utcnow().isoformat()

            if success:
                _progress_store[session_id]["current_step"] = "✅ Completed"
            else:
                _progress_store[session_id]["current_step"] = f"❌ Failed: {error}"

            logger.info("progress_completed", session_id=session_id, success=success)

    @staticmethod
    def get_progress(session_id: str) -> Optional[Dict]:
        """Get current progress for a session."""
        return _progress_store.get(session_id)

    @staticmethod
    def clear_progress(session_id: str):
        """Clear progress for a session."""
        if session_id in _progress_store:
            del _progress_store[session_id]
            logger.info("progress_cleared", session_id=session_id)

    @staticmethod
    def cleanup_old_progress(max_age_hours: int = 24):
        """Clean up old progress entries."""
        from datetime import timedelta
        cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)

        to_remove = []
        for session_id, data in _progress_store.items():
            started_at = datetime.fromisoformat(data["started_at"])
            if started_at < cutoff:
                to_remove.append(session_id)

        for session_id in to_remove:
            del _progress_store[session_id]

        if to_remove:
            logger.info("progress_cleanup", removed_count=len(to_remove))
