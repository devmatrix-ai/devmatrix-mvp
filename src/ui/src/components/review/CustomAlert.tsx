import React from 'react'
import { GlassCard } from '../design-system/GlassCard'
import { cn } from '../design-system/utils'
import { FiCheckCircle, FiAlertCircle, FiAlertTriangle, FiInfo, FiX } from 'react-icons/fi'

/**
 * Props for the CustomAlert component
 */
export interface CustomAlertProps {
  /** Alert severity level */
  severity: 'success' | 'error' | 'warning' | 'info'
  /** Alert message content */
  message: string | React.ReactNode
  /** Optional close handler */
  onClose?: () => void
}

/**
 * CustomAlert - Glassmorphism-styled alert component with colored border
 *
 * Displays alerts with severity-based colors, icons, and optional close button.
 *
 * @example
 * ```tsx
 * <CustomAlert severity="success" message="Operation completed!" />
 * <CustomAlert
 *   severity="error"
 *   message="Something went wrong"
 *   onClose={() => console.log('closed')}
 * />
 * ```
 */
export const CustomAlert: React.FC<CustomAlertProps> = ({ severity, message, onClose }) => {
  const getIcon = () => {
    switch (severity) {
      case 'success':
        return <FiCheckCircle className="text-emerald-400" size={20} />
      case 'error':
        return <FiAlertCircle className="text-red-400" size={20} />
      case 'warning':
        return <FiAlertTriangle className="text-amber-400" size={20} />
      case 'info':
        return <FiInfo className="text-blue-400" size={20} />
    }
  }

  return (
    <GlassCard
      className={cn(
        'border-l-4 p-4',
        severity === 'success' && 'border-emerald-500 bg-emerald-500/10',
        severity === 'error' && 'border-red-500 bg-red-500/10',
        severity === 'warning' && 'border-amber-500 bg-amber-500/10',
        severity === 'info' && 'border-blue-500 bg-blue-500/10'
      )}
    >
      <div className="flex items-start gap-3">
        {getIcon()}
        <div className="flex-1 text-sm text-white">{message}</div>
        {onClose && (
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white transition-colors"
            aria-label="Close alert"
          >
            <FiX size={16} />
          </button>
        )}
      </div>
    </GlassCard>
  )
}
