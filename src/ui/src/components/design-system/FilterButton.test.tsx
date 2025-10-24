import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { FilterButton } from './FilterButton'

describe('FilterButton', () => {
  it('applies active state styling when active', () => {
    const { container } = render(<FilterButton active onClick={() => {}}>Active</FilterButton>)
    const button = container.firstChild as HTMLElement

    expect(button.className).toContain('bg-purple-600')
    expect(button.className).toContain('shadow-lg')
  })

  it('applies inactive state styling when not active', () => {
    const { container } = render(<FilterButton active={false} onClick={() => {}}>Inactive</FilterButton>)
    const button = container.firstChild as HTMLElement

    expect(button.className).toContain('bg-white/10')
    expect(button.className).toContain('hover:bg-white/20')
  })

  it('handles onClick correctly', async () => {
    const handleClick = vi.fn()
    const user = userEvent.setup()

    render(<FilterButton active={false} onClick={handleClick}>Click</FilterButton>)
    const button = screen.getByText('Click')

    await user.click(button)
    expect(handleClick).toHaveBeenCalled()
  })
})
