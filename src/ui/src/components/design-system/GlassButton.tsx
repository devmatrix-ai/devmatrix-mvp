import React from 'react'
import { cn } from './utils'

/**
 * Button variant types
 */
export type GlassButtonVariant = 'primary' | 'secondary' | 'ghost'

/**
 * Button size types
 */
export type GlassButtonSize = 'sm' | 'md' | 'lg'

/**
 * Props for the GlassButton component
 */
export interface GlassButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  /** Button variant style */
  variant?: GlassButtonVariant
  /** Button size */
  size?: GlassButtonSize
  /** Button content */
  children: React.ReactNode
  /** Additional CSS classes to apply */
  className?: string
}

/**
 * GlassButton - Interactive button with glassmorphism styling and purple accent glow
 *
 * @example
 * ```tsx
 * <GlassButton variant="primary" size="md" onClick={handleClick}>
 *   Click Me
 * </GlassButton>
 * ```
 *
 * @example
 * ```tsx
 * <GlassButton variant="ghost" size="sm">
 *   Cancel
 * </GlassButton>
 * ```
 */
export const GlassButton = React.forwardRef<HTMLButtonElement, GlassButtonProps>(
  ({ variant = 'primary', size = 'md', children, className, disabled, ...props }, ref) => {
    const variantClasses = {
      primary: 'bg-purple-600 text-white shadow-lg shadow-purple-500/50 hover:bg-purple-700',
      secondary: 'bg-white/10 text-gray-300 hover:bg-white/20',
      ghost: 'bg-transparent border border-white/20 text-gray-300 hover:bg-white/10'
    }

    const sizeClasses = {
      sm: 'px-3 py-1.5 text-sm',
      md: 'px-4 py-2',
      lg: 'px-6 py-3 text-lg'
    }

    return (
      <button
        ref={ref}
        disabled={disabled}
        className={cn(
          'rounded-lg font-medium transition-all',
          'focus:outline-none focus:ring-2 focus:ring-purple-500 focus:ring-offset-2 focus:ring-offset-gray-900',
          variantClasses[variant],
          sizeClasses[size],
          disabled && 'opacity-50 cursor-not-allowed',
          className
        )}
        {...props}
      >
        {children}
      </button>
    )
  }
)

GlassButton.displayName = 'GlassButton'
