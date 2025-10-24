import React from 'react'
import { cn } from './utils'

/**
 * Props for the GlassInput component
 */
export interface GlassInputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  /** Input value */
  value?: string
  /** Change handler */
  onChange?: (e: React.ChangeEvent<HTMLInputElement>) => void
  /** Placeholder text */
  placeholder?: string
  /** Input type (text, email, password, etc.) */
  type?: string
  /** Optional icon to display on the left */
  icon?: React.ReactNode
  /** Additional CSS classes */
  className?: string
}

/**
 * GlassInput - Glassmorphism-styled text input component
 *
 * A text input with glassmorphism styling, optional icon support, and purple focus ring.
 * Supports all standard HTML input attributes.
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
 *     </>
 *   )
 * }
 * ```
 */
export const GlassInput = React.forwardRef<HTMLInputElement, GlassInputProps>(
  ({ value, onChange, placeholder, type = 'text', icon, className, ...props }, ref) => {
    const hasIcon = !!icon

    return (
      <div className="relative">
        {icon && (
          <div className="absolute left-4 top-1/2 transform -translate-y-1/2 text-gray-400">
            {icon}
          </div>
        )}
        <input
          ref={ref}
          type={type}
          value={value}
          onChange={onChange}
          placeholder={placeholder}
          className={cn(
            'w-full px-4 py-3 bg-white/5 border border-white/20 rounded-lg',
            'text-white placeholder-gray-400',
            'focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent',
            'transition-all',
            hasIcon && 'pl-12',
            className
          )}
          {...props}
        />
      </div>
    )
  }
)

GlassInput.displayName = 'GlassInput'
