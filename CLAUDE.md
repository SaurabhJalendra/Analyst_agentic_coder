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

- One Claude CLI instance per session, stored in `workspace_manager._active_claude_instances`.
- System prompt rebuilt on every chat request (Phase 2 fix, commit `43c04eb`) with fresh git context.
- Frontend polls `/api/progress/{id}` every 1000ms during long requests; no SSE/WebSocket.

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

These should be fixed before this is used by anyone other than the author. Tracked here so any future work can pick them up:

1. **Path-traversal hole**: `GET /api/files/{path:path}` reads any file on disk — no workspace boundary check. The `/api/workspace/{id}/files/...` endpoints are correctly guarded; this one isn't.
2. **Hardcoded CLI path**: `claude_code_service.py:37` hardcodes `C:\Users\Saurabh\.local\bin\claude.exe`. Breaks on every other machine and inside the Linux container. Use `shutil.which("claude")`.
3. **Git creds in URL logs**: `git_utils.py:55` embeds tokens into the clone URL; visible in subprocess stdout.
4. **CORS = `*` + no auth + no rate limiting**: fine for localhost, dangerous if exposed.
5. **Half-implemented plan-approval**: `requires_approval` flows to `ChatResponse` but the React UI never renders an approval step.
6. **Repo hygiene**: `nul` (empty Windows redirection accident), `docker-entrypoint.sh` (dead — refers to old Streamlit), unused `anthropic` SDK in `requirements.txt`, unused `react-syntax-highlighter` in `package.json`.

---

## Auth & Setup Notes

- Backend authenticates Claude Code via `CLAUDE_CODE_ACCESS_TOKEN` + `CLAUDE_CODE_REFRESH_TOKEN` in `.env`. See `AUTHENTICATION_SETUP.md`.
- Each session gets a per-workspace `.claude/settings.local.json` auto-generated with `"allow": ["*"]` to enable autonomous tool use. See `CLAUDE_CODE_SETUP.md`.
- Default repo (`DEFAULT_REPO_URL`) is auto-cloned on session creation if no other repo is active.

---

## Current Focus

_(Update between sessions only — not mid-session)_

- Project setup just initialized via `SETUP.md` on 2026-04-29.
- Next: pick a known-issue from the list above, or start a feature.
