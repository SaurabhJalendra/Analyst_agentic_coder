# Quant Agent — Roadmap

**Last updated:** 2026-05-20 (post deep-audit)
**Audit source:** `docs/audit/2026-05-20-deep-audit.md`

The plan reflects the post-audit reality: real architecture, hollow guarantees, untested product loop. The goal of the next month is to honor the stated idea (institutional research console with traceable artifacts) rather than ship more surface area.

---

## Now (next 2–3 weeks, ~40h)

### Wave 1 — close the compliance hole (~8h)
- **C1** Wire `AuditLogger` to the chat endpoint. Every user message + every SSE event a row in `audit_log`. The PDF "Audit ID" is finally real.
- **C2** Decide: either (a) remove the fake "MNPI walls" / "Entitlements" labels from `ComplianceBar`, or (b) stub a real `/api/entitlements/{session_id}` and have the backend block CLI calls for non-entitled data sources. (a) is honest and 30 minutes; (b) is honest and 2 days.
- **C3** Path-traversal fix on `/api/workspace/{id}/list/` (use `relative_to`, mirror the `/files/` fix).
- **C4** Wire `⌘K` to a minimal `cmdk`-based palette (search sessions + send predefined prompts) OR remove the visual lie.

### Wave 2 — make the backend real (~10h)
- Split `main.py` (1,084 lines) into `routers/{chat,sessions,workspace,audit,export}.py`. `main.py` becomes wiring only.
- UTF-8-on-chunk-boundary fix in `claude_code_service._run_one` (use `readuntil('\n')` with buffered decode).
- Lock the `get_or_create_service` factory.
- Add periodic (hourly) `audit_log` + `artifacts` retention prune. Add `WORKSPACE_BASE_DIR` periodic cleanup (not just startup).
- Real `/ready` endpoint that probes DB write + `shutil.which("claude")` + workspace dir writable. Keep `/health` shallow.

### Wave 3 — make the frontend real (~10h)
- `<ErrorBoundary>` around `<ThreePaneLayout>`. Surface errors as toasts, not white screens.
- Empty-state in `ChatStream` — "Try: backtest momentum on SPY 2010-2024" example prompts. First-touch friction crusher.
- Model selector pill becomes a real `<select>` and threads through to the backend.
- `subagent.delta` writes an activity entry.
- WCAG-AA pass: focus rings on every interactive element, ARIA roles on rail tabs, color-contrast fix on brand bar text.

### Wave 4 — make it dependable (~10h)
- Observability: `prometheus-client` `/metrics`, Sentry SDK init (back + front), request-correlation-id middleware in structlog.
- SQLite WAL mode + nightly backup sidecar (sqlite3 .backup).
- Mypy strict cleanup (71 → 0) and ruff auto-fix pass.
- README + QUICKSTART rewrite (remove all Streamlit references, add `npm install` step, link AUTHENTICATION_SETUP).
- ADRs 0005–0007: per-message-subprocess, slowapi-in-memory-rate-limit (single-process assumption), Zustand-over-Redux.

### Wave 5 — Internal-DAU (calendar-driven, not code-driven)
- 7 consecutive working days. Saurabh uses Quant Agent for a real piece of quant work (one per day). One commit per day capturing what broke and why. Skip a day, restart the counter.

---

## Next (1–3 months)

- **Auth stub** (HS256 JWT issued by `/api/auth/login` backed by a flat user.yaml). Wire BrandBar identity from token claims. Add `actor` column to `audit_log`.
- **Real chart payloads.** Backend includes Plotly data in `ArtifactCreateEvent`. Re-enable the `Chart` component lazy-load.
- **Report tab** — drag artifacts + narrative blocks into a draft, export branded PDF with audit ID.
- **Methodology narrative** — LLM-generated synthesis instead of the templated string we ship today.
- **Search across sessions** — left-rail search input over session titles + audit-log keyword grep.
- **Saved analyses** (Cat Wu pattern) — pin a session as a template.
- **Hygiene**: Trivy/CodeQL in CI; SBOM (CycloneDX) per release; license-compliance audit of frontend deps.

---

## Later (3–6 months — exploratory)

- Postgres migration (ADR-0003 reversal criteria) once concurrent sessions > 50 OR a second tenant is added.
- OIDC / SAML for enterprise SSO.
- Audit log immutability — hash-chain or S3 Object Lock.
- Excel/CSV export of any table.
- Compare/diff mode — pin two artifacts side by side.
- Multi-window pop-out for charts (institutional dual-monitor workflow).
- Dark mode toggle (spec was light-only v1).
- Internationalization (English only today).
- Feature flag system (OpenFeature / Unleash) for staged rollout.

---

## Recently Shipped

- 2026-05-20: deep audit + LICENSE + CHANGELOG + 4 starter ADRs + CLAUDE.md cleanup + lessons.md seeded.
- 2026-05-14: project renamed Analyst Agentic Coder → Quant Agent; GitHub repo renamed; branch pushed for first time.
- 2026-05-10: 7 Critical audit fixes (memory leak, symlink escape, healthcheck, drawer animation, lint, Chart cleanup, frontend CI).
- 2026-04-30: 5-item Important wave (nginx SSE, cli_translator tests + Hypothesis fuzz, progress_tracker removal, lazy-load -55% initial JS, responsive ≤1280px).
- 2026-04-30: 6 Critical audit fixes (git creds, audit-id atomicity, broker session GC, slowapi, EventSource cleanup, sessionStore race).
- 2026-04-29: Phase 3 polish (Plotly, TanStack, methodology panel, audit tab, PDF export, history reload).
- 2026-04-29: Phase 3 backend (audit list, methodology, PDF export endpoints).
- 2026-04-29: Phase 2 frontend (three-pane console shell, Zustand store, SSE consumer).
- 2026-04-29: Phase 1 backend (typed event schema, async stream-json parser, event broker with Last-Event-ID, audit logger, ClaudeCodeService rewrite with stream-json + shutil.which + restart_if_needed + --verbose, SSE endpoint, 202 POST /api/chat, GitHub Actions CI).

---

## Not Doing

(per Cat Wu "say no" discipline — track rejected ideas so they don't come back)

- **Multi-provider AI** (OpenAI, Gemini, local LLMs). The product is opinionated about Claude; provider-neutrality is not a feature here.
- **Custom React framework / build tool.** Vite is fine.
- **Move to Next.js.** SPA + FastAPI is the right cut for this product.
- **Voice input / output.** Not the persona.
- **Mobile app.** Institutional analysts are on desktops with 2 monitors.
- **No-code agent builder.** The differentiator is *transparency over a Claude agent*, not "another no-code platform."
- **Crypto / web3 integration.** Out of scope.
