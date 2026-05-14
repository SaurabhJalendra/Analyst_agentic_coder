# Quant Agent — Idea Document

## The Problem
Existing AI coding assistants (Cursor, Copilot, Aider) are general-purpose. Financial/quant analysts need a Claude-powered coding environment that speaks their domain (notebooks, branded reports, compliance, audit trails) — not just code generation.

## The Solution
Custom Claude Code chatbot: per-session FastAPI backend spawns a Claude Code CLI subprocess in an isolated workspace. React frontend with Quant Agent brand (navy/gold), 3-pane layout (sessions/main/audit), notebook cells, branded artifact cards, methodology + audit tab, PDF export.

## Who It's For
Quant analysts, research engineers in finance, audit professionals. Anyone needing a Claude-powered coding interface with traceable artifacts and brand-aware output.

## Why This, Why Now
- Generic AI coding tools lack domain framing for quant/finance
- 2026: compliance + auditability matter more than ever
- Anthropic SDK + Claude Code CLI mature enough to wrap reliably
- Subprocess wrapper (instead of SDK) preserves Claude Code's full toolset

## Success Looks Like
- Per-session isolated workspaces (no cross-contamination)
- Brand-consistent output (navy/gold, Inter, KaTeX for math)
- Branded artifact cards with full methodology trail
- Audit tab shows every step taken in a session
- PDF export for compliance/handoff
- 3-pane layout works for power users
- Critical audit findings (from 2026-04-30 deep audit) all resolved

## Non-Goals
- ❌ Replace Claude Code itself (we're a UI on top)
- ❌ Multi-tenant SaaS (single-tenant, on-premise)
- ❌ Mobile-first (desktop is the primary)
- ❌ Non-financial domains (quant focus)
- ❌ Public hosting (private/enterprise deployment)

## Open Questions
- Should we support multiple Claude models in one session, or one-per-session?
- Audit trail format: structured JSON, prose, or both?
- Notebook cells: should we support runtime execution beyond Claude's output?
