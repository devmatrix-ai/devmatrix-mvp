import { describe, it, expect } from 'vitest'
import { render } from '@testing-library/react'
import { GlassButton } from './GlassButton'
import { GlassInput } from './GlassInput'
import { PageHeader } from './PageHeader'
import { SectionHeader } from './SectionHeader'

describe('Accessibility', () => {
  it('GlassButton uses semantic button element', () => {
    const { container } = render(<GlassButton>Click</GlassButton>)
    const button = container.querySelector('button')

    expect(button).toBeInTheDocument()
    expect(button?.tagName).toBe('BUTTON')
  })

  it('GlassInput uses semantic input element with proper type', () => {
    const { container } = render(
      <GlassInput type="email" placeholder="Email" onChange={() => {}} />
    )
    const input = container.querySelector('input')

    expect(input).toBeInTheDocument()
    expect(input?.getAttribute('type')).toBe('email')
  })

  it('PageHeader uses semantic h1 heading element for title', () => {
    const { container } = render(
      <PageHeader emoji="🎯" title="Test Title" />
    )
    const heading = container.querySelector('h1')

    expect(heading).toBeInTheDocument()
    expect(heading?.textContent).toBe('Test Title')
  })

  it('SectionHeader uses h2 heading element', () => {
    const { container } = render(<SectionHeader>Section</SectionHeader>)
    const heading = container.querySelector('h2')

    expect(heading).toBeInTheDocument()
    expect(heading?.textContent).toBe('Section')
  })
})
