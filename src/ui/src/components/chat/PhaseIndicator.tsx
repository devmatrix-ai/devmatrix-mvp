/**
 * PhaseIndicator - Individual phase card with status and timing
 *
 * Displays a single phase with:
 * - Icon + phase name
 * - Status badge (pending/active/complete/failed)
 * - Duration (if phase is complete)
 * - Animated active state
 *
 * @example
 * ```tsx
 * <PhaseIndicator
 *   phase={{
 *     name: 'parsing',
 *     status: 'in_progress',
 *     icon: '⚙️',
 *     label: 'Generating Plan Structure'
 *   }}
 *   isActive={true}
 *   showDuration={true}
 * />
 * ```
 */

import React from 'react';
import { FiCheck, FiX, FiLoader, FiClock } from 'react-icons/fi';
import { useTranslation } from '../../i18n';
import type { PhaseIndicatorProps } from '../../types/masterplan';

/**
 * PhaseIndicator component
 */
const PhaseIndicator: React.FC<PhaseIndicatorProps> = ({
  phase,
  isActive,
  showDuration = true,
}) => {
  const { t } = useTranslation();

  /**
   * Get status badge styling
   */
  const getStatusBadgeStyle = (): string => {
    switch (phase.status) {
      case 'completed':
        return 'bg-green-500/20 text-green-400 border-green-500/30';
      case 'in_progress':
        return 'bg-blue-500/20 text-blue-400 border-blue-500/30';
      case 'failed':
        return 'bg-red-500/20 text-red-400 border-red-500/30';
      case 'pending':
      default:
        return 'bg-gray-600/20 text-gray-400 border-gray-600/30';
    }
  };

  /**
   * Get status icon
   */
  const getStatusIcon = () => {
    switch (phase.status) {
      case 'completed':
        return <FiCheck className="inline" />;
      case 'in_progress':
        return <FiLoader className="inline animate-spin" />;
      case 'failed':
        return <FiX className="inline" />;
      case 'pending':
      default:
        return <FiClock className="inline" />;
    }
  };

  /**
   * Get status label
   */
  const getStatusLabel = (): string => {
    switch (phase.status) {
      case 'completed':
        return 'Complete';
      case 'in_progress':
        return 'In Progress';
      case 'failed':
        return 'Failed';
      case 'pending':
      default:
        return 'Pending';
    }
  };

  return (
    <div
      className={`
        relative p-4 rounded-lg border transition-all duration-300
        ${isActive ? 'bg-white/5 border-blue-500/50 shadow-lg shadow-blue-500/20' : 'bg-white/5 border-white/10'}
        ${phase.status === 'in_progress' ? 'animate-pulse' : ''}
      `}
      role="status"
      aria-label={t('masterplan.accessibility.phaseIndicator', {
        phase: phase.label,
        status: phase.status,
      })}
    >
      {/* Icon + Label */}
      <div className="flex items-center gap-3 mb-2">
        <span className="text-2xl" role="img" aria-label={`${phase.label} icon`}>
          {phase.icon}
        </span>
        <div className="flex-1">
          <h4 className={`font-semibold ${isActive ? 'text-white' : 'text-gray-300'}`}>
            {phase.label}
          </h4>
        </div>
      </div>

      {/* Status Badge */}
      <div className={`inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-medium border ${getStatusBadgeStyle()}`}>
        {getStatusIcon()}
        <span>{getStatusLabel()}</span>
      </div>

      {/* Duration (if completed and showDuration is true) */}
      {showDuration && phase.status === 'completed' && phase.duration !== undefined && (
        <div className="mt-2 text-sm text-green-400">
          <FiClock className="inline mr-1" size={14} />
          {t('masterplan.timeline.phaseCompleted', { duration: phase.duration })}
        </div>
      )}

      {/* Active Indicator */}
      {isActive && phase.status === 'in_progress' && (
        <div className="absolute top-2 right-2 w-3 h-3 bg-blue-500 rounded-full animate-ping" />
      )}
    </div>
  );
};

export default PhaseIndicator;
