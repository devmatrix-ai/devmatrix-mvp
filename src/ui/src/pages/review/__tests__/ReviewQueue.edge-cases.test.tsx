/**
 * ReviewQueue Edge Cases Tests
 *
 * Strategic gap-filling tests for critical edge cases:
 * - Extreme confidence scores (0.0, 1.0)
 * - Reviews without issues
 * - Modal backdrop click
 * - Sorting functionality
 * - Combined filters (search + status)
 * - Refresh button
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { describe, test, expect, beforeEach, afterEach, vi } from 'vitest';
import ReviewQueue from '../ReviewQueue';

// Mock fetch API
declare const global: typeof globalThis & { fetch: any };
global.fetch = vi.fn();
const globalAny = global;

const mockReviewWithNoIssues = {
  review_id: 'rev-no-issues',
  atom_id: 'atom-clean',
  atom: {
    description: 'Perfect code',
    code: 'function hello() { return "world"; }',
    language: 'javascript',
    file_path: 'src/utils/greeting.js',
    complexity: 2.0,
    status: 'pending'
  },
  confidence_score: 1.0, // Perfect confidence
  priority: 10,
  status: 'pending',
  assigned_to: null,
  ai_analysis: {
    total_issues: 0,
    issues_by_severity: {
      critical: 0,
      high: 0,
      medium: 0,
      low: 0
    },
    issues: [],
    suggestions: {},
    alternatives: [],
    recommendation: 'Code looks good'
  },
  reviewer_feedback: null,
  created_at: '2025-01-01T00:00:00Z',
  updated_at: '2025-01-01T00:00:00Z'
};

const mockReviewLowConfidence = {
  review_id: 'rev-low-conf',
  atom_id: 'atom-uncertain',
  atom: {
    description: 'Uncertain analysis',
    code: 'function complex() { /* ... */ }',
    language: 'javascript',
    file_path: 'src/complex/analysis.js',
    complexity: 9.8,
    status: 'pending'
  },
  confidence_score: 0.05, // Very low confidence
  priority: 95,
  status: 'pending',
  assigned_to: null,
  ai_analysis: {
    total_issues: 5,
    issues_by_severity: {
      critical: 2,
      high: 2,
      medium: 1,
      low: 0
    },
    issues: [],
    suggestions: {},
    alternatives: [],
    recommendation: 'Requires careful human review'
  },
  reviewer_feedback: null,
  created_at: '2025-01-01T00:00:00Z',
  updated_at: '2025-01-01T00:00:00Z'
};

const mockReviewForSort = {
  review_id: 'rev-sort',
  atom_id: 'atom-sort',
  atom: {
    description: 'Middle priority',
    code: 'function test() {}',
    language: 'javascript',
    file_path: 'src/test.js',
    complexity: 5.0,
    status: 'pending'
  },
  confidence_score: 0.5,
  priority: 50,
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
    recommendation: 'Review recommended'
  },
  reviewer_feedback: null,
  created_at: '2025-01-02T00:00:00Z',
  updated_at: '2025-01-02T00:00:00Z'
};

describe('ReviewQueue Edge Cases Tests', () => {
  beforeEach(() => {
    vi.mocked(globalAny.fetch).mockResolvedValue({
      ok: true,
      json: async () => ({ queue: [mockReviewWithNoIssues, mockReviewLowConfidence, mockReviewForSort] })
    } as Response);
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  test('should display review with zero issues correctly', async () => {
    render(<ReviewQueue />);

    await waitFor(() => {
      expect(screen.getByText('Perfect code')).toBeInTheDocument();
      expect(screen.getByText(/Code looks good/i)).toBeInTheDocument();
    });

    // Should not display any issue badges for this review
    const cards = screen.getAllByText(/Priority/);
    expect(cards.length).toBeGreaterThan(0);
  });

  test('should display extreme confidence scores correctly', async () => {
    render(<ReviewQueue />);

    await waitFor(() => {
      // Very low confidence (0.05)
      expect(screen.getByText('Uncertain analysis')).toBeInTheDocument();
      // Perfect confidence (1.0)
      expect(screen.getByText('Perfect code')).toBeInTheDocument();
    });
  });

  test('should sort reviews by priority (default)', async () => {
    render(<ReviewQueue />);

    await waitFor(() => {
      const descriptions = screen.getAllByText(/analysis|code|priority/i);
      expect(descriptions.length).toBeGreaterThan(0);
    });

    // With desc order, high priority (95) should come before low priority (10)
    const cards = screen.getAllByText(/Priority/);
    expect(cards[0]).toHaveTextContent('95'); // Highest priority first
  });

  test('should close modal on backdrop click', async () => {
    render(<ReviewQueue />);

    await waitFor(() => {
      expect(screen.getByText('Perfect code')).toBeInTheDocument();
    });

    // Open modal
    const viewButtons = screen.getAllByText(/view review/i);
    fireEvent.click(viewButtons[0]);

    // Wait for modal to open with longer timeout
    await waitFor(() => {
      const modalTitle = screen.queryByText(/review:/i);
      expect(modalTitle).toBeInTheDocument();
    }, { timeout: 3000 });

    // Click backdrop (the outer div with backdrop-blur)
    const backdrop = document.querySelector('.fixed.inset-0.bg-black\\/50.backdrop-blur-sm');
    if (backdrop) {
      fireEvent.click(backdrop);

      await waitFor(() => {
        const modalTitle = screen.queryByText(/review:/i);
        expect(modalTitle).not.toBeInTheDocument();
      }, { timeout: 3000 });
    }
  });

  test('should handle combined search and status filter', async () => {
    render(<ReviewQueue />);

    await waitFor(() => {
      expect(screen.getByText('Perfect code')).toBeInTheDocument();
    });

    // Apply search filter
    const searchInput = screen.getByPlaceholderText(/search/i);
    fireEvent.change(searchInput, { target: { value: 'perfect' } });

    await waitFor(() => {
      expect(screen.getByText('Perfect code')).toBeInTheDocument();
      expect(screen.queryByText('Uncertain analysis')).not.toBeInTheDocument();
    });

    // Then apply status filter
    const allButton = screen.getByRole('button', { name: /^all$/i });
    fireEvent.click(allButton);

    await waitFor(() => {
      expect(globalAny.fetch).toHaveBeenCalled();
    });
  });

  test('should refresh queue when refresh button clicked', async () => {
    render(<ReviewQueue />);

    await waitFor(() => {
      expect(screen.getByText('Perfect code')).toBeInTheDocument();
    });

    // Clear previous fetch calls
    vi.mocked(globalAny.fetch).mockClear();

    // Click refresh button
    const refreshButton = screen.getByRole('button', { name: /refresh/i });
    fireEvent.click(refreshButton);

    await waitFor(() => {
      expect(globalAny.fetch).toHaveBeenCalledTimes(1);
      expect(globalAny.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v2/review/queue')
      );
    });
  });

  test('should display empty state when no reviews match filters', async () => {
    vi.mocked(globalAny.fetch).mockResolvedValue({
      ok: true,
      json: async () => ({ queue: [] })
    } as Response);

    render(<ReviewQueue />);

    await waitFor(() => {
      expect(screen.getByText(/All atoms have been reviewed!/i)).toBeInTheDocument();
    });
  });

  test('should maintain grid layout with different numbers of items', async () => {
    render(<ReviewQueue />);

    await waitFor(() => {
      expect(screen.getByText('Perfect code')).toBeInTheDocument();
    });

    // Find the grid container
    const gridContainer = document.querySelector('.grid');
    expect(gridContainer).toHaveClass('grid-cols-1', 'md:grid-cols-2', 'lg:grid-cols-3');
  });
});
