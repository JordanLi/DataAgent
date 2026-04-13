"use client";

import React, { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { DatasourceForm } from "@/components/admin/DatasourceForm";

interface Datasource {
  id: number;
  name: string;
  db_type: string;
  host: string;
  port: number;
  database: string;
  username: string;
  created_at: string;
}

export default function DatasourcesPage() {
  const [datasources, setDatasources] = useState<Datasource[]>([]);
  const [loading, setLoading] = useState(true);
  const [editingId, setEditingId] = useState<number | null | "new">(null);
  const [discovering, setDiscovering] = useState<number | null>(null);

  const fetchDatasources = async () => {
    try {
      setLoading(true);
      const res = await api.get<Datasource[]>("/datasources");
      setDatasources(res);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDatasources();
  }, []);

  const handleDelete = async (id: number) => {
    if (!confirm("Are you sure you want to delete this datasource?")) return;
    try {
      await api.delete(`/datasources/${id}`);
      fetchDatasources();
    } catch (err) {
      console.error(err);
      alert("Failed to delete");
    }
  };

  const handleDiscover = async (id: number) => {
    setDiscovering(id);
    try {
      await api.post(`/datasources/${id}/discover`, {});
      alert("Schema discovery completed successfully!");
    } catch (err: any) {
      console.error(err);
      alert(err.message || "Failed to discover schema");
    } finally {
      setDiscovering(null);
    }
  };

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Datasources</h1>
        <Button onClick={() => setEditingId("new")}>Add Datasource</Button>
      </div>

      {editingId && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full shadow-lg">
            <h2 className="text-xl font-semibold mb-4">
              {editingId === "new" ? "Add Datasource" : "Edit Datasource"}
            </h2>
            <DatasourceForm
              initialData={
                editingId === "new"
                  ? undefined
                  : datasources.find((d) => d.id === editingId)
              }
              onSuccess={() => {
                setEditingId(null);
                fetchDatasources();
              }}
              onCancel={() => setEditingId(null)}
            />
          </div>
        </div>
      )}

      {loading ? (
        <div>Loading...</div>
      ) : (
        <div className="border rounded-lg overflow-hidden">
          <table className="w-full text-left text-sm">
            <thead className="bg-gray-50 text-gray-700">
              <tr>
                <th className="p-3 font-medium">Name</th>
                <th className="p-3 font-medium">Type</th>
                <th className="p-3 font-medium">Host/Database</th>
                <th className="p-3 font-medium text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {datasources.length === 0 && (
                <tr>
                  <td colSpan={4} className="p-4 text-center text-gray-500">
                    No datasources configured yet.
                  </td>
                </tr>
              )}
              {datasources.map((ds) => (
                <tr key={ds.id} className="hover:bg-gray-50">
                  <td className="p-3 font-medium">{ds.name}</td>
                  <td className="p-3">
                    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800">
                      {ds.db_type}
                    </span>
                  </td>
                  <td className="p-3">
                    {ds.host}:{ds.port} / {ds.database}
                  </td>
                  <td className="p-3 text-right space-x-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleDiscover(ds.id)}
                      disabled={discovering === ds.id}
                    >
                      {discovering === ds.id ? "Discovering..." : "Discover Schema"}
                    </Button>
                    <Button variant="ghost" size="sm" onClick={() => setEditingId(ds.id)}>
                      Edit
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="text-red-600 hover:text-red-700"
                      onClick={() => handleDelete(ds.id)}
                    >
                      Delete
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
