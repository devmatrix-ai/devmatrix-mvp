import React from 'react'
import { cn } from './utils'

/**
 * Props for the PageHeader component
 */
export interface PageHeaderProps {
  /** Emoji icon */
  emoji: string
  /** Page title */
  title: string
  /** Optional subtitle */
  subtitle?: string
  /** Additional CSS classes */
  className?: string
}

/**
 * PageHeader - Standardized page header with emoji + title + subtitle
 *
 * A consistent page header layout with large emoji icon, bold title, and optional subtitle.
 * Matches the pattern used in MasterplansPage.
 *
 * @example
 * ```tsx
 * import { PageHeader } from '@/components/design-system'
 *
 * function MyPage() {
 *   return (
 *     <div>
 *       <PageHeader
 *         emoji="🎯"
 *         title="Mission Control"
 *         subtitle="Manage and monitor all your development masterplans"
 *       />
 *     </div>
 *   )
 * }
 * ```
 */
export const PageHeader: React.FC<PageHeaderProps> = ({
  emoji,
  title,
  subtitle,
  className,
}) => {
  return (
    <div className={cn(className)}>
      <div className="flex items-center gap-3 mb-4">
        <div className="text-5xl">{emoji}</div>
        <h1 className="text-4xl font-bold text-white">{title}</h1>
      </div>
      {subtitle && (
        <p className="text-gray-400 text-lg mt-2">{subtitle}</p>
      )}
    </div>
  )
}
