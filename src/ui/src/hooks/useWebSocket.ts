import { useEffect, useState, useCallback } from 'react'
import { wsService } from '../services/websocket'

export function useWebSocket(url?: string) {
  const [isConnected, setIsConnected] = useState(false)

  useEffect(() => {
    wsService.connect(url)

    // Set initial state
    setIsConnected(wsService.isConnected())

    // Listen for connection events
    const cleanup1 = wsService.on('connected', () => {
      console.log('🟢 [useWebSocket] Connected event received')
      setIsConnected(true)
    })
    const cleanup2 = wsService.on('disconnected', () => {
      console.log('🔴 [useWebSocket] Disconnected event received')
      setIsConnected(false)
    })

    // Poll connection status every second to handle HMR and missed events
    // This ensures UI stays in sync with actual WebSocket state
    const interval = setInterval(() => {
      const actualStatus = wsService.isConnected()
      setIsConnected(prev => {
        if (prev !== actualStatus) {
          console.log(`🔄 [useWebSocket] Connection status changed: ${prev} -> ${actualStatus}`)
        }
        return actualStatus
      })
    }, 1000)

    return () => {
      cleanup1()
      cleanup2()
      clearInterval(interval)
    }
  }, [url])

  const send = useCallback((event: string, data?: any) => {
    wsService.send(event, data)
  }, [])

  const joinChat = useCallback((conversationId: string, workspaceId?: string) => {
    wsService.joinChat(conversationId, workspaceId)
  }, [])

  const on = useCallback((event: string, callback: Function) => {
    return wsService.on(event, callback)
  }, [])

  return { isConnected, send, joinChat, on }
}
