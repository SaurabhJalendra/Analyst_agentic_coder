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
    # Start it so it registers, then close it
    await asyncio.wait_for(_consume_one_safely(broker, sub_gen, "s1"), timeout=1.0)
    await sub_gen.aclose()
    await broker.publish("s1", _make_event())
    assert broker.subscriber_count("s1") == 0


async def _consume_one_safely(broker, sub_gen, session_id):
    """Helper: publish a kickoff event and consume it, so the generator registers."""
    pub_task = asyncio.create_task(broker.publish(session_id, _make_event("kickoff")))
    try:
        await sub_gen.__anext__()
    finally:
        await pub_task


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
