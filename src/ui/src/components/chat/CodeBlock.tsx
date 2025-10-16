import { useState } from 'react'
import { FiCopy, FiCheck } from 'react-icons/fi'

interface CodeBlockProps {
  children: React.ReactNode
  className?: string
  inline?: boolean
}

export function CodeBlock({ children, className, inline }: CodeBlockProps) {
  const [copied, setCopied] = useState(false)

  // Extract language from className (format: language-xxx)
  const language = className?.replace(/language-/, '') || 'text'

  const handleCopy = async () => {
    const code = typeof children === 'string' ? children : String(children)
    await navigator.clipboard.writeText(code)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  // Inline code (backticks)
  if (inline) {
    return (
      <code className="px-1.5 py-0.5 bg-gray-200 dark:bg-gray-700 rounded text-sm font-mono">
        {children}
      </code>
    )
  }

  // Code block (triple backticks)
  return (
    <div className="relative group">
      <div className="flex items-center justify-between bg-gray-800 text-gray-300 px-4 py-2 rounded-t-lg text-sm">
        <span className="font-mono">{language}</span>
        <button
          onClick={handleCopy}
          className="flex items-center gap-1 px-2 py-1 rounded hover:bg-gray-700 transition-colors"
          title="Copy code"
        >
          {copied ? (
            <>
              <FiCheck size={14} />
              <span className="text-xs">Copied!</span>
            </>
          ) : (
            <>
              <FiCopy size={14} />
              <span className="text-xs">Copy</span>
            </>
          )}
        </button>
      </div>
      <pre className="bg-gray-900 text-gray-100 p-4 rounded-b-lg overflow-x-auto">
        <code className={className}>{children}</code>
      </pre>
    </div>
  )
}
