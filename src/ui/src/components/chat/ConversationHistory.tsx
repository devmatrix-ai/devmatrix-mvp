import { useState, useEffect } from 'react'
import { formatDistanceToNow } from 'date-fns'
import { es } from 'date-fns/locale'

interface Conversation {
  id: string
  created_at: string
  updated_at: string
  message_count: number
  last_message_preview: string | null
  workspace_id: string | null
}

interface ConversationHistoryProps {
  currentConversationId: string | null
  onSelectConversation: (conversationId: string) => void
  onNewConversation: () => void
  isOpen: boolean
  onClose: () => void
}

export function ConversationHistory({
  currentConversationId,
  onSelectConversation,
  onNewConversation,
  isOpen,
  onClose,
}: ConversationHistoryProps) {
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadConversations()
  }, [])

  const loadConversations = async () => {
    try {
      setLoading(true)
      setError(null)

      const response = await fetch('http://localhost:8000/api/v1/conversations?limit=50')
      if (!response.ok) {
        throw new Error(`Error ${response.status}: ${response.statusText}`)
      }

      const data = await response.json()
      setConversations(data)
    } catch (err: any) {
      console.error('Error loading conversations:', err)
      setError(err.message || 'Error al cargar conversaciones')
    } finally {
      setLoading(false)
    }
  }

  const formatDate = (dateStr: string) => {
    try {
      const date = new Date(dateStr)
      return formatDistanceToNow(date, { addSuffix: true, locale: es })
    } catch {
      return dateStr
    }
  }

  const handleDelete = async (conversationId: string, e: React.MouseEvent) => {
    e.stopPropagation() // Prevent selecting the conversation

    if (!confirm('¿Eliminar esta conversación?')) {
      return
    }

    try {
      const response = await fetch(`http://localhost:8000/api/v1/conversations/${conversationId}`, {
        method: 'DELETE'
      })

      if (!response.ok) {
        throw new Error('Error al eliminar conversación')
      }

      // Reload conversations
      await loadConversations()

      // If deleted current conversation, create new one
      if (conversationId === currentConversationId) {
        onNewConversation()
      }
    } catch (err: any) {
      console.error('Error deleting conversation:', err)
      alert(err.message || 'Error al eliminar conversación')
    }
  }

  return (
    <>
      {/* Sidebar */}
      <div
        className={`fixed left-0 top-0 h-full w-80 bg-gradient-to-b from-gray-900/40 via-purple-900/30 to-gray-900/40 backdrop-blur-xl text-white shadow-2xl shadow-purple-500/10 z-40 transform transition-transform duration-300 ease-in-out border-r border-purple-500/20 ${
          isOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <div className="flex flex-col h-full">
          {/* Header */}
          <div className="p-4 border-b border-purple-500/20 bg-gradient-to-r from-purple-500/10 to-blue-500/10 backdrop-blur-sm">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-lg font-semibold text-purple-100">Conversaciones</h2>
              <button
                onClick={onClose}
                className="text-purple-300 hover:text-purple-100 transition-colors hover:bg-purple-500/20 p-1 rounded"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <button
              onClick={() => {
                onNewConversation()
                onClose()
              }}
              className="w-full bg-gradient-to-r from-purple-600/90 to-blue-600/90 backdrop-blur-sm hover:from-purple-700/90 hover:to-blue-700/90 text-white py-2 px-4 rounded-lg transition-colors flex items-center justify-center gap-2 border border-purple-400/30 shadow-lg shadow-purple-500/20"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
              Nueva Conversación
            </button>
          </div>

          {/* Conversations list */}
          <div className="flex-1 overflow-y-auto">
            {loading && (
              <div className="p-4 text-center text-purple-300">
                <div className="flex items-center justify-center space-x-2">
                  <div className="w-2 h-2 bg-purple-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                  <div className="w-2 h-2 bg-purple-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                  <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                </div>
                <p className="mt-2">Cargando...</p>
              </div>
            )}

            {error && (
              <div className="p-4 text-center">
                <p className="text-red-400">{error}</p>
                <button
                  onClick={loadConversations}
                  className="mt-2 px-4 py-2 bg-purple-500/20 hover:bg-purple-500/30 text-purple-300 rounded-lg transition-colors border border-purple-500/30"
                >
                  Reintentar
                </button>
              </div>
            )}

            {!loading && !error && conversations.length === 0 && (
              <div className="p-4 text-center text-purple-300">
                <svg className="w-12 h-12 mx-auto mb-2 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                </svg>
                <p>No hay conversaciones guardadas</p>
              </div>
            )}

            {!loading && !error && conversations.map((conv) => (
              <div
                key={conv.id}
                onClick={() => {
                  onSelectConversation(conv.id)
                  onClose()
                }}
                className={`p-4 border-b border-purple-500/10 cursor-pointer hover:bg-purple-500/10 backdrop-blur-sm transition-all ${
                  conv.id === currentConversationId
                    ? 'bg-gradient-to-r from-purple-500/20 to-blue-500/20 border-l-4 border-purple-400'
                    : ''
                }`}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-xs text-purple-300">
                        {formatDate(conv.updated_at)}
                      </span>
                      <span className="text-xs text-purple-400 bg-purple-500/20 px-2 py-0.5 rounded-full">
                        {conv.message_count} {conv.message_count === 1 ? 'mensaje' : 'mensajes'}
                      </span>
                    </div>

                    {conv.last_message_preview && (
                      <p className="text-sm text-gray-200 truncate">
                        {conv.last_message_preview}
                      </p>
                    )}
                  </div>

                  <button
                    onClick={(e) => handleDelete(conv.id, e)}
                    className="flex-shrink-0 text-purple-400 hover:text-red-400 transition-colors p-1 hover:bg-red-500/20 rounded"
                    title="Eliminar conversación"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Overlay */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/50 backdrop-blur-sm z-30"
          onClick={onClose}
        />
      )}
    </>
  )
}
