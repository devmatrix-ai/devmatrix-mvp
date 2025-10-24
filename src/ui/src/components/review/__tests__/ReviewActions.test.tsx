import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { vi } from 'vitest'
import ReviewActions from '../ReviewActions'

// Mock fetch globally
global.fetch = vi.fn()

describe('ReviewActions', () => {
  const mockProps = {
    reviewId: 'review-123',
    atomId: 'atom-456',
    currentCode: 'const x = 1;',
    onActionComplete: vi.fn(),
  }

  beforeEach(() => {
    vi.clearAllMocks()
    ;(global.fetch as any).mockClear()
  })

  it('renders all four action buttons', () => {
    render(<ReviewActions {...mockProps} />)

    expect(screen.getByText(/Approve/)).toBeInTheDocument()
    expect(screen.getByText(/Reject/)).toBeInTheDocument()
    expect(screen.getByText(/Edit Code/)).toBeInTheDocument()
    expect(screen.getByText(/Regenerate/)).toBeInTheDocument()
  })

  it('opens reject dialog when Reject button clicked', () => {
    render(<ReviewActions {...mockProps} />)

    const rejectButton = screen.getByText(/Reject/)
    fireEvent.click(rejectButton)

    expect(screen.getByText(/Reject Atom/)).toBeInTheDocument()
    expect(screen.getByPlaceholderText(/Explain why/i)).toBeInTheDocument()
  })

  it('opens edit dialog when Edit Code button clicked', () => {
    render(<ReviewActions {...mockProps} />)

    const editButton = screen.getByRole('button', { name: /Edit Code/ })
    fireEvent.click(editButton)

    expect(screen.getByRole('heading', { name: /Edit Code/ })).toBeInTheDocument()
    expect(screen.getByDisplayValue('const x = 1;')).toBeInTheDocument()
  })

  it('opens regenerate dialog when Regenerate button clicked', () => {
    render(<ReviewActions {...mockProps} />)

    const regenerateButton = screen.getByRole('button', { name: /Regenerate/ })
    fireEvent.click(regenerateButton)

    expect(screen.getByRole('heading', { name: /Request Regeneration/ })).toBeInTheDocument()
    expect(screen.getByPlaceholderText(/What should be changed/i)).toBeInTheDocument()
  })

  it('closes dialog when Cancel button clicked', () => {
    render(<ReviewActions {...mockProps} />)

    // Open reject dialog
    fireEvent.click(screen.getByText(/Reject/))
    expect(screen.getByText(/Reject Atom/)).toBeInTheDocument()

    // Click cancel
    const cancelButton = screen.getAllByText(/Cancel/)[0]
    fireEvent.click(cancelButton)

    // Dialog should be closed
    expect(screen.queryByText(/Reject Atom/)).not.toBeInTheDocument()
  })

  it('calls approve API when Approve button clicked', async () => {
    ;(global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ success: true }),
    })

    render(<ReviewActions {...mockProps} />)

    const approveButton = screen.getByText(/Approve/)
    fireEvent.click(approveButton)

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v2/review/approve'),
        expect.objectContaining({
          method: 'POST',
        })
      )
    })
  })

  it('displays success message after successful approve', async () => {
    ;(global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ success: true }),
    })

    render(<ReviewActions {...mockProps} />)

    const approveButton = screen.getByText(/Approve/)
    fireEvent.click(approveButton)

    await waitFor(() => {
      expect(screen.getByText(/approved successfully/i)).toBeInTheDocument()
    })
  })

  it('displays error message when API call fails', async () => {
    ;(global.fetch as any).mockResolvedValueOnce({
      ok: false,
    })

    render(<ReviewActions {...mockProps} />)

    const approveButton = screen.getByText(/Approve/)
    fireEvent.click(approveButton)

    await waitFor(() => {
      expect(screen.getByText(/Failed to approve/i)).toBeInTheDocument()
    })
  })
})
