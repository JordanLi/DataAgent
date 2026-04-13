import React from 'react'
import { Message } from '@/lib/types'
import { cn } from '@/lib/utils'
import { User, Bot, AlertCircle } from 'lucide-react'
import { SqlPreview } from './SqlPreview'
import { DataTable } from '../results/DataTable'
import { ChartView } from '../results/ChartView'
import { InsightSummary } from '../results/InsightSummary'

interface MessageBubbleProps {
  message: Message
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === 'user'

  return (
    <div className={cn("flex w-full", isUser ? "justify-end" : "justify-start")}>
      <div className={cn("flex max-w-[85%] gap-4", isUser ? "flex-row-reverse" : "flex-row")}>
        {/* Avatar */}
        <div className={cn(
          "flex-shrink-0 h-8 w-8 rounded-full flex items-center justify-center text-white shadow-sm mt-1",
          isUser ? "bg-blue-600" : "bg-emerald-600"
        )}>
          {isUser ? <User className="w-5 h-5" /> : <Bot className="w-5 h-5" />}
        </div>

        {/* Content */}
        <div className={cn(
          "flex flex-col gap-2 min-w-0",
          isUser ? "items-end" : "items-start"
        )}>
          {message.content && (
            <div className={cn(
              "px-4 py-3 rounded-2xl shadow-sm text-sm whitespace-pre-wrap leading-relaxed",
              isUser 
                ? "bg-blue-600 text-white rounded-tr-none" 
                : "bg-white border border-gray-100 text-gray-800 rounded-tl-none"
            )}>
              {message.content}
            </div>
          )}

          {!isUser && message.error && (
            <div className="flex items-start gap-2 bg-red-50 border border-red-200 text-red-800 p-3 rounded-lg text-sm w-full mt-2">
              <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
              <div className="whitespace-pre-wrap font-mono text-xs">{message.error}</div>
            </div>
          )}

          {!isUser && message.sql && (
            <div className="w-full">
              <SqlPreview 
                sql={message.sql} 
                executionTimeMs={message.result?.execution_time_ms}
                rowCount={message.result?.row_count}
              />
            </div>
          )}

          {!isUser && message.result && message.result.rows.length > 0 && (
            <div className="flex flex-col gap-4 w-full mt-2 overflow-hidden bg-gray-50/50 p-4 rounded-xl border border-gray-100">
              {message.result.chart_type !== 'none' && (
                <ChartView result={message.result} />
              )}
              <DataTable 
                columns={message.result.columns} 
                rows={message.result.rows} 
              />
              {message.result.insight && (
                <InsightSummary insight={message.result.insight} />
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
