"""Integration test: POST /api/chat → audit_log rows are written.

Uses the mock-CLI fixture pattern from test_chat_streaming.py.
Monkeypatches _audit_db_path and overrides the get_audit_logger /
get_claude_factory dependencies so everything points at a tmp DB.
"""
from __future__ import annotations

import asyncio
import sqlite3
import sys
from pathlib import Path

import httpx
import pytest

from app.audit_logger import AuditLogger
from app.claude_code_service import ClaudeCodeService
from app.event_broker import EventBroker
from app.main import app, get_audit_logger, get_broker, get_claude_factory
from migrations.run import apply_pending


@pytest.fixture
def mock_claude_cmd(fixtures_dir: Path) -> list[str]:
    return [sys.executable, str(fixtures_dir / "mock_claude.py")]


@pytest.fixture
def audit_db(tmp_path: Path) -> Path:
    """A fresh SQLite DB with migrations applied, for audit isolation."""
    db_path = tmp_path / "audit_integration.db"
    apply_pending(db_path)
    return db_path


@pytest.fixture
def app_with_audit(mock_claude_cmd, fixtures_dir, tmp_path, audit_db, monkeypatch):
    """Full app wiring: mock CLI + real AuditLogger pointing at a tmp DB."""
    fixture = fixtures_dir / "stream_json" / "multi_step.jsonl"
    broker = EventBroker()
    audit = AuditLogger(audit_db)

    # Patch the module-level path so the endpoints that open _audit_db_path
    # directly (e.g. GET /api/audit) also use the tmp DB.
    monkeypatch.setattr("app.main._audit_db_path", audit_db, raising=False)

    def factory(*, workspace_path: Path, session_id: str) -> ClaudeCodeService:
        return ClaudeCodeService(
            workspace_path=workspace_path,
            session_id=session_id,
            broker=broker,
            claude_cmd=mock_claude_cmd,
            env_overrides={"MOCK_CLAUDE_FIXTURE": str(fixture)},
            audit_logger=audit,
            operator="test-op",
        )

    app.dependency_overrides[get_broker] = lambda: broker
    app.dependency_overrides[get_claude_factory] = lambda: factory
    app.dependency_overrides[get_audit_logger] = lambda: audit
    yield app, audit_db
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_chat_writes_user_prompt_and_done_to_audit(app_with_audit):
    """POSTing a chat message must produce at least one user.prompt and one done row."""
    test_app, audit_db = app_with_audit
    session_id = "audit-integ-s1"

    transport = httpx.ASGITransport(app=test_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.post(
            "/api/chat",
            json={"message": "run backtest", "session_id": session_id},
        )
        assert r.status_code == 202

        # Drain the SSE stream so all background tasks complete before we
        # inspect the audit DB.
        async with ac.stream("GET", f"/api/chat/stream/{session_id}") as stream:
            async for line in stream.aiter_lines():
                if line.startswith("event: done"):
                    break

    # Give background coroutines a tick to flush.
    await asyncio.sleep(0.05)

    conn = sqlite3.connect(audit_db)
    try:
        rows = conn.execute(
            "SELECT event_type FROM audit_log WHERE session_id = ?",
            (session_id,),
        ).fetchall()
    finally:
        conn.close()

    event_types = {r[0] for r in rows}
    assert "user.prompt" in event_types, f"Missing user.prompt; found: {event_types}"
    assert "done" in event_types, f"Missing done; found: {event_types}"
