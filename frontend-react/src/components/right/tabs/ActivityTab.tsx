import { useSessionStore } from '../../../store/sessionStore';

const colorByCategory: Record<string, string> = {
  plan: 'text-slate-600 font-semibold',
  tool: 'text-sky-600',
  subagent: 'text-purple-500',
  skill: 'text-emerald-600',
  memory: 'text-amber-600',
  source: 'text-red-600',
  message: 'text-slate-700',
  thinking: 'text-amber-700',
  error: 'text-red-700 font-semibold',
  other: 'text-slate-500',
};

function formatTs(ts: number): string {
  const d = new Date(ts);
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
}

export function ActivityTab() {
  const activity = useSessionStore((s) => s.session.activity);
  return (
    <div className="font-mono text-[10px] leading-relaxed">
      {activity.length === 0 && <div className="text-slate-400 italic">No activity yet.</div>}
      {activity.slice().reverse().map((a) => (
        <div key={a.id} className="flex gap-1.5 py-0.5 border-b border-dotted border-slate-200">
          <span className="text-slate-400 min-w-[42px]">{formatTs(a.ts)}</span>
          <span className={`min-w-[70px] ${colorByCategory[a.category] ?? ''}`}>{a.category.toUpperCase()}</span>
          <span className="text-slate-700 truncate">{a.text}</span>
        </div>
      ))}
    </div>
  );
}
