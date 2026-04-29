import { useSessionStore } from '../../../store/sessionStore';

export function ArtifactsTab() {
  const artifacts = useSessionStore((s) => s.session.artifacts);
  return (
    <>
      <div className="text-[9px] uppercase tracking-wider text-slate-400 mb-1">Generated this session ({artifacts.length})</div>
      {artifacts.length === 0 && <div className="text-[10px] text-slate-400 italic">No artifacts yet.</div>}
      {artifacts.map((a) => (
        <div key={a.id} className="bg-white border border-slate-200 rounded p-2 mb-1.5 text-[10px]">
          <div className="font-semibold text-slate-900">{a.title}</div>
          <div className="text-[9px] text-slate-400 mt-0.5">{a.kind} · {a.sourceAttribution}</div>
        </div>
      ))}
    </>
  );
}
