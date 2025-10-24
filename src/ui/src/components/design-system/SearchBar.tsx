import React from 'react'
import { FiSearch } from 'react-icons/fi'
import { GlassInput } from './GlassInput'

/**
 * Props for the SearchBar component
 */
export interface SearchBarProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'onChange'> {
  /** Search value */
  value: string
  /** Change handler */
  onChange: (e: React.ChangeEvent<HTMLInputElement>) => void
  /** Placeholder text */
  placeholder?: string
  /** Additional CSS classes */
  className?: string
}

/**
 * SearchBar - Pre-configured search input with integrated icon
 *
 * A specialized GlassInput component with a built-in search icon.
 * Uses the same glassmorphism styling as GlassInput.
 *
 * @example
 * ```tsx
 * import { SearchBar } from '@/components/design-system'
 *
 * function MyComponent() {
 *   const [search, setSearch] = React.useState('')
 *
 *   return (
 *     <SearchBar
 *       value={search}
 *       onChange={(e) => setSearch(e.target.value)}
 *       placeholder="Search masterplans..."
 *     />
 *   )
 * }
 * ```
 */
export const SearchBar: React.FC<SearchBarProps> = ({
  value,
  onChange,
  placeholder = 'Search...',
  className = '',
  ...props
}) => {
  return (
    <GlassInput
      type="text"
      value={value}
      onChange={onChange as (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => void}
      placeholder={placeholder}
      icon={<FiSearch className="w-5 h-5" />}
      className={className}
      {...props}
    />
  )
}
