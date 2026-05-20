# ADR 0002 — Server-Sent Events (SSE) for live agent streaming, not WebSocket

**Status:** Accepted (2026-04-29)
**Deciders:** Saurabh Jalendra
**Supersedes:** the polling `/api/progress/{id}` design (Phase 1 plan, since deleted)

## Context

The agent surface (plan steps, sub-agent spawns, tool calls, message deltas) needs to push live updates to the browser. Three options:
1. Long-poll (`/api/progress/{id}` every 1 s). What the original prototype did.
2. WebSocket (full duplex).
3. SSE (server → client only, HTTP/1.1 chunked).

## Decision

SSE via `sse-starlette`, exposed at `GET /api/chat/stream/{session_id}`. Frontend uses the browser-native `EventSource` with the built-in `Last-Event-ID` reconnect header. The endpoint replays buffered events from the per-session in-memory ring buffer.

## Consequences

**Positive**
- Browser `EventSource` is one line on the frontend; auto-reconnect with `Last-Event-ID` is built in.
- Works through nginx with the right `proxy_buffering off; proxy_read_timeout 1h;` config (we have it).
- HTTP/1.1; trivial to debug with `curl -N`.
- One direction matches the actual data flow (the user sends prompts via POST, not via the live stream).
- Stateless server side except for the broker ring buffer.

**Negative**
- Some corporate proxies still strip chunked transfer encoding. WebSockets are more universally supported in 2026 but not 2010 firewalls.
- No back-pressure signal from client to server: a slow consumer just gets dropped events when the broker buffer fills (200 events).
- Browsers cap concurrent EventSource connections at ~6 per origin (HTTP/1.1 limit). Not an issue for single-session use; would be for multi-monitor multi-session.

## Alternatives considered

1. **WebSocket.** Adds full duplex we don't need. More plumbing (no native browser API for typed events; need a JSON-frame protocol). Harder to inspect. No `Last-Event-ID` equivalent.
2. **Long-polling.** What v0 had. Wasted ~60 polls per 60-second agent run, all of which would still feel laggy.

## Reversal criteria

Switch to WebSocket if:
- We ever need client → server live messages (e.g., interactive approve/halt mid-stream that isn't a simple POST).
- The 6-concurrent-stream limit per origin bites in a multi-session UI.
- Deploying behind a corporate proxy that drops chunked HTTP.

## References

- Implementation: `backend/app/event_broker.py`, `backend/app/main.py:454-478`.
- Reconnect contract: `EventBroker.subscribe(session_id, last_event_id)` replays from the ring buffer.
- Frontend consumer: `frontend-react/src/services/eventStream.ts`.
