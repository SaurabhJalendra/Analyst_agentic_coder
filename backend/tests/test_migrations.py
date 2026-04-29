"""Tests for the lightweight migration runner."""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from migrations.run import apply_pending


@pytest.fixture
def tmp_db(tmp_path: Path) -> Path:
    db = tmp_path / "test.db"
    db.touch()
    return db


def test_runner_creates_meta_table(tmp_db: Path):
    apply_pending(tmp_db)
    conn = sqlite3.connect(tmp_db)
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='_migrations'"
    ).fetchall()
    assert rows == [("_migrations",)]


def test_runner_applies_001(tmp_db: Path):
    apply_pending(tmp_db)
    conn = sqlite3.connect(tmp_db)
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}
    assert "audit_log" in tables
    assert "artifacts" in tables


def test_runner_idempotent(tmp_db: Path):
    apply_pending(tmp_db)
    apply_pending(tmp_db)  # second run is a no-op
    conn = sqlite3.connect(tmp_db)
    applied = conn.execute("SELECT COUNT(*) FROM _migrations").fetchone()[0]
    assert applied == 1


def test_audit_log_columns(tmp_db: Path):
    apply_pending(tmp_db)
    conn = sqlite3.connect(tmp_db)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(audit_log)").fetchall()}
    assert {"id", "session_id", "ts", "event_type", "audit_id", "data_json"} <= cols
