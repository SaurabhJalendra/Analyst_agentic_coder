# Phase 2 — Quant Console Frontend Shell Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the existing single-pane React chat UI with the Quant Console three-pane research console, wired to the new SSE backend (`POST /api/chat` 202 + `GET /api/chat/stream/{session_id}`).

**Architecture:** React 19 + TypeScript strict + Vite + Tailwind v4. Zustand store + Immer middleware drives all UI state. `EventSource` consumes SSE events, runs through a Zod-validated reducer, mutates the store. Components subscribe to store slices for re-render. No tests for visual components (Storybook stories serve as behavioral docs); store + service + reducer are unit-tested.

**Tech Stack:** React 19, TypeScript 5.9 (strict), Vite 7, Tailwind v4, Zustand 5, Immer, Zod, axios (existing), Vitest, React Testing Library, Storybook 8.

---

## Spec reference

Implements **Phase 2** of `docs/superpowers/specs/2026-04-29-quant-console-frontend-design.md`. Specifically the frontend component tree, brand color tokens, EventSource consumer, and Zustand state. Phase 1 backend is in place — this consumes it.

**Out of scope:** branded PDF export (Phase 3), Audit log UI population (Phase 3), Report builder rich editing (Phase 3), entitlements service (real impl deferred).

---

## File structure

### New files (all under `frontend-react/`)
| Path | Responsibility |
|---|---|
| `src/types/events.ts` | TS discriminated union mirroring backend Pydantic `event_schema.py` |
| `src/types/domain.ts` | Session, Artifact, AgentState, etc. — application types |
| `src/services/eventStream.ts` | `EventSource` wrapper with `Last-Event-ID` reconnect |
| `src/services/eventReducer.ts` | Pure function: (state, event) → state mutations via Immer |
| `src/store/sessionStore.ts` | Zustand store + Immer middleware + selectors |
| `src/hooks/useSession.ts` | Thin selector hooks; replaces gut of useChat.ts |
| `src/components/frame/BrandBar.tsx` | Navy/gold top bar with Q logo + user identity + RM contact |
| `src/components/frame/ComplianceBar.tsx` | Disclaimer + entitlements pill + MNPI walls indicator + last refresh |
| `src/components/frame/StatusBar.tsx` | Session pill + plan progress + agent count + sources + ⌘K + Halt |
| `src/components/frame/ComplianceFooter.tsx` | Disclosures + audit ID + RM contact |
| `src/components/layout/ThreePaneLayout.tsx` | CSS grid 220/1fr/360 + 60px prompt row + footer |
| `src/components/left/LeftRail.tsx` | Container; mounts the three sections below |
| `src/components/left/SessionsList.tsx` | Sessions + new-session affordance |
| `src/components/left/WorkspaceTree.tsx` | Collapsible folder tree of workspace files |
| `src/components/left/KnowledgePanel.tsx` | Wiki page count, memory count, last-ingest timestamp |
| `src/components/center/ChatStream.tsx` | Virtualized list of message turns |
| `src/components/center/UserMessage.tsx` | Right-aligned light-blue bubble |
| `src/components/center/ThinkingBlock.tsx` | Collapsed amber pill with token count + preview |
| `src/components/center/NotebookCell.tsx` | Code + DataFrame + chart bundled card |
| `src/components/center/BrandedArtifactCard.tsx` | Navy-header artifact with provenance footer + "How this was made" |
| `src/components/center/SubAgentIndicator.tsx` | Colored-border banner for sub-agent status |
| `src/components/center/PlanRail.tsx` | Inline strip "Plan — N/M steps · K sub-agents" |
| `src/components/right/RightRail.tsx` | Container with tab bar |
| `src/components/right/tabs/PlanTab.tsx` | Plan tree (steps + nested sub-agents) |
| `src/components/right/tabs/AgentsTab.tsx` | Agent cards (running/queued/done) + Sources accessed |
| `src/components/right/tabs/ActivityTab.tsx` | Color-coded chronological event stream |
| `src/components/right/tabs/ArtifactsTab.tsx` | Artifact gallery (Phase 2 stub: list w/ no drag) |
| `src/components/right/tabs/ReportTab.tsx` | Phase 2 stub: "Report builder coming in Phase 3" |
| `src/components/right/tabs/AuditTab.tsx` | Phase 2 stub: paginated audit log read |
| `src/components/prompt/PromptInput.tsx` | Textarea with auto-resize + selectors + Export PDF (stub) |
| `src/components/renderers/Chart.tsx` | Phase 2 stub (Plotly chosen in Phase 3) |
| `src/components/renderers/DataTable.tsx` | Phase 2: TanStack Table v8 minimal wrapper |
| `src/components/renderers/MarkdownWithLatex.tsx` | react-markdown + remark-math + rehype-katex |
| `src/components/renderers/CodeBlock.tsx` | highlight.js wrapper |
| `src/services/api.ts` | UPDATED — drop `extractFilePaths` regex, add `postChat` returning event_stream_url |

### Modified files
| Path | Change |
|---|---|
| `src/App.tsx` | Replace single-pane chat with `ThreePaneLayout` mounting frame + rail components |
| `src/main.tsx` | No change beyond ensuring KaTeX CSS is imported |
| `src/index.css` | Add Inter + KaTeX import; keep Tailwind directives; remove old custom CSS |
| `src/hooks/useChat.ts` | Gutted; thin re-export of `useSession` selectors for backward compat (or deleted if no consumers remain) |
| `tailwind.config.js` | Add brand.{800,900}, gold.{500,700} tokens; Inter + JetBrains Mono fonts |
| `package.json` | Add: zustand, immer, zod, @tanstack/react-table, react-markdown, remark-math, rehype-katex, katex, highlight.js, vitest, @testing-library/react, @testing-library/jest-dom, jsdom, @storybook/react-vite (devDependencies). Remove: react-syntax-highlighter (already unused) |
| `vite.config.ts` | Add Vitest config (jsdom env, setupFiles) |

### Deleted files
| Path | Reason |
|---|---|
| `src/App.css` | Legacy unused (per earlier analysis) |
| `src/components/ChatMessage.tsx` | Superseded by `UserMessage` + `BrandedArtifactCard` + `NotebookCell` |
| `src/components/ChatInput.tsx` | Superseded by `PromptInput` |
| `src/components/Sidebar.tsx` | Superseded by `LeftRail` + `SessionsList` |
| `src/components/ProgressIndicator.tsx` | Superseded by status bar + plan rail + agents tab |

---

## Task 0: Tooling baseline + preserve in-flight WIP

**Files:**
- Create: `frontend-react/.prettierrc.json`, `frontend-react/eslint.config.js` (replace existing if minimal)
- Create: `frontend-react/vitest.config.ts`, `frontend-react/src/test-setup.ts`
- Modify: `frontend-react/package.json` (add devDeps + scripts)
- Commit untracked WIP first (the user's in-flight `git status` modifications)

- [ ] **Step 1: Commit existing WIP frontend changes**

The repo has uncommitted modifications to ChatMessage/ProgressIndicator/Sidebar/useChat/index.css/api.ts from prior conversation work — those will be replaced by Phase 2 anyway, but we want a clean preserve-point first.

```bash
cd "D:/Git Repos/Analyst_agentic_coder"
git add frontend-react/src/components/ChatMessage.tsx \
        frontend-react/src/components/ProgressIndicator.tsx \
        frontend-react/src/components/Sidebar.tsx \
        frontend-react/src/hooks/useChat.ts \
        frontend-react/src/index.css \
        frontend-react/src/services/api.ts
git commit -m "wip: preserve frontend in-flight changes pre Phase 2 redesign"
```

- [ ] **Step 2: Add devDependencies via package.json edit**

Edit `frontend-react/package.json` — add to `devDependencies` (alphabetize):

```json
"@storybook/addon-essentials": "^8.6.0",
"@storybook/react-vite": "^8.6.0",
"@testing-library/jest-dom": "^6.4.0",
"@testing-library/react": "^16.0.0",
"@testing-library/user-event": "^14.5.0",
"jsdom": "^25.0.0",
"prettier": "^3.3.0",
"vitest": "^2.1.0"
```

Add to `dependencies`:

```json
"@tanstack/react-table": "^8.20.0",
"highlight.js": "^11.10.0",
"immer": "^10.1.0",
"katex": "^0.16.11",
"react-markdown": "^9.0.1",
"rehype-katex": "^7.0.1",
"remark-math": "^6.0.0",
"zod": "^3.23.8",
"zustand": "^5.0.0"
```

Remove from dependencies (already unused):
```
"react-syntax-highlighter"
```

Add to `scripts`:
```json
"test": "vitest run",
"test:watch": "vitest",
"format": "prettier --write src/",
"format:check": "prettier --check src/"
```

- [ ] **Step 3: Install**

```bash
cd "D:/Git Repos/Analyst_agentic_coder/frontend-react"
npm install
```

Expected: clean install. If a peer-dep warning shows, note it but don't act unless install fails.

- [ ] **Step 4: Add Prettier config**

Create `frontend-react/.prettierrc.json`:
```json
{
  "semi": true,
  "singleQuote": true,
  "trailingComma": "all",
  "printWidth": 100,
  "tabWidth": 2,
  "arrowParens": "always"
}
```

- [ ] **Step 5: Add Vitest config**

Create `frontend-react/vitest.config.ts`:
```ts
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test-setup.ts'],
    coverage: {
      provider: 'v8',
      thresholds: { lines: 70, functions: 70 },
    },
  },
});
```

Create `frontend-react/src/test-setup.ts`:
```ts
import '@testing-library/jest-dom/vitest';
```

- [ ] **Step 6: Verify scripts**

```bash
cd "D:/Git Repos/Analyst_agentic_coder/frontend-react"
npm run lint        # existing eslint script — should still pass on existing code
npx tsc --noEmit    # should still pass on existing code
npm test            # vitest with no tests yet — should print "No test files found" not error
```

- [ ] **Step 7: Commit**

```bash
cd "D:/Git Repos/Analyst_agentic_coder"
git add frontend-react/package.json frontend-react/package-lock.json \
        frontend-react/.prettierrc.json \
        frontend-react/vitest.config.ts frontend-react/src/test-setup.ts
git commit -m "chore(frontend): tooling baseline (Vitest, RTL, Prettier, Storybook deps)"
```

---

## Task 1: TS event schema + Zustand store + EventSource service

**Files:**
- Create: `frontend-react/src/types/events.ts`
- Create: `frontend-react/src/types/domain.ts`
- Create: `frontend-react/src/services/eventStream.ts`
- Create: `frontend-react/src/services/eventReducer.ts`
- Create: `frontend-react/src/store/sessionStore.ts`
- Create: `frontend-react/src/services/eventReducer.test.ts`
- Create: `frontend-react/src/store/sessionStore.test.ts`

- [ ] **Step 1: Write event types (mirror backend Pydantic)**

Create `frontend-react/src/types/events.ts`:
```ts
import { z } from 'zod';

const planStep = z.object({ id: z.string(), description: z.string() });

export const eventSchema = z.discriminatedUnion('type', [
  z.object({ type: z.literal('plan.start'),       plan_id: z.string(), steps: z.array(planStep) }),
  z.object({ type: z.literal('plan.step.start'),  step_id: z.string() }),
  z.object({ type: z.literal('plan.step.done'),   step_id: z.string(), duration_ms: z.number() }),

  z.object({ type: z.literal('subagent.spawn'),   agent_id: z.string(), parent_id: z.string().nullable().optional(), kind: z.string(), model: z.string(), prompt: z.string() }),
  z.object({ type: z.literal('subagent.delta'),   agent_id: z.string(), tokens: z.number(), status_text: z.string().nullable().optional() }),
  z.object({ type: z.literal('subagent.done'),    agent_id: z.string(), duration_ms: z.number(), tokens: z.number(), result: z.string().nullable().optional() }),

  z.object({ type: z.literal('tool.start'),       call_id: z.string(), agent_id: z.string(), tool: z.string(), args_redacted: z.record(z.unknown()) }),
  z.object({ type: z.literal('tool.done'),        call_id: z.string(), duration_ms: z.number(), ok: z.boolean(), result_preview: z.string().nullable().optional() }),

  z.object({ type: z.literal('skill'),            name: z.string(), args: z.string().nullable().optional() }),
  z.object({ type: z.literal('memory'),           op: z.enum(['read', 'write']), path: z.string() }),
  z.object({ type: z.literal('wiki'),             op: z.enum(['read', 'ingest', 'lint', 'query']), target: z.string() }),

  z.object({ type: z.literal('source'),           source: z.string(), operation: z.string(), bytes: z.number().nullable().optional() }),

  z.object({ type: z.literal('thinking'),         agent_id: z.string(), tokens: z.number(), preview_text: z.string() }),

  z.object({ type: z.literal('artifact'),         artifact_id: z.string(), kind: z.enum(['chart', 'table', 'code', 'report', 'file']), title: z.string(), source_attribution: z.string(), methodology_id: z.string() }),

  z.object({ type: z.literal('message.delta'),    message_id: z.string(), append_text: z.string() }),
  z.object({ type: z.literal('message.done'),     message_id: z.string() }),

  z.object({ type: z.literal('cost.delta'),       usd: z.number(), tokens_in: z.number(), tokens_out: z.number() }),

  z.object({ type: z.literal('approval'),         approval_id: z.string(), description: z.string(), danger: z.boolean() }),
  z.object({ type: z.literal('error'),            code: z.string(), message: z.string(), recoverable: z.boolean() }),
  z.object({ type: z.literal('done'),             session_id: z.string() }),
]);

export type AnyEvent = z.infer<typeof eventSchema>;
export type EventOf<T extends AnyEvent['type']> = Extract<AnyEvent, { type: T }>;

export function parseEvent(json: string): AnyEvent {
  return eventSchema.parse(JSON.parse(json));
}
```

- [ ] **Step 2: Write domain types**

Create `frontend-react/src/types/domain.ts`:
```ts
export interface Session {
  id: string;
  title: string;
  createdAt: string;
  updatedAt: string;
}

export interface PlanStep {
  id: string;
  description: string;
  status: 'pending' | 'running' | 'done';
  durationMs?: number;
  startedAt?: number;
}

export interface AgentState {
  id: string;
  parentId?: string;
  kind: string;
  model: string;
  status: 'running' | 'queued' | 'done';
  tokens: number;
  durationMs?: number;
  result?: string;
  toolsUsed: string[];
}

export interface Artifact {
  id: string;
  kind: 'chart' | 'table' | 'code' | 'report' | 'file';
  title: string;
  sourceAttribution: string;
  methodologyId: string;
  createdAt: number;
}

export interface SourceAccess {
  source: string;
  callCount: number;
  lastOp?: string;
}

export interface ActivityEntry {
  id: number;
  ts: number;
  category: 'plan' | 'tool' | 'subagent' | 'skill' | 'memory' | 'source' | 'message' | 'thinking' | 'error' | 'other';
  text: string;
  meta?: Record<string, unknown>;
}

export interface UserMessage { kind: 'user'; id: string; text: string; ts: number; }
export interface AssistantMessage { kind: 'assistant'; id: string; text: string; ts: number; }
export interface ArtifactMessage { kind: 'artifact'; id: string; artifact: Artifact; ts: number; }
export interface ThinkingMessage { kind: 'thinking'; id: string; tokens: number; preview: string; ts: number; }
export interface SubAgentMessage { kind: 'subagent'; id: string; agentId: string; subKind: string; status: AgentState['status']; statusText?: string; ts: number; }

export type ChatTurn = UserMessage | AssistantMessage | ArtifactMessage | ThinkingMessage | SubAgentMessage;
```

- [ ] **Step 3: Write the eventReducer (TDD)**

Create `frontend-react/src/services/eventReducer.test.ts`:
```ts
import { describe, expect, it } from 'vitest';
import { applyEvent, type SessionState, initialSessionState } from './eventReducer';

const baseState = (): SessionState => ({ ...initialSessionState() });

describe('applyEvent', () => {
  it('plan.start populates plan steps as pending', () => {
    const next = applyEvent(baseState(), {
      type: 'plan.start',
      plan_id: 'p1',
      steps: [{ id: 's1', description: 'load' }, { id: 's2', description: 'compute' }],
    });
    expect(next.plan.length).toBe(2);
    expect(next.plan[0]).toMatchObject({ id: 's1', status: 'pending' });
  });

  it('plan.step.start marks the step running', () => {
    let s = baseState();
    s = applyEvent(s, { type: 'plan.start', plan_id: 'p', steps: [{ id: 's1', description: 'x' }] });
    s = applyEvent(s, { type: 'plan.step.start', step_id: 's1' });
    expect(s.plan[0].status).toBe('running');
  });

  it('plan.step.done marks the step done with duration', () => {
    let s = baseState();
    s = applyEvent(s, { type: 'plan.start', plan_id: 'p', steps: [{ id: 's1', description: 'x' }] });
    s = applyEvent(s, { type: 'plan.step.done', step_id: 's1', duration_ms: 50 });
    expect(s.plan[0]).toMatchObject({ status: 'done', durationMs: 50 });
  });

  it('subagent.spawn adds an agent in running state', () => {
    const next = applyEvent(baseState(), {
      type: 'subagent.spawn',
      agent_id: 'a1',
      kind: 'researcher',
      model: 'sonnet',
      prompt: 'x',
    });
    expect(next.agents['a1']).toMatchObject({ id: 'a1', status: 'running', kind: 'researcher' });
  });

  it('subagent.done marks the agent done', () => {
    let s = baseState();
    s = applyEvent(s, { type: 'subagent.spawn', agent_id: 'a1', kind: 'r', model: 'm', prompt: 'p' });
    s = applyEvent(s, { type: 'subagent.done', agent_id: 'a1', duration_ms: 100, tokens: 50, result: 'ok' });
    expect(s.agents['a1']).toMatchObject({ status: 'done', durationMs: 100, tokens: 50 });
  });

  it('tool.start + tool.done append activity entries', () => {
    let s = baseState();
    s = applyEvent(s, { type: 'tool.start', call_id: 'c1', agent_id: 'a', tool: 'Read', args_redacted: { path: 'x' } });
    s = applyEvent(s, { type: 'tool.done', call_id: 'c1', duration_ms: 5, ok: true });
    const tools = s.activity.filter((a) => a.category === 'tool');
    expect(tools.length).toBeGreaterThanOrEqual(1);
  });

  it('source events update sources map', () => {
    let s = baseState();
    s = applyEvent(s, { type: 'source', source: 'Bloomberg', operation: 'HIST_TRR' });
    s = applyEvent(s, { type: 'source', source: 'Bloomberg', operation: 'HIST_TRR' });
    expect(s.sources['Bloomberg'].callCount).toBe(2);
  });

  it('artifact event appends to artifacts and chat as artifact turn', () => {
    const ev = { type: 'artifact', artifact_id: 'a1', kind: 'chart', title: 'Equity', source_attribution: 'Bloomberg', methodology_id: 'm1' } as const;
    const next = applyEvent(baseState(), ev);
    expect(next.artifacts.length).toBe(1);
    expect(next.chat.some((t) => t.kind === 'artifact')).toBe(true);
  });

  it('message.delta appends text to assistant turn', () => {
    let s = baseState();
    s = applyEvent(s, { type: 'message.delta', message_id: 'm1', append_text: 'Hello' });
    s = applyEvent(s, { type: 'message.delta', message_id: 'm1', append_text: ', world' });
    const msg = s.chat.find((t) => t.kind === 'assistant') as { text: string } | undefined;
    expect(msg?.text).toBe('Hello, world');
  });

  it('done sets streaming false', () => {
    const next = applyEvent({ ...baseState(), isStreaming: true }, { type: 'done', session_id: 's1' });
    expect(next.isStreaming).toBe(false);
  });

  it('error event sets error and stops streaming', () => {
    const next = applyEvent(baseState(), { type: 'error', code: 'TIMEOUT', message: 'x', recoverable: true });
    expect(next.error).toMatchObject({ code: 'TIMEOUT' });
    expect(next.isStreaming).toBe(false);
  });
});
```

Create `frontend-react/src/services/eventReducer.ts`:
```ts
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
```

- [ ] **Step 4: Run reducer tests**

```bash
cd "D:/Git Repos/Analyst_agentic_coder/frontend-react"
npm test -- src/services/eventReducer.test.ts
```

Expected: 10 PASSED.

- [ ] **Step 5: Write Zustand store + tests**

Create `frontend-react/src/store/sessionStore.test.ts`:
```ts
import { describe, expect, it, beforeEach } from 'vitest';
import { useSessionStore } from './sessionStore';

describe('sessionStore', () => {
  beforeEach(() => useSessionStore.getState().reset());

  it('resets to initial', () => {
    const s = useSessionStore.getState();
    expect(s.session.chat.length).toBe(0);
    expect(s.session.isStreaming).toBe(false);
  });

  it('handle event mutates session via reducer', () => {
    useSessionStore.getState().handleEvent({ type: 'plan.start', plan_id: 'p', steps: [{ id: 's1', description: 'x' }] });
    expect(useSessionStore.getState().session.plan.length).toBe(1);
  });

  it('appendUser adds user turn and starts streaming', () => {
    useSessionStore.getState().appendUser('hi');
    const s = useSessionStore.getState().session;
    expect(s.chat[0]).toMatchObject({ kind: 'user', text: 'hi' });
    expect(s.isStreaming).toBe(true);
  });
});
```

Create `frontend-react/src/store/sessionStore.ts`:
```ts
import { create } from 'zustand';
import { applyEvent, appendUserMessage, initialSessionState, type SessionState } from '../services/eventReducer';
import type { AnyEvent } from '../types/events';

export interface SessionStore {
  sessionId: string | null;
  session: SessionState;
  setSessionId(id: string | null): void;
  handleEvent(ev: AnyEvent): void;
  appendUser(text: string): void;
  reset(): void;
}

export const useSessionStore = create<SessionStore>((set) => ({
  sessionId: null,
  session: initialSessionState(),
  setSessionId: (id) => set({ sessionId: id }),
  handleEvent: (ev) => set((s) => ({ session: applyEvent(s.session, ev) })),
  appendUser: (text) => set((s) => ({ session: appendUserMessage(s.session, text) })),
  reset: () => set({ sessionId: null, session: initialSessionState() }),
}));
```

- [ ] **Step 6: Run store tests**

```bash
cd "D:/Git Repos/Analyst_agentic_coder/frontend-react"
npm test -- src/store/sessionStore.test.ts
```

Expected: 3 PASSED.

- [ ] **Step 7: Write EventSource service**

Create `frontend-react/src/services/eventStream.ts`:
```ts
import { parseEvent } from '../types/events';
import type { AnyEvent } from '../types/events';

export interface EventStreamHandle {
  close(): void;
}

export interface EventStreamOptions {
  url: string;
  onEvent: (ev: AnyEvent) => void;
  onError?: (err: Event) => void;
  onOpen?: () => void;
  lastEventId?: string;
}

/**
 * Wraps EventSource. Browser auto-reconnects with Last-Event-ID; we just
 * surface validated events. Malformed events are logged and dropped.
 */
export function openEventStream(opts: EventStreamOptions): EventStreamHandle {
  const es = new EventSource(opts.url, { withCredentials: false });

  es.onopen = () => opts.onOpen?.();
  es.onerror = (e) => opts.onError?.(e);

  es.addEventListener('message', (msg: MessageEvent<string>) => {
    try {
      const ev = parseEvent(msg.data);
      opts.onEvent(ev);
    } catch (err) {
      console.warn('[eventStream] dropped malformed event', err, msg.data);
    }
  });

  // SSE supports custom events; the backend names them by event type. Catch them all.
  // (browser EventSource fires both `message` and the named-event handlers; we listen
  // generically via a passthrough.)
  const types: AnyEvent['type'][] = [
    'plan.start', 'plan.step.start', 'plan.step.done',
    'subagent.spawn', 'subagent.delta', 'subagent.done',
    'tool.start', 'tool.done',
    'skill', 'memory', 'wiki', 'source', 'thinking',
    'artifact', 'message.delta', 'message.done',
    'cost.delta', 'approval', 'error', 'done',
  ];
  for (const t of types) {
    es.addEventListener(t, (msg) => {
      const e = msg as MessageEvent<string>;
      try {
        opts.onEvent(parseEvent(e.data));
      } catch (err) {
        console.warn('[eventStream] dropped malformed event', err, e.data);
      }
    });
  }

  return { close: () => es.close() };
}
```

- [ ] **Step 8: Update services/api.ts**

Read current file, then modify:

```ts
// frontend-react/src/services/api.ts (replace fully)
import axios from 'axios';

const BASE = import.meta.env.VITE_API_URL || '';

const http = axios.create({ baseURL: BASE, timeout: 30_000 });

export interface ChatResponse {
  session_id: string;
  event_stream_url: string;
}

export async function postChat(message: string, sessionId: string | null, workspacePath?: string): Promise<ChatResponse> {
  const { data } = await http.post<ChatResponse>('/api/chat', {
    message,
    session_id: sessionId,
    workspace_path: workspacePath,
  });
  return data;
}

export async function listSessions() {
  const { data } = await http.get('/api/sessions');
  return data.sessions ?? data;
}

export async function deleteSession(id: string) {
  await http.delete(`/api/sessions/${id}`);
}

export async function getHistory(id: string) {
  const { data } = await http.get(`/api/session/${id}/history`);
  return data;
}

export function eventStreamUrl(sessionId: string): string {
  return `${BASE}/api/chat/stream/${sessionId}`;
}
```

- [ ] **Step 9: Run all tests + typecheck + lint**

```bash
cd "D:/Git Repos/Analyst_agentic_coder/frontend-react"
npm test
npx tsc --noEmit
npm run lint
```

Expected: 13 tests pass, no type errors, lint clean (existing warnings on touched files OK).

- [ ] **Step 10: Commit**

```bash
cd "D:/Git Repos/Analyst_agentic_coder"
git add frontend-react/src/types/events.ts frontend-react/src/types/domain.ts \
        frontend-react/src/services/eventStream.ts frontend-react/src/services/eventReducer.ts \
        frontend-react/src/services/eventReducer.test.ts \
        frontend-react/src/store/sessionStore.ts frontend-react/src/store/sessionStore.test.ts \
        frontend-react/src/services/api.ts
git commit -m "feat(frontend): event types, Zustand store, EventSource service, reducer"
```

---

## Task 2: Tailwind brand tokens + Inter + KaTeX import

**Files:**
- Modify: `frontend-react/tailwind.config.js`
- Modify: `frontend-react/src/index.css`

- [ ] **Step 1: Modify tailwind.config.js**

Read the current file first. Add to the existing `theme.extend.colors` (do not remove existing colors — add):

```js
brand: {
  900: '#0a1929',
  800: '#0f1f3a',
  700: '#1e293b',
},
gold: {
  500: '#d4a017',
  600: '#c49014',
  700: '#b8860b',
},
```

Add to `theme.extend.fontFamily`:

```js
sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
mono: ['"JetBrains Mono"', 'ui-monospace', 'SFMono-Regular', 'monospace'],
```

- [ ] **Step 2: Modify src/index.css**

Read the current file. Replace its content with:

```css
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
@import 'katex/dist/katex.min.css';

@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  html, body, #root {
    height: 100%;
    margin: 0;
    font-family: theme('fontFamily.sans');
    color: theme('colors.slate.900');
    background: theme('colors.slate.50');
    -webkit-font-smoothing: antialiased;
  }
  code, pre {
    font-family: theme('fontFamily.mono');
  }
}
```

(If Tailwind v4 uses `@import "tailwindcss"` syntax instead of `@tailwind` directives in this project, preserve that — read the file before editing. The `@import` for Inter and KaTeX go at the top either way.)

- [ ] **Step 3: Verify build still works**

```bash
cd "D:/Git Repos/Analyst_agentic_coder/frontend-react"
npm run build
```

Expected: build succeeds. Bundle may grow slightly (KaTeX CSS).

- [ ] **Step 4: Commit**

```bash
cd "D:/Git Repos/Analyst_agentic_coder"
git add frontend-react/tailwind.config.js frontend-react/src/index.css
git commit -m "feat(frontend): Quant Console brand tokens (navy/gold) + Inter + KaTeX"
```

---

## Task 3: Frame components + ThreePaneLayout

**Files:**
- Create: `frontend-react/src/components/frame/{BrandBar,ComplianceBar,StatusBar,ComplianceFooter}.tsx`
- Create: `frontend-react/src/components/layout/ThreePaneLayout.tsx`

(All visual; no unit tests. Visual verification via build + manual smoke in Task 7.)

- [ ] **Step 1: Create BrandBar.tsx**

```tsx
// frontend-react/src/components/frame/BrandBar.tsx
export interface BrandBarProps {
  userIdentity?: string;
  userTier?: string;
  rmName?: string;
}

export function BrandBar({ userIdentity, userTier, rmName }: BrandBarProps) {
  return (
    <header className="bg-gradient-to-b from-brand-900 to-brand-800 text-slate-200 px-5 py-3 flex items-center gap-5 text-[11px]">
      <div className="flex items-center gap-2 font-bold tracking-wider text-[14px] text-white">
        <span className="w-5 h-5 rounded bg-gradient-to-br from-gold-500 to-gold-700 text-brand-900 flex items-center justify-center font-black text-[11px]">
          Q
        </span>
        Quant Console
      </div>
      {(userIdentity || rmName) && (
        <div className="ml-auto text-right text-[10px] leading-tight">
          {userIdentity && (
            <div>
              <strong className="text-white">{userIdentity}</strong>
              {userTier && <> · {userTier}</>}
            </div>
          )}
          {rmName && (
            <div>RM: <span className="text-gold-500 cursor-pointer">{rmName}</span></div>
          )}
        </div>
      )}
    </header>
  );
}
```

- [ ] **Step 2: Create ComplianceBar.tsx**

```tsx
// frontend-react/src/components/frame/ComplianceBar.tsx
export interface ComplianceBarProps {
  entitlements?: string;
  mnpiOn?: boolean;
  lastRefresh?: string;
}

export function ComplianceBar({ entitlements, mnpiOn, lastRefresh }: ComplianceBarProps) {
  return (
    <div className="bg-amber-50 border-b border-amber-300 px-5 py-1 text-[10px] text-amber-900 flex gap-3.5 flex-wrap items-center">
      <span>⚠ Institutional clients only · Not investment advice · See disclosures</span>
      {entitlements && (
        <span className="bg-white border border-amber-300 rounded-full px-2 py-0.5 text-[9px]">
          Entitlements: {entitlements}
        </span>
      )}
      {mnpiOn !== undefined && (
        <span className="bg-white border border-amber-300 rounded-full px-2 py-0.5 text-[9px]">
          MNPI walls: {mnpiOn ? 'ON' : 'OFF'}
        </span>
      )}
      {lastRefresh && <span className="ml-auto">{lastRefresh}</span>}
    </div>
  );
}
```

- [ ] **Step 3: Create StatusBar.tsx**

```tsx
// frontend-react/src/components/frame/StatusBar.tsx
import { useSessionStore } from '../../store/sessionStore';

export function StatusBar() {
  const sessionId = useSessionStore((s) => s.sessionId);
  const session = useSessionStore((s) => s.session);

  const planTotal = session.plan.length;
  const planDone = session.plan.filter((p) => p.status === 'done').length;
  const agentsRunning = Object.values(session.agents).filter((a) => a.status === 'running').length;
  const agentsTotal = Object.keys(session.agents).length;
  const sources = Object.keys(session.sources);

  return (
    <div className="bg-slate-50 border-b border-slate-200 px-5 py-2 flex gap-3 items-center text-[11px] text-slate-600">
      <span className="bg-white border border-slate-200 rounded-full px-2.5 py-0.5">
        Session: <strong className="text-slate-900">{sessionId ?? '—'}</strong>
      </span>
      {planTotal > 0 && (
        <span className="bg-white border border-slate-200 rounded-full px-2.5 py-0.5 text-emerald-600">
          ● Plan {planDone}/{planTotal} {session.isStreaming ? '· running' : ''}
        </span>
      )}
      {agentsTotal > 0 && (
        <span className="bg-white border border-slate-200 rounded-full px-2.5 py-0.5">
          Agents: {agentsTotal} · {agentsRunning} running
        </span>
      )}
      {sources.length > 0 && (
        <span className="bg-white border border-slate-200 rounded-full px-2.5 py-0.5">
          Sources: {sources.join(' · ')}
        </span>
      )}
      <span className="ml-auto cursor-pointer">⌘K</span>
      {session.isStreaming && (
        <span className="bg-white border border-slate-200 rounded-full px-2.5 py-0.5 text-red-600 cursor-pointer">
          Halt
        </span>
      )}
    </div>
  );
}
```

- [ ] **Step 4: Create ComplianceFooter.tsx**

```tsx
// frontend-react/src/components/frame/ComplianceFooter.tsx
export interface ComplianceFooterProps {
  auditId?: string;
  rmName?: string;
}

export function ComplianceFooter({ auditId, rmName }: ComplianceFooterProps) {
  return (
    <footer className="bg-brand-900 text-slate-400 px-5 py-2.5 text-[9px] leading-relaxed">
      <strong className="text-slate-300">Disclosures.</strong> Provided by the institution for institutional clients only. Not investment advice. AI-generated; verify before acting. Sources: Bloomberg, S&P Global, MSCI, FactSet, GIR Research, internal models.
      {auditId && <> Audit ID: <strong className="text-slate-300">{auditId}</strong>.</>}
      {' '}Support: clients@institution{rmName && <> · RM: {rmName}</>}.
    </footer>
  );
}
```

- [ ] **Step 5: Create ThreePaneLayout.tsx**

```tsx
// frontend-react/src/components/layout/ThreePaneLayout.tsx
import type { ReactNode } from 'react';

export interface ThreePaneLayoutProps {
  topBar: ReactNode;
  complianceBar: ReactNode;
  statusBar: ReactNode;
  left: ReactNode;
  center: ReactNode;
  right: ReactNode;
  prompt: ReactNode;
  footer: ReactNode;
}

export function ThreePaneLayout({ topBar, complianceBar, statusBar, left, center, right, prompt, footer }: ThreePaneLayoutProps) {
  return (
    <div className="h-screen w-screen flex flex-col bg-white text-slate-900">
      {topBar}
      {complianceBar}
      {statusBar}
      <div className="flex-1 grid grid-cols-[220px_1fr_360px] min-h-0">
        <aside className="bg-slate-50 border-r border-slate-200 overflow-y-auto p-3">{left}</aside>
        <main className="bg-white overflow-y-auto p-4">{center}</main>
        <aside className="bg-slate-50 border-l border-slate-200 overflow-y-auto p-3">{right}</aside>
      </div>
      <div className="border-t border-slate-200 px-5 py-2.5 bg-white">{prompt}</div>
      {footer}
    </div>
  );
}
```

- [ ] **Step 6: Verify build + typecheck**

```bash
cd "D:/Git Repos/Analyst_agentic_coder/frontend-react"
npx tsc --noEmit
npm run build
```

Expected: clean.

- [ ] **Step 7: Commit**

```bash
cd "D:/Git Repos/Analyst_agentic_coder"
git add frontend-react/src/components/frame/ frontend-react/src/components/layout/
git commit -m "feat(frontend): brand frame (BrandBar, ComplianceBar, StatusBar, Footer) + ThreePaneLayout"
```

---

## Task 4: Left rail components

**Files:**
- Create: `frontend-react/src/components/left/{LeftRail,SessionsList,WorkspaceTree,KnowledgePanel}.tsx`

- [ ] **Step 1: Create LeftRail.tsx**

```tsx
// frontend-react/src/components/left/LeftRail.tsx
import { SessionsList } from './SessionsList';
import { WorkspaceTree } from './WorkspaceTree';
import { KnowledgePanel } from './KnowledgePanel';

export function LeftRail() {
  return (
    <div className="flex flex-col gap-4 text-[11px]">
      <SessionsList />
      <WorkspaceTree />
      <KnowledgePanel />
    </div>
  );
}

export function Label({ children }: { children: React.ReactNode }) {
  return <div className="text-[9px] uppercase tracking-wider text-slate-400 mb-1">{children}</div>;
}
```

- [ ] **Step 2: Create SessionsList.tsx**

```tsx
// frontend-react/src/components/left/SessionsList.tsx
import { useEffect, useState } from 'react';
import { listSessions, deleteSession } from '../../services/api';
import { useSessionStore } from '../../store/sessionStore';
import { Label } from './LeftRail';

interface ApiSession { id: string; created_at: string; }

export function SessionsList() {
  const [sessions, setSessions] = useState<ApiSession[]>([]);
  const currentId = useSessionStore((s) => s.sessionId);
  const setSessionId = useSessionStore((s) => s.setSessionId);
  const reset = useSessionStore((s) => s.reset);

  const refresh = async () => {
    try { setSessions(await listSessions()); } catch { /* tolerate */ }
  };

  useEffect(() => { refresh(); }, []);

  return (
    <div>
      <Label>Sessions</Label>
      <div>
        {sessions.map((s) => (
          <div
            key={s.id}
            onClick={() => setSessionId(s.id)}
            className={`px-1 py-0.5 rounded cursor-pointer ${currentId === s.id ? 'bg-indigo-50 text-brand-900 font-semibold' : 'text-slate-600 hover:bg-slate-100'}`}
          >
            ▸ {s.id.slice(0, 12)}…
          </div>
        ))}
        <div onClick={() => { reset(); refresh(); }} className="px-1 py-0.5 text-slate-400 cursor-pointer hover:text-slate-600">+ New session</div>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Create WorkspaceTree.tsx (stub for v1 — populates from API later)**

```tsx
// frontend-react/src/components/left/WorkspaceTree.tsx
import { Label } from './LeftRail';
import { useSessionStore } from '../../store/sessionStore';

export function WorkspaceTree() {
  const session = useSessionStore((s) => s.session);
  return (
    <div>
      <Label>Workspace</Label>
      <div className="text-slate-600">
        {session.artifacts.length > 0 ? (
          <>
            <div>▾ artifacts/ <span className="text-slate-400">{session.artifacts.length}</span></div>
            {session.artifacts.slice(0, 5).map((a) => (
              <div key={a.id} className="pl-3.5 truncate" title={a.title}>{a.title}</div>
            ))}
          </>
        ) : (
          <div className="text-slate-400 italic">No workspace files yet</div>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Create KnowledgePanel.tsx**

```tsx
// frontend-react/src/components/left/KnowledgePanel.tsx
import { Label } from './LeftRail';

export function KnowledgePanel() {
  return (
    <div>
      <Label>Knowledge</Label>
      <div className="text-[10px] text-slate-600">
        <div>📔 Wiki ready</div>
        <div>🧠 Memory ready</div>
      </div>
    </div>
  );
}
```

- [ ] **Step 5: Verify**

```bash
cd "D:/Git Repos/Analyst_agentic_coder/frontend-react"
npx tsc --noEmit
```

Expected: clean.

- [ ] **Step 6: Commit**

```bash
cd "D:/Git Repos/Analyst_agentic_coder"
git add frontend-react/src/components/left/
git commit -m "feat(frontend): left rail (Sessions, WorkspaceTree, Knowledge)"
```

---

## Task 5: Center pane components

**Files:**
- Create: `frontend-react/src/components/center/{ChatStream,UserMessage,ThinkingBlock,NotebookCell,BrandedArtifactCard,SubAgentIndicator,PlanRail}.tsx`
- Create: `frontend-react/src/components/renderers/{MarkdownWithLatex,CodeBlock,DataTable,Chart}.tsx`

- [ ] **Step 1: Create renderers**

```tsx
// frontend-react/src/components/renderers/MarkdownWithLatex.tsx
import ReactMarkdown from 'react-markdown';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';

export function MarkdownWithLatex({ children }: { children: string }) {
  return (
    <div className="prose prose-sm max-w-none">
      <ReactMarkdown remarkPlugins={[remarkMath]} rehypePlugins={[rehypeKatex]}>
        {children}
      </ReactMarkdown>
    </div>
  );
}
```

```tsx
// frontend-react/src/components/renderers/CodeBlock.tsx
import hljs from 'highlight.js/lib/core';
import python from 'highlight.js/lib/languages/python';
import typescript from 'highlight.js/lib/languages/typescript';
import javascript from 'highlight.js/lib/languages/javascript';
import bash from 'highlight.js/lib/languages/bash';
import 'highlight.js/styles/github-dark.css';

hljs.registerLanguage('python', python);
hljs.registerLanguage('typescript', typescript);
hljs.registerLanguage('javascript', javascript);
hljs.registerLanguage('bash', bash);

export function CodeBlock({ code, language = 'python' }: { code: string; language?: string }) {
  const html = hljs.getLanguage(language) ? hljs.highlight(code, { language }).value : code;
  return (
    <pre className="bg-slate-900 text-slate-100 font-mono text-[10px] px-3 py-2 leading-relaxed overflow-x-auto">
      <code dangerouslySetInnerHTML={{ __html: html }} />
    </pre>
  );
}
```

```tsx
// frontend-react/src/components/renderers/DataTable.tsx
// Phase 2: minimal; full sortable/filterable in Phase 3.
export interface DataTableProps {
  columns: string[];
  rows: (string | number)[][];
}

export function DataTable({ columns, rows }: DataTableProps) {
  return (
    <table className="w-full border-collapse font-mono text-[10px]">
      <thead>
        <tr className="bg-slate-50">
          {columns.map((c) => (
            <th key={c} className="border border-slate-200 px-2 py-1 text-left text-slate-600 font-semibold">{c}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((r, i) => (
          <tr key={i}>
            {r.map((cell, j) => (
              <td key={j} className="border border-slate-200 px-2 py-0.5 text-right first:text-left first:text-slate-600">{cell}</td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}
```

```tsx
// frontend-react/src/components/renderers/Chart.tsx
// Phase 2: stub — concrete library chosen in Phase 3.
export function Chart({ title }: { title: string }) {
  return (
    <div className="h-24 bg-gradient-to-b from-emerald-50 to-white rounded flex items-center justify-center text-[10px] text-slate-500 italic">
      Chart placeholder · {title}
    </div>
  );
}
```

- [ ] **Step 2: Create center turn components**

```tsx
// frontend-react/src/components/center/UserMessage.tsx
export function UserMessage({ text }: { text: string }) {
  return (
    <div className="bg-slate-100 rounded-[12px_12px_4px_12px] px-3 py-2 max-w-[75%] ml-auto text-[12px] my-2">
      {text}
    </div>
  );
}
```

```tsx
// frontend-react/src/components/center/ThinkingBlock.tsx
import { useState } from 'react';

export function ThinkingBlock({ tokens, preview }: { tokens: number; preview: string }) {
  const [open, setOpen] = useState(false);
  return (
    <div onClick={() => setOpen(!open)} className="bg-amber-100 rounded px-3 py-1.5 text-[10px] text-amber-900 my-2 cursor-pointer">
      <span>{open ? '▾' : '▸'} Methodology · {tokens.toLocaleString()} reasoning tokens</span>
      {open && <div className="mt-2 text-amber-800">{preview}</div>}
    </div>
  );
}
```

```tsx
// frontend-react/src/components/center/NotebookCell.tsx
import type { ReactNode } from 'react';
import { CodeBlock } from '../renderers/CodeBlock';

export interface NotebookCellProps {
  title: string;
  language?: string;
  code: string;
  output?: ReactNode;
}

export function NotebookCell({ title, language, code, output }: NotebookCellProps) {
  return (
    <div className="border border-slate-200 rounded-lg my-3 overflow-hidden">
      <div className="bg-slate-50 px-2.5 py-1 font-mono text-[10px] text-slate-600 border-b border-slate-200">{title}</div>
      <CodeBlock code={code} language={language} />
      {output && <div className="px-2.5 py-2 bg-white">{output}</div>}
    </div>
  );
}
```

```tsx
// frontend-react/src/components/center/BrandedArtifactCard.tsx
import type { Artifact } from '../../types/domain';
import type { ReactNode } from 'react';

export interface BrandedArtifactCardProps {
  artifact: Artifact;
  body: ReactNode;
}

export function BrandedArtifactCard({ artifact, body }: BrandedArtifactCardProps) {
  return (
    <div className="border border-slate-200 rounded-lg my-3 overflow-hidden">
      <div className="bg-gradient-to-b from-brand-900 to-brand-800 text-white px-3 py-2 flex justify-between text-[10px]">
        <span><strong>{artifact.title}</strong></span>
        <span className="text-gold-500 font-semibold tracking-wider">Q · QUANT CONSOLE</span>
      </div>
      <div className="p-3">{body}</div>
      <div className="text-[9px] text-slate-400 px-3 py-1.5 bg-slate-50 border-t border-slate-200 flex justify-between">
        <span>Source: {artifact.sourceAttribution}</span>
        <span className="text-sky-700 cursor-pointer">▸ How this was made</span>
      </div>
    </div>
  );
}
```

```tsx
// frontend-react/src/components/center/SubAgentIndicator.tsx
import type { SubAgentMessage } from '../../types/domain';

const palette = {
  researcher: { bg: 'bg-sky-50',    border: 'border-sky-500',    name: 'text-sky-800' },
  verifier:   { bg: 'bg-fuchsia-50', border: 'border-purple-500', name: 'text-purple-700' },
  explore:    { bg: 'bg-emerald-50', border: 'border-emerald-500', name: 'text-emerald-700' },
  plan:       { bg: 'bg-amber-50',   border: 'border-amber-500',  name: 'text-amber-800' },
  general:    { bg: 'bg-slate-100',  border: 'border-slate-400',  name: 'text-slate-700' },
} as const;

function colorsFor(kind: string) {
  return (palette as Record<string, typeof palette.general>)[kind] ?? palette.general;
}

export function SubAgentIndicator({ msg }: { msg: SubAgentMessage }) {
  const c = colorsFor(msg.subKind);
  return (
    <div className={`${c.bg} ${c.border} border-l-[3px] rounded px-3 py-2 text-[10px] my-2`}>
      <strong className={c.name}>↳ {msg.subKind} subagent</strong> · {msg.status}
      {msg.statusText && <> · {msg.statusText}</>}
    </div>
  );
}
```

```tsx
// frontend-react/src/components/center/PlanRail.tsx
import { useSessionStore } from '../../store/sessionStore';

export function PlanRail() {
  const plan = useSessionStore((s) => s.session.plan);
  const agents = useSessionStore((s) => s.session.agents);
  if (plan.length === 0) return null;

  const done = plan.filter((p) => p.status === 'done').length;
  const subAgentCount = Object.keys(agents).length;
  return (
    <div className="my-3 text-[11px] text-slate-600">
      <strong className="text-slate-900">Plan</strong> — {done}/{plan.length} steps · {subAgentCount} sub-agents
    </div>
  );
}
```

```tsx
// frontend-react/src/components/center/ChatStream.tsx
import { useSessionStore } from '../../store/sessionStore';
import { UserMessage } from './UserMessage';
import { ThinkingBlock } from './ThinkingBlock';
import { BrandedArtifactCard } from './BrandedArtifactCard';
import { SubAgentIndicator } from './SubAgentIndicator';
import { PlanRail } from './PlanRail';
import { MarkdownWithLatex } from '../renderers/MarkdownWithLatex';

export function ChatStream() {
  const chat = useSessionStore((s) => s.session.chat);
  return (
    <div>
      {chat.map((turn) => {
        switch (turn.kind) {
          case 'user':
            return <UserMessage key={turn.id} text={turn.text} />;
          case 'assistant':
            return (
              <div key={turn.id} className="my-2 text-[12px]">
                <MarkdownWithLatex>{turn.text}</MarkdownWithLatex>
              </div>
            );
          case 'thinking':
            return <ThinkingBlock key={turn.id} tokens={turn.tokens} preview={turn.preview} />;
          case 'artifact':
            return (
              <BrandedArtifactCard
                key={turn.id}
                artifact={turn.artifact}
                body={<div className="text-[10px] text-slate-500 italic">Artifact rendering coming in Phase 3.</div>}
              />
            );
          case 'subagent':
            return <SubAgentIndicator key={turn.id} msg={turn} />;
        }
      })}
      <PlanRail />
    </div>
  );
}
```

- [ ] **Step 3: Verify**

```bash
cd "D:/Git Repos/Analyst_agentic_coder/frontend-react"
npx tsc --noEmit
```

Expected: clean.

- [ ] **Step 4: Commit**

```bash
cd "D:/Git Repos/Analyst_agentic_coder"
git add frontend-react/src/components/center/ frontend-react/src/components/renderers/
git commit -m "feat(frontend): center pane (ChatStream, NotebookCell, BrandedArtifactCard, etc.) + renderers"
```

---

## Task 6: Right rail with tabs

**Files:**
- Create: `frontend-react/src/components/right/RightRail.tsx`
- Create: `frontend-react/src/components/right/tabs/{PlanTab,AgentsTab,ActivityTab,ArtifactsTab,ReportTab,AuditTab}.tsx`

- [ ] **Step 1: Create tabs**

```tsx
// frontend-react/src/components/right/tabs/PlanTab.tsx
import { useSessionStore } from '../../../store/sessionStore';

export function PlanTab() {
  const plan = useSessionStore((s) => s.session.plan);
  if (plan.length === 0) return <div className="text-[10px] text-slate-400 italic">No active plan.</div>;
  return (
    <div className="border-l-2 border-slate-200 pl-3.5 ml-1">
      {plan.map((step) => (
        <div key={step.id} className={`py-1 text-[10px] relative ${step.status === 'done' ? 'text-emerald-600' : step.status === 'running' ? 'text-slate-900 font-semibold' : 'text-slate-500'}`}>
          <span className={`absolute -left-[19px] top-2 w-1.5 h-1.5 rounded-full ${step.status === 'done' ? 'bg-emerald-600' : step.status === 'running' ? 'bg-amber-500 ring-2 ring-amber-200' : 'bg-slate-200'}`} />
          {step.description} {step.durationMs && <span className="text-slate-400">· {step.durationMs}ms</span>}
        </div>
      ))}
    </div>
  );
}
```

```tsx
// frontend-react/src/components/right/tabs/AgentsTab.tsx
import { useSessionStore } from '../../../store/sessionStore';

export function AgentsTab() {
  const agents = useSessionStore((s) => s.session.agents);
  const sources = useSessionStore((s) => s.session.sources);
  const list = Object.values(agents);
  return (
    <>
      <div className="text-[9px] uppercase tracking-wider text-slate-400 mt-1.5 mb-1">Active agent team</div>
      {list.length === 0 && <div className="text-[10px] text-slate-400 italic">No agents yet.</div>}
      {list.map((a) => (
        <div key={a.id} className={`bg-white border border-slate-200 rounded p-2 mb-1.5 border-l-[3px] ${a.status === 'running' ? 'border-l-sky-500' : a.status === 'done' ? 'border-l-emerald-600' : 'border-l-slate-300 opacity-70'}`}>
          <div className="text-[10px] text-slate-900 font-semibold">{a.id === 'main' ? 'main' : `↳ ${a.kind}`}</div>
          <div className="text-[9px] text-slate-400 mt-0.5">{a.model} · {a.tokens} tokens{a.durationMs ? ` · ${a.durationMs}ms` : ''}</div>
          {a.toolsUsed.length > 0 && <div className="text-[9px] text-slate-600 mt-0.5">tools: {a.toolsUsed.join(', ')}</div>}
        </div>
      ))}
      <div className="text-[9px] uppercase tracking-wider text-slate-400 mt-3.5 mb-1">Sources accessed</div>
      <div className="text-[10px] text-slate-600">
        {Object.values(sources).map((s) => (
          <div key={s.source}>● {s.source} <span className="text-slate-400">{s.callCount} calls</span></div>
        ))}
        {Object.keys(sources).length === 0 && <div className="text-slate-400 italic">none</div>}
      </div>
    </>
  );
}
```

```tsx
// frontend-react/src/components/right/tabs/ActivityTab.tsx
import { useSessionStore } from '../../../store/sessionStore';

const colorByCategory: Record<string, string> = {
  plan: 'text-slate-600 font-semibold',
  tool: 'text-sky-600',
  subagent: 'text-purple-500',
  skill: 'text-emerald-600',
  memory: 'text-amber-600',
  source: 'text-red-600',
  message: 'text-slate-700',
  thinking: 'text-amber-700',
  error: 'text-red-700 font-semibold',
  other: 'text-slate-500',
};

function formatTs(ts: number): string {
  const d = new Date(ts);
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
}

export function ActivityTab() {
  const activity = useSessionStore((s) => s.session.activity);
  return (
    <div className="font-mono text-[10px] leading-relaxed">
      {activity.length === 0 && <div className="text-slate-400 italic">No activity yet.</div>}
      {activity.slice().reverse().map((a) => (
        <div key={a.id} className="flex gap-1.5 py-0.5 border-b border-dotted border-slate-200">
          <span className="text-slate-400 min-w-[42px]">{formatTs(a.ts)}</span>
          <span className={`min-w-[70px] ${colorByCategory[a.category] ?? ''}`}>{a.category.toUpperCase()}</span>
          <span className="text-slate-700 truncate">{a.text}</span>
        </div>
      ))}
    </div>
  );
}
```

```tsx
// frontend-react/src/components/right/tabs/ArtifactsTab.tsx
import { useSessionStore } from '../../../store/sessionStore';

export function ArtifactsTab() {
  const artifacts = useSessionStore((s) => s.session.artifacts);
  return (
    <>
      <div className="text-[9px] uppercase tracking-wider text-slate-400 mb-1">Generated this session ({artifacts.length})</div>
      {artifacts.length === 0 && <div className="text-[10px] text-slate-400 italic">No artifacts yet.</div>}
      {artifacts.map((a) => (
        <div key={a.id} className="bg-white border border-slate-200 rounded p-2 mb-1.5 text-[10px]">
          <div className="font-semibold text-slate-900">{a.title}</div>
          <div className="text-[9px] text-slate-400 mt-0.5">{a.kind} · {a.sourceAttribution}</div>
        </div>
      ))}
    </>
  );
}
```

```tsx
// frontend-react/src/components/right/tabs/ReportTab.tsx
export function ReportTab() {
  return (
    <div className="text-[10px] text-slate-500 italic p-2">
      Report builder coming in Phase 3 — drag artifacts into a narrative document, export branded PDF.
    </div>
  );
}
```

```tsx
// frontend-react/src/components/right/tabs/AuditTab.tsx
export function AuditTab() {
  return (
    <div className="text-[10px] text-slate-500 italic p-2">
      Audit log — populated in Phase 3 from <code>/api/audit/{'{session_id}'}</code>.
    </div>
  );
}
```

- [ ] **Step 2: Create RightRail.tsx**

```tsx
// frontend-react/src/components/right/RightRail.tsx
import { useState } from 'react';
import { useSessionStore } from '../../store/sessionStore';
import { PlanTab } from './tabs/PlanTab';
import { AgentsTab } from './tabs/AgentsTab';
import { ActivityTab } from './tabs/ActivityTab';
import { ArtifactsTab } from './tabs/ArtifactsTab';
import { ReportTab } from './tabs/ReportTab';
import { AuditTab } from './tabs/AuditTab';

const TABS = ['Plan', 'Agents', 'Activity', 'Artifacts', 'Report', 'Audit'] as const;
type TabId = typeof TABS[number];

export function RightRail() {
  const [active, setActive] = useState<TabId>('Agents');
  const agentsCount = useSessionStore((s) => Object.keys(s.session.agents).length);
  const artifactsCount = useSessionStore((s) => s.session.artifacts.length);

  return (
    <div>
      <div className="flex gap-0.5 border-b border-slate-200 -mx-3 -mt-3 mb-2 px-3 pt-2">
        {TABS.map((t) => (
          <button
            key={t}
            onClick={() => setActive(t)}
            className={`px-2.5 py-1 text-[10px] rounded-t ${active === t ? 'bg-white text-slate-900 border border-slate-200 border-b-white -mb-px font-semibold' : 'text-slate-500 hover:text-slate-700'}`}
          >
            {t}
            {t === 'Agents' && agentsCount > 0 && <span className="ml-1 bg-amber-100 text-amber-800 rounded-full px-1.5 text-[9px]">{agentsCount}</span>}
            {t === 'Artifacts' && artifactsCount > 0 && <span className="ml-1 bg-amber-100 text-amber-800 rounded-full px-1.5 text-[9px]">{artifactsCount}</span>}
          </button>
        ))}
      </div>
      {active === 'Plan' && <PlanTab />}
      {active === 'Agents' && <AgentsTab />}
      {active === 'Activity' && <ActivityTab />}
      {active === 'Artifacts' && <ArtifactsTab />}
      {active === 'Report' && <ReportTab />}
      {active === 'Audit' && <AuditTab />}
    </div>
  );
}
```

- [ ] **Step 3: Verify + commit**

```bash
cd "D:/Git Repos/Analyst_agentic_coder/frontend-react"
npx tsc --noEmit
```

```bash
cd "D:/Git Repos/Analyst_agentic_coder"
git add frontend-react/src/components/right/
git commit -m "feat(frontend): right rail with tabs (Plan/Agents/Activity/Artifacts/Report/Audit)"
```

---

## Task 7: PromptInput + App.tsx integration

**Files:**
- Create: `frontend-react/src/components/prompt/PromptInput.tsx`
- Modify: `frontend-react/src/App.tsx`
- Modify: `frontend-react/src/hooks/useChat.ts` (gut)
- Delete: `frontend-react/src/components/{ChatMessage,ChatInput,Sidebar,ProgressIndicator}.tsx`, `frontend-react/src/App.css`

- [ ] **Step 1: Create PromptInput.tsx**

```tsx
// frontend-react/src/components/prompt/PromptInput.tsx
import { useState, useRef, useEffect } from 'react';
import { useSessionStore } from '../../store/sessionStore';
import { postChat, eventStreamUrl } from '../../services/api';
import { openEventStream } from '../../services/eventStream';

export function PromptInput() {
  const [text, setText] = useState('');
  const isStreaming = useSessionStore((s) => s.session.isStreaming);
  const sessionId = useSessionStore((s) => s.sessionId);
  const setSessionId = useSessionStore((s) => s.setSessionId);
  const appendUser = useSessionStore((s) => s.appendUser);
  const handleEvent = useSessionStore((s) => s.handleEvent);
  const ta = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (ta.current) {
      ta.current.style.height = 'auto';
      ta.current.style.height = `${Math.min(ta.current.scrollHeight, 200)}px`;
    }
  }, [text]);

  const submit = async () => {
    const msg = text.trim();
    if (!msg || isStreaming) return;
    setText('');
    appendUser(msg);
    try {
      const resp = await postChat(msg, sessionId);
      setSessionId(resp.session_id);
      const url = eventStreamUrl(resp.session_id);
      const stream = openEventStream({
        url,
        onEvent: (ev) => {
          handleEvent(ev);
          if (ev.type === 'done') stream.close();
        },
        onError: (e) => {
          handleEvent({ type: 'error', code: 'STREAM', message: 'Stream error', recoverable: true });
          stream.close();
        },
      });
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Network error';
      handleEvent({ type: 'error', code: 'NETWORK', message, recoverable: true });
    }
  };

  const onKey = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey && !e.metaKey) {
      e.preventDefault();
      submit();
    }
  };

  return (
    <div className="flex items-center gap-2">
      <span className="text-[10px] text-slate-600 px-2 py-1 border border-slate-200 rounded bg-white">opus-4.7 ▾</span>
      <textarea
        ref={ta}
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={onKey}
        placeholder="Ask, refine, or describe a new analysis…  ⏎ to send, Shift+⏎ for newline"
        className="flex-1 border border-slate-300 rounded-lg px-3 py-2 text-[12px] resize-none min-h-[36px] max-h-[200px] focus:outline-none focus:ring-2 focus:ring-gold-500"
        disabled={isStreaming}
        rows={1}
      />
      <button
        onClick={submit}
        disabled={isStreaming || !text.trim()}
        className="text-[10px] px-3 py-2 rounded bg-brand-900 text-white disabled:bg-slate-300 disabled:cursor-not-allowed"
      >
        {isStreaming ? 'Streaming…' : 'Send'}
      </button>
      <span className="text-[10px] text-slate-400 px-2 py-1 border border-slate-200 rounded">Export PDF</span>
    </div>
  );
}
```

- [ ] **Step 2: Replace App.tsx**

```tsx
// frontend-react/src/App.tsx
import { ThreePaneLayout } from './components/layout/ThreePaneLayout';
import { BrandBar } from './components/frame/BrandBar';
import { ComplianceBar } from './components/frame/ComplianceBar';
import { StatusBar } from './components/frame/StatusBar';
import { ComplianceFooter } from './components/frame/ComplianceFooter';
import { LeftRail } from './components/left/LeftRail';
import { ChatStream } from './components/center/ChatStream';
import { RightRail } from './components/right/RightRail';
import { PromptInput } from './components/prompt/PromptInput';

function App() {
  return (
    <ThreePaneLayout
      topBar={<BrandBar userIdentity="acme.capital@client" userTier="Tier 1" rmName="David Chen" />}
      complianceBar={<ComplianceBar entitlements="US Equity LIVE · EU 15m" mnpiOn lastRefresh={new Date().toISOString().slice(11, 16) + ' GMT'} />}
      statusBar={<StatusBar />}
      left={<LeftRail />}
      center={<ChatStream />}
      right={<RightRail />}
      prompt={<PromptInput />}
      footer={<ComplianceFooter rmName="David Chen" />}
    />
  );
}

export default App;
```

- [ ] **Step 3: Gut useChat.ts**

```ts
// frontend-react/src/hooks/useChat.ts
// Phase 2: replaced by direct Zustand store access in components.
// This file is kept as a thin re-export of the store for any legacy consumer.
export { useSessionStore as useChat } from '../store/sessionStore';
```

- [ ] **Step 4: Delete superseded files**

```bash
cd "D:/Git Repos/Analyst_agentic_coder/frontend-react/src"
rm -f App.css
rm -f components/ChatMessage.tsx components/ChatInput.tsx components/Sidebar.tsx components/ProgressIndicator.tsx components/index.ts
```

- [ ] **Step 5: Verify build**

```bash
cd "D:/Git Repos/Analyst_agentic_coder/frontend-react"
npx tsc --noEmit
npm run build
```

Expected: clean. If `index.ts` was a barrel that exported the deleted components and other code imports from `'./components'`, fix the imports inline (replace with direct paths).

- [ ] **Step 6: Commit**

```bash
cd "D:/Git Repos/Analyst_agentic_coder"
git add frontend-react/src/components/prompt/ frontend-react/src/App.tsx frontend-react/src/hooks/useChat.ts
git rm -f frontend-react/src/App.css \
          frontend-react/src/components/ChatMessage.tsx \
          frontend-react/src/components/ChatInput.tsx \
          frontend-react/src/components/Sidebar.tsx \
          frontend-react/src/components/ProgressIndicator.tsx \
          frontend-react/src/components/index.ts
git commit -m "feat(frontend): integrate ThreePaneLayout in App, add PromptInput, remove legacy components"
```

---

## Task 8: Smoke test against running backend

**No code commit.** Verify the full stack works.

- [ ] **Step 1: Start backend**

```bash
cd "D:/Git Repos/Analyst_agentic_coder/backend"
python -m uvicorn app.main:app --port 8000 &
```

Wait 3s, verify health:
```bash
curl -s http://localhost:8000/health
```

- [ ] **Step 2: Start frontend dev server**

```bash
cd "D:/Git Repos/Analyst_agentic_coder/frontend-react"
npm run dev &
```

Wait until Vite reports `Local: http://localhost:3000/`.

- [ ] **Step 3: Open the URL in a browser**

http://localhost:3000

Expected: the new Quant Console UI renders with:
- Navy/gold BrandBar with "Q · Quant Console"
- Amber compliance bar
- Status bar (mostly empty until a session exists)
- Left rail (Sessions, Workspace, Knowledge labels)
- Center pane (empty chat)
- Right rail with tabs
- Bottom prompt input
- Navy compliance footer

- [ ] **Step 4: Send a real message**

In the prompt input, type "What is 2+2 in one sentence?" and press Enter.

Expected: events stream in live — plan/agents tabs populate, status bar updates, assistant message appears in center.

If the agent emits no events (CLI auth issue), the error banner shows. That's not a Phase 2 bug.

- [ ] **Step 5: Stop services**

Kill the backend + frontend:
```bash
netstat -ano | grep -E ':(8000|3000) ' | head -3
# kill the PIDs:
taskkill /F /PID <pid>
```

- [ ] **Step 6: No commit. Report findings.**

---

## Self-review checklist

- [ ] Spec coverage: every component listed in the spec's "Frontend components" section has a file in this plan.
- [ ] No placeholders: every step contains complete code or exact commands.
- [ ] Type consistency: store/reducer/event types use identical names. `applyEvent` signature matches in test and source. `SessionStore` interface matches between definition and consumers.
- [ ] TDD discipline: store + reducer have tests; visual components are verified via build + smoke test (acceptable for Phase 2 — Phase 3 adds Storybook/Chromatic).
- [ ] Each task ends with a commit; bisectable.

## Open follow-ups (NOT in this plan)

- Phase 3 plan: branded artifact rendering (Plotly/AG Grid choice), audit tab population from backend, PDF export.
- Hygiene plan: CORS allowlist, remove `/api/files/{path}`, scrub git creds in URL logs.
- Backend: consume the entitlements endpoint in compliance bar (currently hardcoded display strings).
- Storybook: per-component stories deferred — Phase 2 ships visual components verified by manual smoke; Phase 3 adds Storybook + Chromatic.
