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
