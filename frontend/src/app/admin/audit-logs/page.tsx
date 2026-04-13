"use client";

import React, { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";

interface AuditLog {
  id: number;
  user_id: number | null;
  action: string;
  datasource_id: number | null;
  sql_executed: string | null;
  row_count: number | null;
  duration_ms: number | null;
  created_at: string;
}

export default function AuditLogsPage() {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(false);
  
  // Filters
  const [userId, setUserId] = useState<string>("");
  const [datasourceId, setDatasourceId] = useState<string>("");
  const [action, setAction] = useState<string>("");
  const [page, setPage] = useState(1);
  const pageSize = 50;

  const fetchLogs = async () => {
    try {
      setLoading(true);
      const params = new URLSearchParams();
      params.append("page", page.toString());
      params.append("page_size", pageSize.toString());
      
      if (userId) params.append("user_id", userId);
      if (datasourceId) params.append("datasource_id", datasourceId);
      if (action) params.append("action", action);

      const res = await api.get<AuditLog[]>(`/admin/audit-logs?${params.toString()}`);
      setLogs(res);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs();
  }, [page]); // Re-fetch on page change

  const handleFilter = (e: React.FormEvent) => {
    e.preventDefault();
    if (page !== 1) {
      setPage(1); // Effect will trigger fetch
    } else {
      fetchLogs();
    }
  };

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold">Audit Logs</h1>
      </div>

      <div className="bg-gray-50 p-4 rounded-lg border">
        <form onSubmit={handleFilter} className="flex space-x-4 items-end">
          <div>
            <label className="block text-sm mb-1 text-gray-700">User ID</label>
            <input 
              type="number"
              className="border rounded p-2 text-sm w-32"
              placeholder="e.g. 1"
              value={userId}
              onChange={(e) => setUserId(e.target.value)}
            />
          </div>
          <div>
            <label className="block text-sm mb-1 text-gray-700">Datasource ID</label>
            <input 
              type="number"
              className="border rounded p-2 text-sm w-32"
              placeholder="e.g. 2"
              value={datasourceId}
              onChange={(e) => setDatasourceId(e.target.value)}
            />
          </div>
          <div>
            <label className="block text-sm mb-1 text-gray-700">Action</label>
            <select 
              className="border rounded p-2 text-sm w-40"
              value={action}
              onChange={(e) => setAction(e.target.value)}
            >
              <option value="">All Actions</option>
              <option value="query">query</option>
              <option value="login">login</option>
              <option value="create_datasource">create_datasource</option>
              <option value="update_datasource">update_datasource</option>
              <option value="delete_datasource">delete_datasource</option>
            </select>
          </div>
          <Button type="submit" variant="default">Filter</Button>
          <Button type="button" variant="outline" onClick={() => {
            setUserId(""); setDatasourceId(""); setAction("");
            if (page !== 1) setPage(1);
            else setTimeout(fetchLogs, 0); // Need to wait for states to clear if page is 1
          }}>Clear</Button>
        </form>
      </div>

      {loading ? (
        <div>Loading logs...</div>
      ) : (
        <div className="border rounded-lg overflow-hidden">
          <table className="w-full text-left text-sm">
            <thead className="bg-gray-50 text-gray-700 border-b">
              <tr>
                <th className="p-3 font-medium">ID</th>
                <th className="p-3 font-medium">Time</th>
                <th className="p-3 font-medium">User ID</th>
                <th className="p-3 font-medium">DS ID</th>
                <th className="p-3 font-medium">Action</th>
                <th className="p-3 font-medium">SQL / Details</th>
                <th className="p-3 font-medium text-right">Rows</th>
                <th className="p-3 font-medium text-right">Duration (ms)</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {logs.length === 0 && (
                <tr>
                  <td colSpan={8} className="p-4 text-center text-gray-500">
                    No audit logs found.
                  </td>
                </tr>
              )}
              {logs.map((log) => (
                <tr key={log.id} className="hover:bg-gray-50">
                  <td className="p-3 text-gray-500">#{log.id}</td>
                  <td className="p-3 whitespace-nowrap text-gray-600">{new Date(log.created_at).toLocaleString()}</td>
                  <td className="p-3">{log.user_id || "-"}</td>
                  <td className="p-3">{log.datasource_id || "-"}</td>
                  <td className="p-3">
                    <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium bg-purple-100 text-purple-800 uppercase tracking-wider">
                      {log.action}
                    </span>
                  </td>
                  <td className="p-3 font-mono text-[11px] text-gray-700 max-w-sm truncate" title={log.sql_executed || ""}>
                    {log.sql_executed || "-"}
                  </td>
                  <td className="p-3 text-right">{log.row_count ?? "-"}</td>
                  <td className="p-3 text-right">{log.duration_ms ? `${log.duration_ms}ms` : "-"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="flex justify-between items-center mt-4 text-sm text-gray-600">
        <div>
          Showing page {page} {logs.length === pageSize ? `(up to ${pageSize} items)` : `(${logs.length} items)`}
        </div>
        <div className="space-x-2">
          <Button 
            variant="outline" 
            size="sm" 
            disabled={page === 1 || loading} 
            onClick={() => setPage(p => p - 1)}
          >
            Previous
          </Button>
          <Button 
            variant="outline" 
            size="sm" 
            disabled={logs.length < pageSize || loading} 
            onClick={() => setPage(p => p + 1)}
          >
            Next
          </Button>
        </div>
      </div>
    </div>
  );
}
