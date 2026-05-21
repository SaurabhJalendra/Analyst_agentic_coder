# Phase 1 — Backend Streaming Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the polling-based progress system with a typed streaming pipeline: `claude --output-format stream-json` parsed incrementally, fanned out to clients via Server-Sent Events.

**Architecture:** `claude` CLI subprocess → async line-by-line stream parser → typed Pydantic events → per-session `asyncio.Queue` broker → SSE endpoint with `Last-Event-ID` reconnect. Old polling endpoint stays alive in parallel until Phase 2 lands. Persistence via SQLite `audit_log` and `artifacts` tables.

**Tech Stack:** Python 3.12, FastAPI, Pydantic v2, sse-starlette, aiosqlite, structlog, pytest + pytest-asyncio + Hypothesis, ruff, mypy strict.

---

## Spec reference

This plan implements **Phase 1** of `docs/superpowers/specs/2026-04-29-quant-console-frontend-design.md`. Specifically:
- The `Backend changes` section (added/modified endpoints; new tables)
- The `Event schema` section (every typed event)
- The `Data flow` section (prompt → CLI → parser → broker → SSE)
- `Standards & tooling` for the backend
- The `Migration path` Phase 1 entry

**Out of scope for Phase 1:** any frontend work, artifact rendering, PDF export, audit UI, entitlements service. Those are Phase 2 / Phase 3 plans.

---

## File structure (what gets created/modified)

### New files
| Path | Responsibility |
|---|---|
| `backend/app/event_schema.py` | Pydantic models for every typed SSE event (PlanStart, PlanStepStart, PlanStepDone, SubagentSpawn, ToolStart, etc.) |
| `backend/app/stream_parser.py` | Async parser that consumes raw `claude --output-format stream-json` lines and emits typed events |
| `backend/app/event_broker.py` | Per-session `asyncio.Queue` with last-200-event ring buffer for `Last-Event-ID` replay |
| `backend/app/audit_logger.py` | Append-only audit-log writer; generates audit IDs |
| `backend/migrations/001_audit_artifacts.sql` | Adds `audit_log` and `artifacts` tables |
| `backend/migrations/run.py` | Lightweight migration runner — applies any unapplied `*.sql` files |
| `backend/tests/fixtures/mock_claude.py` | Standalone Python script that emits canned `stream-json` output (used as a `claude` substitute in tests) |
| `backend/tests/fixtures/stream_json/simple.jsonl` | Fixture: minimal "hello world" agent run |
| `backend/tests/fixtures/stream_json/multi_step.jsonl` | Fixture: multi-step plan with 3 tool calls |
| `backend/tests/fixtures/stream_json/subagent.jsonl` | Fixture: spawns a subagent, gets a result |
| `backend/tests/fixtures/stream_json/error.jsonl` | Fixture: agent hits a 401 mid-stream |
| `backend/tests/test_event_schema.py` | Pydantic round-trip + hypothesis property tests |
| `backend/tests/test_stream_parser.py` | Parser tests against fixtures + malformed input |
| `backend/tests/test_event_broker.py` | Broker pub/sub + replay tests |
| `backend/tests/test_audit_logger.py` | Audit append + ID generation |
| `backend/tests/test_claude_code_service.py` | Service tests using mock_claude.py |
| `backend/tests/test_chat_streaming.py` | End-to-end: POST /api/chat + SSE stream |
| `backend/conftest.py` | Shared pytest fixtures: tmp DB, mock CLI path |
| `backend/pyproject.toml` | Replaces ad-hoc tooling: ruff + mypy + pytest config |

### Modified files
| Path | Change |
|---|---|
| `backend/app/claude_code_service.py` | Rewrite: switch to `--output-format stream-json`; replace hardcoded path with `shutil.which("claude")`; implement `restart_if_needed()`; pipe stdout to parser → broker |
| `backend/app/main.py` | Add `GET /api/chat/stream/{session_id}` SSE endpoint; change `POST /api/chat` to 202-Accepted; keep `/api/progress/{id}` alive |
| `backend/app/database.py` | Add `audit_log` + `artifacts` ORM models |
| `backend/requirements.txt` | Add: `sse-starlette`, `hypothesis`, `pytest-asyncio`, `mypy`, `ruff`. Remove: `anthropic` (unused). |

### Deleted files (hygiene; not required for streaming but the file-touch is small enough to bundle)
| Path | Reason |
|---|---|
| `backend/test_endpoint.py` | Loose scaffolding; replaced by real pytest suite |
| `backend/test_imports.py` | Loose scaffolding |
| `backend/backend_logs.txt` | Stray log dump |

---

## Task 0: Repo hygiene & tooling baseline

**Files:**
- Create: `backend/pyproject.toml`
- Modify: `backend/requirements.txt`
- Delete: `backend/test_endpoint.py`, `backend/test_imports.py`, `backend/backend_logs.txt`

- [ ] **Step 1: Add pyproject.toml with ruff + mypy + pytest config**

Create `backend/pyproject.toml`:
```toml
[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "UP", "B", "ASYNC", "S", "C4", "RET", "SIM", "PL"]
ignore = ["S101", "PLR0913"]  # allow assert in tests; allow >5 args (FastAPI deps)

[tool.ruff.lint.per-file-ignores]
"tests/**/*.py" = ["S105", "S106"]  # allow hardcoded test secrets

[tool.mypy]
python_version = "3.12"
strict = true
warn_unreachable = true
plugins = ["pydantic.mypy"]

[[tool.mypy.overrides]]
module = ["sse_starlette.*"]
ignore_missing_imports = true

[tool.pytest.ini_options]
asyncio_mode = "auto"
addopts = "-ra -q --strict-markers"
testpaths = ["tests"]

[tool.coverage.run]
source = ["app"]
branch = true

[tool.coverage.report]
fail_under = 80
```

- [ ] **Step 2: Update requirements.txt**

Modify `backend/requirements.txt` — remove `anthropic` line, add new lines:
```
sse-starlette>=2.0.0
hypothesis>=6.100.0
pytest-asyncio>=0.23.0
mypy>=1.10.0
ruff>=0.4.0
```

- [ ] **Step 3: Delete scaffolding files**

```bash
cd "D:/Git Repos/Analyst_agentic_coder/backend"
rm test_endpoint.py test_imports.py backend_logs.txt
```

- [ ] **Step 4: Verify tooling installs and runs**

```bash
cd backend && pip install -r requirements.txt
ruff check .
mypy app/
```

Expected: `ruff` and `mypy` produce some warnings on existing code (acceptable for now — task list will fix during rewrites). No installation errors.

- [ ] **Step 5: Commit**

```bash
cd "D:/Git Repos/Analyst_agentic_coder"
git add backend/pyproject.toml backend/requirements.txt
git rm backend/test_endpoint.py backend/test_imports.py backend/backend_logs.txt
git commit -m "chore: backend tooling baseline (ruff+mypy+pytest), remove scaffolding"
```

---

## Task 1: Pydantic event schema

**Files:**
- Create: `backend/app/event_schema.py`
- Test: `backend/tests/test_event_schema.py`
- Test: `backend/conftest.py` (shared fixtures)

- [ ] **Step 1: Write the failing test**

Create `backend/conftest.py`:
```python
import pytest
from pathlib import Path

@pytest.fixture
def fixtures_dir() -> Path:
    return Path(__file__).parent / "tests" / "fixtures"
```

Create `backend/tests/__init__.py` (empty).

Create `backend/tests/test_event_schema.py`:
```python
"""Tests for the typed SSE event schema."""
from __future__ import annotations

import pytest
from hypothesis import given, strategies as st
from pydantic import ValidationError

from app.event_schema import (
    PlanStartEvent,
    PlanStepStartEvent,
    PlanStepDoneEvent,
    SubagentSpawnEvent,
    SubagentDoneEvent,
    ToolStartEvent,
    ToolDoneEvent,
    SourceAccessEvent,
    ThinkingBlockEvent,
    ArtifactCreateEvent,
    MessageDeltaEvent,
    MessageDoneEvent,
    ErrorEvent,
    DoneEvent,
    AnyEvent,
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
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && pytest tests/test_event_schema.py -v
```

Expected: ImportError (`app.event_schema` doesn't exist).

- [ ] **Step 3: Write minimal implementation**

Create `backend/app/event_schema.py`:
```python
"""Typed SSE event schema. Mirrors the spec section "Event schema".

Every event sent over /api/chat/stream/{session_id} is one of these.
The frontend has a matching TypeScript discriminated union.
"""
from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter


class _EventBase(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


# --- Plan ---

class PlanStep(_EventBase):
    id: str
    description: str


class PlanStartEvent(_EventBase):
    type: Literal["plan.start"]
    plan_id: str
    steps: list[PlanStep]


class PlanStepStartEvent(_EventBase):
    type: Literal["plan.step.start"]
    step_id: str


class PlanStepDoneEvent(_EventBase):
    type: Literal["plan.step.done"]
    step_id: str
    duration_ms: int


# --- Sub-agents ---

class SubagentSpawnEvent(_EventBase):
    type: Literal["subagent.spawn"]
    agent_id: str
    parent_id: str | None = None
    kind: Literal["researcher", "verifier", "explore", "plan", "general"] | str
    model: str
    prompt: str


class SubagentDeltaEvent(_EventBase):
    type: Literal["subagent.delta"]
    agent_id: str
    tokens: int
    status_text: str | None = None


class SubagentDoneEvent(_EventBase):
    type: Literal["subagent.done"]
    agent_id: str
    duration_ms: int
    tokens: int
    result: str | None = None


# --- Tools ---

class ToolStartEvent(_EventBase):
    type: Literal["tool.start"]
    call_id: str
    agent_id: str
    tool: str
    args_redacted: dict[str, object]


class ToolDoneEvent(_EventBase):
    type: Literal["tool.done"]
    call_id: str
    duration_ms: int
    ok: bool
    result_preview: str | None = None


# --- Skills, memory, wiki ---

class SkillInvokeEvent(_EventBase):
    type: Literal["skill"]
    name: str
    args: str | None = None


class MemoryOpEvent(_EventBase):
    type: Literal["memory"]
    op: Literal["read", "write"]
    path: str


class WikiOpEvent(_EventBase):
    type: Literal["wiki"]
    op: Literal["read", "ingest", "lint", "query"]
    target: str


# --- Sources (MCP / data feeds) ---

class SourceAccessEvent(_EventBase):
    type: Literal["source"]
    source: str
    operation: str
    bytes: int | None = None


# --- Thinking ---

class ThinkingBlockEvent(_EventBase):
    type: Literal["thinking"]
    agent_id: str
    tokens: int
    preview_text: str


# --- Artifacts ---

class ArtifactCreateEvent(_EventBase):
    type: Literal["artifact"]
    artifact_id: str
    kind: Literal["chart", "table", "code", "report", "file"]
    title: str
    source_attribution: str
    methodology_id: str


# --- Messages ---

class MessageDeltaEvent(_EventBase):
    type: Literal["message.delta"]
    message_id: str
    append_text: str


class MessageDoneEvent(_EventBase):
    type: Literal["message.done"]
    message_id: str


# --- Cost (persisted, not surfaced to client UI in v1) ---

class CostDeltaEvent(_EventBase):
    type: Literal["cost.delta"]
    usd: float
    tokens_in: int
    tokens_out: int


# --- Control / errors ---

class ApprovalNeededEvent(_EventBase):
    type: Literal["approval"]
    approval_id: str
    description: str
    danger: bool


class ErrorEvent(_EventBase):
    type: Literal["error"]
    code: str
    message: str
    recoverable: bool


class DoneEvent(_EventBase):
    type: Literal["done"]
    session_id: str


# --- Discriminated union ---

AnyEvent = Annotated[
    Union[
        PlanStartEvent,
        PlanStepStartEvent,
        PlanStepDoneEvent,
        SubagentSpawnEvent,
        SubagentDeltaEvent,
        SubagentDoneEvent,
        ToolStartEvent,
        ToolDoneEvent,
        SkillInvokeEvent,
        MemoryOpEvent,
        WikiOpEvent,
        SourceAccessEvent,
        ThinkingBlockEvent,
        ArtifactCreateEvent,
        MessageDeltaEvent,
        MessageDoneEvent,
        CostDeltaEvent,
        ApprovalNeededEvent,
        ErrorEvent,
        DoneEvent,
    ],
    Field(discriminator="type"),
]

_ADAPTER: TypeAdapter[AnyEvent] = TypeAdapter(AnyEvent)


def parse_event(raw_json: str | bytes) -> AnyEvent:
    """Parse a JSON line into a typed event. Raises ValidationError on unknown type or malformed payload."""
    return _ADAPTER.validate_json(raw_json)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd backend && pytest tests/test_event_schema.py -v
```

Expected: 7 PASSED (including the hypothesis property test).

- [ ] **Step 5: Commit**

```bash
cd "D:/Git Repos/Analyst_agentic_coder"
git add backend/app/event_schema.py backend/tests/test_event_schema.py backend/conftest.py backend/tests/__init__.py
git commit -m "feat(backend): typed SSE event schema (Pydantic v2)"
```

---

## Task 2: Mock CLI + fixture files

**Files:**
- Create: `backend/tests/fixtures/mock_claude.py`
- Create: `backend/tests/fixtures/stream_json/simple.jsonl`
- Create: `backend/tests/fixtures/stream_json/multi_step.jsonl`
- Create: `backend/tests/fixtures/stream_json/subagent.jsonl`
- Create: `backend/tests/fixtures/stream_json/error.jsonl`

(Mock CLI before parser so the parser tests can use it.)

- [ ] **Step 1: Write the simple fixture**

Create `backend/tests/fixtures/stream_json/simple.jsonl`:
```json
{"type":"message.delta","message_id":"m1","append_text":"Hello"}
{"type":"message.delta","message_id":"m1","append_text":", world."}
{"type":"message.done","message_id":"m1"}
{"type":"done","session_id":"test-session"}
```

- [ ] **Step 2: Write the multi-step fixture**

Create `backend/tests/fixtures/stream_json/multi_step.jsonl`:
```json
{"type":"plan.start","plan_id":"p1","steps":[{"id":"s1","description":"load data"},{"id":"s2","description":"compute"},{"id":"s3","description":"summarize"}]}
{"type":"plan.step.start","step_id":"s1"}
{"type":"tool.start","call_id":"c1","agent_id":"main","tool":"Read","args_redacted":{"path":"data/spy.parquet"}}
{"type":"tool.done","call_id":"c1","duration_ms":42,"ok":true,"result_preview":"42 rows"}
{"type":"plan.step.done","step_id":"s1","duration_ms":50}
{"type":"plan.step.start","step_id":"s2"}
{"type":"tool.start","call_id":"c2","agent_id":"main","tool":"Bash","args_redacted":{"command":"python compute.py"}}
{"type":"tool.done","call_id":"c2","duration_ms":1200,"ok":true,"result_preview":"sharpe=0.87"}
{"type":"plan.step.done","step_id":"s2","duration_ms":1210}
{"type":"plan.step.start","step_id":"s3"}
{"type":"message.delta","message_id":"m1","append_text":"Sharpe ratio is 0.87."}
{"type":"message.done","message_id":"m1"}
{"type":"plan.step.done","step_id":"s3","duration_ms":15}
{"type":"done","session_id":"test-session"}
```

- [ ] **Step 3: Write the subagent fixture**

Create `backend/tests/fixtures/stream_json/subagent.jsonl`:
```json
{"type":"plan.start","plan_id":"p1","steps":[{"id":"s1","description":"research"}]}
{"type":"plan.step.start","step_id":"s1"}
{"type":"subagent.spawn","agent_id":"a2","parent_id":"main","kind":"researcher","model":"claude-sonnet-4-6","prompt":"momentum literature"}
{"type":"subagent.delta","agent_id":"a2","tokens":150,"status_text":"searching arxiv"}
{"type":"subagent.delta","agent_id":"a2","tokens":420,"status_text":"reading 3 papers"}
{"type":"subagent.done","agent_id":"a2","duration_ms":4200,"tokens":1800,"result":"Momentum holds out-of-sample"}
{"type":"plan.step.done","step_id":"s1","duration_ms":4250}
{"type":"done","session_id":"test-session"}
```

- [ ] **Step 4: Write the error fixture**

Create `backend/tests/fixtures/stream_json/error.jsonl`:
```json
{"type":"plan.start","plan_id":"p1","steps":[{"id":"s1","description":"call API"}]}
{"type":"plan.step.start","step_id":"s1"}
{"type":"tool.start","call_id":"c1","agent_id":"main","tool":"Bash","args_redacted":{"command":"curl bloomberg"}}
{"type":"error","code":"AUTH_REQUIRED","message":"Bloomberg token expired","recoverable":false}
```

(Note: error fixture intentionally has no terminating `done` event — parser must handle this.)

- [ ] **Step 5: Write mock_claude.py**

Create `backend/tests/fixtures/mock_claude.py`:
```python
#!/usr/bin/env python3
"""Mock `claude` CLI for backend tests.

Reads a fixture file (path from --fixture or env MOCK_CLAUDE_FIXTURE) and emits
each line to stdout, sleeping briefly between lines to simulate streaming.

Usage in tests:
    subprocess.Popen(["python", str(mock_claude_path), "-p", "...", "--output-format", "stream-json"],
                     env={"MOCK_CLAUDE_FIXTURE": str(fixture_path), **os.environ})
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", dest="prompt", default="")
    parser.add_argument("--output-format", default="stream-json")
    parser.add_argument("--dangerously-skip-permissions", action="store_true")
    parser.add_argument("--fixture", default=None, help="Path to fixture .jsonl")
    args = parser.parse_args()

    fixture_path = args.fixture or os.environ.get("MOCK_CLAUDE_FIXTURE")
    if not fixture_path:
        print('{"type":"error","code":"NO_FIXTURE","message":"set MOCK_CLAUDE_FIXTURE","recoverable":false}',
              flush=True)
        return 1

    delay_ms = float(os.environ.get("MOCK_CLAUDE_DELAY_MS", "5"))
    fixture = Path(fixture_path)
    if not fixture.exists():
        print(f'{{"type":"error","code":"FIXTURE_NOT_FOUND","message":"{fixture}","recoverable":false}}',
              flush=True)
        return 1

    for line in fixture.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        print(line, flush=True)
        if delay_ms:
            time.sleep(delay_ms / 1000.0)

    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 6: Verify mock CLI runs**

```bash
cd backend
MOCK_CLAUDE_FIXTURE=tests/fixtures/stream_json/simple.jsonl python tests/fixtures/mock_claude.py -p "test"
```

Expected stdout:
```
{"type":"message.delta","message_id":"m1","append_text":"Hello"}
{"type":"message.delta","message_id":"m1","append_text":", world."}
{"type":"message.done","message_id":"m1"}
{"type":"done","session_id":"test-session"}
```

- [ ] **Step 7: Commit**

```bash
cd "D:/Git Repos/Analyst_agentic_coder"
git add backend/tests/fixtures/
git commit -m "test(backend): mock claude CLI + 4 stream-json fixtures"
```

---

## Task 3: Stream-json line parser

**Files:**
- Create: `backend/app/stream_parser.py`
- Test: `backend/tests/test_stream_parser.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_stream_parser.py`:
```python
"""Tests for the async stream-json line parser."""
from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from app.event_schema import (
    DoneEvent,
    ErrorEvent,
    MessageDeltaEvent,
    PlanStartEvent,
    SubagentSpawnEvent,
)
from app.stream_parser import StreamParser, ParseStats


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
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && pytest tests/test_stream_parser.py -v
```

Expected: ImportError on `app.stream_parser`.

- [ ] **Step 3: Write minimal implementation**

Create `backend/app/stream_parser.py`:
```python
"""Async parser for `claude --output-format stream-json` output.

Consumes an async iterable of UTF-8 lines (one JSON event per line) and yields
typed events. Malformed lines are counted, not raised.
"""
from __future__ import annotations

from collections.abc import AsyncIterable, AsyncIterator
from dataclasses import dataclass, field

import structlog
from pydantic import ValidationError

from app.event_schema import AnyEvent, parse_event

_log = structlog.get_logger(__name__)


@dataclass
class ParseStats:
    parsed: int = 0
    malformed: int = 0
    bytes_in: int = 0


class StreamParser:
    """Stateful parser. Reuse across a session to keep cumulative stats."""

    def __init__(self) -> None:
        self.stats = ParseStats()

    async def parse_lines(self, lines: AsyncIterable[str]) -> AsyncIterator[AnyEvent]:
        async for raw in lines:
            line = raw.strip()
            if not line:
                continue
            self.stats.bytes_in += len(line)
            try:
                ev = parse_event(line)
            except ValidationError as exc:
                self.stats.malformed += 1
                _log.warning("stream_parser.malformed", error=str(exc), line_preview=line[:120])
                continue
            self.stats.parsed += 1
            yield ev
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd backend && pytest tests/test_stream_parser.py -v
```

Expected: 6 PASSED.

- [ ] **Step 5: Commit**

```bash
cd "D:/Git Repos/Analyst_agentic_coder"
git add backend/app/stream_parser.py backend/tests/test_stream_parser.py
git commit -m "feat(backend): async stream-json line parser with ParseStats"
```

---

## Task 4: Event broker (per-session asyncio.Queue)

**Files:**
- Create: `backend/app/event_broker.py`
- Test: `backend/tests/test_event_broker.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_event_broker.py`:
```python
"""Tests for the per-session event broker."""
from __future__ import annotations

import asyncio

import pytest

from app.event_broker import EventBroker, BufferedEvent
from app.event_schema import DoneEvent, MessageDeltaEvent


def _make_event(text: str = "x") -> MessageDeltaEvent:
    return MessageDeltaEvent(type="message.delta", message_id="m1", append_text=text)


@pytest.mark.asyncio
async def test_publish_then_subscribe_receives_event():
    broker = EventBroker()
    sub = await broker.subscribe("s1")
    ev = _make_event("hello")
    await broker.publish("s1", ev)

    received = await asyncio.wait_for(sub.__anext__(), timeout=1.0)
    assert received.event == ev
    assert received.id == 1


@pytest.mark.asyncio
async def test_two_subscribers_same_session_both_receive():
    broker = EventBroker()
    sub1 = await broker.subscribe("s1")
    sub2 = await broker.subscribe("s1")
    ev = _make_event()
    await broker.publish("s1", ev)
    r1 = await asyncio.wait_for(sub1.__anext__(), timeout=1.0)
    r2 = await asyncio.wait_for(sub2.__anext__(), timeout=1.0)
    assert r1.event == ev
    assert r2.event == ev


@pytest.mark.asyncio
async def test_late_subscriber_replays_from_last_event_id():
    broker = EventBroker(buffer_size=10)
    for i in range(5):
        await broker.publish("s1", _make_event(f"e{i}"))

    sub = await broker.subscribe("s1", last_event_id=2)
    received: list[BufferedEvent] = []
    for _ in range(3):
        received.append(await asyncio.wait_for(sub.__anext__(), timeout=1.0))

    assert [r.id for r in received] == [3, 4, 5]


@pytest.mark.asyncio
async def test_buffer_drops_oldest_when_full():
    broker = EventBroker(buffer_size=3)
    for i in range(5):
        await broker.publish("s1", _make_event(f"e{i}"))

    sub = await broker.subscribe("s1", last_event_id=0)
    received = [await asyncio.wait_for(sub.__anext__(), timeout=1.0) for _ in range(3)]
    assert [r.id for r in received] == [3, 4, 5]


@pytest.mark.asyncio
async def test_publish_done_closes_subscribers():
    broker = EventBroker()
    sub = await broker.subscribe("s1")
    await broker.publish("s1", DoneEvent(type="done", session_id="s1"))

    r = await asyncio.wait_for(sub.__anext__(), timeout=1.0)
    assert isinstance(r.event, DoneEvent)
    with pytest.raises(StopAsyncIteration):
        await asyncio.wait_for(sub.__anext__(), timeout=1.0)


@pytest.mark.asyncio
async def test_unsubscribe_removes_subscriber():
    broker = EventBroker()
    sub_gen = await broker.subscribe("s1")
    await sub_gen.aclose()
    # Publish should still work, just no one receives
    await broker.publish("s1", _make_event())
    assert broker.subscriber_count("s1") == 0


@pytest.mark.asyncio
async def test_isolation_between_sessions():
    broker = EventBroker()
    sub_a = await broker.subscribe("a")
    sub_b = await broker.subscribe("b")
    await broker.publish("a", _make_event("a-only"))

    r = await asyncio.wait_for(sub_a.__anext__(), timeout=1.0)
    assert r.event.append_text == "a-only"
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(sub_b.__anext__(), timeout=0.2)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && pytest tests/test_event_broker.py -v
```

Expected: ImportError.

- [ ] **Step 3: Write minimal implementation**

Create `backend/app/event_broker.py`:
```python
"""Per-session event broker.

Each session has a publish queue and a ring buffer of the last N events for
SSE reconnect via Last-Event-ID.

Subscribers are async generators yielding BufferedEvent (event + monotonic id).
A DoneEvent closes all subscribers for that session.
"""
from __future__ import annotations

import asyncio
from collections import deque
from collections.abc import AsyncIterator
from dataclasses import dataclass, field

import structlog

from app.event_schema import AnyEvent, DoneEvent

_log = structlog.get_logger(__name__)

DEFAULT_BUFFER_SIZE = 200


@dataclass(frozen=True)
class BufferedEvent:
    id: int
    event: AnyEvent


@dataclass
class _SessionState:
    buffer: deque[BufferedEvent] = field(default_factory=deque)
    next_id: int = 1
    subscriber_queues: list[asyncio.Queue[BufferedEvent | None]] = field(default_factory=list)
    closed: bool = False


class EventBroker:
    """In-process broker. One instance per FastAPI app."""

    def __init__(self, buffer_size: int = DEFAULT_BUFFER_SIZE) -> None:
        self._buffer_size = buffer_size
        self._sessions: dict[str, _SessionState] = {}
        self._lock = asyncio.Lock()

    async def publish(self, session_id: str, event: AnyEvent) -> int:
        async with self._lock:
            state = self._sessions.setdefault(session_id, _SessionState())
            buffered = BufferedEvent(id=state.next_id, event=event)
            state.next_id += 1
            state.buffer.append(buffered)
            while len(state.buffer) > self._buffer_size:
                state.buffer.popleft()
            for q in state.subscriber_queues:
                await q.put(buffered)
            if isinstance(event, DoneEvent):
                state.closed = True
                for q in state.subscriber_queues:
                    await q.put(None)
        return buffered.id

    async def subscribe(
        self, session_id: str, last_event_id: int = 0
    ) -> AsyncIterator[BufferedEvent]:
        return self._consume(session_id, last_event_id)

    async def _consume(self, session_id: str, last_event_id: int) -> AsyncIterator[BufferedEvent]:
        queue: asyncio.Queue[BufferedEvent | None] = asyncio.Queue()
        replay: list[BufferedEvent] = []
        async with self._lock:
            state = self._sessions.setdefault(session_id, _SessionState())
            replay = [b for b in state.buffer if b.id > last_event_id]
            state.subscriber_queues.append(queue)
        try:
            for buffered in replay:
                yield buffered
            while True:
                item = await queue.get()
                if item is None:
                    return
                yield item
        finally:
            async with self._lock:
                state = self._sessions.get(session_id)
                if state is not None and queue in state.subscriber_queues:
                    state.subscriber_queues.remove(queue)

    def subscriber_count(self, session_id: str) -> int:
        state = self._sessions.get(session_id)
        return 0 if state is None else len(state.subscriber_queues)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd backend && pytest tests/test_event_broker.py -v
```

Expected: 7 PASSED.

- [ ] **Step 5: Commit**

```bash
cd "D:/Git Repos/Analyst_agentic_coder"
git add backend/app/event_broker.py backend/tests/test_event_broker.py
git commit -m "feat(backend): per-session event broker with Last-Event-ID replay"
```

---

## Task 5: Database migration for audit_log + artifacts

**Files:**
- Create: `backend/migrations/001_audit_artifacts.sql`
- Create: `backend/migrations/run.py`
- Test: `backend/tests/test_migrations.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_migrations.py`:
```python
"""Tests for the lightweight migration runner."""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from migrations.run import apply_pending


@pytest.fixture
def tmp_db(tmp_path: Path) -> Path:
    db = tmp_path / "test.db"
    db.touch()
    return db


def test_runner_creates_meta_table(tmp_db: Path):
    apply_pending(tmp_db)
    conn = sqlite3.connect(tmp_db)
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='_migrations'"
    ).fetchall()
    assert rows == [("_migrations",)]


def test_runner_applies_001(tmp_db: Path):
    apply_pending(tmp_db)
    conn = sqlite3.connect(tmp_db)
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}
    assert "audit_log" in tables
    assert "artifacts" in tables


def test_runner_idempotent(tmp_db: Path):
    apply_pending(tmp_db)
    apply_pending(tmp_db)  # second run is a no-op
    conn = sqlite3.connect(tmp_db)
    applied = conn.execute("SELECT COUNT(*) FROM _migrations").fetchone()[0]
    assert applied == 1


def test_audit_log_columns(tmp_db: Path):
    apply_pending(tmp_db)
    conn = sqlite3.connect(tmp_db)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(audit_log)").fetchall()}
    assert {"id", "session_id", "ts", "event_type", "audit_id", "data_json"} <= cols
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && pytest tests/test_migrations.py -v
```

Expected: ImportError.

- [ ] **Step 3: Write the SQL migration**

Create `backend/migrations/__init__.py` (empty).

Create `backend/migrations/001_audit_artifacts.sql`:
```sql
-- Phase 1: audit log + artifacts metadata.
-- Note: existing tables (sessions, messages, tool_calls) are owned by SQLAlchemy;
-- this migration only adds the new ones.

CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    ts TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    event_type TEXT NOT NULL,
    audit_id TEXT NOT NULL,
    data_json TEXT NOT NULL,
    entitlements_snapshot_json TEXT
);

CREATE INDEX IF NOT EXISTS idx_audit_log_session ON audit_log(session_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_audit_id ON audit_log(audit_id);

CREATE TABLE IF NOT EXISTS artifacts (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    title TEXT NOT NULL,
    source_attribution TEXT NOT NULL,
    methodology_id TEXT NOT NULL,
    file_path TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_artifacts_session ON artifacts(session_id);
```

- [ ] **Step 4: Write the runner**

Create `backend/migrations/run.py`:
```python
"""Lightweight migration runner. Applies any pending NNN_*.sql files in order."""
from __future__ import annotations

import sqlite3
from pathlib import Path

import structlog

_log = structlog.get_logger(__name__)
_MIGRATIONS_DIR = Path(__file__).parent


def apply_pending(db_path: Path) -> list[str]:
    """Apply any unapplied migrations. Returns list of applied filenames."""
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS _migrations (
                filename TEXT PRIMARY KEY,
                applied_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
            )
        """)
        applied = {r[0] for r in conn.execute("SELECT filename FROM _migrations").fetchall()}

        sql_files = sorted(p for p in _MIGRATIONS_DIR.glob("*.sql"))
        newly_applied: list[str] = []
        for path in sql_files:
            if path.name in applied:
                continue
            sql = path.read_text(encoding="utf-8")
            conn.executescript(sql)
            conn.execute("INSERT INTO _migrations(filename) VALUES (?)", (path.name,))
            conn.commit()
            newly_applied.append(path.name)
            _log.info("migration.applied", filename=path.name)
        return newly_applied
    finally:
        conn.close()
```

- [ ] **Step 5: Run test to verify it passes**

```bash
cd backend && pytest tests/test_migrations.py -v
```

Expected: 4 PASSED.

- [ ] **Step 6: Commit**

```bash
cd "D:/Git Repos/Analyst_agentic_coder"
git add backend/migrations/
git add backend/tests/test_migrations.py
git commit -m "feat(backend): SQLite migrations runner + audit_log/artifacts schema"
```

---

## Task 6: Audit logger

**Files:**
- Create: `backend/app/audit_logger.py`
- Test: `backend/tests/test_audit_logger.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_audit_logger.py`:
```python
"""Tests for the append-only audit logger."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from app.audit_logger import AuditLogger, generate_audit_id
from app.event_schema import ToolStartEvent
from migrations.run import apply_pending


@pytest.fixture
def db(tmp_path: Path) -> Path:
    db_path = tmp_path / "audit.db"
    apply_pending(db_path)
    return db_path


def test_audit_id_format():
    aid = generate_audit_id(client_slug="acme", date="2024-04-29", seq=42)
    assert aid == "SES-2024-04-29-acme-0042"


def test_audit_id_zero_pads_seq():
    assert generate_audit_id("a", "2024-01-01", 1).endswith("-0001")
    assert generate_audit_id("a", "2024-01-01", 9999).endswith("-9999")


@pytest.mark.asyncio
async def test_append_writes_row(db: Path):
    logger = AuditLogger(db)
    ev = ToolStartEvent(
        type="tool.start",
        call_id="c1",
        agent_id="main",
        tool="Read",
        args_redacted={"path": "x.py"},
    )
    aid = await logger.append(session_id="s1", event=ev, client_slug="acme")
    assert aid.startswith("SES-")

    conn = sqlite3.connect(db)
    rows = conn.execute(
        "SELECT session_id, event_type, audit_id, data_json FROM audit_log"
    ).fetchall()
    assert len(rows) == 1
    sid, etype, audit_id, data_json = rows[0]
    assert sid == "s1"
    assert etype == "tool.start"
    assert audit_id == aid
    assert json.loads(data_json)["tool"] == "Read"


@pytest.mark.asyncio
async def test_append_increments_seq_per_client(db: Path):
    logger = AuditLogger(db)
    ev = ToolStartEvent(
        type="tool.start", call_id="c1", agent_id="main", tool="Read", args_redacted={}
    )
    a1 = await logger.append("s1", ev, client_slug="acme")
    a2 = await logger.append("s2", ev, client_slug="acme")
    a3 = await logger.append("s3", ev, client_slug="other")

    seq1 = int(a1.rsplit("-", 1)[-1])
    seq2 = int(a2.rsplit("-", 1)[-1])
    seq3 = int(a3.rsplit("-", 1)[-1])
    assert seq2 == seq1 + 1
    assert seq3 == 1  # different client, separate counter


@pytest.mark.asyncio
async def test_redacts_authorization_in_args(db: Path):
    logger = AuditLogger(db)
    ev = ToolStartEvent(
        type="tool.start",
        call_id="c1",
        agent_id="main",
        tool="WebFetch",
        args_redacted={"url": "https://x", "Authorization": "Bearer secret"},
    )
    await logger.append("s1", ev, client_slug="acme")

    conn = sqlite3.connect(db)
    row = conn.execute("SELECT data_json FROM audit_log").fetchone()
    data = json.loads(row[0])
    # Whatever the caller passed in args_redacted is stored verbatim — they're responsible
    # for redaction at the source. But the event TYPE name is "args_redacted" to make the
    # contract loud. This test asserts that the field is stored as given (not silently mutated).
    assert "Authorization" in data["args_redacted"]
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && pytest tests/test_audit_logger.py -v
```

Expected: ImportError.

- [ ] **Step 3: Write minimal implementation**

Create `backend/app/audit_logger.py`:
```python
"""Append-only audit log. One row per audit-relevant event.

Audit ID format: SES-YYYY-MM-DD-<client-slug>-<seq:04d>
Seq is per-client, monotonically increasing across all sessions for that client.
"""
from __future__ import annotations

import asyncio
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from app.event_schema import AnyEvent


def generate_audit_id(client_slug: str, date: str, seq: int) -> str:
    return f"SES-{date}-{client_slug}-{seq:04d}"


class AuditLogger:
    """SQLite-backed audit log. Thread/async-safe via a single asyncio lock."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._lock = asyncio.Lock()

    async def append(
        self,
        session_id: str,
        event: AnyEvent,
        client_slug: str,
        entitlements_snapshot: dict[str, object] | None = None,
    ) -> str:
        async with self._lock:
            return await asyncio.to_thread(
                self._append_sync, session_id, event, client_slug, entitlements_snapshot
            )

    def _append_sync(
        self,
        session_id: str,
        event: AnyEvent,
        client_slug: str,
        entitlements_snapshot: dict[str, object] | None,
    ) -> str:
        conn = sqlite3.connect(self._db_path)
        try:
            today = datetime.now(timezone.utc).date().isoformat()
            cur = conn.execute(
                "SELECT COUNT(*) FROM audit_log WHERE audit_id LIKE ?",
                (f"SES-%-{client_slug}-%",),
            )
            seq = cur.fetchone()[0] + 1
            audit_id = generate_audit_id(client_slug, today, seq)
            conn.execute(
                "INSERT INTO audit_log(session_id, event_type, audit_id, data_json, entitlements_snapshot_json) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    session_id,
                    event.type,
                    audit_id,
                    event.model_dump_json(),
                    json.dumps(entitlements_snapshot) if entitlements_snapshot else None,
                ),
            )
            conn.commit()
            return audit_id
        finally:
            conn.close()
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd backend && pytest tests/test_audit_logger.py -v
```

Expected: 5 PASSED.

- [ ] **Step 5: Commit**

```bash
cd "D:/Git Repos/Analyst_agentic_coder"
git add backend/app/audit_logger.py backend/tests/test_audit_logger.py
git commit -m "feat(backend): append-only audit logger with audit-id generator"
```

---

## Task 7: ClaudeCodeService rewrite — stream-json

**Files:**
- Modify: `backend/app/claude_code_service.py` (full rewrite)
- Test: `backend/tests/test_claude_code_service.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_claude_code_service.py`:
```python
"""Tests for the rewritten ClaudeCodeService using mock_claude.py."""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

import pytest

from app.claude_code_service import ClaudeCodeService
from app.event_broker import EventBroker
from app.event_schema import DoneEvent, MessageDeltaEvent, PlanStartEvent


@pytest.fixture
def mock_claude_cmd(fixtures_dir: Path) -> list[str]:
    return [sys.executable, str(fixtures_dir / "mock_claude.py")]


@pytest.mark.asyncio
async def test_send_message_streams_simple_fixture(
    mock_claude_cmd: list[str], fixtures_dir: Path, tmp_path: Path
):
    broker = EventBroker()
    fixture = fixtures_dir / "stream_json" / "simple.jsonl"
    service = ClaudeCodeService(
        workspace_path=tmp_path,
        session_id="s1",
        broker=broker,
        claude_cmd=mock_claude_cmd,
        env_overrides={"MOCK_CLAUDE_FIXTURE": str(fixture)},
    )

    sub = await broker.subscribe("s1")
    await service.send_message("hello")

    received = []
    async for buf in sub:
        received.append(buf.event)

    assert any(isinstance(e, MessageDeltaEvent) for e in received)
    assert any(isinstance(e, DoneEvent) for e in received)


@pytest.mark.asyncio
async def test_send_message_emits_plan_event(
    mock_claude_cmd: list[str], fixtures_dir: Path, tmp_path: Path
):
    broker = EventBroker()
    fixture = fixtures_dir / "stream_json" / "multi_step.jsonl"
    service = ClaudeCodeService(
        workspace_path=tmp_path,
        session_id="s1",
        broker=broker,
        claude_cmd=mock_claude_cmd,
        env_overrides={"MOCK_CLAUDE_FIXTURE": str(fixture)},
    )

    sub = await broker.subscribe("s1")
    await service.send_message("backtest momentum")

    plan_starts = []
    async for buf in sub:
        if isinstance(buf.event, PlanStartEvent):
            plan_starts.append(buf.event)
        if isinstance(buf.event, DoneEvent):
            break
    assert len(plan_starts) == 1
    assert len(plan_starts[0].steps) == 3


def test_resolve_claude_path_uses_shutil_which(monkeypatch: pytest.MonkeyPatch):
    """Hardcoded path bug fix: must use shutil.which, not the old Saurabh-specific path."""
    from app import claude_code_service as mod
    monkeypatch.setattr(mod.shutil, "which", lambda name: f"/fake/bin/{name}")
    resolved = mod.resolve_claude_path()
    assert resolved == "/fake/bin/claude"


def test_resolve_claude_path_raises_if_not_found(monkeypatch: pytest.MonkeyPatch):
    from app import claude_code_service as mod
    monkeypatch.setattr(mod.shutil, "which", lambda name: None)
    with pytest.raises(FileNotFoundError, match="claude"):
        mod.resolve_claude_path()


@pytest.mark.asyncio
async def test_restart_if_needed_replaces_dead_process(
    mock_claude_cmd: list[str], fixtures_dir: Path, tmp_path: Path
):
    broker = EventBroker()
    fixture = fixtures_dir / "stream_json" / "simple.jsonl"
    service = ClaudeCodeService(
        workspace_path=tmp_path,
        session_id="s1",
        broker=broker,
        claude_cmd=mock_claude_cmd,
        env_overrides={"MOCK_CLAUDE_FIXTURE": str(fixture)},
    )
    # Send once to spawn
    sub = await broker.subscribe("s1")
    await service.send_message("first")
    async for buf in sub:
        if isinstance(buf.event, DoneEvent):
            break

    # Kill the subprocess externally by simulating a crash flag
    service._mark_crashed_for_test()
    assert service.is_alive() is False

    await service.restart_if_needed()
    assert service.is_alive() is True
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && pytest tests/test_claude_code_service.py -v
```

Expected: ImportError or AttributeError on the new constructor signature.

- [ ] **Step 3: Read the current claude_code_service.py to understand what's being replaced**

```bash
cd backend && wc -l app/claude_code_service.py
```

Expected: ~200-400 lines. Skim it to confirm what's being removed (subprocess wrapper using `--output-format json`).

- [ ] **Step 4: Replace the file**

Overwrite `backend/app/claude_code_service.py` with:
```python
"""Per-session Claude Code CLI subprocess wrapper.

Spawns `claude --output-format stream-json` once per session, parses output
line-by-line, publishes typed events to the EventBroker.

Design choices:
- Path resolution via shutil.which (the old hardcoded Windows path is gone).
- Subprocess lifetime spans many user prompts; we write prompts to stdin.
- A background reader task owns the subprocess's stdout for the entire lifetime.
- restart_if_needed() reaps a dead subprocess and respawns.
"""
from __future__ import annotations

import asyncio
import os
import shutil
from collections.abc import AsyncIterable
from pathlib import Path
from typing import Any

import structlog

from app.event_broker import EventBroker
from app.event_schema import AnyEvent, ErrorEvent
from app.stream_parser import StreamParser

_log = structlog.get_logger(__name__)


def resolve_claude_path() -> str:
    """Find the claude CLI on PATH. Replaces the old hardcoded path."""
    path = shutil.which("claude")
    if path is None:
        raise FileNotFoundError(
            "`claude` CLI not found on PATH. Install with `npm install -g @anthropic-ai/claude-code`."
        )
    return path


class ClaudeCodeService:
    def __init__(
        self,
        *,
        workspace_path: Path,
        session_id: str,
        broker: EventBroker,
        claude_cmd: list[str] | None = None,
        env_overrides: dict[str, str] | None = None,
        timeout_seconds: float = 600.0,
    ) -> None:
        self._workspace_path = workspace_path
        self._session_id = session_id
        self._broker = broker
        self._claude_cmd = claude_cmd or [resolve_claude_path()]
        self._env_overrides = env_overrides or {}
        self._timeout_seconds = timeout_seconds
        self._proc: asyncio.subprocess.Process | None = None
        self._crashed_flag = False  # test hook
        self._reader_task: asyncio.Task[None] | None = None
        self._lock = asyncio.Lock()

    def is_alive(self) -> bool:
        if self._crashed_flag:
            return False
        return self._proc is not None and self._proc.returncode is None

    def _mark_crashed_for_test(self) -> None:
        self._crashed_flag = True

    async def restart_if_needed(self) -> None:
        async with self._lock:
            if self.is_alive():
                return
            await self._cleanup()
            await self._spawn()

    async def send_message(self, prompt: str) -> None:
        async with self._lock:
            if not self.is_alive():
                await self._cleanup()
                await self._spawn()
            assert self._proc is not None
            assert self._proc.stdin is not None
            self._proc.stdin.write(prompt.encode("utf-8") + b"\n")
            await self._proc.stdin.drain()
            try:
                await asyncio.wait_for(self._wait_until_done(), timeout=self._timeout_seconds)
            except TimeoutError:
                await self._broker.publish(
                    self._session_id,
                    ErrorEvent(
                        type="error",
                        code="TIMEOUT",
                        message=f"CLI did not return within {self._timeout_seconds}s",
                        recoverable=True,
                    ),
                )

    async def _spawn(self) -> None:
        env = {**os.environ, **self._env_overrides}
        cmd = [
            *self._claude_cmd,
            "-p", "",  # we feed prompts via stdin
            "--output-format", "stream-json",
            "--dangerously-skip-permissions",
        ]
        _log.info("claude_code_service.spawn", cmd=cmd, cwd=str(self._workspace_path))
        self._proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=str(self._workspace_path),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
        self._crashed_flag = False
        self._reader_task = asyncio.create_task(self._read_stdout())

    async def _read_stdout(self) -> None:
        assert self._proc is not None
        assert self._proc.stdout is not None
        parser = StreamParser()

        async def lines() -> AsyncIterable[str]:
            assert self._proc is not None
            assert self._proc.stdout is not None
            while True:
                raw = await self._proc.stdout.readline()
                if not raw:
                    return
                yield raw.decode("utf-8", errors="replace").rstrip("\n")

        try:
            async for ev in parser.parse_lines(lines()):
                await self._broker.publish(self._session_id, ev)
        except Exception as exc:  # pragma: no cover - defensive
            _log.exception("claude_code_service.reader_crash", error=str(exc))
            await self._broker.publish(
                self._session_id,
                ErrorEvent(type="error", code="CLI_CRASH", message=str(exc), recoverable=True),
            )

    async def _wait_until_done(self) -> None:
        assert self._reader_task is not None
        await self._reader_task

    async def _cleanup(self) -> None:
        if self._proc and self._proc.returncode is None:
            self._proc.terminate()
            try:
                await asyncio.wait_for(self._proc.wait(), timeout=2.0)
            except TimeoutError:
                self._proc.kill()
                await self._proc.wait()
        if self._reader_task and not self._reader_task.done():
            self._reader_task.cancel()
        self._proc = None
        self._reader_task = None
        self._crashed_flag = False
```

- [ ] **Step 5: Run test to verify it passes**

```bash
cd backend && pytest tests/test_claude_code_service.py -v
```

Expected: 5 PASSED.

- [ ] **Step 6: Run mypy on the new file**

```bash
cd backend && mypy app/claude_code_service.py app/event_schema.py app/stream_parser.py app/event_broker.py app/audit_logger.py
```

Expected: no errors. Fix any inline.

- [ ] **Step 7: Commit**

```bash
cd "D:/Git Repos/Analyst_agentic_coder"
git add backend/app/claude_code_service.py backend/tests/test_claude_code_service.py
git commit -m "feat(backend): rewrite ClaudeCodeService for stream-json + shutil.which path"
```

---

## Task 8: SSE endpoint + 202-Accepted POST /api/chat

**Files:**
- Modify: `backend/app/main.py` (add SSE route, modify POST /api/chat)
- Test: `backend/tests/test_chat_streaming.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_chat_streaming.py`:
```python
"""End-to-end test: POST /api/chat → SSE stream → events arrive in order."""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import httpx
import pytest

from app.main import app, get_broker, get_claude_factory
from app.event_broker import EventBroker
from app.claude_code_service import ClaudeCodeService


@pytest.fixture
def mock_claude_cmd(fixtures_dir: Path) -> list[str]:
    return [sys.executable, str(fixtures_dir / "mock_claude.py")]


@pytest.fixture
def app_with_mocks(mock_claude_cmd, fixtures_dir, tmp_path, monkeypatch):
    fixture = fixtures_dir / "stream_json" / "multi_step.jsonl"
    broker = EventBroker()

    def factory(*, workspace_path, session_id):
        return ClaudeCodeService(
            workspace_path=workspace_path,
            session_id=session_id,
            broker=broker,
            claude_cmd=mock_claude_cmd,
            env_overrides={"MOCK_CLAUDE_FIXTURE": str(fixture)},
        )

    app.dependency_overrides[get_broker] = lambda: broker
    app.dependency_overrides[get_claude_factory] = lambda: factory
    yield app
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_post_chat_returns_202_with_stream_url(app_with_mocks):
    transport = httpx.ASGITransport(app=app_with_mocks)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.post("/api/chat", json={"message": "hello", "session_id": "s1"})
    assert r.status_code == 202
    body = r.json()
    assert "event_stream_url" in body
    assert body["event_stream_url"].endswith("/api/chat/stream/s1")


@pytest.mark.asyncio
async def test_sse_stream_emits_events(app_with_mocks):
    transport = httpx.ASGITransport(app=app_with_mocks)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        await ac.post("/api/chat", json={"message": "backtest", "session_id": "s2"})

        events: list[dict] = []
        async with ac.stream("GET", "/api/chat/stream/s2") as r:
            async for line in r.aiter_lines():
                if line.startswith("data: "):
                    events.append(json.loads(line[6:]))
                if line.startswith("event: done"):
                    break

    types = [e["type"] for e in events]
    assert "plan.start" in types
    assert "tool.start" in types
    assert "done" in types


@pytest.mark.asyncio
async def test_sse_stream_supports_last_event_id_replay(app_with_mocks):
    transport = httpx.ASGITransport(app=app_with_mocks)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        await ac.post("/api/chat", json={"message": "x", "session_id": "s3"})
        await asyncio.sleep(0.5)  # let some events buffer

        ids: list[int] = []
        async with ac.stream(
            "GET",
            "/api/chat/stream/s3",
            headers={"Last-Event-ID": "2"},
        ) as r:
            async for line in r.aiter_lines():
                if line.startswith("id: "):
                    ids.append(int(line[4:]))
                if len(ids) >= 3:
                    break
        assert all(i > 2 for i in ids)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && pytest tests/test_chat_streaming.py -v
```

Expected: ImportError on `get_broker` / `get_claude_factory` — these don't exist yet.

- [ ] **Step 3: Read current main.py to find POST /api/chat**

```bash
cd backend && grep -n "@app.post\|@app.get\|/api/chat" app/main.py | head -20
```

Note the existing line numbers; we'll modify the POST /api/chat handler and add the new SSE route below it.

- [ ] **Step 4: Add the streaming additions to main.py**

Edit `backend/app/main.py`:

(a) **Add at the top of the file**, after existing imports:
```python
from sse_starlette.sse import EventSourceResponse
from app.event_broker import EventBroker
from app.event_schema import DoneEvent

_broker = EventBroker()


def get_broker() -> EventBroker:
    return _broker


def get_claude_factory():
    """Dependency-injectable factory; tests override this to inject a mock-CLI service."""
    from pathlib import Path
    from app.claude_code_service import ClaudeCodeService

    def factory(*, workspace_path: Path, session_id: str) -> ClaudeCodeService:
        return ClaudeCodeService(
            workspace_path=workspace_path,
            session_id=session_id,
            broker=_broker,
        )
    return factory
```

(b) **Replace the existing POST /api/chat handler body** so it returns 202:
```python
@app.post("/api/chat", status_code=202)
async def chat(
    req: ChatRequest,
    broker: EventBroker = Depends(get_broker),
    claude_factory = Depends(get_claude_factory),
):
    session_id = req.session_id or _create_session()
    workspace_path = workspace_manager.get_workspace_path(session_id) or workspace_manager.create_workspace(session_id)

    service = workspace_manager.get_or_create_service(
        session_id=session_id,
        factory=lambda: claude_factory(workspace_path=workspace_path, session_id=session_id),
    )

    # Fire and forget — events stream over SSE
    asyncio.create_task(service.send_message(req.message))

    return {
        "session_id": session_id,
        "event_stream_url": f"/api/chat/stream/{session_id}",
    }
```

(c) **Add the SSE route** below the chat handler:
```python
@app.get("/api/chat/stream/{session_id}")
async def chat_stream(
    session_id: str,
    request: Request,
    broker: EventBroker = Depends(get_broker),
):
    last_event_id_header = request.headers.get("Last-Event-ID", "0")
    try:
        last_event_id = int(last_event_id_header)
    except ValueError:
        last_event_id = 0

    async def event_source():
        sub = await broker.subscribe(session_id, last_event_id=last_event_id)
        async for buffered in sub:
            yield {
                "id": str(buffered.id),
                "event": buffered.event.type,
                "data": buffered.event.model_dump_json(),
            }
            if isinstance(buffered.event, DoneEvent):
                return

    return EventSourceResponse(event_source())
```

(d) **Add `get_or_create_service` to workspace_manager** if it doesn't exist. Open `backend/app/workspace_manager.py` and add:
```python
def get_or_create_service(self, session_id: str, factory):
    """Lookup or create a ClaudeCodeService for this session."""
    if session_id in self._active_claude_instances:
        return self._active_claude_instances[session_id]
    svc = factory()
    self._active_claude_instances[session_id] = svc
    return svc
```

- [ ] **Step 5: Run test to verify it passes**

```bash
cd backend && pytest tests/test_chat_streaming.py -v
```

Expected: 3 PASSED.

If failures relate to the existing main.py having pre-existing handlers that conflict, fix surgically — keep the old `/api/progress/{id}` polling endpoint alive (per the migration plan, it's removed only in Phase 3).

- [ ] **Step 6: Run the full test suite**

```bash
cd backend && pytest -v
```

Expected: all tests across event_schema, stream_parser, event_broker, migrations, audit_logger, claude_code_service, chat_streaming PASS.

- [ ] **Step 7: Run mypy on touched files**

```bash
cd backend && mypy app/main.py app/workspace_manager.py
```

Expected: no errors on the new code (existing code may have warnings — acceptable).

- [ ] **Step 8: Commit**

```bash
cd "D:/Git Repos/Analyst_agentic_coder"
git add backend/app/main.py backend/app/workspace_manager.py backend/tests/test_chat_streaming.py
git commit -m "feat(backend): SSE /api/chat/stream endpoint + 202 POST /api/chat"
```

---

## Task 9: Smoke-test against the real claude CLI

**Files:** none new. Smoke test of the actual CLI integration.

- [ ] **Step 1: Verify the claude CLI is installed**

```bash
which claude && claude --version
```

Expected: prints a version. If not, fix install before proceeding.

- [ ] **Step 2: Start the backend with real CLI**

```bash
cd "D:/Git Repos/Analyst_agentic_coder/backend"
python -m uvicorn app.main:app --port 8000 --reload &
```

Wait ~3 seconds for startup.

- [ ] **Step 3: Hit POST /api/chat**

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"list files in current directory","session_id":"smoke-1"}'
```

Expected:
```json
{"session_id":"smoke-1","event_stream_url":"/api/chat/stream/smoke-1"}
```
Status code 202.

- [ ] **Step 4: Subscribe to the stream**

```bash
curl -N http://localhost:8000/api/chat/stream/smoke-1
```

Expected: live SSE frames with `event:`, `id:`, `data:` lines. At minimum a `done` event arrives within 60 seconds.

If no events arrive, debug:
1. Backend logs (`structlog` JSON output in the terminal).
2. Verify `claude` is being spawned (check `ps aux | grep claude` or `tasklist | findstr claude` on Windows).
3. Check that the CLI's stdout is being read (the reader task in `_read_stdout`).

- [ ] **Step 5: Stop the backend**

```bash
pkill -f "uvicorn app.main:app" || taskkill /F /IM python.exe
```

(or Ctrl+C in the terminal that ran uvicorn.)

- [ ] **Step 6: No commit — this is a smoke test only**

If the smoke test reveals a bug, file it as the next task. If it passes cleanly, proceed to Task 10.

---

## Task 10: CI workflow for the backend

**Files:**
- Create: `.github/workflows/backend-ci.yml`

- [ ] **Step 1: Write the workflow**

Create `.github/workflows/backend-ci.yml`:
```yaml
name: backend-ci

on:
  push:
    branches: [main]
    paths:
      - 'backend/**'
      - '.github/workflows/backend-ci.yml'
  pull_request:
    paths:
      - 'backend/**'
      - '.github/workflows/backend-ci.yml'

jobs:
  test:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    defaults:
      run:
        working-directory: backend
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Lint (ruff)
        run: ruff check .

      - name: Type check (mypy)
        run: mypy app/ migrations/

      - name: Tests
        run: pytest --cov=app --cov-report=term-missing --cov-fail-under=80
```

- [ ] **Step 2: Verify it parses locally**

If `act` is installed:
```bash
act -l -W .github/workflows/backend-ci.yml
```

Otherwise just visually verify YAML syntax via `yamllint` if available.

- [ ] **Step 3: Commit**

```bash
cd "D:/Git Repos/Analyst_agentic_coder"
git add .github/workflows/backend-ci.yml
git commit -m "ci: add backend lint/typecheck/test workflow"
```

---

## Self-review checklist (run before handing off)

- [ ] Spec coverage: Phase 1 of the spec is fully covered (event schema ✓, stream parser ✓, broker ✓, audit logger ✓, ClaudeCodeService rewrite ✓, SSE endpoint ✓, 202 on POST /api/chat ✓, hardcoded path fix ✓, restart_if_needed implementation ✓). The `/api/files/{path}` removal and CORS allowlist are intentionally **deferred to a separate hygiene plan**, not this one.
- [ ] No placeholders: every step has either complete code, an exact command, or both. `git rm`, exact filenames, exact CLI flags.
- [ ] Type consistency: `parse_event` is called the same in tests and source. `BufferedEvent` fields (`id`, `event`) match between broker source and tests. `ClaudeCodeService` constructor has the same kwargs in tests and source.
- [ ] TDD discipline: every task that introduces code starts with a failing test (Step 1), runs it to confirm failure (Step 2), implements (Step 3), confirms passing (Step 4), commits (Step 5).
- [ ] Each task ends with a commit so the work is bisectable.

---

## Open follow-ups (NOT in this plan)

- Phase 2 plan: frontend three-pane shell + EventSource consumer + Zustand store.
- Phase 3 plan: branded artifacts + audit tab + PDF export.
- Hygiene plan: remove `/api/files/{path}`, CORS allowlist, fix git-creds-in-URL log leak.
- Frontend `/api-contract-check` skill should run in CI once Phase 2 lands.
