import React, { useState, useRef, useEffect, forwardRef, useImperativeHandle } from 'react'
import { FiSend } from 'react-icons/fi'

interface ChatInputProps {
  onSend: (message: string) => void
  disabled?: boolean
  placeholder?: string
}

const COMMANDS = [
  '/help',
  '/orchestrate',
  '/analyze',
  '/test',
  '/clear',
  '/workspace',
]

export const ChatInput = forwardRef<{ focus: () => void }, ChatInputProps>(
  ({ onSend, disabled, placeholder }, ref) => {
    const [message, setMessage] = useState('')
    const [showSuggestions, setShowSuggestions] = useState(false)
    const [suggestions, setSuggestions] = useState<string[]>([])
    const [selectedSuggestion, setSelectedSuggestion] = useState(0)
    const textareaRef = useRef<HTMLTextAreaElement>(null)

    // Expose focus method to parent
    useImperativeHandle(ref, () => ({
      focus: () => {
        textareaRef.current?.focus()
      }
    }))

  useEffect(() => {
    // Auto-resize textarea
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`
    }

    // Show command suggestions
    if (message.startsWith('/')) {
      const matchingCommands = COMMANDS.filter(cmd =>
        cmd.startsWith(message.toLowerCase())
      )
      setSuggestions(matchingCommands)
      setShowSuggestions(matchingCommands.length > 0)
      setSelectedSuggestion(0)
    } else {
      setShowSuggestions(false)
    }
  }, [message])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const trimmedMessage = message.trim()

    if (trimmedMessage && !disabled) {
      onSend(trimmedMessage)
      setMessage('')
      setShowSuggestions(false)
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto'
      }
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (showSuggestions) {
      if (e.key === 'ArrowDown') {
        e.preventDefault()
        setSelectedSuggestion(prev =>
          prev < suggestions.length - 1 ? prev + 1 : 0
        )
      } else if (e.key === 'ArrowUp') {
        e.preventDefault()
        setSelectedSuggestion(prev =>
          prev > 0 ? prev - 1 : suggestions.length - 1
        )
      } else if (e.key === 'Tab' || e.key === 'Enter') {
        if (suggestions.length > 0) {
          e.preventDefault()
          setMessage(suggestions[selectedSuggestion] + ' ')
          setShowSuggestions(false)
          textareaRef.current?.focus()
        }
      } else if (e.key === 'Escape') {
        setShowSuggestions(false)
      }
    } else if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e)
    }
  }

  const selectSuggestion = (suggestion: string) => {
    setMessage(suggestion + ' ')
    setShowSuggestions(false)
    textareaRef.current?.focus()
  }

  return (
    <form onSubmit={handleSubmit} className="relative">
      {/* Command Suggestions */}
      {showSuggestions && (
        <div className="absolute bottom-full left-0 right-0 mb-2 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg overflow-hidden">
          {suggestions.map((suggestion, index) => (
            <button
              key={suggestion}
              type="button"
              onClick={() => selectSuggestion(suggestion)}
              className={`w-full text-left px-4 py-2 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors ${
                index === selectedSuggestion
                  ? 'bg-primary-50 dark:bg-primary-900/20 text-primary-700 dark:text-primary-400'
                  : ''
              }`}
            >
              <span className="font-mono text-sm">{suggestion}</span>
            </button>
          ))}
        </div>
      )}

      {/* Input Field */}
      <div className="flex items-end space-x-2">
        <div className="flex-1 relative">
          <textarea
            ref={textareaRef}
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={placeholder || 'Type a message...'}
            disabled={disabled}
            rows={1}
            className="w-full px-4 py-3 pr-12 bg-gray-50 dark:bg-gray-800 text-gray-900 dark:text-gray-100 border border-gray-300 dark:border-gray-600 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent disabled:opacity-50 disabled:cursor-not-allowed placeholder:text-gray-500 dark:placeholder:text-gray-400"
            style={{ maxHeight: '200px' }}
          />
          <div className="absolute bottom-3 right-3 text-xs text-gray-400">
            <kbd className="px-1.5 py-0.5 bg-gray-200 dark:bg-gray-700 rounded">
              Enter
            </kbd>{' '}
            to send
          </div>
        </div>

        <button
          type="submit"
          disabled={disabled || !message.trim()}
          className="flex-shrink-0 p-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          aria-label="Send message"
        >
          <FiSend size={20} />
        </button>
      </div>
    </form>
  )
}
)
