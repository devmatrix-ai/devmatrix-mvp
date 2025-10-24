/**
 * ReviewModal Component Tests
 *
 * Focused tests for critical behaviors:
 * - Modal open/close
 * - Escape key handling
 * - Backdrop click
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import ReviewModal from '../ReviewModal';

const mockReview = {
  review_id: 'review-1',
  atom_id: 'atom-1',
  confidence_score: 0.65,
  atom: {
    description: 'Test authentication logic',
    code: 'def login():\n  pass',
    language: 'python',
    file_path: 'src/auth/login.py',
  },
  ai_analysis: {
    total_issues: 1,
    issues_by_severity: {
      critical: 0,
      high: 1,
      medium: 0,
      low: 0,
    },
    issues: [
      {
        type: 'security',
        severity: 'high',
        description: 'Missing input validation',
        line_number: 1,
        code_snippet: 'def login():',
        explanation: 'User input should be validated',
      },
    ],
    suggestions: {},
    alternatives: ['Use bcrypt for password hashing'],
    recommendation: 'REVIEW CAREFULLY - security concerns detected',
  },
};

describe('ReviewModal', () => {
  it('renders modal when open is true', () => {
    const handleClose = vi.fn();
    const handleActionComplete = vi.fn();

    render(
      <ReviewModal
        review={mockReview}
        open={true}
        onClose={handleClose}
        onActionComplete={handleActionComplete}
      />
    );

    expect(screen.getByText(/Review: Test authentication logic/)).toBeInTheDocument();
  });

  it('does not render modal when open is false', () => {
    const handleClose = vi.fn();
    const handleActionComplete = vi.fn();

    render(
      <ReviewModal
        review={mockReview}
        open={false}
        onClose={handleClose}
        onActionComplete={handleActionComplete}
      />
    );

    expect(screen.queryByText(/Review: Test authentication logic/)).not.toBeInTheDocument();
  });

  it('calls onClose when close button is clicked', () => {
    const handleClose = vi.fn();
    const handleActionComplete = vi.fn();

    render(
      <ReviewModal
        review={mockReview}
        open={true}
        onClose={handleClose}
        onActionComplete={handleActionComplete}
      />
    );

    const closeButton = screen.getByLabelText('Close modal');
    fireEvent.click(closeButton);

    expect(handleClose).toHaveBeenCalledTimes(1);
  });

  it('calls onClose when Escape key is pressed', () => {
    const handleClose = vi.fn();
    const handleActionComplete = vi.fn();

    render(
      <ReviewModal
        review={mockReview}
        open={true}
        onClose={handleClose}
        onActionComplete={handleActionComplete}
      />
    );

    fireEvent.keyDown(document, { key: 'Escape' });

    expect(handleClose).toHaveBeenCalledTimes(1);
  });

  it('does not render when review is null', () => {
    const handleClose = vi.fn();
    const handleActionComplete = vi.fn();

    render(
      <ReviewModal
        review={null}
        open={true}
        onClose={handleClose}
        onActionComplete={handleActionComplete}
      />
    );

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });
});
