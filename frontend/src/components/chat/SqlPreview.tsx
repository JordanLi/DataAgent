"use client"

import React from 'react'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism'
import { ChevronDown, ChevronRight, Database } from 'lucide-react'

interface SqlPreviewProps {
  sql: string
  executionTimeMs?: number
  rowCount?: number
}

export function SqlPreview({ sql, executionTimeMs, rowCount }: SqlPreviewProps) {
  const [isOpen, setIsOpen] = React.useState(false)

  if (!sql) return null

  return (
    <div className="mt-2 mb-4 border border-gray-200 rounded-md overflow-hidden bg-gray-50">
      <button 
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center w-full px-3 py-2 text-sm text-gray-700 hover:bg-gray-100 transition-colors"
      >
        {isOpen ? <ChevronDown className="w-4 h-4 mr-2" /> : <ChevronRight className="w-4 h-4 mr-2" />}
        <Database className="w-4 h-4 mr-2 text-blue-600" />
        <span className="font-medium">生成的 SQL 查询</span>
        {executionTimeMs !== undefined && rowCount !== undefined && (
          <span className="ml-auto text-xs text-gray-500">
            {rowCount} 行 · {executionTimeMs}ms
          </span>
        )}
      </button>
      
      {isOpen && (
        <div className="border-t border-gray-200">
          <SyntaxHighlighter
            language="sql"
            style={vscDarkPlus}
            customStyle={{ margin: 0, borderRadius: 0, fontSize: '0.875rem' }}
          >
            {sql}
          </SyntaxHighlighter>
        </div>
      )}
    </div>
  )
}
