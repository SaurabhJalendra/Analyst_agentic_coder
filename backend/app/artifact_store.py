"""Artifact persistence helpers.

Raw sqlite3 access (no SQLAlchemy) — matches audit_logger.py pattern.
INSERT OR IGNORE on the PK so a re-scan after a turn does not raise.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path


def insert_artifact(
    db_path: Path,
    *,
    artifact_id: str,
    session_id: str,
    kind: str,
    title: str,
    source_attribution: str,
    methodology_id: str,
    file_path: str | None = None,
) -> None:
    """INSERT a row into the artifacts table.

    Uses INSERT OR IGNORE so repeated scans after the same turn are idempotent.
    """
    conn = sqlite3.connect(db_path, isolation_level=None, timeout=10.0)
    try:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute(
            "INSERT OR IGNORE INTO artifacts "
            "(id, session_id, kind, title, source_attribution, methodology_id, file_path) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                artifact_id,
                session_id,
                kind,
                title,
                source_attribution,
                methodology_id,
                file_path,
            ),
        )
        conn.execute("COMMIT")
    except Exception:
        import contextlib
        with contextlib.suppress(sqlite3.OperationalError):
            conn.execute("ROLLBACK")
        raise
    finally:
        conn.close()


def get_artifact(db_path: Path, artifact_id: str) -> dict | None:
    """Return the artifact row as a dict, or None if not found."""
    conn = sqlite3.connect(db_path, timeout=10.0)
    try:
        cur = conn.execute(
            "SELECT id, session_id, kind, title, source_attribution, "
            "methodology_id, file_path, created_at "
            "FROM artifacts WHERE id = ?",
            (artifact_id,),
        )
        row = cur.fetchone()
    finally:
        conn.close()

    if row is None:
        return None
    return {
        "id": row[0],
        "session_id": row[1],
        "kind": row[2],
        "title": row[3],
        "source_attribution": row[4],
        "methodology_id": row[5],
        "file_path": row[6],
        "created_at": row[7],
    }
