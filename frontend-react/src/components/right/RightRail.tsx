import { useState } from 'react';
import { useSessionStore } from '../../store/sessionStore';
import { PlanTab } from './tabs/PlanTab';
import { AgentsTab } from './tabs/AgentsTab';
import { ActivityTab } from './tabs/ActivityTab';
import { ArtifactsTab } from './tabs/ArtifactsTab';
import { ReportTab } from './tabs/ReportTab';
import { AuditTab } from './tabs/AuditTab';

const TABS = ['Plan', 'Agents', 'Activity', 'Artifacts', 'Report', 'Audit'] as const;
type TabId = typeof TABS[number];

export function RightRail() {
  const [active, setActive] = useState<TabId>('Agents');
  const agentsCount = useSessionStore((s) => Object.keys(s.session.agents).length);
  const artifactsCount = useSessionStore((s) => s.session.artifacts.length);

  return (
    <div>
      <div className="flex gap-0.5 border-b border-slate-200 -mx-3 -mt-3 mb-2 px-3 pt-2">
        {TABS.map((t) => (
          <button
            key={t}
            onClick={() => setActive(t)}
            className={`px-2.5 py-1 text-[10px] rounded-t ${active === t ? 'bg-white text-slate-900 border border-slate-200 border-b-white -mb-px font-semibold' : 'text-slate-500 hover:text-slate-700'}`}
          >
            {t}
            {t === 'Agents' && agentsCount > 0 && <span className="ml-1 bg-amber-100 text-amber-800 rounded-full px-1.5 text-[9px]">{agentsCount}</span>}
            {t === 'Artifacts' && artifactsCount > 0 && <span className="ml-1 bg-amber-100 text-amber-800 rounded-full px-1.5 text-[9px]">{artifactsCount}</span>}
          </button>
        ))}
      </div>
      {active === 'Plan' && <PlanTab />}
      {active === 'Agents' && <AgentsTab />}
      {active === 'Activity' && <ActivityTab />}
      {active === 'Artifacts' && <ArtifactsTab />}
      {active === 'Report' && <ReportTab />}
      {active === 'Audit' && <AuditTab />}
    </div>
  );
}
