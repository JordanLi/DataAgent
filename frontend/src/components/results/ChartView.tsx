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
    // Only render for valid ECharts types
    const validChartTypes = ['line', 'bar', 'pie', 'scatter']
    if (!rows.length || !validChartTypes.includes(chart_type) || !columns.length) return null

    // Simple heuristic: assume first string column is X axis (dimension), others are Y axis (metrics)
    const xAxisCol = columns.find(c => {
      const val = rows[0]?.[c]
      return typeof val === 'string' && isNaN(Number(val))
    }) || columns[0]
    
    // Y axes are columns that can be parsed as numbers (excluding the chosen X axis)
    const yAxisCols = columns.filter(c => {
      if (c === xAxisCol) return false
      // Exclude typical ID columns from being plotted as metrics in Y axis
      if (c.toLowerCase() === 'id' || c.toLowerCase().endsWith('_id')) return false
      
      const val = rows[0]?.[c]
      // A valid number check:
      if (val === null || val === undefined) return false
      if (typeof val === 'number') return true
      return !isNaN(Number(val))
    })
    
    if (yAxisCols.length === 0) return null

    const series = yAxisCols.map(col => ({
      name: col,
      type: chart_type,
      data: rows.map(r => Number(r[col]) || 0)
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
            data: rows.map(r => ({ name: String(r[xAxisCol]), value: Number(r[yAxisCols[0]]) || 0 })),
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
      grid: { containLabel: true, left: '5%', right: '5%', bottom: '5%', top: '15%' },
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
