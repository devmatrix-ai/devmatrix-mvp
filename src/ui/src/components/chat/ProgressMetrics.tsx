/**
 * ProgressMetrics - Display primary, secondary, and tertiary statistics
 *
 * Shows generation metrics in three collapsible levels:
 * - Primary: Always visible (phase, percentage, time)
 * - Secondary: Collapsible (tokens, cost, entities)
 * - Tertiary: Expandable (detailed breakdown, raw JSON)
 *
 * @example
 * ```tsx
 * <ProgressMetrics
 *   tokensUsed={8500}
 *   estimatedTokens={17000}
 *   cost={0.25}
 *   duration={65}
 *   estimatedDuration={135}
 *   entities={{ boundedContexts: 5, aggregates: 12, entities: 45, phases: 3, milestones: 17, tasks: 120 }}
 *   isComplete={false}
 * />
 * ```
 */

import React, { useState } from 'react';
import { FiChevronDown, FiChevronUp } from 'react-icons/fi';
import { GlassCard } from '../design-system';
import { useTranslation } from '../../i18n';
import type { ProgressMetricsProps } from '../../types/masterplan';

/**
 * ProgressMetrics component
 */
const ProgressMetrics: React.FC<ProgressMetricsProps> = ({
  tokensUsed,
  estimatedTokens,
  cost,
  duration,
  estimatedDuration,
  entities,
  isComplete,
}) => {
  const { t } = useTranslation();
  const [secondaryExpanded, setSecondaryExpanded] = useState(true);
  const [tertiaryExpanded, setTertiaryExpanded] = useState(false);

  // Calculate progress percentage
  const percentage = estimatedTokens > 0
    ? Math.min(100, Math.round((tokensUsed / estimatedTokens) * 100))
    : 0;

  // Calculate time remaining
  const timeRemaining = Math.max(0, estimatedDuration - duration);

  // Format numbers with commas
  const formatNumber = (num: number): string => {
    return new Intl.NumberFormat('en-US').format(num);
  };

  // Format cost as USD
  const formatCost = (amount: number): string => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 4,
    }).format(amount);
  };

  return (
    <div className="space-y-4">
      {/* Primary Metrics - Always Visible */}
      <GlassCard className="space-y-4">
        <h3 className="text-lg font-semibold text-white">
          {t('masterplan.metrics.primary')}
        </h3>

        {/* Progress Bar */}
        <div className="space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span className="text-gray-300">{t('masterplan.metrics.progress')}</span>
            <span className="text-white font-bold">{percentage}%</span>
          </div>
          <div
            className="w-full h-3 bg-white/10 rounded-full overflow-hidden"
            role="progressbar"
            aria-valuenow={percentage}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-label={t('masterplan.accessibility.progressBar', { percentage })}
          >
            <div
              className="h-full bg-gradient-to-r from-purple-600 to-blue-600 transition-all duration-500 ease-out"
              style={{ width: `${percentage}%` }}
            />
          </div>
        </div>

        {/* Time Stats */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <p className="text-sm text-gray-400">{t('masterplan.status.elapsedTime', { seconds: duration })}</p>
            <p className="text-2xl font-bold text-white">{duration}s</p>
          </div>
          {!isComplete && (
            <div>
              <p className="text-sm text-gray-400">{t('masterplan.status.timeRemaining', { seconds: timeRemaining })}</p>
              <p className="text-2xl font-bold text-white">{timeRemaining}s</p>
            </div>
          )}
        </div>
      </GlassCard>

      {/* Secondary Metrics - Collapsible */}
      <GlassCard>
        <button
          className="w-full flex items-center justify-between text-left"
          onClick={() => setSecondaryExpanded(!secondaryExpanded)}
          aria-expanded={secondaryExpanded}
          aria-controls="secondary-metrics"
        >
          <h3 className="text-lg font-semibold text-white">
            {t('masterplan.metrics.secondary')}
          </h3>
          {secondaryExpanded ? (
            <FiChevronUp className="text-white" size={20} />
          ) : (
            <FiChevronDown className="text-white" size={20} />
          )}
        </button>

        {secondaryExpanded && (
          <div id="secondary-metrics" className="mt-4 space-y-4">
            {/* Tokens */}
            <div className="space-y-1">
              <p className="text-sm text-gray-400">{t('masterplan.metrics.tokens')}</p>
              <p className="text-xl font-bold text-white">
                {formatNumber(tokensUsed)} / {formatNumber(estimatedTokens)}
              </p>
              <div className="w-full h-2 bg-white/10 rounded-full overflow-hidden">
                <div
                  className="h-full bg-blue-500 transition-all duration-300"
                  style={{ width: `${percentage}%` }}
                />
              </div>
            </div>

            {/* Cost */}
            <div className="space-y-1">
              <p className="text-sm text-gray-400">{t('masterplan.metrics.cost')}</p>
              <p className="text-xl font-bold text-green-400">{formatCost(cost)}</p>
            </div>

            {/* Entity Counts Grid */}
            <div className="grid grid-cols-3 gap-4 pt-4 border-t border-white/10">
              <div className="text-center">
                <p className="text-2xl font-bold text-white">{entities.boundedContexts}</p>
                <p className="text-xs text-gray-400">{t('masterplan.metrics.boundedContexts')}</p>
              </div>
              <div className="text-center">
                <p className="text-2xl font-bold text-white">{entities.aggregates}</p>
                <p className="text-xs text-gray-400">{t('masterplan.metrics.aggregates')}</p>
              </div>
              <div className="text-center">
                <p className="text-2xl font-bold text-white">{entities.entities}</p>
                <p className="text-xs text-gray-400">{t('masterplan.metrics.entities')}</p>
              </div>
            </div>

            {/* Phase/Milestone/Task Counts */}
            <div className="grid grid-cols-3 gap-4 pt-4 border-t border-white/10">
              <div className="text-center">
                <p className="text-2xl font-bold text-purple-400">{entities.phases}</p>
                <p className="text-xs text-gray-400">{t('masterplan.metrics.phases')}</p>
              </div>
              <div className="text-center">
                <p className="text-2xl font-bold text-purple-400">{entities.milestones}</p>
                <p className="text-xs text-gray-400">{t('masterplan.metrics.milestones')}</p>
              </div>
              <div className="text-center">
                <p className="text-2xl font-bold text-purple-400">{entities.tasks}</p>
                <p className="text-xs text-gray-400">{t('masterplan.metrics.tasks')}</p>
              </div>
            </div>
          </div>
        )}
      </GlassCard>

      {/* Tertiary Metrics - Expandable (Debugging) */}
      <GlassCard>
        <button
          className="w-full flex items-center justify-between text-left"
          onClick={() => setTertiaryExpanded(!tertiaryExpanded)}
          aria-expanded={tertiaryExpanded}
          aria-controls="tertiary-metrics"
        >
          <h3 className="text-lg font-semibold text-white">
            {t('masterplan.metrics.tertiary')}
          </h3>
          {tertiaryExpanded ? (
            <FiChevronUp className="text-white" size={20} />
          ) : (
            <FiChevronDown className="text-white" size={20} />
          )}
        </button>

        {tertiaryExpanded && (
          <div id="tertiary-metrics" className="mt-4 space-y-4">
            {/* Detailed Breakdown */}
            <div className="space-y-2">
              <h4 className="text-sm font-semibold text-gray-300">
                {t('masterplan.metrics.breakdown')}
              </h4>
              <div className="bg-black/30 rounded-lg p-4 space-y-2 text-sm font-mono">
                <div className="flex justify-between">
                  <span className="text-gray-400">Tokens:</span>
                  <span className="text-white">{formatNumber(tokensUsed)} / {formatNumber(estimatedTokens)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Cost:</span>
                  <span className="text-green-400">{formatCost(cost)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Duration:</span>
                  <span className="text-white">{duration}s / {estimatedDuration}s</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Percentage:</span>
                  <span className="text-white">{percentage}%</span>
                </div>
              </div>
            </div>

            {/* Raw JSON Data */}
            <div className="space-y-2">
              <h4 className="text-sm font-semibold text-gray-300">
                {t('masterplan.metrics.rawData')}
              </h4>
              <div className="bg-black/30 rounded-lg p-4 max-h-64 overflow-auto">
                <pre className="text-xs text-gray-300 font-mono whitespace-pre-wrap">
                  {JSON.stringify(
                    {
                      tokensUsed,
                      estimatedTokens,
                      cost,
                      duration,
                      estimatedDuration,
                      percentage,
                      timeRemaining,
                      entities,
                      isComplete,
                    },
                    null,
                    2
                  )}
                </pre>
              </div>
            </div>
          </div>
        )}
      </GlassCard>
    </div>
  );
};

export default ProgressMetrics;
