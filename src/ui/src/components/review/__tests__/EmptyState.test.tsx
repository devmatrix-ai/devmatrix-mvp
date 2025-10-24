/**
 * EmptyState Component Tests
 *
 * Strategic gap-filling tests:
 * - Rendering with message
 * - Optional icon display
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import EmptyState from '../EmptyState';

describe('EmptyState', () => {
  it('renders with message and icon', () => {
    render(<EmptyState icon="📭" message="No reviews found" />);

    expect(screen.getByText('📭')).toBeInTheDocument();
    expect(screen.getByText('No reviews found')).toBeInTheDocument();
  });

  it('renders with action button and calls onClick', () => {
    const handleAction = vi.fn();
    render(
      <EmptyState
        icon="📭"
        message="No reviews found"
        action={{
          label: 'Create New',
          onClick: handleAction,
        }}
      />
    );

    const button = screen.getByText('Create New');
    fireEvent.click(button);

    expect(handleAction).toHaveBeenCalledTimes(1);
  });
});
