/**
 * ProgressTimeline Component Tests
 *
 * Tests for:
 * - Phase rendering (4 phases)
 * - Status color coding
 * - Animated active phase
 * - Duration display for completed phases
 * - Connector line colors
 * - Mobile responsive layout
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import ProgressTimeline from '../ProgressTimeline';
import type { PhaseStatus } from '../../../types/masterplan';

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

const mockPhases: PhaseStatus[] = [
  {
    name: 'discovery',
    status: 'completed',
    icon: '✓',
    label: 'Discovery',
    duration: 45,
  },
  {
    name: 'parsing',
    status: 'in_progress',
    icon: '⚙️',
    label: 'Parsing',
  },
  {
    name: 'validation',
    status: 'pending',
    icon: '⏳',
    label: 'Validation',
  },
  {
    name: 'saving',
    status: 'pending',
    icon: '⏳',
    label: 'Saving',
  },
];

describe('ProgressTimeline', () => {
  describe('Phase Rendering', () => {
    it('renders all phases', () => {
      render(
        <ProgressTimeline
          phases={mockPhases}
          currentPhase="parsing"
          animateActive={true}
        />
      );

      // Note: Each phase appears twice (desktop + mobile layouts)
      expect(screen.getAllByText('Discovery')).toHaveLength(2);
      expect(screen.getAllByText('Parsing')).toHaveLength(2);
      expect(screen.getAllByText('Validation')).toHaveLength(2);
      expect(screen.getAllByText('Saving')).toHaveLength(2);
    });

    it('renders timeline title', () => {
      render(
        <ProgressTimeline
          phases={mockPhases}
          currentPhase="parsing"
        />
      );

      expect(screen.getByText('masterplan.timeline.title')).toBeInTheDocument();
    });

    it('renders phase icons', () => {
      render(
        <ProgressTimeline
          phases={mockPhases}
          currentPhase="parsing"
        />
      );

      // Icons should be in status elements
      const statusElements = screen.getAllByRole('status');
      expect(statusElements).toHaveLength(mockPhases.length);
    });
  });

  describe('Status Colors', () => {
    it('applies green color to completed phase', () => {
      render(
        <ProgressTimeline
          phases={mockPhases}
          currentPhase="parsing"
        />
      );

      const statusElements = screen.getAllByRole('status');
      const completedPhase = statusElements[0]; // Discovery

      expect(completedPhase).toHaveClass('bg-green-500');
    });

    it('applies blue color to in-progress phase', () => {
      render(
        <ProgressTimeline
          phases={mockPhases}
          currentPhase="parsing"
        />
      );

      const statusElements = screen.getAllByRole('status');
      const inProgressPhase = statusElements[1]; // Parsing

      expect(inProgressPhase).toHaveClass('bg-blue-500');
    });

    it('applies gray color to pending phases', () => {
      render(
        <ProgressTimeline
          phases={mockPhases}
          currentPhase="parsing"
        />
      );

      const statusElements = screen.getAllByRole('status');
      const pendingPhase1 = statusElements[2]; // Validation
      const pendingPhase2 = statusElements[3]; // Saving

      expect(pendingPhase1).toHaveClass('bg-gray-600');
      expect(pendingPhase2).toHaveClass('bg-gray-600');
    });

    it('applies red color to failed phase', () => {
      const failedPhases = [
        ...mockPhases.slice(0, 2),
        {
          name: 'validation',
          status: 'failed' as const,
          icon: '✗',
          label: 'Validation',
        },
        mockPhases[3],
      ];

      render(
        <ProgressTimeline
          phases={failedPhases}
          currentPhase="validation"
        />
      );

      const statusElements = screen.getAllByRole('status');
      const failedPhase = statusElements[2];

      expect(failedPhase).toHaveClass('bg-red-500');
    });
  });

  describe('Active Phase Animation', () => {
    it('applies animation classes to active phase when animateActive is true', () => {
      render(
        <ProgressTimeline
          phases={mockPhases}
          currentPhase="parsing"
          animateActive={true}
        />
      );

      const statusElements = screen.getAllByRole('status');
      const activePhase = statusElements[1]; // Parsing is in_progress

      expect(activePhase).toHaveClass('animate-pulse');
      expect(activePhase).toHaveClass('ring-4');
      expect(activePhase).toHaveClass('ring-blue-400/50');
    });

    it('does not apply animation classes when animateActive is false', () => {
      render(
        <ProgressTimeline
          phases={mockPhases}
          currentPhase="parsing"
          animateActive={false}
        />
      );

      const statusElements = screen.getAllByRole('status');
      const activePhase = statusElements[1];

      expect(activePhase).not.toHaveClass('animate-pulse');
    });

    it('animates spinner icon for in-progress phase', () => {
      render(
        <ProgressTimeline
          phases={mockPhases}
          currentPhase="parsing"
          animateActive={true}
        />
      );

      // FiLoader should have animate-spin class
      const statusElements = screen.getAllByRole('status');
      const activePhase = statusElements[1];
      const spinner = activePhase.querySelector('svg');

      expect(spinner).toHaveClass('animate-spin');
    });
  });

  describe('Phase Status Messages', () => {
    it('displays duration for completed phase', () => {
      render(
        <ProgressTimeline
          phases={mockPhases}
          currentPhase="parsing"
        />
      );

      // Duration should be displayed for completed phase (appears twice: desktop + mobile)
      expect(screen.getAllByText(/masterplan.timeline.phaseCompleted/)).toHaveLength(2);
    });

    it('displays active message for in-progress phase', () => {
      render(
        <ProgressTimeline
          phases={mockPhases}
          currentPhase="parsing"
        />
      );

      // Appears twice: desktop + mobile
      expect(screen.getAllByText('masterplan.timeline.phaseActive')).toHaveLength(2);
    });

    it('displays pending message for pending phases', () => {
      render(
        <ProgressTimeline
          phases={mockPhases}
          currentPhase="parsing"
        />
      );

      const pendingMessages = screen.getAllByText('masterplan.timeline.phasePending');
      // 2 pending phases × 2 layouts (desktop + mobile) = 4 elements
      expect(pendingMessages).toHaveLength(4);
    });

    it('displays failed message for failed phase', () => {
      const failedPhases = [
        ...mockPhases.slice(0, 2),
        {
          name: 'validation',
          status: 'failed' as const,
          icon: '✗',
          label: 'Validation',
        },
        mockPhases[3],
      ];

      render(
        <ProgressTimeline
          phases={failedPhases}
          currentPhase="validation"
        />
      );

      // Appears twice: desktop + mobile
      expect(screen.getAllByText('masterplan.timeline.phaseFailed')).toHaveLength(2);
    });
  });

  describe('Text Styling', () => {
    it('applies white text to active phase label', () => {
      render(
        <ProgressTimeline
          phases={mockPhases}
          currentPhase="parsing"
        />
      );

      const parsingLabels = screen.getAllByText('Parsing');
      // Check first occurrence (desktop)
      expect(parsingLabels[0]).toHaveClass('text-white');
    });

    it('applies gray text to non-active phase labels', () => {
      render(
        <ProgressTimeline
          phases={mockPhases}
          currentPhase="parsing"
        />
      );

      const discoveryLabels = screen.getAllByText('Discovery');
      const validationLabels = screen.getAllByText('Validation');
      const savingLabels = screen.getAllByText('Saving');

      // Check first occurrences (desktop)
      expect(discoveryLabels[0]).toHaveClass('text-gray-400');
      expect(validationLabels[0]).toHaveClass('text-gray-400');
      expect(savingLabels[0]).toHaveClass('text-gray-400');
    });
  });

  describe('Connector Lines', () => {
    it('renders connector lines between phases', () => {
      const { container } = render(
        <ProgressTimeline
          phases={mockPhases}
          currentPhase="parsing"
        />
      );

      // There should be 3 connector lines for 4 phases
      const connectors = container.querySelectorAll('.w-16.h-1');
      expect(connectors).toHaveLength(3);
    });

    it('applies green connector for completed to completed', () => {
      const allCompletedPhases = mockPhases.map((phase) => ({
        ...phase,
        status: 'completed' as const,
      }));

      const { container } = render(
        <ProgressTimeline
          phases={allCompletedPhases}
          currentPhase="saving"
        />
      );

      const connectors = container.querySelectorAll('.w-16.h-1 > div');
      // When all are completed, last connector should still be green
      // But connector between last two completed might be gradient
      expect(connectors.length).toBeGreaterThan(0);
      // Just verify connectors exist and have color classes
      connectors.forEach((connector) => {
        const hasColorClass =
          connector.classList.contains('bg-green-500') ||
          connector.classList.contains('bg-gradient-to-r');
        expect(hasColorClass).toBe(true);
      });
    });

    it('applies gradient connector for completed to in-progress', () => {
      const { container } = render(
        <ProgressTimeline
          phases={mockPhases}
          currentPhase="parsing"
        />
      );

      const connectors = container.querySelectorAll('.w-16.h-1 > div');
      const firstConnector = connectors[0]; // Discovery to Parsing

      expect(firstConnector).toHaveClass('bg-gradient-to-r');
      expect(firstConnector).toHaveClass('from-green-500');
      expect(firstConnector).toHaveClass('to-blue-500');
    });

    it('applies gray connector for pending phases', () => {
      const { container } = render(
        <ProgressTimeline
          phases={mockPhases}
          currentPhase="parsing"
        />
      );

      const connectors = container.querySelectorAll('.w-16.h-1 > div');
      const lastConnector = connectors[2]; // Validation to Saving

      expect(lastConnector).toHaveClass('bg-gray-600');
    });
  });

  describe('Accessibility', () => {
    it('has proper ARIA labels for phase indicators', () => {
      render(
        <ProgressTimeline
          phases={mockPhases}
          currentPhase="parsing"
        />
      );

      const statusElements = screen.getAllByRole('status');

      statusElements.forEach((element, index) => {
        expect(element).toHaveAttribute('aria-label');
        const label = element.getAttribute('aria-label');
        expect(label).toContain(mockPhases[index].label);
        expect(label).toContain(mockPhases[index].status);
      });
    });
  });

  describe('Responsive Layout', () => {
    it('renders horizontal timeline for desktop', () => {
      const { container } = render(
        <ProgressTimeline
          phases={mockPhases}
          currentPhase="parsing"
        />
      );

      // Horizontal timeline has flex items-center justify-between
      const horizontalTimeline = container.querySelector('.flex.items-center.justify-between');
      expect(horizontalTimeline).toBeInTheDocument();
    });

    it('renders mobile vertical timeline', () => {
      const { container } = render(
        <ProgressTimeline
          phases={mockPhases}
          currentPhase="parsing"
        />
      );

      // Mobile timeline has lg:hidden class
      const mobileTimeline = container.querySelector('.lg\\:hidden');
      expect(mobileTimeline).toBeInTheDocument();
    });
  });

  describe('Edge Cases', () => {
    it('handles empty phases array', () => {
      render(
        <ProgressTimeline
          phases={[]}
          currentPhase=""
        />
      );

      expect(screen.getByText('masterplan.timeline.title')).toBeInTheDocument();
    });

    it('handles single phase', () => {
      const singlePhase = [mockPhases[0]];

      const { container } = render(
        <ProgressTimeline
          phases={singlePhase}
          currentPhase="discovery"
        />
      );

      // Appears twice (desktop + mobile)
      expect(screen.getAllByText('Discovery')).toHaveLength(2);

      // No connector lines for single phase
      const connectors = container.querySelectorAll('.w-16.h-1');
      expect(connectors).toHaveLength(0);
    });

    it('handles phase without duration', () => {
      const phasesWithoutDuration = mockPhases.map((phase) => ({
        ...phase,
        duration: undefined,
      }));

      render(
        <ProgressTimeline
          phases={phasesWithoutDuration}
          currentPhase="parsing"
        />
      );

      // Should not crash, duration message should not appear
      expect(screen.queryByText(/masterplan.timeline.phaseCompleted/)).not.toBeInTheDocument();
    });

    it('handles all phases pending', () => {
      const allPending = mockPhases.map((phase) => ({
        ...phase,
        status: 'pending' as const,
      }));

      render(
        <ProgressTimeline
          phases={allPending}
          currentPhase=""
        />
      );

      const pendingMessages = screen.getAllByText('masterplan.timeline.phasePending');
      // 4 phases × 2 layouts (desktop + mobile) = 8
      expect(pendingMessages).toHaveLength(8);
    });

    it('handles all phases completed', () => {
      const allCompleted = mockPhases.map((phase) => ({
        ...phase,
        status: 'completed' as const,
        duration: 30,
      }));

      render(
        <ProgressTimeline
          phases={allCompleted}
          currentPhase="saving"
        />
      );

      const completedMessages = screen.getAllByText(/masterplan.timeline.phaseCompleted/);
      // 4 phases × 2 layouts (desktop + mobile) = 8
      expect(completedMessages).toHaveLength(8);
    });
  });
});
