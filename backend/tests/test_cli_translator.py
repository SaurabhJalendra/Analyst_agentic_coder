"""Tests for the real-claude-CLI → typed-event translator.

This is the most fragile file in the streaming pipeline — it sits between the
unstable, undocumented `claude --output-format stream-json` schema and our
typed event surface. Cover it thoroughly: real-CLI fixtures, malformed input,
typed-fixture fallback, and a Hypothesis fuzz that asserts the translator
never raises on arbitrary JSON.
"""
from __future__ import annotations

import json

import pytest
from hypothesis import HealthCheck, given, settings, strategies as st

from app.cli_translator import CLITranslator
from app.event_schema import (
    CostDeltaEvent,
    DoneEvent,
    MessageDeltaEvent,
    MessageDoneEvent,
    PlanStartEvent,
    ToolDoneEvent,
    ToolStartEvent,
)


# --- Real-CLI sample lines (captured from `claude -p ... --output-format stream-json --verbose`) ---

ASSISTANT_TEXT = json.dumps(
    {
        "type": "assistant",
        "message": {
            "id": "msg_01ABC",
            "role": "assistant",
            "content": [{"type": "text", "text": "2+2 equals 4."}],
            "usage": {"input_tokens": 6, "output_tokens": 14},
        },
    }
)

ASSISTANT_TOOL_USE = json.dumps(
    {
        "type": "assistant",
        "message": {
            "id": "msg_02XYZ",
            "role": "assistant",
            "content": [
                {
                    "type": "tool_use",
                    "id": "toolu_01",
                    "name": "Read",
                    "input": {"file_path": "x.py"},
                }
            ],
        },
    }
)

USER_TOOL_RESULT = json.dumps(
    {
        "type": "user",
        "message": {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": "toolu_01",
                    "is_error": False,
                    "content": [{"type": "text", "text": "42 lines of code"}],
                }
            ],
        },
    }
)

RESULT_SUCCESS = json.dumps(
    {
        "type": "result",
        "subtype": "success",
        "is_error": False,
        "result": "2+2 equals 4.",
        "duration_ms": 5601,
        "total_cost_usd": 0.2555,
        "usage": {"input_tokens": 6, "output_tokens": 14},
    }
)

SYSTEM_INIT = json.dumps(
    {"type": "system", "subtype": "init", "model": "claude-opus-4-7"}
)

SYSTEM_HOOK = json.dumps(
    {"type": "system", "subtype": "hook_started", "hook_id": "x"}
)

RATE_LIMIT = json.dumps(
    {"type": "rate_limit_event", "rate_limit_info": {"status": "allowed"}}
)


# --- Tests ---


def test_assistant_text_emits_message_delta():
    t = CLITranslator(session_id="s1")
    events = t.translate(ASSISTANT_TEXT)
    assert len(events) == 1
    ev = events[0]
    assert isinstance(ev, MessageDeltaEvent)
    assert ev.message_id == "msg_01ABC"
    assert ev.append_text == "2+2 equals 4."


def test_assistant_tool_use_emits_tool_start():
    t = CLITranslator(session_id="s1")
    events = t.translate(ASSISTANT_TOOL_USE)
    assert len(events) == 1
    ev = events[0]
    assert isinstance(ev, ToolStartEvent)
    assert ev.tool == "Read"
    assert ev.call_id == "toolu_01"
    assert ev.args_redacted == {"file_path": "x.py"}


def test_user_tool_result_emits_tool_done():
    t = CLITranslator(session_id="s1")
    events = t.translate(USER_TOOL_RESULT)
    assert len(events) == 1
    ev = events[0]
    assert isinstance(ev, ToolDoneEvent)
    assert ev.call_id == "toolu_01"
    assert ev.ok is True
    assert ev.result_preview is not None
    assert "42 lines of code" in ev.result_preview


def test_user_tool_result_string_content():
    """Tool result `content` can be a plain string instead of a list of {type:'text',...}."""
    payload = json.dumps(
        {
            "type": "user",
            "message": {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": "t",
                        "content": "raw string output",
                    }
                ],
            },
        }
    )
    events = CLITranslator(session_id="s1").translate(payload)
    assert len(events) == 1
    assert isinstance(events[0], ToolDoneEvent)
    assert events[0].result_preview == "raw string output"


def test_user_tool_result_error_flag():
    payload = json.dumps(
        {
            "type": "user",
            "message": {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": "t",
                        "is_error": True,
                        "content": "boom",
                    }
                ],
            },
        }
    )
    events = CLITranslator(session_id="s1").translate(payload)
    assert isinstance(events[0], ToolDoneEvent)
    assert events[0].ok is False


def test_result_emits_done_plus_cost_plus_message_done():
    t = CLITranslator(session_id="s1")
    # Need a prior assistant event so message_done targets the right id
    t.translate(ASSISTANT_TEXT)
    events = t.translate(RESULT_SUCCESS)
    types = [type(e).__name__ for e in events]
    assert "MessageDoneEvent" in types
    assert "CostDeltaEvent" in types
    assert "DoneEvent" in types
    cost = next(e for e in events if isinstance(e, CostDeltaEvent))
    assert cost.usd == pytest.approx(0.2555)
    assert cost.tokens_in == 6
    msg_done = next(e for e in events if isinstance(e, MessageDoneEvent))
    assert msg_done.message_id == "msg_01ABC"
    done = next(e for e in events if isinstance(e, DoneEvent))
    assert done.session_id == "s1"


def test_result_without_prior_assistant_skips_message_done():
    t = CLITranslator(session_id="s1")
    events = t.translate(RESULT_SUCCESS)
    types = [type(e).__name__ for e in events]
    assert "MessageDoneEvent" not in types
    assert "DoneEvent" in types


def test_system_events_ignored():
    t = CLITranslator(session_id="s1")
    assert t.translate(SYSTEM_INIT) == []
    assert t.translate(SYSTEM_HOOK) == []


def test_rate_limit_ignored():
    t = CLITranslator(session_id="s1").translate(RATE_LIMIT)
    assert t == []


def test_empty_line_ignored():
    assert CLITranslator(session_id="s1").translate("") == []
    assert CLITranslator(session_id="s1").translate("   ") == []


def test_malformed_json_ignored():
    assert CLITranslator(session_id="s1").translate("not json {") == []
    assert CLITranslator(session_id="s1").translate("123") == []  # not a dict
    assert CLITranslator(session_id="s1").translate("[]") == []  # array, not object


def test_unknown_native_type_falls_back_to_typed_parser():
    """Unknown CLI types try our typed parser. Mock CLI fixtures emit our types."""
    raw = json.dumps({"type": "message.delta", "message_id": "m1", "append_text": "hi"})
    events = CLITranslator(session_id="s1").translate(raw)
    assert len(events) == 1
    assert isinstance(events[0], MessageDeltaEvent)


def test_unknown_type_with_no_typed_match_returns_empty():
    raw = json.dumps({"type": "completely.unknown.event", "data": 1})
    assert CLITranslator(session_id="s1").translate(raw) == []


def test_assistant_with_empty_content_returns_empty():
    payload = json.dumps({"type": "assistant", "message": {"id": "m", "content": []}})
    assert CLITranslator(session_id="s1").translate(payload) == []


def test_assistant_with_missing_message_returns_empty():
    payload = json.dumps({"type": "assistant"})
    assert CLITranslator(session_id="s1").translate(payload) == []


def test_assistant_text_with_empty_string_skipped():
    """Empty text deltas are skipped so the chat doesn't get spammed."""
    payload = json.dumps(
        {
            "type": "assistant",
            "message": {"id": "m1", "content": [{"type": "text", "text": ""}]},
        }
    )
    assert CLITranslator(session_id="s1").translate(payload) == []


def test_typed_parser_fallback_on_typed_done_event():
    raw = json.dumps({"type": "done", "session_id": "s1"})
    events = CLITranslator(session_id="s1").translate(raw)
    assert len(events) == 1
    assert isinstance(events[0], DoneEvent)


def test_message_id_persists_across_assistant_chunks():
    """Multiple assistant chunks for the same message should share the id."""
    t = CLITranslator(session_id="s1")
    chunk1 = json.dumps(
        {"type": "assistant", "message": {"id": "msg_X", "content": [{"type": "text", "text": "Hello"}]}}
    )
    chunk2 = json.dumps(
        {"type": "assistant", "message": {"id": "msg_X", "content": [{"type": "text", "text": ", world"}]}}
    )
    e1 = t.translate(chunk1)
    e2 = t.translate(chunk2)
    assert e1[0].message_id == e2[0].message_id == "msg_X"  # type: ignore[union-attr]


def test_plan_start_via_typed_fallback():
    """Mock fixtures emit plan.start directly; translator must handle it."""
    raw = json.dumps(
        {"type": "plan.start", "plan_id": "p", "steps": [{"id": "s", "description": "x"}]}
    )
    events = CLITranslator(session_id="s1").translate(raw)
    assert len(events) == 1
    assert isinstance(events[0], PlanStartEvent)


# --- Hypothesis fuzz: translator must NEVER raise on any UTF-8 input ---


@settings(max_examples=300, suppress_health_check=[HealthCheck.too_slow])
@given(st.text(max_size=2000))
def test_translator_never_raises_on_arbitrary_text(line: str):
    """Property: any string input is either silently ignored or yields valid events.

    This protects against malformed CLI output (truncation, garbage, partial UTF-8)
    causing the streaming pipeline to crash.
    """
    events = CLITranslator(session_id="s").translate(line)
    # Result is always a list (possibly empty). Each item is a typed event.
    assert isinstance(events, list)
    for ev in events:
        # Every event has a typed `type` literal — Pydantic guarantees this.
        assert hasattr(ev, "type")


@settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
@given(
    st.recursive(
        st.none() | st.booleans() | st.integers() | st.text(max_size=50),
        lambda children: st.lists(children, max_size=4)
        | st.dictionaries(st.text(max_size=20), children, max_size=4),
        max_leaves=20,
    )
)
def test_translator_never_raises_on_arbitrary_json(payload: object):
    """Property: any JSON value (object, array, scalar) won't crash the translator."""
    line = json.dumps(payload)
    events = CLITranslator(session_id="s").translate(line)
    assert isinstance(events, list)
