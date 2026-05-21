# Quant Console — Frontend Redesign & Backend Streaming

**Date:** 2026-04-29
**Status:** Draft — pending user review
**Author:** Claude (Opus 4.7) under Saurabh's direction
**Supersedes:** Current `frontend-react/` UI

---

## Context

The repo is a Claude AI coding chatbot wrapping the `claude` CLI as a per-session subprocess. The existing React frontend is functional but generic (single-pane chat, dark theme, polling-based progress). The actual user is a **sophisticated institutional client of an investment bank** (asset manager, hedge fund analyst/PM, corporate treasury) — not an internal quant. The product is being renamed **Quant Console**.

This redesign delivers an agentic, transparent, branded research interface that exposes the full Claude Code surface (plan, sub-agents, tools, MCP sources, memory, skills) while wrapping it in the institutional polish (brand bar, compliance, entitlements, audit, branded PDF export) the audience requires.

Backend rewrite is in scope: replace polling-based progress with `stream-json` event streaming from the CLI, surfaced to the frontend via SSE.

---

## Goals (v1)

1. **Three-pane layout** — sessions + workspace tree (left) / chat + artifacts (center) / agent inspector (right).
2. **Live streaming of the agent's full surface** — plan steps, sub-agent spawns, tool calls, MCP source access, memory ops, skills invoked, extended thinking — surfaced as transparency, not as a power-user dump.
3. **Branded artifact rendering** — charts (Plotly), tables (AG-Grid-style), DataFrames, code+output notebook cells, math (KaTeX), diagrams (Mermaid). Every artifact has a "How this was made" expand.
4. **Compliance & audit** — compliance bar, entitlements indicator, MNPI walls indicator, source attribution on every artifact, audit ID footer, branded PDF export with disclosures.
5. **Backend streaming** — `claude --output-format stream-json` parsed incrementally, fanned out via SSE; old `/api/progress` polling removed.
6. **Quant Console branding** — institution-agnostic chrome (no hard-coded bank name), navy/gold premium aesthetic.

## Non-goals (v1)

- Templates marketplace, RM-curated content sharing, multi-tenant permissions, role-based UI tiers
- Real-time collaborative editing across users
- Mobile / tablet layouts (desktop ≥1280px assumed)
- Internationalization (English-only)
- Replacing SQLite (capacity is fine for v1)

---

## Persona

| Attribute | Value |
|---|---|
| Role | Buy-side analyst, PM, or quant-research-savvy treasurer |
| Sophistication | Reads methodology, expects provenance, will write Python if shown |
| Primary deliverable | Branded report/chart/memo to a PM, IC, or stakeholder |
| Compliance posture | Subject to MNPI walls, entitlement-gated data, audit retention |
| Tooling familiarity | Bloomberg Terminal, Aladdin, AlphaSense, Refinitiv Eikon |
| Screen | Desktop 1280px+ — densely-laid-out terminals are normal |

## Success criteria

1. A user can submit a multi-step quant research prompt and see the agent plan, dispatch sub-agents, hit data sources, generate artifacts, and draft a deliverable — **all visible live**.
2. Every artifact in the chat is **branded**, has a **"How this was made"** expand showing methodology + sources, and can be **exported as a branded PDF** with compliance footer + audit ID.
3. The compliance bar surfaces **entitlements + MNPI status** at all times. Data-source pills reflect what was actually accessed in the current session.
4. The backend streams events; the frontend uses `EventSource`. Polling is removed.
5. WCAG AA contrast met in light theme. Keyboard navigable (⌘K command palette, ⏎ to send, ⌘⏎ to plan).

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│ React 19 SPA (Vite, TS, Tailwind v4)                            │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ EventSource → /api/chat/stream/{session_id}             │    │
│  │ Reducer → Zustand session store → component re-render    │    │
│  └─────────────────────────────────────────────────────────┘    │
└──────────────────────────────┬──────────────────────────────────┘
                               │ HTTP/SSE
┌──────────────────────────────▼──────────────────────────────────┐
│ FastAPI backend (uvicorn)                                       │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ /api/chat (POST)         → spawn/reuse CLI, return 202   │   │
│  │ /api/chat/stream/{id}    → SSE: typed event stream       │   │
│  │ /api/sessions/...        → unchanged                     │   │
│  │ /api/workspace/.../files → unchanged                     │   │
│  │ /api/files/{path}        → REMOVED (security hole)       │   │
│  │ /api/progress/{id}       → REMOVED (replaced by SSE)     │   │
│  └──────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ ClaudeCodeService (rewritten)                             │   │
│  │   spawn: claude -p "..." --output-format stream-json      │   │
│  │   parser: line-by-line, typed events                      │   │
│  │   broker: per-session asyncio.Queue + audit logger         │   │
│  └──────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ AuditLogger     EntitlementsService (stub v1)             │   │
│  └──────────────────────────────────────────────────────────┘   │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                    ┌──────────▼─────────┐
                    │ claude CLI (subproc)│
                    │ workspaces/{uuid}/  │
                    └─────────────────────┘
                    ┌─────────────────────┐
                    │ SQLite              │
                    │  sessions, messages │
                    │  tool_calls, audit  │
                    └─────────────────────┘
```

---

## Frontend components

All components in `frontend-react/src/`. Folder layout follows the existing convention (`components/`, `hooks/`, `services/`, `types/`).

### Frame components (always visible)
- `BrandBar.tsx` — Quant Console logo (gold Q-mark) + user identity + RM contact line. Navy gradient background.
- `ComplianceBar.tsx` — disclaimer text + entitlements pill + MNPI walls indicator + last-refresh time.
- `StatusBar.tsx` — session selector display + plan progress badge + agent count + sources accessed pills + ⌘K + Halt.
- `ComplianceFooter.tsx` — full disclosures + audit ID + RM contact + support email. Navy background.

### Layout
- `ThreePaneLayout.tsx` — CSS grid, 220px / fluid / 360px columns, configurable resize handles (defer drag-resize to v1.1 if cheap).

### Left rail
- `LeftRail.tsx` — container.
- `SessionsList.tsx` — current sessions, active highlight, "+ New session" affordance.
- `WorkspaceTree.tsx` — collapsible folder tree of `data/`, `artifacts/`, `reports/`, `notebooks/`. Click-to-preview file in center pane. Backed by `GET /api/workspace/{id}/list/{dir:path}`.
- `KnowledgePanel.tsx` — wiki page count, memory count, last-ingest indicator. Links to wiki.

### Center
- `ChatStream.tsx` — virtualized scrollable list of message turns (user + assistant + sub-agent indicators).
- `UserMessage.tsx` — light-blue rounded bubble, right-aligned, max 75% width.
- `ThinkingBlock.tsx` — collapsed amber pill showing token count and a 1-line preview; expandable to full thinking content.
- `NotebookCell.tsx` — bordered card with three sections: code (dark slate), output (DataFrame or text), chart (if present). Header shows duration, rerun button.
- `BrandedArtifactCard.tsx` — navy-header card wrapping any artifact (chart, table, report excerpt). Header has accent-gold "Q · QUANT CONSOLE", footer has source line + "How this was made" expand.
- `MethodologyPanel.tsx` — expandable detail of how an artifact was made: prompt, tool calls, sub-agent involvement, data sources, code, params, audit IDs.
- `SubAgentIndicator.tsx` — colored left-border banner (blue=running, purple=queued, green=done) with one-line status. Clicking opens the agent's full breakdown in the right pane.
- `PlanRail.tsx` — inline strip showing "Plan — 5/8 steps · 2 sub-agents in parallel" between turns.

### Right rail (tabbed)
- `RightRail.tsx` — container with tab bar.
- `Tab: Plan` — full plan tree with steps, sub-agents nested under steps, time elapsed, click to expand.
- `Tab: Agents` — agent cards (running/queued/done), per-agent stats (tokens, tools, model), sources accessed (generic names, not MCP identifiers).
- `Tab: Activity` — chronological event stream (typed events, color-coded by category), filterable.
- `Tab: Artifacts` — gallery of artifacts produced this session. Each shows preview, provenance metadata, "Pin", "Add to Report" actions.
- `Tab: Report` — narrative builder. Drag artifacts in, edit prose, export. v1: minimal editor (textarea + drop zones); v2: rich editor.
- `Tab: Audit` — full session audit log: every prompt, every output, every tool call, every entitlement check. Searchable. Exportable.

### Bottom prompt
- `PromptInput.tsx` — textarea with auto-resize, model selector pill, workspace selector pill, attach-data button, attach-file button, **Export PDF** button (primary). Enter to send, ⌘⏎ to plan-mode.

### Renderers (named library-agnostically — chosen impl tracked in Open questions)
- `Chart.tsx` — interactive chart (Plotly or ECharts; decide during Phase 3).
- `DataTable.tsx` — sortable / filterable / sticky-header table (TanStack Table v1; AG Grid only if a feature gap emerges).
- `MarkdownWithLatex.tsx` — `react-markdown` + `remark-math` + `rehype-katex`.
- `MermaidDiagram.tsx` — render Mermaid source to SVG.
- `CodeBlock.tsx` — syntax-highlighted (highlight.js v1; shiki only if accuracy complaints).

### State
- Zustand session store (introduce; don't pile more state into `useChat`):
  ```ts
  interface SessionStore {
    sessions: Session[]
    currentSessionId: string | null
    messages: Message[]
    plan: PlanState
    agents: AgentState[]
    activity: ActivityEvent[]
    artifacts: Artifact[]
    sources: SourceState
    isStreaming: boolean
    error: ErrorState | null
    // selectors, actions...
  }
  ```
- Replace `useChat.ts` with thin hooks that select from the store.

---

## Backend changes

### Removed
- `GET /api/progress/{id}` — replaced by SSE.
- `GET /api/files/{path:path}` — known security hole; remove entirely. Workspace-scoped reads stay.

### Added
- `GET /api/chat/stream/{session_id}` — SSE endpoint streaming typed events. Supports `Last-Event-ID` for reconnect.
- `GET /api/audit/{session_id}` — paginated audit log read for the Audit tab.
- `GET /api/entitlements/{session_id}` — current client entitlements snapshot (mocked v1).

### Modified
- `POST /api/chat` — accepts the prompt, persists the user message, kicks off the CLI subprocess if needed, returns `202 Accepted` with `session_id` and `event_stream_url`. Does NOT block on the agent's response.
- `ClaudeCodeService` — rewritten to:
  - Switch to `--output-format stream-json`.
  - Parse the stream line-by-line into typed events.
  - Push events into a per-session `asyncio.Queue` consumed by SSE.
  - Persist relevant events to SQLite (messages, tool_calls, audit_log).
  - Replace the hardcoded path `C:\Users\Saurabh\.local\bin\claude.exe` with `shutil.which("claude")`.
  - Implement `restart_if_needed()` body (currently incomplete).

### New tables (SQLite)
- `audit_log(id, session_id, ts, event_type, prompt_id, tool_call_id, data_json, entitlements_snapshot)` — one row per audit-relevant event.
- `artifacts(id, session_id, kind, title, source_attribution, methodology_json, file_path, created_at)` — one row per generated artifact.

---

## Event schema

All SSE events are JSON, keyed by `type`. The frontend reducer dispatches by type.

```ts
// Plan
type PlanStartEvent      = { type: 'plan.start';      planId: string; steps: { id: string; description: string }[] }
type PlanStepStartEvent  = { type: 'plan.step.start'; stepId: string }
type PlanStepDoneEvent   = { type: 'plan.step.done';  stepId: string; durationMs: number }

// Sub-agents
type SubagentSpawnEvent  = { type: 'subagent.spawn';  agentId: string; parentId?: string; kind: 'researcher'|'verifier'|'explore'|'plan'|'general'; model: string; prompt: string }
type SubagentDeltaEvent  = { type: 'subagent.delta';  agentId: string; tokens: number; statusText?: string }
type SubagentDoneEvent   = { type: 'subagent.done';   agentId: string; durationMs: number; tokens: number; result?: string }

// Tools
type ToolCallStartEvent  = { type: 'tool.start'; callId: string; agentId: string; tool: 'Read'|'Write'|'Edit'|'Bash'|'Grep'|'Glob'|'WebSearch'|'WebFetch'|string; argsRedacted: object }
type ToolCallDoneEvent   = { type: 'tool.done';  callId: string; durationMs: number; ok: boolean; resultPreview?: string }

// Skills
type SkillInvokeEvent    = { type: 'skill';     name: string; args?: string }

// Memory / Wiki
type MemoryOpEvent       = { type: 'memory';    op: 'read'|'write'; path: string }
type WikiOpEvent         = { type: 'wiki';      op: 'read'|'ingest'|'lint'|'query'; target: string }

// MCP / Sources
type SourceAccessEvent   = { type: 'source';    source: 'Bloomberg'|'Polygon'|'S&P'|'MSCI'|'GIR'|'Internal'|string; operation: string; bytes?: number }

// Thinking
type ThinkingBlockEvent  = { type: 'thinking';  agentId: string; tokens: number; previewText: string }

// Artifact
type ArtifactCreateEvent = { type: 'artifact';  artifactId: string; kind: 'chart'|'table'|'code'|'report'|'file'; title: string; sourceAttribution: string; methodologyId: string }

// Message
type MessageDeltaEvent   = { type: 'message.delta'; messageId: string; appendText: string }
type MessageDoneEvent    = { type: 'message.done';  messageId: string }

// Cost (optional, hidden from client UI in v1 but persisted for admin)
type CostDeltaEvent      = { type: 'cost.delta';  usd: number; tokensIn: number; tokensOut: number }

// Errors / control
type ApprovalNeededEvent = { type: 'approval';  approvalId: string; description: string; danger: boolean }
type ErrorEvent          = { type: 'error';     code: 'TIMEOUT'|'AUTH_REQUIRED'|'ENTITLEMENT_DENIED'|'CLI_CRASH'|string; message: string; recoverable: boolean }
type DoneEvent           = { type: 'done';      sessionId: string }
```

Every event carries a server-assigned monotonic `id` (used as SSE `id:` header) so reconnect via `Last-Event-ID` is correct.

---

## Data flow

**Send a message:**
1. Client `POST /api/chat` with `{ session_id, message }`. Server persists user message, ensures CLI subprocess for the session (spawning if needed), returns `202` with `event_stream_url`.
2. Client opens `EventSource(/api/chat/stream/{session_id})`.
3. Server feeds the prompt to the CLI; CLI emits stream-json on stdout.
4. `ClaudeCodeService` parses each line, maps to a typed event, pushes onto the session's queue, and (for audit-relevant events) writes to `audit_log`.
5. SSE endpoint drains the queue, formats SSE frames (`event: <type>\ndata: <json>\nid: <n>\n\n`), flushes.
6. Client reducer receives events, mutates Zustand store, components re-render only the affected panes.
7. On `done`, client closes the EventSource. The complete message + tool calls are now in the DB; reload-resilience comes from re-reading from DB on session switch.

**Receive a final artifact:**
1. CLI emits `artifact` event with `methodologyId`.
2. Frontend renders a `BrandedArtifactCard` in the chat stream and adds an entry to the Artifacts tab.
3. Clicking "How this was made" calls `GET /api/artifacts/{id}/methodology` to load the full methodology (which is too large to ship in the event).

---

## Visual design

### Color tokens (Tailwind-extend)
| Role | Token | Hex |
|---|---|---|
| Brand primary (navy) | `brand.900` | `#0a1929` |
| Brand secondary (deep navy) | `brand.800` | `#0f1f3a` |
| Accent (gold) | `gold.500` | `#d4a017` |
| Accent dark (gold) | `gold.700` | `#b8860b` |
| Compliance (amber bg) | `amber.50` | `#fef9e7` |
| Compliance border | `amber.300` | `#f3d775` |
| Surface | `slate.50` | `#f8fafc` |
| Surface raised | `white` | `#ffffff` |
| Text primary | `slate.900` | `#0f172a` |
| Text secondary | `slate.600` | `#475569` |
| Text muted | `slate.400` | `#94a3b8` |
| Border | `slate.200` | `#e2e8f0` |
| Pos | `emerald.600` | `#059669` |
| Neg | `red.600` | `#dc2626` |
| Sub-agent: research | `sky.500` | `#0ea5e9` |
| Sub-agent: verifier | `purple.500` | `#a855f7` |
| Sub-agent: done | `emerald.600` | `#059669` |

### Typography
- Display & UI: **Inter** (variable, fallback to system-ui)
- Monospace (code, DataFrames, activity stream): **JetBrains Mono** or system ui-monospace
- Type scale: 9px (label), 10px (meta), 11px (UI default), 12px (body), 13px (heading), 16px (page title)

### Density
- Three-pane requires ≥1280px viewport. Below 1280px, right pane collapses to a slide-over (v1.1).
- Default font sizes are dense (10–12px) — appropriate for institutional users used to Bloomberg.

---

## Compliance & audit

### Compliance bar (always visible)
- Disclaimer: "⚠ Institutional clients only · Not investment advice · See disclosures"
- Entitlements pill: lists licensed feeds with status (LIVE / DELAYED / NONE)
- MNPI walls indicator: ON/OFF
- Last-refresh timestamp

### Entitlements
- Stored as a JSON snapshot per session, fetched on session start from `GET /api/entitlements/{session_id}` (mocked v1 returns a fixed entitlement set; real implementation later).
- Every data-source access is gated by entitlements at the API layer; UI shows a placeholder with "Tier upgrade required — contact your RM" if a request was blocked.
- The entitlement snapshot at session start is recorded in the audit log; subsequent changes (rare) are recorded as separate audit entries.

### Audit log
- Every prompt, every artifact, every tool call, every source access, every approval — appended as a row to `audit_log` with `entitlements_snapshot` reference.
- Audit ID format: `SES-<date>-<client-slug>-<seq>` (e.g. `SES-2024-04-29-acme-0042`).
- Footer surfaces the current audit ID; the Audit tab in the right pane shows the full searchable log.
- PDF exports embed the audit ID + disclosure footer.

### PDF export
- Backend endpoint `POST /api/export/pdf` takes a session ID + a list of artifact IDs + optional narrative blocks → returns a branded PDF with: cover (Quant Console logo, session title, client name, audit ID, date), the artifacts in order, narrative interspersed, and a final disclosure page.
- Watermarked with client identifier on each page.
- Defer rich layout to v1.1; v1 is a clean serial composition.

---

## Error handling

| Failure | Detection | UI behavior | Recovery |
|---|---|---|---|
| CLI hangs >600s | Timeout in `ClaudeCodeService` | Emit `error TIMEOUT`; chat shows red banner with "Retry" button; Halt button always live | User clicks retry or Halt-and-edit-prompt |
| Claude auth expired | Detected from CLI exit code or stderr `401` | Emit `error AUTH_REQUIRED`; modal in center pane with "Contact your RM" + RM contact info | Admin renews tokens out-of-band |
| Entitlement denied for source | API gate before invoking source | Emit `error ENTITLEMENT_DENIED`; placeholder card in chat with explanation; methodology panel records it | User contacts RM (link in placeholder) |
| MCP source down | Source returns error | Source pill in status bar turns amber; emit a `source` event with `error: true`; methodology records the fallback | Agent proceeds in degraded mode if possible |
| SSE disconnect (network blip) | EventSource `error` event | Auto-reconnect with `Last-Event-ID`; backend buffers last 200 events per session in memory + persisted in audit log | Transparent to user |
| Browser closed mid-stream | Backend continues executing | When user returns, reload from DB; truncated stream is re-streamed from `Last-Event-ID` if backend still alive | DB reload guarantees no data loss |
| CLI crash | Subprocess returns non-zero | Emit `error CLI_CRASH`; mark session as needing restart; `restart_if_needed()` rebuilds the CLI on next prompt | Next prompt auto-recovers |

---

## Testing strategy

### Visual regression
- Storybook stories for every component in 3 modes: default, loading, error.
- Playwright snapshot tests against Storybook in WCAG-AA color mode.
- Run on every PR that touches `frontend-react/`.

### API contract
- The existing `/api-contract-check` skill (we built it) runs in CI; backend Pydantic models ↔ frontend TS types must match.

### Streaming pipeline
- `tests/fixtures/stream_json/` — canned `stream-json` outputs for: simple message, multi-step plan, sub-agent dispatch, tool calls, error paths.
- A mock CLI binary that emits a fixture file → `ClaudeCodeService` parses → assert events match expected sequence.
- This decouples backend tests from the actual `claude` binary.

### End-to-end
- Cypress (or Playwright) test:
  1. Start backend with mock CLI.
  2. Open Quant Console.
  3. Send prompt "Backtest momentum on SPY".
  4. Assert plan rail populates with 8 steps.
  5. Assert sub-agent indicator appears.
  6. Assert artifact card renders.
  7. Click "Export PDF" → assert downloaded PDF contains: audit ID, disclosures, the artifact, footer.

### Compliance
- Golden-file test: render an artifact card → assert source line + "How this was made" link + branded header are all present.
- Entitlement-denial test: mock entitlements service to deny credit data → assert placeholder card renders with RM contact link, no real data leaked.

### Manual
- Browser test on at least Chrome 120+, Edge 120+ (typical institutional browsers; Firefox/Safari are best-effort v1).

---

## Standards & tooling

This section is the contract for "best-in-class dev standards." Every choice below is specific; vague aspirations don't count.

### Frontend
- **Language**: TypeScript with `strict: true`, `noUncheckedIndexedAccess: true`, `exactOptionalPropertyTypes: true`. No `any`, no `// @ts-ignore` without an issue link.
- **Build**: Vite 7 with `@vitejs/plugin-react-swc` (existing). Bundle budget enforced by `size-limit` (≤ 500 KB gzipped initial JS).
- **State**: Zustand + `immer` middleware. Server state via **TanStack Query** for cache + retry semantics on REST endpoints; SSE state stays in Zustand.
- **Runtime validation**: **Zod** schemas for every backend response and every SSE event before they reach the reducer. No `any` from the wire.
- **Styling**: Tailwind v4 with the brand color tokens above. No inline styles in production code (mockups exempt).
- **Lint**: ESLint 9 flat config + `typescript-eslint` `strict-type-checked` + `stylistic-type-checked` + `eslint-plugin-react-hooks` + `eslint-plugin-jsx-a11y`.
- **Format**: Prettier (default config + project-specific overrides for line length 100).
- **Tests**: Vitest + React Testing Library for units. Playwright for e2e. **axe-core** integrated into Playwright for accessibility regression. **Storybook 8** for component docs; visual regression via **Chromatic** (or Playwright snapshot if cost is a concern).
- **Coverage**: ≥80 % statements on the store + reducers + event parser; UI components covered by Storybook + visual snapshots.
- **Performance budget**: Lighthouse CI in PR checks — Performance ≥ 90, Accessibility = 100, Best Practices ≥ 90.
- **Bundle hygiene**: `rollup-plugin-visualizer` report on every build; PRs that grow main chunk by >5 % flag for review.

### Backend
- **Language**: Python 3.12+. Full type hints. `mypy --strict` in CI.
- **Lint/format**: **Ruff** (replaces black + isort + flake8 + pyupgrade). One tool, one config.
- **Models**: **Pydantic v2** for every API model and event schema. No raw dicts crossing API/SSE boundaries.
- **Tests**: pytest + pytest-asyncio + pytest-cov. **Hypothesis** for property-based testing of the stream-json event parser (random byte streams must never crash it). Coverage ≥ 80 %.
- **Async**: pure `asyncio`. No threading except for unavoidable subprocess management.
- **Logging**: **structlog** with JSON output. Every request has a correlation ID. Audit events log at INFO; tool calls at DEBUG.
- **Tracing**: OpenTelemetry SDK with OTLP exporter. Every `/api/chat`, every SSE stream, every CLI subprocess spawn is a span.
- **Errors**: structured error responses (RFC 7807 `application/problem+json`). Never leak stack traces to the client.

### CI / repo
- **GitHub Actions** workflows: `lint`, `typecheck`, `test`, `e2e`, `visual-regression`, `security-scan` — all required to merge.
- **Conventional Commits** enforced via commitlint + Husky.
- **Pre-commit** hooks: ruff, prettier, eslint, mypy on staged Python files only.
- **Dependabot** for npm + pip + GitHub Actions.
- **CodeQL** SAST scan on every push to main.
- **Secret scanning** (GitHub native + custom regex for `CLAUDE_CODE_*` tokens).
- **SBOM** generation (CycloneDX) attached to every release.

### Security
- **CORS**: replace `allow_origins=["*"]` with explicit allowlist (institution domain in prod, `localhost:3000` in dev). The current open CORS is a known issue from the audit.
- **Auth**: API gates require a session token (v1 stub: signed cookie + entitlements snapshot; real OIDC/SAML deferred to v2).
- **CSP**: strict Content-Security-Policy header — `default-src 'self'`, no inline scripts, no `eval`.
- **HTTPS only** in prod (Nginx terminates TLS).
- **Rate limiting**: per-session and per-IP at the API gateway (slowapi or nginx-limit-req).
- **No secrets in code or logs**. `.env` only; CI uses repo secrets; structlog scrubs `CLAUDE_CODE_*` and any header named `Authorization`.

### Observability
- **Metrics**: `/metrics` endpoint (Prometheus format) — request latency, SSE connection count, CLI subprocess count, audit-log writes/sec.
- **Errors**: Sentry (or self-hosted GlitchTip) for unhandled exceptions, both backend and frontend.
- **Logs**: structured JSON, shipped to whatever the institution uses (Datadog / ELK / Splunk).
- **Dashboards**: stub Grafana dashboards committed in `ops/dashboards/` for: request latency, agent step durations, source access frequency, audit-log volume.

### Accessibility
- **WCAG 2.1 AA** mandatory. Verified via axe-core in Playwright.
- **Keyboard navigation**: every action reachable without a mouse. ⌘K palette, ⏎ to send, ⌘⏎ to plan, Esc to halt.
- **Focus management**: visible focus rings (Tailwind `ring-2 ring-gold-500 ring-offset-2`).
- **Screen reader**: ARIA labels on icons, `aria-live="polite"` for the activity stream and plan rail.

### Documentation
- **Storybook** for every component (props table, usage examples, visual states).
- **OpenAPI** auto-generated from FastAPI; bundled into the Storybook docs site.
- **ADRs** (Architecture Decision Records) in `docs/adr/` for non-obvious choices (e.g. "ADR-001: stream-json over SSE not WebSocket").
- The existing `wiki/` (Karpathy LLM Wiki pattern) continues to compound knowledge across sessions.
- Every new package added to `package.json` / `requirements.txt` has a one-line justification in the PR description.

### What this raises above the current state

| Area | Now | Standard |
|---|---|---|
| Frontend tests | None visible | Vitest + RTL + Playwright + axe + Chromatic |
| Backend tests | Loose scaffolds (`test_endpoint.py`, `test_imports.py`) | pytest + Hypothesis, ≥80 % coverage, in CI |
| Lint | Frontend ESLint only | Ruff (BE) + ESLint flat + Prettier + commitlint, all enforced via Husky + CI |
| Type checking | Frontend TS, no Python `mypy` | TS strict + `mypy --strict` |
| CORS | `["*"]` | Explicit allowlist |
| Auth | None | Session-token stub (v1), OIDC/SAML (v2) |
| Observability | structlog imported, not configured | structlog JSON + OTel + Prometheus + Sentry |
| Docs | README.md + ad-hoc | Storybook + OpenAPI + ADRs + wiki |
| Security scanning | None | CodeQL + Dependabot + secret scan + SBOM |
| Accessibility | Untested | WCAG AA verified by axe in CI |

---

## Migration path

This is too big for a single commit. Three phases:

**Phase 1 — Backend streaming foundation** (no UI change yet)
- Switch `ClaudeCodeService` to `--output-format stream-json`.
- Implement event parser + `asyncio.Queue` per session.
- Add `/api/chat/stream/{id}` SSE endpoint.
- Keep `/api/progress/{id}` polling alive in parallel for safety.
- Tests: streaming pipeline against fixtures.

**Phase 2 — Frontend three-pane shell**
- Add `BrandBar`, `ComplianceBar`, `StatusBar`, `ComplianceFooter`, `ThreePaneLayout`.
- Wire left rail (`SessionsList`, `WorkspaceTree`, `KnowledgePanel`) and right rail tabs (`Plan`, `Agents`, `Activity`, `Artifacts`).
- Convert `useChat` to Zustand store + `EventSource` consumer.
- Remove polling hooks.
- Tests: Storybook + visual regression.

**Phase 3 — Branded artifacts + Audit + PDF**
- `BrandedArtifactCard`, `MethodologyPanel`, `PlotlyChart`, `AGGridTable`, `MarkdownWithLatex`.
- Audit tab + audit log persistence.
- PDF export endpoint.
- Remove `/api/files/{path}` and `/api/progress/{id}`.
- Hardcoded CLI path → `shutil.which`.
- Tests: e2e + compliance golden.

Each phase is independently shippable.

---

## Open questions

- **Plotly vs ECharts vs lightweight custom?** Plotly has the largest bundle but the best out-of-box quant-flavored charts. Decide during Phase 3.
- **AG Grid (commercial) vs TanStack Table (free)?** AG Grid is the institutional standard but has license cost. TanStack covers most needs. Default to TanStack v1; upgrade if a feature is missing.
- **`shiki` vs `highlight.js` for code blocks?** Shiki is ~10× larger but produces accurate VS-Code-style highlighting. Default to highlight.js; revisit if quality complaints.
- **Resize handles between panes?** Defer to v1.1.
- **Offline / cached artifact viewing?** Out of scope — backend is required for all renders.
- **Token/cost meter for admin/RM**: where does it live? Admin dashboard is out of v1 scope; events are persisted, dashboard later.

---

## Appendix A — Files touched

### New (frontend)
- `frontend-react/src/components/{BrandBar,ComplianceBar,StatusBar,ComplianceFooter,ThreePaneLayout}.tsx`
- `frontend-react/src/components/{LeftRail,RightRail,SessionsList,WorkspaceTree,KnowledgePanel}.tsx`
- `frontend-react/src/components/{ChatStream,UserMessage,ThinkingBlock,NotebookCell,BrandedArtifactCard,MethodologyPanel,SubAgentIndicator,PlanRail}.tsx`
- `frontend-react/src/components/right-rail/{PlanTab,AgentsTab,ActivityTab,ArtifactsTab,ReportTab,AuditTab}.tsx`
- `frontend-react/src/components/renderers/{Chart,DataTable,MarkdownWithLatex,MermaidDiagram,CodeBlock}.tsx`
- `frontend-react/src/store/sessionStore.ts` (Zustand)
- `frontend-react/src/services/eventStream.ts` (EventSource wrapper)
- `frontend-react/src/types/events.ts` (typed event schema mirroring backend)

### Modified (frontend)
- `frontend-react/src/App.tsx` — replace single-pane chat with `ThreePaneLayout`
- `frontend-react/src/services/api.ts` — drop polling, add stream URL builder, add audit/entitlements endpoints
- `frontend-react/src/hooks/useChat.ts` — gut and replace with thin selectors over `sessionStore`
- `frontend-react/tailwind.config.js` — add brand/gold color tokens, font stacks
- `frontend-react/src/index.css` — Inter font, JetBrains Mono import
- `frontend-react/package.json` — add: `zustand`, `react-plotly.js`, `@tanstack/react-table`, `react-markdown`, `remark-math`, `rehype-katex`, `mermaid`, `highlight.js`. Remove: unused `react-syntax-highlighter`.

### New (backend)
- `backend/app/event_schema.py` — Pydantic models for typed events
- `backend/app/event_broker.py` — per-session asyncio.Queue + SSE serialization
- `backend/app/audit_logger.py` — append-only audit log
- `backend/app/entitlements.py` — stub service (returns mock entitlements)
- `backend/app/artifacts.py` — artifact metadata + methodology storage
- `backend/app/pdf_export.py` — PDF generation (defer impl detail; ReportLab or WeasyPrint)
- `backend/migrations/<n>_add_audit_artifacts.sql` — new tables

### Modified (backend)
- `backend/app/main.py` — add `/api/chat/stream`, `/api/audit`, `/api/entitlements`, `/api/export/pdf`; remove `/api/progress`, `/api/files/{path}`; change `/api/chat` to 202-Accepted
- `backend/app/claude_code_service.py` — switch to `stream-json`, line parser, fan to broker, fix hardcoded path, implement `restart_if_needed`
- `backend/app/database.py` — add `audit_log`, `artifacts` tables
- `backend/requirements.txt` — add: `sse-starlette`, `reportlab` (or `weasyprint`)

### Deleted
- `backend/test_endpoint.py`, `backend/test_imports.py` — debugging scaffolding
- `nul`, `backend/backend_logs.txt`, dead `docker-entrypoint.sh`
- The `anthropic` SDK dep in `requirements.txt` (unused since CLI migration)

---

## Appendix B — What this design intentionally does not solve

| Concern | Why deferred |
|---|---|
| RM-shared / curated content | Out of v1 audience scope; no immediate user benefit |
| Templates marketplace | Sophisticated client persona writes free-form prompts |
| Multi-tenancy / RBAC | Single client per backend instance in v1 |
| Mobile / tablet | Institutional users are on desktop; under 1280px collapses to v1.1 slide-over |
| i18n | English-only v1 |
| Real-time multi-user collab | Single-user sessions in v1 |
| Cost meter visible to client | Hidden — bank eats cost; admin dashboard is out of v1 |
| Replacing SQLite | Capacity is fine for the v1 user count |
