"use client"

import React, { useMemo } from 'react'
import ReactECharts from 'echarts-for-react'
import { QueryResult } from '@/lib/types'

interface ChartViewProps {
  result: QueryResult
}

export function ChartView({ result }: ChartViewProps) {
  const { columns, rows, chart_type } = result

  const option = useMemo(() => {
    if (!rows.length || chart_type === 'none' || !columns.length) return null

    // Simple heuristic: assume first column is X axis (dimension), others are Y axis (metrics)
    // In a real implementation, this would be more robust or provided directly by the backend.
    const xAxisCol = columns[0]
    const yAxisCols = columns.slice(1).filter(c => typeof rows[0]?.[c] === 'number')
    
    if (yAxisCols.length === 0) return null

    const series = yAxisCols.map(col => ({
      name: col,
      type: chart_type,
      data: rows.map(r => r[col])
    }))

    if (chart_type === 'pie') {
      return {
        tooltip: { trigger: 'item' },
        legend: { top: 'bottom' },
        series: [
          {
            name: yAxisCols[0],
            type: 'pie',
            radius: '50%',
            data: rows.map(r => ({ name: String(r[xAxisCol]), value: r[yAxisCols[0]] })),
            emphasis: {
              itemStyle: {
                shadowBlur: 10,
                shadowOffsetX: 0,
                shadowColor: 'rgba(0, 0, 0, 0.5)'
              }
            }
          }
        ]
      }
    }

    return {
      tooltip: { trigger: 'axis' },
      legend: { data: yAxisCols },
      xAxis: {
        type: 'category',
        data: rows.map(r => String(r[xAxisCol])),
        axisLabel: { rotate: 30 }
      },
      yAxis: { type: 'value' },
      series
    }
  }, [columns, rows, chart_type])

  if (!option) return null

  return (
    <div className="w-full h-80 bg-white border border-gray-200 rounded-md p-4">
      <ReactECharts option={option} style={{ height: '100%', width: '100%' }} />
    </div>
  )
}
