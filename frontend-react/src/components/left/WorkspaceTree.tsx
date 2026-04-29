import { useEffect, useState } from 'react';
import axios from 'axios';
import { Label } from './LeftRail';
import { useSessionStore } from '../../store/sessionStore';

interface FileItem {
  name: string;
  path: string;
  is_dir: boolean;
  size: number | null;
  download_url: string | null;
}

const BASE = import.meta.env.VITE_API_URL || '';

export function WorkspaceTree() {
  const sessionId = useSessionStore((s) => s.sessionId);
  const isStreaming = useSessionStore((s) => s.session.isStreaming);
  const [items, setItems] = useState<FileItem[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!sessionId) {
      setItems([]);
      setError(null);
      return;
    }
    let cancelled = false;
    const load = async () => {
      try {
        const r = await axios.get<{ items?: FileItem[]; files?: FileItem[] }>(
          `${BASE}/api/workspace/${sessionId}/list/`,
        );
        if (!cancelled) {
          // Backend returns the list under both "items" and "files" — use whichever is present.
          setItems(r.data.items ?? r.data.files ?? []);
          setError(null);
        }
      } catch (err) {
        if (!cancelled) {
          // 404 on a fresh workspace just means "nothing there yet" — show empty, not error.
          const status = (err as { response?: { status?: number } }).response?.status;
          if (status === 404) {
            setItems([]);
            setError(null);
          } else {
            setError('Workspace not yet ready');
          }
        }
      }
    };
    load();
    // Refresh after streaming finishes (new files may have been written)
    const interval = isStreaming ? setInterval(load, 4000) : null;
    return () => {
      cancelled = true;
      if (interval) clearInterval(interval);
    };
  }, [sessionId, isStreaming]);

  return (
    <div>
      <Label>Workspace</Label>
      <div className="text-slate-600">
        {!sessionId && <div className="text-slate-400 italic text-[10px]">No session selected.</div>}
        {sessionId && error && <div className="text-red-600 text-[10px]">{error}</div>}
        {sessionId && !error && items.length === 0 && (
          <div className="text-slate-400 italic text-[10px]">Empty workspace.</div>
        )}
        {items.map((item) => (
          <div key={item.path} className="px-1 py-0.5 truncate" title={item.path}>
            {item.is_dir ? '▾ ' : '  '}
            {item.is_dir ? `${item.name}/` : item.name}
          </div>
        ))}
      </div>
    </div>
  );
}
