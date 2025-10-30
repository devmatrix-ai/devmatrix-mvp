/**
 * MasterPlanProgressModal Component Tests
 *
 * Tests for critical modal behaviors:
 * - Modal open/close functionality
 * - Escape key handling
 * - Backdrop click handling
 * - Body scroll lock
 * - Component rendering based on event state
 * - Lazy loading of child components
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import MasterPlanProgressModal from '../MasterPlanProgressModal';
import type { MasterPlanProgressEvent } from '../../../types/masterplan';

// Mock child components to test lazy loading
vi.mock('../ProgressMetrics', () => ({
  default: () => <div data-testid="progress-metrics">ProgressMetrics</div>,
}));

vi.mock('../ProgressTimeline', () => ({
  default: () => <div data-testid="progress-timeline">ProgressTimeline</div>,
}));

vi.mock('../ErrorPanel', () => ({
  default: () => <div data-testid="error-panel">ErrorPanel</div>,
}));

vi.mock('../FinalSummary', () => ({
  default: () => <div data-testid="final-summary">FinalSummary</div>,
}));

// Mock translation hook
vi.mock('../../../i18n', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}));

const mockInProgressEvent: MasterPlanProgressEvent = {
  event: 'masterplan_tokens_progress',
  data: {
    tokens_received: 5000,
    estimated_total: 10000,
    percentage: 50,
    current_phase: 'parsing',
    cost: 0.15,
    elapsed_seconds: 60,
    estimated_duration: 120,
  },
};

const mockCompleteEvent: MasterPlanProgressEvent = {
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
    architecture_style: 'DDD',
    tech_stack: ['React', 'FastAPI', 'PostgreSQL'],
  },
};

const mockErrorEvent: MasterPlanProgressEvent = {
  event: 'generation_error',
  data: {
    message: 'LLM API error',
    code: 'LLM_API_ERROR',
    details: { status: 503 },
  },
};

describe('MasterPlanProgressModal', () => {
  const mockOnClose = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    // Reset body overflow style
    document.body.style.overflow = 'unset';
  });

  afterEach(() => {
    document.body.style.overflow = 'unset';
  });

  describe('Modal Visibility', () => {
    it('renders modal when open is true and event is provided', () => {
      render(
        <MasterPlanProgressModal
          event={mockInProgressEvent}
          open={true}
          onClose={mockOnClose}
        />
      );

      expect(screen.getByRole('dialog')).toBeInTheDocument();
      expect(screen.getByText('masterplan.title')).toBeInTheDocument();
    });

    it('does not render modal when open is false', () => {
      render(
        <MasterPlanProgressModal
          event={mockInProgressEvent}
          open={false}
          onClose={mockOnClose}
        />
      );

      expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    });

    it('does not render modal when event is null', () => {
      render(
        <MasterPlanProgressModal
          event={null}
          open={true}
          onClose={mockOnClose}
        />
      );

      expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    });
  });

  describe('Modal Interactions', () => {
    it('calls onClose when close button is clicked', () => {
      render(
        <MasterPlanProgressModal
          event={mockInProgressEvent}
          open={true}
          onClose={mockOnClose}
        />
      );

      const closeButton = screen.getByLabelText('masterplan.accessibility.closeModal');
      fireEvent.click(closeButton);

      expect(mockOnClose).toHaveBeenCalledTimes(1);
    });

    it('calls onClose when Escape key is pressed', () => {
      render(
        <MasterPlanProgressModal
          event={mockInProgressEvent}
          open={true}
          onClose={mockOnClose}
        />
      );

      fireEvent.keyDown(document, { key: 'Escape' });

      expect(mockOnClose).toHaveBeenCalledTimes(1);
    });

    it('calls onClose when backdrop is clicked', () => {
      render(
        <MasterPlanProgressModal
          event={mockInProgressEvent}
          open={true}
          onClose={mockOnClose}
        />
      );

      const backdrop = screen.getByRole('dialog').parentElement;
      if (backdrop) {
        fireEvent.click(backdrop);
        expect(mockOnClose).toHaveBeenCalledTimes(1);
      }
    });

    it('does not call onClose when modal content is clicked', () => {
      render(
        <MasterPlanProgressModal
          event={mockInProgressEvent}
          open={true}
          onClose={mockOnClose}
        />
      );

      const modalContent = screen.getByRole('dialog');
      fireEvent.click(modalContent);

      expect(mockOnClose).not.toHaveBeenCalled();
    });
  });

  describe('Body Scroll Lock', () => {
    it('locks body scroll when modal opens', () => {
      const { rerender } = render(
        <MasterPlanProgressModal
          event={mockInProgressEvent}
          open={false}
          onClose={mockOnClose}
        />
      );

      expect(document.body.style.overflow).toBe('unset');

      rerender(
        <MasterPlanProgressModal
          event={mockInProgressEvent}
          open={true}
          onClose={mockOnClose}
        />
      );

      expect(document.body.style.overflow).toBe('hidden');
    });

    it('restores body scroll when modal closes', () => {
      const { unmount } = render(
        <MasterPlanProgressModal
          event={mockInProgressEvent}
          open={true}
          onClose={mockOnClose}
        />
      );

      expect(document.body.style.overflow).toBe('hidden');

      unmount();

      expect(document.body.style.overflow).toBe('unset');
    });
  });

  describe('Event State Rendering', () => {
    it('renders in-progress state correctly', async () => {
      render(
        <MasterPlanProgressModal
          event={mockInProgressEvent}
          open={true}
          onClose={mockOnClose}
        />
      );

      expect(screen.getByText('masterplan.status.generating')).toBeInTheDocument();

      // Wait for lazy-loaded components
      await waitFor(() => {
        expect(screen.getByTestId('progress-timeline')).toBeInTheDocument();
        expect(screen.getByTestId('progress-metrics')).toBeInTheDocument();
      });
    });

    it('renders error state correctly', async () => {
      render(
        <MasterPlanProgressModal
          event={mockErrorEvent}
          open={true}
          onClose={mockOnClose}
        />
      );

      expect(screen.getByText('masterplan.status.failed')).toBeInTheDocument();

      // Wait for lazy-loaded ErrorPanel
      await waitFor(() => {
        expect(screen.getByTestId('error-panel')).toBeInTheDocument();
      });
    });

    it('renders complete state correctly', async () => {
      render(
        <MasterPlanProgressModal
          event={mockCompleteEvent}
          open={true}
          onClose={mockOnClose}
        />
      );

      expect(screen.getByText('masterplan.status.complete')).toBeInTheDocument();

      // Wait for lazy-loaded FinalSummary
      await waitFor(() => {
        expect(screen.getByTestId('final-summary')).toBeInTheDocument();
      });
    });

    it('renders footer buttons only when complete', async () => {
      const { rerender } = render(
        <MasterPlanProgressModal
          event={mockInProgressEvent}
          open={true}
          onClose={mockOnClose}
        />
      );

      // In-progress state should not have footer buttons
      expect(screen.queryByText('masterplan.buttons.viewDetails')).not.toBeInTheDocument();

      rerender(
        <MasterPlanProgressModal
          event={mockCompleteEvent}
          open={true}
          onClose={mockOnClose}
        />
      );

      // Complete state should have footer buttons
      await waitFor(() => {
        expect(screen.getByText('masterplan.buttons.close')).toBeInTheDocument();
        expect(screen.getByText('masterplan.buttons.viewDetails')).toBeInTheDocument();
        expect(screen.getByText('masterplan.buttons.startExecution')).toBeInTheDocument();
      });
    });
  });

  describe('Accessibility', () => {
    it('has proper ARIA attributes', () => {
      render(
        <MasterPlanProgressModal
          event={mockInProgressEvent}
          open={true}
          onClose={mockOnClose}
        />
      );

      const dialog = screen.getByRole('dialog');
      expect(dialog).toHaveAttribute('aria-modal', 'true');
      expect(dialog).toHaveAttribute('aria-labelledby', 'masterplan-modal-title');
      expect(dialog).toHaveAttribute('aria-describedby', 'masterplan-modal-description');
    });

    it('has proper heading structure', () => {
      render(
        <MasterPlanProgressModal
          event={mockInProgressEvent}
          open={true}
          onClose={mockOnClose}
        />
      );

      const title = screen.getByText('masterplan.title');
      expect(title.tagName).toBe('H2');
      expect(title).toHaveAttribute('id', 'masterplan-modal-title');
    });
  });

  describe('Keyboard Navigation', () => {
    it('does not close when other keys are pressed', () => {
      render(
        <MasterPlanProgressModal
          event={mockInProgressEvent}
          open={true}
          onClose={mockOnClose}
        />
      );

      fireEvent.keyDown(document, { key: 'Enter' });
      fireEvent.keyDown(document, { key: 'Space' });
      fireEvent.keyDown(document, { key: 'Tab' });

      expect(mockOnClose).not.toHaveBeenCalled();
    });

    it('only responds to Escape when modal is open', () => {
      const { rerender } = render(
        <MasterPlanProgressModal
          event={mockInProgressEvent}
          open={false}
          onClose={mockOnClose}
        />
      );

      fireEvent.keyDown(document, { key: 'Escape' });
      expect(mockOnClose).not.toHaveBeenCalled();

      rerender(
        <MasterPlanProgressModal
          event={mockInProgressEvent}
          open={true}
          onClose={mockOnClose}
        />
      );

      fireEvent.keyDown(document, { key: 'Escape' });
      expect(mockOnClose).toHaveBeenCalledTimes(1);
    });
  });

  describe('Lazy Loading', () => {
    it('suspends while loading child components', () => {
      render(
        <MasterPlanProgressModal
          event={mockInProgressEvent}
          open={true}
          onClose={mockOnClose}
        />
      );

      // Suspense fallback should be visible initially
      expect(screen.getByText(/Loading/i)).toBeInTheDocument();
    });
  });
});
