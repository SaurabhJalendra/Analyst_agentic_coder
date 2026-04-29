// Phase 2: minimal; full sortable/filterable in Phase 3.
export interface DataTableProps {
  columns: string[];
  rows: (string | number)[][];
}

export function DataTable({ columns, rows }: DataTableProps) {
  return (
    <table className="w-full border-collapse font-mono text-[10px]">
      <thead>
        <tr className="bg-slate-50">
          {columns.map((c) => (
            <th key={c} className="border border-slate-200 px-2 py-1 text-left text-slate-600 font-semibold">{c}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((r, i) => (
          <tr key={i}>
            {r.map((cell, j) => (
              <td key={j} className="border border-slate-200 px-2 py-0.5 text-right first:text-left first:text-slate-600">{cell}</td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}
