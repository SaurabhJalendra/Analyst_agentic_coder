// frontend-react/src/components/frame/ComplianceFooter.tsx
export interface ComplianceFooterProps {
  auditId?: string;
  rmName?: string;
}

export function ComplianceFooter({ auditId, rmName }: ComplianceFooterProps) {
  return (
    <footer className="bg-brand-900 text-slate-400 px-5 py-2.5 text-[9px] leading-relaxed">
      <strong className="text-slate-300">Disclosures.</strong> Provided by the institution for institutional clients only. Not investment advice. AI-generated; verify before acting. Sources: Bloomberg, S&P Global, MSCI, FactSet, GIR Research, internal models.
      {auditId && <> Audit ID: <strong className="text-slate-300">{auditId}</strong>.</>}
      {' '}Support: clients@institution{rmName && <> · RM: {rmName}</>}.
    </footer>
  );
}
