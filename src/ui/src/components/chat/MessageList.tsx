import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeHighlight from 'rehype-highlight'
import { ChatMessage } from '../../hooks/useChat'
import { FiUser, FiCpu, FiInfo } from 'react-icons/fi'
import { format } from 'date-fns'

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
    ? 'bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800'
    : 'bg-gray-100 dark:bg-gray-800'

  const timestamp = format(new Date(message.timestamp), 'HH:mm')

  return (
    <div className={`flex items-start space-x-3 ${isUser ? 'flex-row-reverse space-x-reverse' : ''}`}>
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
              >
                {message.content}
              </ReactMarkdown>
            </div>
          )}
        </div>
        <p className={`text-xs text-gray-500 dark:text-gray-400 mt-1 ${isUser ? 'text-right' : ''}`}>
          {timestamp}
        </p>
      </div>
    </div>
  )
}
