import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { SectionHeader } from './SectionHeader'

describe('SectionHeader', () => {
  it('renders children correctly', () => {
    render(<SectionHeader>Section Title</SectionHeader>)
    expect(screen.getByText('Section Title')).toBeInTheDocument()
  })

  it('applies base styling classes', () => {
    const { container } = render(<SectionHeader>Test</SectionHeader>)
    const header = container.firstChild as HTMLElement

    expect(header.className).toContain('text-2xl')
    expect(header.className).toContain('font-bold')
    expect(header.className).toContain('text-white')
  })

  it('merges custom className correctly', () => {
    const { container } = render(
      <SectionHeader className="custom-margin mb-8">Test</SectionHeader>
    )
    const header = container.firstChild as HTMLElement

    expect(header.className).toContain('custom-margin')
    expect(header.className).toContain('mb-8')
    expect(header.className).toContain('text-2xl')
  })
})
