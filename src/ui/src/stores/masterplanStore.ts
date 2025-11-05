/**
 * MasterPlan Zustand Store
 *
 * Centralized state management for MasterPlan generation progress.
 * Provides persistent state across component remounts and page reloads.
 *
 * Features:
 * - Real-time progress tracking
 * - Phase and milestone status management
 * - Error handling and recovery
 * - LocalStorage persistence
 * - Atomic state updates
 *
 * @since Nov 4, 2025
 * @version 1.0
 */

import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { ProgressState, PhaseStatus, PhaseStatusType, MasterPlanProgressEvent } from '../types/masterplan'

/**
 * Complete MasterPlan store state interface
 */
export interface MasterPlanStoreState {
  // Current generation state
  currentMasterPlanId: string | null
  currentSessionId: string | null
  generationProgress: ProgressState | null
  isGenerating: boolean

  // Tracked phases/milestones
  phases: PhaseStatus[]
  currentPhase: PhaseStatus | null

  // Metrics and statistics
  metrics: {
    tokensReceived: number
    estimatedTotal: number
    percentage: number
    costUsd: number
    durationSeconds: number
    currentPhase: string
  }

  // Event history (limited)
  events: MasterPlanProgressEvent[]

  // Error state
  error: string | null
  retryCount: number

  // Session metadata
  sessionStartTime: number | null
  lastUpdateTime: number | null

  // State actions
  setCurrentMasterPlan: (id: string) => void
  setCurrentSession: (sessionId: string) => void
  startGeneration: () => void
  endGeneration: () => void
  updateProgress: (progress: Partial<ProgressState>) => void
  setPhases: (phases: PhaseStatus[]) => void
  updatePhaseStatus: (phaseName: string, status: PhaseStatusType) => void
  updateMetrics: (metrics: Partial<MasterPlanStoreState['metrics']>) => void
  addEvent: (event: MasterPlanProgressEvent) => void
  setError: (error: string | null) => void
  clearError: () => void
  incrementRetry: () => void
  reset: () => void
}

/**
 * Default/initial state
 */
const initialState = {
  currentMasterPlanId: null,
  currentSessionId: null,
  generationProgress: null,
  isGenerating: false,
  phases: [],
  currentPhase: null,
  metrics: {
    tokensReceived: 0,
    estimatedTotal: 0,
    percentage: 0,
    costUsd: 0,
    durationSeconds: 0,
    currentPhase: '',
  },
  events: [],
  error: null,
  retryCount: 0,
  sessionStartTime: null,
  lastUpdateTime: null,
}

/**
 * MasterPlan Zustand store
 *
 * Usage:
 * ```typescript
 * // In a component
 * const { currentMasterPlanId, phases, updateProgress } = useMasterPlanStore();
 *
 * // Subscribe to specific state
 * const phases = useMasterPlanStore((state) => state.phases);
 *
 * // Use selectors for optimization
 * const currentPhase = useMasterPlanStore((state) => state.currentPhase);
 * ```
 */
export const useMasterPlanStore = create<MasterPlanStoreState>(
  persist(
    (set) => ({
      ...initialState,

  setCurrentMasterPlan: (id: string) => {
    set({
      currentMasterPlanId: id,
      sessionStartTime: Date.now(),
      lastUpdateTime: Date.now(),
    })
  },

  setCurrentSession: (sessionId: string) => {
    set({
      currentSessionId: sessionId,
      lastUpdateTime: Date.now(),
    })
  },

  startGeneration: () => {
    set({
      isGenerating: true,
      sessionStartTime: Date.now(),
      lastUpdateTime: Date.now(),
    })
  },

  endGeneration: () => {
    set({
      isGenerating: false,
      lastUpdateTime: Date.now(),
    })
  },

  updateProgress: (progress: Partial<ProgressState>) => {
    set((state) => ({
      generationProgress: state.generationProgress
        ? { ...state.generationProgress, ...progress }
        : (progress as ProgressState),
      lastUpdateTime: Date.now(),
    }))
  },

  setPhases: (phases: PhaseStatus[]) => {
    const currentPhase =
      phases.find((p) => p.status === 'in_progress') || phases[0] || null
    set({
      phases,
      currentPhase,
      lastUpdateTime: Date.now(),
    })
  },

  updatePhaseStatus: (phaseName: string, status: PhaseStatusType) => {
    set((state): Partial<MasterPlanStoreState> => {
      const updatedPhases = state.phases.map((phase) =>
        phase.name === phaseName ? { ...phase, status } : phase
      )

      const currentPhase =
        updatedPhases.find((p) => p.status === 'in_progress') ||
        updatedPhases[0] ||
        null

      return {
        phases: updatedPhases,
        currentPhase,
        lastUpdateTime: Date.now(),
      }
    })
  },

  updateMetrics: (metrics: Partial<MasterPlanStoreState['metrics']>) => {
    set((state) => ({
      metrics: { ...state.metrics, ...metrics },
      lastUpdateTime: Date.now(),
    }))
  },

  addEvent: (event: MasterPlanProgressEvent) => {
    set((state) => {
      // Keep only last 50 events to save memory
      const events = [event, ...state.events].slice(0, 50)
      return {
        events,
        lastUpdateTime: Date.now(),
      }
    })
  },

  setError: (error: string | null) => {
    set({
      error,
      lastUpdateTime: Date.now(),
    })
  },

  clearError: () => {
    set({
      error: null,
      lastUpdateTime: Date.now(),
    })
  },

  incrementRetry: () => {
    set((state) => ({
      retryCount: state.retryCount + 1,
      lastUpdateTime: Date.now(),
    }))
  },

  reset: () => {
    set(initialState)
  }
    }),
    {
      name: 'masterplan-store',
      // Only persist generation state across page reloads
      partialize: (state) => ({
        isGenerating: state.isGenerating,
        currentSessionId: state.currentSessionId,
      }),
    },
  )
)

/**
 * Utility selector hooks for optimized re-rendering
 */

/**
 * Get only the current phase (prevents unnecessary re-renders)
 */
export const useMasterPlanCurrentPhase = () =>
  useMasterPlanStore((state) => state.currentPhase)

/**
 * Get only the error state
 */
export const useMasterPlanError = () =>
  useMasterPlanStore((state) => state.error)

/**
 * Get only metrics
 */
export const useMasterPlanMetrics = () =>
  useMasterPlanStore((state) => state.metrics)

/**
 * Get only phases
 */
export const useMasterPlanPhases = () =>
  useMasterPlanStore((state) => state.phases)

/**
 * Get only progress percentage
 */
export const useMasterPlanPercentage = () =>
  useMasterPlanStore((state) => state.metrics.percentage)

export default useMasterPlanStore
