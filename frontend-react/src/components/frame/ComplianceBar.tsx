// frontend-react/src/components/frame/ComplianceBar.tsx
export interface ComplianceBarProps {
  lastRefresh?: string;
}

/**
 * Honest pilot-stage disclosure bar.
 *
 * The earlier "Entitlements: ..." and "MNPI walls: ON" pills were removed —
 * nothing in the call path enforced them, so they were compliance theater.
 * They return only when a real entitlements service exists (see
 * docs/adr/0004-no-auth-v1.md and audit finding C2).
 */
export function ComplianceBar({ lastRefresh }: ComplianceBarProps) {
  return (
    <div className="bg-amber-50 border-b border-amber-300 px-5 py-1 text-[10px] text-amber-900 flex gap-3.5 flex-wrap items-center">
      <span>
        ⚠ Single-user local pilot · AI-generated output — verify before acting · Not investment advice
      </span>
      {lastRefresh && <span className="ml-auto">{lastRefresh}</span>}
    </div>
  );
}
