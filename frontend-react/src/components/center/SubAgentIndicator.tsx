import type { SubAgentMessage } from '../../types/domain';

const palette = {
  researcher: { bg: 'bg-sky-50',    border: 'border-sky-500',    name: 'text-sky-800' },
  verifier:   { bg: 'bg-fuchsia-50', border: 'border-purple-500', name: 'text-purple-700' },
  explore:    { bg: 'bg-emerald-50', border: 'border-emerald-500', name: 'text-emerald-700' },
  plan:       { bg: 'bg-amber-50',   border: 'border-amber-500',  name: 'text-amber-800' },
  general:    { bg: 'bg-slate-100',  border: 'border-slate-400',  name: 'text-slate-700' },
} as const;

function colorsFor(kind: string) {
  return (palette as Record<string, typeof palette.general>)[kind] ?? palette.general;
}

export function SubAgentIndicator({ msg }: { msg: SubAgentMessage }) {
  const c = colorsFor(msg.subKind);
  return (
    <div className={`${c.bg} ${c.border} border-l-[3px] rounded px-3 py-2 text-[10px] my-2`}>
      <strong className={c.name}>↳ {msg.subKind} subagent</strong> · {msg.status}
      {msg.statusText && <> · {msg.statusText}</>}
    </div>
  );
}
