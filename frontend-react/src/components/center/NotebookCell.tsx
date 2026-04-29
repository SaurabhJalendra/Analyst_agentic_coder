import type { ReactNode } from 'react';
import { CodeBlock } from '../renderers/CodeBlock';

export interface NotebookCellProps {
  title: string;
  language?: string;
  code: string;
  output?: ReactNode;
}

export function NotebookCell({ title, language, code, output }: NotebookCellProps) {
  return (
    <div className="border border-slate-200 rounded-lg my-3 overflow-hidden">
      <div className="bg-slate-50 px-2.5 py-1 font-mono text-[10px] text-slate-600 border-b border-slate-200">{title}</div>
      <CodeBlock code={code} language={language} />
      {output && <div className="px-2.5 py-2 bg-white">{output}</div>}
    </div>
  );
}
