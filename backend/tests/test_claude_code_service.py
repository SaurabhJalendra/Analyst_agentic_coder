"""Tests for the rewritten ClaudeCodeService using mock_claude.py."""
from __future__ import annotations

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
    sub = await broker.subscribe("s1")
    await service.send_message("first")
    async for buf in sub:
        if isinstance(buf.event, DoneEvent):
            break

    service._mark_crashed_for_test()
    assert service.is_alive() is False

    await service.restart_if_needed()
    assert service.is_alive() is True
