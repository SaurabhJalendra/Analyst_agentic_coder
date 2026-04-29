"""Per-session Claude Code CLI subprocess wrapper.

Each send_message() spawns a fresh `claude -p <prompt> --output-format stream-json
--dangerously-skip-permissions` subprocess and streams its output through the
StreamParser to the EventBroker. After the subprocess exits, a synthetic
DoneEvent is published so SSE subscribers close cleanly even if the CLI didn't
emit one itself.

Design rationale:
- `claude -p` is one-shot print mode; it does NOT read further prompts from stdin.
- Per-message subprocess matches the actual CLI lifecycle.
- restart_if_needed() becomes a no-op contract (each send spawns fresh).
"""
from __future__ import annotations

import asyncio
import os
import shutil
from collections.abc import AsyncIterable
from pathlib import Path

import structlog

from app.cli_translator import CLITranslator
from app.event_broker import EventBroker
from app.event_schema import DoneEvent, ErrorEvent
from app.stream_parser import StreamParser  # noqa: F401  (kept for tests/legacy)

_log = structlog.get_logger(__name__)


def resolve_claude_path() -> str:
    """Find the claude CLI on PATH."""
    path = shutil.which("claude")
    if path is None:
        raise FileNotFoundError(
            "`claude` CLI not found on PATH. "
            "Install with `npm install -g @anthropic-ai/claude-code`."
        )
    return path


class ClaudeCodeService:
    """Per-session service. Spawns a fresh subprocess for each send_message call."""

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
        self._crashed_flag = False  # test hook
        self._lock = asyncio.Lock()

    def is_alive(self) -> bool:
        return not self._crashed_flag

    def _mark_crashed_for_test(self) -> None:
        self._crashed_flag = True

    async def restart_if_needed(self) -> None:
        """No-op in the per-message-subprocess model. Clears crash flag for compat."""
        async with self._lock:
            self._crashed_flag = False

    async def send_message(self, prompt: str) -> None:
        """Spawn a fresh subprocess for this prompt; stream events to the broker."""
        async with self._lock:
            try:
                await asyncio.wait_for(
                    self._run_one(prompt),
                    timeout=self._timeout_seconds,
                )
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
                # Still emit a synthetic Done so subscribers close.
                await self._publish_synthetic_done()

    async def _run_one(self, prompt: str) -> None:
        env = {**os.environ, **self._env_overrides}
        cmd = [
            *self._claude_cmd,
            "-p", prompt,
            "--output-format", "stream-json",
            "--verbose",
            "--dangerously-skip-permissions",
        ]
        _log.info(
            "claude_code_service.spawn",
            cmd=cmd[:3] + ["<prompt>"] + cmd[4:],  # don't log the user's prompt
            cwd=str(self._workspace_path),
        )
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=str(self._workspace_path),
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )

        translator = CLITranslator(self._session_id)
        emitted_done = False
        events_translated = 0

        try:
            assert proc.stdout is not None
            while True:
                raw = await proc.stdout.readline()
                if not raw:
                    break
                line = raw.decode("utf-8", errors="replace").rstrip("\n")
                for ev in translator.translate(line):
                    events_translated += 1
                    await self._broker.publish(self._session_id, ev)
                    if isinstance(ev, DoneEvent):
                        emitted_done = True
        except Exception as exc:  # pragma: no cover - defensive
            _log.exception("claude_code_service.reader_crash", error=str(exc))
            await self._broker.publish(
                self._session_id,
                ErrorEvent(type="error", code="CLI_CRASH", message=str(exc), recoverable=True),
            )

        await proc.wait()

        if proc.returncode != 0 and events_translated == 0:
            stderr = b""
            if proc.stderr is not None:
                stderr = await proc.stderr.read()
            await self._broker.publish(
                self._session_id,
                ErrorEvent(
                    type="error",
                    code="CLI_NONZERO_EXIT",
                    message=(
                        stderr.decode("utf-8", errors="replace")[:500]
                        or f"exit {proc.returncode}"
                    ),
                    recoverable=True,
                ),
            )

        if not emitted_done:
            await self._publish_synthetic_done()

    async def _publish_synthetic_done(self) -> None:
        await self._broker.publish(
            self._session_id,
            DoneEvent(type="done", session_id=self._session_id),
        )
