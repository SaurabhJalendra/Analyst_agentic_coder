import { create } from 'zustand';
import {
  applyEvent,
  appendUserMessage,
  initialSessionState,
  type SessionState,
} from '../services/eventReducer';
import type { AnyEvent } from '../types/events';
import type { ChatTurn } from '../types/domain';

export interface SessionStore {
  sessionId: string | null;
  session: SessionState;
  /**
   * Set just the active session id (does NOT reset session state). Used by
   * PromptInput to "adopt" the server-assigned id for a brand-new session
   * without wiping the just-appended user turn.
   */
  setSessionId(id: string | null): void;
  /**
   * Switch to a different existing session: resets the in-memory session
   * state so the history-fetch hook can repopulate it.
   */
  switchSession(id: string): void;
  handleEvent(ev: AnyEvent): void;
  appendUser(text: string): void;
  /** Replace the chat array — used by the history-fetch hook. */
  replaceChat(turns: ChatTurn[]): void;
  reset(): void;
}

export const useSessionStore = create<SessionStore>((set) => ({
  sessionId: null,
  session: initialSessionState(),
  setSessionId: (id) => set({ sessionId: id }),
  switchSession: (id) => set({ sessionId: id, session: initialSessionState() }),
  handleEvent: (ev) => set((s) => ({ session: applyEvent(s.session, ev) })),
  appendUser: (text) => set((s) => ({ session: appendUserMessage(s.session, text) })),
  replaceChat: (turns) => set((s) => ({ session: { ...s.session, chat: turns } })),
  reset: () => set({ sessionId: null, session: initialSessionState() }),
}));
