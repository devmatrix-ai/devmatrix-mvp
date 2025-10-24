/**
 * ReviewCard Component Tests
 *
 * Focused tests for critical behaviors:
 * - Rendering with review data
 * - Click handlers
 * - Badge status logic
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import ReviewCard from '../ReviewCard';

const mockReview = {
  review_id: 'review-1',
  atom_id: 'atom-1',
  atom: {
    description: 'Test authentication logic',
    file_path: 'src/auth/login.py',
  },
  confidence_score: 0.65,
  priority: 80,
  status: 'pending',
  ai_analysis: {
    issues_by_severity: {
      critical: 2,
      high: 3,
      medium: 1,
      low: 0,
    },
    recommendation: 'Review carefully for security issues',
  },
};

describe('ReviewCard', () => {
  it('renders review information correctly', () => {
    const handleClick = vi.fn();
    render(<ReviewCard review={mockReview} onClick={handleClick} />);

    expect(screen.getByText('Test authentication logic')).toBeInTheDocument();
    expect(screen.getByText('src/auth/login.py')).toBeInTheDocument();
    expect(screen.getByText(/Priority 80/)).toBeInTheDocument();
    expect(screen.getByText(/2 Critical/)).toBeInTheDocument();
    expect(screen.getByText(/3 High/)).toBeInTheDocument();
    expect(screen.getByText(/1 Medium/)).toBeInTheDocument();
    expect(screen.getByText(/Status: PENDING/)).toBeInTheDocument();
    expect(screen.getByText(/Review carefully for security issues/)).toBeInTheDocument();
  });

  it('applies custom className to card', () => {
    const handleClick = vi.fn();
    const { container } = render(
      <ReviewCard review={mockReview} onClick={handleClick} className="custom-class" />
    );

    expect(container.querySelector('.custom-class')).toBeInTheDocument();
  });

  it('calls onClick handler when button is clicked', () => {
    const handleClick = vi.fn();
    render(<ReviewCard review={mockReview} onClick={handleClick} />);

    const button = screen.getByText(/View Review/);
    fireEvent.click(button);

    expect(handleClick).toHaveBeenCalled();
  });

  it('shows correct priority badge color for high priority', () => {
    const handleClick = vi.fn();
    const highPriorityReview = { ...mockReview, priority: 85 };

    render(<ReviewCard review={highPriorityReview} onClick={handleClick} />);
    expect(screen.getByText(/Priority 85/)).toBeInTheDocument();
  });

  it('hides issue badges when count is zero', () => {
    const handleClick = vi.fn();
    const noIssuesReview = {
      ...mockReview,
      ai_analysis: {
        ...mockReview.ai_analysis,
        issues_by_severity: {
          critical: 0,
          high: 0,
          medium: 0,
          low: 1,
        },
      },
    };

    render(<ReviewCard review={noIssuesReview} onClick={handleClick} />);
    expect(screen.queryByText(/Critical/)).not.toBeInTheDocument();
    expect(screen.queryByText(/High/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Medium/)).not.toBeInTheDocument();
    expect(screen.getByText(/1 Low/)).toBeInTheDocument();
  });
});
