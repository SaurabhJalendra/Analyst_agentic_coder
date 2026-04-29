import { useSessionStore } from '../../store/sessionStore';

export function PlanRail() {
  const plan = useSessionStore((s) => s.session.plan);
  const agents = useSessionStore((s) => s.session.agents);
  if (plan.length === 0) return null;

  const done = plan.filter((p) => p.status === 'done').length;
  const subAgentCount = Object.keys(agents).length;
  return (
    <div className="my-3 text-[11px] text-slate-600">
      <strong className="text-slate-900">Plan</strong> — {done}/{plan.length} steps · {subAgentCount} sub-agents
    </div>
  );
}
