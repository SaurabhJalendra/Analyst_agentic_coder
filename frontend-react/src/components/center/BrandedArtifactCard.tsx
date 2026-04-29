import { useState } from 'react';
import type { Artifact } from '../../types/domain';
import type { ReactNode } from 'react';
import { MethodologyPanel } from './MethodologyPanel';

export interface BrandedArtifactCardProps {
  artifact: Artifact;
  body: ReactNode;
}

export function BrandedArtifactCard({ artifact, body }: BrandedArtifactCardProps) {
  const [showMethodology, setShowMethodology] = useState(false);
  return (
    <div className="border border-slate-200 rounded-lg my-3 overflow-hidden">
      <div className="bg-gradient-to-b from-brand-900 to-brand-800 text-white px-3 py-2 flex justify-between text-[10px]">
        <span><strong>{artifact.title}</strong></span>
        <span className="text-gold-500 font-semibold tracking-wider">Q · QUANT CONSOLE</span>
      </div>
      <div className="p-3">{body}</div>
      <div className="text-[9px] text-slate-400 px-3 py-1.5 bg-slate-50 border-t border-slate-200 flex justify-between">
        <span>Source: {artifact.sourceAttribution}</span>
        <span
          onClick={() => setShowMethodology((v) => !v)}
          className="text-sky-700 cursor-pointer hover:text-sky-900"
        >
          {showMethodology ? '▾ Hide methodology' : '▸ How this was made'}
        </span>
      </div>
      {showMethodology && <MethodologyPanel artifactId={artifact.id} />}
    </div>
  );
}
