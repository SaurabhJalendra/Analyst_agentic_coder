"""Tests for the async stream-json line parser."""
from __future__ import annotations

from pathlib import Path

import pytest

from app.event_schema import (
    DoneEvent,
    ErrorEvent,
    MessageDeltaEvent,
    PlanStartEvent,
    SubagentSpawnEvent,
)
from app.stream_parser import ParseStats, StreamParser


async def _events_from_fixture(fixture_path: Path) -> tuple[list, ParseStats]:
    """Drive the parser with a fixture file's contents."""
    parser = StreamParser()
    events = []
    async for ev in parser.parse_lines(_lines(fixture_path)):
        events.append(ev)
    return events, parser.stats


async def _lines(path: Path):
    for line in path.read_text(encoding="utf-8").splitlines():
        yield line


@pytest.mark.asyncio
async def test_simple_fixture_yields_4_events(fixtures_dir: Path):
    events, stats = await _events_from_fixture(fixtures_dir / "stream_json" / "simple.jsonl")
    assert len(events) == 4
    assert isinstance(events[0], MessageDeltaEvent)
    assert isinstance(events[3], DoneEvent)
    assert stats.parsed == 4
    assert stats.malformed == 0


@pytest.mark.asyncio
async def test_multi_step_fixture_yields_plan_events(fixtures_dir: Path):
    events, stats = await _events_from_fixture(fixtures_dir / "stream_json" / "multi_step.jsonl")
    plan_starts = [e for e in events if isinstance(e, PlanStartEvent)]
    assert len(plan_starts) == 1
    assert len(plan_starts[0].steps) == 3
    assert stats.parsed == 14


@pytest.mark.asyncio
async def test_subagent_fixture(fixtures_dir: Path):
    events, _ = await _events_from_fixture(fixtures_dir / "stream_json" / "subagent.jsonl")
    spawns = [e for e in events if isinstance(e, SubagentSpawnEvent)]
    assert len(spawns) == 1
    assert spawns[0].kind == "researcher"


@pytest.mark.asyncio
async def test_error_fixture_no_terminating_done(fixtures_dir: Path):
    events, stats = await _events_from_fixture(fixtures_dir / "stream_json" / "error.jsonl")
    errors = [e for e in events if isinstance(e, ErrorEvent)]
    assert len(errors) == 1
    assert errors[0].code == "AUTH_REQUIRED"
    assert stats.parsed == 4


@pytest.mark.asyncio
async def test_malformed_lines_counted_not_raised():
    """Garbage input should be counted in stats.malformed; not crash the parser."""
    parser = StreamParser()
    events = []
    async def lines():
        yield 'not json at all'
        yield '{"type":"unknown.thing"}'
        yield ''
        yield '{"type":"done","session_id":"s"}'
    async for ev in parser.parse_lines(lines()):
        events.append(ev)
    assert len(events) == 1  # only the valid done event
    assert parser.stats.malformed == 2  # garbage + unknown type
    assert parser.stats.parsed == 1


@pytest.mark.asyncio
async def test_empty_input_yields_nothing():
    parser = StreamParser()
    events = []
    async def lines():
        if False:
            yield  # type: ignore[unreachable]
    async for ev in parser.parse_lines(lines()):
        events.append(ev)
    assert events == []
    assert parser.stats.parsed == 0
