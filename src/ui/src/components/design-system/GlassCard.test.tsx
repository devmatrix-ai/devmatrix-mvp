import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { GlassCard } from './GlassCard'

describe('GlassCard', () => {
  it('renders children correctly', () => {
    render(<GlassCard>Test Content</GlassCard>)
    expect(screen.getByText('Test Content')).toBeInTheDocument()
  })

  it('applies base glassmorphism classes', () => {
    const { container } = render(<GlassCard>Content</GlassCard>)
    const card = container.firstChild as HTMLElement

    expect(card.className).toContain('backdrop-blur-lg')
    expect(card.className).toContain('bg-gradient-to-r')
    expect(card.className).toContain('from-purple-900/20')
    expect(card.className).toContain('to-blue-900/20')
    expect(card.className).toContain('border')
    expect(card.className).toContain('rounded-2xl')
  })

  it('merges custom className prop correctly', () => {
    const { container } = render(
      <GlassCard className="custom-class max-w-md">Content</GlassCard>
    )
    const card = container.firstChild as HTMLElement

    expect(card.className).toContain('custom-class')
    expect(card.className).toContain('max-w-md')
    expect(card.className).toContain('backdrop-blur-lg')
  })

  it('applies hover classes when hover prop is true', () => {
    const { container } = render(<GlassCard hover>Content</GlassCard>)
    const card = container.firstChild as HTMLElement

    expect(card.className).toContain('hover:shadow-xl')
    expect(card.className).toContain('transition-all')
  })

  it('does not apply hover classes when hover prop is false', () => {
    const { container } = render(<GlassCard hover={false}>Content</GlassCard>)
    const card = container.firstChild as HTMLElement

    expect(card.className).not.toContain('hover:shadow-xl')
  })
})
