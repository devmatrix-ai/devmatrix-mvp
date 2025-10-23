import React from 'react'
import { useNavigate } from 'react-router-dom'

interface MasterplanCardProps {
  masterplan: {
    masterplan_id: string
    project_name: string
    description: string
    status: string
    total_phases: number
    total_milestones: number
    total_tasks: number
    completed_tasks: number
    progress_percent: number
    tech_stack: {
      backend?: string
      frontend?: string
      database?: string
      cache?: string
      other?: string[]
    }
    estimated_cost_usd: number
    estimated_duration_minutes: number
    generation_cost_usd: number
    created_at: string
  }
}

const statusColors = {
  draft: 'from-gray-500 to-gray-700',
  approved: 'from-blue-500 to-cyan-500',
  in_progress: 'from-yellow-500 to-orange-500',
  paused: 'from-gray-400 to-gray-600',
  completed: 'from-green-500 to-emerald-500',
  failed: 'from-red-500 to-rose-600',
  cancelled: 'from-gray-500 to-gray-700',
}

const statusIcons = {
  draft: '📝',
  approved: '✅',
  in_progress: '⚡',
  paused: '⏸️',
  completed: '🎉',
  failed: '❌',
  cancelled: '🚫',
}

export const MasterplanCard: React.FC<MasterplanCardProps> = ({ masterplan }) => {
  const navigate = useNavigate()
  const gradient = statusColors[masterplan.status as keyof typeof statusColors] || statusColors.draft
  const icon = statusIcons[masterplan.status as keyof typeof statusIcons] || statusIcons.draft

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr)
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
  }

  const handleClick = () => {
    navigate(`/masterplans/${masterplan.masterplan_id}`)
  }

  return (
    <div
      onClick={handleClick}
      className="group relative cursor-pointer overflow-hidden rounded-2xl bg-gradient-to-br from-white/10 to-white/5 backdrop-blur-lg border border-white/20 hover:border-white/40 transition-all duration-300 hover:scale-[1.02] hover:shadow-2xl"
    >
      {/* Gradient Border Effect */}
      <div className={`absolute inset-0 bg-gradient-to-br ${gradient} opacity-0 group-hover:opacity-10 transition-opacity duration-300`} />

      {/* Card Content */}
      <div className="relative p-6 space-y-4">
        {/* Header */}
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-2xl">{icon}</span>
              <span className={`text-xs font-semibold px-2 py-1 rounded-full bg-gradient-to-r ${gradient} text-white`}>
                {masterplan.status.toUpperCase()}
              </span>
            </div>
            <h3 className="text-xl font-bold text-white truncate group-hover:text-transparent group-hover:bg-clip-text group-hover:bg-gradient-to-r group-hover:from-blue-400 group-hover:to-purple-400 transition-all">
              {masterplan.project_name}
            </h3>
            <p className="text-sm text-gray-400 line-clamp-2 mt-1">
              {masterplan.description}
            </p>
          </div>
        </div>

        {/* Progress Bar */}
        <div className="space-y-1">
          <div className="flex justify-between text-xs text-gray-400">
            <span>Progress</span>
            <span>{Math.round(masterplan.progress_percent)}%</span>
          </div>
          <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
            <div
              className={`h-full bg-gradient-to-r ${gradient} transition-all duration-500`}
              style={{ width: `${masterplan.progress_percent}%` }}
            />
          </div>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-3 gap-3">
          <div className="bg-white/5 rounded-lg p-3 text-center">
            <div className="text-2xl font-bold text-purple-400">{masterplan.total_phases}</div>
            <div className="text-xs text-gray-500">Phases</div>
          </div>
          <div className="bg-white/5 rounded-lg p-3 text-center">
            <div className="text-2xl font-bold text-blue-400">{masterplan.total_milestones}</div>
            <div className="text-xs text-gray-500">Milestones</div>
          </div>
          <div className="bg-white/5 rounded-lg p-3 text-center">
            <div className="text-2xl font-bold text-green-400">
              {masterplan.completed_tasks}/{masterplan.total_tasks}
            </div>
            <div className="text-xs text-gray-500">Tasks</div>
          </div>
        </div>

        {/* Tech Stack Badges */}
        <div className="flex flex-wrap gap-2">
          {masterplan.tech_stack.backend && (
            <span className="px-2 py-1 text-xs rounded-full bg-purple-500/20 text-purple-300 border border-purple-500/30">
              {masterplan.tech_stack.backend}
            </span>
          )}
          {masterplan.tech_stack.frontend && (
            <span className="px-2 py-1 text-xs rounded-full bg-blue-500/20 text-blue-300 border border-blue-500/30">
              {masterplan.tech_stack.frontend}
            </span>
          )}
          {masterplan.tech_stack.database && (
            <span className="px-2 py-1 text-xs rounded-full bg-green-500/20 text-green-300 border border-green-500/30">
              {masterplan.tech_stack.database}
            </span>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between pt-3 border-t border-white/10">
          <div className="text-xs text-gray-500">
            Created {formatDate(masterplan.created_at)}
          </div>
          <div className="flex items-center gap-3 text-xs">
            <div className="text-yellow-400">
              💰 ${masterplan.generation_cost_usd.toFixed(4)}
            </div>
            <div className="text-blue-400">
              ⏱️ ~{masterplan.estimated_duration_minutes}min
            </div>
          </div>
        </div>

        {/* Hover Arrow */}
        <div className="absolute top-4 right-4 opacity-0 group-hover:opacity-100 transition-opacity duration-300">
          <div className="w-8 h-8 rounded-full bg-white/10 flex items-center justify-center">
            <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          </div>
        </div>
      </div>
    </div>
  )
}
