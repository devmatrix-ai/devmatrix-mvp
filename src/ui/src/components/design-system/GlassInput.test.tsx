import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { GlassInput } from './GlassInput'
import { FiSearch } from 'react-icons/fi'

describe('GlassInput', () => {
  it('renders input with placeholder', () => {
    render(<GlassInput placeholder="Enter text..." onChange={() => {}} />)
    expect(screen.getByPlaceholderText('Enter text...')).toBeInTheDocument()
  })

  it('handles onChange correctly', async () => {
    const handleChange = vi.fn()
    const user = userEvent.setup()

    render(<GlassInput placeholder="Test" onChange={handleChange} />)
    const input = screen.getByPlaceholderText('Test')

    await user.type(input, 'Hello')
    expect(handleChange).toHaveBeenCalled()
  })

  it('applies pl-12 when icon provided', () => {
    render(<GlassInput icon={<FiSearch />} placeholder="Search" onChange={() => {}} />)
    const input = screen.getByPlaceholderText('Search')

    expect(input.className).toContain('pl-12')
  })

  it('merges custom className correctly', () => {
    render(<GlassInput placeholder="Test" onChange={() => {}} className="custom-class" />)
    const input = screen.getByPlaceholderText('Test')

    expect(input.className).toContain('custom-class')
    expect(input.className).toContain('bg-white/5')
  })

  it('forwards ref correctly', () => {
    const ref = { current: null as HTMLInputElement | null }
    render(<GlassInput ref={ref} placeholder="Test" onChange={() => {}} />)

    expect(ref.current).toBeInstanceOf(HTMLInputElement)
  })
})
