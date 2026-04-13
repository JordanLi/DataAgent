"use client";

import React, { useState } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

interface Datasource {
  id?: number;
  name: string;
  db_type: string;
  host: string;
  port: number;
  database: string;
  username: string;
  password?: string;
}

export function DatasourceForm({
  initialData,
  onSuccess,
  onCancel,
}: {
  initialData?: Datasource;
  onSuccess: () => void;
  onCancel: () => void;
}) {
  const [formData, setFormData] = useState<Datasource>(
    initialData || {
      name: "",
      db_type: "mysql",
      host: "localhost",
      port: 3306,
      database: "",
      username: "",
      password: "",
    }
  );
  const [loading, setLoading] = useState(false);
  const [testing, setTesting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: name === "port" ? parseInt(value) || 0 : value,
    }));
  };

  const handleTest = async () => {
    if (!initialData?.id) {
      setError("Please save the datasource first before testing.");
      return;
    }
    setTesting(true);
    setError(null);
    try {
      await api.post(`/datasources/${initialData.id}/test`, {});
      alert("Connection successful!");
    } catch (err: any) {
      setError(err.message || "Test failed");
    } finally {
      setTesting(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      if (initialData?.id) {
        await api.patch(`/datasources/${initialData.id}`, formData);
      } else {
        await api.post("/datasources", formData);
      }
      onSuccess();
    } catch (err: any) {
      setError(err.message || "Failed to save datasource");
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {error && <div className="text-red-500 text-sm">{error}</div>}
      
      <div>
        <label className="block text-sm font-medium mb-1">Name</label>
        <Input required name="name" value={formData.name} onChange={handleChange} />
      </div>
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium mb-1">Host</label>
          <Input required name="host" value={formData.host} onChange={handleChange} />
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">Port</label>
          <Input required type="number" name="port" value={formData.port} onChange={handleChange} />
        </div>
      </div>
      <div>
        <label className="block text-sm font-medium mb-1">Database</label>
        <Input required name="database" value={formData.database} onChange={handleChange} />
      </div>
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium mb-1">Username</label>
          <Input required name="username" value={formData.username} onChange={handleChange} />
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">Password</label>
          <Input type="password" name="password" value={formData.password} onChange={handleChange} />
        </div>
      </div>

      <div className="flex justify-end space-x-2 pt-4">
        {initialData?.id && (
          <Button type="button" variant="outline" onClick={handleTest} disabled={testing || loading}>
            {testing ? "Testing..." : "Test Connection"}
          </Button>
        )}
        <Button type="button" variant="ghost" onClick={onCancel} disabled={loading || testing}>
          Cancel
        </Button>
        <Button type="submit" disabled={loading || testing}>
          {loading ? "Saving..." : "Save"}
        </Button>
      </div>
    </form>
  );
}
