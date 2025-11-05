/**
 * User Profile Page
 *
 * Shows user information, usage statistics, and quota limits.
 */

import { useState, useEffect } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { authService } from '../services/authService'
import { FiUser, FiMail, FiCalendar, FiActivity, FiCpu, FiDatabase, FiTrendingUp } from 'react-icons/fi'
import {
  GlassCard,
  PageHeader,
  StatusBadge,
} from '../components/design-system'

interface UsageData {
  current_month: {
    llm_tokens_used: number
    llm_cost_usd: number
    masterplans_created: number
    storage_bytes: number
    api_calls: number
  }
  quota: {
    llm_tokens_monthly_limit: number | null
    masterplans_limit: number | null
    storage_bytes_limit: number | null
    api_calls_per_minute: number
  }
}

export function ProfilePage() {
  const { user } = useAuth()
  const [usage, setUsage] = useState<UsageData | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    loadUsageData()
  }, [])

  const loadUsageData = async () => {
    try {
      const apiBaseUrl = import.meta.env.VITE_API_URL || '/api/v1'
      const response = await fetch(`${apiBaseUrl}/usage/status`, {
        headers: authService.getAuthHeaders(),
      })
      if (response.ok) {
        const data = await response.json()
        setUsage(data)
      }
    } catch (error) {
      console.error('Failed to load usage data:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 B'
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
  }

  const formatNumber = (num: number) => {
    return new Intl.NumberFormat().format(num)
  }

  const calculatePercentage = (used: number, limit: number | null) => {
    if (!limit) return 0
    return Math.min((used / limit) * 100, 100)
  }

  if (!user) {
    return null
  }

  return (
    <div className="flex-1 p-8 overflow-auto bg-gradient-to-br from-gray-900 via-purple-900/20 to-blue-900/20">
      <div className="max-w-4xl mx-auto space-y-6">
        <PageHeader
          emoji="👤"
          title="Profile"
          subtitle="Manage your account and view usage statistics"
        />

        {/* User Information Card */}
        <GlassCard className="p-6">
          <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <FiUser /> Account Information
          </h2>
          <div className="space-y-4">
            <div className="flex items-start gap-3">
              <FiUser className="text-gray-400 mt-1" />
              <div>
                <p className="text-sm text-gray-400">Username</p>
                <p className="font-medium text-white">{user.username}</p>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <FiMail className="text-gray-400 mt-1" />
              <div className="flex-1">
                <p className="text-sm text-gray-400">Email</p>
                <div className="flex items-center gap-2">
                  <p className="font-medium text-white">{user.email}</p>
                  {user.is_verified && (
                    <StatusBadge status="success">✓ Verified</StatusBadge>
                  )}
                </div>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <FiCalendar className="text-gray-400 mt-1" />
              <div>
                <p className="text-sm text-gray-400">Member since</p>
                <p className="font-medium text-white">
                  {new Date(user.created_at).toLocaleDateString('en-US', {
                    year: 'numeric',
                    month: 'long',
                    day: 'numeric',
                  })}
                </p>
              </div>
            </div>
          </div>
        </GlassCard>

        {/* Usage Statistics */}
        <GlassCard>
          {isLoading ? (
            <div className="p-12 flex flex-col items-center justify-center">
              <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-purple-600 border-r-transparent"></div>
              <p className="mt-4 text-sm text-gray-400">Loading usage data...</p>
            </div>
          ) : usage ? (
            <>
              <div className="border-b border-white/10 p-6">
                <h2 className="text-lg font-semibold text-white flex items-center gap-2">
                  <FiTrendingUp /> Usage Statistics
                </h2>
              </div>
              <div className="p-6 grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* LLM Tokens */}
                <GlassCard className="p-4">
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <div className="p-2 bg-purple-500/20 backdrop-blur-sm rounded-lg">
                        <FiCpu className="text-purple-400" size={20} />
                      </div>
                      <h3 className="text-sm font-medium text-gray-300">LLM Tokens</h3>
                    </div>
                  </div>
                  <p className="text-2xl font-bold text-white mb-2">
                    {formatNumber(usage.current_month.llm_tokens_used)}
                  </p>
                  <p className="text-xs text-gray-400">
                    Cost: ${usage.current_month.llm_cost_usd.toFixed(2)}
                  </p>
                  {usage.quota.llm_tokens_monthly_limit && (
                    <div className="mt-3">
                      <div className="flex justify-between text-xs text-gray-400 mb-1">
                        <span>{calculatePercentage(
                          usage.current_month.llm_tokens_used,
                          usage.quota.llm_tokens_monthly_limit
                        ).toFixed(0)}% used</span>
                        <span>{formatNumber(usage.quota.llm_tokens_monthly_limit)} limit</span>
                      </div>
                      <div className="w-full bg-white/10 rounded-full h-2">
                        <div
                          className="bg-purple-500 h-2 rounded-full transition-all"
                          style={{
                            width: `${calculatePercentage(
                              usage.current_month.llm_tokens_used,
                              usage.quota.llm_tokens_monthly_limit
                            )}%`,
                          }}
                        />
                      </div>
                    </div>
                  )}
                </GlassCard>

                {/* Masterplans */}
                <GlassCard className="p-4">
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <div className="p-2 bg-blue-500/20 backdrop-blur-sm rounded-lg">
                        <FiActivity className="text-blue-400" size={20} />
                      </div>
                      <h3 className="text-sm font-medium text-gray-300">Masterplans</h3>
                    </div>
                  </div>
                  <p className="text-2xl font-bold text-white mb-2">
                    {usage.current_month.masterplans_created}
                  </p>
                  {usage.quota.masterplans_limit && (
                    <div className="mt-3">
                      <div className="flex justify-between text-xs text-gray-400 mb-1">
                        <span>{calculatePercentage(
                          usage.current_month.masterplans_created,
                          usage.quota.masterplans_limit
                        ).toFixed(0)}% used</span>
                        <span>{usage.quota.masterplans_limit} limit</span>
                      </div>
                      <div className="w-full bg-white/10 rounded-full h-2">
                        <div
                          className="bg-blue-500 h-2 rounded-full transition-all"
                          style={{
                            width: `${calculatePercentage(
                              usage.current_month.masterplans_created,
                              usage.quota.masterplans_limit
                            )}%`,
                          }}
                        />
                      </div>
                    </div>
                  )}
                </GlassCard>

                {/* Storage */}
                <GlassCard className="p-4">
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <div className="p-2 bg-emerald-500/20 backdrop-blur-sm rounded-lg">
                        <FiDatabase className="text-emerald-400" size={20} />
                      </div>
                      <h3 className="text-sm font-medium text-gray-300">Storage</h3>
                    </div>
                  </div>
                  <p className="text-2xl font-bold text-white mb-2">
                    {formatBytes(usage.current_month.storage_bytes)}
                  </p>
                  {usage.quota.storage_bytes_limit && (
                    <div className="mt-3">
                      <div className="flex justify-between text-xs text-gray-400 mb-1">
                        <span>{calculatePercentage(
                          usage.current_month.storage_bytes,
                          usage.quota.storage_bytes_limit
                        ).toFixed(0)}% used</span>
                        <span>{formatBytes(usage.quota.storage_bytes_limit)} limit</span>
                      </div>
                      <div className="w-full bg-white/10 rounded-full h-2">
                        <div
                          className="bg-emerald-500 h-2 rounded-full transition-all"
                          style={{
                            width: `${calculatePercentage(
                              usage.current_month.storage_bytes,
                              usage.quota.storage_bytes_limit
                            )}%`,
                          }}
                        />
                      </div>
                    </div>
                  )}
                </GlassCard>

                {/* API Calls */}
                <GlassCard className="p-4">
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <div className="p-2 bg-amber-500/20 backdrop-blur-sm rounded-lg">
                        <FiActivity className="text-amber-400" size={20} />
                      </div>
                      <h3 className="text-sm font-medium text-gray-300">API Calls</h3>
                    </div>
                  </div>
                  <p className="text-2xl font-bold text-white mb-2">
                    {formatNumber(usage.current_month.api_calls)}
                  </p>
                  <p className="text-xs text-gray-400">
                    Rate limit: {usage.quota.api_calls_per_minute} calls/minute
                  </p>
                </GlassCard>
              </div>
          </>
        ) : (
          <div className="p-12 text-center text-gray-400">
            No usage data available
          </div>
        )}
        </GlassCard>
      </div>
    </div>
  )
}
