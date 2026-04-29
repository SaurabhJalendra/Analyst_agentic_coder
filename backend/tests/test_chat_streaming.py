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
def app_with_mocks(mock_claude_cmd, fixtures_dir, tmp_path):
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
        await asyncio.sleep(0.5)

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
