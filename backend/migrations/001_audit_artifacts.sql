-- Phase 1: audit log + artifacts metadata.
-- Note: existing tables (sessions, messages, tool_calls) are owned by SQLAlchemy;
-- this migration only adds the new ones.

CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    ts TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    event_type TEXT NOT NULL,
    audit_id TEXT NOT NULL,
    data_json TEXT NOT NULL,
    entitlements_snapshot_json TEXT
);

CREATE INDEX IF NOT EXISTS idx_audit_log_session ON audit_log(session_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_audit_id ON audit_log(audit_id);

CREATE TABLE IF NOT EXISTS artifacts (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    title TEXT NOT NULL,
    source_attribution TEXT NOT NULL,
    methodology_id TEXT NOT NULL,
    file_path TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_artifacts_session ON artifacts(session_id);
