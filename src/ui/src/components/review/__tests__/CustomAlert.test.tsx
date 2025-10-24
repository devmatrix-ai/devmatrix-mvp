import { render, screen, fireEvent } from '@testing-library/react'
import { vi } from 'vitest'
import { CustomAlert } from '../CustomAlert'

describe('CustomAlert', () => {
  it('renders success alert with correct icon and styling', () => {
    render(<CustomAlert severity="success" message="Success message" />)

    expect(screen.getByText('Success message')).toBeInTheDocument()
    const container = screen.getByText('Success message').closest('.border-emerald-500')
    expect(container).toBeInTheDocument()
  })

  it('renders error alert with correct icon and styling', () => {
    render(<CustomAlert severity="error" message="Error message" />)

    expect(screen.getByText('Error message')).toBeInTheDocument()
    const container = screen.getByText('Error message').closest('.border-red-500')
    expect(container).toBeInTheDocument()
  })

  it('renders warning alert with correct icon and styling', () => {
    render(<CustomAlert severity="warning" message="Warning message" />)

    expect(screen.getByText('Warning message')).toBeInTheDocument()
    const container = screen.getByText('Warning message').closest('.border-amber-500')
    expect(container).toBeInTheDocument()
  })

  it('renders info alert with correct icon and styling', () => {
    render(<CustomAlert severity="info" message="Info message" />)

    expect(screen.getByText('Info message')).toBeInTheDocument()
    const container = screen.getByText('Info message').closest('.border-blue-500')
    expect(container).toBeInTheDocument()
  })

  it('shows close button when onClose is provided', () => {
    render(<CustomAlert severity="info" message="Test" onClose={() => {}} />)

    const closeButton = screen.getByLabelText('Close alert')
    expect(closeButton).toBeInTheDocument()
  })

  it('calls onClose when close button is clicked', () => {
    const handleClose = vi.fn()
    render(<CustomAlert severity="info" message="Test" onClose={handleClose} />)

    const closeButton = screen.getByLabelText('Close alert')
    fireEvent.click(closeButton)

    expect(handleClose).toHaveBeenCalledTimes(1)
  })

  it('does not show close button when onClose is not provided', () => {
    render(<CustomAlert severity="info" message="Test" />)

    expect(screen.queryByLabelText('Close alert')).not.toBeInTheDocument()
  })

  it('renders ReactNode as message', () => {
    render(
      <CustomAlert
        severity="success"
        message={<div><strong>Bold</strong> text</div>}
      />
    )

    expect(screen.getByText('Bold')).toBeInTheDocument()
    expect(screen.getByText('text')).toBeInTheDocument()
  })
})
