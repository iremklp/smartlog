import {
  createColumnHelper,
  flexRender,
  getCoreRowModel,
  useReactTable
} from "@tanstack/react-table";

import { getEventParserName } from "../lib/api/contracts";
import type { StoredEvent } from "../lib/api/types";
import { formatDate } from "../lib/utils/format";

interface EventsTableProps {
  rows: StoredEvent[];
  onSelect?: (id: string) => void;
}

const columnHelper = createColumnHelper<StoredEvent>();

const columns = [
  columnHelper.accessor("id", {
    header: "Event ID",
    cell: (ctx) => <span className="font-mono text-xs text-inkSoft">{ctx.getValue()}</span>
  }),
  columnHelper.accessor((row) => row.event.timestamp, {
    id: "timestamp",
    header: "Timestamp",
    cell: (ctx) => formatDate(ctx.getValue())
  }),
  columnHelper.accessor((row) => row.event.severity, {
    id: "severity",
    header: "Severity"
  }),
  columnHelper.accessor((row) => getEventParserName(row.event) ?? "-", {
    id: "parser",
    header: "Parser"
  }),
  columnHelper.accessor((row) => row.event.message, {
    id: "message",
    header: "Message"
  })
];

export function EventsTable({ rows, onSelect }: EventsTableProps) {
  const table = useReactTable({
    data: rows,
    columns,
    getCoreRowModel: getCoreRowModel()
  });

  return (
    <div className="overflow-x-auto rounded-xl border border-white/10">
      <table className="min-w-full divide-y divide-white/10">
        <thead className="bg-black/20">
          {table.getHeaderGroups().map((headerGroup) => (
            <tr key={headerGroup.id}>
              {headerGroup.headers.map((header) => (
                <th
                  key={header.id}
                  className="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-inkSoft"
                >
                  {header.isPlaceholder
                    ? null
                    : flexRender(header.column.columnDef.header, header.getContext())}
                </th>
              ))}
            </tr>
          ))}
        </thead>
        <tbody className="divide-y divide-white/5">
          {table.getRowModel().rows.map((row) => (
            <tr
              key={row.id}
              className="cursor-pointer transition hover:bg-white/5"
              onClick={() => onSelect?.(row.original.id)}
            >
              {row.getVisibleCells().map((cell) => (
                <td key={cell.id} className="px-3 py-2 text-sm text-ink">
                  {flexRender(cell.column.columnDef.cell, cell.getContext())}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
