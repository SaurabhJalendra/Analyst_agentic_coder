"""Translates raw `claude --output-format stream-json` lines into our typed events.

The actual Claude Code CLI emits events with these top-level types:
  - "system"   — meta/init events (hook_started, hook_response, init). Ignored for UI.
  - "assistant" — message.content[] of {type:'text'|'tool_use', ...}
  - "user"     — message.content[] of {type:'tool_result', ...} (when a tool returns)
  - "result"   — final summary with the answer + cost + usage
  - "rate_limit_event" — informational rate-limit status. Ignored for UI.

Our internal SSE schema was designed for an idealized agentic surface (plan/subagent
events). The CLI doesn't emit those. This translator maps the CLI's real output into
the subset of our schema that makes sense (message.delta/done, tool.start/done, cost,
done). For test fixtures that already speak our typed schema, we fall back to the
typed parser.
"""
from __future__ import annotations

import json

from pydantic import ValidationError

from app.event_schema import (
    AnyEvent,
    CostDeltaEvent,
    DoneEvent,
    MessageDeltaEvent,
    MessageDoneEvent,
    ToolDoneEvent,
    ToolStartEvent,
    parse_event,
)


class CLITranslator:
    """Stateful translator. One instance per send_message call."""

    def __init__(self, session_id: str) -> None:
        self._session_id = session_id
        self._last_message_id: str | None = None

    def translate(self, line: str) -> list[AnyEvent]:
        """Translate one stdout line. Returns 0+ typed events."""
        line = line.strip()
        if not line:
            return []
        try:
            raw = json.loads(line)
        except json.JSONDecodeError:
            return []

        if not isinstance(raw, dict):
            return []

        t = raw.get("type")

        # Native CLI types
        if t == "system":
            return []  # init/hook_started/hook_response — meta, ignore in UI
        if t == "rate_limit_event":
            return []
        if t == "assistant":
            return self._translate_assistant(raw)
        if t == "user":
            return self._translate_user(raw)
        if t == "result":
            return self._translate_result(raw)

        # Fallback: maybe a typed event (mock CLI / test fixtures use our schema)
        try:
            return [parse_event(line)]
        except ValidationError:
            return []

    def _translate_assistant(self, raw: dict) -> list[AnyEvent]:
        msg = raw.get("message") or {}
        msg_id = str(msg.get("id") or self._last_message_id or "msg-1")
        self._last_message_id = msg_id
        content = msg.get("content") or []
        events: list[AnyEvent] = []
        for item in content:
            if not isinstance(item, dict):
                continue
            kind = item.get("type")
            if kind == "text":
                text = str(item.get("text", ""))
                if text:
                    events.append(
                        MessageDeltaEvent(
                            type="message.delta",
                            message_id=msg_id,
                            append_text=text,
                        )
                    )
            elif kind == "tool_use":
                events.append(
                    ToolStartEvent(
                        type="tool.start",
                        call_id=str(item.get("id") or ""),
                        agent_id="main",
                        tool=str(item.get("name") or "unknown"),
                        args_redacted=item.get("input") or {},
                    )
                )
        return events

    def _translate_user(self, raw: dict) -> list[AnyEvent]:
        msg = raw.get("message") or {}
        content = msg.get("content") or []
        events: list[AnyEvent] = []
        for item in content:
            if not isinstance(item, dict) or item.get("type") != "tool_result":
                continue
            preview = item.get("content")
            if isinstance(preview, list):
                # content can be a list of {type:"text", text:"..."}
                preview_text = " ".join(
                    str(p.get("text", "")) for p in preview if isinstance(p, dict)
                )
            else:
                preview_text = str(preview or "")
            events.append(
                ToolDoneEvent(
                    type="tool.done",
                    call_id=str(item.get("tool_use_id") or ""),
                    duration_ms=0,  # CLI doesn't report per-tool duration
                    ok=not bool(item.get("is_error", False)),
                    result_preview=preview_text[:300] if preview_text else None,
                )
            )
        return events

    def _translate_result(self, raw: dict) -> list[AnyEvent]:
        events: list[AnyEvent] = []
        # Close out the last assistant message if there was one
        if self._last_message_id is not None:
            events.append(
                MessageDoneEvent(type="message.done", message_id=self._last_message_id)
            )
        # Cost / usage (persisted; UI hides it from the client)
        cost_usd = float(raw.get("total_cost_usd") or 0)
        usage = raw.get("usage") or {}
        if cost_usd or usage:
            events.append(
                CostDeltaEvent(
                    type="cost.delta",
                    usd=cost_usd,
                    tokens_in=int(usage.get("input_tokens", 0) or 0),
                    tokens_out=int(usage.get("output_tokens", 0) or 0),
                )
            )
        events.append(DoneEvent(type="done", session_id=self._session_id))
        return events
