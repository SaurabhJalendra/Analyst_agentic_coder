import { Label } from './LeftRail';
import { useSessionStore } from '../../store/sessionStore';

export function WorkspaceTree() {
  const session = useSessionStore((s) => s.session);
  return (
    <div>
      <Label>Workspace</Label>
      <div className="text-slate-600">
        {session.artifacts.length > 0 ? (
          <>
            <div>▾ artifacts/ <span className="text-slate-400">{session.artifacts.length}</span></div>
            {session.artifacts.slice(0, 5).map((a) => (
              <div key={a.id} className="pl-3.5 truncate" title={a.title}>{a.title}</div>
            ))}
          </>
        ) : (
          <div className="text-slate-400 italic">No workspace files yet</div>
        )}
      </div>
    </div>
  );
}
