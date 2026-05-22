"""Tests for artifact_store.py (INSERT/SELECT on the artifacts table)."""
from __future__ import annotations

from pathlib import Path

import pytest

from app.artifact_store import get_artifact, insert_artifact
from migrations.run import apply_pending


@pytest.fixture
def tmp_db(tmp_path: Path) -> Path:
    db = tmp_path / "artifacts_test.db"
    db.touch()
    apply_pending(db)
    return db


def test_insert_and_get_round_trip(tmp_db: Path):
    insert_artifact(
        tmp_db,
        artifact_id="art-001",
        session_id="sess-1",
        kind="chart",
        title="Equity Curve",
        source_attribution="Generated in session",
        methodology_id="art-001",
        file_path="/workspaces/sess-1/artifacts/equity.chart.json",
    )

    row = get_artifact(tmp_db, "art-001")
    assert row is not None
    assert row["id"] == "art-001"
    assert row["session_id"] == "sess-1"
    assert row["kind"] == "chart"
    assert row["title"] == "Equity Curve"
    assert row["source_attribution"] == "Generated in session"
    assert row["methodology_id"] == "art-001"
    assert row["file_path"] == "/workspaces/sess-1/artifacts/equity.chart.json"
    assert row["created_at"] is not None


def test_get_returns_none_for_missing(tmp_db: Path):
    result = get_artifact(tmp_db, "nonexistent-id")
    assert result is None


def test_insert_or_ignore_on_duplicate_pk(tmp_db: Path):
    """Re-inserting the same artifact_id must not raise — INSERT OR IGNORE."""
    insert_artifact(
        tmp_db,
        artifact_id="art-dupe",
        session_id="sess-1",
        kind="chart",
        title="First",
        source_attribution="session",
        methodology_id="art-dupe",
    )
    # Second call with same PK — must not raise.
    insert_artifact(
        tmp_db,
        artifact_id="art-dupe",
        session_id="sess-1",
        kind="chart",
        title="Should Be Ignored",
        source_attribution="session",
        methodology_id="art-dupe",
    )
    row = get_artifact(tmp_db, "art-dupe")
    assert row is not None
    # First write wins (INSERT OR IGNORE).
    assert row["title"] == "First"


def test_insert_without_file_path(tmp_db: Path):
    insert_artifact(
        tmp_db,
        artifact_id="art-no-file",
        session_id="sess-1",
        kind="chart",
        title="No File",
        source_attribution="session",
        methodology_id="art-no-file",
        file_path=None,
    )
    row = get_artifact(tmp_db, "art-no-file")
    assert row is not None
    assert row["file_path"] is None


def test_multiple_artifacts_same_session(tmp_db: Path):
    for i in range(3):
        insert_artifact(
            tmp_db,
            artifact_id=f"art-{i}",
            session_id="sess-multi",
            kind="chart",
            title=f"Chart {i}",
            source_attribution="session",
            methodology_id=f"art-{i}",
        )

    for i in range(3):
        row = get_artifact(tmp_db, f"art-{i}")
        assert row is not None
        assert row["title"] == f"Chart {i}"
