# Quant Agent — Idea Document

**Last updated:** 2026-05-21 (post-pivot)

## The problem

A quant research analyst at an investment bank spends ~70% of their time on *plumbing* — pulling data, writing boilerplate backtest code, formatting reports, re-deriving analyses they did three months ago — and only ~30% on actual research thinking. And every number they produce must be *defensible*: where did it come from, is it overfit, does it survive out-of-sample?

General AI coding tools (Cursor, Copilot, the `claude` CLI itself) help with the code but don't speak the domain: no notebooks tuned for quant work, no traceable artifacts, no audit trail, no compounding research memory, no connection to the firm's own datasets.

## The solution

A **quant research workbench** where the analyst commands a team of specialist Claude agents over their firm's data. Every backtest, chart, and report is traceable to its source and method; every analysis compounds into the firm's research memory.

Built on the Claude Code CLI as the agent runtime — its skills, sub-agent teams, MCP connectors, and scheduled routines are surfaced *as product features*, not hidden plumbing.

**One line:** *A research workbench where a quant analyst commands a team of specialist Claude agents over their firm's data — every result traceable to its source and method, every analysis compounding into firm research memory.*

## Who it's for

**Primary user:** a quant research analyst at an investment bank — mid-level, writes Python (pandas / numpy / statsmodels), understands backtesting, factor models, risk. They turn questions from PMs and the investment committee into defensible research.

**Audience for the output (not users):** PMs, the investment committee, clients — they receive the deliverables (branded reports, memos), they never touch the app.

**Deployment context:** inside the bank's perimeter. The datasets are the bank's, proprietary, and cannot leave. Quant Agent runs as a local process; data is worked on in place.

## The interaction model

The analyst is a **research director commanding a team.** They supply judgment, direction, and skepticism. The agent team supplies the labor — data wrangling, code, computation, formatting, traceability. The analyst stays in the loop on the *thinking*; the agent removes the *plumbing*.

Three modes of use:
1. **Interactive deep-dive** — a question → a traced answer + deliverable. The 80% case.
2. **Standing routines** — scheduled recurring research (daily data refresh, weekly factor monitor). The analyst wakes to flags, not a blank page.
3. **Knowledge recall** — "what did we find on momentum last quarter?" answered from the compounding wiki, with citations.

## The moat

**It shows its work.** An analyst (or the PM above them) can click any number → see the exact code, data version, and steps that produced it. That transparency surface — audit log, methodology trail, source attribution — is not decoration; it is *the product*. It's what a notebook tool, a code-assistant, or the raw CLI cannot copy, and it's what makes AI-generated quant research trustable.

## The honest bar

If Quant Agent isn't meaningfully better than "a quant just runs the `claude` CLI pointed at their data," it has no reason to exist. What clears that bar: the visible agent-team + audit + methodology surface, pre-built quant skills, the firm-data connector, and compounding research memory.

## Key design rule (data privacy)

**Compute over data locally; reason over results.** The agent writes a script, runs it on the firm's data *on disk*, and only derived results — aggregates, stats, charts, samples — enter the model context. Raw proprietary rows never stream to the API.

## Why this, why now

- 2026 Claude Code is far more capable than at first integration — skills, sub-agent teams, MCP, routines are mature and worth surfacing as product.
- Compliance and auditability of AI output matter more than ever; "shows its work" is timely.
- The subprocess-over-SDK choice (see `docs/adr/0001`) preserves Claude Code's full, evolving toolset for free.

## Explicitly out of scope

- **Trade execution / live strategy operation** — lives in the separate `Trading-Agent` repo. Quant Agent *researches and recommends*; it does not trade. (Future: it may hand a validated strategy spec to Trading-Agent.)
- **Multi-tenant SaaS** — single-firm, single-deployment for v1 (see `docs/adr/0003`).
- **Replacing the analyst** — it's a force multiplier for one analyst, not a headcount replacement.
- **Mobile-first / public hosting** — desktop, inside the firm perimeter.

## Success looks like

- The analyst's daily backtest/research loop runs *in* Quant Agent, not in a scratch notebook.
- Every figure in a deliverable is one click from its code + data lineage.
- A standing routine surfaces something useful before the analyst asks.
- The wiki answers a "what did we find last quarter" question without re-running the work.
- The author passes the 7-day Internal-DAU gate honestly.

## Open questions

- Real firm-data connector shape: file-mount, DB connection string, or a dedicated MCP server? (Decide when the vertical slice's yfinance stand-in is replaced.)
- Specialized sub-agents (data / backtest / risk / report) vs one generalist — decide from dogfood evidence.
- Auth: when does the v2 auth layer start? (Trigger criteria in `docs/adr/0004`.)

## Traceability

Vision → roadmap: `ROADMAP.md`. Decisions: `docs/adr/`. Latest audit: `docs/audit/`. Current build slice: `docs/superpowers/specs/`.
