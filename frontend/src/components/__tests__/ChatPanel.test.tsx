import React from 'react'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { ChatPanel } from '../chat/ChatPanel'
import { useChatStore } from '@/store/chatStore'
import * as api from '@/lib/api'

jest.mock('@/store/chatStore')
jest.mock('@/lib/api', () => ({
  chatStream: jest.fn()
}))
import { chatStream } from '@/lib/api'
jest.mock('../chat/MessageBubble', () => ({
  MessageBubble: ({ message }: any) => <div data-testid="message-bubble">{message.content}</div>
}))
jest.mock('../chat/QueryInput', () => ({
  QueryInput: ({ onSend, disabled }: any) => (
    <div data-testid="query-input">
      <button disabled={disabled} onClick={() => onSend('Hello world')}>Send</button>
    </div>
  )
}))

describe('ChatPanel', () => {
  const mockAddMessage = jest.fn()
  const mockUpdateMessage = jest.fn()
  const mockSetIsStreaming = jest.fn()
  
  beforeEach(() => {
    jest.clearAllMocks()
    ;(useChatStore as unknown as jest.Mock).mockReturnValue({
      messages: [],
      addMessage: mockAddMessage,
      updateMessage: mockUpdateMessage,
      selectedDatasourceId: 1,
      currentConversationId: null,
      setCurrentConversationId: jest.fn(),
      setIsStreaming: mockSetIsStreaming,
      isStreaming: false
    })
    
    // Mock scrollIntoView
    window.HTMLElement.prototype.scrollIntoView = jest.fn()
  })

  it('renders welcome screen when no messages', () => {
    render(<ChatPanel />)
    expect(screen.getByText(/我是 DataAgent/)).toBeInTheDocument()
  })

  it('renders messages when available', () => {
    ;(useChatStore as unknown as jest.Mock).mockReturnValue({
      messages: [
        { id: '1', role: 'user', content: 'First message', created_at: '' }
      ],
      addMessage: mockAddMessage,
      updateMessage: mockUpdateMessage,
      selectedDatasourceId: 1,
      currentConversationId: null,
      setCurrentConversationId: jest.fn(),
      setIsStreaming: mockSetIsStreaming,
      isStreaming: false
    })
    
    render(<ChatPanel />)
    expect(screen.queryByText(/我是 DataAgent/)).not.toBeInTheDocument()
    expect(screen.getByTestId('message-bubble')).toHaveTextContent('First message')
  })

  it('shows alert if no datasource is selected', () => {
    ;(useChatStore as unknown as jest.Mock).mockReturnValue({
      messages: [],
      selectedDatasourceId: null,
      addMessage: mockAddMessage,
      updateMessage: mockUpdateMessage,
      setCurrentConversationId: jest.fn(),
      setIsStreaming: mockSetIsStreaming,
      isStreaming: false
    })

    const alertMock = jest.spyOn(window, 'alert').mockImplementation(() => {})
    render(<ChatPanel />)
    
    fireEvent.click(screen.getByText('Send'))
    
    expect(alertMock).toHaveBeenCalledWith('请先选择一个数据源')
    alertMock.mockRestore()
  })

  it('adds messages and starts streaming on send', async () => {
    (chatStream as jest.Mock).mockImplementation(async function* () {
      yield { event: 'done', data: '{}' }
    })
    
    render(<ChatPanel />)
    fireEvent.click(screen.getByText('Send'))
    
    expect(mockAddMessage).toHaveBeenCalledTimes(2) // User message + Empty bot message
    expect(mockSetIsStreaming).toHaveBeenCalledWith(true)
    
    await waitFor(() => {
      expect(mockSetIsStreaming).toHaveBeenLastCalledWith(false)
    })
  })
})
