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
