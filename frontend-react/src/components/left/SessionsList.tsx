import { useEffect, useState } from 'react';
import { listSessions } from '../../services/api';
import { useSessionStore } from '../../store/sessionStore';
import { Label } from './LeftRail';

interface ApiSession {
  id: string;
  created_at: string;
  active_repo?: string | null;
  message_count?: number;
}

function formatSessionLabel(s: ApiSession): string {
  const ts = s.created_at ? new Date(s.created_at) : null;
  if (!ts || Number.isNaN(ts.getTime())) return s.id.slice(0, 8);
  const date = `${String(ts.getMonth() + 1).padStart(2, '0')}/${String(ts.getDate()).padStart(2, '0')}`;
  const time = `${String(ts.getHours()).padStart(2, '0')}:${String(ts.getMinutes()).padStart(2, '0')}`;
  return `${date} ${time}`;
}

export function SessionsList() {
  const [sessions, setSessions] = useState<ApiSession[]>([]);
  const currentId = useSessionStore((s) => s.sessionId);
  const setSessionId = useSessionStore((s) => s.setSessionId);
  const reset = useSessionStore((s) => s.reset);

  const refresh = async () => {
    try {
      const data: ApiSession[] = await listSessions();
      const sorted = [...data].sort((a, b) => (a.created_at < b.created_at ? 1 : -1));
      setSessions(sorted);
    } catch {
      /* tolerate */
    }
  };

  useEffect(() => {
    refresh();
  }, []);

  // Re-list whenever the active session id changes (catches new-session creation
  // from PromptInput and session deletion).
  useEffect(() => {
    refresh();
  }, [currentId]);

  return (
    <div>
      <Label>Sessions</Label>
      <div>
        {sessions.length === 0 && (
          <div className="text-slate-400 italic text-[10px]">No sessions yet.</div>
        )}
        {sessions.map((s) => {
          const active = currentId === s.id;
          const msgs = s.message_count ?? 0;
          return (
            <div
              key={s.id}
              onClick={() => setSessionId(s.id)}
              title={s.id}
              className={`px-1.5 py-0.5 rounded cursor-pointer flex items-baseline gap-2 ${active ? 'bg-indigo-50 text-brand-900 font-semibold' : 'text-slate-600 hover:bg-slate-100'}`}
            >
              <span>{formatSessionLabel(s)}</span>
              {msgs > 0 && <span className="text-[9px] text-slate-400">· {msgs} msg{msgs === 1 ? '' : 's'}</span>}
            </div>
          );
        })}
        <div
          onClick={() => {
            reset();
            refresh();
          }}
          className="px-1.5 py-0.5 mt-1 text-slate-400 cursor-pointer hover:text-slate-600 text-[10px]"
        >
          + New session
        </div>
      </div>
    </div>
  );
}
