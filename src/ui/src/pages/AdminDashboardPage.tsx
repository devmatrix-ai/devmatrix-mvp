/**
 * Admin Dashboard Page
 *
 * Comprehensive admin interface for:
 * - System statistics and monitoring
 * - User management (CRUD operations)
 * - Quota management
 * - Top users analytics
 */

import { useState, useEffect } from 'react'
import { adminService, AdminUser, SystemStats, TopUser, QuotaUpdate, UserUpdateStatus } from '../services/adminService'
import {
  FiUsers,
  FiActivity,
  FiDatabase,
  FiCpu,
  FiSearch,
  FiEdit2,
  FiTrash2,
  FiX,
  FiCheck,
  FiAlertCircle,
  FiTrendingUp,
} from 'react-icons/fi'

export function AdminDashboardPage() {
  const [activeTab, setActiveTab] = useState<'overview' | 'users' | 'analytics'>('overview')
  const [stats, setStats] = useState<SystemStats | null>(null)
  const [users, setUsers] = useState<AdminUser[]>([])
  const [totalUsers, setTotalUsers] = useState(0)
  const [currentPage, setCurrentPage] = useState(1)
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedUser, setSelectedUser] = useState<AdminUser | null>(null)
  const [deleteConfirmUser, setDeleteConfirmUser] = useState<AdminUser | null>(null)
  const [topUsers, setTopUsers] = useState<TopUser[]>([])
  const [topUsersMetric, setTopUsersMetric] = useState<'tokens' | 'masterplans' | 'storage' | 'api_calls'>('tokens')
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const pageSize = 20

  // Load data on mount and tab change
  useEffect(() => {
    loadData()
  }, [activeTab, currentPage, searchQuery, topUsersMetric])

  const loadData = async () => {
    setIsLoading(true)
    setError(null)

    try {
      if (activeTab === 'overview') {
        const statsData = await adminService.getSystemStats()
        setStats(statsData)
      } else if (activeTab === 'users') {
        const usersData = await adminService.getUsers(currentPage, pageSize, searchQuery || undefined)
        setUsers(usersData.users)
        setTotalUsers(usersData.total)
      } else if (activeTab === 'analytics') {
        const topUsersData = await adminService.getTopUsers(topUsersMetric, 10)
        setTopUsers(topUsersData)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load data')
    } finally {
      setIsLoading(false)
    }
  }

  const handleUserStatusUpdate = async (userId: string, status: UserUpdateStatus) => {
    try {
      const updatedUser = await adminService.updateUserStatus(userId, status)
      setUsers(users.map(u => u.user_id === userId ? updatedUser : u))
      if (selectedUser?.user_id === userId) {
        setSelectedUser(updatedUser)
      }
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to update user status')
    }
  }

  const handleQuotaUpdate = async (userId: string, quota: QuotaUpdate) => {
    try {
      const updatedUser = await adminService.updateUserQuota(userId, quota)
      setUsers(users.map(u => u.user_id === userId ? updatedUser : u))
      if (selectedUser?.user_id === userId) {
        setSelectedUser(updatedUser)
      }
      alert('Quota updated successfully')
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to update quota')
    }
  }

  const handleDeleteUser = async (userId: string) => {
    try {
      await adminService.deleteUser(userId)
      setUsers(users.filter(u => u.user_id !== userId))
      setDeleteConfirmUser(null)
      setSelectedUser(null)
      setTotalUsers(totalUsers - 1)
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to delete user')
    }
  }

  const formatNumber = (num: number) => new Intl.NumberFormat().format(num)
  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 B'
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
  }

  return (
    <div className="flex-1 p-8 overflow-auto">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
            Admin Dashboard
          </h1>
          <p className="mt-2 text-gray-600 dark:text-gray-400">
            System management and user administration
          </p>
        </div>

        {/* Tabs */}
        <div className="border-b border-gray-200 dark:border-gray-700">
          <nav className="flex gap-8">
            <button
              onClick={() => setActiveTab('overview')}
              className={`pb-4 border-b-2 font-medium transition-colors ${
                activeTab === 'overview'
                  ? 'border-primary-600 text-primary-600 dark:text-primary-400'
                  : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'
              }`}
            >
              Overview
            </button>
            <button
              onClick={() => setActiveTab('users')}
              className={`pb-4 border-b-2 font-medium transition-colors ${
                activeTab === 'users'
                  ? 'border-primary-600 text-primary-600 dark:text-primary-400'
                  : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'
              }`}
            >
              Users
            </button>
            <button
              onClick={() => setActiveTab('analytics')}
              className={`pb-4 border-b-2 font-medium transition-colors ${
                activeTab === 'analytics'
                  ? 'border-primary-600 text-primary-600 dark:text-primary-400'
                  : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'
              }`}
            >
              Analytics
            </button>
          </nav>
        </div>

        {/* Error Display */}
        {error && (
          <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4 flex items-start gap-3">
            <FiAlertCircle className="text-red-600 dark:text-red-400 mt-0.5" size={20} />
            <div>
              <p className="font-medium text-red-900 dark:text-red-100">Error</p>
              <p className="text-sm text-red-700 dark:text-red-300">{error}</p>
            </div>
          </div>
        )}

        {/* Loading State */}
        {isLoading && (
          <div className="flex justify-center py-12">
            <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-primary-600 border-r-transparent"></div>
          </div>
        )}

        {/* Overview Tab */}
        {!isLoading && activeTab === 'overview' && stats && (
          <div className="space-y-6">
            {/* Stats Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              {/* Total Users */}
              <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
                <div className="flex items-center gap-3 mb-2">
                  <div className="p-2 bg-blue-100 dark:bg-blue-900/20 rounded-lg">
                    <FiUsers className="text-blue-600 dark:text-blue-400" size={24} />
                  </div>
                  <h3 className="text-sm font-medium text-gray-600 dark:text-gray-400">Total Users</h3>
                </div>
                <p className="text-3xl font-bold text-gray-900 dark:text-white">{formatNumber(stats.total_users)}</p>
                <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                  {formatNumber(stats.active_users)} active · {formatNumber(stats.verified_users)} verified
                </p>
              </div>

              {/* Conversations */}
              <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
                <div className="flex items-center gap-3 mb-2">
                  <div className="p-2 bg-green-100 dark:bg-green-900/20 rounded-lg">
                    <FiActivity className="text-green-600 dark:text-green-400" size={24} />
                  </div>
                  <h3 className="text-sm font-medium text-gray-600 dark:text-gray-400">Activity</h3>
                </div>
                <p className="text-3xl font-bold text-gray-900 dark:text-white">{formatNumber(stats.total_conversations)}</p>
                <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                  {formatNumber(stats.total_messages)} messages · {formatNumber(stats.total_masterplans)} masterplans
                </p>
              </div>

              {/* Token Usage */}
              <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
                <div className="flex items-center gap-3 mb-2">
                  <div className="p-2 bg-purple-100 dark:bg-purple-900/20 rounded-lg">
                    <FiCpu className="text-purple-600 dark:text-purple-400" size={24} />
                  </div>
                  <h3 className="text-sm font-medium text-gray-600 dark:text-gray-400">LLM Tokens</h3>
                </div>
                <p className="text-3xl font-bold text-gray-900 dark:text-white">{formatNumber(stats.total_llm_tokens_used)}</p>
                <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                  {formatNumber(Math.round(stats.avg_tokens_per_user))} avg per user
                </p>
              </div>

              {/* Storage */}
              <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
                <div className="flex items-center gap-3 mb-2">
                  <div className="p-2 bg-orange-100 dark:bg-orange-900/20 rounded-lg">
                    <FiDatabase className="text-orange-600 dark:text-orange-400" size={24} />
                  </div>
                  <h3 className="text-sm font-medium text-gray-600 dark:text-gray-400">Storage</h3>
                </div>
                <p className="text-3xl font-bold text-gray-900 dark:text-white">{formatBytes(stats.total_storage_bytes)}</p>
                <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                  Total system usage
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Users Tab */}
        {!isLoading && activeTab === 'users' && (
          <div className="space-y-6">
            {/* Search Bar */}
            <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
              <div className="relative">
                <FiSearch className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={20} />
                <input
                  type="text"
                  placeholder="Search by email or username..."
                  value={searchQuery}
                  onChange={(e) => {
                    setSearchQuery(e.target.value)
                    setCurrentPage(1)
                  }}
                  className="w-full pl-10 pr-4 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                />
              </div>
            </div>

            {/* Users Table */}
            <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-gray-50 dark:bg-gray-700 border-b border-gray-200 dark:border-gray-600">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                        User
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                        Status
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                        Joined
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                        Last Login
                      </th>
                      <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                        Actions
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                    {users.map((user) => (
                      <tr key={user.user_id} className="hover:bg-gray-50 dark:hover:bg-gray-700/50">
                        <td className="px-6 py-4">
                          <div>
                            <p className="font-medium text-gray-900 dark:text-white">{user.username}</p>
                            <p className="text-sm text-gray-500 dark:text-gray-400">{user.email}</p>
                          </div>
                        </td>
                        <td className="px-6 py-4">
                          <div className="flex flex-col gap-1">
                            {user.is_superuser && (
                              <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-purple-100 dark:bg-purple-900/20 text-purple-800 dark:text-purple-200">
                                Admin
                              </span>
                            )}
                            {user.is_active ? (
                              <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 dark:bg-green-900/20 text-green-800 dark:text-green-200">
                                Active
                              </span>
                            ) : (
                              <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-red-100 dark:bg-red-900/20 text-red-800 dark:text-red-200">
                                Inactive
                              </span>
                            )}
                            {user.is_verified && (
                              <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 dark:bg-blue-900/20 text-blue-800 dark:text-blue-200">
                                Verified
                              </span>
                            )}
                          </div>
                        </td>
                        <td className="px-6 py-4 text-sm text-gray-500 dark:text-gray-400">
                          {new Date(user.created_at).toLocaleDateString()}
                        </td>
                        <td className="px-6 py-4 text-sm text-gray-500 dark:text-gray-400">
                          {user.last_login_at ? new Date(user.last_login_at).toLocaleDateString() : 'Never'}
                        </td>
                        <td className="px-6 py-4 text-right">
                          <button
                            onClick={() => setSelectedUser(user)}
                            className="text-primary-600 dark:text-primary-400 hover:text-primary-700 dark:hover:text-primary-300 mr-3"
                            aria-label="Edit user"
                          >
                            <FiEdit2 size={18} />
                          </button>
                          <button
                            onClick={() => setDeleteConfirmUser(user)}
                            className="text-red-600 dark:text-red-400 hover:text-red-700 dark:hover:text-red-300"
                            aria-label="Delete user"
                          >
                            <FiTrash2 size={18} />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Pagination */}
              <div className="px-6 py-4 bg-gray-50 dark:bg-gray-700 border-t border-gray-200 dark:border-gray-600 flex items-center justify-between">
                <p className="text-sm text-gray-700 dark:text-gray-300">
                  Showing <span className="font-medium">{(currentPage - 1) * pageSize + 1}</span> to{' '}
                  <span className="font-medium">{Math.min(currentPage * pageSize, totalUsers)}</span> of{' '}
                  <span className="font-medium">{totalUsers}</span> users
                </p>
                <div className="flex gap-2">
                  <button
                    onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
                    disabled={currentPage === 1}
                    className="px-4 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
                  >
                    Previous
                  </button>
                  <button
                    onClick={() => setCurrentPage(currentPage + 1)}
                    disabled={currentPage * pageSize >= totalUsers}
                    className="px-4 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
                  >
                    Next
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Analytics Tab */}
        {!isLoading && activeTab === 'analytics' && (
          <div className="space-y-6">
            {/* Metric Selector */}
            <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Top Users By
              </label>
              <select
                value={topUsersMetric}
                onChange={(e) => setTopUsersMetric(e.target.value as any)}
                className="w-full px-4 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
              >
                <option value="tokens">LLM Tokens Used</option>
                <option value="masterplans">Masterplans Created</option>
                <option value="storage">Storage Used</option>
                <option value="api_calls">API Calls</option>
              </select>
            </div>

            {/* Top Users List */}
            <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
                <FiTrendingUp /> Top 10 Users
              </h3>
              <div className="space-y-3">
                {topUsers.map((user, index) => (
                  <div
                    key={user.user_id}
                    className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg"
                  >
                    <div className="flex items-center gap-4">
                      <div className="flex items-center justify-center w-8 h-8 bg-primary-100 dark:bg-primary-900/20 text-primary-600 dark:text-primary-400 rounded-full font-bold">
                        {index + 1}
                      </div>
                      <div>
                        <p className="font-medium text-gray-900 dark:text-white">{user.username}</p>
                        <p className="text-sm text-gray-500 dark:text-gray-400">{user.email}</p>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="font-bold text-gray-900 dark:text-white">
                        {topUsersMetric === 'storage' ? formatBytes(user.metric_value) : formatNumber(user.metric_value)}
                      </p>
                      <p className="text-xs text-gray-500 dark:text-gray-400">
                        {topUsersMetric === 'tokens' && 'tokens'}
                        {topUsersMetric === 'masterplans' && 'masterplans'}
                        {topUsersMetric === 'storage' && 'used'}
                        {topUsersMetric === 'api_calls' && 'calls'}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* User Edit Modal */}
      {selectedUser && (
        <UserEditModal
          user={selectedUser}
          onClose={() => setSelectedUser(null)}
          onUpdateStatus={handleUserStatusUpdate}
          onUpdateQuota={handleQuotaUpdate}
        />
      )}

      {/* Delete Confirmation Modal */}
      {deleteConfirmUser && (
        <DeleteConfirmModal
          user={deleteConfirmUser}
          onConfirm={() => handleDeleteUser(deleteConfirmUser.user_id)}
          onCancel={() => setDeleteConfirmUser(null)}
        />
      )}
    </div>
  )
}

// User Edit Modal Component
interface UserEditModalProps {
  user: AdminUser
  onClose: () => void
  onUpdateStatus: (userId: string, status: UserUpdateStatus) => void
  onUpdateQuota: (userId: string, quota: QuotaUpdate) => void
}

function UserEditModal({ user, onClose, onUpdateStatus, onUpdateQuota }: UserEditModalProps) {
  const [isActive, setIsActive] = useState(user.is_active)
  const [isVerified, setIsVerified] = useState(user.is_verified)
  const [isSuperuser, setIsSuperuser] = useState(user.is_superuser)
  const [tokenLimit, setTokenLimit] = useState(user.llm_tokens_monthly_limit?.toString() || '')
  const [masterplansLimit, setMasterplansLimit] = useState(user.masterplans_limit?.toString() || '')
  const [storageLimit, setStorageLimit] = useState(user.storage_bytes_limit?.toString() || '')
  const [apiCallsLimit, setApiCallsLimit] = useState(user.api_calls_per_minute?.toString() || '60')

  const handleSaveStatus = () => {
    onUpdateStatus(user.user_id, {
      is_active: isActive,
      is_verified: isVerified,
      is_superuser: isSuperuser,
    })
  }

  const handleSaveQuota = () => {
    onUpdateQuota(user.user_id, {
      llm_tokens_monthly_limit: tokenLimit ? parseInt(tokenLimit) : null,
      masterplans_limit: masterplansLimit ? parseInt(masterplansLimit) : null,
      storage_bytes_limit: storageLimit ? parseInt(storageLimit) : null,
      api_calls_per_minute: parseInt(apiCallsLimit),
    })
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white dark:bg-gray-800 rounded-lg max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        <div className="sticky top-0 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 px-6 py-4 flex items-center justify-between">
          <h2 className="text-xl font-bold text-gray-900 dark:text-white">Edit User</h2>
          <button
            onClick={onClose}
            className="text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300"
          >
            <FiX size={24} />
          </button>
        </div>

        <div className="p-6 space-y-6">
          {/* User Info */}
          <div>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-3">User Information</h3>
            <div className="space-y-2 text-sm">
              <p className="text-gray-600 dark:text-gray-400">
                <span className="font-medium">Username:</span> {user.username}
              </p>
              <p className="text-gray-600 dark:text-gray-400">
                <span className="font-medium">Email:</span> {user.email}
              </p>
              <p className="text-gray-600 dark:text-gray-400">
                <span className="font-medium">User ID:</span> {user.user_id}
              </p>
              <p className="text-gray-600 dark:text-gray-400">
                <span className="font-medium">Created:</span> {new Date(user.created_at).toLocaleString()}
              </p>
            </div>
          </div>

          {/* Status Settings */}
          <div>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-3">Status Settings</h3>
            <div className="space-y-3">
              <label className="flex items-center gap-3">
                <input
                  type="checkbox"
                  checked={isActive}
                  onChange={(e) => setIsActive(e.target.checked)}
                  className="w-4 h-4 text-primary-600 rounded focus:ring-2 focus:ring-primary-500"
                />
                <span className="text-gray-700 dark:text-gray-300">Active</span>
              </label>
              <label className="flex items-center gap-3">
                <input
                  type="checkbox"
                  checked={isVerified}
                  onChange={(e) => setIsVerified(e.target.checked)}
                  className="w-4 h-4 text-primary-600 rounded focus:ring-2 focus:ring-primary-500"
                />
                <span className="text-gray-700 dark:text-gray-300">Verified</span>
              </label>
              <label className="flex items-center gap-3">
                <input
                  type="checkbox"
                  checked={isSuperuser}
                  onChange={(e) => setIsSuperuser(e.target.checked)}
                  className="w-4 h-4 text-primary-600 rounded focus:ring-2 focus:ring-primary-500"
                />
                <span className="text-gray-700 dark:text-gray-300">Superuser (Admin)</span>
              </label>
            </div>
            <button
              onClick={handleSaveStatus}
              className="mt-4 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors flex items-center gap-2"
            >
              <FiCheck size={18} />
              Save Status
            </button>
          </div>

          {/* Quota Settings */}
          <div>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-3">Quota Settings</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  LLM Tokens Monthly Limit
                </label>
                <input
                  type="number"
                  value={tokenLimit}
                  onChange={(e) => setTokenLimit(e.target.value)}
                  placeholder="Unlimited"
                  className="w-full px-4 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Masterplans Limit
                </label>
                <input
                  type="number"
                  value={masterplansLimit}
                  onChange={(e) => setMasterplansLimit(e.target.value)}
                  placeholder="Unlimited"
                  className="w-full px-4 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Storage Limit (bytes)
                </label>
                <input
                  type="number"
                  value={storageLimit}
                  onChange={(e) => setStorageLimit(e.target.value)}
                  placeholder="Unlimited"
                  className="w-full px-4 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  API Calls Per Minute
                </label>
                <input
                  type="number"
                  value={apiCallsLimit}
                  onChange={(e) => setApiCallsLimit(e.target.value)}
                  className="w-full px-4 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                />
              </div>
            </div>
            <button
              onClick={handleSaveQuota}
              className="mt-4 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors flex items-center gap-2"
            >
              <FiCheck size={18} />
              Save Quota
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

// Delete Confirmation Modal Component
interface DeleteConfirmModalProps {
  user: AdminUser
  onConfirm: () => void
  onCancel: () => void
}

function DeleteConfirmModal({ user, onConfirm, onCancel }: DeleteConfirmModalProps) {
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white dark:bg-gray-800 rounded-lg max-w-md w-full p-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2 bg-red-100 dark:bg-red-900/20 rounded-lg">
            <FiAlertCircle className="text-red-600 dark:text-red-400" size={24} />
          </div>
          <h2 className="text-xl font-bold text-gray-900 dark:text-white">Delete User</h2>
        </div>
        <p className="text-gray-600 dark:text-gray-400 mb-6">
          Are you sure you want to delete user <span className="font-medium">{user.username}</span> ({user.email})?
          This action cannot be undone.
        </p>
        <div className="flex gap-3">
          <button
            onClick={onConfirm}
            className="flex-1 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
          >
            Delete
          </button>
          <button
            onClick={onCancel}
            className="flex-1 px-4 py-2 bg-gray-200 dark:bg-gray-700 text-gray-900 dark:text-white rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  )
}
