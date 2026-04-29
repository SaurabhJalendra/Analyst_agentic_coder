import { produce } from 'immer';
import type { AnyEvent } from '../types/events';
import type {
  ActivityEntry,
  AgentState,
  Artifact,
  ChatTurn,
  PlanStep,
  SourceAccess,
} from '../types/domain';

export interface SessionState {
  plan: PlanStep[];
  agents: Record<string, AgentState>;
  activity: ActivityEntry[];
  artifacts: Artifact[];
  sources: Record<string, SourceAccess>;
  chat: ChatTurn[];
  isStreaming: boolean;
  error: { code: string; message: string; recoverable: boolean } | null;
  cost: { usd: number; tokensIn: number; tokensOut: number };
  lastEventId: number;
}

export const initialSessionState = (): SessionState => ({
  plan: [],
  agents: {},
  activity: [],
  artifacts: [],
  sources: {},
  chat: [],
  isStreaming: false,
  error: null,
  cost: { usd: 0, tokensIn: 0, tokensOut: 0 },
  lastEventId: 0,
});

let _activitySeq = 0;
const nextActivityId = () => ++_activitySeq;

function pushActivity(state: SessionState, category: ActivityEntry['category'], text: string, meta?: Record<string, unknown>) {
  state.activity.push({ id: nextActivityId(), ts: Date.now(), category, text, meta });
  if (state.activity.length > 500) state.activity.splice(0, state.activity.length - 500);
}

export function applyEvent(state: SessionState, event: AnyEvent): SessionState {
  return produce(state, (draft) => {
    switch (event.type) {
      case 'plan.start':
        draft.plan = event.steps.map((s) => ({ id: s.id, description: s.description, status: 'pending' }));
        pushActivity(draft, 'plan', `plan started with ${event.steps.length} steps`);
        break;
      case 'plan.step.start': {
        const step = draft.plan.find((s) => s.id === event.step_id);
        if (step) { step.status = 'running'; step.startedAt = Date.now(); }
        pushActivity(draft, 'plan', `step ${event.step_id} started`);
        break;
      }
      case 'plan.step.done': {
        const step = draft.plan.find((s) => s.id === event.step_id);
        if (step) { step.status = 'done'; step.durationMs = event.duration_ms; }
        pushActivity(draft, 'plan', `step ${event.step_id} done in ${event.duration_ms}ms`);
        break;
      }
      case 'subagent.spawn':
        draft.agents[event.agent_id] = {
          id: event.agent_id,
          parentId: event.parent_id ?? undefined,
          kind: event.kind,
          model: event.model,
          status: 'running',
          tokens: 0,
          toolsUsed: [],
        };
        draft.chat.push({ kind: 'subagent', id: `sa-${event.agent_id}`, agentId: event.agent_id, subKind: event.kind, status: 'running', ts: Date.now() });
        pushActivity(draft, 'subagent', `spawn ${event.kind} (${event.agent_id})`);
        break;
      case 'subagent.delta': {
        const ag = draft.agents[event.agent_id];
        if (ag) ag.tokens = event.tokens;
        const chatTurn = draft.chat.find((t) => t.kind === 'subagent' && t.agentId === event.agent_id);
        if (chatTurn && chatTurn.kind === 'subagent') chatTurn.statusText = event.status_text ?? undefined;
        break;
      }
      case 'subagent.done': {
        const ag = draft.agents[event.agent_id];
        if (ag) { ag.status = 'done'; ag.tokens = event.tokens; ag.durationMs = event.duration_ms; ag.result = event.result ?? undefined; }
        const chatTurn = draft.chat.find((t) => t.kind === 'subagent' && t.agentId === event.agent_id);
        if (chatTurn && chatTurn.kind === 'subagent') chatTurn.status = 'done';
        pushActivity(draft, 'subagent', `done ${event.agent_id} in ${event.duration_ms}ms`);
        break;
      }
      case 'tool.start':
        pushActivity(draft, 'tool', `${event.tool} start`, { call_id: event.call_id, args: event.args_redacted });
        break;
      case 'tool.done':
        pushActivity(draft, 'tool', `tool done in ${event.duration_ms}ms ${event.ok ? 'ok' : 'fail'}`, { call_id: event.call_id });
        break;
      case 'skill':
        pushActivity(draft, 'skill', `/${event.name}${event.args ? ' ' + event.args : ''}`);
        break;
      case 'memory':
        pushActivity(draft, 'memory', `${event.op} ${event.path}`);
        break;
      case 'wiki':
        pushActivity(draft, 'memory', `wiki ${event.op} ${event.target}`);
        break;
      case 'source': {
        const src = draft.sources[event.source] ?? (draft.sources[event.source] = { source: event.source, callCount: 0 });
        src.callCount += 1;
        src.lastOp = event.operation;
        pushActivity(draft, 'source', `${event.source}: ${event.operation}`);
        break;
      }
      case 'thinking':
        draft.chat.push({ kind: 'thinking', id: `th-${event.agent_id}-${Date.now()}`, tokens: event.tokens, preview: event.preview_text, ts: Date.now() });
        pushActivity(draft, 'thinking', `${event.tokens} tokens`);
        break;
      case 'artifact': {
        const art: Artifact = { id: event.artifact_id, kind: event.kind, title: event.title, sourceAttribution: event.source_attribution, methodologyId: event.methodology_id, createdAt: Date.now() };
        draft.artifacts.push(art);
        draft.chat.push({ kind: 'artifact', id: `art-${event.artifact_id}`, artifact: art, ts: Date.now() });
        break;
      }
      case 'message.delta': {
        let msg = draft.chat.find((t) => t.kind === 'assistant' && t.id === event.message_id);
        if (!msg) {
          msg = { kind: 'assistant', id: event.message_id, text: '', ts: Date.now() };
          draft.chat.push(msg);
        }
        if (msg.kind === 'assistant') msg.text += event.append_text;
        break;
      }
      case 'message.done':
        pushActivity(draft, 'message', `message ${event.message_id} done`);
        break;
      case 'cost.delta':
        draft.cost.usd += event.usd;
        draft.cost.tokensIn += event.tokens_in;
        draft.cost.tokensOut += event.tokens_out;
        break;
      case 'approval':
        pushActivity(draft, 'other', `approval needed: ${event.description}`);
        break;
      case 'error':
        draft.error = { code: event.code, message: event.message, recoverable: event.recoverable };
        draft.isStreaming = false;
        pushActivity(draft, 'error', `${event.code}: ${event.message}`);
        break;
      case 'done':
        draft.isStreaming = false;
        break;
    }
  });
}

export function appendUserMessage(state: SessionState, text: string): SessionState {
  return produce(state, (draft) => {
    draft.chat.push({ kind: 'user', id: `u-${Date.now()}`, text, ts: Date.now() });
    draft.isStreaming = true;
    draft.error = null;
    draft.plan = [];
    draft.agents = {};
  });
}
