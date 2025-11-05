/**
 * WebSocketProvider - Singleton WebSocket Context Provider
 *
 * Ensures only one instance of useWebSocket hook exists across the entire app.
 * This prevents multiple independent buffers and subscription managers from interfering.
 *
 * @example
 * ```tsx
 * <WebSocketProvider>
 *   <App />
 * </WebSocketProvider>
 * ```
 */

import React, { createContext, useContext } from 'react'
import { useWebSocket, UseWebSocketResult } from '../hooks/useWebSocket'

// Create the context
const WebSocketContext = createContext<UseWebSocketResult | null>(null)

// Provider component
export function WebSocketProvider({ children }: { children: React.ReactNode }) {
  // Create a single instance of the hook for the entire app
  const wsState = useWebSocket()

  return (
    <WebSocketContext.Provider value={wsState}>
      {children}
    </WebSocketContext.Provider>
  )
}

/**
 * Custom hook to access WebSocket state from context
 * This ensures all components use the same singleton instance
 */
export function useWebSocketContext(): UseWebSocketResult {
  const context = useContext(WebSocketContext)

  if (!context) {
    throw new Error(
      'useWebSocketContext must be used within WebSocketProvider. ' +
      'Make sure your app is wrapped with <WebSocketProvider>.</WebSocketProvider>'
    )
  }

  return context
}
