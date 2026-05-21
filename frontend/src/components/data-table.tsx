import { useState } from "react";

interface Column {
  key: string;
  label: string;
  render?: (value: any, row: any) => React.ReactNode;
}

interface DataTableProps {
  columns: Column[];
  data: any[];
  searchPlaceholder?: string;
  onSearch?: (term: string) => void;
}

export function DataTable({ columns, data, searchPlaceholder, onSearch }: DataTableProps) {
  const [localSearch, setLocalSearch] = useState("");

  return (
    <div>
      {onSearch && (
        <div className="mb-4">
          <input
            type="text"
            placeholder={searchPlaceholder || "Buscar..."}
            value={localSearch}
            onChange={(e) => { setLocalSearch(e.target.value); onSearch(e.target.value); }}
            className="w-full max-w-sm px-3 py-2 border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-green-500"
          />
        </div>
      )}
      <div className="overflow-x-auto border rounded-lg bg-white">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b">
            <tr>
              {columns.map((col) => (
                <th key={col.key} className="text-left px-4 py-3 font-medium text-gray-500">
                  {col.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.length === 0 ? (
              <tr>
                <td colSpan={columns.length} className="text-center text-gray-400 py-8">
                  No hay datos disponibles
                </td>
              </tr>
            ) : (
              data.map((row, i) => (
                <tr key={row.id ?? i} className="border-b last:border-0 hover:bg-gray-50">
                  {columns.map((col) => (
                    <td key={col.key} className="px-4 py-3">
                      {col.render ? col.render(row[col.key], row) : row[col.key] ?? "-"}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
