import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { SearchBar } from './SearchBar'

describe('SearchBar', () => {
  it('renders with search icon', () => {
    const { container } = render(<SearchBar value="" onChange={() => {}} />)
    const svgIcon = container.querySelector('svg')

    expect(svgIcon).toBeInTheDocument()
  })

  it('handles search input changes', async () => {
    const handleChange = vi.fn()
    const user = userEvent.setup()

    render(<SearchBar value="" onChange={handleChange} placeholder="Search..." />)
    const input = screen.getByPlaceholderText('Search...')

    await user.type(input, 'test')
    expect(handleChange).toHaveBeenCalled()
  })
})
