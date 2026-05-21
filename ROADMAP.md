# Quant Agent — Roadmap

**Last updated:** 2026-05-21 (post-pivot to P1 + dogfood-first sequencing)
**Vision:** `IDEA.md` · **Audit:** `docs/audit/2026-05-20-deep-audit.md` · **Current slice spec:** `docs/superpowers/specs/2026-05-21-vertical-slice.md`

## How we build (the Anthropic way)

We stop building toward the audit's full punch-list. We build the **thinnest real thing**, dogfood it daily, and let *use* drive what we fix next. Spec-as-prototype; Internal-DAU gate; weekly honest `/demo`; polish only what we actually touch.

---

## Milestone 0 — Close Wave 1 (in progress)

The compliance-honesty + security fixes from the deep audit. Correct under every product direction.
- ✅ C2 — removed cosmetic compliance labels (honest pilot framing)
- ✅ C3 — path-traversal fix on `/api/workspace/{id}/list/`
- ✅ C4 — removed dead ⌘K span
- ◐ C1 — wire `AuditLogger` into the chat pipeline (in progress)

---

## Milestone 1 — THE VERTICAL SLICE (the immediate goal, ~1 week)

The thinnest end-to-end build that makes the daily backtest dogfood *real*. Spec: `docs/superpowers/specs/2026-05-21-vertical-slice.md`.

**In the slice:**
1. **Chart payload pipeline** — backend emits real series in `ArtifactCreateEvent`; frontend renders a live Plotly chart. *This is the single most important item — without the equity curve, day 1 of dogfood fails.*
2. **Data into the workspace** — a `yfinance → parquet` capability as a local stand-in for the bank-data connector. The agent can pull equity OHLCV into the session workspace.
3. **The loop works** — analyst asks for a backtest → agent loads data → writes + runs backtest code → notebook cell shows code + DataFrame + the equity-curve chart.

**Out of the slice (waits for dogfood signal):** real bank-data connector, specialized sub-agents, report agent / branded PDF, routines, wiki compounding, observability, auth.

**Done when:** the author can run a real backtest in Quant Agent and see the equity curve, end to end.

---

## Milestone 2 — Internal-DAU (calendar-driven, ~1 week)

7 consecutive working days. The author uses the vertical slice every working day for a real backtest. One line per day in `tasks/lessons.md`: what broke, what was annoying. Skip a day → reset the counter. Weekly `/demo` for an honest "did I actually use it."

**This milestone produces the priority list for everything after.** We do not pre-plan Milestone 3+ in detail — the dogfood writes it.

---

## Milestone 3+ — Driven by dogfood (rough buckets, re-ranked by use)

The audit's remaining items live here, **un-prioritized until dogfood ranks them:**

- **Backend hardening** — split `main.py` into routers; UTF-8-on-chunk fix; lock `get_or_create_service` factory; `audit_log`/`artifacts` retention prune; real `/ready` endpoint.
- **Frontend** — `<ErrorBoundary>`; empty-state example prompts; real model selector; `subagent.delta` activity entry; WCAG-AA pass.
- **Dependability** — observability (`/metrics`, the chosen own-`/api/client-errors` endpoint, correlation IDs); SQLite WAL + backup sidecar; mypy/ruff cleanup.
- **The real data connector** — replace the yfinance stand-in with a firm-data connector (file-mount / DB / MCP — shape TBD) + the "compute-locally" discipline.
- **Specialized agents** — turn generic sub-agents into data / backtest / risk / report specialists.
- **Report agent** — real branded PDF with artifact bodies, not metadata.
- **Wiki compounding** — analyses auto-distil into the research knowledge base; `/wiki-query` recall.
- **Routines** — scheduled recurring research (daily data refresh, weekly factor monitor).

---

## Next (1–3 months)

- Auth stub (HS256 JWT, flat user list); `actor` column on `audit_log`; BrandBar identity from token.
- Methodology narrative — LLM-generated synthesis, not the templated string.
- Search across sessions; saved analyses (pin a session as a template).
- Hygiene: Trivy/CodeQL in CI; SBOM per release; JS license-compliance audit.
- ADRs 0005–0007: per-message-subprocess; in-memory rate-limit single-process assumption; Zustand-over-Redux.

## Later (3–6 months — exploratory)

- Postgres migration (ADR-0003 reversal criteria).
- OIDC / SAML SSO. Audit-log immutability (hash-chain / S3 Object Lock).
- Excel/CSV export; compare/diff mode; multi-window pop-out charts; dark mode.
- Hand-off integration: Quant Agent → `Trading-Agent` (validated strategy spec).
- Feature flag system for staged rollout.

---

## Recently Shipped

- 2026-05-21: pivot to P1 (workbench, orchestration + knowledge folded in); IDEA.md rewritten; roadmap re-sequenced dogfood-first; vertical-slice spec.
- 2026-05-20: deep audit + LICENSE + CHANGELOG + 4 ADRs + CLAUDE.md cleanup + lessons.md seeded.
- 2026-05-14: renamed Analyst Agentic Coder → Quant Agent; GitHub repo renamed; branch pushed.
- 2026-05-10: 7 Critical audit fixes (memory leak, symlink escape, healthcheck, drawer animation, lint, Chart cleanup, frontend CI).
- 2026-04-30: 5-item Important wave (nginx SSE, cli_translator tests + fuzz, progress_tracker removal, lazy-load -55% JS, responsive ≤1280px).
- 2026-04-30: 6 Critical audit fixes (git creds, audit-id atomicity, broker GC, slowapi, EventSource cleanup, sessionStore race).
- 2026-04-29: Phase 3 (Plotly/TanStack/methodology/audit/PDF + backend endpoints).
- 2026-04-29: Phase 2 frontend (three-pane console shell, Zustand, SSE consumer).
- 2026-04-29: Phase 1 backend (typed event schema, stream-json parser, event broker, audit logger, ClaudeCodeService rewrite, SSE endpoint, CI).

---

## Not Doing

(per Cat Wu "say no" discipline — track rejected ideas so they don't come back)

- **Trade execution** — lives in the separate `Trading-Agent` repo. Quant Agent researches and recommends; it does not trade.
- **Multi-provider AI** (OpenAI, Gemini, local LLMs). The product is opinionated about Claude.
- **Multi-tenant SaaS** for v1 — single firm, single deployment.
- **Custom React framework / Next.js migration.** SPA + FastAPI is the right cut.
- **Voice I/O. Mobile app.** Institutional analysts are on desktops.
- **No-code agent builder.** The differentiator is transparency over a Claude agent, not another no-code platform.
- **Crypto / web3.** Out of scope.
