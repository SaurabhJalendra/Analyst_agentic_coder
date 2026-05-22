"""Tests for GET /api/artifacts/{artifact_id}/payload."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from migrations.run import apply_pending


def _seed_artifact(
    db: Path,
    *,
    artifact_id: str,
    session_id: str = "sess-1",
    kind: str = "chart",
    title: str = "Test Chart",
    file_path: str | None = None,
) -> None:
    conn = sqlite3.connect(db)
    conn.execute(
        "INSERT INTO artifacts "
        "(id, session_id, kind, title, source_attribution, methodology_id, file_path) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (artifact_id, session_id, kind, title, "Generated in session", artifact_id, file_path),
    )
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# 404 for unknown artifact
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_payload_404_unknown_artifact(tmp_path: Path, monkeypatch):
    db = tmp_path / "test.db"
    apply_pending(db)
    monkeypatch.setattr("app.main._audit_db_path", db, raising=False)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get("/api/artifacts/nonexistent-id/payload")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# 404 for non-chart kind
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_payload_404_non_chart_kind(tmp_path: Path, monkeypatch):
    db = tmp_path / "test.db"
    apply_pending(db)
    _seed_artifact(db, artifact_id="rep-001", kind="report", title="A Report")
    monkeypatch.setattr("app.main._audit_db_path", db, raising=False)
    # Also patch the import in artifact_store used by the endpoint
    monkeypatch.setattr("app.main.get_artifact",
                        lambda path, aid: {
                            "id": "rep-001",
                            "session_id": "sess-1",
                            "kind": "report",
                            "title": "A Report",
                            "source_attribution": "session",
                            "methodology_id": "rep-001",
                            "file_path": None,
                            "created_at": "2026-05-21",
                        })

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get("/api/artifacts/rep-001/payload")
    assert r.status_code == 404
    assert "chart" in r.json()["detail"].lower()


# ---------------------------------------------------------------------------
# 200 + correct shape for a seeded chart artifact
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_payload_200_chart_correct_shape(tmp_path: Path, monkeypatch):
    db = tmp_path / "test.db"
    apply_pending(db)

    # Write a real chart file on disk.
    chart_payload = {
        "title": "Equity Curve",
        "data": [{"type": "scatter", "x": [1, 2, 3], "y": [100, 110, 105], "mode": "lines"}],
        "layout": {"xaxis": {"title": "Day"}, "yaxis": {"title": "USD"}},
    }
    chart_file = tmp_path / "equity.chart.json"
    chart_file.write_text(json.dumps(chart_payload), encoding="utf-8")

    _seed_artifact(
        db,
        artifact_id="chart-001",
        kind="chart",
        title="Equity Curve",
        file_path=str(chart_file),
    )
    monkeypatch.setattr("app.main._audit_db_path", db, raising=False)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get("/api/artifacts/chart-001/payload")

    assert r.status_code == 200
    body = r.json()
    assert body["artifact_id"] == "chart-001"
    assert body["kind"] == "chart"
    assert body["title"] == "Equity Curve"
    assert "payload" in body
    payload = body["payload"]
    assert "data" in payload
    assert "layout" in payload
    assert isinstance(payload["data"], list)
    assert len(payload["data"]) == 1
    assert payload["data"][0]["type"] == "scatter"


# ---------------------------------------------------------------------------
# 404 when chart file is missing from disk
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_payload_404_missing_file_on_disk(tmp_path: Path, monkeypatch):
    db = tmp_path / "test.db"
    apply_pending(db)

    _seed_artifact(
        db,
        artifact_id="chart-missing",
        kind="chart",
        title="Ghost Chart",
        file_path=str(tmp_path / "artifacts" / "ghost.chart.json"),  # does not exist
    )
    monkeypatch.setattr("app.main._audit_db_path", db, raising=False)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get("/api/artifacts/chart-missing/payload")
    assert r.status_code == 404
