import { useState, useEffect, useCallback } from 'react'
import { useWebSocket } from './useWebSocket'

export interface ChatMessage {
  message_id?: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: string
  metadata?: Record<string, any>
}

export interface UseChatOptions {
  conversationId?: string
  workspaceId?: string
  onMessage?: (message: ChatMessage) => void
  onError?: (error: any) => void
}

export function useChat(options: UseChatOptions = {}) {
  const { isConnected, send, on } = useWebSocket()
  const [conversationId, setConversationId] = useState<string | null>(
    options.conversationId || null
  )
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [isJoined, setIsJoined] = useState(false)

  // Join chat room on mount
  useEffect(() => {
    if (!isConnected || isJoined) return

    send('join_chat', {
      conversation_id: options.conversationId,
      workspace_id: options.workspaceId,
    })

    const cleanup1 = on('chat_joined', (data: any) => {
      setConversationId(data.conversation_id)
      setMessages(data.history || [])
      setIsJoined(true)
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

        if (options.onMessage) {
          options.onMessage(assistantMsg)
        }
      } else if (data.type === 'status') {
        // Optional: handle status updates
        console.log('Status:', data.content)
      } else if (data.type === 'error') {
        setIsLoading(false)
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
      if (conversationId) {
        send('leave_chat', { conversation_id: conversationId })
      }
    }
  }, [isConnected, isJoined, options.conversationId, options.workspaceId])

  const sendMessage = useCallback(
    (content: string, metadata?: Record<string, any>) => {
      if (!conversationId || !isJoined) {
        console.warn('Cannot send message: not joined to chat')
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
  }, [])

  return {
    conversationId,
    messages,
    isLoading,
    isConnected: isConnected && isJoined,
    sendMessage,
    clearMessages,
  }
}
