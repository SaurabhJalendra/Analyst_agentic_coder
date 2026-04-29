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

import structlog

from app.event_broker import EventBroker
from app.event_schema import ErrorEvent
from app.stream_parser import StreamParser

_log = structlog.get_logger(__name__)


def resolve_claude_path() -> str:
    """Find the claude CLI on PATH. Replaces the old hardcoded path."""
    path = shutil.which("claude")
    if path is None:
        raise FileNotFoundError(
            "`claude` CLI not found on PATH. "
            "Install with `npm install -g @anthropic-ai/claude-code`."
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
