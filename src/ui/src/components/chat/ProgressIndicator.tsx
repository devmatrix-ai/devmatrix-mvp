import React, { useState, useEffect } from 'react'
import { ProgressEvent } from '../../hooks/useChat'

interface ProgressIndicatorProps {
  progress: ProgressEvent | null
}

export const ProgressIndicator: React.FC<ProgressIndicatorProps> = ({ progress }) => {
  const [taskProgress, setTaskProgress] = useState({ completed: 0, total: 0 })

  useEffect(() => {
    if (!progress) return

    const { event, data } = progress

    // Track task progress for progress bar using real backend data
    if (event === 'execution_start' && data.total_tasks) {
      setTaskProgress({ completed: 0, total: data.total_tasks })
    } else if (event === 'task_complete' && data.completed !== undefined && data.total_tasks) {
      // Use actual backend data instead of local counter
      setTaskProgress({ completed: data.completed, total: data.total_tasks })
    } else if (event === 'execution_complete' && data.total_tasks) {
      setTaskProgress({ completed: data.completed || data.total_tasks, total: data.total_tasks })
    }
  }, [progress])

  if (!progress) return null

  const getProgressMessage = (event: string, data: Record<string, any>): string => {
    switch (event) {
      case 'phase_start':
        return data.message || `Fase: ${data.phase}`
      case 'phase_complete':
        return data.phase === 'decompose_tasks'
          ? `✓ ${data.num_tasks} tareas identificadas`
          : `✓ Fase completada: ${data.phase}`
      case 'execution_start':
        return `🚀 Ejecutando ${data.total_tasks} tareas...`
      case 'task_start':
        return `${data.progress} - ${data.description}`
      case 'task_complete':
        const files = data.output_files?.length || 0
        return `✓ ${data.task_id} completada${files > 0 ? ` (${files} archivos)` : ''}`
      case 'task_failed':
        return `✗ ${data.task_id} falló: ${data.error}`
      case 'execution_complete':
        return `✓ Ejecución completa: ${data.completed}/${data.total_tasks} exitosas`
      default:
        return `${event}: ${JSON.stringify(data)}`
    }
  }

  const getProgressIcon = (event: string): string => {
    switch (event) {
      case 'phase_start':
      case 'execution_start':
        return '⚙️'
      case 'task_start':
        return '🔄'
      case 'task_complete':
      case 'phase_complete':
      case 'execution_complete':
        return '✓'
      case 'task_failed':
        return '✗'
      default:
        return '●'
    }
  }

  const getProgressColor = (event: string): string => {
    switch (event) {
      case 'task_complete':
      case 'phase_complete':
      case 'execution_complete':
        return 'text-green-600 dark:text-green-400'
      case 'task_failed':
        return 'text-red-600 dark:text-red-400'
      case 'task_start':
      case 'phase_start':
      case 'execution_start':
        return 'text-blue-600 dark:text-blue-400'
      default:
        return 'text-gray-600 dark:text-gray-400'
    }
  }

  const progressPercentage = taskProgress.total > 0
    ? Math.round((taskProgress.completed / taskProgress.total) * 100)
    : 0

  const showProgressBar = taskProgress.total > 0

  return (
    <div className="space-y-2">
      {/* Progress bar - only show during execution */}
      {showProgressBar && (
        <div className="px-4 py-3 bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-900/30 dark:to-indigo-900/30 rounded-lg border border-blue-200 dark:border-blue-800">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-semibold text-blue-900 dark:text-blue-100">
              Progreso General
            </span>
            <span className="text-sm font-bold text-blue-700 dark:text-blue-300">
              {taskProgress.completed}/{taskProgress.total} tareas ({progressPercentage}%)
            </span>
          </div>
          <div className="w-full bg-blue-200 dark:bg-blue-800 rounded-full h-3 overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-blue-500 to-indigo-600 dark:from-blue-400 dark:to-indigo-500 rounded-full transition-all duration-500 ease-out flex items-center justify-end pr-1"
              style={{ width: `${progressPercentage}%` }}
            >
              {progressPercentage > 10 && (
                <span className="text-xs font-bold text-white drop-shadow">
                  {progressPercentage}%
                </span>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Current event message */}
      <div className="flex items-center gap-3 px-4 py-2.5 bg-white dark:bg-gray-800 rounded-lg border-2 border-blue-300 dark:border-blue-700 shadow-sm">
        <span className="text-xl animate-pulse">
          {getProgressIcon(progress.event)}
        </span>
        <div className="flex-1">
          <span className={`text-sm font-medium ${getProgressColor(progress.event)}`}>
            {getProgressMessage(progress.event, progress.data)}
          </span>
        </div>
      </div>
    </div>
  )
}
