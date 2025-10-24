import React from 'react'
import { cn } from './utils'

/**
 * Status badge types
 */
export type StatusBadgeStatus = 'success' | 'warning' | 'error' | 'info' | 'default'

/**
 * Props for the StatusBadge component
 */
export interface StatusBadgeProps {
  /** Badge content */
  children: React.ReactNode
  /** Status type for color coding */
  status?: StatusBadgeStatus
  /** Additional CSS classes to apply */
  className?: string
}

/**
 * StatusBadge - Color-coded status indicators with glassmorphism background
 *
 * @example
 * ```tsx
 * <StatusBadge status="success">
 *   Completed
 * </StatusBadge>
 * ```
 *
 * @example
 * ```tsx
 * <StatusBadge status="error">
 *   Failed
 * </StatusBadge>
 * ```
 */
export const StatusBadge: React.FC<StatusBadgeProps> = ({
  children,
  status = 'default',
  className
}) => {
  const statusClasses = {
    success: 'bg-green-500/20 text-green-400 border-green-500/50',
    warning: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/50',
    error: 'bg-red-500/20 text-red-400 border-red-500/50',
    info: 'bg-blue-500/20 text-blue-400 border-blue-500/50',
    default: 'bg-gray-500/20 text-gray-400 border-gray-500/50'
  }

  return (
    <span
      className={cn(
        'px-3 py-1 rounded-full text-xs font-medium border',
        statusClasses[status],
        className
      )}
    >
      {children}
    </span>
  )
}
