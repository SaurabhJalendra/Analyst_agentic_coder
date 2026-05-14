# Quant Agent — Roadmap

**Last updated:** 2026-05-13

## Now (next 2-4 weeks)
- Resolve remaining audit findings (7 Critical from 2026-04-30 deep audit) — partially done
- Finish frontend Phase 3 polish (Plotly chart, TanStack table, methodology, audit, PDF export, history reload)
- Backend Phase 3 endpoints: audit list, artifact methodology, branded PDF export
- Tighten CORS allowlist + remove dead docker-entrypoint

## Next (1-3 months)
- Real Claude CLI stream-json → typed events (backend done, expand coverage)
- Multi-repo workspace support (one session, many repos)
- Persistent session state (resume across page reloads)
- Authentication (single-tenant but with login)
- Audit replay (re-run a session from saved state)

## Later (exploratory)
- Customer dashboard (manage multiple analysts' sessions)
- Slack/Linear integration via Claude MCP
- Custom Claude Code skills bundled per industry vertical
- Branded artifact templates for common quant outputs (backtests, factor models)

## Recently Shipped (last 10)
- ✅ 7 Critical findings from 2026-04-30 deep audit (fixed)
- ✅ 5-item Important-fixes wave (audit follow-up polish)
- ✅ Frontend: 2 Critical audit findings (EventSource + setSessionId)
- ✅ Backend: 4 Critical audit findings
- ✅ Frontend: remove fake placeholders, wire real data sources
- ✅ Backend: translate real claude CLI stream-json to typed events
- ✅ Frontend Phase 3 polish — Plotly chart, TanStack table, methodology, audit tab, PDF export
- ✅ Backend Phase 3 endpoints — audit list, artifact methodology, branded PDF export
- ✅ CORS tighten + /api/files traversal hole fix + drop dead docker-entrypoint
- ✅ Frontend ThreePaneLayout in App + PromptInput + remove legacy components

## Not Doing
- ❌ Multi-tenant SaaS (intentionally on-premise / single-tenant)
- ❌ Mobile app
- ❌ Non-quant domains
- ❌ Replace Claude Code itself
- ❌ Public hosting
