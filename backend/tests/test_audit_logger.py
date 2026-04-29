"""Tests for the append-only audit logger."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from app.audit_logger import AuditLogger, generate_audit_id
from app.event_schema import ToolStartEvent
from migrations.run import apply_pending


@pytest.fixture
def db(tmp_path: Path) -> Path:
    db_path = tmp_path / "audit.db"
    apply_pending(db_path)
    return db_path


def test_audit_id_format():
    aid = generate_audit_id(client_slug="acme", date="2024-04-29", seq=42)
    assert aid == "SES-2024-04-29-acme-0042"


def test_audit_id_zero_pads_seq():
    assert generate_audit_id("a", "2024-01-01", 1).endswith("-0001")
    assert generate_audit_id("a", "2024-01-01", 9999).endswith("-9999")


@pytest.mark.asyncio
async def test_append_writes_row(db: Path):
    logger = AuditLogger(db)
    ev = ToolStartEvent(
        type="tool.start",
        call_id="c1",
        agent_id="main",
        tool="Read",
        args_redacted={"path": "x.py"},
    )
    aid = await logger.append(session_id="s1", event=ev, client_slug="acme")
    assert aid.startswith("SES-")

    conn = sqlite3.connect(db)
    rows = conn.execute(
        "SELECT session_id, event_type, audit_id, data_json FROM audit_log"
    ).fetchall()
    assert len(rows) == 1
    sid, etype, audit_id, data_json = rows[0]
    assert sid == "s1"
    assert etype == "tool.start"
    assert audit_id == aid
    assert json.loads(data_json)["tool"] == "Read"


@pytest.mark.asyncio
async def test_append_increments_seq_per_client(db: Path):
    logger = AuditLogger(db)
    ev = ToolStartEvent(
        type="tool.start", call_id="c1", agent_id="main", tool="Read", args_redacted={}
    )
    a1 = await logger.append("s1", ev, client_slug="acme")
    a2 = await logger.append("s2", ev, client_slug="acme")
    a3 = await logger.append("s3", ev, client_slug="other")

    seq1 = int(a1.rsplit("-", 1)[-1])
    seq2 = int(a2.rsplit("-", 1)[-1])
    seq3 = int(a3.rsplit("-", 1)[-1])
    assert seq2 == seq1 + 1
    assert seq3 == 1


@pytest.mark.asyncio
async def test_redacts_authorization_in_args(db: Path):
    """Caller is responsible for redaction; data is stored as-given (not silently mutated)."""
    logger = AuditLogger(db)
    ev = ToolStartEvent(
        type="tool.start",
        call_id="c1",
        agent_id="main",
        tool="WebFetch",
        args_redacted={"url": "https://x", "Authorization": "Bearer secret"},
    )
    await logger.append("s1", ev, client_slug="acme")

    conn = sqlite3.connect(db)
    row = conn.execute("SELECT data_json FROM audit_log").fetchone()
    data = json.loads(row[0])
    assert "Authorization" in data["args_redacted"]
