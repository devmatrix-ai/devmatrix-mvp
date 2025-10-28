import React, { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'

interface Subtask {
  subtask_id: string
  subtask_number: number
  name: string
  description: string
  status: string
  completed: boolean
}

interface Task {
  task_id: string
  task_number: number
  name: string
  description: string
  status: string
  complexity: string
  target_files: string[]
  subtasks: Subtask[]
}

interface Milestone {
  milestone_id: string
  milestone_number: number
  name: string
  description: string
  total_tasks: number
  completed_tasks: number
  progress_percent: number
  tasks: Task[]
}

interface Phase {
  phase_id: string
  phase_type: string
  phase_number: number
  name: string
  description: string
  total_tasks: number
  completed_tasks: number
  progress_percent: number
  milestones: Milestone[]
}

interface Masterplan {
  masterplan_id: string
  project_name: string
  description: string
  status: string
  total_phases: number
  total_milestones: number
  total_tasks: number
  completed_tasks: number
  progress_percent: number
  tech_stack: Record<string, any>
  estimated_cost_usd: number
  estimated_duration_minutes: number
  phases: Phase[]
  created_at: string
  workspace_path?: string
}

export const MasterplanDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [masterplan, setMasterplan] = useState<Masterplan | null>(null)
  const [loading, setLoading] = useState(true)
  const [expandedMilestone, setExpandedMilestone] = useState<string | null>(null)
  const [expandedTask, setExpandedTask] = useState<string | null>(null)
  const [actionLoading, setActionLoading] = useState(false)
  const [notification, setNotification] = useState<{ type: 'success' | 'error', message: string } | null>(null)

  useEffect(() => {
    if (id) {
      fetchMasterplan(id)
    }
  }, [id])

  const fetchMasterplan = async (masterplanId: string) => {
    try {
      setLoading(true)
      const response = await fetch(`/api/v1/masterplans/${masterplanId}`)
      const data = await response.json()
      setMasterplan(data)
    } catch (error) {
      console.error('Error fetching masterplan:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleApprove = async () => {
    if (!masterplan) return

    try {
      setActionLoading(true)
      const response = await fetch(`/api/v1/masterplans/${masterplan.masterplan_id}/approve`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        }
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'Failed to approve masterplan')
      }

      const updatedMasterplan = await response.json()
      setMasterplan(updatedMasterplan)
      setNotification({ type: 'success', message: 'Masterplan approved successfully!' })
      setTimeout(() => setNotification(null), 3000)
    } catch (error) {
      console.error('Error approving masterplan:', error)
      setNotification({
        type: 'error',
        message: error instanceof Error ? error.message : 'Failed to approve masterplan'
      })
      setTimeout(() => setNotification(null), 5000)
    } finally {
      setActionLoading(false)
    }
  }

  const handleReject = async () => {
    if (!masterplan) return

    try {
      setActionLoading(true)
      const response = await fetch(`/api/v1/masterplans/${masterplan.masterplan_id}/reject`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        }
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'Failed to reject masterplan')
      }

      const updatedMasterplan = await response.json()
      setMasterplan(updatedMasterplan)
      setNotification({ type: 'success', message: 'Masterplan rejected successfully!' })
      setTimeout(() => setNotification(null), 3000)
    } catch (error) {
      console.error('Error rejecting masterplan:', error)
      setNotification({
        type: 'error',
        message: error instanceof Error ? error.message : 'Failed to reject masterplan'
      })
      setTimeout(() => setNotification(null), 5000)
    } finally {
      setActionLoading(false)
    }
  }

  const handleExecute = async () => {
    if (!masterplan) return

    try {
      setActionLoading(true)
      const response = await fetch(`/api/v1/masterplans/${masterplan.masterplan_id}/execute`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        }
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'Failed to execute masterplan')
      }

      const executionResponse = await response.json()

      // Update masterplan status to in_progress
      setMasterplan(prev => prev ? { ...prev, status: 'in_progress' } : null)

      setNotification({
        type: 'success',
        message: `Execution started! Workspace: ${executionResponse.workspace_path}`
      })

      // Auto-refresh masterplan data after a short delay
      setTimeout(() => {
        if (id) fetchMasterplan(id)
      }, 2000)

      setTimeout(() => setNotification(null), 5000)
    } catch (error) {
      console.error('Error executing masterplan:', error)
      setNotification({
        type: 'error',
        message: error instanceof Error ? error.message : 'Failed to execute masterplan'
      })
      setTimeout(() => setNotification(null), 5000)
    } finally {
      setActionLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 via-purple-900/20 to-blue-900/20 flex items-center justify-center">
        <div className="relative">
          <div className="w-20 h-20 border-4 border-purple-500/30 border-t-purple-500 rounded-full animate-spin"></div>
          <div className="absolute inset-0 flex items-center justify-center">
            <span className="text-3xl">🚀</span>
          </div>
        </div>
      </div>
    )
  }

  if (!masterplan) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 via-purple-900/20 to-blue-900/20 flex items-center justify-center">
        <div className="text-center">
          <div className="text-6xl mb-4">❌</div>
          <h2 className="text-2xl font-bold text-white mb-2">Masterplan not found</h2>
          <button
            onClick={() => navigate('/masterplans')}
            className="mt-4 px-6 py-3 bg-purple-600 hover:bg-purple-700 text-white rounded-lg transition-colors"
          >
            Back to Masterplans
          </button>
        </div>
      </div>
    )
  }

  const phaseColors = {
    setup: 'from-blue-500 to-cyan-500',
    core: 'from-purple-500 to-pink-500',
    polish: 'from-green-500 to-emerald-500',
  }

  const statusColor = (status: string) => {
    const colors: Record<string, string> = {
      pending: 'text-gray-400',
      ready: 'text-blue-400',
      in_progress: 'text-yellow-400',
      completed: 'text-green-400',
      failed: 'text-red-400',
    }
    return colors[status] || 'text-gray-400'
  }

  const showApprovalButtons = masterplan.status === 'draft'
  const showExecuteButton = masterplan.status === 'approved'

  return (
    <div className="h-screen overflow-auto bg-gradient-to-br from-gray-900 via-purple-900/20 to-blue-900/20 p-8">
      <div className="max-w-7xl mx-auto space-y-8">
        {/* Notification */}
        {notification && (
          <div
            className={`fixed top-4 right-4 z-50 px-6 py-4 rounded-lg shadow-lg ${
              notification.type === 'success'
                ? 'bg-green-500/90 text-white'
                : 'bg-red-500/90 text-white'
            }`}
          >
            {notification.message}
          </div>
        )}

        {/* Back Button */}
        <button
          onClick={() => navigate('/masterplans')}
          className="flex items-center gap-2 text-gray-400 hover:text-white transition-colors"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
          Back to Masterplans
        </button>

        {/* Header */}
        <div className="bg-gradient-to-r from-purple-900/20 to-blue-900/20 backdrop-blur-lg rounded-2xl border border-white/10 p-8">
          <div className="flex items-start justify-between mb-6">
            <div>
              <h1 className="text-4xl font-bold text-white mb-2">{masterplan.project_name}</h1>
              <p className="text-gray-400 text-lg">{masterplan.description}</p>
            </div>
            <div className="flex items-center gap-3">
              <span className="px-4 py-2 rounded-lg bg-purple-600 text-white font-semibold">
                {masterplan.status.toUpperCase()}
              </span>
            </div>
          </div>

          {/* Approval Buttons - Show only when status is draft */}
          {showApprovalButtons && (
            <div className="flex gap-3 mb-6">
              <button
                onClick={handleApprove}
                disabled={actionLoading}
                className="px-6 py-3 bg-green-600 hover:bg-green-700 text-white font-semibold rounded-lg shadow-lg shadow-green-500/50 transition-all focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2 focus:ring-offset-gray-900 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {actionLoading ? 'Processing...' : '✓ Approve Masterplan'}
              </button>
              <button
                onClick={handleReject}
                disabled={actionLoading}
                className="px-6 py-3 bg-red-600 hover:bg-red-700 text-white font-semibold rounded-lg shadow-lg shadow-red-500/50 transition-all focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2 focus:ring-offset-gray-900 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {actionLoading ? 'Processing...' : '✗ Reject Masterplan'}
              </button>
            </div>
          )}

          {/* Execute Button - Show only when status is approved */}
          {showExecuteButton && (
            <div className="flex gap-3 mb-6">
              <button
                onClick={handleExecute}
                disabled={actionLoading}
                className="px-8 py-4 bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 text-white font-bold text-lg rounded-lg shadow-lg shadow-purple-500/50 transition-all focus:outline-none focus:ring-2 focus:ring-purple-500 focus:ring-offset-2 focus:ring-offset-gray-900 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-3"
              >
                {actionLoading ? (
                  <>
                    <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                    <span>Starting Execution...</span>
                  </>
                ) : (
                  <>
                    <span className="text-2xl">🚀</span>
                    <span>Execute Masterplan</span>
                  </>
                )}
              </button>
            </div>
          )}

          {/* Workspace Path - Show when available */}
          {masterplan.workspace_path && (
            <div className="mb-6 p-4 bg-blue-500/10 border border-blue-500/30 rounded-lg">
              <div className="flex items-center gap-2 text-blue-300 text-sm">
                <span className="font-semibold">📁 Workspace:</span>
                <code className="font-mono">{masterplan.workspace_path}</code>
              </div>
            </div>
          )}

          {/* Progress Bar */}
          <div className="mb-6">
            <div className="flex justify-between text-sm text-gray-400 mb-2">
              <span>Overall Progress</span>
              <span>{Math.round(masterplan.progress_percent)}%</span>
            </div>
            <div className="h-4 bg-gray-800 rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-purple-500 to-pink-500 transition-all duration-500"
                style={{ width: `${masterplan.progress_percent}%` }}
              />
            </div>
          </div>

          {/* Stats Grid */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-white/5 rounded-lg p-4">
              <div className="text-3xl font-bold text-blue-400">{masterplan.total_phases}</div>
              <div className="text-sm text-gray-400">Phases</div>
            </div>
            <div className="bg-white/5 rounded-lg p-4">
              <div className="text-3xl font-bold text-purple-400">{masterplan.total_milestones}</div>
              <div className="text-sm text-gray-400">Milestones</div>
            </div>
            <div className="bg-white/5 rounded-lg p-4">
              <div className="text-3xl font-bold text-green-400">
                {masterplan.completed_tasks}/{masterplan.total_tasks}
              </div>
              <div className="text-sm text-gray-400">Tasks</div>
            </div>
            <div className="bg-white/5 rounded-lg p-4">
              <div className="text-3xl font-bold text-yellow-400">
                ${masterplan.estimated_cost_usd.toFixed(2)}
              </div>
              <div className="text-sm text-gray-400">Est. Cost</div>
            </div>
          </div>
        </div>

        {/* Phases Timeline */}
        <div className="space-y-6">
          {masterplan.phases.map((phase) => {
            const gradient = phaseColors[phase.phase_type as keyof typeof phaseColors] || 'from-gray-500 to-gray-700'

            return (
              <div key={phase.phase_id} className="relative">
                {/* Phase Header */}
                <div className={`bg-gradient-to-r ${gradient} rounded-2xl p-6 mb-4`}>
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="flex items-center gap-3 mb-2">
                        <span className="text-3xl">
                          {phase.phase_type === 'setup' ? '⚙️' : phase.phase_type === 'core' ? '🎯' : '✨'}
                        </span>
                        <h2 className="text-2xl font-bold text-white">{phase.name}</h2>
                      </div>
                      <p className="text-white/80">{phase.description}</p>
                    </div>
                    <div className="text-right">
                      <div className="text-3xl font-bold text-white">
                        {phase.completed_tasks}/{phase.total_tasks}
                      </div>
                      <div className="text-sm text-white/60">tasks</div>
                    </div>
                  </div>
                </div>

                {/* Milestones */}
                <div className="pl-8 border-l-4 border-white/10 space-y-4">
                  {phase.milestones.map((milestone) => (
                    <div key={milestone.milestone_id} className="relative">
                      {/* Milestone Bullet */}
                      <div className="absolute -left-10 top-6 w-6 h-6 rounded-full bg-gradient-to-r from-purple-500 to-pink-500 border-4 border-gray-900"></div>

                      {/* Milestone Card */}
                      <div className="bg-white/5 backdrop-blur-lg rounded-xl border border-white/10 overflow-hidden">
                        <button
                          onClick={() => setExpandedMilestone(expandedMilestone === milestone.milestone_id ? null : milestone.milestone_id)}
                          className="w-full p-6 text-left hover:bg-white/5 transition-colors"
                        >
                          <div className="flex items-center justify-between">
                            <div className="flex-1">
                              <h3 className="text-xl font-bold text-white mb-2">{milestone.name}</h3>
                              <p className="text-gray-400 text-sm mb-3">{milestone.description}</p>
                              <div className="flex items-center gap-4 text-sm">
                                <span className="text-purple-400">
                                  📋 {milestone.tasks.length} tasks
                                </span>
                                <span className="text-green-400">
                                  ✅ {milestone.completed_tasks} completed
                                </span>
                              </div>
                            </div>
                            <svg
                              className={`w-6 h-6 text-white transition-transform ${
                                expandedMilestone === milestone.milestone_id ? 'rotate-180' : ''
                              }`}
                              fill="none"
                              stroke="currentColor"
                              viewBox="0 0 24 24"
                            >
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                            </svg>
                          </div>
                        </button>

                        {/* Tasks (Expandable) */}
                        {expandedMilestone === milestone.milestone_id && (
                          <div className="border-t border-white/10 p-6 space-y-3">
                            {milestone.tasks.map((task) => (
                              <div
                                key={task.task_id}
                                className="bg-white/5 rounded-lg overflow-hidden"
                              >
                                <button
                                  onClick={() => setExpandedTask(expandedTask === task.task_id ? null : task.task_id)}
                                  className="w-full p-4 hover:bg-white/10 transition-colors text-left"
                                >
                                  <div className="flex items-start gap-3">
                                    <span className={`text-lg ${statusColor(task.status)}`}>
                                      {task.status === 'completed' ? '✅' : task.status === 'in_progress' ? '⚡' : '⏳'}
                                    </span>
                                    <div className="flex-1">
                                      <div className="flex items-center gap-2 mb-1 flex-wrap">
                                        <span className="text-sm font-mono text-gray-500">#{task.task_number}</span>
                                        <h4 className="font-semibold text-white">{task.name}</h4>
                                        <span className={`text-xs px-2 py-1 rounded ${
                                          task.complexity === 'high' ? 'bg-red-500/20 text-red-300' :
                                          task.complexity === 'medium' ? 'bg-yellow-500/20 text-yellow-300' :
                                          'bg-green-500/20 text-green-300'
                                        }`}>
                                          {task.complexity}
                                        </span>
                                        {task.subtasks && task.subtasks.length > 0 && (
                                          <span className="text-xs px-2 py-1 bg-purple-500/20 text-purple-300 rounded">
                                            {task.subtasks.filter(s => s.completed).length}/{task.subtasks.length} subtasks
                                          </span>
                                        )}
                                      </div>
                                      <p className="text-sm text-gray-400">{task.description}</p>
                                      {task.target_files && task.target_files.length > 0 && (
                                        <div className="mt-2 flex flex-wrap gap-1">
                                          {task.target_files.slice(0, 3).map((file, idx) => (
                                            <span key={idx} className="text-xs px-2 py-1 bg-blue-500/20 text-blue-300 rounded">
                                              📄 {file}
                                            </span>
                                          ))}
                                          {task.target_files.length > 3 && (
                                            <span className="text-xs px-2 py-1 bg-purple-500/20 text-purple-400 rounded">
                                              +{task.target_files.length - 3} more
                                            </span>
                                          )}
                                        </div>
                                      )}
                                    </div>
                                    {task.subtasks && task.subtasks.length > 0 && (
                                      <svg
                                        className={`w-5 h-5 text-gray-400 transition-transform ${
                                          expandedTask === task.task_id ? 'rotate-180' : ''
                                        }`}
                                        fill="none"
                                        stroke="currentColor"
                                        viewBox="0 0 24 24"
                                      >
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                                      </svg>
                                    )}
                                  </div>
                                </button>

                                {/* Subtasks (Nested Accordion) */}
                                {expandedTask === task.task_id && task.subtasks && task.subtasks.length > 0 && (
                                  <div className="border-t border-white/10 bg-white/5 p-4 space-y-2">
                                    <div className="text-xs font-semibold text-purple-300 mb-3 flex items-center gap-2">
                                      <span>⚙️</span>
                                      <span>AUTONOMOUS EXECUTION STEPS</span>
                                    </div>
                                    {task.subtasks.map((subtask) => (
                                      <div
                                        key={subtask.subtask_id}
                                        className="flex items-start gap-3 p-3 bg-white/5 rounded-lg hover:bg-white/10 transition-colors"
                                      >
                                        <span className="text-sm">
                                          {subtask.completed ? '✅' : '⭕'}
                                        </span>
                                        <div className="flex-1 min-w-0">
                                          <div className="flex items-center gap-2 mb-1">
                                            <span className="text-xs font-mono text-gray-500">{subtask.subtask_number}.</span>
                                            <span className="text-sm font-medium text-white">{subtask.name}</span>
                                          </div>
                                          {subtask.description && (
                                            <p className="text-xs text-gray-400 font-mono">{subtask.description}</p>
                                          )}
                                        </div>
                                      </div>
                                    ))}
                                  </div>
                                )}
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
