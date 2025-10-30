/**
 * InlineProgressHeader - Compact progress indicator inline in chat
 *
 * Displays a 50px height inline header with:
 * - Phase indicator (emoji + text)
 * - Progress bar (0-100%)
 * - Time remaining
 * - Click handler to open detailed modal
 * - Always visible, independent of modal state
 *
 * @example
 * ```tsx
 * <InlineProgressHeader
 *   event={masterPlanProgress}
 *   onClick={() => setModalOpen(true)}
 * />
 * ```
 */

import React, { useMemo } from 'react';
import { FiClock, FiZap } from 'react-icons/fi';
import { useTranslation } from '../../i18n';
import type { InlineProgressHeaderProps } from '../../types/masterplan';

/**
 * InlineProgressHeader component
 */
const InlineProgressHeader: React.FC<InlineProgressHeaderProps> = ({
  event,
  onClick,
}) => {
  const { t } = useTranslation();

  // Extract data from event
  const percentage = event?.data?.percentage || 0;
  // const _currentPhase = event?.data?.current_phase || '';
  const timeRemaining = event?.data?.time_remaining || 0;
  const tokensReceived = event?.data?.tokens_received || 0;
  const estimatedTotal = event?.data?.estimated_total || 0;

  // Determine phase label and emoji
  const phaseInfo = useMemo(() => {
    const eventType = event?.event || '';

    if (eventType.includes('discovery')) {
      return {
        emoji: '🔍',
        label: t('masterplan.phase.discovery'),
      };
    }

    if (eventType.includes('parsing')) {
      return {
        emoji: '⚙️',
        label: t('masterplan.phase.parsing'),
      };
    }

    if (eventType.includes('validation')) {
      return {
        emoji: '✅',
        label: t('masterplan.phase.validation'),
      };
    }

    if (eventType.includes('saving')) {
      return {
        emoji: '💾',
        label: t('masterplan.phase.saving'),
      };
    }

    if (eventType.includes('complete')) {
      return {
        emoji: '✓',
        label: t('masterplan.status.complete'),
      };
    }

    return {
      emoji: '🚀',
      label: t('masterplan.status.generating'),
    };
  }, [event, t]);

  // Don't render if no event
  if (!event) {
    return null;
  }

  return (
    <div
      className="w-full h-[50px] px-4 py-2 bg-gradient-to-r from-purple-900/20 to-blue-900/20 backdrop-blur-lg border border-white/10 rounded-lg cursor-pointer hover:border-white/20 transition-all"
      onClick={onClick}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onClick();
        }
      }}
      aria-label={`${phaseInfo.label} - ${percentage}% complete. Click for details`}
    >
      <div className="flex items-center justify-between h-full gap-4">
        {/* Left: Phase Indicator */}
        <div className="flex items-center gap-2 flex-shrink-0">
          <span className="text-2xl" role="img" aria-label={phaseInfo.label}>
            {phaseInfo.emoji}
          </span>
          <div className="flex flex-col">
            <span className="text-xs text-gray-400 leading-tight">
              {t('masterplan.status.generating')}
            </span>
            <span className="text-sm font-semibold text-white leading-tight">
              {phaseInfo.label}
            </span>
          </div>
        </div>

        {/* Center: Progress Bar */}
        <div className="flex-1 flex items-center gap-3 min-w-0">
          <div className="flex-1 h-2 bg-white/10 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-purple-600 to-blue-600 transition-all duration-500 ease-out"
              style={{ width: `${Math.min(100, Math.max(0, percentage))}%` }}
              role="progressbar"
              aria-valuenow={percentage}
              aria-valuemin={0}
              aria-valuemax={100}
            />
          </div>
          <span className="text-sm font-bold text-white flex-shrink-0 w-12 text-right">
            {percentage}%
          </span>
        </div>

        {/* Right: Time Remaining & Token Info */}
        <div className="flex items-center gap-4 flex-shrink-0 text-sm text-gray-400">
          {/* Time Remaining */}
          {timeRemaining > 0 && (
            <div className="flex items-center gap-1">
              <FiClock size={14} />
              <span>{t('masterplan.status.timeRemaining', { seconds: timeRemaining })}</span>
            </div>
          )}

          {/* Token Progress */}
          {tokensReceived > 0 && estimatedTotal > 0 && (
            <div className="hidden md:flex items-center gap-1">
              <FiZap size={14} />
              <span>{tokensReceived} / {estimatedTotal}</span>
            </div>
          )}
        </div>
      </div>

      {/* Hover hint */}
      <div className="absolute bottom-[-8px] left-1/2 transform -translate-x-1/2 opacity-0 group-hover:opacity-100 transition-opacity">
        <span className="text-xs text-gray-500">
          {t('masterplan.buttons.expand')}
        </span>
      </div>
    </div>
  );
};

export default InlineProgressHeader;
