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

import React, { useEffect, useCallback, useRef, useState } from 'react';
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

  // Extract session ID from event with fallback chain
  // Priority: propMasterplanId > masterplan_id > session_id > discovery_id
  const eventData = event?.data || {}

  // Use state to initialize sessionId from discovery session_id or prop
  // CRITICAL: sessionId must NEVER change to masterplan_id - it must remain constant
  // throughout both discovery and masterplan phases for event filtering to work correctly
  const [sessionId, setSessionId] = useState<string | undefined>(propMasterplanId)

  // Initialize sessionId from discovery_session_id if not already set
  useEffect(() => {
    // Only set sessionId if we don't have one yet (first initialization only)
    if (!sessionId && eventData?.session_id) {
      console.log('[MasterPlanProgressModal] Initializing sessionId from discovery event:', {
        sessionId: eventData.session_id
      })
      setSessionId(eventData.session_id)
    }
  }, [eventData?.session_id, sessionId])

  console.log('[MasterPlanProgressModal] Current sessionId:', {
    sessionId,
    propMasterplanId,
    eventMasterplanId: eventData.masterplan_id,
    eventSessionId: eventData.session_id,
    eventDiscoveryId: eventData.discovery_id,
  });

  // Track joined rooms to avoid duplicate JOIN/LEAVE calls
  const joinedRoomsRef = useRef<Set<string>>(new Set());

  // Backup: Join rooms if not already joined (useChat should have done this already)
  // This is a safety measure in case the modal is opened without going through the normal flow
  useEffect(() => {
    if (open && sessionId) {
      if (!joinedRoomsRef.current.has(sessionId)) {
        console.log('[MasterPlanProgressModal] Backup join for rooms:', sessionId);
        wsService.send('join_discovery', { session_id: sessionId });
        wsService.send('join_masterplan', { masterplan_id: sessionId });
        joinedRoomsRef.current.add(sessionId);
      }
    } else if (!open && sessionId) {
      // Modal is closing, leave all rooms
      console.log('[MasterPlanProgressModal] Modal closed, leaving rooms:', sessionId);
      wsService.send('leave_discovery', { session_id: sessionId });
      wsService.send('leave_masterplan', { masterplan_id: sessionId });
      joinedRoomsRef.current.delete(sessionId);
    }
  }, [open, sessionId]);

  // Get real-time progress from hook
  // By this point, useChat should have already joined the discovery room
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
