/**
 * ProgressTimeline - Visualize generation phases in sequential order
 *
 * Displays 4 phases (Discovery → Parsing → Validation → Saving) with:
 * - Color-coded status indicators
 * - Animated active phase
 * - Duration display for completed phases
 * - Phase-specific icons
 *
 * @example
 * ```tsx
 * <ProgressTimeline
 *   phases={[
 *     { name: 'discovery', status: 'completed', duration: 45, icon: '✓', label: 'Discovery' },
 *     { name: 'parsing', status: 'in_progress', icon: '⚙️', label: 'Parsing' },
 *     { name: 'validation', status: 'pending', icon: '⏳', label: 'Validation' },
 *     { name: 'saving', status: 'pending', icon: '⏳', label: 'Saving' }
 *   ]}
 *   currentPhase="parsing"
 * />
 * ```
 */

import React from 'react';
import { FiCheck, FiX, FiLoader } from 'react-icons/fi';
import { GlassCard } from '../design-system';
import { useTranslation } from '../../i18n';
import type { ProgressTimelineProps, PhaseStatus } from '../../types/masterplan';

/**
 * ProgressTimeline component
 */
const ProgressTimeline: React.FC<ProgressTimelineProps> = ({
  phases,
  // currentPhase,
  animateActive = true,
}) => {
  const { t } = useTranslation();

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
   * Get connector line color
   */
  const getConnectorColor = (currentStatus: PhaseStatus['status'], nextStatus: PhaseStatus['status']): string => {
    if (currentStatus === 'completed' && (nextStatus === 'completed' || nextStatus === 'in_progress')) {
      return 'bg-gradient-to-r from-green-500 to-blue-500';
    }
    if (currentStatus === 'completed') {
      return 'bg-green-500';
    }
    return 'bg-gray-600';
  };

  return (
    <GlassCard>
      <h3 className="text-lg font-semibold text-white mb-6">
        {t('masterplan.timeline.title')}
      </h3>

      {/* Horizontal Timeline */}
      <div className="relative">
        <div className="flex items-center justify-between">
          {phases.map((phase, index) => (
            <React.Fragment key={phase.name}>
              {/* Phase Card */}
              <div className="flex flex-col items-center flex-1 min-w-0">
                {/* Status Icon */}
                <div
                  className={`w-16 h-16 rounded-full flex items-center justify-center ${getStatusColor(
                    phase.status
                  )} transition-all duration-300 shadow-lg ${
                    phase.status === 'in_progress' && animateActive
                      ? 'animate-pulse ring-4 ring-blue-400/50'
                      : ''
                  }`}
                  role="status"
                  aria-label={t('masterplan.accessibility.phaseIndicator', {
                    phase: phase.label,
                    status: phase.status,
                  })}
                >
                  {getStatusIcon(phase.status)}
                </div>

                {/* Phase Label */}
                <div className="mt-3 text-center">
                  <p
                    className={`text-sm font-semibold ${
                      phase.status === 'in_progress' ? 'text-white' : 'text-gray-400'
                    }`}
                  >
                    {phase.label}
                  </p>

                  {/* Duration (if completed) */}
                  {phase.status === 'completed' && phase.duration && (
                    <p className="text-xs text-green-400 mt-1">
                      {t('masterplan.timeline.phaseCompleted', { duration: phase.duration })}
                    </p>
                  )}

                  {/* Status Messages */}
                  {phase.status === 'in_progress' && (
                    <p className="text-xs text-blue-400 mt-1">
                      {t('masterplan.timeline.phaseActive')}
                    </p>
                  )}

                  {phase.status === 'pending' && (
                    <p className="text-xs text-gray-500 mt-1">
                      {t('masterplan.timeline.phasePending')}
                    </p>
                  )}

                  {phase.status === 'failed' && (
                    <p className="text-xs text-red-400 mt-1">
                      {t('masterplan.timeline.phaseFailed')}
                    </p>
                  )}
                </div>
              </div>

              {/* Connector Line */}
              {index < phases.length - 1 && (
                <div className="flex-shrink-0 w-16 h-1 mx-2 relative top-[-30px]">
                  <div
                    className={`h-full rounded transition-all duration-500 ${getConnectorColor(
                      phase.status,
                      phases[index + 1].status
                    )}`}
                  />
                </div>
              )}
            </React.Fragment>
          ))}
        </div>
      </div>

      {/* Mobile-friendly vertical timeline (shown on small screens) */}
      <div className="mt-8 lg:hidden space-y-4">
        {phases.map((phase, index) => (
          <div
            key={phase.name}
            className="flex items-start gap-4"
          >
            {/* Status Icon */}
            <div
              className={`w-12 h-12 rounded-full flex items-center justify-center flex-shrink-0 ${getStatusColor(
                phase.status
              )} ${
                phase.status === 'in_progress' && animateActive
                  ? 'animate-pulse ring-4 ring-blue-400/50'
                  : ''
              }`}
            >
              {getStatusIcon(phase.status)}
            </div>

            {/* Phase Info */}
            <div className="flex-1 pt-1">
              <p className={`font-semibold ${phase.status === 'in_progress' ? 'text-white' : 'text-gray-400'}`}>
                {phase.label}
              </p>

              {phase.status === 'completed' && phase.duration && (
                <p className="text-sm text-green-400 mt-1">
                  {t('masterplan.timeline.phaseCompleted', { duration: phase.duration })}
                </p>
              )}

              {phase.status === 'in_progress' && (
                <p className="text-sm text-blue-400 mt-1">
                  {t('masterplan.timeline.phaseActive')}
                </p>
              )}

              {phase.status === 'pending' && (
                <p className="text-sm text-gray-500 mt-1">
                  {t('masterplan.timeline.phasePending')}
                </p>
              )}

              {phase.status === 'failed' && (
                <p className="text-sm text-red-400 mt-1">
                  {t('masterplan.timeline.phaseFailed')}
                </p>
              )}
            </div>

            {/* Vertical Connector */}
            {index < phases.length - 1 && (
              <div className="absolute left-6 w-0.5 h-full ml-[23px] mt-12">
                <div
                  className={`w-full h-16 ${getConnectorColor(phase.status, phases[index + 1].status)}`}
                />
              </div>
            )}
          </div>
        ))}
      </div>
    </GlassCard>
  );
};

export default ProgressTimeline;
