import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { StatusBadge } from './StatusBadge'

describe('StatusBadge', () => {
  it('renders children correctly', () => {
    render(<StatusBadge>Active</StatusBadge>)
    expect(screen.getByText('Active')).toBeInTheDocument()
  })

  it('applies default status classes when no status provided', () => {
    render(<StatusBadge>Default</StatusBadge>)
    const badge = screen.getByText('Default')

    expect(badge.className).toContain('bg-gray-500/20')
    expect(badge.className).toContain('text-gray-400')
    expect(badge.className).toContain('border-gray-500/50')
  })

  it('renders success status with correct classes', () => {
    render(<StatusBadge status="success">Success</StatusBadge>)
    const badge = screen.getByText('Success')

    expect(badge.className).toContain('bg-green-500/20')
    expect(badge.className).toContain('text-green-400')
    expect(badge.className).toContain('border-green-500/50')
  })

  it('renders warning status with correct classes', () => {
    render(<StatusBadge status="warning">Warning</StatusBadge>)
    const badge = screen.getByText('Warning')

    expect(badge.className).toContain('bg-yellow-500/20')
    expect(badge.className).toContain('text-yellow-400')
  })

  it('renders error status with correct classes', () => {
    render(<StatusBadge status="error">Error</StatusBadge>)
    const badge = screen.getByText('Error')

    expect(badge.className).toContain('bg-red-500/20')
    expect(badge.className).toContain('text-red-400')
  })

  it('renders info status with correct classes', () => {
    render(<StatusBadge status="info">Info</StatusBadge>)
    const badge = screen.getByText('Info')

    expect(badge.className).toContain('bg-blue-500/20')
    expect(badge.className).toContain('text-blue-400')
  })

  it('merges custom className prop correctly', () => {
    render(
      <StatusBadge status="success" className="custom-margin">
        Success
      </StatusBadge>
    )
    const badge = screen.getByText('Success')

    expect(badge.className).toContain('custom-margin')
    expect(badge.className).toContain('bg-green-500/20')
  })

  it('applies base styling classes', () => {
    render(<StatusBadge>Badge</StatusBadge>)
    const badge = screen.getByText('Badge')

    expect(badge.className).toContain('px-3')
    expect(badge.className).toContain('py-1')
    expect(badge.className).toContain('rounded-full')
    expect(badge.className).toContain('text-xs')
    expect(badge.className).toContain('font-medium')
    expect(badge.className).toContain('border')
  })
})
