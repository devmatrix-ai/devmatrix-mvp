import { io, Socket } from 'socket.io-client'

// Global socket instance that survives HMR
declare global {
  interface Window {
    __DEVMATRIX_SOCKET__?: Socket
  }
}

export class WebSocketService {
  private socket: Socket | null = null
  private listeners: Map<string, Set<Function>> = new Map()
  private currentRoom: string | null = null  // Track current chat room for auto-rejoin

  connect(url?: string): void {
    // Check for existing global socket instance (survives HMR)
    if (window.__DEVMATRIX_SOCKET__) {
      console.log('🌐 [WebSocketService] Found global socket, reusing it', {
        connected: window.__DEVMATRIX_SOCKET__.connected,
        id: window.__DEVMATRIX_SOCKET__.id
      })
      this.socket = window.__DEVMATRIX_SOCKET__

      // Re-register event handlers for this instance after HMR
      this.registerEventHandlers()

      return
    }

    // Prevent creating multiple socket instances
    if (this.socket) {
      console.log('⏭️  [WebSocketService] Socket already exists, reusing it', {
        connected: this.socket.connected,
        id: this.socket.id
      })

      // If disconnected, try to reconnect
      if (this.socket.disconnected) {
        console.log('🔄 [WebSocketService] Socket disconnected, reconnecting...')
        this.socket.connect()
      }
      return
    }

    // Use environment variable or default to backend URL
    const socketUrl = url || import.meta.env.VITE_WS_URL || 'http://localhost:8000'
    console.log('🔌 [WebSocketService] Creating NEW socket, connecting to:', socketUrl)

    this.socket = io(socketUrl, {
      path: '/socket.io',
      transports: ['websocket', 'polling'],
      // Reconnection settings - exponential backoff
      reconnection: true,
      reconnectionDelay: 1000,  // Start with 1s delay
      reconnectionDelayMax: 10000,  // Max 10s delay between attempts
      reconnectionAttempts: Infinity,  // Keep trying forever
      // Timeout settings - match backend configuration
      timeout: 30000,  // Connection timeout: 30s
      // Note: pingTimeout and pingInterval are handled server-side
      // Performance settings
      upgrade: true,  // Allow transport upgrades
      rememberUpgrade: true,  // Remember successful upgrade
    })

    // Store in global to survive HMR
    window.__DEVMATRIX_SOCKET__ = this.socket

    this.registerEventHandlers()

    console.log('🎯 [WebSocketService] Initial socket state:', {
      connected: this.socket.connected,
      id: this.socket.id,
      disconnected: this.socket.disconnected
    })

    // Forward all events to listeners
    this.socket.onAny((event, ...args) => {
      console.log('📨 [WebSocketService] Received Socket.IO event:', {
        event,
        argsCount: args.length,
        firstArg: args[0]
      })
      this.emit(event, ...args)
    })
  }

  private registerEventHandlers(): void {
    if (!this.socket) return

    console.log('📝 [WebSocketService] Registering event handlers...')

    // Remove old listeners to prevent duplicates
    this.socket.off('connect')
    this.socket.off('disconnect')
    this.socket.off('connect_error')
    this.socket.off('reconnect_attempt')
    this.socket.off('reconnect')
    this.socket.off('error')

    this.socket.on('connect', () => {
      console.log('✅ [WebSocketService] CONNECT event fired - SID:', this.socket?.id)
      console.log('🔍 [WebSocketService] Socket state after connect:', {
        connected: this.socket?.connected,
        id: this.socket?.id,
        disconnected: this.socket?.disconnected
      })
      this.emit('connected', { sid: this.socket?.id })
    })

    this.socket.on('disconnect', (reason) => {
      console.warn('⚠️ [WebSocketService] DISCONNECT event - Reason:', reason)
      this.emit('disconnected', { reason })
    })

    this.socket.on('connect_error', (error) => {
      console.error('❌ [WebSocketService] CONNECT_ERROR event:', error.message, error)
    })

    this.socket.on('reconnect_attempt', (attemptNumber) => {
      console.log(`🔄 [WebSocketService] RECONNECT_ATTEMPT event (attempt ${attemptNumber})`)
    })

    this.socket.on('reconnect', (attemptNumber) => {
      console.log(`✅ [WebSocketService] RECONNECT event after ${attemptNumber} attempts`)

      // Auto-rejoin the last room if we were in one
      if (this.currentRoom && this.socket) {
        console.log(`🔄 Auto-rejoining room: ${this.currentRoom}`)
        const token = localStorage.getItem('access_token')
        this.socket.emit('join_chat', { conversation_id: this.currentRoom, token })
      }

      this.emit('connected', { sid: this.socket?.id, reconnected: true })
    })

    this.socket.on('error', (error) => {
      console.error('❌ [WebSocketService] ERROR event:', error)
      this.emit('error', error)
    })
  }

  disconnect(): void {
    if (this.socket) {
      this.socket.disconnect()
      this.socket = null
    }
  }

  emit(event: string, data?: any): void {
    const eventListeners = this.listeners.get(event)
    if (eventListeners) {
      eventListeners.forEach(callback => callback(data))
    }
  }

  send(event: string, data?: any): void {
    if (!this.socket) {
      console.warn('WebSocket not initialized, cannot send:', event)
      return
    }

    // If socket exists but not yet connected, wait a bit and retry
    if (!this.socket.connected) {
      console.log('WebSocket connecting, waiting...')
      setTimeout(() => this.send(event, data), 100)
      return
    }

    // Track current room for auto-rejoin after reconnection
    if (event === 'join_chat' && data?.conversation_id) {
      this.currentRoom = data.conversation_id
      console.log(`📍 Tracking current room: ${this.currentRoom}`)
    }

    this.socket.emit(event, data)
  }

  /**
   * Join a chat room and track it for auto-rejoin after reconnection
   * Sends JWT token from localStorage for authentication
   */
  joinChat(conversationId: string, workspaceId?: string): void {
    this.currentRoom = conversationId
    const token = localStorage.getItem('access_token')
    if (!token) {
      console.warn('⚠️ [WebSocketService] No JWT token found in localStorage, cannot join chat')
      return
    }
    this.send('join_chat', {
      conversation_id: conversationId,
      workspace_id: workspaceId,
      token
    })
  }

  /**
   * Leave the current chat room
   */
  leaveChat(): void {
    if (this.currentRoom) {
      this.send('leave_chat', { conversation_id: this.currentRoom })
      this.currentRoom = null
    }
  }

  on(event: string, callback: Function): () => void {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, new Set())
    }
    this.listeners.get(event)!.add(callback)

    // Return cleanup function
    return () => {
      this.listeners.get(event)?.delete(callback)
    }
  }

  off(event: string, callback?: Function): void {
    if (callback) {
      this.listeners.get(event)?.delete(callback)
    } else {
      this.listeners.delete(event)
    }
  }

  isConnected(): boolean {
    const connected = this.socket?.connected ?? false
    // Verbose logging to debug connection state
    if (!connected && this.socket) {
      console.log('🔍 [WebSocketService] isConnected check:', {
        hasSocket: !!this.socket,
        connected: this.socket.connected,
        id: this.socket.id,
        disconnected: this.socket.disconnected
      })
    }
    return connected
  }
}

// Singleton instance
export const wsService = new WebSocketService()
