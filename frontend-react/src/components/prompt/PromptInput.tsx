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
        onError: (_e) => {
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
