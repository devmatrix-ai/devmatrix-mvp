import { create } from 'zustand'

interface ChatState {
  conversationId: string | null
  workspaceId: string | null
  isOpen: boolean
  setConversationId: (id: string | null) => void
  setWorkspaceId: (id: string | null) => void
  toggleChat: () => void
  openChat: () => void
  closeChat: () => void
}

export const useChatStore = create<ChatState>((set) => ({
  conversationId: null,
  workspaceId: null,
  isOpen: true,

  setConversationId: (id) => set({ conversationId: id }),
  setWorkspaceId: (id) => set({ workspaceId: id }),
  toggleChat: () => set((state) => ({ isOpen: !state.isOpen })),
  openChat: () => set({ isOpen: true }),
  closeChat: () => set({ isOpen: false }),
}))
