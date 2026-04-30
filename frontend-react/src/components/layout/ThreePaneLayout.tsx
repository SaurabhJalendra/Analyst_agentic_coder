// frontend-react/src/components/layout/ThreePaneLayout.tsx
import { useEffect, useState, type ReactNode } from 'react';

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

const BREAKPOINT_PX = 1280;

/**
 * Three-pane research console.
 *
 *   ≥1280px: full three-pane CSS grid (220 / 1fr / 360).
 *   <1280px: right pane hides; a floating "Inspector" button toggles it as a
 *            slide-over from the right edge. Left pane keeps its width;
 *            main pane gets the freed space.
 *   <768px:  left pane also collapses to a slide-over from the left.
 *
 * The breakpoint listener tracks viewport width so the layout reacts live to
 * resize, including dragging from desktop to mobile width during a session.
 */
export function ThreePaneLayout({
  topBar,
  complianceBar,
  statusBar,
  left,
  center,
  right,
  prompt,
  footer,
}: ThreePaneLayoutProps) {
  const [vw, setVw] = useState(() =>
    typeof window === 'undefined' ? 1920 : window.innerWidth,
  );
  const [inspectorOpen, setInspectorOpen] = useState(false);
  const [navOpen, setNavOpen] = useState(false);

  useEffect(() => {
    const handler = () => setVw(window.innerWidth);
    window.addEventListener('resize', handler);
    return () => window.removeEventListener('resize', handler);
  }, []);

  const isDesktop = vw >= BREAKPOINT_PX;
  const isNarrow = vw < 768;

  return (
    <div className="h-screen w-screen flex flex-col bg-white text-slate-900">
      {topBar}
      {complianceBar}
      <div className="relative flex items-center">
        <div className="flex-1 min-w-0">{statusBar}</div>
        {!isDesktop && (
          <div className="flex gap-1 pr-3 py-1">
            {isNarrow && (
              <button
                onClick={() => setNavOpen((v) => !v)}
                className="text-[10px] px-2 py-1 border border-slate-200 rounded bg-white hover:bg-slate-50"
                aria-label="Toggle sessions and workspace"
              >
                ☰ Nav
              </button>
            )}
            <button
              onClick={() => setInspectorOpen((v) => !v)}
              className="text-[10px] px-2 py-1 border border-slate-200 rounded bg-white hover:bg-slate-50"
              aria-label="Toggle inspector pane"
            >
              ▦ Inspector
            </button>
          </div>
        )}
      </div>

      <div
        className="flex-1 min-h-0 grid"
        style={{
          gridTemplateColumns: isDesktop
            ? '220px 1fr 360px'
            : isNarrow
              ? '1fr'
              : '220px 1fr',
        }}
      >
        {/* LEFT — desktop+tablet inline; mobile slide-over */}
        {!isNarrow && (
          <aside className="bg-slate-50 border-r border-slate-200 overflow-y-auto p-3">
            {left}
          </aside>
        )}
        <main className="bg-white overflow-y-auto p-4">{center}</main>
        {/* RIGHT — desktop only inline */}
        {isDesktop && (
          <aside className="bg-slate-50 border-l border-slate-200 overflow-y-auto p-3">
            {right}
          </aside>
        )}
      </div>

      {/* Mobile NAV slide-over (left) */}
      {isNarrow && navOpen && (
        <Drawer side="left" onClose={() => setNavOpen(false)}>
          {left}
        </Drawer>
      )}

      {/* Tablet/Mobile INSPECTOR slide-over (right) */}
      {!isDesktop && inspectorOpen && (
        <Drawer side="right" onClose={() => setInspectorOpen(false)}>
          {right}
        </Drawer>
      )}

      <div className="border-t border-slate-200 px-5 py-2.5 bg-white">{prompt}</div>
      {footer}
    </div>
  );
}

interface DrawerProps {
  side: 'left' | 'right';
  onClose: () => void;
  children: ReactNode;
}

function Drawer({ side, onClose, children }: DrawerProps) {
  // Close on Escape — keyboard accessibility for power users.
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [onClose]);

  return (
    <>
      {/* Backdrop — click to close */}
      <button
        onClick={onClose}
        className="fixed inset-0 bg-slate-900/30 z-40 cursor-default"
        aria-label="Close drawer"
        tabIndex={-1}
      />
      <aside
        className={`fixed top-0 bottom-0 ${side === 'left' ? 'left-0 border-r' : 'right-0 border-l'} w-[min(360px,80vw)] bg-slate-50 border-slate-200 z-50 overflow-y-auto p-3 shadow-xl animate-slide-${side}`}
        role="dialog"
        aria-modal="true"
      >
        {children}
      </aside>
    </>
  );
}
