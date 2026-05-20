# Changelog

All notable changes to Quant Agent. Keep-a-Changelog format. Reverse chronological.

## [Unreleased]

### Pending audit-fix waves (see `docs/audit/2026-05-20-deep-audit.md`)

- Wire `AuditLogger` to the chat endpoint (currently audit_log table is never written in production)
- Path-traversal fix on `/api/workspace/{id}/list/` (sibling-traversal still possible)
- Split `main.py` (1,084 lines) into routers
- Frontend `<ErrorBoundary>` + observability
- Real ADRs for CLI-over-SDK, SSE, SQLite-vs-Postgres, no-auth-v1

## [0.3.0] — 2026-05-14

### Changed
- **Renamed:** "Analyst Agentic Coder" → "Quant Agent". Folder still on disk as `Analyst_agentic_coder` (user-action required); GitHub repo renamed to `SaurabhJalendra/quant-agent`; local `origin` URL updated.
- BrandBar display from "Quant Console" to "Quant Agent" — unified product brand.
- Docker container + network names: `analyst-coder-*` → `quant-agent-*`.

## [0.2.4] — 2026-05-10 (`2bd04eb`)

### Fixed (7 Critical from 2026-04-30 audit)
- `_active_claude_instances` memory leak: `db_utils.delete_session` and `cleanup_all_sessions` now release the in-memory `ClaudeCodeService` after DB commit.
- Symlink-escape in workspace path validation on `/files/` endpoint: `relative_to()` replaces fragile `str(...).startswith(...)`.
- Backend healthcheck `start_period` 10s → 90s; added `stop_grace_period: 30s`.
- Drawer slide animation: split template `animate-slide-${side}` into literal class strings so Tailwind JIT compiles them.
- `Chart.tsx`: removed unused `DEMO_EQUITY_CURVE` export (broke Fast Refresh); added default export for future `React.lazy`.
- ESLint `react-hooks/set-state-in-effect` + `incompatible-library` disabled — over-aggressive for our fetch-effect patterns.
- New `.github/workflows/frontend-ci.yml`: tsc + eslint + vitest + build + 1 MB bundle ceiling.

## [0.2.3] — 2026-04-30 (`1d86fd5`)

### Added
- `backend/tests/test_cli_translator.py`: 21 tests including Hypothesis fuzz (~500 generated cases) — asserts the translator never raises on arbitrary input.
- Responsive layout below 1280px: right pane → Inspector slide-over drawer; below 768px also Nav drawer. Esc closes drawers.

### Changed
- nginx `/api/` location: `proxy_buffering off`, `proxy_request_buffering off`, `proxy_cache off`, `proxy_read_timeout 1h`, `chunked_transfer_encoding on` — SSE streams now flush through nginx in prod.
- `MarkdownWithLatex` lazy-loaded via `React.lazy`. KaTeX CSS moved into the chunk. Initial JS dropped from 219 KB → 100 KB gzipped (-55%).

### Removed
- `app/progress_tracker.py` + `/api/progress/{session_id}` endpoint (replaced by SSE per Phase 1 spec).

## [0.2.2] — 2026-04-30 (`bafe480`, `775b59c`)

### Fixed (6 Critical from 2026-04-29 audit)
- `git_utils.py`: HTTP basic auth via `http.extraheader` instead of URL-embedded creds; stderr redaction.
- `audit_logger.py`: `BEGIN IMMEDIATE` + retry on `SQLITE_BUSY` makes the audit-id sequence atomic.
- `event_broker.py`: closed sessions dropped from `_sessions` after last subscriber leaves.
- `main.py`: slowapi rate limiter (20/min/IP) on `/api/chat`.
- `sessionStore`: split `setSessionId` (sync, id-only) from `switchSession` (id + reset).
- `PromptInput`: active EventSource tracked in `useRef`, closed on unmount only; stale-session events filtered via `useSessionStore.getState().sessionId !== targetSid`.

## [0.2.1] — 2026-04-29 (Phase 3, `4dce120` + `49a776e`)

### Added
- Backend: `GET /api/audit/{session_id}` (paginated), `GET /api/artifacts/{id}/methodology`, `POST /api/export/pdf` (ReportLab branded).
- Frontend: real Plotly Chart component, TanStack DataTable, MethodologyPanel ("How this was made"), AuditTab populated from API, PDF export button, session-history reload hook.

## [0.2.0] — 2026-04-29 (Phase 2, `97e5a28`)

### Added
- Quant Console three-pane shell: BrandBar (navy/gold), ComplianceBar, StatusBar, ComplianceFooter, ThreePaneLayout.
- Left rail: SessionsList, WorkspaceTree, KnowledgePanel (later removed as placeholder).
- Center: ChatStream with UserMessage, ThinkingBlock, NotebookCell, BrandedArtifactCard, SubAgentIndicator, PlanRail.
- Right rail tabs: Plan / Agents / Activity / Artifacts / Report (stub) / Audit (stub).
- PromptInput with model selector pill, Send, Export PDF.
- Zustand session store + Immer eventReducer + Zod-validated SSE event types.
- React 19 + Vite 7 + Tailwind v4 + Inter + KaTeX.

### Removed
- Legacy single-pane Streamlit components: ChatMessage, ChatInput, Sidebar, ProgressIndicator.

## [0.1.0] — 2026-04-29 (Phase 1, `4f1b940` + `0f9cd20`)

### Added
- Typed Pydantic v2 event schema (20 events, discriminated union).
- Async `stream-json` line parser with `ParseStats`.
- Per-session `EventBroker` with `Last-Event-ID` replay (ring buffer).
- `cli_translator` mapping real Claude CLI `system`/`assistant`/`user`/`result` events to typed schema.
- `ClaudeCodeService` rewrite — per-message subprocess, `shutil.which`, `--verbose` flag (CLI requirement), synthetic `done` if CLI doesn't emit one.
- SSE endpoint `GET /api/chat/stream/{session_id}`; `POST /api/chat` returns 202 + `event_stream_url`.
- `audit_log` + `artifacts` migration; lightweight migration runner.
- `AuditLogger` writer (NOTE: only used in tests as of `0.2.4` — see Unreleased).
- GitHub Actions backend-ci workflow.

### Changed
- Backend now requires Python 3.11+ and the `claude` CLI on PATH (`shutil.which`).
