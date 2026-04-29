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
        conn = sqlite3.connect(self._db_path)
        try:
            today = datetime.now(UTC).date().isoformat()
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
            conn.commit()
            return audit_id
        finally:
            conn.close()
