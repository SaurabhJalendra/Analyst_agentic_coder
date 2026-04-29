import { useMemo, useState } from 'react';
import {
  type ColumnDef,
  flexRender,
  getCoreRowModel,
  getSortedRowModel,
  type SortingState,
  useReactTable,
} from '@tanstack/react-table';

export interface DataTableProps<T extends object> {
  columns: ColumnDef<T>[];
  data: T[];
}

export function DataTable<T extends object>({ columns, data }: DataTableProps<T>) {
  const [sorting, setSorting] = useState<SortingState>([]);
  const table = useReactTable({
    data,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  });

  return (
    <table className="w-full border-collapse font-mono text-[10px]">
      <thead>
        {table.getHeaderGroups().map((hg) => (
          <tr key={hg.id} className="bg-slate-50">
            {hg.headers.map((h) => (
              <th
                key={h.id}
                onClick={h.column.getToggleSortingHandler()}
                className="border border-slate-200 px-2 py-1 text-left text-slate-600 font-semibold cursor-pointer select-none hover:text-slate-900"
              >
                {flexRender(h.column.columnDef.header, h.getContext())}
                {{ asc: ' ▲', desc: ' ▼' }[h.column.getIsSorted() as string] ?? ''}
              </th>
            ))}
          </tr>
        ))}
      </thead>
      <tbody>
        {table.getRowModel().rows.map((row) => (
          <tr key={row.id}>
            {row.getVisibleCells().map((cell) => (
              <td key={cell.id} className="border border-slate-200 px-2 py-0.5 text-right first:text-left first:text-slate-600">
                {flexRender(cell.column.columnDef.cell, cell.getContext())}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

// Convenience helper for the common case of "string|number 2D array with column headers"
export function SimpleTable({ columns, rows }: { columns: string[]; rows: (string | number)[][] }) {
  type Row = Record<string, string | number>;
  const data = useMemo<Row[]>(
    () => rows.map((r) => Object.fromEntries(columns.map((c, i) => [c, r[i]] as const)) as Row),
    [columns, rows],
  );
  const cols = useMemo<ColumnDef<Row>[]>(
    () => columns.map((c) => ({ accessorKey: c, header: c })),
    [columns],
  );
  return <DataTable columns={cols} data={data} />;
}
