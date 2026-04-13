"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Database, Settings, Users, FileText, MessageSquare } from "lucide-react";

export default function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();

  const navItems = [
    { name: "Datasources", href: "/admin/datasources", icon: Database },
    { name: "Semantic Layer", href: "/admin/semantic", icon: Settings },
    { name: "Users", href: "/admin/users", icon: Users },
    { name: "Audit Logs", href: "/admin/audit-logs", icon: FileText },
  ];

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar */}
      <div className="w-64 bg-white border-r border-gray-200 flex flex-col hidden md:flex shrink-0">
        <div className="p-4 border-b border-gray-200">
          <h1 className="text-xl font-bold text-gray-800 tracking-tight flex items-center gap-2">
            <span className="bg-purple-600 text-white p-1 rounded-md">
              <Settings className="w-5 h-5" />
            </span>
            Admin Panel
          </h1>
        </div>

        <nav className="flex-1 overflow-y-auto py-4 px-3 space-y-1">
          {navItems.map((item) => {
            const isActive = pathname.startsWith(item.href);
            return (
              <Link
                key={item.name}
                href={item.href}
                className={`flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                  isActive
                    ? "bg-purple-50 text-purple-700"
                    : "text-gray-600 hover:bg-gray-100 hover:text-gray-900"
                }`}
              >
                <item.icon className={`w-4 h-4 ${isActive ? "text-purple-600" : "text-gray-400"}`} />
                {item.name}
              </Link>
            );
          })}
        </nav>

        <div className="p-4 border-t border-gray-200">
          <Link
            href="/chat"
            className="flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium text-gray-600 hover:bg-gray-100 hover:text-gray-900 transition-colors"
          >
            <MessageSquare className="w-4 h-4 text-gray-400" />
            Back to Chat
          </Link>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col min-w-0 overflow-y-auto">
        <header className="h-14 border-b border-gray-200 bg-white flex items-center px-4 sm:px-6 z-10 shrink-0 md:hidden">
          <h1 className="text-lg font-bold text-gray-800">Admin Panel</h1>
        </header>
        <main className="flex-1 bg-white">
          {children}
        </main>
      </div>
    </div>
  );
}
