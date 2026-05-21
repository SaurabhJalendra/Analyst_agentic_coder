# Spec — Vertical Slice: a real backtest, end to end

**Date:** 2026-05-21 · **Status:** Draft → build · **Style:** thin spec, spec-as-prototype

## Goal

The thinnest end-to-end build that makes the daily backtest dogfood real: the analyst asks for a backtest, the agent pulls data, writes and runs the backtest, and a **live equity-curve chart renders** in the chat — with the code and the DataFrame beside it.

**Done when:** the author runs a real backtest in Quant Agent and sees the equity curve, end to end. That's it. No report agent, no routines, no specialized sub-agents, no real bank-data connector — those wait for dogfood signal.

## The one hard problem

The `claude` CLI does not emit our `artifact` events — `cli_translator.py` only produces message / tool / done / cost events. So "the agent makes a chart" has to be solved by a **file convention**, not by hoping the CLI emits an artifact event.

## Design — the chart-artifact file convention

1. **The agent writes charts as files.** System-prompt instruction: when producing a chart, the agent writes `artifacts/<name>.chart.json` in the workspace, a Plotly-shaped payload: `{ "title": str, "data": [...], "layout": {...} }`.
2. **Backend scans for them.** After `ClaudeCodeService._run_one` finishes a turn, scan `<workspace>/artifacts/*.chart.json` for files new since the turn started. For each, INSERT an `artifacts` row (the table that's currently never written) and publish an `ArtifactCreateEvent` to the broker.
3. **The payload is fetched lazily, not streamed.** The SSE `ArtifactCreateEvent` stays lean (id, kind, title, source). The frontend fetches the chart data from a new endpoint `GET /api/artifacts/{artifact_id}/payload` — mirrors the existing methodology-fetch pattern. Keeps SSE light.
4. **Frontend renders it.** `BrandedArtifactCard` for `kind === 'chart'` fetches the payload and renders `<Chart data layout />` (the existing `Chart.tsx`, lazy-loaded). The "payload not yet emitted" placeholder is replaced.

## Data into the workspace

- Add `yfinance` and `pyarrow` to `backend/requirements.txt` — they land in the environment the `claude` subprocess inherits, so the agent's Bash can use them.
- System-prompt addition: the agent may use `yfinance` to pull equity OHLCV into `data/*.parquet` in the workspace. (Local stand-in for the real bank-data connector — that's a later milestone.)

## Tasks (TDD where it bites)

| # | Task | Files |
|---|---|---|
| 1 | Extend `artifacts` persistence: a writer that INSERTs an `artifacts` row | `backend/app/artifact_store.py` (new), `migrations` if a column is needed |
| 2 | Workspace artifact scanner: detect new `*.chart.json` after a turn, validate the Plotly shape, return artifact records | `backend/app/artifact_scanner.py` (new) + tests |
| 3 | Wire the scanner into `_run_one`: after the turn, scan → INSERT row → publish `ArtifactCreateEvent` | `claude_code_service.py` |
| 4 | `GET /api/artifacts/{artifact_id}/payload` — returns the stored `{data, layout}` for a chart artifact; 404 if none | `main.py` (or `routers/` once split) + test |
| 5 | System prompt: chart-json convention + `yfinance`/`data/*.parquet` guidance | `_build_system_prompt` in `main.py` |
| 6 | `requirements.txt`: add `yfinance`, `pyarrow` | `backend/requirements.txt` |
| 7 | Frontend: `BrandedArtifactCard` (kind=chart) fetches `/payload`, renders `<Chart>`; remove the placeholder | `BrandedArtifactCard.tsx`, `ChatStream.tsx`, `Chart.tsx` (lazy) |
| 8 | Smoke test: real `claude` CLI run that produces `data/*.parquet` + an `artifacts/*.chart.json`, verify the chart renders in the browser | manual / Chrome |

## Out of scope (explicit)

Real bank-data connector · specialized sub-agents · report agent / branded PDF · routines / scheduling · wiki compounding · observability · auth. All deferred to dogfood-driven Milestone 3+.

## Risks

- **The agent may not follow the chart-json convention reliably.** Mitigation: make the system-prompt instruction concrete with an example; the `/model-audit`-style skills come later. If it's flaky, a `/chart` skill that enforces the format is the fallback.
- **`yfinance` rate limits / flakiness.** Acceptable for a local dogfood stand-in; the real connector replaces it.
- **`Chart.tsx` lazy chunk** already exists; verify Plotly still tree-shakes and the bundle ceiling (1 MB) holds.

## Verification

Backend `pytest` green incl. new scanner + payload tests. Frontend `tsc` + `vitest` + `lint` green. Manual: a backtest prompt in the browser yields a rendered equity curve. Bundle under the CI ceiling.
