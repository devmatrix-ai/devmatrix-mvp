import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeHighlight from 'rehype-highlight'
import { ChatMessage } from '../../hooks/useChat'
import { FiUser, FiCpu, FiInfo, FiCopy, FiRefreshCw, FiCheck } from 'react-icons/fi'
import { useState } from 'react'
import { format } from 'date-fns'
import { CodeBlock } from './CodeBlock'

interface MessageListProps {
  messages: ChatMessage[]
  isLoading?: boolean
}

export function MessageList({ messages, isLoading }: MessageListProps) {
  return (
    <>
      {messages.map((message, index) => (
        <Message key={`${message.timestamp}-${index}`} message={message} />
      ))}

      {isLoading && (
        <div className="flex items-start space-x-3">
          <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary-100 dark:bg-primary-900 flex items-center justify-center">
            <FiCpu className="text-primary-600 dark:text-primary-400" size={16} />
          </div>
          <div className="flex-1 bg-gray-100 dark:bg-gray-800 rounded-lg p-3">
            <div className="flex space-x-2">
              <div className="w-2 h-2 bg-primary-600 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
              <div className="w-2 h-2 bg-primary-600 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
              <div className="w-2 h-2 bg-primary-600 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
            </div>
          </div>
        </div>
      )}
    </>
  )
}

interface MessageProps {
  message: ChatMessage
}

function Message({ message }: MessageProps) {
  const [copied, setCopied] = useState(false)
  const isUser = message.role === 'user'
  const isSystem = message.role === 'system'

  const icon = isUser ? (
    <FiUser className="text-gray-600 dark:text-gray-400" size={16} />
  ) : isSystem ? (
    <FiInfo className="text-yellow-600 dark:text-yellow-400" size={16} />
  ) : (
    <FiCpu className="text-primary-600 dark:text-primary-400" size={16} />
  )

  const bgColor = isUser
    ? 'bg-primary-600 text-white'
    : isSystem
    ? 'bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 text-yellow-900 dark:text-yellow-100'
    : 'bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-gray-100'

  const timestamp = format(new Date(message.timestamp), 'HH:mm')

  const handleCopyMessage = async () => {
    await navigator.clipboard.writeText(message.content)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const handleRegenerate = () => {
    // TODO: Implement regenerate functionality
    console.log('Regenerate message:', message)
  }

  return (
    <div className={`group flex items-start space-x-3 ${isUser ? 'flex-row-reverse space-x-reverse' : ''}`}>
      <div className={`flex-shrink-0 w-8 h-8 rounded-full ${isUser ? 'bg-primary-600' : isSystem ? 'bg-yellow-100 dark:bg-yellow-900' : 'bg-primary-100 dark:bg-primary-900'} flex items-center justify-center`}>
        {icon}
      </div>

      <div className={`flex-1 max-w-[80%] ${isUser ? 'items-end' : ''}`}>
        <div className={`rounded-lg p-3 ${bgColor}`}>
          {isUser ? (
            <p className="whitespace-pre-wrap">{message.content}</p>
          ) : (
            <div className="markdown prose-sm max-w-none dark:prose-invert">
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                rehypePlugins={[rehypeHighlight]}
                components={{
                  code(props: any) {
                    const { inline, className, children } = props
                    return (
                      <CodeBlock inline={inline} className={className}>
                        {children}
                      </CodeBlock>
                    )
                  }
                }}
              >
                {message.content}
              </ReactMarkdown>
            </div>
          )}
        </div>
        <div className={`flex items-center gap-2 mt-1 ${isUser ? 'justify-end' : ''}`}>
          <p className="text-xs text-gray-500 dark:text-gray-400">
            {timestamp}
          </p>
          {!isUser && (
            <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
              <button
                onClick={handleCopyMessage}
                className="p-1 rounded hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
                title="Copy message"
              >
                {copied ? (
                  <FiCheck size={12} className="text-green-600" />
                ) : (
                  <FiCopy size={12} className="text-gray-500 dark:text-gray-400" />
                )}
              </button>
              <button
                onClick={handleRegenerate}
                className="p-1 rounded hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
                title="Regenerate response"
              >
                <FiRefreshCw size={12} className="text-gray-500 dark:text-gray-400" />
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
