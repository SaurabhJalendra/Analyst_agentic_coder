import { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import { useSessionStore } from '../../store/sessionStore';
import { postChat, eventStreamUrl } from '../../services/api';
import { openEventStream, type EventStreamHandle } from '../../services/eventStream';

const BASE = import.meta.env.VITE_API_URL || '';

interface ActiveStream {
  handle: EventStreamHandle;
  sid: string;
}

export function PromptInput() {
  const [text, setText] = useState('');
  const isStreaming = useSessionStore((s) => s.session.isStreaming);
  const sessionId = useSessionStore((s) => s.sessionId);
  const setSessionId = useSessionStore((s) => s.setSessionId);
  const appendUser = useSessionStore((s) => s.appendUser);
  const handleEvent = useSessionStore((s) => s.handleEvent);
  const ta = useRef<HTMLTextAreaElement>(null);
  const streamRef = useRef<ActiveStream | null>(null);

  useEffect(() => {
    if (ta.current) {
      ta.current.style.height = 'auto';
      ta.current.style.height = `${Math.min(ta.current.scrollHeight, 200)}px`;
    }
  }, [text]);

  // Close the active stream on unmount only. Closing on sessionId change is
  // intentionally avoided because PromptInput itself sets the sessionId after
  // POST /api/chat returns; the resulting effect cleanup would race with the
  // just-opened stream. Cross-session pollution is prevented by checking the
  // store's current sessionId inside onEvent (see submit below).
  useEffect(() => {
    return () => {
      if (streamRef.current) {
        streamRef.current.handle.close();
        streamRef.current = null;
      }
    };
  }, []);

  const closeActiveStream = () => {
    if (streamRef.current) {
      streamRef.current.handle.close();
      streamRef.current = null;
    }
  };

  const exportPdf = async () => {
    if (!sessionId) return;
    try {
      const r = await axios.post(
        `${BASE}/api/export/pdf`,
        { session_id: sessionId, artifact_ids: [], narrative: '' },
        { responseType: 'blob' },
      );
      const url = URL.createObjectURL(r.data as Blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `quant-console-${sessionId}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error('PDF export failed', err);
    }
  };

  const submit = async () => {
    const msg = text.trim();
    if (!msg || isStreaming) return;
    setText('');
    appendUser(msg);

    closeActiveStream();

    try {
      const resp = await postChat(msg, sessionId);
      const targetSid = resp.session_id;
      setSessionId(targetSid);
      const handle = openEventStream({
        url: eventStreamUrl(targetSid),
        onEvent: (ev) => {
          // Filter out stale events that arrive after the user has switched
          // to a different session — otherwise the old stream would mutate
          // the new session's state.
          if (useSessionStore.getState().sessionId !== targetSid) return;
          handleEvent(ev);
          if (ev.type === 'done') closeActiveStream();
        },
        onError: () => {
          if (useSessionStore.getState().sessionId !== targetSid) return;
          handleEvent({ type: 'error', code: 'STREAM', message: 'Stream error', recoverable: true });
          closeActiveStream();
        },
      });
      streamRef.current = { handle, sid: targetSid };
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
      <span className="text-[10px] text-slate-600 px-2 py-1 border border-slate-200 rounded bg-white">
        opus-4.7 ▾
      </span>
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
      <button
        onClick={exportPdf}
        disabled={!sessionId}
        className="text-[10px] text-slate-600 px-2 py-1 border border-slate-200 rounded hover:bg-slate-50 disabled:text-slate-300 disabled:cursor-not-allowed"
        title={sessionId ? 'Export branded PDF of this session' : 'Send a message first'}
      >
        Export PDF
      </button>
    </div>
  );
}
