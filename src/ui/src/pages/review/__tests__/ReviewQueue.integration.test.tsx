/**
 * ReviewQueue Integration Tests
 *
 * Tests critical user workflows:
 * - Search functionality
 * - Filter functionality
 * - Modal open/close
 * - Responsive behavior
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { describe, test, expect, beforeEach, afterEach, vi } from 'vitest';
import ReviewQueue from '../ReviewQueue';

// Mock fetch API
declare const global: typeof globalThis & { fetch: any };
global.fetch = vi.fn();
const globalAny = global;

const mockReviews = [
  {
    review_id: 'rev-1',
    atom_id: 'atom-1',
    atom: {
      description: 'Authentication logic needs review',
      code: 'function auth() { return true; }',
      language: 'javascript',
      file_path: 'src/auth/login.js',
      complexity: 8.5,
      status: 'pending'
    },
    confidence_score: 0.45,
    priority: 85,
    status: 'pending',
    assigned_to: null,
    ai_analysis: {
      total_issues: 3,
      issues_by_severity: {
        critical: 1,
        high: 1,
        medium: 1,
        low: 0
      },
      issues: [],
      suggestions: {},
      alternatives: [],
      recommendation: 'Manual review required'
    },
    reviewer_feedback: null,
    created_at: '2025-01-01T00:00:00Z',
    updated_at: '2025-01-01T00:00:00Z'
  },
  {
    review_id: 'rev-2',
    atom_id: 'atom-2',
    atom: {
      description: 'Database query optimization',
      code: 'SELECT * FROM users',
      language: 'sql',
      file_path: 'src/db/queries.sql',
      complexity: 6.2,
      status: 'pending'
    },
    confidence_score: 0.62,
    priority: 55,
    status: 'pending',
    assigned_to: null,
    ai_analysis: {
      total_issues: 1,
      issues_by_severity: {
        critical: 0,
        high: 0,
        medium: 1,
        low: 0
      },
      issues: [],
      suggestions: {},
      alternatives: [],
      recommendation: 'Consider optimization'
    },
    reviewer_feedback: null,
    created_at: '2025-01-01T01:00:00Z',
    updated_at: '2025-01-01T01:00:00Z'
  }
];

describe('ReviewQueue Integration Tests', () => {
  beforeEach(() => {
    vi.mocked(globalAny.fetch).mockResolvedValue({
      ok: true,
      json: async () => ({ queue: mockReviews })
    } as Response);
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  test('should load and display reviews', async () => {
    render(<ReviewQueue />);

    await waitFor(() => {
      expect(screen.getByText('Authentication logic needs review')).toBeInTheDocument();
      expect(screen.getByText('Database query optimization')).toBeInTheDocument();
    });
  });

  test('should filter reviews by search query', async () => {
    render(<ReviewQueue />);

    await waitFor(() => {
      expect(screen.getByText('Authentication logic needs review')).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText(/search/i);
    fireEvent.change(searchInput, { target: { value: 'database' } });

    await waitFor(() => {
      expect(screen.queryByText('Authentication logic needs review')).not.toBeInTheDocument();
      expect(screen.getByText('Database query optimization')).toBeInTheDocument();
    });
  });

  test('should filter reviews by status', async () => {
    render(<ReviewQueue />);

    await waitFor(() => {
      expect(screen.getByText('Authentication logic needs review')).toBeInTheDocument();
    });

    // Test approved filter (should show no results)
    const approvedButton = screen.getByRole('button', { name: /approved/i });
    fireEvent.click(approvedButton);

    await waitFor(() => {
      expect(globalAny.fetch).toHaveBeenCalledWith(
        expect.stringContaining('status=approved')
      );
    });
  });

  test('should open modal when clicking review card', async () => {
    render(<ReviewQueue />);

    await waitFor(() => {
      expect(screen.getByText('Authentication logic needs review')).toBeInTheDocument();
    });

    // Find and click the "View Review" button
    const viewButtons = screen.getAllByText(/view review/i);
    fireEvent.click(viewButtons[0]);

    await waitFor(() => {
      // Modal should show review title
      expect(screen.getByText(/review: authentication logic needs review/i)).toBeInTheDocument();
    });
  });

  test('should close modal with X button', async () => {
    render(<ReviewQueue />);

    await waitFor(() => {
      expect(screen.getByText('Authentication logic needs review')).toBeInTheDocument();
    });

    // Open modal
    const viewButtons = screen.getAllByText(/view review/i);
    fireEvent.click(viewButtons[0]);

    await waitFor(() => {
      expect(screen.getByText(/review: authentication logic needs review/i)).toBeInTheDocument();
    });

    // Close modal with X button
    const closeButton = screen.getByLabelText(/close modal/i);
    fireEvent.click(closeButton);

    await waitFor(() => {
      expect(screen.queryByText(/review: authentication logic needs review/i)).not.toBeInTheDocument();
    });
  });

  test('should close modal with Escape key', async () => {
    render(<ReviewQueue />);

    await waitFor(() => {
      expect(screen.getByText('Authentication logic needs review')).toBeInTheDocument();
    });

    // Open modal
    const viewButtons = screen.getAllByText(/view review/i);
    fireEvent.click(viewButtons[0]);

    await waitFor(() => {
      expect(screen.getByText(/review: authentication logic needs review/i)).toBeInTheDocument();
    });

    // Close modal with Escape key
    fireEvent.keyDown(document, { key: 'Escape', code: 'Escape' });

    await waitFor(() => {
      expect(screen.queryByText(/review: authentication logic needs review/i)).not.toBeInTheDocument();
    });
  });

  test('should display loading state initially', () => {
    render(<ReviewQueue />);
    expect(screen.getByRole('status')).toBeInTheDocument();
  });

  test('should display error state on fetch failure', async () => {
    vi.mocked(globalAny.fetch).mockRejectedValueOnce(new Error('Network error'));

    render(<ReviewQueue />);

    await waitFor(() => {
      expect(screen.getByText(/network error/i)).toBeInTheDocument();
    });
  });
});
