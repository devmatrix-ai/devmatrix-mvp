import React from 'react'

interface EntityCounterProps {
  icon: string
  label: string
  count: number
  total: number
  complete: boolean
}

export const EntityCounter: React.FC<EntityCounterProps> = ({
  icon,
  label,
  count,
  total,
  complete
}) => {
  const percentage = total > 0 ? (count / total) * 100 : 0

  return (
    <div
      className={`
        p-3 rounded-lg transition-all duration-500 ease-out transform
        ${complete
          ? 'bg-gradient-to-br from-green-100 to-green-50 dark:from-green-900/40 dark:to-green-900/20 border-2 border-green-400 dark:border-green-600 scale-105'
          : 'bg-white dark:bg-gray-800 border-2 border-purple-200 dark:border-purple-700'
        }
      `}
    >
      {/* Icon with pulse animation when active */}
      <div className={`text-3xl mb-2 ${!complete && count > 0 ? 'animate-pulse' : ''}`}>
        {icon}
      </div>

      {/* Counter */}
      <div
        className={`
          text-xl font-bold transition-colors duration-300
          ${complete
            ? 'text-green-700 dark:text-green-300'
            : 'text-purple-700 dark:text-purple-300'
          }
        `}
      >
        {count} / {total}
      </div>

      {/* Label */}
      <div className="text-xs text-gray-600 dark:text-gray-400 mt-1">
        {label}
      </div>

      {/* Mini progress bar */}
      <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-1.5 mt-2 overflow-hidden">
        <div
          className={`
            h-full rounded-full transition-all duration-500 ease-out
            ${complete
              ? 'bg-gradient-to-r from-green-500 to-green-600'
              : 'bg-gradient-to-r from-purple-500 to-blue-600'
            }
          `}
          style={{ width: `${Math.min(percentage, 100)}%` }}
        />
      </div>
    </div>
  )
}
