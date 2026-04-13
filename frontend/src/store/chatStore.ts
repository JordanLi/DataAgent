import { create } from 'zustand'
import { Message, Conversation, DataSource } from '@/lib/types'

interface ChatState {
  currentConversationId: number | null;
  messages: Message[];
  datasources: DataSource[];
  selectedDatasourceId: number | null;
  isStreaming: boolean;
  
  // Actions
  setDatasources: (sources: DataSource[]) => void;
  setSelectedDatasourceId: (id: number | null) => void;
  setCurrentConversationId: (id: number | null) => void;
  setMessages: (messages: Message[]) => void;
  addMessage: (message: Message) => void;
  updateMessage: (id: string, partialMsg: Partial<Message>) => void;
  setIsStreaming: (isStreaming: boolean) => void;
  clearMessages: () => void;
}

export const useChatStore = create<ChatState>((set) => ({
  currentConversationId: null,
  messages: [],
  datasources: [],
  selectedDatasourceId: null,
  isStreaming: false,

  setDatasources: (datasources) => set({ datasources }),
  setSelectedDatasourceId: (selectedDatasourceId) => set({ selectedDatasourceId }),
  setCurrentConversationId: (currentConversationId) => set({ currentConversationId }),
  setMessages: (messages) => set({ messages }),
  addMessage: (message) => set((state) => ({ messages: [...state.messages, message] })),
  updateMessage: (id, partialMsg) => set((state) => ({
    messages: state.messages.map((m) => m.id === id ? { ...m, ...partialMsg } : m)
  })),
  setIsStreaming: (isStreaming) => set({ isStreaming }),
  clearMessages: () => set({ messages: [], currentConversationId: null }),
}))
