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
