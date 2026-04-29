// Phase 2: stub — concrete library chosen in Phase 3.
export function Chart({ title }: { title: string }) {
  return (
    <div className="h-24 bg-gradient-to-b from-emerald-50 to-white rounded flex items-center justify-center text-[10px] text-slate-500 italic">
      Chart placeholder · {title}
    </div>
  );
}
