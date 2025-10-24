import React from 'react'
import { cn } from './utils'

/**
 * Props for the FilterButton component
 */
export interface FilterButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  /** Button content */
  children: React.ReactNode
  /** Whether the filter is active */
  active: boolean
  /** Click handler */
  onClick: () => void
  /** Additional CSS classes */
  className?: string
}

/**
 * FilterButton - Toggle button for filtering with active/inactive states
 *
 * A button component designed for filter controls with distinct active and inactive states.
 * Active state shows purple background with glow, inactive state shows subtle glass effect.
 *
 * @example
 * ```tsx
 * import { FilterButton } from '@/components/design-system'
 *
 * function MyFilters() {
 *   const [selectedStatus, setSelectedStatus] = React.useState('all')
 *
 *   return (
 *     <div className="flex gap-2">
 *       {['all', 'active', 'completed'].map((status) => (
 *         <FilterButton
 *           key={status}
 *           active={selectedStatus === status}
 *           onClick={() => setSelectedStatus(status)}
 *         >
 *           {status}
 *         </FilterButton>
 *       ))}
 *     </div>
 *   )
 * }
 * ```
 */
export const FilterButton: React.FC<FilterButtonProps> = ({
  children,
  active,
  onClick,
  className,
  ...props
}) => {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        'px-4 py-2 rounded-lg font-medium text-sm transition-all',
        active
          ? 'bg-purple-600 text-white shadow-lg shadow-purple-500/50'
          : 'bg-white/10 text-gray-300 hover:bg-white/20',
        className
      )}
      {...props}
    >
      {children}
    </button>
  )
}
