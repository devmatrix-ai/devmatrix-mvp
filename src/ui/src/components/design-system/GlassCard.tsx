import React from 'react'
import { cn } from './utils'

/**
 * Props for the GlassCard component
 */
export interface GlassCardProps {
  /** Content to render inside the card */
  children: React.ReactNode
  /** Additional CSS classes to apply */
  className?: string
  /** Enable hover shadow effect */
  hover?: boolean
}

/**
 * GlassCard - A glassmorphism-styled card container with backdrop blur and gradient borders
 *
 * @example
 * ```tsx
 * <GlassCard hover>
 *   <h2>Card Title</h2>
 *   <p>Card content goes here</p>
 * </GlassCard>
 * ```
 *
 * @example
 * ```tsx
 * <GlassCard className="max-w-md">
 *   <p>Custom width card</p>
 * </GlassCard>
 * ```
 */
export const GlassCard: React.FC<GlassCardProps> = ({
  children,
  className,
  hover = false
}) => {
  return (
    <div
      className={cn(
        'backdrop-blur-lg bg-gradient-to-r from-purple-900/20 to-blue-900/20',
        'border border-white/10 rounded-2xl p-6',
        hover && 'hover:shadow-xl transition-all',
        className
      )}
    >
      {children}
    </div>
  )
}
