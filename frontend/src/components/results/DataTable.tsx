import React from 'react'

interface DataTableProps {
  columns: string[]
  rows: Record<string, unknown>[]
}

export function DataTable({ columns, rows }: DataTableProps) {
  if (!columns?.length) return null

  return (
    <div className="w-full overflow-auto rounded-md border border-gray-200 bg-white">
      <table className="w-full text-sm text-left">
        <thead className="bg-gray-50 border-b border-gray-200">
          <tr>
            {columns.map((col) => (
              <th key={col} className="px-4 py-3 font-semibold text-gray-700 truncate max-w-xs">
                {col}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {rows.map((row, i) => (
            <tr key={i} className="hover:bg-gray-50">
              {columns.map((col) => (
                <td key={`${i}-${col}`} className="px-4 py-2 truncate max-w-xs text-gray-600">
                  {String(row[col] ?? '')}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
