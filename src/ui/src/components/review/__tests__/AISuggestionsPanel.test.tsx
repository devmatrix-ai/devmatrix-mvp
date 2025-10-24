/**
 * AISuggestionsPanel - Tests
 *
 * Author: DevMatrix Team
 * Date: 2025-10-24
 */

import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import AISuggestionsPanel from '../AISuggestionsPanel'

describe('AISuggestionsPanel', () => {
  const mockAnalysis = {
    total_issues: 5,
    issues_by_severity: {
      critical: 2,
      high: 1,
      medium: 1,
      low: 1,
    },
    issues: [
      {
        type: 'security',
        severity: 'critical',
        description: 'SQL Injection vulnerability',
        line_number: 42,
        code_snippet: 'query = "SELECT * FROM users WHERE id = " + userId',
        explanation: 'User input is directly concatenated into SQL query',
      },
      {
        type: 'performance',
        severity: 'medium',
        description: 'Inefficient loop',
        line_number: 15,
        code_snippet: null,
        explanation: 'Consider using map() instead of forEach()',
      },
    ],
    suggestions: {},
    alternatives: [
      'const query = `SELECT * FROM users WHERE id = ?`;\ndb.query(query, [userId]);',
      'const user = await db.users.findById(userId);',
    ],
    recommendation: 'EDIT REQUIRED: Critical security issues detected',
  }

  it('renders confidence score with ConfidenceIndicator', () => {
    render(<AISuggestionsPanel analysis={mockAnalysis} confidenceScore={0.65} />)
    expect(screen.getByText(/confidence score/i)).toBeInTheDocument()
    expect(screen.getByText(/65%/i)).toBeInTheDocument()
  })

  it('displays AI recommendation with CustomAlert', () => {
    render(<AISuggestionsPanel analysis={mockAnalysis} confidenceScore={0.65} />)
    expect(screen.getByText(/EDIT REQUIRED: Critical security issues detected/i)).toBeInTheDocument()
  })

  it('shows issues summary with severity badges', () => {
    render(<AISuggestionsPanel analysis={mockAnalysis} confidenceScore={0.65} />)
    expect(screen.getByText(/issues detected \(5\)/i)).toBeInTheDocument()
    expect(screen.getByText(/2 critical/i)).toBeInTheDocument()
    expect(screen.getByText(/1 high/i)).toBeInTheDocument()
    expect(screen.getByText(/1 medium/i)).toBeInTheDocument()
    expect(screen.getByText(/1 low/i)).toBeInTheDocument()
  })

  it('displays issue details with descriptions and explanations', () => {
    render(<AISuggestionsPanel analysis={mockAnalysis} confidenceScore={0.65} />)
    expect(screen.getByText(/SQL Injection vulnerability/i)).toBeInTheDocument()
    expect(screen.getByText(/User input is directly concatenated into SQL query/i)).toBeInTheDocument()
    expect(screen.getByText(/line 42/i)).toBeInTheDocument()
  })

  it('expands alternatives accordion when clicked', () => {
    render(<AISuggestionsPanel analysis={mockAnalysis} confidenceScore={0.65} />)

    const accordionButton = screen.getByRole('button', { name: /alternative implementations/i })
    expect(accordionButton).toBeInTheDocument()

    // Check alternatives are not visible initially
    expect(screen.queryByText(/const query =/)).not.toBeInTheDocument()

    // Click to expand
    fireEvent.click(accordionButton)

    // Check alternatives are now visible
    expect(screen.getByText(/const query =/)).toBeInTheDocument()
  })

  it('copies alternative implementation when copy button clicked', async () => {
    // Mock clipboard API
    Object.assign(navigator, {
      clipboard: {
        writeText: vi.fn(() => Promise.resolve()),
      },
    })

    render(<AISuggestionsPanel analysis={mockAnalysis} confidenceScore={0.65} />)

    // Expand accordion first
    const accordionButton = screen.getByRole('button', { name: /alternative implementations/i })
    fireEvent.click(accordionButton)

    // Find and click copy button
    const copyButtons = screen.getAllByRole('button', { name: /copy/i })
    fireEvent.click(copyButtons[0])

    // Verify clipboard was called with correct text
    expect(navigator.clipboard.writeText).toHaveBeenCalledWith(mockAnalysis.alternatives[0])
  })

  it('does not render alternatives accordion when no alternatives exist', () => {
    const analysisWithoutAlternatives = {
      ...mockAnalysis,
      alternatives: [],
    }

    render(<AISuggestionsPanel analysis={analysisWithoutAlternatives} confidenceScore={0.65} />)
    expect(screen.queryByRole('button', { name: /alternative implementations/i })).not.toBeInTheDocument()
  })
})
