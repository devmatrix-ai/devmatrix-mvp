/**
 * FinalSummary - Completion screen with success indicator and actions
 *
 * Displays generation completion with:
 * - Success checkmark animation
 * - Final statistics (tokens, cost, duration)
 * - Detailed breakdown (phases, architecture, tech stack)
 * - Action buttons (View Details, Start Execution, Export)
 *
 * @example
 * ```tsx
 * <FinalSummary
 *   stats={{
 *     totalTokens: 25000,
 *     totalCost: 0.40,
 *     totalDuration: 135,
 *     entities: { boundedContexts: 5, aggregates: 12, entities: 45 },
 *     phases: { phases: 3, milestones: 17, tasks: 120 }
 *   }}
 *   architectureStyle="DDD"
 *   techStack={['React', 'FastAPI', 'PostgreSQL']}
 *   onViewDetails={handleViewDetails}
 *   onStartExecution={handleStartExecution}
 * />
 * ```
 */

import React from 'react';
import { FiCheckCircle, FiClock, FiDollarSign, FiLayers } from 'react-icons/fi';
import { GlassCard, GlassButton } from '../design-system';
import { useTranslation } from '../../i18n';
import type { FinalSummaryProps } from '../../types/masterplan';

/**
 * FinalSummary component
 */
const FinalSummary: React.FC<FinalSummaryProps> = ({
  stats,
  architectureStyle,
  techStack,
  onViewDetails,
  onStartExecution,
  onExport,
}) => {
  const { t } = useTranslation();

  // Format numbers
  const formatNumber = (num: number): string => {
    return new Intl.NumberFormat('en-US').format(num);
  };

  // Format cost
  const formatCost = (amount: number): string => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 4,
    }).format(amount);
  };

  return (
    <div className="space-y-6">
      {/* Success Header */}
      <div className="text-center">
        <div className="inline-flex items-center justify-center w-24 h-24 rounded-full bg-green-500/20 mb-4 animate-checkBounce">
          <FiCheckCircle className="text-green-400" size={48} />
        </div>
        <h2 className="text-3xl font-bold text-white mb-2">
          {t('masterplan.summary.title')}
        </h2>
        <p className="text-gray-400">
          {t('masterplan.summary.subtitle')}
        </p>
      </div>

      {/* Total Statistics */}
      <GlassCard>
        <h3 className="text-lg font-semibold text-white mb-4">
          {t('masterplan.summary.totalStats')}
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Total Tokens */}
          <div className="text-center p-4 bg-white/5 rounded-lg">
            <FiLayers className="mx-auto text-blue-400 mb-2" size={24} />
            <p className="text-sm text-gray-400 mb-1">
              {t('masterplan.summary.totalTokens')}
            </p>
            <p className="text-2xl font-bold text-white">
              {formatNumber(stats.totalTokens)}
            </p>
          </div>

          {/* Total Cost */}
          <div className="text-center p-4 bg-white/5 rounded-lg">
            <FiDollarSign className="mx-auto text-green-400 mb-2" size={24} />
            <p className="text-sm text-gray-400 mb-1">
              {t('masterplan.summary.totalCost')}
            </p>
            <p className="text-2xl font-bold text-green-400">
              {formatCost(stats.totalCost)}
            </p>
          </div>

          {/* Total Duration */}
          <div className="text-center p-4 bg-white/5 rounded-lg">
            <FiClock className="mx-auto text-purple-400 mb-2" size={24} />
            <p className="text-sm text-gray-400 mb-1">
              {t('masterplan.summary.totalDuration')}
            </p>
            <p className="text-2xl font-bold text-white">
              {stats.totalDuration}s
            </p>
          </div>
        </div>
      </GlassCard>

      {/* Entity Summary */}
      <GlassCard>
        <h3 className="text-lg font-semibold text-white mb-4">
          {t('masterplan.summary.entitySummary')}
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          <div className="text-center">
            <p className="text-3xl font-bold text-white">{stats.entities.boundedContexts}</p>
            <p className="text-sm text-gray-400">{t('masterplan.metrics.boundedContexts')}</p>
          </div>
          <div className="text-center">
            <p className="text-3xl font-bold text-white">{stats.entities.aggregates}</p>
            <p className="text-sm text-gray-400">{t('masterplan.metrics.aggregates')}</p>
          </div>
          <div className="text-center">
            <p className="text-3xl font-bold text-white">{stats.entities.entities}</p>
            <p className="text-sm text-gray-400">{t('masterplan.metrics.entities')}</p>
          </div>
          <div className="text-center">
            <p className="text-3xl font-bold text-purple-400">{stats.phases.phases}</p>
            <p className="text-sm text-gray-400">{t('masterplan.metrics.phases')}</p>
          </div>
          <div className="text-center">
            <p className="text-3xl font-bold text-purple-400">{stats.phases.milestones}</p>
            <p className="text-sm text-gray-400">{t('masterplan.metrics.milestones')}</p>
          </div>
          <div className="text-center">
            <p className="text-3xl font-bold text-purple-400">{stats.phases.tasks}</p>
            <p className="text-sm text-gray-400">{t('masterplan.metrics.tasks')}</p>
          </div>
        </div>
      </GlassCard>

      {/* Detailed Breakdown */}
      {(architectureStyle || (techStack && techStack.length > 0)) && (
        <GlassCard>
          <h3 className="text-lg font-semibold text-white mb-4">
            {t('masterplan.summary.detailedBreakdown')}
          </h3>

          {/* Architecture Style */}
          {architectureStyle && (
            <div className="mb-4">
              <p className="text-sm text-gray-400 mb-1">
                {t('masterplan.summary.architectureStyle')}
              </p>
              <p className="text-lg font-semibold text-white">{architectureStyle}</p>
            </div>
          )}

          {/* Tech Stack */}
          {techStack && techStack.length > 0 && (
            <div>
              <p className="text-sm text-gray-400 mb-2">
                {t('masterplan.summary.techStack')}
              </p>
              <div className="flex flex-wrap gap-2">
                {techStack.map((tech, index) => (
                  <span
                    key={index}
                    className="px-3 py-1 bg-purple-500/20 text-purple-300 border border-purple-500/30 rounded-full text-sm font-medium"
                  >
                    {tech}
                  </span>
                ))}
              </div>
            </div>
          )}
        </GlassCard>
      )}

      {/* Action Buttons */}
      <div className="flex flex-col sm:flex-row items-center gap-3">
        <GlassButton
          variant="primary"
          size="lg"
          onClick={onViewDetails}
          className="w-full sm:w-auto"
        >
          {t('masterplan.buttons.viewDetails')}
        </GlassButton>
        <GlassButton
          variant="secondary"
          size="lg"
          onClick={onStartExecution}
          className="w-full sm:w-auto"
        >
          {t('masterplan.buttons.startExecution')}
        </GlassButton>
        {onExport && (
          <GlassButton
            variant="ghost"
            size="lg"
            onClick={onExport}
            className="w-full sm:w-auto"
          >
            {t('masterplan.buttons.export')}
          </GlassButton>
        )}
      </div>

      {/* Success Announcement for Screen Readers */}
      <div
        role="status"
        aria-live="polite"
        className="sr-only"
      >
        {t('masterplan.accessibility.completionAnnouncement')}
      </div>
    </div>
  );
};

export default FinalSummary;
