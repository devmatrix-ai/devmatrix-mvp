import React from 'react'
import { ProgressEvent } from '../../hooks/useChat'

interface ProgressIndicatorProps {
  progress: ProgressEvent | null
}

export const ProgressIndicator: React.FC<ProgressIndicatorProps> = ({ progress }) => {
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

  return (
    <div className="flex items-center gap-2 px-4 py-2 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
      <span className="text-lg animate-pulse">
        {getProgressIcon(progress.event)}
      </span>
      <span className={`text-sm font-medium ${getProgressColor(progress.event)}`}>
        {getProgressMessage(progress.event, progress.data)}
      </span>
    </div>
  )
}
