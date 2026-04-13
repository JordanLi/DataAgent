"use client";

import React, { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

interface User {
  id: number;
  username: string;
  role: string;
  is_active: boolean;
  created_at: string;
}

export default function UsersPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(false);
  
  const [editingUser, setEditingUser] = useState<Partial<User> & { password?: string } | null>(null);
  const [isNew, setIsNew] = useState(false);

  useEffect(() => {
    fetchUsers();
  }, []);

  const fetchUsers = async () => {
    try {
      setLoading(true);
      const res = await api.get<User[]>("/admin/users");
      setUsers(res);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm("Are you sure you want to delete this user?")) return;
    try {
      await api.delete(`/admin/users/${id}`);
      fetchUsers();
    } catch (err) {
      console.error(err);
      alert("Failed to delete user");
    }
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingUser) return;
    
    try {
      if (isNew) {
        await api.post("/admin/users", editingUser);
      } else {
        await api.patch(`/admin/users/${editingUser.id}`, editingUser);
      }
      setEditingUser(null);
      fetchUsers();
    } catch (err: any) {
      console.error(err);
      alert(err.message || "Failed to save user");
    }
  };

  const handleToggleStatus = async (user: User) => {
    try {
      await api.patch(`/admin/users/${user.id}`, { is_active: !user.is_active });
      fetchUsers();
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold">User Management</h1>
        <Button onClick={() => { 
          setIsNew(true); 
          setEditingUser({ username: "", role: "viewer", is_active: true }); 
        }}>
          Add User
        </Button>
      </div>

      {loading ? (
        <div>Loading users...</div>
      ) : (
        <div className="border rounded-lg overflow-hidden">
          <table className="w-full text-left text-sm">
            <thead className="bg-gray-50 text-gray-700">
              <tr>
                <th className="p-3 font-medium">Username</th>
                <th className="p-3 font-medium">Role</th>
                <th className="p-3 font-medium">Status</th>
                <th className="p-3 font-medium">Created At</th>
                <th className="p-3 font-medium text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {users.length === 0 && (
                <tr>
                  <td colSpan={5} className="p-4 text-center text-gray-500">
                    No users found.
                  </td>
                </tr>
              )}
              {users.map((user) => (
                <tr key={user.id} className="hover:bg-gray-50">
                  <td className="p-3 font-medium">{user.username}</td>
                  <td className="p-3">
                    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800">
                      {user.role}
                    </span>
                  </td>
                  <td className="p-3">
                    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${user.is_active ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}`}>
                      {user.is_active ? "Active" : "Inactive"}
                    </span>
                  </td>
                  <td className="p-3">{new Date(user.created_at).toLocaleString()}</td>
                  <td className="p-3 text-right space-x-2">
                    <Button variant="ghost" size="sm" onClick={() => handleToggleStatus(user)}>
                      {user.is_active ? "Disable" : "Enable"}
                    </Button>
                    <Button variant="ghost" size="sm" onClick={() => {
                      setIsNew(false);
                      setEditingUser(user);
                    }}>
                      Edit
                    </Button>
                    <Button variant="ghost" size="sm" className="text-red-600 hover:text-red-700" onClick={() => handleDelete(user.id)}>
                      Delete
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {editingUser && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full shadow-lg">
            <h2 className="text-xl font-semibold mb-4">{isNew ? "Add User" : "Edit User"}</h2>
            <form onSubmit={handleSave} className="space-y-4">
              <div>
                <label className="block text-sm mb-1">Username</label>
                <Input 
                  required 
                  disabled={!isNew}
                  value={editingUser.username || ""} 
                  onChange={e => setEditingUser({...editingUser, username: e.target.value})} 
                />
              </div>
              <div>
                <label className="block text-sm mb-1">Password {isNew ? "" : "(Leave blank to keep unchanged)"}</label>
                <Input 
                  type="password" 
                  required={isNew} 
                  value={editingUser.password || ""} 
                  onChange={e => setEditingUser({...editingUser, password: e.target.value})} 
                />
              </div>
              <div>
                <label className="block text-sm mb-1">Role</label>
                <select 
                  className="border rounded p-2 w-full"
                  value={editingUser.role || "viewer"}
                  onChange={e => setEditingUser({...editingUser, role: e.target.value})}
                >
                  <option value="admin">Admin</option>
                  <option value="analyst">Analyst</option>
                  <option value="viewer">Viewer</option>
                </select>
              </div>
              <div className="flex items-center space-x-2 pt-2">
                <input 
                  type="checkbox" 
                  id="isActive"
                  checked={editingUser.is_active ?? true}
                  onChange={e => setEditingUser({...editingUser, is_active: e.target.checked})}
                />
                <label htmlFor="isActive" className="text-sm">Account is active</label>
              </div>

              <div className="flex justify-end space-x-2 pt-4">
                <Button type="button" variant="ghost" onClick={() => setEditingUser(null)}>Cancel</Button>
                <Button type="submit">Save</Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
