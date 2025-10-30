/**
 * useMasterPlanProgress - Custom hook for MasterPlan progress state management
 *
 * Manages progress state from WebSocket events with:
 * - Event processing and state updates
 * - Elapsed time calculation with timer
 * - Phase tracking and status management
 * - sessionStorage persistence for page refresh recovery
 * - Error handling and retry mechanism
 *
 * @example
 * ```tsx
 * function MyComponent() {
 *   const { state, phases, handleRetry, isLoading } = useMasterPlanProgress(event);
 *
 *   return (
 *     <div>
 *       <p>Progress: {state.percentage}%</p>
 *       <p>Phase: {state.currentPhase}</p>
 *     </div>
 *   );
 * }
 * ```
 */

import { useState, useEffect, useCallback, useMemo } from 'react';
import type {
  MasterPlanProgressEvent,
  ProgressState,
  PhaseStatus,
  UseMasterPlanProgressResult,
} from '../types/masterplan';
import {
  storeMasterPlanSession,
  getMasterPlanSession,
  clearMasterPlanSession,
} from '../utils/masterplanStorage';
import { fetchMasterPlanStatus } from '../api/masterplanClient';

/**
 * Initial progress state
 */
const initialState: ProgressState = {
  tokensReceived: 0,
  estimatedTotalTokens: 0,
  percentage: 0,
  currentPhase: '',
  phasesFound: 0,
  milestonesFound: 0,
  tasksFound: 0,
  startTime: null,
  elapsedSeconds: 0,
  estimatedDurationSeconds: 0,
  isParsing: false,
  isValidating: false,
  isSaving: false,
  isComplete: false,
  cost: 0,
  boundedContexts: 0,
  aggregates: 0,
  entities: 0,
};

/**
 * useMasterPlanProgress hook
 */
export function useMasterPlanProgress(
  event: MasterPlanProgressEvent | null
): UseMasterPlanProgressResult {
  const [state, setState] = useState<ProgressState>(initialState);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  /**
   * Initialize from sessionStorage on mount
   */
  useEffect(() => {
    const initializeFromStorage = async () => {
      const stored = getMasterPlanSession();
      if (stored) {
        setSessionId(stored.masterplan_id);
        setIsLoading(true);

        try {
          // Fetch latest status from API
          const status = await fetchMasterPlanStatus(stored.masterplan_id);

          // Resume progress state
          setState((prev) => ({
            ...prev,
            tokensReceived: status.stats.tokens_used,
            estimatedTotalTokens: status.stats.estimated_tokens,
            percentage: status.progress_percentage,
            currentPhase: status.current_phase,
            boundedContexts: status.stats.entities.bounded_contexts,
            aggregates: status.stats.entities.aggregates,
            entities: status.stats.entities.entities,
            phasesFound: status.stats.entities.phases,
            milestonesFound: status.stats.entities.milestones,
            tasksFound: status.stats.entities.tasks,
            cost: status.stats.cost,
            elapsedSeconds: status.stats.duration_seconds,
            isComplete: status.is_complete,
            startTime: new Date(stored.started_at),
          }));
        } catch (error) {
          console.error('Failed to recover MasterPlan status:', error);
          // Clear stale sessionStorage on error
          clearMasterPlanSession();
          setSessionId(null);
        } finally {
          setIsLoading(false);
        }
      }
    };

    initializeFromStorage();
  }, []);

  /**
   * Process incoming WebSocket events
   */
  useEffect(() => {
    if (!event) return;

    const eventType = event.event;
    const data = event.data;

    switch (eventType) {
      case 'discovery_generation_start':
        setState((prev) => ({
          ...prev,
          startTime: new Date(),
          currentPhase: 'discovery',
          estimatedTotalTokens: data.estimated_tokens || 0,
          estimatedDurationSeconds: data.estimated_duration_seconds || 0,
        }));
        break;

      case 'discovery_tokens_progress':
        setState((prev) => ({
          ...prev,
          tokensReceived: data.tokens_received || 0,
          estimatedTotalTokens: data.estimated_total || prev.estimatedTotalTokens,
          percentage: Math.min(48, data.percentage || 0), // Cap discovery at 48%
          currentPhase: data.current_phase || 'discovery',
        }));
        break;

      case 'discovery_entity_discovered':
        setState((prev) => ({
          ...prev,
          boundedContexts: data.bounded_contexts || prev.boundedContexts,
          aggregates: data.aggregates || prev.aggregates,
          entities: data.entities || prev.entities,
        }));
        break;

      case 'discovery_parsing_complete':
        setState((prev) => ({
          ...prev,
          isParsing: false,
          percentage: 48,
          boundedContexts: data.total_bounded_contexts || prev.boundedContexts,
          aggregates: data.total_aggregates || prev.aggregates,
          entities: data.total_entities || prev.entities,
        }));
        break;

      case 'discovery_saving_start':
        setState((prev) => ({
          ...prev,
          isSaving: true,
        }));
        break;

      case 'discovery_generation_complete':
        setState((prev) => ({
          ...prev,
          isSaving: false,
          percentage: 50,
          cost: (prev.cost || 0) + (data.cost || 0),
        }));
        break;

      case 'masterplan_generation_start':
        setState((prev) => ({
          ...prev,
          currentPhase: 'parsing',
          percentage: 50,
          estimatedTotalTokens: (prev.estimatedTotalTokens || 0) + (data.estimated_tokens || 0),
          estimatedDurationSeconds:
            (prev.estimatedDurationSeconds || 0) + (data.estimated_duration_seconds || 0),
        }));

        // Store session for persistence
        if (data.masterplan_id) {
          setSessionId(data.masterplan_id);
          storeMasterPlanSession({
            masterplan_id: data.masterplan_id,
            started_at: state.startTime?.toISOString() || new Date().toISOString(),
            current_phase: 'parsing',
            progress_percentage: 50,
          });
        }
        break;

      case 'masterplan_tokens_progress':
        // Map 0-100% to 50-92.5% range
        const mappedPercentage = 50 + ((data.percentage || 0) / 100) * 42.5;
        setState((prev) => ({
          ...prev,
          tokensReceived: (prev.tokensReceived || 0) + (data.tokens_received || 0),
          percentage: Math.min(92.5, Math.round(mappedPercentage)),
          currentPhase: data.current_phase || 'parsing',
        }));
        break;

      case 'masterplan_entity_discovered':
        setState((prev) => {
          const updates: Partial<ProgressState> = {};
          const entityType = data.type;

          if (entityType === 'phase') {
            updates.phasesFound = (prev.phasesFound || 0) + (data.count || 1);
          } else if (entityType === 'milestone') {
            updates.milestonesFound = (prev.milestonesFound || 0) + (data.count || 1);
          } else if (entityType === 'task') {
            updates.tasksFound = (prev.tasksFound || 0) + (data.count || 1);
          }

          return { ...prev, ...updates };
        });
        break;

      case 'masterplan_parsing_complete':
        setState((prev) => ({
          ...prev,
          isParsing: false,
          percentage: 93,
          phasesFound: data.total_phases || prev.phasesFound,
          milestonesFound: data.total_milestones || prev.milestonesFound,
          tasksFound: data.total_tasks || prev.tasksFound,
        }));
        break;

      case 'masterplan_validation_start':
        setState((prev) => ({
          ...prev,
          isValidating: true,
          currentPhase: 'validation',
          percentage: 95,
        }));
        break;

      case 'masterplan_saving_start':
        setState((prev) => ({
          ...prev,
          isValidating: false,
          isSaving: true,
          currentPhase: 'saving',
          percentage: 97,
        }));
        break;

      case 'masterplan_generation_complete':
        setState((prev) => ({
          ...prev,
          isSaving: false,
          isComplete: true,
          percentage: 100,
          currentPhase: 'complete',
          cost: data.total_cost || prev.cost,
          phasesFound: data.total_phases || prev.phasesFound,
          milestonesFound: data.total_milestones || prev.milestonesFound,
          tasksFound: data.total_tasks || prev.tasksFound,
        }));

        // Clear sessionStorage on completion
        clearMasterPlanSession();
        setSessionId(null);
        break;

      case 'generation_error':
        setState((prev) => ({
          ...prev,
          error: {
            message: data.message || 'Unknown error',
            code: data.code || 'UNKNOWN',
            details: data.details,
            stackTrace: data.stackTrace,
            timestamp: new Date(),
            source: data.source || 'unknown',
          },
        }));

        // Clear sessionStorage on error
        clearMasterPlanSession();
        setSessionId(null);
        break;

      default:
        break;
    }
  }, [event, state.startTime]);

  /**
   * Timer for elapsed time calculation
   */
  useEffect(() => {
    if (!state.startTime || state.isComplete) return;

    const timer = setInterval(() => {
      setState((prev) => ({
        ...prev,
        elapsedSeconds: Math.floor((Date.now() - prev.startTime!.getTime()) / 1000),
      }));
    }, 1000);

    return () => clearInterval(timer);
  }, [state.startTime, state.isComplete]);

  /**
   * Generate phase statuses from current state
   */
  const phases: PhaseStatus[] = useMemo(() => {
    const getPhaseStatus = (phaseName: string): PhaseStatus['status'] => {
      if (state.currentPhase === phaseName) {
        return 'in_progress';
      }

      const phaseOrder = ['discovery', 'parsing', 'validation', 'saving'];
      const currentIndex = phaseOrder.indexOf(state.currentPhase);
      const targetIndex = phaseOrder.indexOf(phaseName);

      if (currentIndex > targetIndex) {
        return 'completed';
      }

      return 'pending';
    };

    return [
      {
        name: 'discovery',
        status: getPhaseStatus('discovery'),
        icon: '🔍',
        label: 'Analyzing DDD Requirements',
      },
      {
        name: 'parsing',
        status: getPhaseStatus('parsing'),
        icon: '⚙️',
        label: 'Generating Plan Structure',
      },
      {
        name: 'validation',
        status: getPhaseStatus('validation'),
        icon: '✅',
        label: 'Validating Dependencies',
      },
      {
        name: 'saving',
        status: getPhaseStatus('saving'),
        icon: '💾',
        label: 'Saving to Database',
      },
    ];
  }, [state.currentPhase]);

  /**
   * Clear error state
   */
  const clearError = useCallback(() => {
    setState((prev) => ({
      ...prev,
      error: undefined,
    }));
  }, []);

  /**
   * Handle retry generation
   */
  const handleRetry = useCallback(async () => {
    // Clear error state
    clearError();

    // Reset state to initial
    setState(initialState);

    // Clear sessionStorage
    clearMasterPlanSession();
    setSessionId(null);

    // Note: Re-triggering /masterplan command should be handled by parent component
    // This hook only manages state, not WebSocket communication
    console.log('Retry triggered - parent component should re-send /masterplan command');
  }, [clearError]);

  return {
    state,
    sessionId,
    phases,
    handleRetry,
    clearError,
    isLoading,
  };
}

export default useMasterPlanProgress;
