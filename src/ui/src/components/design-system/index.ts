/**
 * Design System - Glassmorphism Components
 *
 * A comprehensive, tree-shakeable component library featuring glassmorphism-styled UI primitives
 * for consistent, modern interfaces. Built with React 18+, TypeScript, and Tailwind CSS.
 *
 * ## Features
 * - 🎨 Consistent glassmorphism aesthetic with dark theme
 * - 🔷 8 production-ready components (cards, buttons, inputs, headers)
 * - 📦 Fully tree-shakeable - import only what you need
 * - 🎯 TypeScript-first with complete type safety
 * - ♿ Accessible by default (ARIA, semantic HTML, keyboard navigation)
 * - 🎨 Customizable via className prop with intelligent merging
 * - 🚀 Zero runtime overhead - pure Tailwind CSS styling
 *
 * ## Quick Start
 *
 * @example
 * ```tsx
 * import { GlassCard, GlassButton, StatusBadge, PageHeader } from '@/components/design-system'
 *
 * function MyPage() {
 *   return (
 *     <>
 *       <PageHeader
 *         emoji="🎯"
 *         title="Dashboard"
 *         subtitle="Monitor your system metrics"
 *       />
 *
 *       <GlassCard hover>
 *         <h2 className="text-xl font-bold text-white mb-4">System Status</h2>
 *         <StatusBadge status="success">Online</StatusBadge>
 *         <GlassButton variant="primary" size="md" className="mt-4">
 *           View Details
 *         </GlassButton>
 *       </GlassCard>
 *     </>
 *   )
 * }
 * ```
 *
 * ## Component Categories
 *
 * ### Core Components
 * - **GlassCard**: Container with backdrop blur and gradient borders
 * - **GlassButton**: Interactive button with 3 variants (primary/secondary/ghost)
 * - **StatusBadge**: Color-coded status indicators (5 states)
 *
 * ### Input Components
 * - **GlassInput**: Text input with optional icon support
 * - **SearchBar**: Pre-configured search input with integrated icon
 * - **FilterButton**: Toggle button with active/inactive states
 *
 * ### Header Components
 * - **PageHeader**: Standardized page header with emoji + title + subtitle
 * - **SectionHeader**: Consistent section titles
 *
 * ## Utility Functions
 * - **cn()**: Optimized className merging utility (wraps clsx)
 *
 * ## Customization
 *
 * All components accept a `className` prop for Tailwind utility extension:
 *
 * @example
 * ```tsx
 * // Add custom spacing and width
 * <GlassCard className="max-w-md mx-auto mt-8">
 *   <GlassButton className="w-full">Full Width Button</GlassButton>
 * </GlassCard>
 * ```
 *
 * ## Tree-Shaking
 *
 * Import only what you need - unused components are automatically excluded from your bundle:
 *
 * @example
 * ```tsx
 * // Only GlassCard is bundled
 * import { GlassCard } from '@/components/design-system'
 *
 * // Multiple selective imports - only these 3 components bundled
 * import { GlassButton, SearchBar, PageHeader } from '@/components/design-system'
 * ```
 *
 * ## TypeScript Support
 *
 * Full TypeScript support with exported interfaces for all components:
 *
 * @example
 * ```tsx
 * import { GlassButtonProps, StatusBadgeStatus } from '@/components/design-system'
 *
 * const buttonProps: GlassButtonProps = {
 *   variant: 'primary',
 *   size: 'md',
 *   onClick: () => console.log('clicked')
 * }
 *
 * const status: StatusBadgeStatus = 'success'
 * ```
 *
 * @packageDocumentation
 */

// ============================================================================
// Core Components
// ============================================================================

/**
 * GlassCard - Reusable card container with backdrop blur and gradient borders
 *
 * @example
 * ```tsx
 * <GlassCard hover>
 *   <h3>Card Title</h3>
 *   <p>Card content</p>
 * </GlassCard>
 * ```
 */
export { GlassCard, type GlassCardProps } from './GlassCard'

/**
 * GlassButton - Interactive button with purple accent glow and three variants
 *
 * @example
 * ```tsx
 * <GlassButton variant="primary" size="md" onClick={handleClick}>
 *   Submit
 * </GlassButton>
 * ```
 */
export { GlassButton, type GlassButtonProps, type GlassButtonVariant, type GlassButtonSize } from './GlassButton'

/**
 * StatusBadge - Color-coded status indicators with glassmorphism background
 *
 * @example
 * ```tsx
 * <StatusBadge status="success">Active</StatusBadge>
 * <StatusBadge status="error">Failed</StatusBadge>
 * ```
 */
export { StatusBadge, type StatusBadgeProps, type StatusBadgeStatus } from './StatusBadge'

// ============================================================================
// Input Components
// ============================================================================

/**
 * GlassInput - Text input with glassmorphism styling and optional icon support
 *
 * @example
 * ```tsx
 * <GlassInput
 *   value={value}
 *   onChange={(e) => setValue(e.target.value)}
 *   placeholder="Enter text..."
 *   icon={<FiSearch />}
 * />
 * ```
 */
export { GlassInput, type GlassInputProps } from './GlassInput'

/**
 * SearchBar - Integrated search input with icon and glassmorphism styling
 *
 * @example
 * ```tsx
 * <SearchBar
 *   value={search}
 *   onChange={(e) => setSearch(e.target.value)}
 *   placeholder="Search masterplans..."
 * />
 * ```
 */
export { SearchBar, type SearchBarProps } from './SearchBar'

/**
 * FilterButton - Toggle button for filtering with active/inactive states
 *
 * @example
 * ```tsx
 * <FilterButton
 *   active={filter === 'active'}
 *   onClick={() => setFilter('active')}
 * >
 *   Active Items
 * </FilterButton>
 * ```
 */
export { FilterButton, type FilterButtonProps } from './FilterButton'

// ============================================================================
// Header Components
// ============================================================================

/**
 * PageHeader - Standardized page header with emoji + title + optional subtitle
 *
 * @example
 * ```tsx
 * <PageHeader
 *   emoji="🎯"
 *   title="Mission Control"
 *   subtitle="Manage all your development masterplans"
 * />
 * ```
 */
export { PageHeader, type PageHeaderProps } from './PageHeader'

/**
 * SectionHeader - Consistent section titles across pages
 *
 * @example
 * ```tsx
 * <SectionHeader>Recent Activity</SectionHeader>
 * ```
 */
export { SectionHeader, type SectionHeaderProps } from './SectionHeader'

// ============================================================================
// Utilities
// ============================================================================

/**
 * cn() - Utility function for merging Tailwind CSS classes
 *
 * Optimized className merging using clsx for conditional classes, arrays, and objects.
 * Use this when building custom components or extending design system components.
 *
 * @example
 * ```tsx
 * import { cn } from '@/components/design-system'
 *
 * // Basic usage
 * cn('text-white', 'bg-purple-600')
 * // => "text-white bg-purple-600"
 *
 * // With conditionals
 * cn('base-class', isActive && 'active-class')
 * // => "base-class active-class" (when isActive is true)
 *
 * // In custom components
 * function MyComponent({ className }) {
 *   return <div className={cn('base-styles', className)} />
 * }
 * ```
 */
export { cn } from './utils'
