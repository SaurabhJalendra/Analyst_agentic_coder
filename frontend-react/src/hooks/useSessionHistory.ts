import { useEffect } from 'react';
import axios from 'axios';
import { useSessionStore } from '../store/sessionStore';
import type { ChatTurn } from '../types/domain';

interface ApiHistoryMessage {
  role: 'user' | 'assistant' | string;
  content: string;
  timestamp: string;
}

const BASE = import.meta.env.VITE_API_URL || '';

/**
 * Watches `sessionId` and reloads chat history when it changes — but only
 * when there's no chat yet (i.e. switching to an existing session, NOT after
 * just creating a new session via PromptInput which already has a user turn).
 *
 * The cancel flag prevents a stale fetch from overwriting newer state when the
 * user rapidly switches between sessions.
 */
export function useSessionHistory(): void {
  const sessionId = useSessionStore((s) => s.sessionId);
  const chatLength = useSessionStore((s) => s.session.chat.length);
  const replaceChat = useSessionStore((s) => s.replaceChat);

  useEffect(() => {
    if (!sessionId) return;
    if (chatLength > 0) return; // already populated (new session or in-progress)

    let cancelled = false;
    axios
      .get<{ messages: ApiHistoryMessage[] }>(`${BASE}/api/session/${sessionId}/history`)
      .then((r) => {
        if (cancelled) return;
        const messages = r.data.messages ?? [];
        const turns: ChatTurn[] = messages.map((m, i) => {
          const ts = Date.parse(m.timestamp) || Date.now();
          if (m.role === 'user') {
            return { kind: 'user', id: `hist-u-${i}`, text: m.content, ts };
          }
          return { kind: 'assistant', id: `hist-a-${i}`, text: m.content, ts };
        });
        replaceChat(turns);
      })
      .catch((err) => {
        if (cancelled) return;
        // 404 (session not found) and network errors are non-fatal — leave the
        // chat empty and let the user start fresh.
        console.warn('[useSessionHistory] failed to load', err);
      });

    return () => {
      cancelled = true;
    };
  }, [sessionId, chatLength, replaceChat]);
}
