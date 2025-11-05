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
import { useMasterPlanProgress } from '../../hooks/useMasterPlanProgress';
import { useMasterPlanError } from '../../stores/masterplanStore';
import { wsService } from '../../services/websocket';
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
  masterplanId: propMasterplanId,
}) => {
  const { t } = useTranslation();

  // Extract session ID from event to track generation
  // During Discovery phase: use session_id from discovery_generation_start
  // During MasterPlan phase: use masterplan_id if available, fall back to session_id
  const eventData = event?.data || {}
  const sessionId = propMasterplanId ||
                    eventData.masterplan_id ||
                    eventData.discovery_id ||
                    eventData.session_id;

  console.log('[MasterPlanProgressModal] Extracted session/masterplan ID:', {
    propMasterplanId,
    eventMasterplanId: eventData.masterplan_id,
    eventDiscoveryId: eventData.discovery_id,
    eventSessionId: eventData.session_id,
    finalSessionId: sessionId,
    eventType: event?.event,
    fullEventData: JSON.stringify(eventData),
  });

  // Get real-time progress from hook
  const {
    state: progressState,
    phases,
    handleRetry,
    clearError,
    isLoading,
  } = useMasterPlanProgress(sessionId);

  // Debug logging
  React.useEffect(() => {
    if (open) {
      console.log('[MasterPlanProgressModal] Modal opened with progress state:', {
        isOpen: open,
        sessionId,
        currentPhase: progressState.currentPhase,
        percentage: progressState.percentage,
        tokensReceived: progressState.tokensReceived,
        isComplete: progressState.isComplete,
        isLoading,
      });
    }
  }, [open, progressState, sessionId, isLoading]);

  // Get error from store
  const storeError = useMasterPlanError();

  // Determine modal state from progress state
  const isComplete = progressState.isComplete;
  const isError = storeError !== null;

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

  // Join masterplan room to receive real-time events
  useEffect(() => {
    if (open && masterplanId) {
      console.log('[MasterPlanProgressModal] Joining masterplan room:', masterplanId);
      wsService.send('join_masterplan', { masterplan_id: masterplanId });

      // Return cleanup function to leave room when modal closes
      return () => {
        console.log('[MasterPlanProgressModal] Leaving masterplan room:', masterplanId);
        wsService.send('leave_masterplan', { masterplan_id: masterplanId });
      };
    }
  }, [open, masterplanId]);

  // Handle backdrop click
  const handleBackdropClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  // Handle retry using hook's retry function
  const onRetry = useCallback(async () => {
    await handleRetry();
    clearError();
  }, [handleRetry, clearError]);

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

  // Don't render if not open
  if (!open) {
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
          {isError && storeError && (
            <React.Suspense fallback={<div className="animate-pulse">Loading...</div>}>
              <ErrorPanel
                error={{
                  message: storeError,
                  code: 'GENERATION_ERROR',
                  details: { error: storeError },
                }}
                onRetry={onRetry}
                isRetrying={isLoading}
              />
            </React.Suspense>
          )}

          {/* Success/Complete state */}
          {isComplete && (
            <React.Suspense fallback={<div className="animate-pulse">Loading...</div>}>
              <FinalSummary
                stats={{
                  totalTokens: progressState.tokensReceived,
                  totalCost: progressState.cost,
                  totalDuration: progressState.elapsedSeconds,
                  entities: {
                    boundedContexts: progressState.boundedContexts,
                    aggregates: progressState.aggregates,
                    entities: progressState.entities,
                  },
                  phases: {
                    phases: progressState.phasesFound,
                    milestones: progressState.milestonesFound,
                    tasks: progressState.tasksFound,
                  },
                }}
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
                  phases={phases}
                  currentPhase={progressState.currentPhase}
                  animateActive={true}
                />
              </React.Suspense>

              {/* Progress Metrics */}
              <React.Suspense fallback={<div className="animate-pulse">Loading metrics...</div>}>
                <ProgressMetrics
                  tokensUsed={progressState.tokensReceived}
                  estimatedTokens={progressState.estimatedTotalTokens}
                  cost={progressState.cost}
                  duration={progressState.elapsedSeconds}
                  estimatedDuration={progressState.estimatedDurationSeconds}
                  entities={{
                    boundedContexts: progressState.boundedContexts,
                    aggregates: progressState.aggregates,
                    entities: progressState.entities,
                    phases: progressState.phasesFound,
                    milestones: progressState.milestonesFound,
                    tasks: progressState.tasksFound,
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
