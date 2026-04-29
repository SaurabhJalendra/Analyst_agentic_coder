import { useEffect, useState } from 'react';
import axios from 'axios';
import { useSessionStore } from '../../../store/sessionStore';

interface AuditRow {
  id: number;
  ts: string;
  event_type: string;
  audit_id: string;
  data: Record<string, unknown>;
}

const BASE = import.meta.env.VITE_API_URL || '';

export function AuditTab() {
  const sessionId = useSessionStore((s) => s.sessionId);
  const [rows, setRows] = useState<AuditRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!sessionId) { setRows([]); return; }
    let cancelled = false;
    setLoading(true);
    axios.get<{ rows: AuditRow[] }>(`${BASE}/api/audit/${sessionId}?limit=200`)
      .then((r) => { if (!cancelled) setRows(r.data.rows); })
      .catch((e) => { if (!cancelled) setError(e instanceof Error ? e.message : 'Failed to load'); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [sessionId]);

  if (!sessionId) {
    return <div className="text-[10px] text-slate-500 italic p-2">No session yet — start a chat to see the audit log.</div>;
  }
  if (loading) return <div className="text-[10px] text-slate-500 italic p-2">Loading audit log…</div>;
  if (error) return <div className="text-[10px] text-red-600 p-2">{error}</div>;
  if (rows.length === 0) return <div className="text-[10px] text-slate-500 italic p-2">No audit rows yet.</div>;

  return (
    <div className="font-mono text-[10px] leading-relaxed">
      <div className="text-[9px] uppercase tracking-wider text-slate-400 mb-1">Audit log ({rows.length} rows)</div>
      {rows.map((r) => (
        <div key={r.id} className="flex gap-1.5 py-0.5 border-b border-dotted border-slate-200">
          <span className="text-slate-400 min-w-[58px]">{r.ts.slice(11, 19)}</span>
          <span className="min-w-[100px] text-slate-600 truncate">{r.event_type}</span>
          <span className="text-slate-700 truncate flex-1" title={r.audit_id}>{r.audit_id}</span>
        </div>
      ))}
    </div>
  );
}
