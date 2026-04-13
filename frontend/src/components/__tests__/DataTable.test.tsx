import React from 'react'
import { render, screen } from '@testing-library/react'
import { DataTable } from '../results/DataTable'

describe('DataTable', () => {
  it('renders nothing when columns are empty', () => {
    const { container } = render(<DataTable columns={[]} rows={[]} />)
    expect(container).toBeEmptyDOMElement()
  })

  it('renders table headers and rows correctly', () => {
    const columns = ['id', 'name', 'age']
    const rows = [
      { id: 1, name: 'Alice', age: 25 },
      { id: 2, name: 'Bob', age: 30 }
    ]

    render(<DataTable columns={columns} rows={rows} />)

    // Check headers
    columns.forEach(col => {
      expect(screen.getByText(col)).toBeInTheDocument()
    })

    // Check cells
    expect(screen.getByText('Alice')).toBeInTheDocument()
    expect(screen.getByText('25')).toBeInTheDocument()
    expect(screen.getByText('Bob')).toBeInTheDocument()
    expect(screen.getByText('30')).toBeInTheDocument()
  })

  it('handles missing values gracefully', () => {
    const columns = ['name', 'description']
    const rows = [
      { name: 'Test', description: null },
      { name: 'Test2', description: undefined }
    ]

    render(<DataTable columns={columns} rows={rows} />)
    
    // It should render two empty strings for description. The text content will just be the names.
    expect(screen.getByText('Test')).toBeInTheDocument()
    expect(screen.getByText('Test2')).toBeInTheDocument()
  })
})
