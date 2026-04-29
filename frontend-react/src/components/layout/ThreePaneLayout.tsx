// frontend-react/src/components/layout/ThreePaneLayout.tsx
import type { ReactNode } from 'react';

export interface ThreePaneLayoutProps {
  topBar: ReactNode;
  complianceBar: ReactNode;
  statusBar: ReactNode;
  left: ReactNode;
  center: ReactNode;
  right: ReactNode;
  prompt: ReactNode;
  footer: ReactNode;
}

export function ThreePaneLayout({ topBar, complianceBar, statusBar, left, center, right, prompt, footer }: ThreePaneLayoutProps) {
  return (
    <div className="h-screen w-screen flex flex-col bg-white text-slate-900">
      {topBar}
      {complianceBar}
      {statusBar}
      <div className="flex-1 grid grid-cols-[220px_1fr_360px] min-h-0">
        <aside className="bg-slate-50 border-r border-slate-200 overflow-y-auto p-3">{left}</aside>
        <main className="bg-white overflow-y-auto p-4">{center}</main>
        <aside className="bg-slate-50 border-l border-slate-200 overflow-y-auto p-3">{right}</aside>
      </div>
      <div className="border-t border-slate-200 px-5 py-2.5 bg-white">{prompt}</div>
      {footer}
    </div>
  );
}
