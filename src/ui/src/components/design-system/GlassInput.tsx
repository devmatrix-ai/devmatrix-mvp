import React from 'react'
import { cn } from './utils'

/**
 * Props for the GlassInput component
 */
export interface GlassInputProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'onChange'> {
  /** Input value */
  value?: string
  /** Change handler */
  onChange?: (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => void
  /** Placeholder text */
  placeholder?: string
  /** Input type (text, email, password, etc.) */
  type?: string
  /** Optional icon to display on the left */
  icon?: React.ReactNode
  /** Additional CSS classes */
  className?: string
  /** Render as textarea instead of input */
  multiline?: boolean
  /** Number of rows for textarea (default: 4) */
  rows?: number
}

/**
 * GlassInput - Glassmorphism-styled text input component
 *
 * A text input or textarea with glassmorphism styling, optional icon support, and purple focus ring.
 * Supports all standard HTML input/textarea attributes.
 *
 * @example
 * ```tsx
 * import { GlassInput } from '@/components/design-system'
 * import { FiSearch } from 'react-icons/fi'
 *
 * function MyForm() {
 *   const [value, setValue] = React.useState('')
 *
 *   return (
 *     <>
 *       <GlassInput
 *         value={value}
 *         onChange={(e) => setValue(e.target.value)}
 *         placeholder="Search..."
 *         icon={<FiSearch />}
 *       />
 *       <GlassInput
 *         type="email"
 *         placeholder="Email address"
 *       />
 *       <GlassInput
 *         multiline
 *         rows={6}
 *         placeholder="Enter your message..."
 *       />
 *     </>
 *   )
 * }
 * ```
 */
export const GlassInput = React.forwardRef<HTMLInputElement | HTMLTextAreaElement, GlassInputProps>(
  ({ value, onChange, placeholder, type = 'text', icon, className, multiline = false, rows = 4, ...props }, ref) => {
    const hasIcon = !!icon

    const sharedClasses = cn(
      'w-full px-4 py-3 bg-white/5 border border-white/20 rounded-lg',
      'text-white placeholder-gray-400',
      'focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent',
      'transition-all',
      hasIcon && 'pl-12',
      className
    )

    return (
      <div className="relative">
        {icon && (
          <div className={cn(
            'absolute left-4 text-gray-400',
            multiline ? 'top-3' : 'top-1/2 transform -translate-y-1/2'
          )}>
            {icon}
          </div>
        )}
        {multiline ? (
          <textarea
            ref={ref as React.Ref<HTMLTextAreaElement>}
            rows={rows}
            value={value}
            onChange={onChange}
            placeholder={placeholder}
            className={cn(sharedClasses, 'resize-none')}
            {...(props as React.TextareaHTMLAttributes<HTMLTextAreaElement>)}
          />
        ) : (
          <input
            ref={ref as React.Ref<HTMLInputElement>}
            type={type}
            value={value}
            onChange={onChange}
            placeholder={placeholder}
            className={sharedClasses}
            {...(props as React.InputHTMLAttributes<HTMLInputElement>)}
          />
        )}
      </div>
    )
  }
)

GlassInput.displayName = 'GlassInput'
