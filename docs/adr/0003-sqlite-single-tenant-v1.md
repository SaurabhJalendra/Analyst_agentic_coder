# ADR 0003 — SQLite with single-tenant assumption for v1

**Status:** Accepted (2026-04-29) · Time-bound: revisit when concurrent sessions > 100 or multi-tenant deploy is on the roadmap.
**Deciders:** Saurabh Jalendra

## Context

The persistence layer needs: chat sessions, messages, tool_calls, an append-only audit log, artifacts metadata, and migrations. Options: SQLite (file-based), Postgres (server), DuckDB, MongoDB, key-value store.

## Decision

**SQLite via SQLAlchemy async (`aiosqlite`)** for the main session DB, plus **raw `sqlite3` connections** in `audit_logger.py` and the `/api/audit/{id}` read path for atomic `BEGIN IMMEDIATE` semantics that SQLAlchemy makes awkward.

Single-tenant: one backend container = one client = one SQLite file at `backend/chatbot.db`. The `_active_claude_instances` registry is global and not sharded.

## Consequences

**Positive**
- Zero deploy complexity. One Docker container, one file on disk.
- Embedded; transactions just work; no network round-trips.
- File-based backups are simple (`sqlite3 .backup`).
- The migration runner (`migrations/run.py`) is ~40 lines.

**Negative**
- Concurrent writes serialize. Under load, audit-log writes (every tool call) become the bottleneck even with WAL mode. We currently don't have WAL mode enabled (technical debt — see audit 2026-05-20 I16).
- No horizontal scale. One backend instance per client; can't load-balance.
- Multi-tenancy requires a full data-model rework (`client_id` partition key on every table).
- The mix of SQLAlchemy + raw `sqlite3` for audit creates a layering smell. Audit layer is hard-coupled to SQLite; swapping to Postgres later is a real rewrite.

## Alternatives considered

1. **Postgres from day one.** Rejected: deploy complexity for a single-user local product. Migration to PG when needed is documented as foreseeable cost (see Reversal).
2. **DuckDB.** Tempting for the audit log (columnar, fast aggregations). Rejected as overkill — and the operational story for a long-running write-heavy workload is less proven than Postgres.
3. **SQLite + Postgres hybrid** (SQLite for transactional session state, Postgres for audit). Rejected as premature complexity.

## Reversal criteria

Migrate to Postgres when ANY of these is true:
- Concurrent sessions per backend regularly exceed ~50 (audit-log write contention starts to matter).
- A second client is added and we need data isolation beyond "another container."
- We add SSO / RBAC that wants stored credentials shared across instances.
- We need PITR (point-in-time recovery) or hot-standby for compliance.

Migration cost estimate: ~16 hours.
- 6 h: rewrite `audit_logger.py` and audit-read path to use SQLAlchemy + the async PG driver.
- 4 h: shim or remove raw `sqlite3` queries from `main.py` (the `/api/audit/{id}` reader).
- 3 h: data migration (`sqlite3 → pg_dump-compatible export → psql`).
- 3 h: update CI/deploy/compose to include a Postgres service + connection pooling.

## References

- Schema: `backend/migrations/001_audit_artifacts.sql`, `backend/app/database.py`.
- Audit writer: `backend/app/audit_logger.py` (raw sqlite3 with BEGIN IMMEDIATE + retry).
- Audit reader: `backend/app/main.py:765-810` (raw sqlite3 again — see audit C5 about extracting routers).
