import React, { useState, useEffect } from 'react'
import { EntityCounter } from './EntityCounter'
import { StatusItem } from './StatusItem'

// Event types
export interface MasterPlanProgressEvent {
  event: string
  data: Record<string, any>
}

interface MasterPlanProgressIndicatorProps {
  event: MasterPlanProgressEvent | null
  onComplete?: () => void
}

interface ProgressState {
  // Progress tracking
  tokensReceived: number
  estimatedTotalTokens: number
  percentage: number

  // Phase tracking
  currentPhase: string

  // Entities discovered
  phasesFound: number
  milestonesFound: number
  tasksFound: number

  // Timing
  startTime: Date | null
  elapsedSeconds: number
  estimatedDurationSeconds: number

  // Status flags
  isParsing: boolean
  isValidating: boolean
  isSaving: boolean
  isComplete: boolean
}

export const MasterPlanProgressIndicator: React.FC<MasterPlanProgressIndicatorProps> = ({
  event,
  onComplete
}) => {
  const [state, setState] = useState<ProgressState>({
    tokensReceived: 0,
    estimatedTotalTokens: 17000,
    percentage: 0,
    currentPhase: 'Iniciando generación...',
    phasesFound: 0,
    milestonesFound: 0,
    tasksFound: 0,
    startTime: null,
    elapsedSeconds: 0,
    estimatedDurationSeconds: 90,
    isParsing: false,
    isValidating: false,
    isSaving: false,
    isComplete: false
  })

  // Timer for elapsed time
  useEffect(() => {
    if (!state.startTime || state.isComplete) return

    const interval = setInterval(() => {
      setState(prev => ({
        ...prev,
        elapsedSeconds: Math.floor((Date.now() - prev.startTime!.getTime()) / 1000)
      }))
    }, 1000)

    return () => clearInterval(interval)
  }, [state.startTime, state.isComplete])

  // Handle events
  useEffect(() => {
    console.log('🔄 [MasterPlanProgressIndicator] useEffect triggered', {
      hasEvent: !!event,
      event: event
    })

    if (!event) {
      console.log('⏸️ [MasterPlanProgressIndicator] Event is null, returning early')
      return
    }

    const { event: eventType, data } = event
    console.log('📦 [MasterPlanProgressIndicator] Processing event:', eventType, 'with data:', data)

    switch (eventType) {
      // ===== Discovery Events =====
      case 'discovery_generation_start':
        console.log('🔍 [MasterPlanProgressIndicator] Starting discovery, setting startTime')
        setState(prev => {
          const newState = {
            ...prev,
            startTime: new Date(),
            estimatedTotalTokens: data.estimated_tokens || 8000,
            estimatedDurationSeconds: data.estimated_duration_seconds || 30,
            currentPhase: 'Analizando requisitos DDD...',
            percentage: 0
          }
          console.log('🔍 [MasterPlanProgressIndicator] New state after discovery_generation_start:', {
            startTime: newState.startTime,
            currentPhase: newState.currentPhase,
            percentage: newState.percentage
          })
          return newState
        })
        break

      case 'discovery_tokens_progress':
        setState(prev => {
          const rawPercentage = data.percentage || 0
          const cappedPercentage = Math.min(rawPercentage, 45) // Discovery is first half

          return {
            ...prev,
            tokensReceived: data.tokens_received || 0,
            estimatedTotalTokens: data.estimated_total || 8000,
            percentage: cappedPercentage,
            currentPhase: data.current_phase || prev.currentPhase
          }
        })
        break

      case 'discovery_parsing_complete':
        setState(prev => ({
          ...prev,
          currentPhase: 'Discovery completado - Preparando MasterPlan...',
          percentage: 48
        }))
        break

      case 'discovery_generation_complete':
        setState(prev => ({
          ...prev,
          currentPhase: 'Discovery completado - Iniciando MasterPlan...',
          percentage: 50
        }))
        break

      // ===== MasterPlan Events =====
      case 'masterplan_generation_start':
        console.log('🎬 [MasterPlanProgressIndicator] Starting masterplan generation')
        setState(prev => ({
          ...prev,
          // Keep startTime from discovery if it exists
          startTime: prev.startTime || new Date(),
          estimatedTotalTokens: data.estimated_tokens || 17000,
          // Add to existing duration
          estimatedDurationSeconds: prev.estimatedDurationSeconds + (data.estimated_duration_seconds || 90),
          currentPhase: 'Generando estructura del plan...',
          percentage: 50
        }))
        break

      case 'masterplan_tokens_progress':
        setState(prev => {
          // Map masterplan progress (0-95%) to second half (50-92.5%)
          const rawPercentage = data.percentage || 0
          const mappedPercentage = 50 + (rawPercentage * 0.45) // 50% + (0-95% * 0.45) = 50-92.5%

          return {
            ...prev,
            tokensReceived: data.tokens_received || 0,
            estimatedTotalTokens: data.estimated_total || 17000,
            percentage: Math.round(mappedPercentage),
            currentPhase: data.current_phase || prev.currentPhase
          }
        })
        break

      case 'masterplan_entity_discovered':
        setState(prev => {
          const updates: Partial<ProgressState> = {}

          if (data.type === 'phase') {
            updates.phasesFound = data.count || 0
          } else if (data.type === 'milestone') {
            updates.milestonesFound = data.count || 0
          } else if (data.type === 'task') {
            updates.tasksFound = data.count || 0
          }

          return { ...prev, ...updates }
        })
        break

      case 'masterplan_parsing_complete':
        setState(prev => ({
          ...prev,
          isParsing: false,
          phasesFound: data.total_phases || 3,
          milestonesFound: data.total_milestones || 17,
          tasksFound: data.total_tasks || 50,
          currentPhase: 'Parsing completado',
          percentage: 93  // Updated to fit in 50-100% range
        }))
        break

      case 'masterplan_validation_start':
        setState(prev => ({
          ...prev,
          isValidating: true,
          currentPhase: 'Validando dependencias...',
          percentage: 95  // Updated to fit in 50-100% range
        }))
        break

      case 'masterplan_saving_start':
        setState(prev => ({
          ...prev,
          isValidating: false,
          isSaving: true,
          currentPhase: 'Guardando en base de datos...',
          percentage: 97  // Updated to fit in 50-100% range
        }))
        break

      case 'masterplan_generation_complete':
        setState(prev => ({
          ...prev,
          isSaving: false,
          isComplete: true,
          currentPhase: 'Generación completada',
          percentage: 100,
          phasesFound: data.total_phases || 3,
          milestonesFound: data.total_milestones || 17,
          tasksFound: data.total_tasks || 50
        }))

        // Notify parent after a delay (for animation)
        if (onComplete) {
          setTimeout(() => onComplete(), 2000)
        }
        break
    }
  }, [event, onComplete])

  console.log('🔍 [MasterPlanProgressIndicator] Render cycle - checking startTime:', {
    hasStartTime: !!state.startTime,
    startTime: state.startTime,
    currentPhase: state.currentPhase,
    percentage: state.percentage
  })

  if (!state.startTime) {
    console.log('⏸️  [MasterPlanProgressIndicator] Not rendering - startTime is null')
    return null
  }

  console.log('🎨 [MasterPlanProgressIndicator] Rendering progress UI with state:', {
    percentage: state.percentage,
    currentPhase: state.currentPhase,
    isComplete: state.isComplete,
    phasesFound: state.phasesFound,
    milestonesFound: state.milestonesFound,
    tasksFound: state.tasksFound
  })

  const estimatedRemainingSeconds = Math.max(
    0,
    state.estimatedDurationSeconds - state.elapsedSeconds
  )

  // Status items
  const discoveryStatus: 'done' = 'done'
  const generationStatus = state.isComplete ? 'done' : 'in_progress'
  const phasesStatus = state.phasesFound === 3 ? 'done' : state.phasesFound > 0 ? 'in_progress' : 'pending'
  const milestonesStatus = state.milestonesFound >= 17 ? 'done' : state.milestonesFound > 0 ? 'in_progress' : 'pending'
  const tasksStatus = state.tasksFound === 50 ? 'done' : state.tasksFound > 0 ? 'in_progress' : 'pending'
  const validationStatus = state.isValidating ? 'in_progress' : state.isSaving || state.isComplete ? 'done' : 'pending'
  const savingStatus = state.isSaving ? 'in_progress' : state.isComplete ? 'done' : 'pending'

  return (
    <div
      className="
        space-y-4 p-5 rounded-xl shadow-lg
        bg-gradient-to-br from-purple-50 via-blue-50 to-indigo-50
        dark:from-purple-900/20 dark:via-blue-900/20 dark:to-indigo-900/20
        border-2 border-purple-300 dark:border-purple-700
        animate-fade-in
      "
    >
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="text-3xl animate-bounce-slow">
          {state.isComplete ? '✅' : '🤖'}
        </div>
        <div className="flex-1">
          <h3 className="font-bold text-lg text-purple-900 dark:text-purple-100">
            {state.isComplete ? 'MasterPlan Generado' : 'Generando MasterPlan'}
          </h3>
          <p className="text-sm text-purple-700 dark:text-purple-300">
            {state.currentPhase}
          </p>
        </div>
        {state.isComplete && (
          <div className="text-2xl animate-scale-in">🎉</div>
        )}
      </div>

      {/* Progress Bar */}
      <div className="space-y-2">
        <div className="flex justify-between text-xs font-medium text-purple-700 dark:text-purple-300">
          <span>{state.currentPhase}</span>
          <span className="font-bold">{state.percentage}%</span>
        </div>

        {/* Main progress bar */}
        <div className="w-full bg-purple-200 dark:bg-purple-800 rounded-full h-5 overflow-hidden shadow-inner">
          <div
            className="
              h-full rounded-full transition-all duration-700 ease-out
              bg-gradient-to-r from-purple-500 via-blue-600 to-indigo-600
              dark:from-purple-400 dark:via-blue-500 dark:to-indigo-500
              flex items-center justify-end pr-2
              shadow-md
            "
            style={{ width: `${state.percentage}%` }}
          >
            {state.percentage > 15 && (
              <span className="text-xs font-bold text-white drop-shadow-lg">
                {state.percentage}%
              </span>
            )}
          </div>
        </div>

        {/* Token and time info */}
        <div className="flex justify-between text-xs text-gray-600 dark:text-gray-400">
          <span className="font-mono">
            {state.tokensReceived > 0
              ? `${state.tokensReceived.toLocaleString()} / ${state.estimatedTotalTokens.toLocaleString()} tokens`
              : 'Preparando...'
            }
          </span>
          <span className="font-mono">
            {state.elapsedSeconds}s
            {!state.isComplete && estimatedRemainingSeconds > 0 && (
              <> / ~{estimatedRemainingSeconds}s restantes</>
            )}
          </span>
        </div>
      </div>

      {/* Entities Discovered - Grid with counters */}
      <div className="grid grid-cols-3 gap-3">
        <EntityCounter
          icon="📦"
          label="Fases"
          count={state.phasesFound}
          total={3}
          complete={state.phasesFound === 3}
        />
        <EntityCounter
          icon="🎯"
          label="Milestones"
          count={state.milestonesFound}
          total={17}
          complete={state.milestonesFound >= 17}
        />
        <EntityCounter
          icon="✅"
          label="Tareas"
          count={state.tasksFound}
          total={50}
          complete={state.tasksFound === 50}
        />
      </div>

      {/* Status Timeline */}
      <div className="space-y-1 bg-white dark:bg-gray-800/50 rounded-lg p-3 shadow-inner">
        <StatusItem
          icon="✓"
          text="Discovery completado"
          status={discoveryStatus}
        />
        <StatusItem
          icon={generationStatus === 'done' ? '✓' : '⚙️'}
          text="Generando estructura del plan"
          status={generationStatus}
        />
        {state.phasesFound > 0 && (
          <StatusItem
            icon={phasesStatus === 'done' ? '✓' : '⏳'}
            text={`Fases identificadas (${state.phasesFound}/3)`}
            status={phasesStatus}
          />
        )}
        {state.milestonesFound > 0 && (
          <StatusItem
            icon={milestonesStatus === 'done' ? '✓' : '⏳'}
            text={`Milestones creados (${state.milestonesFound}/17)`}
            status={milestonesStatus}
          />
        )}
        {state.tasksFound > 0 && (
          <StatusItem
            icon={tasksStatus === 'done' ? '✓' : '⏳'}
            text={`Tareas generadas (${state.tasksFound}/50)`}
            status={tasksStatus}
          />
        )}
        {(state.isValidating || validationStatus === 'done') && (
          <StatusItem
            icon={validationStatus === 'done' ? '✓' : '🔍'}
            text="Validando dependencias"
            status={validationStatus}
          />
        )}
        {(state.isSaving || savingStatus === 'done') && (
          <StatusItem
            icon={savingStatus === 'done' ? '✓' : '💾'}
            text="Guardando en base de datos"
            status={savingStatus}
          />
        )}
      </div>

      {/* Completion message */}
      {state.isComplete && (
        <div className="bg-green-100 dark:bg-green-900/30 border-2 border-green-400 dark:border-green-600 rounded-lg p-3 animate-fade-in">
          <div className="flex items-center gap-2 text-green-800 dark:text-green-200">
            <span className="text-xl">🎉</span>
            <div className="flex-1">
              <p className="font-bold">MasterPlan generado exitosamente</p>
              <p className="text-sm mt-1">
                {state.phasesFound} fases • {state.milestonesFound} milestones • {state.tasksFound} tareas
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
