import { useState } from 'react'
import { BrowserRouter as Router, Routes, Route, useNavigate, useLocation, Navigate } from 'react-router-dom'
import { ChatWindow } from './components/chat/ChatWindow'
import { ProtectedRoute } from './components/ProtectedRoute'
import { useChatStore } from './stores/chatStore'
import { useTheme } from './contexts/ThemeContext'
import { useAuth } from './contexts/AuthContext'
import { FiMessageSquare, FiHome, FiSettings, FiSun, FiMoon, FiMonitor, FiTarget, FiUser, FiLogOut, FiShield, FiCheckCircle } from 'react-icons/fi'
import { MasterplansPage } from './pages/MasterplansPage'
import { ReviewQueue } from './pages/review/ReviewQueue'
import { MasterplanDetailPage } from './pages/MasterplanDetailPage'
import { LoginPage } from './pages/LoginPage'
import { RegisterPage } from './pages/RegisterPage'
import { ForgotPasswordPage } from './pages/ForgotPasswordPage'
import { ResetPasswordPage } from './pages/ResetPasswordPage'
import { ProfilePage } from './pages/ProfilePage'
import { AdminDashboardPage } from './pages/AdminDashboardPage'
import { AdminRoute } from './components/AdminRoute'
import { VerifyEmailPage } from './pages/VerifyEmailPage'
import { VerifyEmailPendingPage } from './pages/VerifyEmailPendingPage'

function AppContent() {
  const { workspaceId } = useChatStore()
  const { theme, setTheme, actualTheme } = useTheme()
  const { user, isAuthenticated, logout } = useAuth()
  const [isMinimized, setIsMinimized] = useState(false)
  const [showUserMenu, setShowUserMenu] = useState(false)
  const navigate = useNavigate()
  const location = useLocation()

  const isActive = (path: string) => {
    if (path === '/') return location.pathname === '/'
    return location.pathname.startsWith(path)
  }

  // Check if current route is an auth page
  const isAuthPage = ['/login', '/register', '/forgot-password', '/reset-password', '/verify-email', '/verify-email-pending'].some(
    path => location.pathname.startsWith(path)
  )

  const handleLogout = async () => {
    await logout()
    setShowUserMenu(false)
    navigate('/login')
  }

  // Don't show sidebar on auth pages
  if (isAuthPage) {
    return (
      <div className="min-h-screen">
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/forgot-password" element={<ForgotPasswordPage />} />
          <Route path="/reset-password" element={<ResetPasswordPage />} />
          <Route path="/verify-email" element={<VerifyEmailPage />} />
          <Route path="/verify-email-pending" element={<VerifyEmailPendingPage />} />
        </Routes>
      </div>
    )
  }

  return (
    <div className="flex h-screen bg-gray-50 dark:bg-gray-900">
      {/* Sidebar */}
      <div className="w-16 bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 flex flex-col items-center py-4 space-y-4">
        <div className="w-10 h-10 bg-gradient-to-br from-primary-600 to-primary-700 rounded-lg flex items-center justify-center text-white font-bold text-lg">
          D
        </div>

        <div className="flex-1 flex flex-col space-y-2">
          <button
            onClick={() => navigate('/')}
            className={`p-3 rounded-lg transition-colors ${
              isActive('/')
                ? 'bg-primary-100 dark:bg-primary-900 text-primary-600 dark:text-primary-400'
                : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700'
            }`}
            aria-label="Home"
          >
            <FiHome size={24} />
          </button>

          <button
            onClick={() => navigate('/chat')}
            className={`p-3 rounded-lg transition-colors ${
              isActive('/chat')
                ? 'bg-primary-100 dark:bg-primary-900 text-primary-600 dark:text-primary-400'
                : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700'
            }`}
            aria-label="Chat"
          >
            <FiMessageSquare size={24} />
          </button>

          <button
            onClick={() => navigate('/masterplans')}
            className={`p-3 rounded-lg transition-colors ${
              isActive('/masterplans')
                ? 'bg-primary-100 dark:bg-primary-900 text-primary-600 dark:text-primary-400'
                : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700'
            }`}
            aria-label="Masterplans"
          >
            <FiTarget size={24} />
          </button>

          <button
            onClick={() => navigate('/review')}
            className={`p-3 rounded-lg transition-colors ${
              isActive('/review')
                ? 'bg-primary-100 dark:bg-primary-900 text-primary-600 dark:text-primary-400'
                : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700'
            }`}
            aria-label="Review Queue"
          >
            <FiCheckCircle size={24} />
          </button>

          <button
            onClick={() => navigate('/settings')}
            className={`p-3 rounded-lg transition-colors ${
              isActive('/settings')
                ? 'bg-primary-100 dark:bg-primary-900 text-primary-600 dark:text-primary-400'
                : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700'
            }`}
            aria-label="Settings"
          >
            <FiSettings size={24} />
          </button>

          {/* Admin Panel - Only visible to superusers */}
          {isAuthenticated && user?.is_superuser && (
            <button
              onClick={() => navigate('/admin')}
              className={`p-3 rounded-lg transition-colors ${
                isActive('/admin')
                  ? 'bg-primary-100 dark:bg-primary-900 text-primary-600 dark:text-primary-400'
                  : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700'
              }`}
              aria-label="Admin"
            >
              <FiShield size={24} />
            </button>
          )}
        </div>

        {/* User Menu - Bottom */}
        {isAuthenticated && user && (
          <div className="relative">
            <button
              onClick={() => setShowUserMenu(!showUserMenu)}
              className="p-3 rounded-lg text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
              aria-label="User menu"
            >
              <FiUser size={24} />
            </button>

            {/* User Dropdown Menu */}
            {showUserMenu && (
              <>
                <div
                  className="fixed inset-0 z-10"
                  onClick={() => setShowUserMenu(false)}
                />
                <div className="absolute bottom-full left-16 mb-2 w-64 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 shadow-xl z-20">
                  <div className="p-4 border-b border-gray-200 dark:border-gray-700">
                    <p className="font-medium text-gray-900 dark:text-white">
                      {user.username}
                    </p>
                    <p className="text-sm text-gray-500 dark:text-gray-400">
                      {user.email}
                    </p>
                  </div>
                  <div className="p-2">
                    <button
                      onClick={() => {
                        navigate('/profile')
                        setShowUserMenu(false)
                      }}
                      className="w-full flex items-center gap-3 px-4 py-2 text-left text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
                    >
                      <FiUser size={18} />
                      <span>Profile</span>
                    </button>
                    <button
                      onClick={handleLogout}
                      className="w-full flex items-center gap-3 px-4 py-2 text-left text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors"
                    >
                      <FiLogOut size={18} />
                      <span>Logout</span>
                    </button>
                  </div>
                </div>
              </>
            )}
          </div>
        )}
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col">
        <Routes>
          {/* Home Page */}
          <Route path="/" element={
            <div className="flex-1 flex items-center justify-center p-8">
              <div className="text-center">
                <h1 className="text-4xl font-bold text-gray-900 dark:text-white mb-4">
                  Welcome to DevMatrix
                </h1>
                <p className="text-lg text-gray-600 dark:text-gray-400 mb-8">
                  AI-powered development environment with multi-agent orchestration
                </p>
                <button
                  onClick={() => navigate('/chat')}
                  className="px-6 py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors font-medium"
                >
                  Start Chat
                </button>
              </div>
            </div>
          } />

          {/* Protected Routes */}
          <Route path="/chat" element={
            <ProtectedRoute>
              <div className="flex-1 p-8">
                <ChatWindow
                  workspaceId={workspaceId || undefined}
                  isMinimized={isMinimized}
                  onToggleMinimize={() => setIsMinimized(!isMinimized)}
                />
              </div>
            </ProtectedRoute>
          } />

          <Route path="/masterplans" element={
            <ProtectedRoute>
              <MasterplansPage />
            </ProtectedRoute>
          } />

          <Route path="/masterplans/:id" element={
            <ProtectedRoute>
              <MasterplanDetailPage />
            </ProtectedRoute>
          } />

          <Route path="/review" element={
            <ProtectedRoute>
              <ReviewQueue />
            </ProtectedRoute>
          } />

          <Route path="/profile" element={
            <ProtectedRoute>
              <ProfilePage />
            </ProtectedRoute>
          } />

          <Route path="/admin" element={
            <AdminRoute>
              <AdminDashboardPage />
            </AdminRoute>
          } />

          <Route path="/settings" element={
            <div className="flex-1 p-8 overflow-auto">
              <div className="max-w-2xl mx-auto">
                <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-6">
                  Settings
                </h2>

                {/* Theme Settings */}
                <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6 mb-6">
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                    Appearance
                  </h3>
                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                        Theme
                      </label>
                      <div className="flex gap-2">
                        <button
                          onClick={() => setTheme('light')}
                          className={`flex-1 p-4 rounded-lg border-2 transition-colors ${
                            theme === 'light'
                              ? 'border-primary-600 bg-primary-50 dark:bg-primary-900/20'
                              : 'border-gray-200 dark:border-gray-700'
                          }`}
                        >
                          <FiSun className="mx-auto mb-2" size={24} />
                          <p className="text-sm font-medium">Light</p>
                        </button>
                        <button
                          onClick={() => setTheme('dark')}
                          className={`flex-1 p-4 rounded-lg border-2 transition-colors ${
                            theme === 'dark'
                              ? 'border-primary-600 bg-primary-50 dark:bg-primary-900/20'
                              : 'border-gray-200 dark:border-gray-700'
                          }`}
                        >
                          <FiMoon className="mx-auto mb-2" size={24} />
                          <p className="text-sm font-medium">Dark</p>
                        </button>
                        <button
                          onClick={() => setTheme('system')}
                          className={`flex-1 p-4 rounded-lg border-2 transition-colors ${
                            theme === 'system'
                              ? 'border-primary-600 bg-primary-50 dark:bg-primary-900/20'
                              : 'border-gray-200 dark:border-gray-700'
                          }`}
                        >
                          <FiMonitor className="mx-auto mb-2" size={24} />
                          <p className="text-sm font-medium">System</p>
                        </button>
                      </div>
                      {theme === 'system' && (
                        <p className="text-xs text-gray-500 dark:text-gray-400 mt-2">
                          Currently using: {actualTheme} theme
                        </p>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          } />

          {/* Catch-all redirect */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </div>
    </div>
  )
}

function App() {
  return (
    <Router>
      <AppContent />
    </Router>
  )
}

export default App
