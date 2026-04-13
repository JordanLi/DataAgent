"use client";

import React, { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";

interface ColumnMeta {
  name: string;
  type: string;
  comment?: string;
  is_primary?: boolean;
}

interface TableMetadata {
  id: number;
  table_name: string;
  table_comment: string | null;
  columns_json: string | null;
}

interface SchemaViewerProps {
  datasourceId: number;
  onAddAlias: (tableName: string, columnName: string) => void;
}

export function SchemaViewer({ datasourceId, onAddAlias }: SchemaViewerProps) {
  const [tables, setTables] = useState<TableMetadata[]>([]);
  const [loading, setLoading] = useState(false);
  const [expandedTables, setExpandedTables] = useState<Record<string, boolean>>({});

  useEffect(() => {
    if (!datasourceId) return;
    fetchSchema();
  }, [datasourceId]);

  const fetchSchema = async () => {
    try {
      setLoading(true);
      const res = await api.get<TableMetadata[]>(`/datasources/${datasourceId}/schema`);
      setTables(res);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const toggleTable = (tableName: string) => {
    setExpandedTables((prev) => ({
      ...prev,
      [tableName]: !prev[tableName],
    }));
  };

  if (loading) {
    return <div className="text-sm text-gray-500">Loading schema...</div>;
  }

  if (tables.length === 0) {
    return (
      <div className="text-sm text-gray-500">
        No schema found. Have you run "Discover Schema"?
      </div>
    );
  }

  return (
    <div className="border rounded-lg p-4 bg-white space-y-2 h-full overflow-y-auto">
      <h3 className="font-semibold text-lg mb-4">Schema Explorer</h3>
      {tables.map((table) => {
        let columns: ColumnMeta[] = [];
        try {
          if (table.columns_json) {
            columns = JSON.parse(table.columns_json);
          }
        } catch (e) {
          // ignore
        }

        const isExpanded = expandedTables[table.table_name];

        return (
          <div key={table.table_name} className="border-b last:border-0 pb-2 mb-2">
            <div
              className="flex items-center justify-between cursor-pointer hover:bg-gray-50 p-2 rounded"
              onClick={() => toggleTable(table.table_name)}
            >
              <div className="flex items-center space-x-2">
                <span className="text-gray-500">{isExpanded ? "▼" : "▶"}</span>
                <span className="font-medium">{table.table_name}</span>
                {table.table_comment && (
                  <span className="text-xs text-gray-400">({table.table_comment})</span>
                )}
              </div>
            </div>
            {isExpanded && (
              <div className="pl-6 pr-2 mt-2 space-y-1">
                {columns.map((col) => (
                  <div
                    key={col.name}
                    className="flex justify-between items-center group text-sm py-1 hover:bg-gray-50 rounded px-2"
                  >
                    <div className="flex items-center space-x-2">
                      <span className="font-mono text-blue-600">{col.name}</span>
                      <span className="text-xs text-gray-500">{col.type}</span>
                      {col.is_primary && (
                        <span className="text-[10px] bg-yellow-100 text-yellow-800 px-1 rounded">PK</span>
                      )}
                      {col.comment && (
                        <span className="text-xs text-gray-400 truncate max-w-[150px]">
                          - {col.comment}
                        </span>
                      )}
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="opacity-0 group-hover:opacity-100 h-6 px-2 text-xs"
                      onClick={(e) => {
                        e.stopPropagation();
                        onAddAlias(table.table_name, col.name);
                      }}
                    >
                      + Alias
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
