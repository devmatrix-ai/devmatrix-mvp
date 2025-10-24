import { describe, it, expect } from 'vitest'
import { cn } from './utils'

describe('cn utility', () => {
  it('merges multiple class strings', () => {
    expect(cn('text-white', 'bg-purple-600')).toBe('text-white bg-purple-600')
  })

  it('handles conditional classes', () => {
    expect(cn('base', true && 'active', false && 'inactive')).toBe('base active')
  })

  it('handles arrays and objects', () => {
    expect(cn(['text-lg', 'font-bold'], { 'text-white': true, 'text-gray': false }))
      .toBe('text-lg font-bold text-white')
  })

  it('handles undefined and null gracefully', () => {
    expect(cn('base', undefined, null, 'end')).toBe('base end')
  })
})
