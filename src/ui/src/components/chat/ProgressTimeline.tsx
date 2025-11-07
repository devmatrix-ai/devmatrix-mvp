/**
 * ProgressTimeline - Visualize generation phases grouped by category
 *
 * Displays 9 phases grouped into 3 categories:
 * - Discovery & Parsing: discovery, parsing, validation
 * - Analysis & Planning: complexity_analysis, dependency_calculation, timeline_estimation, risk_analysis, resource_optimization
 * - Finalization: saving
 *
 * Features:
 * - Category-based grouping for better organization
 * - Color-coded status indicators
 * - Animated active phase
 * - Duration display for completed phases
 * - Category progress indicators
 *
 * @example
 * ```tsx
 * <ProgressTimeline
 *   phases={phasesList}
 *   currentPhase="complexity_analysis"
 * />
 * ```
 */

import React, { useMemo } from 'react';
import { FiCheck, FiX, FiLoader } from 'react-icons/fi';
import { GlassCard } from '../design-system';
import { useTranslation } from '../../i18n';
import type { ProgressTimelineProps, PhaseStatus } from '../../types/masterplan';

/**
 * Phase category type
 */
interface PhaseCategory {
  id: string;
  label: string;
  icon: string;
  phases: PhaseStatus[];
}

/**
 * ProgressTimeline component
 */
const ProgressTimeline: React.FC<ProgressTimelineProps> = ({
  phases,
  currentPhase,
  animateActive = true,
}) => {
  const { t } = useTranslation();

  // Group phases by category
  const categories = useMemo((): PhaseCategory[] => {
    const categoryMap: Record<string, PhaseCategory> = {
      'discovery-parsing': {
        id: 'discovery-parsing',
        label: 'Discovery & Parsing',
        icon: '📡',
        phases: [],
      },
      'analysis-planning': {
        id: 'analysis-planning',
        label: 'Analysis & Planning',
        icon: '📊',
        phases: [],
      },
      finalization: {
        id: 'finalization',
        label: 'Finalization',
        icon: '💾',
        phases: [],
      },
    };

    // Distribute phases into categories
    phases.forEach((phase) => {
      if (['discovery', 'parsing', 'validation'].includes(phase.name)) {
        categoryMap['discovery-parsing'].phases.push(phase);
      } else if (
        ['complexity_analysis', 'dependency_calculation', 'timeline_estimation', 'risk_analysis', 'resource_optimization'].includes(
          phase.name
        )
      ) {
        categoryMap['analysis-planning'].phases.push(phase);
      } else if (phase.name === 'saving') {
        categoryMap['finalization'].phases.push(phase);
      }
    });

    return Object.values(categoryMap);
  }, [phases]);

  /**
   * Get status color classes
   */
  const getStatusColor = (status: PhaseStatus['status']): string => {
    switch (status) {
      case 'completed':
        return 'bg-green-500 text-white';
      case 'in_progress':
        return 'bg-blue-500 text-white';
      case 'failed':
        return 'bg-red-500 text-white';
      case 'pending':
      default:
        return 'bg-gray-600 text-gray-400';
    }
  };

  /**
   * Get status icon
   */
  const getStatusIcon = (status: PhaseStatus['status']) => {
    switch (status) {
      case 'completed':
        return <FiCheck size={20} />;
      case 'in_progress':
        return <FiLoader size={20} className={animateActive ? 'animate-spin' : ''} />;
      case 'failed':
        return <FiX size={20} />;
      case 'pending':
      default:
        return <span className="text-sm">⏳</span>;
    }
  };

  /**
   * Calculate category status based on phases within it
   */
  const getCategoryStatus = (categoryPhases: PhaseStatus[]): PhaseStatus['status'] => {
    const hasInProgress = categoryPhases.some((p) => p.status === 'in_progress');
    const allCompleted = categoryPhases.every((p) => p.status === 'completed');
    const hasFailed = categoryPhases.some((p) => p.status === 'failed');

    if (hasFailed) return 'failed';
    if (hasInProgress) return 'in_progress';
    if (allCompleted) return 'completed';
    return 'pending';
  };

  /**
   * Check if any phase in category is active
   */
  const isCurrentPhaseInCategory = (categoryPhases: PhaseStatus[]): boolean => {
    return categoryPhases.some((p) => p.name === currentPhase);
  };

  return (
    <GlassCard>
      <h3 className="text-lg font-semibold text-white mb-6">
        {t('masterplan.timeline.title')}
      </h3>

      {/* Categories */}
      <div className="space-y-6">
        {categories.map((category, categoryIndex) => {
          const categoryStatus = getCategoryStatus(category.phases);
          const isCategoryActive = isCurrentPhaseInCategory(category.phases);

          return (
            <div key={category.id} className="relative">
              {/* Category Header */}
              <div
                className={`flex items-center gap-3 pb-4 border-b transition-all ${
                  isCategoryActive
                    ? 'border-blue-400/50'
                    : categoryStatus === 'completed'
                    ? 'border-green-400/30'
                    : 'border-gray-600/30'
                }`}
              >
                {/* Category Icon & Title */}
                <div
                  className={`text-2xl ${
                    isCategoryActive ? 'animate-pulse' : ''
                  }`}
                >
                  {category.icon}
                </div>
                <div className="flex-1">
                  <h4 className={`font-semibold ${isCategoryActive ? 'text-blue-300' : 'text-gray-300'}`}>
                    {category.label}
                  </h4>
                  {/* Category Progress */}
                  <div className="mt-2 flex items-center gap-2">
                    <div className="flex-1 h-1 bg-gray-700 rounded-full overflow-hidden">
                      <div
                        className={`h-full transition-all duration-300 ${
                          categoryStatus === 'completed'
                            ? 'bg-green-500 w-full'
                            : categoryStatus === 'in_progress'
                            ? 'bg-blue-500 w-2/3'
                            : 'bg-gray-600 w-0'
                        }`}
                      />
                    </div>
                    <span className="text-xs text-gray-400">
                      {category.phases.filter((p) => p.status === 'completed').length}/{category.phases.length}
                    </span>
                  </div>
                </div>
                {/* Category Status Icon */}
                <div className={`flex-shrink-0 ${getStatusColor(categoryStatus)} w-10 h-10 rounded-full flex items-center justify-center`}>
                  {getStatusIcon(categoryStatus)}
                </div>
              </div>

              {/* Phases in Category */}
              <div className="mt-4 ml-8 space-y-3">
                {category.phases.map((phase) => (
                  <div key={phase.name} className="flex items-center gap-3 group">
                    {/* Phase Icon */}
                    <div
                      className={`w-8 h-8 rounded-full flex items-center justify-center text-sm flex-shrink-0 transition-all ${
                        phase.status === 'in_progress' && animateActive
                          ? 'ring-2 ring-blue-400/70 animate-pulse'
                          : ''
                      } ${getStatusColor(phase.status)}`}
                      role="status"
                      aria-label={t('masterplan.accessibility.phaseIndicator', {
                        phase: phase.label,
                        status: phase.status,
                      })}
                    >
                      {getStatusIcon(phase.status)}
                    </div>

                    {/* Phase Info */}
                    <div className="flex-1 min-w-0">
                      <p
                        className={`text-sm font-medium truncate ${
                          phase.status === 'in_progress'
                            ? 'text-white'
                            : phase.status === 'completed'
                            ? 'text-green-400'
                            : 'text-gray-400'
                        }`}
                      >
                        {phase.label}
                      </p>
                      {/* Status message */}
                      {phase.status === 'completed' && phase.duration && (
                        <p className="text-xs text-green-400/70">
                          {Math.round(phase.duration)}s
                        </p>
                      )}
                      {phase.status === 'in_progress' && (
                        <p className="text-xs text-blue-400/70 animate-pulse">
                          {t('masterplan.timeline.phaseActive')}
                        </p>
                      )}
                    </div>
                  </div>
                ))}
              </div>

              {/* Category Separator */}
              {categoryIndex < categories.length - 1 && (
                <div className="mt-6 mb-2 h-px bg-gradient-to-r from-gray-700/50 via-gray-600/50 to-transparent" />
              )}
            </div>
          );
        })}
      </div>
    </GlassCard>
  );
};

export default ProgressTimeline;
