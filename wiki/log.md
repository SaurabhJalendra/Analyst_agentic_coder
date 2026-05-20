# Wiki Log

> Append-only chronological record. ISO-8601 timestamps. Never edit a past entry.
> Format per entry:
> ```
> ## YYYY-MM-DDTHH:MM — short title
> **Trigger:** what kicked this off (ingest, query, lint, manual)
> **Pages touched:** [[page-1]], [[page-2]]
> **Pages created:** [[page-3]]
> **Key claims added:** ...
> **What changed in understanding:** one sentence
> ```

---

## 2026-04-29T10:00 — Wiki initialized

**Trigger:** Manual setup. User requested LLM Wiki pattern from Karpathy be applied to this project.

**Pages created:**
- [[../SCHEMA|SCHEMA]] — the maintenance contract
- [[index]] — catalog
- [[log|this log]]
- [[concepts/claude-code-cli-vs-sdk]] — explains the CLI-over-SDK architectural choice
- [[concepts/workspace-isolation]] — explains the per-session sandbox
- [[concepts/llm-wiki-pattern]] — meta-page about the wiki itself
- [[entities/claude-code-service]] — points at `backend/app/claude_code_service.py`
- [[entities/workspace-manager]] — points at `backend/app/workspace_manager.py`
- [[entities/usechat-hook]] — points at `frontend-react/src/hooks/useChat.ts`

**Pages touched:** N/A (first ingest)

**Key claims established:**
- The project uses `claude` CLI subprocess instead of the Anthropic SDK (~700 LOC removed in favor of ~235 LOC, see `CLEANUP_SUMMARY.md`).
- Per-session workspace isolation is enforced by path-resolve checks on workspace-scoped endpoints, but `/api/files/{path}` is unguarded (known issue).
- The wiki itself follows Karpathy's pattern: index + log + concepts/entities/synthesis + sources.

**What changed in understanding:** We now have a persistent, structured place to grow knowledge about this codebase. Future sessions should start with a `/wiki-query` for context instead of re-scanning the repo.

**Source:** [Karpathy's llm-wiki gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) (2026-04 reading).

---

## 2026-05-20T11:00 — Deep audit + documentation pass

**Trigger:** Manual. User requested a full-project deep audit "behave like a top team of best engineers and researchers and quants" and document everything that needs documenting.

**Pages created:**
- [[../../docs/audit/2026-05-20-deep-audit|2026-05-20 deep audit]] — top-level report (severity-graded findings + 5-wave plan)
- [[../../docs/adr/0001-claude-cli-over-anthropic-sdk|ADR-0001 CLI-over-SDK]]
- [[../../docs/adr/0002-sse-over-websocket|ADR-0002 SSE over WebSocket]]
- [[../../docs/adr/0003-sqlite-single-tenant-v1|ADR-0003 SQLite single-tenant v1]]
- [[../../docs/adr/0004-no-auth-v1|ADR-0004 No auth in v1]]
- `LICENSE` (MIT)
- `CHANGELOG.md` (Keep-a-Changelog format, seeded from git log)
- `tasks/lessons.md` updated with 5 patterns (verify-agent-findings, capture-real-output-first, no-compliance-theater, Internal-DAU-real, wiki-must-be-used)

**Pages touched:**
- [[../../CLAUDE|project CLAUDE.md]] — Architecture (polling → SSE), Known Issues (synced with current reality), Current Focus
- [[../../README|README.md]] — removed stale Streamlit references, added current stack, current security posture, troubleshooting
- [[../../ROADMAP|ROADMAP.md]] — restructured into 5 waves + Now / Next / Later / Not Doing

**Key claims established:**
- The streaming substrate is real; the compliance pillar is theater.
- `AuditLogger` is **never instantiated in production code** — only in tests. The `audit_log` table is permanently empty. This is the biggest single finding.
- Path-traversal hole still open on `/api/workspace/{id}/list/` (sibling-traversal via `startswith`). Mirror of the fix already applied to `/files/`.
- `main.py` is 1,084 lines, no router separation.
- mypy strict: 71 errors. ruff: 119 issues (53 auto-fixable).
- Internal-DAU gate not passed: no 7 consecutive days of author use.
- `⌘K`, "Entitlements: ...", "MNPI walls: ON", `opus-4.7 ▾` model selector — all decorative UI elements with no backing logic.

**Verified false positives from audit agents** (do NOT chase):
- `.env` is not tracked (correctly gitignored). Same false positive as the 2026-04-30 audit.
- Hardcoded CLI path is NOT still present (fixed commit `909c62b`).
- Double-DoneEvent race: `emitted_done` flag correctly gates the synthetic done.
- BrandBar identity not rendered: intentional placeholder cleanup, not a bug.

**What changed in understanding:** The project has been graded against itself favorably; against the stated idea (institutional research console with traceable artifacts), it's at ~5.5/10. The next 4 waves close the compliance hole, split `main.py`, harden the frontend, and only then is Internal-DAU dogfooding the gate before any external demo.

**Source:** Audit report at `docs/audit/2026-05-20-deep-audit.md`.

---
