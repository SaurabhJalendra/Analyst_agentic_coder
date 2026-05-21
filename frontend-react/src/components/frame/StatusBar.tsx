// frontend-react/src/components/frame/StatusBar.tsx
import { useSessionStore } from '../../store/sessionStore';

export function StatusBar() {
  const sessionId = useSessionStore((s) => s.sessionId);
  const session = useSessionStore((s) => s.session);

  const planTotal = session.plan.length;
  const planDone = session.plan.filter((p) => p.status === 'done').length;
  const agentsRunning = Object.values(session.agents).filter((a) => a.status === 'running').length;
  const agentsTotal = Object.keys(session.agents).length;
  const sources = Object.keys(session.sources);

  return (
    <div className="bg-slate-50 border-b border-slate-200 px-5 py-2 flex gap-3 items-center text-[11px] text-slate-600">
      <span className="bg-white border border-slate-200 rounded-full px-2.5 py-0.5">
        Session: <strong className="text-slate-900">{sessionId ?? '—'}</strong>
      </span>
      {planTotal > 0 && (
        <span className="bg-white border border-slate-200 rounded-full px-2.5 py-0.5 text-emerald-600">
          ● Plan {planDone}/{planTotal} {session.isStreaming ? '· running' : ''}
        </span>
      )}
      {agentsTotal > 0 && (
        <span className="bg-white border border-slate-200 rounded-full px-2.5 py-0.5">
          Agents: {agentsTotal} · {agentsRunning} running
        </span>
      )}
      {sources.length > 0 && (
        <span className="bg-white border border-slate-200 rounded-full px-2.5 py-0.5">
          Sources: {sources.join(' · ')}
        </span>
      )}
      {session.isStreaming && (
        <span className="ml-auto bg-white border border-slate-200 rounded-full px-2.5 py-0.5 text-red-600 cursor-pointer">
          Halt
        </span>
      )}
    </div>
  );
}
