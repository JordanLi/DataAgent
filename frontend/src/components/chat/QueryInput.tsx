"use client"

import React, { useRef } from 'react'
import { Send, CornerDownLeft } from 'lucide-react'
import { Textarea } from '@/components/ui/textarea'
import { Button } from '@/components/ui/button'
import { useChatStore } from '@/store/chatStore'

interface QueryInputProps {
  onSend: (text: string) => void
  disabled?: boolean
}

export function QueryInput({ onSend, disabled }: QueryInputProps) {
  const [input, setInput] = React.useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const handleSend = () => {
    if (!input.trim() || disabled) return
    onSend(input.trim())
    setInput('')
    textareaRef.current?.focus()
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="relative flex w-full max-w-4xl mx-auto flex-col rounded-xl border border-gray-200 bg-white p-2 shadow-sm focus-within:ring-2 focus-within:ring-blue-500 focus-within:ring-opacity-50">
      <Textarea
        ref={textareaRef}
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="在这里输入您的问题，例如：'上个月订单量最多的十个商品是什么？'"
        className="min-h-[60px] max-h-[200px] border-0 focus-visible:ring-0 resize-none shadow-none text-base p-2"
        disabled={disabled}
      />
      <div className="flex items-center justify-between mt-2 px-2">
        <div className="text-xs text-gray-400 flex items-center gap-1">
          <CornerDownLeft className="w-3 h-3" /> 按 Enter 发送，Shift + Enter 换行
        </div>
        <Button 
          size="icon" 
          onClick={handleSend}
          disabled={!input.trim() || disabled}
          className="h-8 w-8 rounded-lg bg-blue-600 hover:bg-blue-700"
        >
          <Send className="h-4 w-4" />
        </Button>
      </div>
    </div>
  )
}
