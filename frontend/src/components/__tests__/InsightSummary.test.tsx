import React from 'react'
import { render, screen } from '@testing-library/react'
import { InsightSummary } from '../results/InsightSummary'

describe('InsightSummary', () => {
  it('renders nothing when insight is empty', () => {
    const { container } = render(<InsightSummary insight="" />)
    expect(container).toBeEmptyDOMElement()
  })

  it('renders the insight text correctly', () => {
    const text = 'Here is a sample insight summary.'
    render(<InsightSummary insight={text} />)
    
    expect(screen.getByText(text)).toBeInTheDocument()
  })
})
