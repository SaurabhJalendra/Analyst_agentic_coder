# Quant Agent

An institutional-client research console (FastAPI + React) wrapping the `claude` CLI as a per-session subprocess. The React frontend talks to it over HTTP + SSE. Formerly "Analyst Agentic Coder" — renamed 2026-05-14.

> Workflow rules (plan mode, subagent strategy, parallel execution, verification, etc.) are defined in the global `~/.claude/CLAUDE.md` and apply here. This file documents only what is project-specific.

---

## Stack

**Backend** — `backend/`
- Python 3.11+, FastAPI, Uvicorn, SQLAlchemy 2.x async + aiosqlite
- Subprocess wrapper around `claude` CLI (`claude_code_service.py`) — NOT the Anthropic SDK
- structlog, gitpython, httpx, pydantic v2

**Frontend** — `frontend-react/`
- React 19 + TypeScript 5.9 + Vite 7 + Tailwind v4
- axios (10-min timeout), react-markdown + remark-gfm, lucide-react
- Hooks-only state (no Redux/Zustand), no router (single page)

**Infra**
- Docker compose (prod/dev split), Nginx alpine for prod frontend
- SQLite at `backend/chatbot.db`, workspaces under `backend/workspaces/{session_id}/`

---

## Conventions

- **Backend**: `async def` for all routes and DB ops. Pydantic models in `app/main.py` for request/response. Tools live under `app/` not `app/tools/` (tools/ was removed during the Claude Code CLI migration — see `CLEANUP_SUMMARY.md`).
- **Frontend**: TypeScript-only (no `.js` in `src/`). `import type { ... }` for type-only imports. Components in `src/components/{Name}.tsx` with a barrel `index.ts`. Hooks in `src/hooks/`. API calls only via `services/api.ts`.
- **Naming**: snake_case for Python, camelCase for TS, PascalCase for React components.
- **Comments**: Default to none. Only when WHY is non-obvious.

---

## Architecture

```
React (Vite/Nginx) ──► FastAPI ──► ClaudeCodeService (per-session subprocess)
   port 3000/80         port 8000        claude.exe -p ... --output-format json
                          │
                          ├── SQLite (sessions, messages, tool_calls)
                          └── workspaces/{uuid}/  (git-cloned repos)
```

- Per-message Claude CLI subprocess (the `_active_claude_instances` registry holds a `ClaudeCodeService` wrapper per session; each `send_message` spawns a fresh `claude` subprocess).
- System prompt rebuilt on every chat request with fresh git context.
- **SSE** streaming from `GET /api/chat/stream/{session_id}` (replaced the old polling endpoint in commit `4f1b940`). Frontend uses `EventSource` with `Last-Event-ID` reconnect.
- `cli_translator.py` maps real Claude CLI `system`/`assistant`/`user`/`result` events into our typed Pydantic schema.

---

## Key Commands

| Action | Command |
|---|---|
| Run backend | `cd backend && python -m uvicorn app.main:app --reload --port 8000` |
| Run frontend (dev) | `cd frontend-react && npm run dev` |
| Build frontend | `cd frontend-react && npm run build` |
| Frontend lint | `cd frontend-react && npm run lint` |
| Frontend typecheck | `cd frontend-react && npx tsc --noEmit` |
| Verify env | `python verify_setup.py` |
| Docker prod | `docker compose up --build` |
| Docker dev | `docker compose -f docker-compose.dev.yml up --build` |
| Health check | `curl http://localhost:8000/health` |

No Python test runner is configured. `backend/test_endpoint.py` and `backend/test_imports.py` are scaffolding, not pytest.

---

## Known Issues / Tech Debt

Open items as of 2026-05-20. Full audit at `docs/audit/2026-05-20-deep-audit.md`; ranked next-actions in `ROADMAP.md`.

### Critical (block any client pilot)
1. **`AuditLogger` is never instantiated in production code** — `audit_log` table is permanently empty. `/api/audit/{id}` returns nothing real; PDF "audit ID" is decorative. (`backend/app/main.py` chat handler, see audit C1.)
2. **Compliance bar is cosmetic** — "MNPI walls: ON" and "Entitlements: ..." have no enforcement anywhere in the call path. Audit finding C2.
3. **Path-traversal still open on `/api/workspace/{id}/list/`** at `main.py:723` — uses string `startswith()` (sibling-traversal possible). The `/files/` endpoint at line 661 was fixed; this one wasn't. Audit C3.
4. **`main.py` is 1,084 lines** with 25+ endpoints — needs router split. Audit C5.
5. **`⌘K` is a dead `<span>`** in StatusBar — visual lie. Either wire a command palette or remove. Audit C4.
6. **Internal-DAU gate (rule 6g) not passed** — no 7-day daily use by the author.

### Important
- Stale UI placeholders: hardcoded `opus-4.7 ▾` model selector, BrandBar without identity (intentional until auth lands).
- Frontend has no `<ErrorBoundary>` and no client-side error telemetry.
- No observability (no `/metrics`, no Sentry, no OTel).
- SQLite lacks WAL mode and a backup story.
- 71 mypy strict errors / 119 ruff issues (53 auto-fixable).
- No retention policy on `audit_log` / `artifacts` once they're populated.
- UTF-8-on-chunk-boundary risk in the SSE stdout reader (`claude_code_service.py:130`).
- `get_or_create_service` factory race (no lock around the lookup-or-create).

### Fixed (kept for changelog continuity)
- ✅ Path-traversal on `/api/files/{path}` (endpoint removed, commit `327bf5c`).
- ✅ Hardcoded CLI path (replaced with `shutil.which`, commit `909c62b`).
- ✅ Git creds in URL logs (now `http.extraheader`, commit `bafe480`).
- ✅ CORS `*` (now env-driven allowlist).
- ✅ `nul`, `docker-entrypoint.sh`, unused `anthropic` and `react-syntax-highlighter` deps — all removed.

---

## Auth & Setup Notes

- Backend authenticates Claude Code via `CLAUDE_CODE_ACCESS_TOKEN` + `CLAUDE_CODE_REFRESH_TOKEN` in `.env`. See `AUTHENTICATION_SETUP.md`.
- Each session gets a per-workspace `.claude/settings.local.json` auto-generated with `"allow": ["*"]` to enable autonomous tool use. See `CLAUDE_CODE_SETUP.md`.
- Default repo (`DEFAULT_REPO_URL`) is auto-cloned on session creation if no other repo is active.

---

## Current Focus

_(Update between sessions only — not mid-session)_

- 2026-05-20 deep audit complete. Findings: `docs/audit/2026-05-20-deep-audit.md`. ADRs filed for CLI-over-SDK, SSE, SQLite, no-auth. LICENSE + CHANGELOG seeded.
- Next wave (per ROADMAP.md): C1 audit-write wiring, C2 compliance enforcement decision, C3 list-endpoint path fix, C5 main.py router split, C4 ⌘K wire-or-remove.
- Then Internal-DAU dogfooding week before any external demo.
