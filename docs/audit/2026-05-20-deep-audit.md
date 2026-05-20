# Quant Agent — Deep Audit 2026-05-20

**Scope:** Full-project audit across idea fidelity, architecture, frontend UX, backend correctness, security & production readiness, observability/ops, docs & onboarding.
**Method:** 7 parallel Explore agents (one lens each) + my own baseline checks. Every finding below is verified against actual code (cite `file:line`). False positives from agents are listed separately.
**Branch state:** `feature/phase-1-backend-streaming`, 32 commits ahead of `main`, pushed to origin. Backend tests 66/66, frontend 14/14, tsc clean, lint clean.

---

## TL;DR — what's true

The architecture and the streaming pipeline are real and good. The visible product is a **convincing-looking institutional console with hollow compliance**. The thing the compliance bar says ("MNPI walls: ON", "Entitlements: X") is decorative — no enforcement. The audit log table is wired into a `/api/audit/{id}` reader **but the production code never writes a single row** (`AuditLogger` is instantiated only in tests). The product loop has never closed: the author hasn't used this 7 days in a row (Internal-DAU gate per Cat Wu / Anthropic).

This passes "looks like a smart prototype". It does not yet pass "an institutional buy-side analyst trusts it with capital decisions."

---

## ✅ What's verified working

- **Streaming pipeline end-to-end**: `POST /api/chat` → spawn CLI per message → translate stream-json → SSE → frontend `EventSource` → Zustand store → re-render. Real assistant text flows.
- **Per-session workspace isolation**: each session in its own dir, git-cloneable, gated by `relative_to()` on the `/files/` endpoint.
- **Plan / sub-agent / activity / artifact tabs**: render from real SSE events (verified in earlier Chrome session).
- **Branded artifact cards** with "How this was made" expand calling `GET /api/artifacts/{id}/methodology`.
- **PDF export** endpoint returns a real branded PDF.
- **Session switch + history reload** via `useSessionHistory` hook with cancel-on-rapid-switch.
- **Rate limit, CORS allowlist, symlink-escape fix, EventBroker session cleanup, slowapi, BEGIN IMMEDIATE audit-id sequencing** — all verified live in code.
- **Branch pushed, GitHub repo renamed to `quant-agent`, local origin updated.**

---

## 🚨 Critical — block any client pilot

### C1. The audit log is never written
**Verified by:** `grep -rn "AuditLogger(" backend/` → only `tests/`. The production `chat()` handler never instantiates `AuditLogger` or calls `.append()`. The `audit_log` table is permanently empty in any deployed instance.
**Impact:** Every compliance story collapses. PDF exports reference an audit ID that has no corresponding row. `/api/audit/{session_id}` returns empty arrays in production. The whole "institutional traceability" pillar is decoration.
**Fix:** Instantiate one `AuditLogger` in `main.py` startup; pass it as a dependency to the chat handler; call `.append()` on user message + each SSE event. ~3 hours.

### C2. Compliance bar is cosmetic
**Verified by:** `frontend-react/src/App.tsx` passes no `entitlements`/`mnpiOn` props to `ComplianceBar`. `BrandBar` also gets no `userIdentity`/`userTier`/`rmName`. The bar always renders the defaults; "MNPI walls: ON" is a string label with zero enforcement logic anywhere in the call path.
**Impact:** A sophisticated analyst notices in 30 seconds that the compliance posture is theater. Any real client review fails.
**Fix:** Either remove the labels entirely (don't lie) OR wire `/api/entitlements/{session_id}` (currently doesn't exist) and have the backend block CLI calls for non-entitled data sources. ~2 days for the stub; weeks for real enforcement.

### C3. Path-traversal hole still open in `/api/workspace/{id}/list/`
**Verified by:** `backend/app/main.py:723` still uses `if not str(full_path).startswith(str(workspace_resolved))`. The companion `/api/workspace/{id}/files/{path}` endpoint at line 661 was fixed (`relative_to`); the list endpoint was not.
**Impact:** Sibling-directory traversal works (e.g. workspace at `/data/ws-X` accepts `/data/ws-X-evil/...` because the prefix matches). Same class of bug we fixed in the 7-Critical wave.
**Fix:** Same one-liner — `relative_to(workspace_resolved)` in a try/except. 5 min.

### C4. ⌘K is a visual lie
**Verified by:** `frontend-react/src/components/frame/StatusBar.tsx` renders `⌘K` as a `<span>` with cursor:pointer but **no event handler**. Grep finds no command-palette implementation anywhere.
**Impact:** Power users see ⌘K, expect Linear-style fuzzy search, click, get nothing. Immediately undermines trust in everything else.
**Fix:** Either remove the visual (10 min) or build a minimal command palette using `cmdk` library (4 hours).

### C5. `main.py` is 1,084 lines
**Verified by:** `wc -l backend/app/main.py` → 1084. 25+ endpoints; HTTP routing, system-prompt building, message reconstruction, session lifecycle, PDF rendering all in one file. No `APIRouter` separation.
**Impact:** New endpoints land here too; merge conflicts compound; tests can't target individual concerns; code review is impossible at scale.
**Fix:** Split into `routers/chat.py`, `routers/workspace.py`, `routers/audit.py`, `routers/export.py`, `routers/sessions.py`, with `main.py` reduced to wiring. ~4 hours.

### C6. Internal-DAU gate failed
**Verified by:** Commit history is project-setup + build-out + audit-fix sprints. No 7 consecutive days of "user noticed X, fixed X" iteration. The product was built top-down from the spec, never lived in.
**Impact:** Per Anthropic launch criterion (and our own CLAUDE.md rule 6g): "use the feature yourself daily for 7 consecutive days BEFORE any public release. Skip a day → reset counter." This is the hardest gate to fake. Without it, all the polish is unvalidated.
**Fix:** Saurabh actually uses Quant Agent every day for a week to do a real quant task (a backtest, a market summary, a small piece of investment research) and the fixes from that loop land. Calendar-driven, not code-driven.

---

## 🟡 Important — fix before "best-in-class" claim

### I1. README + QUICKSTART + CLAUDE.md still reference Streamlit
**Verified:** README has 7 "Streamlit" mentions, QUICKSTART 2, CLAUDE.md 2, AUTHENTICATION_SETUP.md 3. The project hasn't used Streamlit since the Phase 1 redesign months ago.
**Impact:** A new dev cloning the repo follows README, can't find `streamlit_app.py`, abandons setup.
**Fix:** Targeted rewrite of the front matter of each. ~30 min.

### I2. CLAUDE.md "Architecture" section claims polling, not SSE
**Verified:** `CLAUDE.md` (project) line 48 still says "Frontend polls `/api/progress/{id}` every 1000ms during long requests; no SSE/WebSocket." This is the architecture we replaced in Phase 1.
**Impact:** Any agent/dev reading this thinks the system is polling-based.
**Fix:** Update that line + the "Known Issues" section (most are fixed). ~10 min.

### I3. Mypy strict: 71 errors, ruff: 119 (53 auto-fixable)
**Verified by agent run.** Mostly missing return-type annotations in `main.py`, untyped sqlite cursors, missing stubs for reportlab.
**Impact:** Backend CI uses these tools; PRs would fail. Our own `backend-ci.yml` workflow runs mypy.
**Fix:** Add `reportlab-stubs`; annotate handlers; ruff --fix the 53 mechanical ones. ~3 hours.

### I4. UTF-8 decode-on-chunk-boundary risk in SSE reader
**Verified by:** `claude_code_service.py:130` does `raw.decode("utf-8", errors="replace").rstrip("\n")` per `readline()`. If a multi-byte UTF-8 character splits across a chunk boundary, `errors="replace"` silently replaces it with U+FFFD, corrupting the JSON line, which the translator drops.
**Impact:** Silent data loss under network/buffer pressure with non-ASCII output.
**Fix:** Use `asyncio.StreamReader.readuntil(b'\n')` and decode after the full line is assembled. ~30 min.

### I5. `_active_claude_instances` factory race
**Verified by:** `workspace_manager.get_or_create_service` does a dict lookup + factory call + dict insert WITHOUT a lock. Two concurrent `/api/chat` POSTs for the same fresh session_id can both spawn a service. The `asyncio.Lock` inside `ClaudeCodeService` only serializes future calls, not creation.
**Impact:** Two subprocesses for the same session, one leaks. Hard to repro in tests; will happen under burst load.
**Fix:** Wrap the lookup-or-create in a per-session async lock. ~20 min.

### I6. `audit_log` and `artifacts` retention unbounded
**Verified by:** `migrations/001_audit_artifacts.sql` has no retention. No cleanup job. Grows forever.
**Impact:** Long-running deploy fills disk; SQLite slows down on huge `audit_log`.
**Fix:** `DELETE FROM audit_log WHERE ts < datetime('now', '-90 days')` periodic. ~20 min once we actually populate the table (C1).

### I7. Frontend has zero error boundary, zero client-side logging
**Verified by agent + code read.** A React render exception white-screens the page; no telemetry, no Sentry init, no `componentDidCatch` boundary, no `console.error` aggregation.
**Impact:** A bad deploy hides; we discover failures only via "the chat won't load" user complaints.
**Fix:** Add `<ErrorBoundary>` around the `<ThreePaneLayout>`; consider Sentry for now; at minimum `window.addEventListener('error', ...)` ship to backend. ~2 hours.

### I8. Frontend Plotly + KaTeX cargo-culted but unused at runtime
**Verified by:** `Chart.tsx` is no longer imported anywhere; `BrandedArtifactCard` renders a placeholder. `plotly.js-basic-dist-min`, `react-plotly.js`, `@types/react-plotly.js` remain in `package.json`.
**Impact:** ~5 MB of `node_modules` for nothing; future accidental import would re-bloat the bundle.
**Fix:** Either delete `Chart.tsx` + remove the 3 plotly deps, OR wire real chart payloads through artifact events (Phase 3.1 work). 10 min vs ~6 hours.

### I9. No ADRs exist
**Verified:** No `docs/adr/` directory. Major decisions (CLI-over-SDK, SSE-over-WS, SQLite-vs-Postgres, no-auth-v1, Zustand-vs-Redux, per-message subprocess) live in commit messages or implicit in code. Per workspace CLAUDE.md rule 6f, every major decision needs an ADR.
**Impact:** In 6 months no one will remember WHY any of these were chosen. Reversing them is unsafe.
**Fix:** Write 4–6 ADRs. ~2 hours.

### I10. No LICENSE, no CHANGELOG
**Verified:** `ls LICENSE*` → not found. No `CHANGELOG.md`. README references `[Your License Here]` as a literal placeholder.
**Impact:** Per workspace CLAUDE.md rule 6l, every project needs both. README is also broken (placeholder text).
**Fix:** Add MIT LICENSE (or chosen) + Keep-a-Changelog format CHANGELOG seeded from `git log`. ~30 min.

### I11. Hardcoded `opus-4.7 ▾` model selector
**Verified:** `PromptInput.tsx:108-110` — a `<span>` with the string "opus-4.7 ▾", no dropdown, no model state, no propagation to backend.
**Impact:** Same trust hole as ⌘K. Says "you can change model"; can't.
**Fix:** Either remove the pill or build a real `<select>` + thread the choice into `POST /api/chat`. ~1 hour.

### I12. Drawer animate-slide-* class verification
**Verified by:** I fixed the template-string bug last session by hardcoding the two literal class strings. Tailwind config has keyframes. But the agent flagged it again, so let me triple-check: `ThreePaneLayout.tsx` uses literal `animate-slide-left` / `animate-slide-right`. Verified in code. ✅ Closed.

### I13. Workspace tree at `<1280px` invisible
**Verified:** Left rail collapses to a drawer toggle at `<768px` only. Between 768–1280, left rail is inline (220px); fine. At `<768`, the Nav drawer opens. No issue here that needs an immediate fix.

### I14. Backend healthcheck `/health` is a stub
**Verified:** `backend/app/main.py:316` returns `{"status":"healthy"}` regardless. Doesn't probe DB, doesn't probe `claude` CLI, doesn't probe workspace dir.
**Impact:** Container reports healthy while CLI auth is expired, DB is corrupt, or audit logger fails. Healthcheck is theater.
**Fix:** Add `/ready` that probes DB write + `shutil.which("claude")` + workspace dir writable. ~30 min.

### I15. No observability (Prometheus / Sentry / OTel)
**Verified:** No `/metrics` endpoint. No Sentry init. No OTel SDK in `requirements.txt`. Logs go to stdout, lost on container restart.
**Impact:** Production debugging is grep-the-container-logs-before-it-dies.
**Fix:** Add `prometheus-client` for `/metrics`; add Sentry SDK with DSN env var; add `structlog.contextvars` for request-correlation IDs. ~4 hours total.

### I16. SQLite has no WAL mode + no backup
**Verified:** `database.py` uses default SQLite journal mode (rollback). Audit_logger opens a fresh connection per write. No `PRAGMA journal_mode=WAL` anywhere. No backup sidecar.
**Impact:** Power loss can corrupt the DB. No PITR.
**Fix:** Enable WAL on connection setup. Add a backup sidecar (sqlite3 .backup nightly to S3 or local). ~1 hour.

### I17. Wiki is dormant after initialization
**Verified by:** `wiki/log.md` has 1 entry (the 2026-04-29 initialization). No subsequent `/wiki-ingest` or `/wiki-query` runs. The Karpathy LLM-Wiki pattern doesn't compound knowledge if no one writes to it.
**Impact:** Wiki is structurally correct but operationally dead. Just-in-time knowledge from this audit is going into THIS document, not the wiki.
**Fix:** After this audit, `/wiki-ingest` a new source page from the audit findings. Set a discipline to log significant decisions in `wiki/log.md`. Cultural, not technical.

---

## 🔵 Minor

- **Hypothesis cache committed?** No (verified gitignored).
- **`backend/=4.0.0` stray file** from earlier `pip install reportlab>=4.0.0` shell mishap — has been cleaned up.
- **Subagent activity log gap**: `eventReducer.ts` doesn't push an activity entry on `subagent.delta`. Minor UX inconsistency.
- **Plotly + KaTeX font ttf files in dist/** not pre-gzipped (`gzip_static off`).
- **MethodologyPanel uncached** — every expand fires a fresh axios. Use TanStack Query or in-store memoization.
- **Cold-start `start_period: 90s`** undocumented (we bumped it; nowhere is the 30-60s CLI auth time written down).
- **Stale env var passthroughs in `docker-compose.yml`**: `MAX_CONTEXT_LENGTH`, `LOG_LEVEL`, `GITHUB_ACCESS_TOKEN` are passed but never read by the app. Dead config.

---

## 🔁 False positives I caught in agent reports (do NOT chase)

- **".env tracked in git, secrets exposed"** — VERIFIED FALSE. `git ls-files | grep -E "^\.env$"` returns nothing. `.env` is gitignored. The Security agent saw the working-tree file and assumed.
- **"Hardcoded `C:\Users\Saurabh\...\claude.exe` path"** — VERIFIED FALSE. `grep` of `claude_code_service.py` finds no such path. Fixed in commit `909c62b` to `shutil.which("claude")`.
- **"Double DoneEvent race"** — VERIFIED FALSE. When the translator emits a `DoneEvent` (from a real CLI `result`), `emitted_done` is set, and `_publish_synthetic_done()` is gated behind `if not emitted_done`. No double-fire possible.
- **"BrandBar identity not rendered → trust issue"** — INTENTIONAL. We intentionally removed the hardcoded placeholders in the placeholder-cleanup commit. The UX agent flagged this as a bug; it's the correct state until real auth lands.

---

## Where it stacks up vs the goal

The goal: "a product like it has been made by the Anthropic team."

The honest gap:
- **Idea-fidelity**: 6/10 — substrate is right, compliance pillar is theater.
- **Architecture**: 7/10 — clean module boundaries, good event model, but `main.py` bloat + audit-write disconnect.
- **Code quality**: 6/10 — tests for new modules, none for legacy. Mypy + ruff not clean.
- **UX polish**: 6/10 — looks the part on first glance, breaks under scrutiny (fake selectors, dead ⌘K, no empty state).
- **Production readiness**: 3/10 — no auth, no obs, no backups, no real audit, no SSL.
- **Documentation**: 4/10 — wiki + plans + spec exist, but README/CLAUDE.md/QUICKSTART are stale.
- **Innovation/novelty**: 7/10 — the live agent surface (plan + sub-agents + sources + audit) is genuinely differentiated; just needs to be true rather than rendered.

**Overall: 5.5/10 against the stated target.** Real architecture, hollow guarantees, untested product loop.

---

## Recommended next-3-week plan (40 hours)

**Wave 1 — close the compliance hole (8h)**: C1 (wire AuditLogger), C2 (either remove the fake labels or stub the entitlements API), C3 (path-traversal fix on list endpoint), C4 (kill ⌘K span).

**Wave 2 — make it real (10h)**: Split `main.py` into routers (C5). UTF-8 boundary fix (I4). Factory race fix (I5). Audit + artifacts retention (I6). Healthcheck + `/ready` (I14).

**Wave 3 — make it a product (10h)**: Frontend error boundary (I7). Real ⌘K command palette OR remove. Model selector dropdown wired. Empty-state examples on first load. Activity entry for subagent.delta.

**Wave 4 — make it dependable (10h)**: Observability — Prometheus `/metrics`, Sentry, request correlation IDs (I15). SQLite WAL + nightly backup sidecar (I16). 4 ADRs (CLI/SSE/SQLite/Auth) (I9). LICENSE + CHANGELOG (I10). README/CLAUDE.md/QUICKSTART update (I1, I2). Mypy/ruff cleanup (I3).

**Wave 5 — Internal-DAU (calendar)**: Saurabh uses Quant Agent every working day for a real quant task. 7 consecutive days. Log the friction. Fix the top 5 things he stubs his toe on. Only after this is the product allowed to ship.

After Wave 5, the project is genuinely ready to demo to a buy-side client. Until then, it's a high-quality prototype.

---

**End of audit.**
