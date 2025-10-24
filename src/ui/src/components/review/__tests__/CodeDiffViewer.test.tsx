/**
 * CodeDiffViewer - Tests
 *
 * Author: DevMatrix Team
 * Date: 2025-10-24
 */

import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import CodeDiffViewer from '../CodeDiffViewer'

describe('CodeDiffViewer', () => {
  const mockCode = `function calculateTotal(items) {
  let total = 0;
  for (let i = 0; i < items.length; i++) {
    total += items[i].price;
  }
  return total;
}`

  const mockOriginalCode = `function calculateTotal(items) {
  var total = 0;
  for (var i = 0; i < items.length; i++) {
    total = total + items[i].price;
  }
  return total;
}`

  const mockIssues = [
    {
      type: 'style',
      severity: 'low',
      description: 'Use const instead of let',
      line_number: 2,
      code_snippet: 'let total = 0;',
      explanation: 'Variables that are not reassigned should use const',
    },
    {
      type: 'performance',
      severity: 'medium',
      description: 'Consider using reduce',
      line_number: 3,
      code_snippet: null,
      explanation: 'Array.reduce() is more functional and readable',
    },
  ]

  it('renders code viewer header with title', () => {
    render(<CodeDiffViewer code={mockCode} language="javascript" issues={[]} />)
    expect(screen.getByText(/code review/i)).toBeInTheDocument()
  })

  it('displays language badge', () => {
    render(<CodeDiffViewer code={mockCode} language="javascript" issues={[]} />)
    expect(screen.getByText('javascript')).toBeInTheDocument()
  })

  it('shows issues count badge with correct status', () => {
    render(<CodeDiffViewer code={mockCode} language="javascript" issues={mockIssues} />)
    expect(screen.getByText(/2 issues/i)).toBeInTheDocument()
  })

  it('copies code when copy button clicked', async () => {
    // Mock clipboard API
    Object.assign(navigator, {
      clipboard: {
        writeText: vi.fn(() => Promise.resolve()),
      },
    })

    render(<CodeDiffViewer code={mockCode} language="javascript" issues={[]} />)

    const copyButton = screen.getByRole('button', { name: /copy/i })
    fireEvent.click(copyButton)

    expect(navigator.clipboard.writeText).toHaveBeenCalledWith(mockCode)
  })

  it('switches between current and diff tabs when original code provided', () => {
    render(
      <CodeDiffViewer
        code={mockCode}
        language="javascript"
        issues={[]}
        originalCode={mockOriginalCode}
      />
    )

    // Should show both tabs
    const currentTab = screen.getByRole('button', { name: /current code/i })
    const diffTab = screen.getByRole('button', { name: /diff view/i })

    expect(currentTab).toBeInTheDocument()
    expect(diffTab).toBeInTheDocument()

    // Diff should be active by default when originalCode provided
    expect(diffTab).toHaveClass('bg-purple-600')

    // Switch to current tab
    fireEvent.click(currentTab)
    expect(currentTab).toHaveClass('bg-purple-600')
  })

  it('does not show tabs when no original code provided', () => {
    render(<CodeDiffViewer code={mockCode} language="javascript" issues={[]} />)

    expect(screen.queryByRole('button', { name: /current code/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /diff view/i })).not.toBeInTheDocument()
  })

  it('displays issues list when issues present', () => {
    render(<CodeDiffViewer code={mockCode} language="javascript" issues={mockIssues} />)

    expect(screen.getByText(/issues found \(2\)/i)).toBeInTheDocument()
    expect(screen.getByText(/line 2: use const instead of let/i)).toBeInTheDocument()
    expect(screen.getByText(/variables that are not reassigned should use const/i)).toBeInTheDocument()
  })

  it('shows issues summary footer with severity breakdown', () => {
    render(<CodeDiffViewer code={mockCode} language="javascript" issues={mockIssues} />)

    // Should show severity breakdown
    expect(screen.getByText(/0 critical\/high/i)).toBeInTheDocument()
    expect(screen.getByText(/1 medium/i)).toBeInTheDocument()
    expect(screen.getByText(/1 low/i)).toBeInTheDocument()
  })

  it('does not render issues section when no issues', () => {
    render(<CodeDiffViewer code={mockCode} language="javascript" issues={[]} />)

    expect(screen.queryByText(/issues found/i)).not.toBeInTheDocument()
  })
})
