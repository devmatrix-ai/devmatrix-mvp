import { useRef, useEffect } from 'react'
import { useChat } from '../../hooks/useChat'
import { useKeyboardShortcuts } from '../../hooks/useKeyboardShortcuts'
import { MessageList } from './MessageList'
import { ChatInput } from './ChatInput'
import { ProgressIndicator } from './ProgressIndicator'
import { MasterPlanProgressIndicator } from './MasterPlanProgressIndicator'
import { ConversationHistory } from './ConversationHistory'
import { FiMessageSquare, FiX, FiMinus, FiPlusCircle, FiDownload } from 'react-icons/fi'

interface ChatWindowProps {
  workspaceId?: string
  onClose?: () => void
  isMinimized?: boolean
  onToggleMinimize?: () => void
}

export function ChatWindow({
  workspaceId,
  onClose,
  isMinimized,
  onToggleMinimize,
}: ChatWindowProps) {
  const {
    conversationId,
    messages,
    isLoading,
    isConnected,
    progress,
    masterPlanProgress,
    sendMessage,
    clearMessages,
    switchConversation,
  } = useChat({ workspaceId })

  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<{ focus: () => void }>(null)

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Focus input when loading completes
  useEffect(() => {
    if (!isLoading && isConnected) {
      inputRef.current?.focus()
    }
  }, [isLoading, isConnected])

  const handleSendMessage = (content: string) => {
    sendMessage(content)
  }

  const handleNewProject = () => {
    if (confirm('¿Empezar un nuevo proyecto? Esto borrará el historial del chat actual.')) {
      // Clear current conversation and start fresh
      switchConversation(null)
    }
  }

  const handleSelectConversation = (convId: string) => {
    if (convId === conversationId) {
      return // Already on this conversation
    }

    // Switch to selected conversation
    switchConversation(convId)
  }

  const handleExportChat = () => {
    if (messages.length === 0) {
      alert('No hay mensajes para exportar')
      return
    }

    // Create markdown export
    const markdown = messages
      .map((msg) => {
        const role = msg.role === 'user' ? '**Usuario**' : msg.role === 'system' ? '**Sistema**' : '**Asistente**'
        const timestamp = new Date(msg.timestamp).toLocaleString()
        return `### ${role} - ${timestamp}\n\n${msg.content}\n\n---\n`
      })
      .join('\n')

    const header = `# DevMatrix Chat Export\n\nConversation ID: ${conversationId}\nWorkspace: ${workspaceId || 'default'}\nExported: ${new Date().toLocaleString()}\n\n---\n\n`

    const fullContent = header + markdown

    // Create download
    const blob = new Blob([fullContent], { type: 'text/markdown' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `devmatrix-chat-${conversationId}-${Date.now()}.md`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  // Keyboard shortcuts
  useKeyboardShortcuts([
    {
      key: 'k',
      ctrlKey: true,
      handler: () => inputRef.current?.focus(),
      description: 'Focus input'
    },
    {
      key: 'l',
      ctrlKey: true,
      handler: () => {
        if (confirm('¿Borrar todos los mensajes?')) {
          clearMessages()
        }
      },
      description: 'Clear messages'
    },
    {
      key: 'n',
      ctrlKey: true,
      handler: handleNewProject,
      description: 'New project'
    }
  ])

  return (
    <>
      {/* Conversation History Sidebar */}
      <ConversationHistory
        currentConversationId={conversationId}
        onSelectConversation={handleSelectConversation}
        onNewConversation={handleNewProject}
      />

      <div className="flex flex-col h-full bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg shadow-xl">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-gray-700 bg-gradient-to-r from-primary-600 to-primary-700">
        <div className="flex items-center space-x-2">
          <FiMessageSquare className="text-white" size={20} />
          <div>
            <h3 className="text-white font-semibold">DevMatrix Chat</h3>
            <p className="text-xs text-primary-100">
              {isConnected ? (
                <span className="flex items-center">
                  <span className="w-2 h-2 bg-green-400 rounded-full mr-1.5 animate-pulse" />
                  Connected
                </span>
              ) : (
                <span className="flex items-center">
                  <span className="w-2 h-2 bg-red-400 rounded-full mr-1.5" />
                  Disconnected
                </span>
              )}
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-2">
          <button
            onClick={handleExportChat}
            className="text-white hover:bg-primary-800 px-2 py-1.5 rounded transition-colors flex items-center space-x-1.5 text-sm"
            aria-label="Export Chat"
            title="Exportar Chat"
            disabled={messages.length === 0}
          >
            <FiDownload size={16} />
            <span className="hidden sm:inline">Exportar</span>
          </button>
          <button
            onClick={handleNewProject}
            className="text-white hover:bg-primary-800 px-2 py-1.5 rounded transition-colors flex items-center space-x-1.5 text-sm"
            aria-label="New Project"
            title="Nuevo Proyecto"
          >
            <FiPlusCircle size={16} />
            <span className="hidden sm:inline">Nuevo</span>
          </button>
          {onToggleMinimize && (
            <button
              onClick={onToggleMinimize}
              className="text-white hover:bg-primary-800 p-1.5 rounded transition-colors"
              aria-label={isMinimized ? 'Maximize' : 'Minimize'}
            >
              <FiMinus size={18} />
            </button>
          )}
          {onClose && (
            <button
              onClick={onClose}
              className="text-white hover:bg-primary-800 p-1.5 rounded transition-colors"
              aria-label="Close"
            >
              <FiX size={18} />
            </button>
          )}
        </div>
      </div>

      {!isMinimized && (
        <>
          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {messages.length === 0 && (
              <div className="flex flex-col items-center justify-center h-full text-center text-gray-500 dark:text-gray-400">
                <FiMessageSquare size={48} className="mb-4 opacity-50" />
                <p className="text-lg font-medium">Start a conversation</p>
                <p className="text-sm mt-2">
                  Ask me to create workflows, analyze code, or help with development tasks.
                </p>
                <div className="mt-4 text-xs space-y-1">
                  <p className="font-mono text-primary-600 dark:text-primary-400">
                    Try: /masterplan Create a Task Management API
                  </p>
                  <p className="font-mono text-primary-600 dark:text-primary-400">
                    Or: /orchestrate for full workflow execution
                  </p>
                  <p className="font-mono text-primary-600 dark:text-primary-400">
                    Or: /help for all commands
                  </p>
                </div>
              </div>
            )}

            <MessageList messages={messages} isLoading={isLoading} />

            {/* MasterPlan Progress Indicator - Show during MasterPlan generation */}
            {(() => {
              console.log('🎨 [ChatWindow] Checking masterPlanProgress:', {
                isTruthy: !!masterPlanProgress,
                value: masterPlanProgress
              })

              if (!masterPlanProgress) {
                console.log('⏸️ [ChatWindow] masterPlanProgress is falsy, not rendering indicator')
                return null
              }

              console.log('✅ [ChatWindow] Rendering MasterPlanProgressIndicator with:', masterPlanProgress)
              return (
                <div className="mt-4">
                  <MasterPlanProgressIndicator
                    event={masterPlanProgress}
                    onComplete={() => {
                      // Progress will be cleared automatically by the hook after 3s
                    }}
                  />
                </div>
              )
            })()}

            {/* Progress Indicator - Show when loading or progress events */}
            {(isLoading || progress) && (
              <div className="mt-4">
                {progress ? (
                  <ProgressIndicator progress={progress} />
                ) : (
                  <div className="flex items-center gap-3 px-4 py-3 bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
                    <div className="flex space-x-1">
                      <div className="w-2 h-2 bg-blue-600 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                      <div className="w-2 h-2 bg-blue-600 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                      <div className="w-2 h-2 bg-blue-600 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                    </div>
                    <span className="text-sm font-medium text-blue-700 dark:text-blue-300">
                      Procesando tu mensaje...
                    </span>
                  </div>
                )}
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Input */}
          <div className="border-t border-gray-200 dark:border-gray-700 p-4">
            <ChatInput
              ref={inputRef}
              onSend={handleSendMessage}
              disabled={!isConnected || isLoading}
              placeholder={
                isConnected
                  ? 'Type a message or /help for commands...'
                  : 'Connecting...'
              }
            />
          </div>
        </>
      )}

      {/* Conversation ID (debug) */}
      {conversationId && import.meta.env.DEV && (
        <div className="px-4 py-2 text-xs text-gray-500 border-t border-gray-200 dark:border-gray-700">
          Conversation: {conversationId}
        </div>
      )}
    </div>
    </>
  )
}
