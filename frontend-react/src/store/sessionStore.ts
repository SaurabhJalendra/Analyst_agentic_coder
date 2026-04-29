import { create } from 'zustand';
import { applyEvent, appendUserMessage, initialSessionState, type SessionState } from '../services/eventReducer';
import type { AnyEvent } from '../types/events';

export interface SessionStore {
  sessionId: string | null;
  session: SessionState;
  setSessionId(id: string | null): Promise<void>;
  handleEvent(ev: AnyEvent): void;
  appendUser(text: string): void;
  reset(): void;
}

export const useSessionStore = create<SessionStore>((set) => ({
  sessionId: null,
  session: initialSessionState(),
  setSessionId: async (id: string | null) => {
    set({ sessionId: id, session: initialSessionState() });
    if (!id) return;
    try {
      const { default: axios } = await import('axios');
      const BASE = import.meta.env.VITE_API_URL || '';
      const r = await axios.get<{ messages: Array<{ role: string; content: string; timestamp: string }> }>(`${BASE}/api/session/${id}/history`);
      const messages = r.data.messages ?? [];
      set((s) => {
        const chat = messages.map((m, i) => m.role === 'user'
          ? ({ kind: 'user' as const, id: `hist-u-${i}`, text: m.content, ts: Date.parse(m.timestamp) || Date.now() })
          : ({ kind: 'assistant' as const, id: `hist-a-${i}`, text: m.content, ts: Date.parse(m.timestamp) || Date.now() })
        );
        return { session: { ...s.session, chat } };
      });
    } catch (err) {
      console.warn('Failed to reload session history', err);
    }
  },
  handleEvent: (ev) => set((s) => ({ session: applyEvent(s.session, ev) })),
  appendUser: (text) => set((s) => ({ session: appendUserMessage(s.session, text) })),
  reset: () => set({ sessionId: null, session: initialSessionState() }),
}));
