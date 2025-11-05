/**
 * useMasterPlanProgress Hook - State Machine for Progress Tracking
 *
 * Transforms WebSocket events into progress tracking through:
 * - ProgressState management (tokens, percentage, phase tracking)
 * - Phase timeline progression (discovery, parsing, validation, saving)
 * - Real-time metrics from WebSocket events
 * - Error state and retry functionality
 *
 * @since Nov 4, 2025
 * @version 1.0
 */

import { useEffect, useCallback, useRef, useState } from 'react'
import { useWebSocketContext } from '../providers/WebSocketProvider'
import { useMasterPlanStore } from '../stores/masterplanStore'
import type {
  ProgressState,
  PhaseStatus,
  PhaseName,
  PhaseStatusType,
  UseMasterPlanProgressResult,
} from '../types/masterplan'

/**
 * Initial progress state
 */
const initialProgressState: ProgressState = {
  tokensReceived: 0,
  estimatedTotalTokens: 0,
  percentage: 0,
  currentPhase: 'idle',
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
}

/**
 * Phase definitions for MasterPlan generation
 */
const PHASES_DEFINITION: PhaseStatus[] = [
  {
    name: 'discovery',
    status: 'pending',
    icon: '📡',
    label: 'Discovery phase',
  },
  {
    name: 'parsing',
    status: 'pending',
    icon: '📝',
    label: 'Parsing phase',
  },
  {
    name: 'validation',
    status: 'pending',
    icon: '✓',
    label: 'Validation phase',
  },
  {
    name: 'saving',
    status: 'pending',
    icon: '💾',
    label: 'Saving phase',
  },
]

/**
 * Hook for tracking MasterPlan generation progress through WebSocket events
 *
 * Manages state machine transitions based on WebSocket events and
 * persists progress to Zustand store for centralized state management.
 *
 * @param sessionId - Optional session ID to track specific generation
 * @returns Progress state, phases, and control functions
 */
export function useMasterPlanProgress(
  sessionId?: string
): UseMasterPlanProgressResult {
  // WebSocket hook for event subscription (singleton from provider)
  const { events, latestEvent } = useWebSocketContext()

  // Store access for persistence
  const {
    currentMasterPlanId,
    updateProgress,
    setPhases,
    updateMetrics,
    clearError: clearStoreError,
  } = useMasterPlanStore()

  // Local state for progress tracking
  const [progressState, setProgressState] = useState<ProgressState>(initialProgressState)
  const [phases, setLocalPhases] = useState<PhaseStatus[]>(PHASES_DEFINITION)

  // Refs for tracking timing without re-renders
  const phaseTimesRef = useRef<Record<PhaseName, { start: number; end?: number }>>({
    discovery: { start: 0 },
    parsing: { start: 0 },
    validation: { start: 0 },
    saving: { start: 0 },
  })
  const startTimeRef = useRef<number | null>(null)
  const debounceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const lastProcessedEventRef = useRef<string>('')

  /**
   * Update single phase status and timing
   */
  const updatePhaseStatus = useCallback(
    (phaseName: PhaseName, status: PhaseStatusType, startTime?: number, endTime?: number) => {
      setLocalPhases((prevPhases) =>
        prevPhases.map((phase) =>
          phase.name === phaseName
            ? {
                ...phase,
                status,
                startTime: startTime ? new Date(startTime) : phase.startTime,
                endTime: endTime ? new Date(endTime) : phase.endTime,
                duration:
                  startTime && endTime ? Math.round((endTime - startTime) / 1000) : phase.duration,
              }
            : phase
        )
      )
    },
    []
  )

  /**
   * Calculate elapsed seconds since generation start
   */
  const calculateElapsedSeconds = useCallback(() => {
    if (!startTimeRef.current) return 0
    return Math.round((Date.now() - startTimeRef.current) / 1000)
  }, [])

  /**
   * Handle WebSocket events and update progress state machine
   */
  useEffect(() => {
    // Filter events for this session if sessionId is provided
    // If sessionId is not provided, use all events (useful during generation before masterplanId exists)
    let eventToProcess = latestEvent

    if (sessionId && events.length > 0) {
      // Find the latest event that matches this session
      const sessionEvents = events.filter(
        (e) => e.sessionId === sessionId || e.data?.session_id === sessionId
      )
      eventToProcess = sessionEvents[sessionEvents.length - 1] || null

      console.log('[useMasterPlanProgress] Filtering events for session:', {
        sessionId,
        totalEvents: events.length,
        filteredEvents: sessionEvents.length,
        latestEvent: eventToProcess?.type,
      })
    } else if (events.length > 0) {
      // No sessionId provided - use latest event from any session (during generation)
      console.log('[useMasterPlanProgress] No sessionId filter, using latest event:', {
        latestEventType: latestEvent?.type,
        eventBufferSize: events.length,
      })
    }

    if (!eventToProcess) return

    // Create unique key for this event to avoid duplicate processing
    const eventKey = `${eventToProcess.type}:${eventToProcess.timestamp}`
    if (eventKey === lastProcessedEventRef.current) {
      return
    }
    lastProcessedEventRef.current = eventKey

    const event = eventToProcess
    const eventData = event.data || {}

    // Debounce metrics updates to prevent excessive renders
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current)
    }

    debounceTimerRef.current = setTimeout(() => {
      // Handle different event types
      switch (event.type) {
        case 'masterplan_generation_start': {
          // Continue progress from discovery phase, don't reset
          setProgressState((prev) => ({
            ...prev,
            currentPhase: 'MasterPlan Generation',
            percentage: Math.max(prev.percentage, 30), // Continue from at least 30%
            cost: eventData.estimated_cost || prev.cost,
            estimatedDurationSeconds: eventData.estimated_duration_seconds || 600,
            estimatedTotalTokens: eventData.estimated_tokens || prev.estimatedTotalTokens,
            elapsedSeconds: calculateElapsedSeconds(),
          }))
          break
        }

        case 'masterplan_tokens_progress': {
          const tokensReceived = eventData.tokens_received || 0
          const estimatedTotal = eventData.estimated_total || 1
          const percentage = Math.min((tokensReceived / estimatedTotal) * 100, 95)

          setProgressState((prev) => ({
            ...prev,
            tokensReceived,
            estimatedTotalTokens: estimatedTotal,
            percentage,
            elapsedSeconds: calculateElapsedSeconds(),
          }))
          break
        }

        case 'masterplan_entity_discovered': {
          const entityType = eventData.entity_type?.toLowerCase() || 'task'

          setProgressState((prev) => {
            if (entityType === 'phase') {
              return { ...prev, phasesFound: prev.phasesFound + 1 }
            } else if (entityType === 'milestone') {
              return { ...prev, milestonesFound: prev.milestonesFound + 1 }
            } else {
              return { ...prev, tasksFound: prev.tasksFound + 1 }
            }
          })
          break
        }

        case 'masterplan_parsing_complete': {
          const now = Date.now()
          if (phaseTimesRef.current['discovery'].start === 0) {
            phaseTimesRef.current['discovery'].start = startTimeRef.current || now - 5000
          }
          phaseTimesRef.current['discovery'].end = now
          phaseTimesRef.current['parsing'].start = now

          updatePhaseStatus('discovery', 'completed', undefined, now)
          updatePhaseStatus('parsing', 'in_progress', now)

          setProgressState((prev) => ({
            ...prev,
            currentPhase: 'Parsing',
            isParsing: true,
            percentage: Math.min(prev.percentage + 15, 95),
          }))
          break
        }

        case 'masterplan_validation_start': {
          const now = Date.now()
          phaseTimesRef.current['parsing'].end = now
          phaseTimesRef.current['validation'].start = now

          updatePhaseStatus('parsing', 'completed', undefined, now)
          updatePhaseStatus('validation', 'in_progress', now)

          setProgressState((prev) => ({
            ...prev,
            currentPhase: 'Validating',
            isParsing: false,
            isValidating: true,
            percentage: Math.min(prev.percentage + 20, 95),
          }))
          break
        }

        case 'masterplan_saving_start': {
          const now = Date.now()
          phaseTimesRef.current['validation'].end = now
          phaseTimesRef.current['saving'].start = now

          updatePhaseStatus('validation', 'completed', undefined, now)
          updatePhaseStatus('saving', 'in_progress', now)

          setProgressState((prev) => ({
            ...prev,
            currentPhase: 'Saving',
            isValidating: false,
            isSaving: true,
            percentage: Math.min(prev.percentage + 15, 95),
          }))
          break
        }

        case 'masterplan_generation_complete': {
          const now = Date.now()
          phaseTimesRef.current['saving'].end = now

          updatePhaseStatus('saving', 'completed', undefined, now)

          setProgressState((prev) => ({
            ...prev,
            currentPhase: 'Complete',
            percentage: 100,
            isSaving: false,
            isComplete: true,
            elapsedSeconds: calculateElapsedSeconds(),
          }))
          break
        }

        case 'discovery_generation_start': {
          if (!startTimeRef.current) {
            startTimeRef.current = Date.now()
          }
          updatePhaseStatus('discovery', 'in_progress', startTimeRef.current)
          setProgressState((prev) => ({
            ...prev,
            currentPhase: 'Generating',
            startTime: new Date(),
          }))
          break
        }

        case 'discovery_tokens_progress': {
          const tokensReceived = eventData.tokens_received || 0
          const estimatedTotal = eventData.estimated_total || 1
          const percentage = Math.min((tokensReceived / estimatedTotal) * 100, 95)

          setProgressState((prev) => ({
            ...prev,
            tokensReceived,
            estimatedTotalTokens: estimatedTotal,
            percentage,
            elapsedSeconds: calculateElapsedSeconds(),
          }))
          break
        }

        case 'discovery_parsing_complete': {
          setProgressState((prev) => ({
            ...prev,
            currentPhase: 'Parsing Discovery',
            percentage: 15,
            boundedContexts: eventData.total_bounded_contexts || 0,
            aggregates: eventData.total_aggregates || 0,
            entities: eventData.total_entities || 0,
            elapsedSeconds: calculateElapsedSeconds(),
          }))
          break
        }

        case 'discovery_saving_start': {
          setProgressState((prev) => ({
            ...prev,
            currentPhase: 'Saving Discovery',
            percentage: 20,
            entities: eventData.total_entities || prev.entities,
            elapsedSeconds: calculateElapsedSeconds(),
          }))
          break
        }

        case 'discovery_generation_complete': {
          updatePhaseStatus('discovery', 'completed', undefined, Date.now())
          // Don't mark as complete yet - MasterPlan generation still pending
          setProgressState((prev) => ({
            ...prev,
            currentPhase: 'Discovery Complete',
            percentage: 25, // Discovery is ~25% of total progress
            boundedContexts: eventData.total_bounded_contexts || 0,
            aggregates: eventData.total_aggregates || 0,
            entities: eventData.total_entities || 0,
            elapsedSeconds: calculateElapsedSeconds(),
          }))
          break
        }

        default:
          // Other events are handled implicitly
          break
      }
    }, 100) // Debounce by 100ms

    return () => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current)
      }
    }
  }, [events, sessionId, latestEvent, updatePhaseStatus, calculateElapsedSeconds])

  /**
   * Sync local state to Zustand store
   */
  useEffect(() => {
    updateProgress(progressState)
    setPhases(phases)
    updateMetrics({
      tokensReceived: progressState.tokensReceived,
      estimatedTotal: progressState.estimatedTotalTokens,
      percentage: progressState.percentage,
      costUsd: progressState.cost,
      durationSeconds: progressState.elapsedSeconds,
      currentPhase: progressState.currentPhase,
    })
  }, [progressState, phases, updateProgress, setPhases, updateMetrics])

  /**
   * Handle retry after error
   */
  const handleRetry = useCallback(async () => {
    clearStoreError()
    setProgressState(initialProgressState)
    setLocalPhases(PHASES_DEFINITION)
    startTimeRef.current = null
    phaseTimesRef.current = {
      discovery: { start: 0 },
      parsing: { start: 0 },
      validation: { start: 0 },
      saving: { start: 0 },
    }

    // TODO: Call ChatService.retryMasterplanGeneration(currentMasterPlanId)
  }, [clearStoreError, currentMasterPlanId])

  return {
    state: progressState,
    sessionId: sessionId || currentMasterPlanId,
    phases,
    handleRetry,
    clearError: clearStoreError,
    isLoading: !progressState.isComplete && progressState.startTime !== null,
  }
}
