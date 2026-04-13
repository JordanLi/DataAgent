"use client";

import React, { useState, useEffect } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { SchemaViewer } from "./SchemaViewer";

interface Datasource {
  id: number;
  name: string;
}

export function SemanticEditor() {
  const [datasources, setDatasources] = useState<Datasource[]>([]);
  const [selectedDs, setSelectedDs] = useState<number | null>(null);
  const [activeTab, setActiveTab] = useState<"terms" | "aliases" | "enums" | "relations">("terms");

  // Data states
  const [terms, setTerms] = useState<any[]>([]);
  const [aliases, setAliases] = useState<any[]>([]);
  const [enums, setEnums] = useState<any[]>([]);
  const [relations, setRelations] = useState<any[]>([]);

  // Add/Edit states
  const [editingItem, setEditingItem] = useState<any | null>(null);
  const [isNew, setIsNew] = useState(false);

  useEffect(() => {
    api.get<Datasource[]>("/datasources")
      .then((data) => {
        setDatasources(data);
        if (data.length > 0) setSelectedDs(data[0].id);
      })
      .catch((err) => {
        console.error("Failed to load datasources:", err);
      });
  }, []);

  useEffect(() => {
    if (!selectedDs) return;
    fetchData();
  }, [selectedDs, activeTab]);

  const fetchData = async () => {
    try {
      const res = await api.get(`/semantic/datasources/${selectedDs}/${activeTab}`);
      if (activeTab === "terms") setTerms(res as any);
      if (activeTab === "aliases") setAliases(res as any);
      if (activeTab === "enums") setEnums(res as any);
      if (activeTab === "relations") setRelations(res as any);
    } catch (err) {
      console.error(err);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm("Are you sure?")) return;
    try {
      await api.delete(`/semantic/datasources/${selectedDs}/${activeTab}/${id}`);
      fetchData();
    } catch (err) {
      console.error(err);
    }
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (isNew) {
        await api.post(`/semantic/datasources/${selectedDs}/${activeTab}`, editingItem);
      } else {
        await api.patch(`/semantic/datasources/${selectedDs}/${activeTab}/${editingItem.id}`, editingItem);
      }
      setEditingItem(null);
      fetchData();
    } catch (err) {
      console.error(err);
      alert("Failed to save");
    }
  };

  if (!selectedDs) {
    return <div>No datasources available. Please add one first.</div>;
  }

  const renderTable = (headers: string[], fields: string[], data: any[]) => (
    <div className="border rounded-lg overflow-hidden mt-4">
      <table className="w-full text-left text-sm">
        <thead className="bg-gray-50">
          <tr>
            {headers.map((h, i) => (
              <th key={i} className="p-3 font-medium">{h}</th>
            ))}
            <th className="p-3 font-medium text-right">Actions</th>
          </tr>
        </thead>
        <tbody className="divide-y">
          {data.length === 0 && (
            <tr>
              <td colSpan={headers.length + 1} className="p-4 text-center text-gray-500">
                No items found.
              </td>
            </tr>
          )}
          {data.map((item) => (
            <tr key={item.id} className="hover:bg-gray-50">
              {fields.map((f, i) => (
                <td key={i} className="p-3">{item[f]}</td>
              ))}
              <td className="p-3 text-right space-x-2">
                <Button variant="ghost" size="sm" onClick={() => { setEditingItem(item); setIsNew(false); }}>
                  Edit
                </Button>
                <Button variant="ghost" size="sm" className="text-red-600" onClick={() => handleDelete(item.id)}>
                  Delete
                </Button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );

  const handleAddAlias = (tableName: string, columnName: string) => {
    setActiveTab("aliases");
    setEditingItem({
      table_name: tableName,
      column_name: columnName,
      alias_name: "",
      description: ""
    });
    setIsNew(true);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center space-x-4">
        <label className="font-medium">Select Datasource:</label>
        <select
          className="border rounded p-2"
          value={selectedDs}
          onChange={(e) => setSelectedDs(Number(e.target.value))}
        >
          {datasources.map((ds) => (
            <option key={ds.id} value={ds.id}>{ds.name}</option>
          ))}
        </select>
      </div>

      <div className="flex gap-6 h-[75vh]">
        {/* Left column: Schema Viewer */}
        <div className="w-1/3 h-full">
          <SchemaViewer datasourceId={selectedDs} onAddAlias={handleAddAlias} />
        </div>

        {/* Right column: Semantic Editor */}
        <div className="w-2/3 flex flex-col space-y-6 h-full overflow-y-auto pr-2">
          <div className="flex border-b space-x-4 shrink-0">
            {(["terms", "aliases", "enums", "relations"] as const).map((tab) => (
              <button
                key={tab}
                className={`pb-2 px-1 capitalize ${activeTab === tab ? "border-b-2 border-black font-semibold" : "text-gray-500"}`}
                onClick={() => setActiveTab(tab)}
              >
                {tab}
              </button>
            ))}
          </div>

          <div className="flex justify-between items-center shrink-0">
            <h2 className="text-lg font-semibold capitalize">{activeTab}</h2>
            <Button onClick={() => { setEditingItem({}); setIsNew(true); }}>Add New</Button>
          </div>

          <div className="flex-1 overflow-y-auto">
            {activeTab === "terms" && renderTable(["Term Name", "Definition", "SQL Expression"], ["term_name", "definition", "sql_expression"], terms)}
            {activeTab === "aliases" && renderTable(["Table", "Column", "Alias", "Description"], ["table_name", "column_name", "alias_name", "description"], aliases)}
            {activeTab === "enums" && renderTable(["Table", "Column", "Value", "Label"], ["table_name", "column_name", "enum_value", "display_label"], enums)}
            {activeTab === "relations" && renderTable(["Source", "Target", "Type"], ["source_table", "target_table", "relation_type"], relations)}
          </div>
        </div>
      </div>

      {editingItem && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full shadow-lg">
            <h2 className="text-xl font-semibold mb-4 capitalize">{isNew ? "Add" : "Edit"} {activeTab}</h2>
            <form onSubmit={handleSave} className="space-y-4">
              {activeTab === "terms" && (
                <>
                  <div>
                    <label className="block text-sm mb-1">Term Name</label>
                    <Input required value={editingItem.term_name || ""} onChange={e => setEditingItem({...editingItem, term_name: e.target.value})} />
                  </div>
                  <div>
                    <label className="block text-sm mb-1">Definition</label>
                    <Input value={editingItem.definition || ""} onChange={e => setEditingItem({...editingItem, definition: e.target.value})} />
                  </div>
                  <div>
                    <label className="block text-sm mb-1">SQL Expression</label>
                    <Input required value={editingItem.sql_expression || ""} onChange={e => setEditingItem({...editingItem, sql_expression: e.target.value})} />
                  </div>
                </>
              )}
              {activeTab === "aliases" && (
                <>
                  <div>
                    <label className="block text-sm mb-1">Table Name</label>
                    <Input required value={editingItem.table_name || ""} onChange={e => setEditingItem({...editingItem, table_name: e.target.value})} />
                  </div>
                  <div>
                    <label className="block text-sm mb-1">Column Name</label>
                    <Input required value={editingItem.column_name || ""} onChange={e => setEditingItem({...editingItem, column_name: e.target.value})} />
                  </div>
                  <div>
                    <label className="block text-sm mb-1">Alias Name</label>
                    <Input required value={editingItem.alias_name || ""} onChange={e => setEditingItem({...editingItem, alias_name: e.target.value})} />
                  </div>
                  <div>
                    <label className="block text-sm mb-1">Description</label>
                    <Input value={editingItem.description || ""} onChange={e => setEditingItem({...editingItem, description: e.target.value})} />
                  </div>
                </>
              )}
              {activeTab === "enums" && (
                <>
                  <div>
                    <label className="block text-sm mb-1">Table Name</label>
                    <Input required value={editingItem.table_name || ""} onChange={e => setEditingItem({...editingItem, table_name: e.target.value})} />
                  </div>
                  <div>
                    <label className="block text-sm mb-1">Column Name</label>
                    <Input required value={editingItem.column_name || ""} onChange={e => setEditingItem({...editingItem, column_name: e.target.value})} />
                  </div>
                  <div>
                    <label className="block text-sm mb-1">Enum Value</label>
                    <Input required value={editingItem.enum_value || ""} onChange={e => setEditingItem({...editingItem, enum_value: e.target.value})} />
                  </div>
                  <div>
                    <label className="block text-sm mb-1">Display Label</label>
                    <Input required value={editingItem.display_label || ""} onChange={e => setEditingItem({...editingItem, display_label: e.target.value})} />
                  </div>
                </>
              )}
              {activeTab === "relations" && (
                <>
                  <div>
                    <label className="block text-sm mb-1">Source Table</label>
                    <Input required value={editingItem.source_table || ""} onChange={e => setEditingItem({...editingItem, source_table: e.target.value})} />
                  </div>
                  <div>
                    <label className="block text-sm mb-1">Source Column</label>
                    <Input required value={editingItem.source_column || ""} onChange={e => setEditingItem({...editingItem, source_column: e.target.value})} />
                  </div>
                  <div>
                    <label className="block text-sm mb-1">Target Table</label>
                    <Input required value={editingItem.target_table || ""} onChange={e => setEditingItem({...editingItem, target_table: e.target.value})} />
                  </div>
                  <div>
                    <label className="block text-sm mb-1">Target Column</label>
                    <Input required value={editingItem.target_column || ""} onChange={e => setEditingItem({...editingItem, target_column: e.target.value})} />
                  </div>
                  <div>
                    <label className="block text-sm mb-1">Relation Type</label>
                    <select className="border rounded p-2 w-full" value={editingItem.relation_type || "one_to_many"} onChange={e => setEditingItem({...editingItem, relation_type: e.target.value})}>
                      <option value="one_to_one">One to One</option>
                      <option value="one_to_many">One to Many</option>
                      <option value="many_to_one">Many to One</option>
                      <option value="many_to_many">Many to Many</option>
                    </select>
                  </div>
                </>
              )}

              <div className="flex justify-end space-x-2 pt-4">
                <Button type="button" variant="ghost" onClick={() => setEditingItem(null)}>Cancel</Button>
                <Button type="submit">Save</Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
