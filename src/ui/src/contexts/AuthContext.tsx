/**
 * Authentication Context
 *
 * Provides authentication state and methods throughout the application.
 * Handles automatic token refresh and user session management.
 */

import { createContext, useContext, useState, useEffect, ReactNode, useCallback } from 'react'
import { authService, User, LoginRequest, RegisterRequest } from '../services/authService'

interface AuthContextType {
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
  login: (data: LoginRequest) => Promise<void>
  register: (data: RegisterRequest) => Promise<void>
  logout: () => Promise<void>
  refreshUser: () => Promise<void>
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

interface AuthProviderProps {
  children: ReactNode
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  /**
   * Load user on mount if token exists
   */
  useEffect(() => {
    loadUser()
  }, [])

  /**
   * Setup automatic token refresh every 45 minutes
   * (tokens expire after 1 hour, so refresh at 45 min)
   */
  useEffect(() => {
    if (!authService.isAuthenticated()) return

    const interval = setInterval(async () => {
      try {
        await authService.refreshAccessToken()
        console.log('Access token refreshed automatically')
      } catch (error) {
        console.error('Failed to refresh token:', error)
        setUser(null)
      }
    }, 45 * 60 * 1000) // 45 minutes

    return () => clearInterval(interval)
  }, [user])

  /**
   * Load current user from backend
   */
  const loadUser = async () => {
    try {
      if (authService.isAuthenticated()) {
        const currentUser = await authService.getCurrentUser()
        setUser(currentUser)
      }
    } catch (error) {
      console.error('Failed to load user:', error)
      // Token might be invalid, try to refresh
      try {
        await authService.refreshAccessToken()
        const currentUser = await authService.getCurrentUser()
        setUser(currentUser)
      } catch (refreshError) {
        console.error('Token refresh failed:', refreshError)
        setUser(null)
      }
    } finally {
      setIsLoading(false)
    }
  }

  /**
   * Refresh user data from backend
   */
  const refreshUser = useCallback(async () => {
    try {
      const currentUser = await authService.getCurrentUser()
      setUser(currentUser)
    } catch (error) {
      console.error('Failed to refresh user:', error)
      throw error
    }
  }, [])

  /**
   * Login user with email and password
   */
  const login = async (data: LoginRequest) => {
    setIsLoading(true)
    try {
      const response = await authService.login(data)
      setUser(response.user)
    } catch (error) {
      console.error('Login error:', error)
      throw error
    } finally {
      setIsLoading(false)
    }
  }

  /**
   * Register new user
   */
  const register = async (data: RegisterRequest) => {
    setIsLoading(true)
    try {
      const response = await authService.register(data)
      setUser(response.user)
    } catch (error) {
      console.error('Registration error:', error)
      throw error
    } finally {
      setIsLoading(false)
    }
  }

  /**
   * Logout user and clear session
   */
  const logout = async () => {
    setIsLoading(true)
    try {
      await authService.logout()
      setUser(null)
    } catch (error) {
      console.error('Logout error:', error)
      // Clear user even if API call fails
      setUser(null)
    } finally {
      setIsLoading(false)
    }
  }

  const value: AuthContextType = {
    user,
    isAuthenticated: !!user,
    isLoading,
    login,
    register,
    logout,
    refreshUser,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

/**
 * Hook to access auth context
 */
export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
