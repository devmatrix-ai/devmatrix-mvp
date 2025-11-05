import React, { useState, useEffect } from 'react'
import { MasterplanCard } from './MasterplanCard'
import { authService } from '@/services/authService'

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

interface MasterplansListProps {
  statusFilter?: string
}

export const MasterplansList: React.FC<MasterplansListProps> = ({ statusFilter }) => {
  const [masterplans, setMasterplans] = useState<Masterplan[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedStatus, setSelectedStatus] = useState<string>(statusFilter || 'all')

  useEffect(() => {
    fetchMasterplans()
  }, [selectedStatus])

  const fetchMasterplans = async () => {
    try {
      setLoading(true)
      setError(null)
      const token = authService.getAccessToken()

      if (!token) {
        throw new Error('Not authenticated. Please log in.')
      }

      const statusParam = selectedStatus !== 'all' ? `?status=${selectedStatus}` : ''
      const response = await fetch(`/api/v1/masterplans${statusParam}`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      })

      if (!response.ok) {
        throw new Error(`Failed to fetch masterplans: ${response.statusText}`)
      }

      const data = await response.json()
      // Filter out rejected masterplans
      const filtered = (data.masterplans || []).filter((mp: Masterplan) => mp.status !== 'rejected')
      setMasterplans(filtered)
    } catch (error) {
      console.error('Error fetching masterplans:', error)
      setError(error instanceof Error ? error.message : 'Failed to load masterplans')
    } finally {
      setLoading(false)
    }
  }

  const filteredMasterplans = masterplans.filter(mp =>
    mp.project_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    mp.description.toLowerCase().includes(searchTerm.toLowerCase())
  )

  return (
    <div className="space-y-6">
      {/* Header with Search and Filters */}
      <div className="bg-gradient-to-r from-purple-900/20 to-blue-900/20 backdrop-blur-lg rounded-2xl border border-white/10 p-6">
        <div className="flex flex-col md:flex-row gap-4 items-center justify-between">
          {/* Search Bar */}
          <div className="relative flex-1 w-full">
            <input
              type="text"
              placeholder="Search masterplans..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full px-4 py-3 pl-12 bg-white/5 border border-white/20 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all"
            />
            <svg
              className="absolute left-4 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
              />
            </svg>
          </div>

          {/* Status Filter */}
          <div className="flex gap-2 flex-wrap">
            {['all', 'draft', 'approved', 'in_progress', 'completed'].map((status) => (
              <button
                key={status}
                onClick={() => setSelectedStatus(status)}
                className={`px-4 py-2 rounded-lg font-medium text-sm transition-all ${
                  selectedStatus === status
                    ? 'bg-purple-600 text-white shadow-lg shadow-purple-500/50'
                    : 'bg-white/10 text-gray-300 hover:bg-white/20'
                }`}
              >
                {status === 'all' ? 'All' : status.replace('_', ' ').charAt(0).toUpperCase() + status.slice(1).replace('_', ' ')}
              </button>
            ))}
          </div>
        </div>

        {/* Stats Summary */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6">
          <div className="bg-white/5 rounded-lg p-4">
            <div className="text-3xl font-bold text-white">{masterplans.length}</div>
            <div className="text-sm text-gray-400">Total Plans</div>
          </div>
          <div className="bg-white/5 rounded-lg p-4">
            <div className="text-3xl font-bold text-green-400">
              {masterplans.filter(mp => mp.status === 'completed').length}
            </div>
            <div className="text-sm text-gray-400">Completed</div>
          </div>
          <div className="bg-white/5 rounded-lg p-4">
            <div className="text-3xl font-bold text-yellow-400">
              {masterplans.filter(mp => mp.status === 'in_progress').length}
            </div>
            <div className="text-sm text-gray-400">In Progress</div>
          </div>
          <div className="bg-white/5 rounded-lg p-4">
            <div className="text-3xl font-bold text-gray-400">
              {masterplans.filter(mp => mp.status === 'draft').length}
            </div>
            <div className="text-sm text-gray-400">Drafts</div>
          </div>
        </div>
      </div>

      {/* Error State */}
      {error && (
        <div className="bg-red-900/20 border border-red-500/50 rounded-lg p-4 text-red-400">
          <p className="font-semibold">Error loading masterplans</p>
          <p className="text-sm mt-1">{error}</p>
        </div>
      )}

      {/* Loading State */}
      {loading && (
        <div className="flex items-center justify-center py-20">
          <div className="relative">
            <div className="w-16 h-16 border-4 border-purple-500/30 border-t-purple-500 rounded-full animate-spin"></div>
            <div className="absolute inset-0 flex items-center justify-center">
              <span className="text-2xl">🚀</span>
            </div>
          </div>
        </div>
      )}

      {/* Masterplans Grid */}
      {!loading && filteredMasterplans.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredMasterplans.map((masterplan) => (
            <MasterplanCard key={masterplan.masterplan_id} masterplan={masterplan} />
          ))}
        </div>
      )}

      {/* Empty State */}
      {!loading && filteredMasterplans.length === 0 && (
        <div className="text-center py-20">
          <div className="text-6xl mb-4">📋</div>
          <h3 className="text-2xl font-bold text-white mb-2">No masterplans found</h3>
          <p className="text-gray-400">
            {searchTerm ? 'Try a different search term' : 'Create your first masterplan to get started'}
          </p>
        </div>
      )}
    </div>
  )
}
