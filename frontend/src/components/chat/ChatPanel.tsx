"use client"

import React, { useEffect, useRef } from 'react'
import { useChatStore } from '@/store/chatStore'
import { MessageBubble } from './MessageBubble'
import { QueryInput } from './QueryInput'
import { chatStream } from '@/lib/api'
import { Message, QueryResult } from '@/lib/types'

export function ChatPanel() {
  const { 
    messages, 
    addMessage, 
    updateMessage, 
    selectedDatasourceId,
    currentConversationId,
    setCurrentConversationId,
    setIsStreaming,
    isStreaming
  } = useChatStore()
  
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSend = async (text: string) => {
    if (!selectedDatasourceId) {
      alert("请先选择一个数据源")
      return
    }

    const userMessageId = Math.random().toString(36).substring(7)
    const userMessage: Message = {
      id: userMessageId,
      role: 'user',
      content: text,
      created_at: new Date().toISOString()
    }

    addMessage(userMessage)
    
    const botMessageId = Math.random().toString(36).substring(7)
    const botMessage: Message = {
      id: botMessageId,
      role: 'assistant',
      content: '',
      created_at: new Date().toISOString()
    }
    
    addMessage(botMessage)
    setIsStreaming(true)

    try {
      const stream = chatStream({
        conversation_id: currentConversationId,
        datasource_id: selectedDatasourceId,
        question: text
      })

      for await (const chunk of stream) {
        const { event, data } = chunk
        if (!data) continue

        const payload = JSON.parse(data)
        
        switch (payload.type) {
          case 'sql':
          case 'sql_rewritten':
            updateMessage(botMessageId, { sql: payload.content })
            break
            
          case 'result': {
            const formattedRows = Array.isArray(payload.rows) 
              ? payload.rows.map((rowArr: any) => {
                  if (Array.isArray(rowArr)) {
                    const obj: Record<string, any> = {}
                    payload.columns.forEach((col: string, i: number) => {
                      obj[col] = rowArr[i]
                    })
                    return obj
                  }
                  return rowArr // fallback if it's already an object
                })
              : []

            updateMessage(botMessageId, { 
              result: {
                columns: payload.columns,
                rows: formattedRows,
                row_count: payload.row_count,
                execution_time_ms: payload.execution_time_ms,
                chart_type: 'none',
                insight: ''
              } 
            })
            break
          }
            
          case 'summary':
            const existingResult = useChatStore.getState().messages.find((m) => m.id === botMessageId)?.result
            
            // If the backend didn't send 'result' yet or it's missing, create a blank one
            updateMessage(botMessageId, { 
              result: {
                columns: existingResult?.columns ?? [],
                rows: existingResult?.rows ?? [],
                row_count: existingResult?.row_count ?? 0,
                execution_time_ms: existingResult?.execution_time_ms ?? 0,
                insight: payload.content,
                chart_type: payload.chart_type ?? existingResult?.chart_type ?? 'none'
              } satisfies QueryResult
            })
            break
            
          case 'error':
            updateMessage(botMessageId, { error: payload.content })
            break
            
          case 'done':
            setIsStreaming(false)
            if (payload.conversation_id && !currentConversationId) {
              setCurrentConversationId(payload.conversation_id)
            }
            break
            
          case 'thinking':
          case 'sql_stream':
            // Ignore these for now, or update UI to show progress if desired
            break
            
          default:
            console.warn('Unknown event type', payload.type)
        }
      }
    } catch (err: any) {
      updateMessage(botMessageId, { error: err.message || '发生未知错误' })
    } finally {
      setIsStreaming(false)
    }
  }

  return (
    <div className="flex flex-col h-full bg-gray-50/30 relative">
      <div className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8 space-y-6">
        {messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-gray-400 mt-20">
            <div className="w-16 h-16 bg-blue-50 text-blue-600 rounded-2xl flex items-center justify-center mb-6 shadow-sm">
              <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
              </svg>
            </div>
            <h3 className="text-xl font-semibold text-gray-700 mb-2">我是 DataAgent，您的数据助手</h3>
            <p className="text-sm max-w-sm text-center">
              使用自然语言查询数据，我会自动生成 SQL、执行查询，并以表格和图表的形式返回结果。
            </p>
          </div>
        ) : (
          <div className="max-w-4xl mx-auto space-y-8">
            {messages.map((msg) => (
              <MessageBubble key={msg.id} message={msg} />
            ))}
            <div ref={bottomRef} className="h-4" />
          </div>
        )}
      </div>

      <div className="p-4 sm:p-6 bg-gradient-to-t from-gray-50 to-transparent sticky bottom-0 w-full">
        <QueryInput onSend={handleSend} disabled={isStreaming} />
      </div>
    </div>
  )
}
