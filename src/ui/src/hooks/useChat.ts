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
  const [masterPlanProgress, setMasterPlanProgress] = useState<ProgressEvent | null>(null)

  // Register event listeners (only once when connected)
  useEffect(() => {
    if (!isConnected) return

    const cleanup1 = on('chat_joined', (data: any) => {
      console.log('✅ [useChat] chat_joined event received:', data)
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

    // Discovery Progress Events (lines 118-146)
    const cleanup4 = on('discovery_generation_start', (data: any) => {
      console.log('🔍 [WebSocket] discovery_generation_start received:', data)
      console.log('🔍 [WebSocket] Setting masterPlanProgress state...')
      setMasterPlanProgress({ event: 'discovery_generation_start', data })
      console.log('🔍 [WebSocket] masterPlanProgress state set complete')
    })

    const cleanup5 = on('discovery_tokens_progress', (data: any) => {
      console.log('📊 [WebSocket] discovery_tokens_progress received:', data)
      setMasterPlanProgress({ event: 'discovery_tokens_progress', data })
    })

    const cleanup6 = on('discovery_entity_discovered', (data: any) => {
      console.log('🔍 [WebSocket] discovery_entity_discovered received:', data)
      setMasterPlanProgress({ event: 'discovery_entity_discovered', data })
    })

    const cleanup7 = on('discovery_parsing_complete', (data: any) => {
      console.log('✅ [WebSocket] discovery_parsing_complete received:', data)
      setMasterPlanProgress({ event: 'discovery_parsing_complete', data })
    })

    const cleanup8 = on('discovery_saving_start', (data: any) => {
      console.log('💾 [WebSocket] discovery_saving_start received:', data)
      setMasterPlanProgress({ event: 'discovery_saving_start', data })
    })

    const cleanup9 = on('discovery_generation_complete', (data: any) => {
      console.log('🎉 [WebSocket] discovery_generation_complete received:', data)
      setMasterPlanProgress({ event: 'discovery_generation_complete', data })
    })

    // MasterPlan Progress Events
    const cleanup10 = on('masterplan_generation_start', (data: any) => {
      console.log('🚀 [WebSocket] masterplan_generation_start received:', data)
      setMasterPlanProgress({ event: 'masterplan_generation_start', data })
    })

    const cleanup11 = on('masterplan_tokens_progress', (data: any) => {
      console.log('📊 [WebSocket] masterplan_tokens_progress received:', data)
      setMasterPlanProgress({ event: 'masterplan_tokens_progress', data })
    })

    const cleanup12 = on('masterplan_entity_discovered', (data: any) => {
      console.log('🔍 [WebSocket] masterplan_entity_discovered received:', data)
      setMasterPlanProgress({ event: 'masterplan_entity_discovered', data })
    })

    const cleanup13 = on('masterplan_parsing_complete', (data: any) => {
      console.log('✅ [WebSocket] masterplan_parsing_complete received:', data)
      setMasterPlanProgress({ event: 'masterplan_parsing_complete', data })
    })

    const cleanup14 = on('masterplan_validation_start', (data: any) => {
      console.log('🔬 [WebSocket] masterplan_validation_start received:', data)
      setMasterPlanProgress({ event: 'masterplan_validation_start', data })
    })

    const cleanup15 = on('masterplan_saving_start', (data: any) => {
      console.log('💾 [WebSocket] masterplan_saving_start received:', data)
      setMasterPlanProgress({ event: 'masterplan_saving_start', data })
    })

    const cleanup16 = on('masterplan_generation_complete', (data: any) => {
      console.log('🎉 [WebSocket] masterplan_generation_complete received:', data)
      setMasterPlanProgress({ event: 'masterplan_generation_complete', data })
      // Hide progress after 3 seconds
      setTimeout(() => setMasterPlanProgress(null), 3000)
    })

    return () => {
      cleanup1()
      cleanup2()
      cleanup3()
      cleanup4()
      cleanup5()
      cleanup6()
      cleanup7()
      cleanup8()
      cleanup9()
      cleanup10()
      cleanup11()
      cleanup12()
      cleanup13()
      cleanup14()
      cleanup15()
      cleanup16()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isConnected, on])

  // Join chat room when connection is established
  useEffect(() => {
    console.log('📡 [useChat] Join effect triggered:', { isConnected, isJoined, conversationId })

    if (!isConnected) {
      console.log('⏸️  [useChat] Not connected, waiting...')
      return
    }

    if (isJoined) {
      console.log('✅ [useChat] Already joined, skipping')
      return
    }

    console.log('📡 [useChat] Joining chat room...', conversationId || 'new')

    // Use saved conversation_id if available
    send('join_chat', {
      conversation_id: conversationId,
      workspace_id: options.workspaceId,
    })

    // No cleanup needed - server handles disconnections automatically
    // Cleanup would cause issues with React StrictMode in development
  }, [isConnected, isJoined, conversationId, options.workspaceId, send])

  // Reset join status when connection is lost
  useEffect(() => {
    if (!isConnected && isJoined) {
      console.log('⚠️ Connection lost - will rejoin when reconnected')
      setIsJoined(false)
    }
  }, [isConnected, isJoined])

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
    setMasterPlanProgress(null)

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

  const finalIsConnected = isConnected && isJoined

  // Debug log connection state
  useEffect(() => {
    console.log('🔍 [useChat] Connection state:', {
      wsConnected: isConnected,
      chatJoined: isJoined,
      finalIsConnected
    })
  }, [isConnected, isJoined, finalIsConnected])

  // Debug log masterPlanProgress changes
  useEffect(() => {
    if (masterPlanProgress) {
      console.log('📊 [useChat] masterPlanProgress STATE CHANGED:', {
        event: masterPlanProgress.event,
        dataKeys: Object.keys(masterPlanProgress.data || {})
      })
    } else {
      console.log('📊 [useChat] masterPlanProgress CLEARED (null)')
    }
  }, [masterPlanProgress])

  return {
    conversationId,
    messages,
    isLoading,
    isConnected: finalIsConnected,
    progress,
    masterPlanProgress,
    sendMessage,
    clearMessages,
    switchConversation,
  }
}
