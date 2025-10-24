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
  FiEdit2,
  FiTrash2,
  FiX,
  FiCheck,
  FiAlertCircle,
  FiTrendingUp,
} from 'react-icons/fi'
import {
  PageHeader,
  GlassCard,
  GlassButton,
  GlassInput,
  SearchBar,
  StatusBadge,
  cn,
} from '../components/design-system'
import { CustomAlert } from '../components/review/CustomAlert'
import LoadingState from '../components/review/LoadingState'

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
    <div className="flex-1 p-8 overflow-auto bg-gradient-to-br from-gray-900 via-purple-900/20 to-blue-900/20">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <PageHeader emoji="🛡️" title="Admin Dashboard" />

        {/* Tabs */}
        <div className="border-b border-white/10">
          <nav className="flex gap-8">
            <button
              onClick={() => setActiveTab('overview')}
              className={cn(
                'pb-4 px-4 border-b-2 font-medium transition-colors',
                activeTab === 'overview'
                  ? 'border-purple-600 bg-purple-600 text-white'
                  : 'border-transparent text-gray-400 hover:text-white hover:bg-white/10'
              )}
            >
              Overview
            </button>
            <button
              onClick={() => setActiveTab('users')}
              className={cn(
                'pb-4 px-4 border-b-2 font-medium transition-colors',
                activeTab === 'users'
                  ? 'border-purple-600 bg-purple-600 text-white'
                  : 'border-transparent text-gray-400 hover:text-white hover:bg-white/10'
              )}
            >
              Users
            </button>
            <button
              onClick={() => setActiveTab('analytics')}
              className={cn(
                'pb-4 px-4 border-b-2 font-medium transition-colors',
                activeTab === 'analytics'
                  ? 'border-purple-600 bg-purple-600 text-white'
                  : 'border-transparent text-gray-400 hover:text-white hover:bg-white/10'
              )}
            >
              Analytics
            </button>
          </nav>
        </div>

        {/* Error Display */}
        {error && (
          <CustomAlert
            severity="error"
            message={error}
            onClose={() => setError(null)}
          />
        )}

        {/* Loading State */}
        {isLoading && <LoadingState />}

        {/* Overview Tab */}
        {!isLoading && activeTab === 'overview' && stats && (
          <div className="space-y-6">
            {/* Stats Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              {/* Total Users */}
              <GlassCard className="p-6">
                <div className="flex items-center gap-3 mb-2">
                  <div className="p-2 bg-blue-500/20 backdrop-blur-sm rounded-lg">
                    <FiUsers className="text-blue-400" size={24} />
                  </div>
                  <h3 className="text-sm font-medium text-gray-300">Total Users</h3>
                </div>
                <p className="text-3xl font-bold text-white">{formatNumber(stats.total_users)}</p>
                <p className="text-sm text-gray-300 mt-1">
                  {formatNumber(stats.active_users)} active · {formatNumber(stats.verified_users)} verified
                </p>
              </GlassCard>

              {/* Conversations */}
              <GlassCard className="p-6">
                <div className="flex items-center gap-3 mb-2">
                  <div className="p-2 bg-emerald-500/20 backdrop-blur-sm rounded-lg">
                    <FiActivity className="text-emerald-400" size={24} />
                  </div>
                  <h3 className="text-sm font-medium text-gray-300">Activity</h3>
                </div>
                <p className="text-3xl font-bold text-white">{formatNumber(stats.total_conversations)}</p>
                <p className="text-sm text-gray-300 mt-1">
                  {formatNumber(stats.total_messages)} messages · {formatNumber(stats.total_masterplans)} masterplans
                </p>
              </GlassCard>

              {/* Token Usage */}
              <GlassCard className="p-6">
                <div className="flex items-center gap-3 mb-2">
                  <div className="p-2 bg-purple-500/20 backdrop-blur-sm rounded-lg">
                    <FiCpu className="text-purple-400" size={24} />
                  </div>
                  <h3 className="text-sm font-medium text-gray-300">LLM Tokens</h3>
                </div>
                <p className="text-3xl font-bold text-white">{formatNumber(stats.total_llm_tokens_used)}</p>
                <p className="text-sm text-gray-300 mt-1">
                  {formatNumber(Math.round(stats.avg_tokens_per_user))} avg per user
                </p>
              </GlassCard>

              {/* Storage */}
              <GlassCard className="p-6">
                <div className="flex items-center gap-3 mb-2">
                  <div className="p-2 bg-amber-500/20 backdrop-blur-sm rounded-lg">
                    <FiDatabase className="text-amber-400" size={24} />
                  </div>
                  <h3 className="text-sm font-medium text-gray-300">Storage</h3>
                </div>
                <p className="text-3xl font-bold text-white">{formatBytes(stats.total_storage_bytes)}</p>
                <p className="text-sm text-gray-300 mt-1">
                  Total system usage
                </p>
              </GlassCard>
            </div>
          </div>
        )}

        {/* Users Tab */}
        {!isLoading && activeTab === 'users' && (
          <div className="space-y-6">
            {/* Search Bar */}
            <GlassCard className="p-4">
              <SearchBar
                value={searchQuery}
                onChange={(e) => {
                  setSearchQuery(e.target.value)
                  setCurrentPage(1)
                }}
                placeholder="Search by email or username..."
              />
            </GlassCard>

            {/* Users Table */}
            <GlassCard className="overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-white/5 border-b border-white/10">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">
                        User
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">
                        Status
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">
                        Joined
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">
                        Last Login
                      </th>
                      <th className="px-6 py-3 text-right text-xs font-medium text-gray-300 uppercase tracking-wider">
                        Actions
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/10">
                    {users.map((user) => (
                      <tr key={user.user_id} className="hover:bg-white/5 transition-colors">
                        <td className="px-6 py-4">
                          <div>
                            <p className="font-medium text-white">{user.username}</p>
                            <p className="text-sm text-gray-400">{user.email}</p>
                          </div>
                        </td>
                        <td className="px-6 py-4">
                          <div className="flex flex-col gap-1">
                            {user.is_superuser && (
                              <StatusBadge status="warning">Admin</StatusBadge>
                            )}
                            {user.is_active ? (
                              <StatusBadge status="success">Active</StatusBadge>
                            ) : (
                              <StatusBadge status="default">Inactive</StatusBadge>
                            )}
                            {user.is_verified && (
                              <StatusBadge status="info">✓ Verified</StatusBadge>
                            )}
                          </div>
                        </td>
                        <td className="px-6 py-4 text-sm text-gray-400">
                          {new Date(user.created_at).toLocaleDateString()}
                        </td>
                        <td className="px-6 py-4 text-sm text-gray-400">
                          {user.last_login_at ? new Date(user.last_login_at).toLocaleDateString() : 'Never'}
                        </td>
                        <td className="px-6 py-4 text-right">
                          <GlassButton
                            variant="ghost"
                            size="sm"
                            onClick={() => setSelectedUser(user)}
                            aria-label="Edit user"
                          >
                            <FiEdit2 size={16} />
                          </GlassButton>
                          <GlassButton
                            variant="ghost"
                            size="sm"
                            onClick={() => setDeleteConfirmUser(user)}
                            aria-label="Delete user"
                            className="ml-2"
                          >
                            <FiTrash2 size={16} className="text-red-400" />
                          </GlassButton>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Pagination */}
              <div className="px-6 py-4 bg-white/5 border-t border-white/10 flex items-center justify-between">
                <p className="text-sm text-gray-400">
                  Showing <span className="font-medium">{(currentPage - 1) * pageSize + 1}</span> to{' '}
                  <span className="font-medium">{Math.min(currentPage * pageSize, totalUsers)}</span> of{' '}
                  <span className="font-medium">{totalUsers}</span> users
                </p>
                <div className="flex gap-2">
                  <GlassButton
                    variant="ghost"
                    disabled={currentPage === 1}
                    onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
                  >
                    Previous
                  </GlassButton>
                  <GlassButton
                    variant="ghost"
                    disabled={currentPage * pageSize >= totalUsers}
                    onClick={() => setCurrentPage(currentPage + 1)}
                  >
                    Next
                  </GlassButton>
                </div>
              </div>
            </GlassCard>
          </div>
        )}

        {/* Analytics Tab */}
        {!isLoading && activeTab === 'analytics' && (
          <div className="space-y-6">
            {/* Metric Selector */}
            <GlassCard className="p-4">
              <label className="block text-sm font-medium text-white mb-2">
                Top Users By
              </label>
              <select
                value={topUsersMetric}
                onChange={(e) => setTopUsersMetric(e.target.value as any)}
                className="w-full px-4 py-2 bg-white/5 border border-white/20 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-purple-500"
              >
                <option value="tokens" className="bg-gray-800">LLM Tokens Used</option>
                <option value="masterplans" className="bg-gray-800">Masterplans Created</option>
                <option value="storage" className="bg-gray-800">Storage Used</option>
                <option value="api_calls" className="bg-gray-800">API Calls</option>
              </select>
            </GlassCard>

            {/* Top Users List */}
            <GlassCard className="p-6">
              <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                <FiTrendingUp className="text-purple-400" /> Top 10 Users
              </h3>
              <div className="space-y-3">
                {topUsers.map((user, index) => (
                  <div
                    key={user.user_id}
                    className="flex items-center justify-between p-4 bg-white/5 rounded-lg hover:bg-white/10 transition-colors"
                  >
                    <div className="flex items-center gap-4">
                      <div className="flex items-center justify-center w-8 h-8 bg-purple-500/20 text-purple-400 rounded-full font-bold">
                        {index + 1}
                      </div>
                      <div>
                        <p className="font-medium text-white">{user.username}</p>
                        <p className="text-sm text-gray-400">{user.email}</p>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="font-bold text-gray-300">
                        {topUsersMetric === 'storage' ? formatBytes(user.metric_value) : formatNumber(user.metric_value)}
                      </p>
                      <p className="text-xs text-gray-400">
                        {topUsersMetric === 'tokens' && 'tokens'}
                        {topUsersMetric === 'masterplans' && 'masterplans'}
                        {topUsersMetric === 'storage' && 'used'}
                        {topUsersMetric === 'api_calls' && 'calls'}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </GlassCard>
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
    <div
      className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4"
      onClick={onClose}
    >
      <div onClick={(e: React.MouseEvent) => e.stopPropagation()}>
        <GlassCard className="max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
          <div className="sticky top-0 bg-gray-900/80 backdrop-blur-sm border-b border-white/10 px-6 py-4 flex items-center justify-between">
          <h2 className="text-xl font-bold text-white">Edit User</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white transition-colors"
            aria-label="Close modal"
          >
            <FiX size={24} />
          </button>
        </div>

        <div className="p-6 space-y-6">
          {/* User Info */}
          <div>
            <h3 className="text-lg font-semibold text-white mb-3">User Information</h3>
            <div className="space-y-2 text-sm">
              <p className="text-gray-300">
                <span className="font-medium">Username:</span> {user.username}
              </p>
              <p className="text-gray-300">
                <span className="font-medium">Email:</span> {user.email}
              </p>
              <p className="text-gray-300">
                <span className="font-medium">User ID:</span> {user.user_id}
              </p>
              <p className="text-gray-300">
                <span className="font-medium">Created:</span> {new Date(user.created_at).toLocaleString()}
              </p>
            </div>
          </div>

          {/* Status Settings */}
          <div className="border-t border-white/10 pt-6">
            <h3 className="text-lg font-semibold text-white mb-3">Status Settings</h3>
            <div className="space-y-3">
              <label className="flex items-center gap-3">
                <input
                  type="checkbox"
                  checked={isActive}
                  onChange={(e) => setIsActive(e.target.checked)}
                  className="w-4 h-4 text-purple-600 bg-white/10 border-white/20 rounded focus:ring-2 focus:ring-purple-500"
                />
                <span className="text-gray-300">Active</span>
              </label>
              <label className="flex items-center gap-3">
                <input
                  type="checkbox"
                  checked={isVerified}
                  onChange={(e) => setIsVerified(e.target.checked)}
                  className="w-4 h-4 text-purple-600 bg-white/10 border-white/20 rounded focus:ring-2 focus:ring-purple-500"
                />
                <span className="text-gray-300">Verified</span>
              </label>
              <label className="flex items-center gap-3">
                <input
                  type="checkbox"
                  checked={isSuperuser}
                  onChange={(e) => setIsSuperuser(e.target.checked)}
                  className="w-4 h-4 text-purple-600 bg-white/10 border-white/20 rounded focus:ring-2 focus:ring-purple-500"
                />
                <span className="text-gray-300">Superuser (Admin)</span>
              </label>
            </div>
            <GlassButton
              variant="primary"
              onClick={handleSaveStatus}
              className="mt-4"
            >
              <FiCheck size={18} />
              Save Status
            </GlassButton>
          </div>

          {/* Quota Settings */}
          <div className="border-t border-white/10 pt-6">
            <h3 className="text-lg font-semibold text-white mb-3">Quota Settings</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">
                  LLM Tokens Monthly Limit
                </label>
                <GlassInput
                  type="number"
                  value={tokenLimit}
                  onChange={(e) => setTokenLimit(e.target.value)}
                  placeholder="Unlimited"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">
                  Masterplans Limit
                </label>
                <GlassInput
                  type="number"
                  value={masterplansLimit}
                  onChange={(e) => setMasterplansLimit(e.target.value)}
                  placeholder="Unlimited"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">
                  Storage Limit (bytes)
                </label>
                <GlassInput
                  type="number"
                  value={storageLimit}
                  onChange={(e) => setStorageLimit(e.target.value)}
                  placeholder="Unlimited"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">
                  API Calls Per Minute
                </label>
                <GlassInput
                  type="number"
                  value={apiCallsLimit}
                  onChange={(e) => setApiCallsLimit(e.target.value)}
                />
              </div>
            </div>
            <GlassButton
              variant="primary"
              onClick={handleSaveQuota}
              className="mt-4"
            >
              <FiCheck size={18} />
              Save Quota
            </GlassButton>
          </div>
        </div>
        </GlassCard>
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
    <div
      className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4"
      onClick={onCancel}
    >
      <div onClick={(e: React.MouseEvent) => e.stopPropagation()}>
        <GlassCard className="max-w-md w-full mx-4">
          <div className="p-6">
          <div className="flex items-center gap-3 mb-4">
            <div className="p-2 bg-red-500/20 backdrop-blur-sm rounded-lg">
              <FiAlertCircle className="text-red-400" size={24} />
            </div>
            <h2 className="text-xl font-bold text-white">Delete User</h2>
          </div>
          <p className="text-gray-300 mb-6">
            Are you sure you want to delete user <span className="font-medium text-white">{user.username}</span> ({user.email})?
            This action cannot be undone.
          </p>
          <div className="flex gap-3">
            <GlassButton
              variant="primary"
              onClick={onConfirm}
              className="flex-1 bg-red-600 hover:bg-red-700"
            >
              Delete
            </GlassButton>
            <GlassButton
              variant="ghost"
              onClick={onCancel}
              className="flex-1"
            >
              Cancel
            </GlassButton>
          </div>
          </div>
        </GlassCard>
      </div>
    </div>
  )
}
