/**
 * MasterPlanProgressModal - Full-screen modal for MasterPlan generation progress
 *
 * Displays real-time progress tracking, detailed statistics, phase timeline,
 * error handling, and completion summary in a responsive layout.
 *
 * Follows ReviewModal.tsx pattern for consistency with existing codebase.
 *
 * @example
 * ```tsx
 * <MasterPlanProgressModal
 *   event={masterPlanProgress}
 *   open={modalOpen}
 *   onClose={() => setModalOpen(false)}
 * />
 * ```
 */

import React, { useEffect, useCallback } from 'react';
import { FiX } from 'react-icons/fi';
import { GlassCard, GlassButton } from '../design-system';
import { useTranslation } from '../../i18n';
import type { MasterPlanProgressModalProps } from '../../types/masterplan';

// Placeholder imports for components to be created
// These will be implemented in subsequent tasks
const ProgressMetrics = React.lazy(() => import('./ProgressMetrics'));
const ProgressTimeline = React.lazy(() => import('./ProgressTimeline'));
const ErrorPanel = React.lazy(() => import('./ErrorPanel'));
const FinalSummary = React.lazy(() => import('./FinalSummary'));

/**
 * MasterPlanProgressModal component
 */
const MasterPlanProgressModal: React.FC<MasterPlanProgressModalProps> = ({
  event,
  open,
  onClose,
  // masterplanId,
}) => {
  const { t } = useTranslation();

  // Extract state from event (will be improved when hook is created)
  const isComplete = event?.event === 'masterplan_generation_complete';
  const isError = event?.event === 'generation_error';

  // Handle escape key
  const handleEscapeKey = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === 'Escape' && open) {
        onClose();
      }
    },
    [open, onClose]
  );

  // Setup keyboard listeners and prevent body scroll
  useEffect(() => {
    if (open) {
      document.addEventListener('keydown', handleEscapeKey);
      // Prevent body scroll when modal is open
      document.body.style.overflow = 'hidden';
    }

    return () => {
      document.removeEventListener('keydown', handleEscapeKey);
      document.body.style.overflow = 'unset';
    };
  }, [open, handleEscapeKey]);

  // Handle backdrop click
  const handleBackdropClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  // Handle retry (placeholder - will be implemented with hook)
  const handleRetry = useCallback(async () => {
    console.log('Retry generation triggered');
    // TODO: Implement retry logic in Task Group 5
  }, []);

  // Handle view details (placeholder)
  const handleViewDetails = useCallback(() => {
    console.log('View details clicked');
    // TODO: Navigate to MasterPlan details page
  }, []);

  // Handle start execution (placeholder)
  const handleStartExecution = useCallback(() => {
    console.log('Start execution clicked');
    // TODO: Navigate to execution flow
  }, []);

  // Don't render if not open or no event
  if (!open || !event) {
    return null;
  }

  return (
    <div
      className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4"
      onClick={handleBackdropClick}
      role="dialog"
      aria-modal="true"
      aria-labelledby="masterplan-modal-title"
      aria-describedby="masterplan-modal-description"
    >
      <GlassCard className="w-11/12 max-w-5xl max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-white/10">
          <div>
            <h2
              id="masterplan-modal-title"
              className="text-2xl font-bold text-white"
            >
              {t('masterplan.title')}
            </h2>
            <p
              id="masterplan-modal-description"
              className="text-sm text-gray-400 mt-1"
            >
              {isComplete
                ? t('masterplan.status.complete')
                : isError
                ? t('masterplan.status.failed')
                : t('masterplan.status.generating')}
            </p>
          </div>
          <GlassButton
            variant="ghost"
            size="sm"
            onClick={onClose}
            aria-label={t('masterplan.accessibility.closeModal')}
          >
            <FiX size={24} />
          </GlassButton>
        </div>

        {/* Body - Scrollable content */}
        <div
          className="flex-1 overflow-auto p-6"
          style={{ maxHeight: 'calc(100vh - 300px)' }}
        >
          {/* Error state */}
          {isError && (
            <React.Suspense fallback={<div className="animate-pulse">Loading...</div>}>
              <ErrorPanel
                error={{
                  message: event.data?.message || 'Unknown error',
                  code: event.data?.code || 'UNKNOWN',
                  details: event.data?.details,
                  stackTrace: event.data?.stackTrace,
                }}
                onRetry={handleRetry}
                isRetrying={false}
              />
            </React.Suspense>
          )}

          {/* Success/Complete state */}
          {isComplete && (
            <React.Suspense fallback={<div className="animate-pulse">Loading...</div>}>
              <FinalSummary
                stats={{
                  totalTokens: event.data?.total_tokens || 0,
                  totalCost: event.data?.total_cost || 0,
                  totalDuration: event.data?.total_duration || 0,
                  entities: {
                    boundedContexts: event.data?.bounded_contexts || 0,
                    aggregates: event.data?.aggregates || 0,
                    entities: event.data?.entities || 0,
                  },
                  phases: {
                    phases: event.data?.total_phases || 0,
                    milestones: event.data?.total_milestones || 0,
                    tasks: event.data?.total_tasks || 0,
                  },
                }}
                architectureStyle={event.data?.architecture_style}
                techStack={event.data?.tech_stack}
                onViewDetails={handleViewDetails}
                onStartExecution={handleStartExecution}
              />
            </React.Suspense>
          )}

          {/* In-progress state */}
          {!isError && !isComplete && (
            <div className="space-y-6">
              {/* Progress Timeline */}
              <React.Suspense fallback={<div className="animate-pulse">Loading timeline...</div>}>
                <ProgressTimeline
                  phases={[
                    {
                      name: 'discovery',
                      status: 'completed',
                      icon: '✓',
                      label: t('masterplan.phase.discovery'),
                    },
                    {
                      name: 'parsing',
                      status: 'in_progress',
                      icon: '⚙️',
                      label: t('masterplan.phase.parsing'),
                    },
                    {
                      name: 'validation',
                      status: 'pending',
                      icon: '⏳',
                      label: t('masterplan.phase.validation'),
                    },
                    {
                      name: 'saving',
                      status: 'pending',
                      icon: '⏳',
                      label: t('masterplan.phase.saving'),
                    },
                  ]}
                  currentPhase="parsing"
                  animateActive={true}
                />
              </React.Suspense>

              {/* Progress Metrics */}
              <React.Suspense fallback={<div className="animate-pulse">Loading metrics...</div>}>
                <ProgressMetrics
                  tokensUsed={event.data?.tokens_received || 0}
                  estimatedTokens={event.data?.estimated_total || 0}
                  cost={event.data?.cost || 0}
                  duration={event.data?.elapsed_seconds || 0}
                  estimatedDuration={event.data?.estimated_duration || 0}
                  entities={{
                    boundedContexts: event.data?.bounded_contexts || 0,
                    aggregates: event.data?.aggregates || 0,
                    entities: event.data?.entities || 0,
                    phases: event.data?.phases || 0,
                    milestones: event.data?.milestones || 0,
                    tasks: event.data?.tasks || 0,
                  }}
                  isComplete={false}
                />
              </React.Suspense>
            </div>
          )}
        </div>

        {/* Footer - Action buttons (conditional) */}
        {isComplete && (
          <div className="p-6 border-t border-white/10">
            <div className="flex items-center justify-end gap-3">
              <GlassButton variant="ghost" onClick={onClose}>
                {t('masterplan.buttons.close')}
              </GlassButton>
              <GlassButton variant="secondary" onClick={handleViewDetails}>
                {t('masterplan.buttons.viewDetails')}
              </GlassButton>
              <GlassButton variant="primary" onClick={handleStartExecution}>
                {t('masterplan.buttons.startExecution')}
              </GlassButton>
            </div>
          </div>
        )}
      </GlassCard>
    </div>
  );
};

export default MasterPlanProgressModal;
