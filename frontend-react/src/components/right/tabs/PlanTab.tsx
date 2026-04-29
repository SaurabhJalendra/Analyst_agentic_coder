import { useSessionStore } from '../../../store/sessionStore';

export function PlanTab() {
  const plan = useSessionStore((s) => s.session.plan);
  if (plan.length === 0) return <div className="text-[10px] text-slate-400 italic">No active plan.</div>;
  return (
    <div className="border-l-2 border-slate-200 pl-3.5 ml-1">
      {plan.map((step) => (
        <div key={step.id} className={`py-1 text-[10px] relative ${step.status === 'done' ? 'text-emerald-600' : step.status === 'running' ? 'text-slate-900 font-semibold' : 'text-slate-500'}`}>
          <span className={`absolute -left-[19px] top-2 w-1.5 h-1.5 rounded-full ${step.status === 'done' ? 'bg-emerald-600' : step.status === 'running' ? 'bg-amber-500 ring-2 ring-amber-200' : 'bg-slate-200'}`} />
          {step.description} {step.durationMs && <span className="text-slate-400">· {step.durationMs}ms</span>}
        </div>
      ))}
    </div>
  );
}
