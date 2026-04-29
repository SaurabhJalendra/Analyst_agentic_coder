import { useState } from 'react';

export function ThinkingBlock({ tokens, preview }: { tokens: number; preview: string }) {
  const [open, setOpen] = useState(false);
  return (
    <div onClick={() => setOpen(!open)} className="bg-amber-100 rounded px-3 py-1.5 text-[10px] text-amber-900 my-2 cursor-pointer">
      <span>{open ? '▾' : '▸'} Methodology · {tokens.toLocaleString()} reasoning tokens</span>
      {open && <div className="mt-2 text-amber-800">{preview}</div>}
    </div>
  );
}
