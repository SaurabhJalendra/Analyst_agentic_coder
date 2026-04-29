import { useEffect, useState } from 'react';
import axios from 'axios';

interface Methodology {
  artifact_id: string;
  title: string;
  source_attribution: string;
  created_at: string;
  methodology: {
    tool_calls: Array<{ tool: string; args_redacted: Record<string, unknown>; duration_ms?: number }>;
    sources: Array<{ source: string; operation: string; count?: number }>;
    agents_involved: string[];
    narrative: string;
  };
}

const BASE = import.meta.env.VITE_API_URL || '';

export function MethodologyPanel({ artifactId }: { artifactId: string }) {
  const [data, setData] = useState<Methodology | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    axios.get<Methodology>(`${BASE}/api/artifacts/${artifactId}/methodology`)
      .then((r) => { if (!cancelled) setData(r.data); })
      .catch((e) => { if (!cancelled) setError(e instanceof Error ? e.message : 'Failed to load'); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [artifactId]);

  if (loading) return <div className="text-[10px] text-slate-400 italic p-2">Loading methodology…</div>;
  if (error) return <div className="text-[10px] text-red-600 p-2">{error}</div>;
  if (!data) return null;

  const m = data.methodology;
  return (
    <div className="text-[10px] text-slate-700 p-3 bg-slate-50 border-t border-slate-200">
      <div className="font-semibold text-slate-900 mb-1">How this was made</div>
      <p className="mb-2 text-slate-600">{m.narrative}</p>
      {m.agents_involved.length > 0 && (
        <div className="mb-1"><strong>Agents:</strong> {m.agents_involved.join(', ')}</div>
      )}
      {m.tool_calls.length > 0 && (
        <div className="mb-1"><strong>Tool calls:</strong> {m.tool_calls.map((tc) => tc.tool).join(', ')} ({m.tool_calls.length})</div>
      )}
      {m.sources.length > 0 && (
        <div><strong>Sources:</strong> {m.sources.map((s) => s.source).join(', ')}</div>
      )}
    </div>
  );
}
