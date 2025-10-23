/**
 * Admin Service
 *
 * Handles all admin-related API calls including:
 * - User management (list, view, update, delete)
 * - System statistics
 * - Quota management
 */

import { authService } from './authService'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'

export interface AdminUser {
  user_id: string
  email: string
  username: string
  is_active: boolean
  is_verified: boolean
  is_superuser: boolean
  created_at: string
  last_login_at: string | null
  // Quota information
  llm_tokens_monthly_limit: number | null
  masterplans_limit: number | null
  storage_bytes_limit: number | null
  api_calls_per_minute: number
}

export interface UserUpdateStatus {
  is_active?: boolean
  is_verified?: boolean
  is_superuser?: boolean
}

export interface QuotaUpdate {
  llm_tokens_monthly_limit?: number | null
  masterplans_limit?: number | null
  storage_bytes_limit?: number | null
  api_calls_per_minute?: number
}

export interface SystemStats {
  total_users: number
  active_users: number
  verified_users: number
  total_conversations: number
  total_messages: number
  total_masterplans: number
  total_llm_tokens_used: number
  total_storage_bytes: number
  avg_tokens_per_user: number
  avg_masterplans_per_user: number
}

export interface TopUser {
  user_id: string
  username: string
  email: string
  metric_value: number
  metric_type: string
}

export interface UsersListResponse {
  users: AdminUser[]
  total: number
  page: number
  page_size: number
}

class AdminService {
  /**
   * Get paginated list of all users
   */
  async getUsers(page: number = 1, pageSize: number = 20, search?: string): Promise<UsersListResponse> {
    const params = new URLSearchParams({
      page: page.toString(),
      page_size: pageSize.toString(),
    })

    if (search) {
      params.append('search', search)
    }

    const response = await fetch(`${API_BASE_URL}/admin/users?${params.toString()}`, {
      headers: authService.getAuthHeaders(),
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || 'Failed to fetch users')
    }

    return response.json()
  }

  /**
   * Get detailed information about a specific user
   */
  async getUserDetails(userId: string): Promise<AdminUser> {
    const response = await fetch(`${API_BASE_URL}/admin/users/${userId}`, {
      headers: authService.getAuthHeaders(),
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || 'Failed to fetch user details')
    }

    return response.json()
  }

  /**
   * Update user status (active, verified, superuser)
   */
  async updateUserStatus(userId: string, status: UserUpdateStatus): Promise<AdminUser> {
    const response = await fetch(`${API_BASE_URL}/admin/users/${userId}/status`, {
      method: 'PATCH',
      headers: {
        ...authService.getAuthHeaders(),
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(status),
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || 'Failed to update user status')
    }

    return response.json()
  }

  /**
   * Delete a user
   */
  async deleteUser(userId: string): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/admin/users/${userId}`, {
      method: 'DELETE',
      headers: authService.getAuthHeaders(),
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || 'Failed to delete user')
    }
  }

  /**
   * Update user quota limits
   */
  async updateUserQuota(userId: string, quota: QuotaUpdate): Promise<AdminUser> {
    const response = await fetch(`${API_BASE_URL}/admin/users/${userId}/quota`, {
      method: 'PUT',
      headers: {
        ...authService.getAuthHeaders(),
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(quota),
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || 'Failed to update user quota')
    }

    return response.json()
  }

  /**
   * Get system-wide statistics
   */
  async getSystemStats(): Promise<SystemStats> {
    const response = await fetch(`${API_BASE_URL}/admin/stats`, {
      headers: authService.getAuthHeaders(),
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || 'Failed to fetch system stats')
    }

    return response.json()
  }

  /**
   * Get top users by usage metric
   */
  async getTopUsers(metric: 'tokens' | 'masterplans' | 'storage' | 'api_calls', limit: number = 10): Promise<TopUser[]> {
    const response = await fetch(`${API_BASE_URL}/admin/stats/top-users?metric=${metric}&limit=${limit}`, {
      headers: authService.getAuthHeaders(),
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || 'Failed to fetch top users')
    }

    return response.json()
  }
}

export const adminService = new AdminService()
