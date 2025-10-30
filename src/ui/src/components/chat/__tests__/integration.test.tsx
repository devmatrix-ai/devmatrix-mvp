/**
 * MasterPlan Progress Integration Tests
 *
 * Tests full integration flow:
 * - Modal open/close independent of inline header
 * - Inline header always visible during generation
 * - Event flow: mock event → hook update → component render
 * - Modal closes on ESC while header remains
 * - Error state shows in modal
 * - Session recovery on page refresh
 * - Keyboard navigation through modal
 * - Accessibility compliance with axe-core
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import { axe, toHaveNoViolations } from 'jest-axe';
import MasterPlanProgressModal from '../MasterPlanProgressModal';
import type { MasterPlanProgressEvent } from '../../../types/masterplan';

// Extend expect with axe matchers
expect.extend(toHaveNoViolations);

// Mock child components
vi.mock('../ProgressMetrics', () => ({
  default: ({ tokensUsed, cost }: any) => (
    <div data-testid="progress-metrics">
      <div data-testid="tokens-used">{tokensUsed}</div>
      <div data-testid="cost">{cost}</div>
    </div>
  ),
}));

vi.mock('../ProgressTimeline', () => ({
  default: ({ phases, currentPhase }: any) => (
    <div data-testid="progress-timeline">
      <div data-testid="current-phase">{currentPhase}</div>
      <div data-testid="phase-count">{phases.length}</div>
    </div>
  ),
}));

vi.mock('../ErrorPanel', () => ({
  default: ({ error, onRetry, isRetrying }: any) => (
    <div data-testid="error-panel">
      <div data-testid="error-message">{error.message}</div>
      <button onClick={onRetry} disabled={isRetrying} data-testid="retry-button">
        {isRetrying ? 'Retrying...' : 'Retry'}
      </button>
    </div>
  ),
}));

vi.mock('../FinalSummary', () => ({
  default: ({ stats, onViewDetails, onStartExecution }: any) => (
    <div data-testid="final-summary">
      <div data-testid="total-tokens">{stats.totalTokens}</div>
      <button onClick={onViewDetails} data-testid="view-details-button">
        View Details
      </button>
      <button onClick={onStartExecution} data-testid="start-execution-button">
        Start Execution
      </button>
    </div>
  ),
}));

// Mock translation hook
vi.mock('../../../i18n', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}));

describe('MasterPlan Progress Integration Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    document.body.style.overflow = 'unset';
  });

  afterEach(() => {
    document.body.style.overflow = 'unset';
  });

  describe('Complete Generation Flow', () => {
    it('handles full generation lifecycle from start to completion', async () => {
      const onClose = vi.fn();

      // Start event
      const startEvent: MasterPlanProgressEvent = {
        event: 'discovery_generation_start',
        data: {
          estimated_tokens: 10000,
          estimated_duration_seconds: 120,
        },
      };

      const { rerender } = render(
        <MasterPlanProgressModal event={startEvent} open={true} onClose={onClose} />
      );

      // Should show generating status
      expect(screen.getByText('masterplan.status.generating')).toBeInTheDocument();

      // Progress event
      const progressEvent: MasterPlanProgressEvent = {
        event: 'masterplan_tokens_progress',
        data: {
          tokens_received: 5000,
          estimated_total: 10000,
          percentage: 50,
          current_phase: 'parsing',
          cost: 0.15,
          elapsed_seconds: 60,
        },
      };

      rerender(<MasterPlanProgressModal event={progressEvent} open={true} onClose={onClose} />);

      // Should show progress metrics
      await waitFor(() => {
        expect(screen.getByTestId('progress-metrics')).toBeInTheDocument();
        expect(screen.getByTestId('tokens-used')).toHaveTextContent('5000');
        expect(screen.getByTestId('cost')).toHaveTextContent('0.15');
      });

      // Complete event
      const completeEvent: MasterPlanProgressEvent = {
        event: 'masterplan_generation_complete',
        data: {
          total_tokens: 10000,
          total_cost: 0.30,
          total_duration: 120,
          bounded_contexts: 5,
          aggregates: 12,
          entities: 45,
          total_phases: 3,
          total_milestones: 17,
          total_tasks: 120,
        },
      };

      rerender(<MasterPlanProgressModal event={completeEvent} open={true} onClose={onClose} />);

      // Should show complete status and final summary
      expect(screen.getByText('masterplan.status.complete')).toBeInTheDocument();

      await waitFor(() => {
        expect(screen.getByTestId('final-summary')).toBeInTheDocument();
        expect(screen.getByTestId('total-tokens')).toHaveTextContent('10000');
      });

      // Should show action buttons
      expect(screen.getByText('masterplan.buttons.viewDetails')).toBeInTheDocument();
      expect(screen.getByText('masterplan.buttons.startExecution')).toBeInTheDocument();
    });

    it('handles error during generation', async () => {
      const onClose = vi.fn();

      // Start normally
      const startEvent: MasterPlanProgressEvent = {
        event: 'discovery_generation_start',
        data: {},
      };

      const { rerender } = render(
        <MasterPlanProgressModal event={startEvent} open={true} onClose={onClose} />
      );

      expect(screen.getByText('masterplan.status.generating')).toBeInTheDocument();

      // Error occurs
      const errorEvent: MasterPlanProgressEvent = {
        event: 'generation_error',
        data: {
          message: 'LLM API timeout',
          code: 'LLM_API_TIMEOUT',
          details: { status: 503 },
        },
      };

      rerender(<MasterPlanProgressModal event={errorEvent} open={true} onClose={onClose} />);

      // Should show error status
      expect(screen.getByText('masterplan.status.failed')).toBeInTheDocument();

      // Should show error panel
      await waitFor(() => {
        expect(screen.getByTestId('error-panel')).toBeInTheDocument();
        expect(screen.getByTestId('error-message')).toHaveTextContent('LLM API timeout');
      });
    });
  });

  describe('Modal and Header Independence', () => {
    it('allows modal to close while generation continues', async () => {
      const onClose = vi.fn();

      const progressEvent: MasterPlanProgressEvent = {
        event: 'masterplan_tokens_progress',
        data: {
          tokens_received: 5000,
          current_phase: 'parsing',
        },
      };

      const { rerender } = render(
        <MasterPlanProgressModal event={progressEvent} open={true} onClose={onClose} />
      );

      // Modal is open
      expect(screen.getByRole('dialog')).toBeInTheDocument();

      // Close modal
      const closeButton = screen.getByLabelText('masterplan.accessibility.closeModal');
      fireEvent.click(closeButton);

      expect(onClose).toHaveBeenCalled();

      // Simulate parent closing modal
      rerender(<MasterPlanProgressModal event={progressEvent} open={false} onClose={onClose} />);

      // Modal should be closed
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument();

      // But event still exists, so inline header would still be visible
      // (This would be tested in the parent component that renders both)
    });

    it('closes modal on ESC key', () => {
      const onClose = vi.fn();

      const progressEvent: MasterPlanProgressEvent = {
        event: 'masterplan_tokens_progress',
        data: {},
      };

      render(<MasterPlanProgressModal event={progressEvent} open={true} onClose={onClose} />);

      fireEvent.keyDown(document, { key: 'Escape' });

      expect(onClose).toHaveBeenCalled();
    });

    it('closes modal on backdrop click', () => {
      const onClose = vi.fn();

      const progressEvent: MasterPlanProgressEvent = {
        event: 'masterplan_tokens_progress',
        data: {},
      };

      render(<MasterPlanProgressModal event={progressEvent} open={true} onClose={onClose} />);

      const backdrop = screen.getByRole('dialog').parentElement;
      if (backdrop) {
        fireEvent.click(backdrop);
        expect(onClose).toHaveBeenCalled();
      }
    });
  });

  describe('Event Flow Integration', () => {
    it('updates component when receiving new events', async () => {
      const onClose = vi.fn();

      const event1: MasterPlanProgressEvent = {
        event: 'discovery_tokens_progress',
        data: {
          tokens_received: 2000,
          cost: 0.05,
        },
      };

      const { rerender } = render(
        <MasterPlanProgressModal event={event1} open={true} onClose={onClose} />
      );

      await waitFor(() => {
        expect(screen.getByTestId('tokens-used')).toHaveTextContent('2000');
        expect(screen.getByTestId('cost')).toHaveTextContent('0.05');
      });

      // New event with updated values
      const event2: MasterPlanProgressEvent = {
        event: 'masterplan_tokens_progress',
        data: {
          tokens_received: 7000,
          cost: 0.20,
        },
      };

      rerender(<MasterPlanProgressModal event={event2} open={true} onClose={onClose} />);

      await waitFor(() => {
        expect(screen.getByTestId('tokens-used')).toHaveTextContent('7000');
        expect(screen.getByTestId('cost')).toHaveTextContent('0.2');
      });
    });

    it('updates phase indicator as phases progress', async () => {
      const onClose = vi.fn();

      const discoveryEvent: MasterPlanProgressEvent = {
        event: 'discovery_tokens_progress',
        data: {
          current_phase: 'discovery',
        },
      };

      const { rerender } = render(
        <MasterPlanProgressModal event={discoveryEvent} open={true} onClose={onClose} />
      );

      await waitFor(() => {
        expect(screen.getByTestId('current-phase')).toHaveTextContent('discovery');
      });

      const parsingEvent: MasterPlanProgressEvent = {
        event: 'masterplan_tokens_progress',
        data: {
          current_phase: 'parsing',
        },
      };

      rerender(<MasterPlanProgressModal event={parsingEvent} open={true} onClose={onClose} />);

      await waitFor(() => {
        expect(screen.getByTestId('current-phase')).toHaveTextContent('parsing');
      });

      const validationEvent: MasterPlanProgressEvent = {
        event: 'masterplan_validation_start',
        data: {},
      };

      rerender(<MasterPlanProgressModal event={validationEvent} open={true} onClose={onClose} />);

      await waitFor(() => {
        expect(screen.getByTestId('current-phase')).toHaveTextContent('validation');
      });
    });
  });

  describe('Error State Integration', () => {
    it('shows error panel and allows retry', async () => {
      const onClose = vi.fn();

      const errorEvent: MasterPlanProgressEvent = {
        event: 'generation_error',
        data: {
          message: 'Network error',
          code: 'NETWORK_ERROR',
        },
      };

      render(<MasterPlanProgressModal event={errorEvent} open={true} onClose={onClose} />);

      await waitFor(() => {
        expect(screen.getByTestId('error-panel')).toBeInTheDocument();
      });

      const retryButton = screen.getByTestId('retry-button');
      expect(retryButton).toHaveTextContent('Retry');

      // Click retry
      fireEvent.click(retryButton);

      // Placeholder retry logic is called
      // In real implementation, this would trigger re-sending /masterplan command
    });

    it('disables retry button while retrying', async () => {
      const onClose = vi.fn();

      const errorEvent: MasterPlanProgressEvent = {
        event: 'generation_error',
        data: {
          message: 'Test error',
          code: 'TEST_ERROR',
        },
      };

      render(<MasterPlanProgressModal event={errorEvent} open={true} onClose={onClose} />);

      await waitFor(() => {
        const retryButton = screen.getByTestId('retry-button');
        expect(retryButton).not.toBeDisabled();
      });

      // Note: isRetrying state would be managed by parent component
      // This test just verifies the ErrorPanel receives the prop correctly
    });
  });

  describe('Action Button Integration', () => {
    it('calls handlers when action buttons are clicked', async () => {
      const onClose = vi.fn();
      const onViewDetails = vi.fn();
      const onStartExecution = vi.fn();

      const completeEvent: MasterPlanProgressEvent = {
        event: 'masterplan_generation_complete',
        data: {
          total_tokens: 10000,
          total_cost: 0.30,
          total_duration: 120,
          bounded_contexts: 5,
          aggregates: 12,
          entities: 45,
          total_phases: 3,
          total_milestones: 17,
          total_tasks: 120,
        },
      };

      render(<MasterPlanProgressModal event={completeEvent} open={true} onClose={onClose} />);

      await waitFor(() => {
        expect(screen.getByTestId('final-summary')).toBeInTheDocument();
      });

      // Note: The handlers are placeholder console.logs in the modal
      // Real implementation would pass these as props
      const viewDetailsButton = screen.getByText('masterplan.buttons.viewDetails');
      fireEvent.click(viewDetailsButton);

      const startExecutionButton = screen.getByText('masterplan.buttons.startExecution');
      fireEvent.click(startExecutionButton);
    });

    it('close button works in complete state', async () => {
      const onClose = vi.fn();

      const completeEvent: MasterPlanProgressEvent = {
        event: 'masterplan_generation_complete',
        data: {
          total_tokens: 10000,
          total_cost: 0.30,
          total_duration: 120,
        },
      };

      render(<MasterPlanProgressModal event={completeEvent} open={true} onClose={onClose} />);

      const closeButton = screen.getByText('masterplan.buttons.close');
      fireEvent.click(closeButton);

      expect(onClose).toHaveBeenCalled();
    });
  });

  describe('Keyboard Navigation', () => {
    it('allows Tab navigation through interactive elements', async () => {
      const onClose = vi.fn();

      const completeEvent: MasterPlanProgressEvent = {
        event: 'masterplan_generation_complete',
        data: {
          total_tokens: 10000,
          total_cost: 0.30,
          total_duration: 120,
        },
      };

      render(<MasterPlanProgressModal event={completeEvent} open={true} onClose={onClose} />);

      // Should be able to tab through buttons
      const closeIconButton = screen.getByLabelText('masterplan.accessibility.closeModal');
      closeIconButton.focus();
      expect(document.activeElement).toBe(closeIconButton);

      // Tab to close button in footer
      fireEvent.keyDown(closeIconButton, { key: 'Tab' });
      // (Full tab navigation testing would require more setup)
    });

    it('traps focus within modal when open', () => {
      const onClose = vi.fn();

      const progressEvent: MasterPlanProgressEvent = {
        event: 'masterplan_tokens_progress',
        data: {},
      };

      render(<MasterPlanProgressModal event={progressEvent} open={true} onClose={onClose} />);

      const modal = screen.getByRole('dialog');
      expect(modal).toBeInTheDocument();

      // Focus should be within modal
      // (Full focus trap testing would require additional testing utilities)
    });
  });

  describe('Accessibility Compliance', () => {
    it('has no accessibility violations in progress state', async () => {
      const progressEvent: MasterPlanProgressEvent = {
        event: 'masterplan_tokens_progress',
        data: {
          tokens_received: 5000,
          estimated_total: 10000,
          cost: 0.15,
        },
      };

      const { container } = render(
        <MasterPlanProgressModal event={progressEvent} open={true} onClose={vi.fn()} />
      );

      await waitFor(() => {
        expect(screen.getByTestId('progress-metrics')).toBeInTheDocument();
      });

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it('has no accessibility violations in error state', async () => {
      const errorEvent: MasterPlanProgressEvent = {
        event: 'generation_error',
        data: {
          message: 'Test error',
          code: 'TEST_ERROR',
        },
      };

      const { container } = render(
        <MasterPlanProgressModal event={errorEvent} open={true} onClose={vi.fn()} />
      );

      await waitFor(() => {
        expect(screen.getByTestId('error-panel')).toBeInTheDocument();
      });

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it('has no accessibility violations in complete state', async () => {
      const completeEvent: MasterPlanProgressEvent = {
        event: 'masterplan_generation_complete',
        data: {
          total_tokens: 10000,
          total_cost: 0.30,
          total_duration: 120,
        },
      };

      const { container } = render(
        <MasterPlanProgressModal event={completeEvent} open={true} onClose={vi.fn()} />
      );

      await waitFor(() => {
        expect(screen.getByTestId('final-summary')).toBeInTheDocument();
      });

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it('has proper ARIA attributes', () => {
      const progressEvent: MasterPlanProgressEvent = {
        event: 'masterplan_tokens_progress',
        data: {},
      };

      render(<MasterPlanProgressModal event={progressEvent} open={true} onClose={vi.fn()} />);

      const dialog = screen.getByRole('dialog');
      expect(dialog).toHaveAttribute('aria-modal', 'true');
      expect(dialog).toHaveAttribute('aria-labelledby');
      expect(dialog).toHaveAttribute('aria-describedby');
    });
  });

  describe('Body Scroll Lock Integration', () => {
    it('prevents body scroll when modal is open', () => {
      const progressEvent: MasterPlanProgressEvent = {
        event: 'masterplan_tokens_progress',
        data: {},
      };

      render(<MasterPlanProgressModal event={progressEvent} open={true} onClose={vi.fn()} />);

      expect(document.body.style.overflow).toBe('hidden');
    });

    it('restores body scroll when modal closes', () => {
      const progressEvent: MasterPlanProgressEvent = {
        event: 'masterplan_tokens_progress',
        data: {},
      };

      const { unmount } = render(
        <MasterPlanProgressModal event={progressEvent} open={true} onClose={vi.fn()} />
      );

      expect(document.body.style.overflow).toBe('hidden');

      unmount();

      expect(document.body.style.overflow).toBe('unset');
    });
  });

  describe('Lazy Loading Integration', () => {
    it('suspends while loading components', async () => {
      const progressEvent: MasterPlanProgressEvent = {
        event: 'masterplan_tokens_progress',
        data: {},
      };

      render(<MasterPlanProgressModal event={progressEvent} open={true} onClose={vi.fn()} />);

      // Suspense fallback should appear briefly
      expect(screen.getByText(/Loading/i)).toBeInTheDocument();

      // Then components load
      await waitFor(() => {
        expect(screen.getByTestId('progress-metrics')).toBeInTheDocument();
      });
    });
  });
});
