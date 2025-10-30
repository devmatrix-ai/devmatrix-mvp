/**
 * ProgressMetrics Component Tests
 *
 * Tests for:
 * - Primary metrics rendering (progress bar, time stats)
 * - Secondary metrics collapsible section
 * - Tertiary metrics expandable section
 * - Percentage calculations
 * - Number formatting
 * - Cost formatting
 * - Entity counts display
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import ProgressMetrics from '../ProgressMetrics';
import type { ProgressMetricsProps } from '../../../types/masterplan';

// Mock translation hook
vi.mock('../../../i18n', () => ({
  useTranslation: () => ({
    t: (key: string, params?: Record<string, any>) => {
      if (params) {
        return `${key}:${JSON.stringify(params)}`;
      }
      return key;
    },
  }),
}));

const mockProps: ProgressMetricsProps = {
  tokensUsed: 8500,
  estimatedTokens: 17000,
  cost: 0.2567,
  duration: 65,
  estimatedDuration: 135,
  entities: {
    boundedContexts: 5,
    aggregates: 12,
    entities: 45,
    phases: 3,
    milestones: 17,
    tasks: 120,
  },
  isComplete: false,
};

describe('ProgressMetrics', () => {
  describe('Primary Metrics', () => {
    it('renders primary metrics section', () => {
      render(<ProgressMetrics {...mockProps} />);

      expect(screen.getByText('masterplan.metrics.primary')).toBeInTheDocument();
    });

    it('calculates and displays correct percentage', () => {
      render(<ProgressMetrics {...mockProps} />);

      // 8500 / 17000 = 0.5 = 50%
      expect(screen.getByText('50%')).toBeInTheDocument();
    });

    it('displays progress bar with correct width', () => {
      render(<ProgressMetrics {...mockProps} />);

      const progressBar = screen.getByRole('progressbar');
      expect(progressBar).toHaveAttribute('aria-valuenow', '50');
      expect(progressBar).toHaveAttribute('aria-valuemin', '0');
      expect(progressBar).toHaveAttribute('aria-valuemax', '100');

      const progressFill = progressBar.querySelector('div');
      expect(progressFill).toHaveStyle({ width: '50%' });
    });

    it('caps percentage at 100%', () => {
      const overflowProps = {
        ...mockProps,
        tokensUsed: 20000,
        estimatedTokens: 17000,
      };

      render(<ProgressMetrics {...overflowProps} />);

      expect(screen.getByText('100%')).toBeInTheDocument();
    });

    it('handles zero estimated tokens gracefully', () => {
      const zeroProps = {
        ...mockProps,
        estimatedTokens: 0,
      };

      render(<ProgressMetrics {...zeroProps} />);

      expect(screen.getByText('0%')).toBeInTheDocument();
    });

    it('displays elapsed time', () => {
      render(<ProgressMetrics {...mockProps} />);

      expect(screen.getByText('65s')).toBeInTheDocument();
    });

    it('displays time remaining when not complete', () => {
      render(<ProgressMetrics {...mockProps} />);

      // 135 - 65 = 70 seconds remaining
      expect(screen.getByText('70s')).toBeInTheDocument();
    });

    it('does not display time remaining when complete', () => {
      const completeProps = {
        ...mockProps,
        isComplete: true,
      };

      render(<ProgressMetrics {...completeProps} />);

      // Should only show elapsed time, not remaining
      const timeDisplays = screen.getAllByText(/\d+s/);
      expect(timeDisplays).toHaveLength(1);
    });
  });

  describe('Secondary Metrics', () => {
    it('renders secondary metrics section collapsed by default', () => {
      render(<ProgressMetrics {...mockProps} />);

      expect(screen.getByText('masterplan.metrics.secondary')).toBeInTheDocument();
      expect(screen.getByRole('button', { expanded: true })).toBeInTheDocument();
    });

    it('toggles secondary metrics visibility', () => {
      render(<ProgressMetrics {...mockProps} />);

      const toggleButton = screen.getByRole('button', { expanded: true });

      // Initially expanded
      expect(screen.getByText('masterplan.metrics.tokens')).toBeInTheDocument();

      // Click to collapse
      fireEvent.click(toggleButton);
      expect(screen.queryByText('masterplan.metrics.tokens')).not.toBeInTheDocument();

      // Click to expand again
      fireEvent.click(toggleButton);
      expect(screen.getByText('masterplan.metrics.tokens')).toBeInTheDocument();
    });

    it('displays token counts with formatting', () => {
      render(<ProgressMetrics {...mockProps} />);

      // Numbers should be formatted with commas
      expect(screen.getByText(/8,500/)).toBeInTheDocument();
      expect(screen.getByText(/17,000/)).toBeInTheDocument();
    });

    it('displays cost with currency formatting', () => {
      render(<ProgressMetrics {...mockProps} />);

      // Cost should be formatted as USD
      expect(screen.getByText(/\$0\.2567/)).toBeInTheDocument();
    });

    it('displays all entity counts', () => {
      render(<ProgressMetrics {...mockProps} />);

      expect(screen.getByText('5')).toBeInTheDocument(); // boundedContexts
      expect(screen.getByText('12')).toBeInTheDocument(); // aggregates
      expect(screen.getByText('45')).toBeInTheDocument(); // entities
      expect(screen.getByText('3')).toBeInTheDocument(); // phases
      expect(screen.getByText('17')).toBeInTheDocument(); // milestones
      expect(screen.getByText('120')).toBeInTheDocument(); // tasks
    });
  });

  describe('Tertiary Metrics', () => {
    it('renders tertiary metrics section collapsed by default', () => {
      render(<ProgressMetrics {...mockProps} />);

      expect(screen.getByText('masterplan.metrics.tertiary')).toBeInTheDocument();
      const tertiaryButton = screen.getAllByRole('button').find(
        (button) => button.getAttribute('aria-expanded') === 'false'
      );
      expect(tertiaryButton).toBeInTheDocument();
    });

    it('toggles tertiary metrics visibility', () => {
      render(<ProgressMetrics {...mockProps} />);

      const buttons = screen.getAllByRole('button');
      const tertiaryButton = buttons[1]; // Second button is tertiary

      // Initially collapsed
      expect(screen.queryByText('masterplan.metrics.breakdown')).not.toBeInTheDocument();

      // Click to expand
      fireEvent.click(tertiaryButton);
      expect(screen.getByText('masterplan.metrics.breakdown')).toBeInTheDocument();

      // Click to collapse
      fireEvent.click(tertiaryButton);
      expect(screen.queryByText('masterplan.metrics.breakdown')).not.toBeInTheDocument();
    });

    it('displays detailed breakdown when expanded', () => {
      render(<ProgressMetrics {...mockProps} />);

      const buttons = screen.getAllByRole('button');
      const tertiaryButton = buttons[1];

      fireEvent.click(tertiaryButton);

      expect(screen.getByText('masterplan.metrics.breakdown')).toBeInTheDocument();
      expect(screen.getByText(/Tokens:/)).toBeInTheDocument();
      expect(screen.getByText(/Cost:/)).toBeInTheDocument();
      expect(screen.getByText(/Duration:/)).toBeInTheDocument();
      expect(screen.getByText(/Percentage:/)).toBeInTheDocument();
    });

    it('displays raw JSON data when expanded', () => {
      render(<ProgressMetrics {...mockProps} />);

      const buttons = screen.getAllByRole('button');
      const tertiaryButton = buttons[1];

      fireEvent.click(tertiaryButton);

      expect(screen.getByText('masterplan.metrics.rawData')).toBeInTheDocument();

      // Should contain JSON with all data
      const jsonContainer = screen.getByText(/tokensUsed/);
      expect(jsonContainer).toBeInTheDocument();
    });
  });

  describe('Number Formatting', () => {
    it('formats large numbers with commas', () => {
      const largeNumberProps = {
        ...mockProps,
        tokensUsed: 1234567,
        estimatedTokens: 9876543,
      };

      render(<ProgressMetrics {...largeNumberProps} />);

      expect(screen.getByText(/1,234,567/)).toBeInTheDocument();
      expect(screen.getByText(/9,876,543/)).toBeInTheDocument();
    });

    it('formats cost to 4 decimal places', () => {
      const costProps = {
        ...mockProps,
        cost: 0.123456789,
      };

      render(<ProgressMetrics {...costProps} />);

      // Cost should be formatted to 4 decimal places max
      expect(screen.getByText(/\$0\.1235/)).toBeInTheDocument();
    });
  });

  describe('Progress Bar Animation', () => {
    it('applies transition classes to progress bar', () => {
      render(<ProgressMetrics {...mockProps} />);

      const progressBar = screen.getByRole('progressbar');
      const progressFill = progressBar.querySelector('div');

      expect(progressFill).toHaveClass('transition-all', 'duration-500', 'ease-out');
    });
  });

  describe('Accessibility', () => {
    it('has proper ARIA labels for progress bar', () => {
      render(<ProgressMetrics {...mockProps} />);

      const progressBar = screen.getByRole('progressbar');
      expect(progressBar).toHaveAttribute('aria-label');
    });

    it('has proper ARIA controls for collapsible sections', () => {
      render(<ProgressMetrics {...mockProps} />);

      const buttons = screen.getAllByRole('button');

      buttons.forEach((button) => {
        expect(button).toHaveAttribute('aria-expanded');
        expect(button).toHaveAttribute('aria-controls');
      });
    });

    it('updates aria-expanded when toggling sections', () => {
      render(<ProgressMetrics {...mockProps} />);

      const button = screen.getAllByRole('button')[0];

      expect(button).toHaveAttribute('aria-expanded', 'true');

      fireEvent.click(button);
      expect(button).toHaveAttribute('aria-expanded', 'false');

      fireEvent.click(button);
      expect(button).toHaveAttribute('aria-expanded', 'true');
    });
  });

  describe('Edge Cases', () => {
    it('handles zero values gracefully', () => {
      const zeroProps = {
        tokensUsed: 0,
        estimatedTokens: 0,
        cost: 0,
        duration: 0,
        estimatedDuration: 0,
        entities: {
          boundedContexts: 0,
          aggregates: 0,
          entities: 0,
          phases: 0,
          milestones: 0,
          tasks: 0,
        },
        isComplete: false,
      };

      render(<ProgressMetrics {...zeroProps} />);

      expect(screen.getByText('0%')).toBeInTheDocument();
      expect(screen.getByText('$0.00')).toBeInTheDocument();
    });

    it('handles very large numbers', () => {
      const largeProps = {
        ...mockProps,
        tokensUsed: 999999999,
        estimatedTokens: 999999999,
        cost: 999.9999,
      };

      render(<ProgressMetrics {...largeProps} />);

      expect(screen.getByText(/999,999,999/)).toBeInTheDocument();
      expect(screen.getByText(/\$1,000\.0000/)).toBeInTheDocument();
    });

    it('handles negative time remaining correctly', () => {
      const overtimeProps = {
        ...mockProps,
        duration: 200,
        estimatedDuration: 100,
      };

      render(<ProgressMetrics {...overtimeProps} />);

      // Should show 0 instead of negative value
      expect(screen.getByText('0s')).toBeInTheDocument();
    });
  });
});
