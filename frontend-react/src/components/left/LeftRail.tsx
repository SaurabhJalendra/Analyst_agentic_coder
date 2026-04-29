import { SessionsList } from './SessionsList';
import { WorkspaceTree } from './WorkspaceTree';
import { KnowledgePanel } from './KnowledgePanel';

export function LeftRail() {
  return (
    <div className="flex flex-col gap-4 text-[11px]">
      <SessionsList />
      <WorkspaceTree />
      <KnowledgePanel />
    </div>
  );
}

export function Label({ children }: { children: React.ReactNode }) {
  return <div className="text-[9px] uppercase tracking-wider text-slate-400 mb-1">{children}</div>;
}
