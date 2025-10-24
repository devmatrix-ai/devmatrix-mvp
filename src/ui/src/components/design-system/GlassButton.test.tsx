import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { GlassButton } from './GlassButton'

describe('GlassButton', () => {
  it('renders children correctly', () => {
    render(<GlassButton>Click Me</GlassButton>)
    expect(screen.getByText('Click Me')).toBeInTheDocument()
  })

  it('renders primary variant with correct classes', () => {
    render(<GlassButton variant="primary">Primary</GlassButton>)
    const button = screen.getByText('Primary')

    expect(button.className).toContain('bg-purple-600')
    expect(button.className).toContain('text-white')
    expect(button.className).toContain('shadow-lg')
  })

  it('renders secondary variant with correct classes', () => {
    render(<GlassButton variant="secondary">Secondary</GlassButton>)
    const button = screen.getByText('Secondary')

    expect(button.className).toContain('bg-white/10')
    expect(button.className).toContain('text-gray-300')
  })

  it('renders ghost variant with correct classes', () => {
    render(<GlassButton variant="ghost">Ghost</GlassButton>)
    const button = screen.getByText('Ghost')

    expect(button.className).toContain('bg-transparent')
    expect(button.className).toContain('border')
    expect(button.className).toContain('border-white/20')
  })

  it('applies size classes correctly', () => {
    const { rerender } = render(<GlassButton size="sm">Small</GlassButton>)
    expect(screen.getByText('Small').className).toContain('px-3')
    expect(screen.getByText('Small').className).toContain('text-sm')

    rerender(<GlassButton size="md">Medium</GlassButton>)
    expect(screen.getByText('Medium').className).toContain('px-4')

    rerender(<GlassButton size="lg">Large</GlassButton>)
    expect(screen.getByText('Large').className).toContain('px-6')
    expect(screen.getByText('Large').className).toContain('text-lg')
  })

  it('handles onClick events', async () => {
    const user = userEvent.setup()
    const handleClick = vi.fn()

    render(<GlassButton onClick={handleClick}>Click</GlassButton>)
    const button = screen.getByText('Click')

    await user.click(button)
    expect(handleClick).toHaveBeenCalledTimes(1)
  })

  it('applies disabled state correctly', () => {
    render(<GlassButton disabled>Disabled</GlassButton>)
    const button = screen.getByText('Disabled')

    expect(button).toBeDisabled()
    expect(button.className).toContain('opacity-50')
    expect(button.className).toContain('cursor-not-allowed')
  })

  it('merges custom className prop correctly', () => {
    render(<GlassButton className="custom-width">Button</GlassButton>)
    const button = screen.getByText('Button')

    expect(button.className).toContain('custom-width')
    expect(button.className).toContain('bg-purple-600')
  })

  it('forwards ref correctly', () => {
    const ref = { current: null as HTMLButtonElement | null }
    render(<GlassButton ref={ref}>Button</GlassButton>)

    expect(ref.current).toBeInstanceOf(HTMLButtonElement)
  })
})
