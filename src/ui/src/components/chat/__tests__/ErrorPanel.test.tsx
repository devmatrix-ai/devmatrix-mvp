/**
 * ErrorPanel Component Tests
 *
 * Tests for:
 * - Error message display
 * - Error code display
 * - Expandable details section
 * - Expandable stack trace section
 * - Retry button functionality
 * - Loading state during retry
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import ErrorPanel from '../ErrorPanel';
import type { ErrorPanelProps } from '../../../types/masterplan';

// Mock translation hook
vi.mock('../../../i18n', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}));

const mockError = {
  message: 'Generation failed due to LLM API timeout',
  code: 'LLM_API_TIMEOUT',
  details: {
    status: 503,
    service: 'Claude API',
    retry_after: 60,
  },
  stackTrace: 'Error: LLM_API_TIMEOUT\n  at generateMasterPlan (/app/src/masterplan.py:45)\n  at processRequest (/app/src/handler.py:120)',
};

describe('ErrorPanel', () => {
  const mockOnRetry = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Error Display', () => {
    it('renders error title', () => {
      render(
        <ErrorPanel
          error={mockError}
          onRetry={mockOnRetry}
          isRetrying={false}
        />
      );

      expect(screen.getByText('masterplan.errors.title')).toBeInTheDocument();
    });

    it('displays error message', () => {
      render(
        <ErrorPanel
          error={mockError}
          onRetry={mockOnRetry}
          isRetrying={false}
        />
      );

      expect(screen.getByText(mockError.message)).toBeInTheDocument();
    });

    it('displays error code', () => {
      render(
        <ErrorPanel
          error={mockError}
          onRetry={mockOnRetry}
          isRetrying={false}
        />
      );

      expect(screen.getByText(/masterplan.errors.code/)).toBeInTheDocument();
      expect(screen.getByText(mockError.code)).toBeInTheDocument();
    });

    it('renders alert icon', () => {
      const { container } = render(
        <ErrorPanel
          error={mockError}
          onRetry={mockOnRetry}
          isRetrying={false}
        />
      );

      // FiAlertTriangle icon should be present
      const icon = container.querySelector('.text-red-500');
      expect(icon).toBeInTheDocument();
    });
  });

  describe('Error Details Section', () => {
    it('renders details expand button when details exist', () => {
      render(
        <ErrorPanel
          error={mockError}
          onRetry={mockOnRetry}
          isRetrying={false}
        />
      );

      expect(screen.getByText('masterplan.errors.details')).toBeInTheDocument();
    });

    it('does not render details section when no details', () => {
      const errorWithoutDetails = {
        ...mockError,
        details: undefined,
      };

      render(
        <ErrorPanel
          error={errorWithoutDetails}
          onRetry={mockOnRetry}
          isRetrying={false}
        />
      );

      expect(screen.queryByText('masterplan.errors.details')).not.toBeInTheDocument();
    });

    it('does not render details section when details is empty object', () => {
      const errorWithEmptyDetails = {
        ...mockError,
        details: {},
      };

      render(
        <ErrorPanel
          error={errorWithEmptyDetails}
          onRetry={mockOnRetry}
          isRetrying={false}
        />
      );

      expect(screen.queryByText('masterplan.errors.details')).not.toBeInTheDocument();
    });

    it('toggles details visibility when button is clicked', () => {
      render(
        <ErrorPanel
          error={mockError}
          onRetry={mockOnRetry}
          isRetrying={false}
        />
      );

      const detailsButton = screen.getByText('masterplan.errors.details').closest('button');

      // Initially collapsed
      expect(screen.queryByText(/"status":/)).not.toBeInTheDocument();

      // Click to expand
      if (detailsButton) {
        fireEvent.click(detailsButton);
      }
      expect(screen.getByText(/"status":/)).toBeInTheDocument();

      // Click to collapse
      if (detailsButton) {
        fireEvent.click(detailsButton);
      }
      expect(screen.queryByText(/"status":/)).not.toBeInTheDocument();
    });

    it('displays details as formatted JSON', () => {
      render(
        <ErrorPanel
          error={mockError}
          onRetry={mockOnRetry}
          isRetrying={false}
        />
      );

      const detailsButton = screen.getByText('masterplan.errors.details').closest('button');
      if (detailsButton) {
        fireEvent.click(detailsButton);
      }

      // Should display JSON with proper formatting
      expect(screen.getByText(/"status":/)).toBeInTheDocument();
      expect(screen.getByText(/"service":/)).toBeInTheDocument();
      expect(screen.getByText(/"retry_after":/)).toBeInTheDocument();
    });

    it('has proper ARIA attributes for details section', () => {
      render(
        <ErrorPanel
          error={mockError}
          onRetry={mockOnRetry}
          isRetrying={false}
        />
      );

      const detailsButton = screen.getByText('masterplan.errors.details').closest('button');

      expect(detailsButton).toHaveAttribute('aria-expanded', 'false');
      expect(detailsButton).toHaveAttribute('aria-controls', 'error-details');
    });
  });

  describe('Stack Trace Section', () => {
    it('renders stack trace expand button when stack trace exists', () => {
      render(
        <ErrorPanel
          error={mockError}
          onRetry={mockOnRetry}
          isRetrying={false}
        />
      );

      expect(screen.getByText('masterplan.errors.stackTrace')).toBeInTheDocument();
    });

    it('does not render stack trace section when no stack trace', () => {
      const errorWithoutStack = {
        ...mockError,
        stackTrace: undefined,
      };

      render(
        <ErrorPanel
          error={errorWithoutStack}
          onRetry={mockOnRetry}
          isRetrying={false}
        />
      );

      expect(screen.queryByText('masterplan.errors.stackTrace')).not.toBeInTheDocument();
    });

    it('toggles stack trace visibility when button is clicked', () => {
      render(
        <ErrorPanel
          error={mockError}
          onRetry={mockOnRetry}
          isRetrying={false}
        />
      );

      const stackButton = screen.getByText('masterplan.errors.stackTrace').closest('button');

      // Initially collapsed
      expect(screen.queryByText(/at generateMasterPlan/)).not.toBeInTheDocument();

      // Click to expand
      if (stackButton) {
        fireEvent.click(stackButton);
      }
      expect(screen.getByText(/at generateMasterPlan/)).toBeInTheDocument();

      // Click to collapse
      if (stackButton) {
        fireEvent.click(stackButton);
      }
      expect(screen.queryByText(/at generateMasterPlan/)).not.toBeInTheDocument();
    });

    it('displays stack trace with proper formatting', () => {
      render(
        <ErrorPanel
          error={mockError}
          onRetry={mockOnRetry}
          isRetrying={false}
        />
      );

      const stackButton = screen.getByText('masterplan.errors.stackTrace').closest('button');
      if (stackButton) {
        fireEvent.click(stackButton);
      }

      expect(screen.getByText(/at generateMasterPlan/)).toBeInTheDocument();
      expect(screen.getByText(/at processRequest/)).toBeInTheDocument();
    });

    it('has proper ARIA attributes for stack trace section', () => {
      render(
        <ErrorPanel
          error={mockError}
          onRetry={mockOnRetry}
          isRetrying={false}
        />
      );

      const stackButton = screen.getByText('masterplan.errors.stackTrace').closest('button');

      expect(stackButton).toHaveAttribute('aria-expanded', 'false');
      expect(stackButton).toHaveAttribute('aria-controls', 'error-stack');
    });
  });

  describe('Retry Button', () => {
    it('renders retry button', () => {
      render(
        <ErrorPanel
          error={mockError}
          onRetry={mockOnRetry}
          isRetrying={false}
        />
      );

      const retryButton = screen.getByText('masterplan.buttons.retry');
      expect(retryButton).toBeInTheDocument();
    });

    it('calls onRetry when retry button is clicked', () => {
      render(
        <ErrorPanel
          error={mockError}
          onRetry={mockOnRetry}
          isRetrying={false}
        />
      );

      const retryButton = screen.getByText('masterplan.buttons.retry');
      fireEvent.click(retryButton);

      expect(mockOnRetry).toHaveBeenCalledTimes(1);
    });

    it('disables retry button when retrying', () => {
      render(
        <ErrorPanel
          error={mockError}
          onRetry={mockOnRetry}
          isRetrying={true}
        />
      );

      const retryButton = screen.getByText('masterplan.errors.retryingMessage');
      expect(retryButton.closest('button')).toBeDisabled();
    });

    it('changes button text when retrying', () => {
      const { rerender } = render(
        <ErrorPanel
          error={mockError}
          onRetry={mockOnRetry}
          isRetrying={false}
        />
      );

      expect(screen.getByText('masterplan.buttons.retry')).toBeInTheDocument();

      rerender(
        <ErrorPanel
          error={mockError}
          onRetry={mockOnRetry}
          isRetrying={true}
        />
      );

      expect(screen.queryByText('masterplan.buttons.retry')).not.toBeInTheDocument();
      expect(screen.getAllByText('masterplan.errors.retryingMessage')).toHaveLength(2);
    });

    it('shows spinning icon when retrying', () => {
      const { container } = render(
        <ErrorPanel
          error={mockError}
          onRetry={mockOnRetry}
          isRetrying={true}
        />
      );

      // FiRefreshCw icon should have animate-spin class
      const icon = container.querySelector('.animate-spin');
      expect(icon).toBeInTheDocument();
    });

    it('has proper ARIA label for retry button', () => {
      render(
        <ErrorPanel
          error={mockError}
          onRetry={mockOnRetry}
          isRetrying={false}
        />
      );

      const retryButton = screen.getByText('masterplan.buttons.retry').closest('button');
      expect(retryButton).toHaveAttribute('aria-label', 'masterplan.accessibility.retryButton');
    });
  });

  describe('Retrying State', () => {
    it('displays retrying message when isRetrying is true', () => {
      render(
        <ErrorPanel
          error={mockError}
          onRetry={mockOnRetry}
          isRetrying={true}
        />
      );

      const messages = screen.getAllByText('masterplan.errors.retryingMessage');
      expect(messages.length).toBeGreaterThan(0);
    });

    it('does not display retrying message when isRetrying is false', () => {
      render(
        <ErrorPanel
          error={mockError}
          onRetry={mockOnRetry}
          isRetrying={false}
        />
      );

      const messages = screen.queryAllByText('masterplan.errors.retryingMessage');
      expect(messages).toHaveLength(0);
    });

    it('has proper ARIA live region for retrying message', () => {
      render(
        <ErrorPanel
          error={mockError}
          onRetry={mockOnRetry}
          isRetrying={true}
        />
      );

      const liveRegion = screen.getByRole('status');
      expect(liveRegion).toHaveAttribute('aria-live', 'polite');
    });
  });

  describe('Styling', () => {
    it('applies error theme colors', () => {
      const { container } = render(
        <ErrorPanel
          error={mockError}
          onRetry={mockOnRetry}
          isRetrying={false}
        />
      );

      // GlassCard should have red border and red background tint
      const card = container.querySelector('.border-red-500\\/50');
      expect(card).toBeInTheDocument();

      const bgTint = container.querySelector('.bg-red-900\\/10');
      expect(bgTint).toBeInTheDocument();
    });
  });

  describe('Edge Cases', () => {
    it('handles error with minimal information', () => {
      const minimalError = {
        message: 'Unknown error',
        code: 'UNKNOWN',
      };

      render(
        <ErrorPanel
          error={minimalError}
          onRetry={mockOnRetry}
          isRetrying={false}
        />
      );

      expect(screen.getByText('Unknown error')).toBeInTheDocument();
      expect(screen.getByText('UNKNOWN')).toBeInTheDocument();
      expect(screen.queryByText('masterplan.errors.details')).not.toBeInTheDocument();
      expect(screen.queryByText('masterplan.errors.stackTrace')).not.toBeInTheDocument();
    });

    it('handles very long error messages', () => {
      const longError = {
        message: 'A'.repeat(500),
        code: 'LONG_ERROR',
      };

      render(
        <ErrorPanel
          error={longError}
          onRetry={mockOnRetry}
          isRetrying={false}
        />
      );

      expect(screen.getByText('A'.repeat(500))).toBeInTheDocument();
    });

    it('handles complex nested details object', () => {
      const complexError = {
        ...mockError,
        details: {
          level1: {
            level2: {
              level3: {
                value: 'deep value',
              },
            },
          },
          array: [1, 2, 3],
        },
      };

      render(
        <ErrorPanel
          error={complexError}
          onRetry={mockOnRetry}
          isRetrying={false}
        />
      );

      const detailsButton = screen.getByText('masterplan.errors.details').closest('button');
      if (detailsButton) {
        fireEvent.click(detailsButton);
      }

      // Should render nested JSON
      expect(screen.getByText(/"level1":/)).toBeInTheDocument();
    });
  });
});
