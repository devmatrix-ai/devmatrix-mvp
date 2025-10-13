import { useEffect, useState, useCallback } from 'react'
import { wsService } from '../services/websocket'

export function useWebSocket(url?: string) {
  const [isConnected, setIsConnected] = useState(false)

  useEffect(() => {
    wsService.connect(url)

    const cleanup1 = wsService.on('connected', () => setIsConnected(true))
    const cleanup2 = wsService.on('disconnected', () => setIsConnected(false))

    setIsConnected(wsService.isConnected())

    return () => {
      cleanup1()
      cleanup2()
    }
  }, [url])

  const send = useCallback((event: string, data?: any) => {
    wsService.send(event, data)
  }, [])

  const on = useCallback((event: string, callback: Function) => {
    return wsService.on(event, callback)
  }, [])

  return { isConnected, send, on }
}
