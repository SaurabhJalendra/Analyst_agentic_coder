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
