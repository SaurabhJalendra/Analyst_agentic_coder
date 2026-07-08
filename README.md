# Quant Agent

An institutional-client research console — a Claude AI agent for quant analysis and report generation, wrapping the `claude` CLI in a per-session sandbox.

## Features

- **Agentic chat** with live streaming of plan, sub-agents, tool calls, and source access
- **Per-session workspaces** — each chat clones into its own isolated git repo
- **Branded artifacts** — live Plotly charts rendered from agent-emitted payloads, tables (TanStack), code blocks, markdown + LaTeX
- **Audit trail** — every prompt and tool call written to an append-only audit log, exportable to PDF
- **Honest pilot disclosures** — single-user local-pilot banner + "not investment advice" footer (the earlier entitlements/MNPI-wall pills were removed as unenforced — see audit C2)

## Architecture

- **Backend**: FastAPI + SSE streaming of typed events from the `claude` CLI subprocess
- **Frontend**: React 19 + TypeScript + Tailwind v4 + Zustand, three-pane "Quant Agent" console
- **AI**: Claude Code CLI (not the Anthropic SDK) — see `wiki/concepts/claude-code-cli-vs-sdk.md`
- **Database**: SQLite with audit-log + artifacts tables
- **Deploy**: Docker compose (prod + dev variants)

## Prerequisites

- Python 3.11+ and Node 20+
- The `claude` CLI installed on PATH (`npm install -g @anthropic-ai/claude-code`) and authenticated. See `AUTHENTICATION_SETUP.md` for the OAuth token flow.
- Git
- (Optional) Docker + Docker Compose

## Quick start

```bash
git clone https://github.com/SaurabhJalendra/quant-agent.git
cd quant-agent
cp .env.example .env
# Edit .env: set CLAUDE_CODE_ACCESS_TOKEN + CLAUDE_CODE_REFRESH_TOKEN

# Backend
cd backend && pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000 &

# Frontend (separate terminal)
cd frontend-react && npm install
npm run dev  # serves http://localhost:3000
```

The frontend dev server proxies `/api/` to the backend on :8000.

For Docker:
```bash
cp .env.example .env  # then edit
docker compose up --build
```

## Tech stack

- **Backend**: FastAPI + SSE streaming + SQLAlchemy async + aiosqlite. The `claude` CLI as the agent runtime (not the Anthropic SDK — see `docs/adr/0001-claude-cli-over-anthropic-sdk.md`).
- **Frontend**: React 19 + TypeScript strict + Vite 7 + Tailwind v4 + Zustand + Zod (event validation) + Plotly (lazy).
- **Persistence**: SQLite for v1 (`docs/adr/0003-sqlite-single-tenant-v1.md`).
- **Streaming**: SSE over `GET /api/chat/stream/{session_id}` (`docs/adr/0002-sse-over-websocket.md`).

See `CHANGELOG.md` for what's shipped and `ROADMAP.md` for what's next. `docs/audit/` carries the latest deep audit.

## Project layout

```
quant-agent/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI app (chat, sessions, audit, export, workspace)
│   │   ├── claude_code_service.py  # Per-message subprocess wrapper around `claude` CLI
│   │   ├── cli_translator.py       # Real CLI stream-json → typed events
│   │   ├── stream_parser.py        # Async line parser
│   │   ├── event_broker.py         # Per-session SSE broker with Last-Event-ID replay
│   │   ├── event_schema.py         # Pydantic v2 discriminated union of all event types
│   │   ├── audit_logger.py         # Append-only audit log (BEGIN IMMEDIATE atomic)
│   │   ├── workspace_manager.py    # Per-session workspace isolation + git context
│   │   ├── git_utils.py            # Clone helpers (creds via http.extraheader, never URL)
│   │   ├── db_utils.py             # Session CRUD (also releases in-memory CLI instances)
│   │   └── database.py             # SQLAlchemy models
│   ├── migrations/
│   │   ├── run.py                  # Lightweight migration runner
│   │   └── 001_audit_artifacts.sql
│   └── tests/                      # 87 tests: cli_translator Hypothesis fuzz + audit, artifact & chart pipeline
├── frontend-react/
│   └── src/
│       ├── App.tsx
│       ├── components/
│       │   ├── frame/              # BrandBar, ComplianceBar, StatusBar, ComplianceFooter
│       │   ├── layout/             # ThreePaneLayout (responsive drawers ≤1280px)
│       │   ├── left/               # SessionsList, WorkspaceTree
│       │   ├── center/             # ChatStream, BrandedArtifactCard, MethodologyPanel, …
│       │   ├── right/tabs/         # Plan, Agents, Activity, Artifacts, Report, Audit
│       │   ├── prompt/PromptInput.tsx
│       │   └── renderers/          # MarkdownWithLatex (lazy), Chart, DataTable, CodeBlock
│       ├── store/sessionStore.ts   # Zustand
│       ├── services/               # api.ts (axios), eventStream.ts (EventSource), eventReducer.ts (Immer)
│       └── hooks/useSessionHistory.ts
├── docs/
│   ├── adr/                        # Architecture Decision Records
│   ├── audit/2026-05-20-deep-audit.md
│   └── superpowers/                # Plans + specs
├── wiki/                           # Karpathy LLM-Wiki pattern (concepts, entities, log)
├── tasks/lessons.md                # Self-improvement log
├── docker-compose.yml              # prod
├── docker-compose.dev.yml          # dev (hot reload)
└── ROADMAP.md / CHANGELOG.md / IDEA.md / inbox.md / LICENSE
```

## Configuration

`.env.example` lists every variable the backend reads. Required:
- `CLAUDE_CODE_ACCESS_TOKEN`, `CLAUDE_CODE_REFRESH_TOKEN` — see `AUTHENTICATION_SETUP.md`.

Optional:
- `DEFAULT_REPO_URL` / `DEFAULT_REPO_BRANCH` — auto-cloned into each new session's workspace.
- `CORS_ORIGINS` — comma-separated allowlist (defaults to localhost dev URLs).
- `BACKEND_PORT`, `FRONTEND_PORT`.

## Key commands

| | |
|---|---|
| Backend | `cd backend && python -m uvicorn app.main:app --reload --port 8000` |
| Frontend (dev) | `cd frontend-react && npm run dev` |
| Frontend build | `cd frontend-react && npm run build` |
| Frontend lint | `cd frontend-react && npm run lint` |
| Frontend typecheck | `cd frontend-react && npx tsc --noEmit` |
| Backend tests | `cd backend && python -m pytest` |
| Health check | `curl http://localhost:8000/health` |
| Docker prod | `docker compose up --build` |
| Docker dev | `docker compose -f docker-compose.dev.yml up --build` |

## Troubleshooting

- **`claude: command not found`** — `npm install -g @anthropic-ai/claude-code` and re-run.
- **Backend health passes but chat hangs** — Claude CLI tokens likely expired. Check `~/.claude/config.json`; regenerate per `AUTHENTICATION_SETUP.md`.
- **Frontend shows white screen after dep changes** — Vite dep cache stale. `rm -rf frontend-react/node_modules/.vite && npm run dev`.
- **`Device or resource busy` on file ops** — VS Code or a running uvicorn/vite holds the file. Stop services, retry.
- **DB reset** — delete `backend/chatbot.db`; restart backend (migrations rerun).

## Security posture (current honest state)

- **No authentication** in v1 — see `docs/adr/0004-no-auth-v1.md`. Do NOT expose to the internet.
- CORS allowlist via `CORS_ORIGINS`; defaults to localhost.
- slowapi rate limit (20/min/IP) on `/api/chat`.
- Compliance/entitlements pills were **removed** (nothing enforced them); the bar now shows only honest pilot disclosures until a real entitlements service ships (audit C2, closed).
- Audit log is **wired and written** on every chat turn via an injected `AuditLogger` (audit C1, closed) — `/api/audit/{id}` and PDF export read real rows.
- `main.py` is still a single ~1,186-line module; the router split (audit C5) is the main open structural item.

## Contributing

Solo project for now. If you'd like to engage, open an issue at https://github.com/SaurabhJalendra/quant-agent/issues.

## License

MIT — see [`LICENSE`](LICENSE). © 2026 Saurabh Jalendra.

## Support

- GitHub Issues: https://github.com/SaurabhJalendra/quant-agent/issues
- API docs (live): http://localhost:8000/docs
- Architecture decisions: `docs/adr/`

## Acknowledgments

- Agent runtime: [Claude Code CLI](https://github.com/anthropics/claude-code) by Anthropic
- Backend: [FastAPI](https://fastapi.tiangolo.com/)
- Frontend: [React](https://react.dev/) + [Vite](https://vite.dev/) + [Tailwind CSS](https://tailwindcss.com/)
- Charts: [Plotly](https://plotly.com/javascript/)
