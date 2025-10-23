/**
 * User Profile Page
 *
 * Shows user information, usage statistics, and quota limits.
 */

import { useState, useEffect } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { authService } from '../services/authService'
import { FiUser, FiMail, FiCalendar, FiActivity, FiCpu, FiDatabase, FiTrendingUp } from 'react-icons/fi'

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
      const response = await fetch('http://localhost:8000/api/v1/usage/status', {
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
    <div className="flex-1 p-8 overflow-auto">
      <div className="max-w-4xl mx-auto space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
            Profile
          </h1>
          <p className="mt-2 text-gray-600 dark:text-gray-400">
            Manage your account and view usage statistics
          </p>
        </div>

        {/* User Information Card */}
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
            <FiUser /> Account Information
          </h2>
          <div className="space-y-4">
            <div className="flex items-start gap-3">
              <FiUser className="text-gray-400 mt-1" />
              <div>
                <p className="text-sm text-gray-500 dark:text-gray-400">Username</p>
                <p className="font-medium text-gray-900 dark:text-white">{user.username}</p>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <FiMail className="text-gray-400 mt-1" />
              <div>
                <p className="text-sm text-gray-500 dark:text-gray-400">Email</p>
                <p className="font-medium text-gray-900 dark:text-white">{user.email}</p>
                {user.is_verified && (
                  <span className="inline-block mt-1 px-2 py-0.5 bg-green-100 dark:bg-green-900/20 text-green-800 dark:text-green-200 text-xs rounded">
                    Verified
                  </span>
                )}
              </div>
            </div>
            <div className="flex items-start gap-3">
              <FiCalendar className="text-gray-400 mt-1" />
              <div>
                <p className="text-sm text-gray-500 dark:text-gray-400">Member since</p>
                <p className="font-medium text-gray-900 dark:text-white">
                  {new Date(user.created_at).toLocaleDateString('en-US', {
                    year: 'numeric',
                    month: 'long',
                    day: 'numeric',
                  })}
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Usage Statistics */}
        {isLoading ? (
          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-12 text-center">
            <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-primary-600 border-r-transparent"></div>
            <p className="mt-4 text-sm text-gray-600 dark:text-gray-400">
              Loading usage data...
            </p>
          </div>
        ) : usage ? (
          <>
            {/* Current Month Usage */}
            <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
                <FiTrendingUp /> Current Month Usage
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* LLM Tokens */}
                <div className="p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
                  <div className="flex items-center gap-2 mb-2">
                    <FiCpu className="text-primary-600" />
                    <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                      LLM Tokens
                    </span>
                  </div>
                  <p className="text-2xl font-bold text-gray-900 dark:text-white">
                    {formatNumber(usage.current_month.llm_tokens_used)}
                  </p>
                  {usage.quota.llm_tokens_monthly_limit && (
                    <div className="mt-2">
                      <div className="flex justify-between text-xs text-gray-600 dark:text-gray-400 mb-1">
                        <span>{formatNumber(usage.current_month.llm_tokens_used)} used</span>
                        <span>{formatNumber(usage.quota.llm_tokens_monthly_limit)} limit</span>
                      </div>
                      <div className="w-full bg-gray-200 dark:bg-gray-600 rounded-full h-2">
                        <div
                          className="bg-primary-600 h-2 rounded-full"
                          style={{
                            width: `${calculatePercentage(
                              usage.current_month.llm_tokens_used,
                              usage.quota.llm_tokens_monthly_limit
                            )}%`,
                          }}
                        ></div>
                      </div>
                    </div>
                  )}
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-2">
                    Cost: ${usage.current_month.llm_cost_usd.toFixed(2)}
                  </p>
                </div>

                {/* Masterplans */}
                <div className="p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
                  <div className="flex items-center gap-2 mb-2">
                    <FiActivity className="text-purple-600" />
                    <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                      Masterplans
                    </span>
                  </div>
                  <p className="text-2xl font-bold text-gray-900 dark:text-white">
                    {usage.current_month.masterplans_created}
                  </p>
                  {usage.quota.masterplans_limit && (
                    <div className="mt-2">
                      <div className="flex justify-between text-xs text-gray-600 dark:text-gray-400 mb-1">
                        <span>{usage.current_month.masterplans_created} created</span>
                        <span>{usage.quota.masterplans_limit} limit</span>
                      </div>
                      <div className="w-full bg-gray-200 dark:bg-gray-600 rounded-full h-2">
                        <div
                          className="bg-purple-600 h-2 rounded-full"
                          style={{
                            width: `${calculatePercentage(
                              usage.current_month.masterplans_created,
                              usage.quota.masterplans_limit
                            )}%`,
                          }}
                        ></div>
                      </div>
                    </div>
                  )}
                </div>

                {/* Storage */}
                <div className="p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
                  <div className="flex items-center gap-2 mb-2">
                    <FiDatabase className="text-blue-600" />
                    <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                      Storage
                    </span>
                  </div>
                  <p className="text-2xl font-bold text-gray-900 dark:text-white">
                    {formatBytes(usage.current_month.storage_bytes)}
                  </p>
                  {usage.quota.storage_bytes_limit && (
                    <div className="mt-2">
                      <div className="flex justify-between text-xs text-gray-600 dark:text-gray-400 mb-1">
                        <span>{formatBytes(usage.current_month.storage_bytes)} used</span>
                        <span>{formatBytes(usage.quota.storage_bytes_limit)} limit</span>
                      </div>
                      <div className="w-full bg-gray-200 dark:bg-gray-600 rounded-full h-2">
                        <div
                          className="bg-blue-600 h-2 rounded-full"
                          style={{
                            width: `${calculatePercentage(
                              usage.current_month.storage_bytes,
                              usage.quota.storage_bytes_limit
                            )}%`,
                          }}
                        ></div>
                      </div>
                    </div>
                  )}
                </div>

                {/* API Calls */}
                <div className="p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
                  <div className="flex items-center gap-2 mb-2">
                    <FiActivity className="text-green-600" />
                    <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                      API Calls
                    </span>
                  </div>
                  <p className="text-2xl font-bold text-gray-900 dark:text-white">
                    {formatNumber(usage.current_month.api_calls)}
                  </p>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-2">
                    Rate limit: {usage.quota.api_calls_per_minute} calls/minute
                  </p>
                </div>
              </div>
            </div>
          </>
        ) : (
          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6 text-center text-gray-600 dark:text-gray-400">
            No usage data available
          </div>
        )}
      </div>
    </div>
  )
}
