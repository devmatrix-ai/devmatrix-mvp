import React, { useState } from 'react'
import { GlassCard } from '../design-system/GlassCard'
import { cn } from '../design-system/utils'
import { FiChevronDown } from 'react-icons/fi'

/**
 * Props for the CustomAccordion component
 */
export interface CustomAccordionProps {
  /** Accordion title */
  title: string
  /** Optional icon to display before title */
  icon?: React.ReactNode
  /** Content to display when expanded */
  children: React.ReactNode
  /** Whether accordion starts expanded */
  defaultExpanded?: boolean
}

/**
 * CustomAccordion - Expandable section with glassmorphism styling
 *
 * A collapsible section component with smooth expand/collapse animation.
 *
 * @example
 * ```tsx
 * import { FiCode } from 'react-icons/fi'
 *
 * <CustomAccordion title="Details" icon={<FiCode />}>
 *   <p>Hidden content here</p>
 * </CustomAccordion>
 *
 * <CustomAccordion title="Options" defaultExpanded>
 *   <div>Options content</div>
 * </CustomAccordion>
 * ```
 */
export const CustomAccordion: React.FC<CustomAccordionProps> = ({
  title,
  icon,
  children,
  defaultExpanded = false
}) => {
  const [expanded, setExpanded] = useState(defaultExpanded)

  return (
    <GlassCard className="overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between p-4 hover:bg-white/5 transition-colors"
        aria-expanded={expanded}
        aria-label={`Toggle ${title}`}
      >
        <div className="flex items-center gap-2">
          {icon}
          <span className="text-sm font-medium text-white">{title}</span>
        </div>
        <FiChevronDown
          className={cn(
            'text-gray-400 transition-transform',
            expanded && 'rotate-180'
          )}
          size={20}
        />
      </button>

      {expanded && (
        <div className="border-t border-white/10">
          {children}
        </div>
      )}
    </GlassCard>
  )
}
