/**
 * ErrorState Component Tests
 *
 * Strategic gap-filling tests:
 * - Error message display
 * - Retry functionality
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import ErrorState from '../ErrorState';

describe('ErrorState', () => {
  it('renders error message', () => {
    render(<ErrorState error="Network connection failed" />);

    expect(screen.getByText(/Network connection failed/i)).toBeInTheDocument();
  });

  it('renders retry button and calls onRetry', () => {
    const handleRetry = vi.fn();
    render(<ErrorState error="Failed to load" onRetry={handleRetry} />);

    const retryButton = screen.getByText(/retry/i);
    fireEvent.click(retryButton);

    expect(handleRetry).toHaveBeenCalledTimes(1);
  });
});
