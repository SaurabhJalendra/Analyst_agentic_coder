"""Async parser for `claude --output-format stream-json` output.

Consumes an async iterable of UTF-8 lines (one JSON event per line) and yields
typed events. Malformed lines are counted, not raised.
"""
from __future__ import annotations

from collections.abc import AsyncIterable, AsyncIterator
from dataclasses import dataclass

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
