// frontend-react/src/components/frame/ComplianceBar.tsx
export interface ComplianceBarProps {
  entitlements?: string;
  mnpiOn?: boolean;
  lastRefresh?: string;
}

export function ComplianceBar({ entitlements, mnpiOn, lastRefresh }: ComplianceBarProps) {
  return (
    <div className="bg-amber-50 border-b border-amber-300 px-5 py-1 text-[10px] text-amber-900 flex gap-3.5 flex-wrap items-center">
      <span>⚠ Institutional clients only · Not investment advice · See disclosures</span>
      {entitlements && (
        <span className="bg-white border border-amber-300 rounded-full px-2 py-0.5 text-[9px]">
          Entitlements: {entitlements}
        </span>
      )}
      {mnpiOn !== undefined && (
        <span className="bg-white border border-amber-300 rounded-full px-2 py-0.5 text-[9px]">
          MNPI walls: {mnpiOn ? 'ON' : 'OFF'}
        </span>
      )}
      {lastRefresh && <span className="ml-auto">{lastRefresh}</span>}
    </div>
  );
}
