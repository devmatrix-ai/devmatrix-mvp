import { useState, useEffect, useCallback } from 'react'
import { useWebSocket } from './useWebSocket'

export interface ChatMessage {
  message_id?: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: string
  metadata?: Record<string, any>
}

export interface ProgressEvent {
  event: string
  data: Record<string, any>
}

export interface UseChatOptions {
  conversationId?: string
  workspaceId?: string
  onMessage?: (message: ChatMessage) => void
  onError?: (error: any) => void
  onProgress?: (event: ProgressEvent) => void
}

// Helper to get localStorage key for conversation
const getConversationKey = (workspaceId?: string) => {
  return `devmatrix_conversation_${workspaceId || 'default'}`
}

export function useChat(options: UseChatOptions = {}) {
  const { isConnected, send, on } = useWebSocket()

  // Try to restore conversation_id from localStorage
  const savedConversationId = options.conversationId ||
    (typeof window !== 'undefined' ? localStorage.getItem(getConversationKey(options.workspaceId)) : null)

  const [conversationId, setConversationId] = useState<string | null>(savedConversationId)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [isJoined, setIsJoined] = useState(false)
  const [progress, setProgress] = useState<ProgressEvent | null>(null)

  // Register event listeners (only once when connected)
  useEffect(() => {
    if (!isConnected) return

    const cleanup1 = on('chat_joined', (data: any) => {
      const convId = data.conversation_id
      setConversationId(convId)
      setMessages(data.history || [])
      setIsJoined(true)

      // Save conversation_id to localStorage for persistence
      if (convId && typeof window !== 'undefined') {
        localStorage.setItem(getConversationKey(options.workspaceId), convId)
      }
    })

    const cleanup2 = on('message', (data: any) => {
      if (data.type === 'user_message') {
        const userMsg: ChatMessage = {
          role: 'user',
          content: data.content,
          timestamp: new Date().toISOString(),
        }
        setMessages(prev => [...prev, userMsg])
      } else if (data.type === 'message') {
        const assistantMsg: ChatMessage = {
          role: data.role || 'assistant',
          content: data.content,
          timestamp: new Date().toISOString(),
          metadata: data.metadata,
        }
        setMessages(prev => [...prev, assistantMsg])
        setIsLoading(false)
        setProgress(null) // Clear progress when message completes

        if (options.onMessage) {
          options.onMessage(assistantMsg)
        }
      } else if (data.type === 'status') {
        // Status messages - could be shown in UI later
      } else if (data.type === 'progress') {
        // Progress events during orchestration
        const progressEvent: ProgressEvent = {
          event: data.event,
          data: data.data
        }
        setProgress(progressEvent)
        if (options.onProgress) {
          options.onProgress(progressEvent)
        }
      } else if (data.type === 'error') {
        console.error('[useChat] Error received from backend:', {
          error: data.error,
          message: data.message,
          details: data.details,
          fullData: data
        })
        setIsLoading(false)
        setProgress(null)
        if (options.onError) {
          options.onError(data)
        }
      }
    })

    const cleanup3 = on('error', (error: any) => {
      setIsLoading(false)
      if (options.onError) {
        options.onError(error)
      }
    })

    return () => {
      cleanup1()
      cleanup2()
      cleanup3()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isConnected, on])

  // Join chat room (separate effect)
  useEffect(() => {
    if (!isConnected || isJoined) return

    // Use saved conversation_id if available
    send('join_chat', {
      conversation_id: conversationId,
      workspace_id: options.workspaceId,
    })

    // No cleanup needed - server handles disconnections automatically
    // Cleanup would cause issues with React StrictMode in development
  }, [isConnected, isJoined, conversationId, options.workspaceId, send])

  const sendMessage = useCallback(
    (content: string, metadata?: Record<string, any>) => {
      if (!conversationId || !isJoined) {
        console.warn('[useChat] Cannot send message: not joined to chat')
        return
      }

      setIsLoading(true)
      send('send_message', {
        conversation_id: conversationId,
        content,
        metadata,
      })
    },
    [conversationId, isJoined, send]
  )

  const clearMessages = useCallback(() => {
    setMessages([])
    // Clear conversation from localStorage to start fresh
    if (typeof window !== 'undefined') {
      localStorage.removeItem(getConversationKey(options.workspaceId))
    }
    setConversationId(null)
    setIsJoined(false)
  }, [options.workspaceId])

  const switchConversation = useCallback((newConversationId: string | null) => {
    // Clear current conversation
    setMessages([])
    setIsJoined(false)
    setIsLoading(false)
    setProgress(null)

    // Update conversation ID
    setConversationId(newConversationId)

    // Update localStorage
    if (typeof window !== 'undefined') {
      if (newConversationId) {
        localStorage.setItem(getConversationKey(options.workspaceId), newConversationId)
      } else {
        localStorage.removeItem(getConversationKey(options.workspaceId))
      }
    }
  }, [options.workspaceId])

  return {
    conversationId,
    messages,
    isLoading,
    isConnected: isConnected && isJoined,
    progress,
    sendMessage,
    clearMessages,
    switchConversation,
  }
}
