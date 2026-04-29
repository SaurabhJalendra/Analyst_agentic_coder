"""Typed SSE event schema. Mirrors the spec section "Event schema".

Every event sent over /api/chat/stream/{session_id} is one of these.
The frontend has a matching TypeScript discriminated union.
"""
from __future__ import annotations

from typing import Annotated, Literal

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
    PlanStartEvent
    | PlanStepStartEvent
    | PlanStepDoneEvent
    | SubagentSpawnEvent
    | SubagentDeltaEvent
    | SubagentDoneEvent
    | ToolStartEvent
    | ToolDoneEvent
    | SkillInvokeEvent
    | MemoryOpEvent
    | WikiOpEvent
    | SourceAccessEvent
    | ThinkingBlockEvent
    | ArtifactCreateEvent
    | MessageDeltaEvent
    | MessageDoneEvent
    | CostDeltaEvent
    | ApprovalNeededEvent
    | ErrorEvent
    | DoneEvent,
    Field(discriminator="type"),
]

_ADAPTER: TypeAdapter[AnyEvent] = TypeAdapter(AnyEvent)


def parse_event(raw_json: str | bytes) -> AnyEvent:
    """Parse a JSON line into a typed event.

    Raises ValidationError on unknown type or malformed payload.
    """
    return _ADAPTER.validate_json(raw_json)
