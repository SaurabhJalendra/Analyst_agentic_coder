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
async def test_restart_if_needed_clears_crashed_flag(
    mock_claude_cmd: list[str], fixtures_dir: Path, tmp_path: Path
):
    """In the per-message-subprocess model, restart_if_needed just clears the crash marker."""
    broker = EventBroker()
    fixture = fixtures_dir / "stream_json" / "simple.jsonl"
    service = ClaudeCodeService(
        workspace_path=tmp_path,
        session_id="s1",
        broker=broker,
        claude_cmd=mock_claude_cmd,
        env_overrides={"MOCK_CLAUDE_FIXTURE": str(fixture)},
    )

    service._mark_crashed_for_test()
    assert service.is_alive() is False

    await service.restart_if_needed()
    assert service.is_alive() is True


@pytest.mark.asyncio
async def test_synthetic_done_when_cli_emits_none(
    mock_claude_cmd: list[str], tmp_path: Path
):
    """When the CLI exits without emitting a `done` event, the service publishes a synthetic one."""
    # Create a fixture with NO done event
    nodone = tmp_path / "no_done.jsonl"
    nodone.write_text(
        '{"type":"message.delta","message_id":"m1","append_text":"hi"}\n'
        '{"type":"message.done","message_id":"m1"}\n',
        encoding="utf-8",
    )

    broker = EventBroker()
    service = ClaudeCodeService(
        workspace_path=tmp_path,
        session_id="s1",
        broker=broker,
        claude_cmd=mock_claude_cmd,
        env_overrides={"MOCK_CLAUDE_FIXTURE": str(nodone)},
    )

    sub = await broker.subscribe("s1")
    await service.send_message("hi")

    received = []
    async for buf in sub:
        received.append(buf.event)

    assert any(isinstance(e, DoneEvent) for e in received), "synthetic Done should be emitted"


@pytest.mark.asyncio
async def test_cli_invocation_includes_verbose_flag(
    mock_claude_cmd: list[str], fixtures_dir: Path, tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    """Regression: claude --print --output-format stream-json REQUIRES --verbose.
    Smoke test on 2026-04-29 caught the missing flag (CLI rejects with
    'When using --print, --output-format=stream-json requires --verbose').
    """
    import asyncio as _asyncio

    captured_cmd: list[list[str]] = []
    real_create = _asyncio.create_subprocess_exec

    async def capturing_create(*args: str, **kwargs: object):
        captured_cmd.append(list(args))
        return await real_create(*args, **kwargs)

    monkeypatch.setattr(_asyncio, "create_subprocess_exec", capturing_create)

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
    await service.send_message("test")
    async for buf in sub:
        if isinstance(buf.event, DoneEvent):
            break

    assert captured_cmd, "subprocess was never spawned"
    cmd = captured_cmd[0]
    assert "--verbose" in cmd, f"--verbose flag missing from cmd: {cmd}"
    # And the order matters: --verbose must accompany --output-format stream-json
    of_idx = cmd.index("--output-format")
    assert cmd[of_idx + 1] == "stream-json"
    assert "--verbose" in cmd[of_idx:], "--verbose must come after --output-format"
