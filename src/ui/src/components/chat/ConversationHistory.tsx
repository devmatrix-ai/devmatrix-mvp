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
}

export function ConversationHistory({
  currentConversationId,
  onSelectConversation,
  onNewConversation,
}: ConversationHistoryProps) {
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isOpen, setIsOpen] = useState(false)

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
      {/* Toggle button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="fixed left-4 top-4 z-50 bg-gray-800 hover:bg-gray-700 text-white p-2 rounded-lg shadow-lg transition-colors"
        title="Historial de conversaciones"
      >
        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
        </svg>
      </button>

      {/* Sidebar */}
      <div
        className={`fixed left-0 top-0 h-full w-80 bg-gray-900 text-white shadow-2xl z-40 transform transition-transform duration-300 ease-in-out ${
          isOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <div className="flex flex-col h-full">
          {/* Header */}
          <div className="p-4 border-b border-gray-700">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-lg font-semibold">Conversaciones</h2>
              <button
                onClick={() => setIsOpen(false)}
                className="text-gray-400 hover:text-white transition-colors"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <button
              onClick={() => {
                onNewConversation()
                setIsOpen(false)
              }}
              className="w-full bg-blue-600 hover:bg-blue-700 text-white py-2 px-4 rounded-lg transition-colors flex items-center justify-center gap-2"
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
              <div className="p-4 text-center text-gray-400">
                Cargando...
              </div>
            )}

            {error && (
              <div className="p-4 text-center text-red-400">
                {error}
                <button
                  onClick={loadConversations}
                  className="block mx-auto mt-2 text-blue-400 hover:text-blue-300"
                >
                  Reintentar
                </button>
              </div>
            )}

            {!loading && !error && conversations.length === 0 && (
              <div className="p-4 text-center text-gray-400">
                No hay conversaciones guardadas
              </div>
            )}

            {!loading && !error && conversations.map((conv) => (
              <div
                key={conv.id}
                onClick={() => {
                  onSelectConversation(conv.id)
                  setIsOpen(false)
                }}
                className={`p-4 border-b border-gray-800 cursor-pointer hover:bg-gray-800 transition-colors ${
                  conv.id === currentConversationId ? 'bg-gray-800 border-l-4 border-blue-500' : ''
                }`}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-xs text-gray-400">
                        {formatDate(conv.updated_at)}
                      </span>
                      <span className="text-xs text-gray-500">
                        {conv.message_count} {conv.message_count === 1 ? 'mensaje' : 'mensajes'}
                      </span>
                    </div>

                    {conv.last_message_preview && (
                      <p className="text-sm text-gray-300 truncate">
                        {conv.last_message_preview}
                      </p>
                    )}
                  </div>

                  <button
                    onClick={(e) => handleDelete(conv.id, e)}
                    className="flex-shrink-0 text-gray-500 hover:text-red-400 transition-colors p-1"
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
          className="fixed inset-0 bg-black bg-opacity-50 z-30"
          onClick={() => setIsOpen(false)}
        />
      )}
    </>
  )
}
