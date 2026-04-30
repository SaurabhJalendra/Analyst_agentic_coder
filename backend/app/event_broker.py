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
        already_closed: bool
        async with self._lock:
            state = self._sessions.setdefault(session_id, _SessionState())
            replay = [b for b in state.buffer if b.id > last_event_id]
            already_closed = state.closed
            if not already_closed:
                state.subscriber_queues.append(queue)
        try:
            for buffered in replay:
                yield buffered
            if already_closed:
                return
            while True:
                item = await queue.get()
                if item is None:
                    return
                yield item
        finally:
            # Remove the queue from subscriber_queues without re-entering the
            # async lock (safe: list.remove is thread-safe enough for single-
            # threaded asyncio; the lock guards concurrent publish/subscribe).
            _state = self._sessions.get(session_id)
            if _state is not None:
                if queue in _state.subscriber_queues:
                    _state.subscriber_queues.remove(queue)
                # Drop the session entry once it's done streaming and no one
                # else is listening — otherwise _sessions accumulates forever
                # (one per chat ever). The buffer for `Last-Event-ID` replay
                # is intentionally lost: a reconnect after this point gets a
                # fresh stream which is fine because `done` already fired.
                if _state.closed and not _state.subscriber_queues:
                    self._sessions.pop(session_id, None)

    def subscriber_count(self, session_id: str) -> int:
        state = self._sessions.get(session_id)
        return 0 if state is None else len(state.subscriber_queues)
