import React from 'react'
import { Lightbulb } from 'lucide-react'

interface InsightSummaryProps {
  insight: string
}

export function InsightSummary({ insight }: InsightSummaryProps) {
  if (!insight) return null

  return (
    <div className="bg-blue-50 border border-blue-100 rounded-md p-4 mt-2">
      <div className="flex items-start gap-2">
        <Lightbulb className="w-5 h-5 text-blue-600 mt-0.5 flex-shrink-0" />
        <div className="text-sm text-blue-900 leading-relaxed whitespace-pre-wrap">
          {insight}
        </div>
      </div>
    </div>
  )
}
