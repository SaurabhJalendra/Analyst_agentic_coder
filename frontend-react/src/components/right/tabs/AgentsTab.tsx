import { useSessionStore } from '../../../store/sessionStore';

export function AgentsTab() {
  const agents = useSessionStore((s) => s.session.agents);
  const sources = useSessionStore((s) => s.session.sources);
  const list = Object.values(agents);
  return (
    <>
      <div className="text-[9px] uppercase tracking-wider text-slate-400 mt-1.5 mb-1">Active agent team</div>
      {list.length === 0 && <div className="text-[10px] text-slate-400 italic">No agents yet.</div>}
      {list.map((a) => (
        <div key={a.id} className={`bg-white border border-slate-200 rounded p-2 mb-1.5 border-l-[3px] ${a.status === 'running' ? 'border-l-sky-500' : a.status === 'done' ? 'border-l-emerald-600' : 'border-l-slate-300 opacity-70'}`}>
          <div className="text-[10px] text-slate-900 font-semibold">{a.id === 'main' ? 'main' : `↳ ${a.kind}`}</div>
          <div className="text-[9px] text-slate-400 mt-0.5">{a.model} · {a.tokens} tokens{a.durationMs ? ` · ${a.durationMs}ms` : ''}</div>
          {a.toolsUsed.length > 0 && <div className="text-[9px] text-slate-600 mt-0.5">tools: {a.toolsUsed.join(', ')}</div>}
        </div>
      ))}
      <div className="text-[9px] uppercase tracking-wider text-slate-400 mt-3.5 mb-1">Sources accessed</div>
      <div className="text-[10px] text-slate-600">
        {Object.values(sources).map((s) => (
          <div key={s.source}>● {s.source} <span className="text-slate-400">{s.callCount} calls</span></div>
        ))}
        {Object.keys(sources).length === 0 && <div className="text-slate-400 italic">none</div>}
      </div>
    </>
  );
}
