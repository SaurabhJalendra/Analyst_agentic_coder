"""Tests for the typed SSE event schema."""
from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError

from app.event_schema import (
    AnyEvent,  # noqa: F401
    ArtifactCreateEvent,  # noqa: F401
    DoneEvent,
    ErrorEvent,
    MessageDeltaEvent,
    MessageDoneEvent,  # noqa: F401
    PlanStartEvent,
    PlanStepDoneEvent,  # noqa: F401
    PlanStepStartEvent,  # noqa: F401
    SourceAccessEvent,  # noqa: F401
    SubagentDoneEvent,  # noqa: F401
    SubagentSpawnEvent,  # noqa: F401
    ThinkingBlockEvent,  # noqa: F401
    ToolDoneEvent,  # noqa: F401
    ToolStartEvent,
    parse_event,
)


def test_plan_start_event_serialization():
    ev = PlanStartEvent(
        type="plan.start",
        plan_id="p1",
        steps=[{"id": "s1", "description": "load data"}],
    )
    blob = ev.model_dump_json()
    parsed = PlanStartEvent.model_validate_json(blob)
    assert parsed == ev


def test_tool_start_args_redacted_required():
    """Tool args must always go through args_redacted (never raw args)."""
    with pytest.raises(ValidationError):
        ToolStartEvent(type="tool.start", call_id="c1", agent_id="main", tool="Read")  # type: ignore[call-arg]


def test_error_event_recoverable_field():
    ev = ErrorEvent(type="error", code="TIMEOUT", message="cli hung", recoverable=True)
    assert ev.recoverable is True


def test_parse_event_dispatches_by_type():
    raw = '{"type":"plan.start","plan_id":"p1","steps":[{"id":"s1","description":"x"}]}'
    ev = parse_event(raw)
    assert isinstance(ev, PlanStartEvent)


def test_parse_event_unknown_type_raises():
    raw = '{"type":"plan.unicorn","data":1}'
    with pytest.raises(ValidationError):
        parse_event(raw)


@given(st.text(min_size=1, max_size=20), st.integers(min_value=0, max_value=10**6))
def test_message_delta_round_trip(message_id: str, length: int):
    """Property: any valid MessageDelta serializes and deserializes identically."""
    ev = MessageDeltaEvent(type="message.delta", message_id=message_id, append_text="x" * length)
    blob = ev.model_dump_json()
    parsed = MessageDeltaEvent.model_validate_json(blob)
    assert parsed == ev


def test_any_event_discriminated_union():
    """AnyEvent is a discriminated union; parsing chooses the right concrete class."""
    raw_plan = '{"type":"plan.start","plan_id":"p","steps":[]}'
    raw_done = '{"type":"done","session_id":"s"}'
    plan = parse_event(raw_plan)
    done = parse_event(raw_done)
    assert isinstance(plan, PlanStartEvent)
    assert isinstance(done, DoneEvent)
