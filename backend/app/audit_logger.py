"""Append-only audit log. One row per audit-relevant event.

Audit ID format: SES-YYYY-MM-DD-<client-slug>-<seq:04d>
Seq is per-client, monotonically increasing across all sessions for that client.
"""
from __future__ import annotations

import asyncio
import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from app.event_schema import AnyEvent


def generate_audit_id(client_slug: str, date: str, seq: int) -> str:
    return f"SES-{date}-{client_slug}-{seq:04d}"


class AuditLogger:
    """SQLite-backed audit log. Thread/async-safe via a single asyncio lock."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._lock = asyncio.Lock()

    async def append(
        self,
        session_id: str,
        event: AnyEvent,
        client_slug: str,
        entitlements_snapshot: dict[str, object] | None = None,
    ) -> str:
        async with self._lock:
            return await asyncio.to_thread(
                self._append_sync, session_id, event, client_slug, entitlements_snapshot
            )

    def _append_sync(
        self,
        session_id: str,
        event: AnyEvent,
        client_slug: str,
        entitlements_snapshot: dict[str, object] | None,
    ) -> str:
        # isolation_level=None gives us manual transaction control. We use
        # BEGIN IMMEDIATE so the SELECT-then-INSERT pair is atomic against
        # other writers (SQLite serializes write transactions on the same DB).
        # Retry on SQLITE_BUSY in case another writer holds the lock briefly.
        conn = sqlite3.connect(self._db_path, isolation_level=None, timeout=10.0)
        try:
            today = datetime.now(UTC).date().isoformat()
            for attempt in range(5):
                try:
                    conn.execute("BEGIN IMMEDIATE")
                    cur = conn.execute(
                        "SELECT COUNT(*) FROM audit_log WHERE audit_id LIKE ?",
                        (f"SES-%-{client_slug}-%",),
                    )
                    seq = cur.fetchone()[0] + 1
                    audit_id = generate_audit_id(client_slug, today, seq)
                    conn.execute(
                        "INSERT INTO audit_log"
                        "(session_id, event_type, audit_id, data_json, entitlements_snapshot_json) "
                        "VALUES (?, ?, ?, ?, ?)",
                        (
                            session_id,
                            event.type,
                            audit_id,
                            event.model_dump_json(),
                            json.dumps(entitlements_snapshot) if entitlements_snapshot else None,
                        ),
                    )
                    conn.execute("COMMIT")
                    return audit_id
                except sqlite3.OperationalError as exc:
                    # Roll back any partial state and retry on lock contention.
                    try:
                        conn.execute("ROLLBACK")
                    except sqlite3.OperationalError:
                        pass
                    if "locked" in str(exc).lower() and attempt < 4:
                        continue
                    raise
            raise RuntimeError("audit_logger: exceeded retry budget under contention")
        finally:
            conn.close()
