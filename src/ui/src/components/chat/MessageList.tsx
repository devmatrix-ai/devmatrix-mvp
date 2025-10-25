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
          <div className="flex-shrink-0 w-8 h-8 rounded-full bg-purple-500/20 backdrop-blur-sm flex items-center justify-center border border-purple-400/30">
            <FiCpu className="text-purple-400" size={16} />
          </div>
          <div className="flex-1 bg-white/5 backdrop-blur-sm rounded-lg p-3 border border-white/10">
            <div className="flex space-x-2">
              <div className="w-2 h-2 bg-purple-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
              <div className="w-2 h-2 bg-purple-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
              <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
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
    <FiUser className="text-purple-100" size={16} />
  ) : isSystem ? (
    <FiInfo className="text-yellow-400" size={16} />
  ) : (
    <FiCpu className="text-purple-400" size={16} />
  )

  const bgColor = isUser
    ? 'bg-gradient-to-r from-purple-600/80 to-blue-600/80 backdrop-blur-sm text-white border border-purple-400/30'
    : isSystem
    ? 'bg-yellow-500/20 backdrop-blur-sm border border-yellow-400/30 text-yellow-100'
    : 'bg-white/5 backdrop-blur-sm text-gray-100 border border-white/10'

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
      <div className={`flex-shrink-0 w-8 h-8 rounded-full ${isUser ? 'bg-gradient-to-br from-purple-600 to-blue-600 border border-purple-400/30' : isSystem ? 'bg-yellow-500/20 backdrop-blur-sm border border-yellow-400/30' : 'bg-purple-500/20 backdrop-blur-sm border border-purple-400/30'} flex items-center justify-center`}>
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
          <p className="text-xs text-gray-400">
            {timestamp}
          </p>
          {!isUser && (
            <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
              <button
                onClick={handleCopyMessage}
                className="p-1 rounded hover:bg-white/10 transition-colors backdrop-blur-sm"
                title="Copy message"
              >
                {copied ? (
                  <FiCheck size={12} className="text-green-400" />
                ) : (
                  <FiCopy size={12} className="text-gray-400" />
                )}
              </button>
              <button
                onClick={handleRegenerate}
                className="p-1 rounded hover:bg-white/10 transition-colors backdrop-blur-sm"
                title="Regenerate response"
              >
                <FiRefreshCw size={12} className="text-gray-400" />
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
