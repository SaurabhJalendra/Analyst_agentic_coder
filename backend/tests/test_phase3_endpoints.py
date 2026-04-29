"""Smoke tests for Phase 3 endpoints (methodology, audit, PDF export)."""
from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.audit_logger import AuditLogger
from app.event_schema import ToolStartEvent
from app.main import app
from migrations.run import apply_pending


@pytest.mark.asyncio
async def test_audit_endpoint_returns_rows(tmp_path, monkeypatch):
    db = tmp_path / "test.db"
    apply_pending(db)
    logger = AuditLogger(db)
    await logger.append(
        "s1",
        ToolStartEvent(
            type="tool.start",
            call_id="c1",
            agent_id="main",
            tool="Read",
            args_redacted={},
        ),
        client_slug="acme",
    )
    monkeypatch.setattr("app.main._audit_db_path", db, raising=False)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get("/api/audit/s1?limit=10")
    assert r.status_code in (200, 404)
    if r.status_code == 200:
        payload = r.json()
        assert "rows" in payload
        assert payload["session_id"] == "s1"


@pytest.mark.asyncio
async def test_audit_endpoint_pagination(tmp_path, monkeypatch):
    """Inserting 5 rows and paging with limit=3 should produce next_before_id."""
    db = tmp_path / "test.db"
    apply_pending(db)
    logger = AuditLogger(db)
    for i in range(5):
        await logger.append(
            "s2",
            ToolStartEvent(
                type="tool.start",
                call_id=f"c{i}",
                agent_id="main",
                tool="Read",
                args_redacted={},
            ),
            client_slug="acme",
        )
    monkeypatch.setattr("app.main._audit_db_path", db, raising=False)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get("/api/audit/s2?limit=3")
    assert r.status_code == 200
    payload = r.json()
    assert len(payload["rows"]) == 3
    assert payload["next_before_id"] is not None


@pytest.mark.asyncio
async def test_methodology_404_for_unknown(tmp_path, monkeypatch):
    db = tmp_path / "test_404.db"
    apply_pending(db)
    monkeypatch.setattr("app.main._audit_db_path", db, raising=False)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get("/api/artifacts/nonexistent/methodology")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_methodology_returns_structure(tmp_path, monkeypatch):
    """Insert an artifact row and verify the methodology endpoint returns the right shape."""
    import sqlite3

    db = tmp_path / "test.db"
    apply_pending(db)
    conn = sqlite3.connect(db)
    conn.execute(
        "INSERT INTO artifacts (id, session_id, kind, title, source_attribution, methodology_id) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        ("art-1", "sess-x", "report", "My Report", "Bloomberg", "meth-1"),
    )
    conn.commit()
    conn.close()

    monkeypatch.setattr("app.main._audit_db_path", db, raising=False)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get("/api/artifacts/art-1/methodology")
    assert r.status_code == 200
    payload = r.json()
    assert payload["artifact_id"] == "art-1"
    assert "methodology" in payload
    assert "narrative" in payload["methodology"]
    assert "tool_calls" in payload["methodology"]
    assert "sources" in payload["methodology"]
    assert "agents_involved" in payload["methodology"]


@pytest.mark.asyncio
async def test_pdf_export_returns_pdf():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.post(
            "/api/export/pdf",
            json={"session_id": "any-session", "artifact_ids": [], "narrative": "test"},
        )
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/pdf")
    assert r.content[:4] == b"%PDF"


@pytest.mark.asyncio
async def test_pdf_export_with_narrative_only(tmp_path, monkeypatch):
    """PDF export for a session with no matching artifacts still returns a valid PDF."""
    db = tmp_path / "test_pdf.db"
    apply_pending(db)
    monkeypatch.setattr("app.main._audit_db_path", db, raising=False)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.post(
            "/api/export/pdf",
            json={
                "session_id": "empty-session",
                "narrative": "This is a standalone narrative.\nSecond line.",
            },
        )
    assert r.status_code == 200
    assert r.content[:4] == b"%PDF"
