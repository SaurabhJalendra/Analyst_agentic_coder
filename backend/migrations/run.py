"""Lightweight migration runner. Applies any pending NNN_*.sql files in order."""
from __future__ import annotations

import sqlite3
from pathlib import Path

import structlog

_log = structlog.get_logger(__name__)
_MIGRATIONS_DIR = Path(__file__).parent


def apply_pending(db_path: Path) -> list[str]:
    """Apply any unapplied migrations. Returns list of applied filenames."""
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS _migrations (
                filename TEXT PRIMARY KEY,
                applied_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
            )
        """)
        applied = {r[0] for r in conn.execute("SELECT filename FROM _migrations").fetchall()}

        sql_files = sorted(p for p in _MIGRATIONS_DIR.glob("*.sql"))
        newly_applied: list[str] = []
        for path in sql_files:
            if path.name in applied:
                continue
            sql = path.read_text(encoding="utf-8")
            conn.executescript(sql)
            conn.execute("INSERT INTO _migrations(filename) VALUES (?)", (path.name,))
            conn.commit()
            newly_applied.append(path.name)
            _log.info("migration.applied", filename=path.name)
        return newly_applied
    finally:
        conn.close()
