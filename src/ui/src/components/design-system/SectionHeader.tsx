import React from 'react'
import { cn } from './utils'

/**
 * Props for the SectionHeader component
 */
export interface SectionHeaderProps {
  /** Header text */
  children: React.ReactNode
  /** Additional CSS classes */
  className?: string
}

/**
 * SectionHeader - Consistent section title component
 *
 * A simple wrapper component for section headers with standardized styling.
 * Provides consistent typography across all pages.
 *
 * @example
 * ```tsx
 * import { SectionHeader } from '@/components/design-system'
 *
 * function MyComponent() {
 *   return (
 *     <div>
 *       <SectionHeader>Recent Activity</SectionHeader>
 *     </div>
 *   )
 * }
 * ```
 */
export const SectionHeader: React.FC<SectionHeaderProps> = ({
  children,
  className,
}) => {
  return (
    <h2 className={cn('text-2xl font-bold text-white', className)}>
      {children}
    </h2>
  )
}
