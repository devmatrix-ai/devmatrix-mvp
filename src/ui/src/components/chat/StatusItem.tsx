import React from 'react'

interface StatusItemProps {
  icon: string
  text: string
  status: 'pending' | 'in_progress' | 'done'
}

export const StatusItem: React.FC<StatusItemProps> = ({
  icon,
  text,
  status
}) => {
  const getStatusStyles = () => {
    switch (status) {
      case 'pending':
        return {
          text: 'text-gray-400',
          icon: 'opacity-50',
          animation: ''
        }
      case 'in_progress':
        return {
          text: 'text-blue-400 font-medium',
          icon: 'animate-pulse',
          animation: 'scale-105'
        }
      case 'done':
        return {
          text: 'text-green-400 font-medium',
          icon: '',
          animation: 'scale-100'
        }
    }
  }

  const styles = getStatusStyles()

  return (
    <div
      className={`
        flex items-center gap-2 text-sm py-1 px-2 rounded backdrop-blur-sm
        transition-all duration-300 ease-out transform
        ${status === 'in_progress' ? 'bg-blue-500/20 border border-blue-400/30' : ''}
        ${status === 'done' ? 'bg-green-500/20 border border-green-400/30' : ''}
        ${styles.text}
      `}
    >
      {/* Icon */}
      <span
        className={`
          text-base transition-all duration-300
          ${styles.icon}
        `}
      >
        {icon}
      </span>

      {/* Text */}
      <span className="flex-1 transition-all duration-300">
        {text}
      </span>

      {/* Spinner for in_progress */}
      {status === 'in_progress' && (
        <div className="ml-auto">
          <div className="w-3 h-3 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />
        </div>
      )}

      {/* Checkmark for done */}
      {status === 'done' && (
        <div className="ml-auto">
          <div className="w-4 h-4 bg-green-400 rounded-full flex items-center justify-center animate-scale-in">
            <svg className="w-3 h-3 text-gray-900" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
            </svg>
          </div>
        </div>
      )}
    </div>
  )
}
