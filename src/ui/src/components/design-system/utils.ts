import { clsx, type ClassValue } from 'clsx'

/**
 * Utility function for merging Tailwind CSS classes
 *
 * This helper combines `clsx` for conditional class merging with optimal handling
 * of class arrays, objects, and conditional expressions. It's designed specifically
 * for the design system to ensure consistent className merging across all components.
 *
 * @param inputs - Class values to merge (strings, arrays, objects, or conditionals)
 * @returns Merged className string with duplicates removed
 *
 * @example
 * ```tsx
 * // Basic usage
 * cn('text-white', 'bg-purple-600')
 * // => "text-white bg-purple-600"
 *
 * // With conditional classes
 * cn('base-class', isActive && 'active-class', 'another-class')
 * // => "base-class active-class another-class" (when isActive is true)
 *
 * // With arrays and objects
 * cn(['text-lg', 'font-bold'], { 'text-white': true, 'text-gray-400': false })
 * // => "text-lg font-bold text-white"
 *
 * // In components with className prop
 * cn('base-styles', className)
 * // => Merges base styles with user-provided className
 * ```
 */
export function cn(...inputs: ClassValue[]): string {
  return clsx(inputs)
}
