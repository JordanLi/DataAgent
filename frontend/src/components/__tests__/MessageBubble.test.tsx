import React from 'react'
import { render, screen } from '@testing-library/react'
import { MessageBubble } from '../chat/MessageBubble'
import { Message } from '@/lib/types'

// Mock child components to isolate testing of MessageBubble logic
jest.mock('../chat/SqlPreview', () => ({
  SqlPreview: ({ sql }: { sql: string }) => <div data-testid="sql-preview">{sql}</div>
}))

jest.mock('../results/DataTable', () => ({
  DataTable: () => <div data-testid="data-table" />
}))

jest.mock('../results/ChartView', () => ({
  ChartView: () => <div data-testid="chart-view" />
}))

jest.mock('../results/InsightSummary', () => ({
  InsightSummary: ({ insight }: { insight: string }) => <div data-testid="insight-summary">{insight}</div>
}))

describe('MessageBubble', () => {
  it('renders user message correctly', () => {
    const userMessage: Message = {
      id: '1',
      role: 'user',
      content: 'Show me total sales',
      created_at: new Date().toISOString()
    }
    
    render(<MessageBubble message={userMessage} />)
    expect(screen.getByText('Show me total sales')).toBeInTheDocument()
  })

  it('renders assistant message with content correctly', () => {
    const botMessage: Message = {
      id: '2',
      role: 'assistant',
      content: 'Here are the sales:',
      created_at: new Date().toISOString()
    }
    
    render(<MessageBubble message={botMessage} />)
    expect(screen.getByText('Here are the sales:')).toBeInTheDocument()
  })

  it('renders assistant message with error', () => {
    const botMessage: Message = {
      id: '3',
      role: 'assistant',
      content: '',
      error: 'Invalid syntax near SELECT',
      created_at: new Date().toISOString()
    }
    
    render(<MessageBubble message={botMessage} />)
    expect(screen.getByText('Invalid syntax near SELECT')).toBeInTheDocument()
  })

  it('renders assistant message with sql preview', () => {
    const botMessage: Message = {
      id: '4',
      role: 'assistant',
      content: '',
      sql: 'SELECT * FROM sales',
      created_at: new Date().toISOString()
    }
    
    render(<MessageBubble message={botMessage} />)
    expect(screen.getByTestId('sql-preview')).toHaveTextContent('SELECT * FROM sales')
  })

  it('renders assistant message with full result (table, chart, insight)', () => {
    const botMessage: Message = {
      id: '5',
      role: 'assistant',
      content: '',
      sql: 'SELECT date, amount FROM sales',
      result: {
        columns: ['date', 'amount'],
        rows: [{ date: '2023-10-01', amount: 100 }],
        row_count: 1,
        execution_time_ms: 10,
        chart_type: 'line',
        insight: 'Sales are steady.'
      },
      created_at: new Date().toISOString()
    }
    
    render(<MessageBubble message={botMessage} />)
    expect(screen.getByTestId('sql-preview')).toBeInTheDocument()
    expect(screen.getByTestId('chart-view')).toBeInTheDocument()
    expect(screen.getByTestId('data-table')).toBeInTheDocument()
    expect(screen.getByTestId('insight-summary')).toHaveTextContent('Sales are steady.')
  })
})
