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
    setCurrentDiscovery,
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

    // Extract sessionId from latest event if not provided
    const effectiveSessionId = sessionId || latestEvent?.data?.session_id

    if (effectiveSessionId && events.length > 0) {
      // Find the latest event that matches this session
      console.log('[useMasterPlanProgress] DEBUG - Filtering events:', {
        sessionIdToMatch: effectiveSessionId,
        totalEvents: events.length,
        eventSummary: events.map(e => ({
          type: e.type,
          sessionId: e.sessionId,
          session_id: e.data?.session_id,
          masterplan_id: e.data?.masterplan_id,
          timestamp: new Date(e.timestamp).toISOString(),
        }))
      })

      // Filter events by session_id - sessionId is always the discovery session_id
      // All events (both discovery and masterplan) have session_id field
      const sessionEvents = events.filter(
        (e) => e.sessionId === effectiveSessionId || e.data?.session_id === effectiveSessionId
      )
      eventToProcess = sessionEvents[sessionEvents.length - 1] || null

      console.log('[useMasterPlanProgress] Filtering events for session:', {
        sessionId: effectiveSessionId,
        totalEvents: events.length,
        filteredEvents: sessionEvents.length,
        latestEvent: eventToProcess?.type,
        matchedEvents: sessionEvents.map(e => e.type),
      })
    } else if (events.length > 0) {
      // No sessionId provided - use latest event from any session (during generation)
      console.log('[useMasterPlanProgress] No sessionId filter, using latest event:', {
        sessionIdProvided: !!sessionId,
        effectiveSessionId,
        latestEventType: latestEvent?.type,
        eventBufferSize: events.length,
        latestEventData: latestEvent?.data,
      })
    }

    if (!eventToProcess) {
      console.log('[useMasterPlanProgress] No event to process, skipping update')
      return
    }

    // Create unique key for this event to avoid duplicate processing
    const eventKey = `${eventToProcess.type}:${eventToProcess.timestamp}`
    if (eventKey === lastProcessedEventRef.current) {
      return
    }
    lastProcessedEventRef.current = eventKey

    const event = eventToProcess
    const eventData = event.data || {}

    // Process event immediately without debounce to avoid race conditions
    console.log('[useMasterPlanProgress] Processing event:', {
      eventType: event.type,
      eventData: event.data,
      timestamp: new Date(event.timestamp).toISOString(),
    })

    // Handle different event types
    switch (event.type) {
        case 'masterplan_generation_start': {
          // Continue progress from discovery phase, don't reset
          console.log('[useMasterPlanProgress] masterplan_generation_start eventData:', eventData)

          // Save discovery_id to store for traceability
          if (eventData.discovery_id) {
            setCurrentDiscovery(eventData.discovery_id)
          }

          setProgressState((prev) => ({
            ...prev,
            currentPhase: 'MasterPlan Generation',
            percentage: Math.max(prev.percentage, 30), // Continue from at least 30%
            cost: eventData.estimated_cost_usd || eventData.estimated_cost || prev.cost,
            estimatedDurationSeconds: eventData.estimated_duration_seconds || 600,
            estimatedTotalTokens: eventData.estimated_tokens || prev.estimatedTotalTokens,
            elapsedSeconds: calculateElapsedSeconds(),
          }))
          break
        }

        case 'masterplan_tokens_progress': {
          const tokensReceived = eventData.tokens_received || 0
          const estimatedTotal = eventData.estimated_total || 1
          const calculatedPercentage = Math.min((tokensReceived / estimatedTotal) * 100, 95)

          setProgressState((prev) => ({
            ...prev,
            tokensReceived,
            estimatedTotalTokens: estimatedTotal,
            // Ensure progress never decreases (events may arrive out of order)
            percentage: Math.max(prev.percentage, calculatedPercentage),
            elapsedSeconds: calculateElapsedSeconds(),
          }))
          break
        }

        case 'masterplan_entity_discovered': {
          const entityType = (eventData.entity_type || eventData.type)
            ?.toLowerCase()
            ?.replace(/([a-z])([A-Z])/g, '$1_$2')
            ?.toLowerCase() || 'task'
          console.log('[useMasterPlanProgress] masterplan_entity_discovered:', {
            rawData: eventData,
            entityType,
            count: eventData.count,
          })

          setProgressState((prev) => {
            if (entityType === 'phase') {
              return { ...prev, phasesFound: eventData.count || prev.phasesFound + 1 }
            } else if (entityType === 'milestone') {
              return { ...prev, milestonesFound: eventData.count || prev.milestonesFound + 1 }
            } else {
              return { ...prev, tasksFound: eventData.count || prev.tasksFound + 1 }
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

          // Log additional metadata if available
          if (eventData.llm_model || eventData.architecture_style) {
            console.log('[useMasterPlanProgress] MasterPlan metadata:', {
              llm_model: eventData.llm_model,
              architecture_style: eventData.architecture_style,
              tech_stack: eventData.tech_stack,
            })
          }

          setProgressState((prev) => ({
            ...prev,
            currentPhase: 'Complete',
            percentage: 100,
            isSaving: false,
            isComplete: true,
            elapsedSeconds: calculateElapsedSeconds(),
            phasesFound: eventData.total_phases || prev.phasesFound,
            milestonesFound: eventData.total_milestones || prev.milestonesFound,
            tasksFound: eventData.total_tasks || prev.tasksFound,
            cost: eventData.generation_cost_usd || prev.cost,
          }))
          break
        }

        case 'discovery_generation_start': {
          if (!startTimeRef.current) {
            startTimeRef.current = Date.now()
          }
          updatePhaseStatus('discovery', 'in_progress', startTimeRef.current)
          console.log('[useMasterPlanProgress] discovery_generation_start eventData:', eventData)
          setProgressState((prev) => ({
            ...prev,
            currentPhase: 'Generating',
            startTime: new Date(),
            estimatedTotalTokens: eventData.estimated_tokens || 8000,
            estimatedDurationSeconds: eventData.estimated_duration_seconds || 30,
            cost: eventData.estimated_cost_usd || 0.09,
          }))
          break
        }

        case 'discovery_tokens_progress': {
          const tokensReceived = eventData.tokens_received || 0
          const estimatedTotal = eventData.estimated_total || 1
          const calculatedPercentage = Math.min((tokensReceived / estimatedTotal) * 100, 95)

          setProgressState((prev) => ({
            ...prev,
            tokensReceived,
            estimatedTotalTokens: estimatedTotal,
            // Ensure progress never decreases (events may arrive out of order)
            percentage: Math.max(prev.percentage, calculatedPercentage),
            elapsedSeconds: calculateElapsedSeconds(),
          }))
          break
        }

        case 'discovery_entity_discovered': {
          const entityType = (eventData.entity_type || eventData.type)
            ?.toLowerCase()
            ?.replace(/([a-z])([A-Z])/g, '$1_$2')
            ?.toLowerCase() || 'entity'
          const count = eventData.count || 1

          console.log('[useMasterPlanProgress] discovery_entity_discovered:', {
            entityType,
            name: eventData.name,
            count,
          })

          setProgressState((prev) => {
            if (entityType === 'domain') {
              return { ...prev, currentPhase: `Found domain: ${eventData.name || 'Unknown'}` }
            } else if (entityType === 'bounded_context' || entityType === 'context') {
              return { ...prev, boundedContexts: Math.max(prev.boundedContexts, count) }
            } else if (entityType === 'aggregate') {
              return { ...prev, aggregates: Math.max(prev.aggregates, count) }
            } else if (entityType === 'entity') {
              return { ...prev, entities: Math.max(prev.entities, count) }
            }
            return prev
          })
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
          console.log('[useMasterPlanProgress] Unknown event type, skipping:', event.type)
          break
      }

      console.log('[useMasterPlanProgress] Event processing complete')
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
