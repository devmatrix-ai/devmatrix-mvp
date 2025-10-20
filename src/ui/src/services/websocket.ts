import { io, Socket } from 'socket.io-client'

export class WebSocketService {
  private socket: Socket | null = null
  private listeners: Map<string, Set<Function>> = new Map()

  connect(url?: string): void {
    if (this.socket?.connected) {
      return
    }

    // Use relative URL for Socket.IO to work with Vite proxy
    const socketUrl = url || window.location.origin

    this.socket = io(socketUrl, {
      path: '/socket.io',
      transports: ['websocket', 'polling'],
      reconnection: true,
      reconnectionDelay: 1000,
      reconnectionDelayMax: 5000,
      reconnectionAttempts: 5,
    })

    this.socket.on('connect', () => {
      console.log('WebSocket connected')
      this.emit('connected', { sid: this.socket?.id })
    })

    this.socket.on('disconnect', () => {
      console.log('WebSocket disconnected')
      this.emit('disconnected', {})
    })

    this.socket.on('error', (error) => {
      console.error('WebSocket error:', error)
      this.emit('error', error)
    })

    // Forward all events to listeners
    this.socket.onAny((event, ...args) => {
      this.emit(event, ...args)
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

    this.socket.emit(event, data)
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
    return this.socket?.connected ?? false
  }
}

// Singleton instance
export const wsService = new WebSocketService()
