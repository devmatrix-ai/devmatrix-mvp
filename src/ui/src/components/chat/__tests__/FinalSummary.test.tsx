/**
 * FinalSummary Component Tests
 *
 * Tests for:
 * - Success indicator animation
 * - Total statistics display
 * - Entity summary
 * - Architecture style and tech stack
 * - Action buttons
 * - Number and cost formatting
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import FinalSummary from '../FinalSummary';
import type { FinalSummaryProps } from '../../../types/masterplan';

// Mock translation hook
vi.mock('../../../i18n', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}));

const mockStats = {
  totalTokens: 25000,
  totalCost: 0.4567,
  totalDuration: 135,
  entities: {
    boundedContexts: 5,
    aggregates: 12,
    entities: 45,
  },
  phases: {
    phases: 3,
    milestones: 17,
    tasks: 120,
  },
};

describe('FinalSummary', () => {
  const mockOnViewDetails = vi.fn();
  const mockOnStartExecution = vi.fn();
  const mockOnExport = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Success Header', () => {
    it('renders success title', () => {
      render(
        <FinalSummary
          stats={mockStats}
          onViewDetails={mockOnViewDetails}
          onStartExecution={mockOnStartExecution}
        />
      );

      expect(screen.getByText('masterplan.summary.title')).toBeInTheDocument();
    });

    it('renders success subtitle', () => {
      render(
        <FinalSummary
          stats={mockStats}
          onViewDetails={mockOnViewDetails}
          onStartExecution={mockOnStartExecution}
        />
      );

      expect(screen.getByText('masterplan.summary.subtitle')).toBeInTheDocument();
    });

    it('renders success checkmark icon', () => {
      const { container } = render(
        <FinalSummary
          stats={mockStats}
          onViewDetails={mockOnViewDetails}
          onStartExecution={mockOnStartExecution}
        />
      );

      // FiCheckCircle icon should be present
      const checkIcon = container.querySelector('.text-green-400');
      expect(checkIcon).toBeInTheDocument();
    });

    it('applies animation to success icon container', () => {
      const { container } = render(
        <FinalSummary
          stats={mockStats}
          onViewDetails={mockOnViewDetails}
          onStartExecution={mockOnStartExecution}
        />
      );

      const iconContainer = container.querySelector('.animate-checkBounce');
      expect(iconContainer).toBeInTheDocument();
    });
  });

  describe('Total Statistics', () => {
    it('displays total tokens with formatting', () => {
      render(
        <FinalSummary
          stats={mockStats}
          onViewDetails={mockOnViewDetails}
          onStartExecution={mockOnStartExecution}
        />
      );

      expect(screen.getByText('25,000')).toBeInTheDocument();
    });

    it('displays total cost with currency formatting', () => {
      render(
        <FinalSummary
          stats={mockStats}
          onViewDetails={mockOnViewDetails}
          onStartExecution={mockOnStartExecution}
        />
      );

      // Cost should be formatted as USD with up to 4 decimal places
      expect(screen.getByText(/\$0\.4567/)).toBeInTheDocument();
    });

    it('displays total duration', () => {
      render(
        <FinalSummary
          stats={mockStats}
          onViewDetails={mockOnViewDetails}
          onStartExecution={mockOnStartExecution}
        />
      );

      expect(screen.getByText('135s')).toBeInTheDocument();
    });

    it('renders statistics icons', () => {
      const { container } = render(
        <FinalSummary
          stats={mockStats}
          onViewDetails={mockOnViewDetails}
          onStartExecution={mockOnStartExecution}
        />
      );

      // Should have FiLayers, FiDollarSign, FiClock icons
      const icons = container.querySelectorAll('svg');
      expect(icons.length).toBeGreaterThan(0);
    });
  });

  describe('Entity Summary', () => {
    it('displays all entity counts', () => {
      render(
        <FinalSummary
          stats={mockStats}
          onViewDetails={mockOnViewDetails}
          onStartExecution={mockOnStartExecution}
        />
      );

      expect(screen.getByText('5')).toBeInTheDocument(); // boundedContexts
      expect(screen.getByText('12')).toBeInTheDocument(); // aggregates
      expect(screen.getByText('45')).toBeInTheDocument(); // entities
      expect(screen.getByText('3')).toBeInTheDocument(); // phases
      expect(screen.getByText('17')).toBeInTheDocument(); // milestones
      expect(screen.getByText('120')).toBeInTheDocument(); // tasks
    });

    it('displays entity labels', () => {
      render(
        <FinalSummary
          stats={mockStats}
          onViewDetails={mockOnViewDetails}
          onStartExecution={mockOnStartExecution}
        />
      );

      expect(screen.getByText('masterplan.metrics.boundedContexts')).toBeInTheDocument();
      expect(screen.getByText('masterplan.metrics.aggregates')).toBeInTheDocument();
      expect(screen.getByText('masterplan.metrics.entities')).toBeInTheDocument();
      expect(screen.getByText('masterplan.metrics.phases')).toBeInTheDocument();
      expect(screen.getByText('masterplan.metrics.milestones')).toBeInTheDocument();
      expect(screen.getByText('masterplan.metrics.tasks')).toBeInTheDocument();
    });
  });

  describe('Architecture Style and Tech Stack', () => {
    it('displays architecture style when provided', () => {
      render(
        <FinalSummary
          stats={mockStats}
          architectureStyle="Domain-Driven Design (DDD)"
          onViewDetails={mockOnViewDetails}
          onStartExecution={mockOnStartExecution}
        />
      );

      expect(screen.getByText('masterplan.summary.architectureStyle')).toBeInTheDocument();
      expect(screen.getByText('Domain-Driven Design (DDD)')).toBeInTheDocument();
    });

    it('does not display architecture section when not provided', () => {
      render(
        <FinalSummary
          stats={mockStats}
          onViewDetails={mockOnViewDetails}
          onStartExecution={mockOnStartExecution}
        />
      );

      expect(screen.queryByText('masterplan.summary.architectureStyle')).not.toBeInTheDocument();
    });

    it('displays tech stack when provided', () => {
      const techStack = ['React', 'FastAPI', 'PostgreSQL', 'Redis'];

      render(
        <FinalSummary
          stats={mockStats}
          techStack={techStack}
          onViewDetails={mockOnViewDetails}
          onStartExecution={mockOnStartExecution}
        />
      );

      expect(screen.getByText('masterplan.summary.techStack')).toBeInTheDocument();
      expect(screen.getByText('React')).toBeInTheDocument();
      expect(screen.getByText('FastAPI')).toBeInTheDocument();
      expect(screen.getByText('PostgreSQL')).toBeInTheDocument();
      expect(screen.getByText('Redis')).toBeInTheDocument();
    });

    it('does not display tech stack section when empty array', () => {
      render(
        <FinalSummary
          stats={mockStats}
          techStack={[]}
          onViewDetails={mockOnViewDetails}
          onStartExecution={mockOnStartExecution}
        />
      );

      expect(screen.queryByText('masterplan.summary.techStack')).not.toBeInTheDocument();
    });

    it('does not display tech stack section when not provided', () => {
      render(
        <FinalSummary
          stats={mockStats}
          onViewDetails={mockOnViewDetails}
          onStartExecution={mockOnStartExecution}
        />
      );

      expect(screen.queryByText('masterplan.summary.techStack')).not.toBeInTheDocument();
    });

    it('displays both architecture and tech stack when both provided', () => {
      render(
        <FinalSummary
          stats={mockStats}
          architectureStyle="DDD"
          techStack={['React', 'FastAPI']}
          onViewDetails={mockOnViewDetails}
          onStartExecution={mockOnStartExecution}
        />
      );

      expect(screen.getByText('masterplan.summary.detailedBreakdown')).toBeInTheDocument();
      expect(screen.getByText('DDD')).toBeInTheDocument();
      expect(screen.getByText('React')).toBeInTheDocument();
    });
  });

  describe('Action Buttons', () => {
    it('renders View Details button', () => {
      render(
        <FinalSummary
          stats={mockStats}
          onViewDetails={mockOnViewDetails}
          onStartExecution={mockOnStartExecution}
        />
      );

      expect(screen.getByText('masterplan.buttons.viewDetails')).toBeInTheDocument();
    });

    it('renders Start Execution button', () => {
      render(
        <FinalSummary
          stats={mockStats}
          onViewDetails={mockOnViewDetails}
          onStartExecution={mockOnStartExecution}
        />
      );

      expect(screen.getByText('masterplan.buttons.startExecution')).toBeInTheDocument();
    });

    it('calls onViewDetails when View Details button is clicked', () => {
      render(
        <FinalSummary
          stats={mockStats}
          onViewDetails={mockOnViewDetails}
          onStartExecution={mockOnStartExecution}
        />
      );

      const button = screen.getByText('masterplan.buttons.viewDetails');
      fireEvent.click(button);

      expect(mockOnViewDetails).toHaveBeenCalledTimes(1);
    });

    it('calls onStartExecution when Start Execution button is clicked', () => {
      render(
        <FinalSummary
          stats={mockStats}
          onViewDetails={mockOnViewDetails}
          onStartExecution={mockOnStartExecution}
        />
      );

      const button = screen.getByText('masterplan.buttons.startExecution');
      fireEvent.click(button);

      expect(mockOnStartExecution).toHaveBeenCalledTimes(1);
    });

    it('renders Export button when onExport is provided', () => {
      render(
        <FinalSummary
          stats={mockStats}
          onViewDetails={mockOnViewDetails}
          onStartExecution={mockOnStartExecution}
          onExport={mockOnExport}
        />
      );

      expect(screen.getByText('masterplan.buttons.export')).toBeInTheDocument();
    });

    it('does not render Export button when onExport is not provided', () => {
      render(
        <FinalSummary
          stats={mockStats}
          onViewDetails={mockOnViewDetails}
          onStartExecution={mockOnStartExecution}
        />
      );

      expect(screen.queryByText('masterplan.buttons.export')).not.toBeInTheDocument();
    });

    it('calls onExport when Export button is clicked', () => {
      render(
        <FinalSummary
          stats={mockStats}
          onViewDetails={mockOnViewDetails}
          onStartExecution={mockOnStartExecution}
          onExport={mockOnExport}
        />
      );

      const button = screen.getByText('masterplan.buttons.export');
      fireEvent.click(button);

      expect(mockOnExport).toHaveBeenCalledTimes(1);
    });
  });

  describe('Accessibility', () => {
    it('has success announcement for screen readers', () => {
      render(
        <FinalSummary
          stats={mockStats}
          onViewDetails={mockOnViewDetails}
          onStartExecution={mockOnStartExecution}
        />
      );

      const announcement = screen.getByRole('status');
      expect(announcement).toHaveAttribute('aria-live', 'polite');
      expect(announcement).toHaveClass('sr-only');
    });

    it('announces completion message', () => {
      render(
        <FinalSummary
          stats={mockStats}
          onViewDetails={mockOnViewDetails}
          onStartExecution={mockOnStartExecution}
        />
      );

      expect(screen.getByText('masterplan.accessibility.completionAnnouncement')).toBeInTheDocument();
    });
  });

  describe('Number Formatting', () => {
    it('formats large token numbers with commas', () => {
      const largeStats = {
        ...mockStats,
        totalTokens: 1234567,
      };

      render(
        <FinalSummary
          stats={largeStats}
          onViewDetails={mockOnViewDetails}
          onStartExecution={mockOnStartExecution}
        />
      );

      expect(screen.getByText('1,234,567')).toBeInTheDocument();
    });

    it('formats cost to 4 decimal places', () => {
      const preciseStats = {
        ...mockStats,
        totalCost: 0.123456789,
      };

      render(
        <FinalSummary
          stats={preciseStats}
          onViewDetails={mockOnViewDetails}
          onStartExecution={mockOnStartExecution}
        />
      );

      // Should round to 4 decimal places
      expect(screen.getByText(/\$0\.1235/)).toBeInTheDocument();
    });

    it('formats cost to minimum 2 decimal places', () => {
      const wholeStats = {
        ...mockStats,
        totalCost: 5,
      };

      render(
        <FinalSummary
          stats={wholeStats}
          onViewDetails={mockOnViewDetails}
          onStartExecution={mockOnStartExecution}
        />
      );

      expect(screen.getByText(/\$5\.00/)).toBeInTheDocument();
    });
  });

  describe('Responsive Layout', () => {
    it('applies responsive classes to button container', () => {
      const { container } = render(
        <FinalSummary
          stats={mockStats}
          onViewDetails={mockOnViewDetails}
          onStartExecution={mockOnStartExecution}
        />
      );

      const buttonContainer = container.querySelector('.flex-col.sm\\:flex-row');
      expect(buttonContainer).toBeInTheDocument();
    });

    it('applies responsive grid to statistics', () => {
      const { container } = render(
        <FinalSummary
          stats={mockStats}
          onViewDetails={mockOnViewDetails}
          onStartExecution={mockOnStartExecution}
        />
      );

      const statsGrid = container.querySelector('.grid.grid-cols-1.md\\:grid-cols-3');
      expect(statsGrid).toBeInTheDocument();
    });
  });

  describe('Edge Cases', () => {
    it('handles zero values gracefully', () => {
      const zeroStats = {
        totalTokens: 0,
        totalCost: 0,
        totalDuration: 0,
        entities: {
          boundedContexts: 0,
          aggregates: 0,
          entities: 0,
        },
        phases: {
          phases: 0,
          milestones: 0,
          tasks: 0,
        },
      };

      render(
        <FinalSummary
          stats={zeroStats}
          onViewDetails={mockOnViewDetails}
          onStartExecution={mockOnStartExecution}
        />
      );

      expect(screen.getByText('0')).toBeInTheDocument();
      expect(screen.getByText(/\$0\.00/)).toBeInTheDocument();
      expect(screen.getByText('0s')).toBeInTheDocument();
    });

    it('handles very large numbers', () => {
      const hugeStats = {
        ...mockStats,
        totalTokens: 999999999,
        entities: {
          boundedContexts: 999,
          aggregates: 9999,
          entities: 99999,
        },
        phases: {
          phases: 99,
          milestones: 999,
          tasks: 9999,
        },
      };

      render(
        <FinalSummary
          stats={hugeStats}
          onViewDetails={mockOnViewDetails}
          onStartExecution={mockOnStartExecution}
        />
      );

      expect(screen.getByText('999,999,999')).toBeInTheDocument();
      expect(screen.getByText('999')).toBeInTheDocument();
      expect(screen.getByText('9999')).toBeInTheDocument();
    });

    it('handles empty tech stack array', () => {
      render(
        <FinalSummary
          stats={mockStats}
          architectureStyle="DDD"
          techStack={[]}
          onViewDetails={mockOnViewDetails}
          onStartExecution={mockOnStartExecution}
        />
      );

      // Should still show architecture but not tech stack
      expect(screen.getByText('DDD')).toBeInTheDocument();
      expect(screen.queryByText('masterplan.summary.techStack')).not.toBeInTheDocument();
    });

    it('handles single tech stack item', () => {
      render(
        <FinalSummary
          stats={mockStats}
          techStack={['React']}
          onViewDetails={mockOnViewDetails}
          onStartExecution={mockOnStartExecution}
        />
      );

      expect(screen.getByText('React')).toBeInTheDocument();
    });
  });
});
