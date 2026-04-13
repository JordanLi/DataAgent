"use client"

import React, { useEffect } from 'react'
import Link from 'next/link'
import { ChatPanel } from '@/components/chat/ChatPanel'
import { useChatStore } from '@/store/chatStore'
import { Database } from 'lucide-react'
import { DataSource } from '@/lib/types'

export default function ChatPage() {
  const { setDatasources, setSelectedDatasourceId, datasources, selectedDatasourceId } = useChatStore()

  // For MVP, we mock the datasources if API is not fully ready.
  // In real app, this fetches from /api/datasources
  useEffect(() => {
    const fetchDatasources = async () => {
      try {
        // const res = await api.get<{items: DataSource[]}>('/datasources')
        // setDatasources(res.items)
        
        // Mock data source for MVP testing without backend
        const mockSource: DataSource = {
          id: 1,
          name: 'Production DB (MySQL)',
          db_type: 'mysql',
          host: 'localhost',
          port: 3306,
          database: 'ecommerce',
          username: 'root',
          is_active: true,
          created_at: new Date().toISOString()
        }
        setDatasources([mockSource])
        setSelectedDatasourceId(mockSource.id)
      } catch (err) {
        console.error(err)
      }
    }
    fetchDatasources()
  }, [])

  return (
    <div className="flex h-screen bg-white">
      {/* Sidebar Placeholder */}
      <div className="w-64 border-r border-gray-200 bg-gray-50 flex flex-col hidden md:flex">
        <div className="p-4 border-b border-gray-200">
          <h1 className="text-xl font-bold text-gray-800 tracking-tight flex items-center gap-2">
            <span className="bg-blue-600 text-white p-1 rounded-md">
              <Database className="w-5 h-5" />
            </span>
            DataAgent
          </h1>
        </div>
        
        <div className="p-4 flex-1 overflow-y-auto">
          <button className="w-full bg-white border border-gray-200 text-sm font-medium rounded-md py-2 px-4 text-gray-700 hover:bg-gray-50 hover:text-blue-600 transition-colors shadow-sm mb-6">
            + 新建对话
          </button>
          
          <div className="space-y-1">
            <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">历史对话</h2>
            {/* Mock History Items */}
            <div className="text-sm text-gray-600 hover:bg-gray-100 p-2 rounded-md cursor-pointer transition-colors">
              上个月销量最高的商品
            </div>
            <div className="text-sm text-gray-600 hover:bg-gray-100 p-2 rounded-md cursor-pointer transition-colors">
              用户注册趋势分析
            </div>
          </div>
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col h-full min-w-0">
        {/* Top Header */}
        <header className="h-14 border-b border-gray-200 bg-white flex items-center justify-between px-4 sm:px-6 z-10 shrink-0">
          <div className="flex items-center gap-3">
            <span className="text-sm font-medium text-gray-500">当前数据源:</span>
            <select 
              className="text-sm border-gray-300 rounded-md bg-gray-50 py-1 pl-2 pr-8 focus:ring-blue-500 focus:border-blue-500"
              value={selectedDatasourceId || ''}
              onChange={(e) => setSelectedDatasourceId(Number(e.target.value))}
            >
              {datasources.map(ds => (
                <option key={ds.id} value={ds.id}>{ds.name}</option>
              ))}
            </select>
          </div>
          
          <div className="flex items-center gap-4">
            <Link 
              href="/admin/datasources" 
              className="text-sm font-medium text-gray-500 hover:text-gray-900 transition-colors"
            >
              管理后台
            </Link>
            <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-blue-600 to-blue-400 text-white flex items-center justify-center font-bold text-sm shadow-sm cursor-pointer hover:shadow transition-shadow">
              A
            </div>
          </div>
        </header>

        {/* Chat Panel */}
        <main className="flex-1 overflow-hidden">
          <ChatPanel />
        </main>
      </div>
    </div>
  )
}
