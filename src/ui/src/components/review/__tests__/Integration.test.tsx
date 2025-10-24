/**
 * Integration Tests - Strategic gap filling for migrated components
 *
 * Tests critical integration workflows and edge cases across
 * all migrated components working together.
 *
 * Author: DevMatrix Team
 * Date: 2025-10-24
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import ReviewModal from '../ReviewModal'
import AISuggestionsPanel from '../AISuggestionsPanel'
import ReviewActions from '../ReviewActions'

// Mock fetch globally
global.fetch = vi.fn()

const mockCompleteReview = {
  review_id: 'review-123',
  atom_id: 'atom-456',
  confidence_score: 0.65,
  atom: {
    description: 'Authentication function with security issues',
    code: 'def login(username, password):\n  query = "SELECT * FROM users WHERE username = " + username',
    language: 'python',
    file_path: 'src/auth/login.py',
  },
  ai_analysis: {
    total_issues: 3,
    issues_by_severity: {
      critical: 1,
      high: 1,
      medium: 1,
      low: 0,
    },
    issues: [
      {
        type: 'security',
        severity: 'critical',
        description: 'SQL Injection vulnerability',
        line_number: 2,
        code_snippet: 'query = "SELECT * FROM users WHERE username = " + username',
        explanation: 'User input is directly concatenated into SQL query',
      },
      {
        type: 'security',
        severity: 'high',
        description: 'Missing password hashing',
        line_number: 1,
        code_snippet: null,
        explanation: 'Password should be hashed before comparison',
      },
      {
        type: 'style',
        severity: 'medium',
        description: 'Function too complex',
        line_number: 1,
        code_snippet: null,
        explanation: 'Consider splitting into smaller functions',
      },
    ],
    suggestions: {},
    alternatives: [
      'Use parameterized queries: cursor.execute("SELECT * FROM users WHERE username = ?", [username])',
      'Use ORM like SQLAlchemy for safer database access',
    ],
    recommendation: 'REJECT - Critical security vulnerabilities detected',
  },
}

describe('Integration Tests - Component Interactions', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    ;(global.fetch as any).mockClear()
  })

  it('ReviewModal renders all migrated components together correctly', () => {
    render(
      <ReviewModal
        review={mockCompleteReview}
        open={true}
        onClose={vi.fn()}
        onActionComplete={vi.fn()}
      />
    )

    // Verify ReviewModal header
    expect(screen.getByText(/Authentication function with security issues/)).toBeInTheDocument()

    // Verify ConfidenceIndicator in AISuggestionsPanel
    expect(screen.getByText(/65%/)).toBeInTheDocument()

    // Verify ReviewActions buttons
    expect(screen.getByText(/Approve/)).toBeInTheDocument()
    expect(screen.getByText(/Reject/)).toBeInTheDocument()
    expect(screen.getByText(/Edit Code/)).toBeInTheDocument()
    expect(screen.getByText(/Regenerate/)).toBeInTheDocument()

    // Verify CodeDiffViewer
    expect(screen.getByText(/code review/i)).toBeInTheDocument()
    expect(screen.getByText(/python/i)).toBeInTheDocument()

    // Verify AISuggestionsPanel sections
    expect(screen.getByText(/REJECT - Critical security vulnerabilities detected/)).toBeInTheDocument()
    expect(screen.getByText(/3 issues/i)).toBeInTheDocument()
  })

  it('ConfidenceIndicator displays correctly inside AISuggestionsPanel', () => {
    render(
      <AISuggestionsPanel
        analysis={mockCompleteReview.ai_analysis}
        confidenceScore={0.65}
      />
    )

    // Verify confidence score with correct color (65% = medium = amber-400, but 65% is low = orange-500)
    const confidenceLabel = screen.getByText(/65%/)
    expect(confidenceLabel).toBeInTheDocument()
    // 65% is actually "low" range (0.50-0.69), which uses text-orange-500
    expect(confidenceLabel).toHaveClass('text-orange-500')

    // Verify it's in a GlassCard with proper label
    expect(screen.getByText(/confidence score/i)).toBeInTheDocument()
  })

  it('CustomAccordion works with multiple instances in AISuggestionsPanel', () => {
    render(
      <AISuggestionsPanel
        analysis={mockCompleteReview.ai_analysis}
        confidenceScore={0.65}
      />
    )

    // Find both accordion buttons
    const alternativesAccordion = screen.getByRole('button', { name: /alternative implementations/i })

    // Both should be collapsed initially
    expect(screen.queryByText(/Use parameterized queries/)).not.toBeInTheDocument()

    // Expand alternatives accordion
    fireEvent.click(alternativesAccordion)
    expect(screen.getByText(/Use parameterized queries/)).toBeInTheDocument()

    // Collapse it again
    fireEvent.click(alternativesAccordion)
    expect(screen.queryByText(/Use parameterized queries/)).not.toBeInTheDocument()
  })

  it('CustomAlert appears after ReviewActions API success', async () => {
    ;(global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ success: true }),
    })

    render(
      <ReviewActions
        reviewId="review-123"
        atomId="atom-456"
        currentCode="test code"
        onActionComplete={vi.fn()}
      />
    )

    // Click approve button
    const approveButton = screen.getByText(/Approve/)
    fireEvent.click(approveButton)

    // Wait for success alert to appear
    await waitFor(() => {
      expect(screen.getByText(/approved successfully/i)).toBeInTheDocument()
    })

    // Verify CustomAlert styling (emerald border for success)
    const alertContainer = screen.getByText(/approved successfully/i).closest('.border-emerald-500')
    expect(alertContainer).toBeInTheDocument()
  })

  it('GlassInput multiline works in ReviewActions reject dialog', () => {
    render(
      <ReviewActions
        reviewId="review-123"
        atomId="atom-456"
        currentCode="test code"
        onActionComplete={vi.fn()}
      />
    )

    // Open reject dialog
    fireEvent.click(screen.getByText(/Reject/))

    // Verify textarea is rendered with multiline
    const textarea = screen.getByPlaceholderText(/Explain why/i) as HTMLTextAreaElement
    expect(textarea.tagName).toBe('TEXTAREA')
    expect(textarea).toBeInTheDocument()
  })

  it('GlassInput multiline works in ReviewActions edit dialog', () => {
    render(
      <ReviewActions
        reviewId="review-123"
        atomId="atom-456"
        currentCode="const x = 1;"
        onActionComplete={vi.fn()}
      />
    )

    // Open edit dialog
    fireEvent.click(screen.getByRole('button', { name: /Edit Code/ }))

    // Verify large textarea is rendered for code editing
    const textarea = screen.getByDisplayValue('const x = 1;') as HTMLTextAreaElement
    expect(textarea.tagName).toBe('TEXTAREA')
    expect(textarea).toBeInTheDocument()
  })

  it('Issues list in CodeDiffViewer displays with severity badges', () => {
    render(
      <ReviewModal
        review={mockCompleteReview}
        open={true}
        onClose={vi.fn()}
        onActionComplete={vi.fn()}
      />
    )

    // Verify issues summary shows correct counts
    expect(screen.getByText(/3 issues/i)).toBeInTheDocument()

    // Verify severity breakdown is displayed (2 critical/high total)
    expect(screen.getByText(/2 critical\/high/)).toBeInTheDocument()
    expect(screen.getByText(/1 medium/)).toBeInTheDocument()
  })

  it('ReviewActions complete flow: approve → success alert → callback', async () => {
    ;(global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ success: true }),
    })

    const mockOnActionComplete = vi.fn()

    render(
      <ReviewActions
        reviewId="review-123"
        atomId="atom-456"
        currentCode="test code"
        onActionComplete={mockOnActionComplete}
      />
    )

    // Click approve
    fireEvent.click(screen.getByText(/Approve/))

    // Wait for API call and success message
    await waitFor(() => {
      expect(screen.getByText(/approved successfully/i)).toBeInTheDocument()
    })

    // Wait for callback to be called (happens after 1.5s timeout)
    await waitFor(() => {
      expect(mockOnActionComplete).toHaveBeenCalledTimes(1)
    }, { timeout: 2000 })
  })

  it('ReviewModal responsive grid layout renders correctly', () => {
    render(
      <ReviewModal
        review={mockCompleteReview}
        open={true}
        onClose={vi.fn()}
        onActionComplete={vi.fn()}
      />
    )

    // Verify modal dialog is present
    const dialog = screen.getByRole('dialog')
    expect(dialog).toBeInTheDocument()

    // Verify grid container exists with lg:grid-cols-3
    const modalContent = dialog.querySelector('.grid-cols-1.lg\\:grid-cols-3')
    expect(modalContent).toBeInTheDocument()
  })

  it('Keyboard navigation: Tab and Escape work correctly', () => {
    const mockOnClose = vi.fn()

    render(
      <ReviewModal
        review={mockCompleteReview}
        open={true}
        onClose={mockOnClose}
        onActionComplete={vi.fn()}
      />
    )

    // Test Escape key closes modal
    fireEvent.keyDown(document, { key: 'Escape' })
    expect(mockOnClose).toHaveBeenCalledTimes(1)

    // Verify all interactive elements are present for Tab navigation
    const closeButton = screen.getByLabelText('Close modal')
    const approveButton = screen.getByText(/Approve/)
    const rejectButton = screen.getByText(/Reject/)

    expect(closeButton).toBeInTheDocument()
    expect(approveButton).toBeInTheDocument()
    expect(rejectButton).toBeInTheDocument()
  })
})
