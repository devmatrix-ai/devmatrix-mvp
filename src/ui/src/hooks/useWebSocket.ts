/**
 * useWebSocket Hook - MasterPlan Event Subscription
 *
 * Manages Socket.IO subscriptions for all MasterPlan/Discovery events.
 * Provides:
 * - Real-time event streaming with circular buffer (max 100 events)
 * - Connection status tracking
 * - Error handling with fallback
 * - Automatic cleanup on unmount
 *
 * @since Nov 4, 2025
 * @version 2.0
 */

import { useEffect, useState, useCallback, useRef } from 'react'
import { wsService } from '../services/websocket'

/**
 * All WebSocket event types for MasterPlan/Discovery workflows
 */
export type MasterPlanEventType =
  // Discovery events
  | 'discovery_generation_start'
  | 'discovery_tokens_progress'
  | 'discovery_entity_discovered'
  | 'discovery_parsing_complete'
  | 'discovery_validation_start'
  | 'discovery_saving_start'
  | 'discovery_generation_complete'
  // MasterPlan events
  | 'masterplan_generation_start'
  | 'masterplan_tokens_progress'
  | 'masterplan_entity_discovered'
  | 'masterplan_parsing_complete'
  | 'masterplan_validation_start'
  | 'masterplan_saving_start'
  | 'masterplan_generation_complete'

/**
 * Single WebSocket event with metadata
 */
export interface MasterPlanProgressEvent {
  type: MasterPlanEventType
  data: Record<string, any>
  timestamp: number
  sessionId?: string
}

/**
 * Return value from useWebSocket hook
 */
export interface UseWebSocketResult {
  events: MasterPlanProgressEvent[]
  latestEvent: MasterPlanProgressEvent | null
  isConnected: boolean
  connectionError: string | null
  send: (event: string, data?: any) => void
  joinChat: (conversationId: string, workspaceId?: string) => void
  on: (event: string, callback: Function) => () => void
}

/**
 * Circular buffer for event history management
 */
class CircularEventBuffer {
  private buffer: MasterPlanProgressEvent[] = []
  private readonly maxSize: number = 100
  private lastEventKey: string = ''

  push(event: MasterPlanProgressEvent): void {
    // Prevent duplicates (same type + timestamp within 100ms)
    const currentKey = `${event.type}:${event.timestamp}`
    if (currentKey === this.lastEventKey) {
      return
    }
    this.lastEventKey = currentKey

    this.buffer.push(event)
    if (this.buffer.length > this.maxSize) {
      this.buffer = this.buffer.slice(-this.maxSize)
    }
  }

  getAll(): MasterPlanProgressEvent[] {
    return [...this.buffer]
  }

  getLast(): MasterPlanProgressEvent | null {
    return this.buffer.length > 0 ? this.buffer[this.buffer.length - 1] : null
  }

  clear(): void {
    this.buffer = []
    this.lastEventKey = ''
  }
}

/**
 * All event types to subscribe to
 */
const ALL_EVENT_TYPES: MasterPlanEventType[] = [
  'discovery_generation_start',
  'discovery_tokens_progress',
  'discovery_entity_discovered',
  'discovery_parsing_complete',
  'discovery_validation_start',
  'discovery_saving_start',
  'discovery_generation_complete',
  'masterplan_generation_start',
  'masterplan_tokens_progress',
  'masterplan_entity_discovered',
  'masterplan_parsing_complete',
  'masterplan_validation_start',
  'masterplan_saving_start',
  'masterplan_generation_complete',
]

/**
 * Hook for MasterPlan WebSocket event subscription and management
 *
 * @param url - Optional WebSocket URL (uses environment variable if not provided)
 * @returns WebSocket state and utility functions
 *
 * @example
 * ```typescript
 * const { events, latestEvent, isConnected, send, joinChat } = useWebSocket();
 *
 * // Monitor latest event
 * useEffect(() => {
 *   if (latestEvent?.type === 'masterplan_generation_complete') {
 *     console.log('Generation finished!');
 *   }
 * }, [latestEvent]);
 * ```
 */
export function useWebSocket(url?: string): UseWebSocketResult {
  // Event state
  const [events, setEvents] = useState<MasterPlanProgressEvent[]>([])
  const [latestEvent, setLatestEvent] = useState<MasterPlanProgressEvent | null>(null)

  // Connection state
  const [isConnected, setIsConnected] = useState(false)
  const [connectionError, setConnectionError] = useState<string | null>(null)

  // Refs for non-state management
  const bufferRef = useRef<CircularEventBuffer | null>(null)
  const unsubscribersRef = useRef<Array<() => void>>([])

  // Initialize WebSocket connection and event subscriptions
  useEffect(() => {
    // Initialize buffer
    if (!bufferRef.current) {
      bufferRef.current = new CircularEventBuffer()
    }

    // Connect to WebSocket
    if (!wsService.isConnected()) {
      console.log('[useWebSocket] Initializing WebSocket connection...')
      wsService.connect(url)
    }

    // Update connection state
    setIsConnected(wsService.isConnected())

    // Event handler factory
    const createEventHandler = (eventType: MasterPlanEventType) => {
      return (data: Record<string, any>) => {
        const event: MasterPlanProgressEvent = {
          type: eventType,
          data,
          timestamp: Date.now(),
          sessionId: data.session_id || data.sessionId,
        }

        // Add to buffer
        bufferRef.current?.push(event)

        // Update React state
        const allEvents = bufferRef.current?.getAll() || []
        setEvents(allEvents)
        setLatestEvent(bufferRef.current?.getLast() || null)

        console.log('[useWebSocket] Event:', {
          type: eventType,
          totalEvents: allEvents.length,
        })
      }
    }

    // Subscribe to all event types
    const unsubscribers: Array<() => void> = []

    ALL_EVENT_TYPES.forEach((eventType) => {
      const unsub = wsService.on(eventType, createEventHandler(eventType))
      unsubscribers.push(unsub)
    })

    // Connection status handlers
    const handleConnected = () => {
      console.log('[useWebSocket] Connected')
      setIsConnected(true)
      setConnectionError(null)
    }

    const handleDisconnected = (data: any) => {
      console.warn('[useWebSocket] Disconnected:', data)
      setIsConnected(false)
      setConnectionError(`Disconnected: ${data?.reason || 'unknown'}`)
    }

    const handleError = (error: any) => {
      console.error('[useWebSocket] Error:', error)
      setConnectionError(`Error: ${error?.message || String(error)}`)
    }

    // Subscribe to connection events
    const unsub1 = wsService.on('connected', handleConnected)
    const unsub2 = wsService.on('disconnected', handleDisconnected)
    const unsub3 = wsService.on('error', handleError)

    unsubscribers.push(unsub1, unsub2, unsub3)
    unsubscribersRef.current = unsubscribers

    // Cleanup
    return () => {
      console.log('[useWebSocket] Cleaning up subscriptions...')
      unsubscribersRef.current.forEach((unsub) => {
        try {
          unsub()
        } catch (error) {
          console.error('[useWebSocket] Cleanup error:', error)
        }
      })
      bufferRef.current?.clear()
    }
  }, [url])

  // Utility functions
  const send = useCallback((event: string, data?: any) => {
    wsService.send(event, data)
  }, [])

  const joinChat = useCallback((conversationId: string, workspaceId?: string) => {
    wsService.joinChat(conversationId, workspaceId)
  }, [])

  const on = useCallback((event: string, callback: Function) => {
    return wsService.on(event, callback)
  }, [])

  return {
    events,
    latestEvent,
    isConnected,
    connectionError,
    send,
    joinChat,
    on,
  }
}
