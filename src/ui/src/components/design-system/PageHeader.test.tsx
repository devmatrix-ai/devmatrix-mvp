import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { PageHeader } from './PageHeader'

describe('PageHeader', () => {
  it('renders emoji and title', () => {
    render(<PageHeader emoji="🎯" title="Test Title" />)

    expect(screen.getByText('🎯')).toBeInTheDocument()
    expect(screen.getByText('Test Title')).toBeInTheDocument()
  })

  it('renders optional subtitle', () => {
    render(<PageHeader emoji="📋" title="Title" subtitle="Subtitle text" />)

    expect(screen.getByText('Subtitle text')).toBeInTheDocument()
  })

  it('applies flex layout with gap-3', () => {
    const { container } = render(<PageHeader emoji="🚀" title="Test" />)
    const headerContainer = container.firstChild as HTMLElement
    const flexDiv = headerContainer.firstChild as HTMLElement

    expect(flexDiv.className).toContain('flex')
    expect(flexDiv.className).toContain('gap-3')
  })
})
