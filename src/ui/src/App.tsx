import { useState } from 'react'
import { BrowserRouter as Router, Routes, Route, useNavigate, useLocation, Navigate } from 'react-router-dom'
import { ChatWindow } from './components/chat/ChatWindow'
import { ProtectedRoute } from './components/ProtectedRoute'
import { useChatStore } from './stores/chatStore'
import { useTheme } from './contexts/ThemeContext'
import { useAuth } from './contexts/AuthContext'
import { FiMessageSquare, FiHome, FiSettings, FiSun, FiMoon, FiMonitor, FiTarget, FiUser, FiLogOut, FiShield, FiCheckCircle } from 'react-icons/fi'
import { MasterplansPage } from './pages/MasterplansPage'
import ReviewQueue from './pages/review/ReviewQueue'
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
    <div className="flex h-screen bg-gradient-to-br from-gray-900 via-purple-900/20 to-blue-900/20">
      {/* Sidebar */}
      <div className="w-16 bg-gradient-to-b from-gray-900/40 via-purple-900/20 to-gray-900/40 backdrop-blur-xl border-r border-purple-500/20 flex flex-col items-center py-4 space-y-4">
        <div className="w-10 h-10 bg-gradient-to-br from-purple-600 to-blue-600 rounded-lg flex items-center justify-center text-white font-bold text-lg shadow-lg">
          D
        </div>

        <div className="flex-1 flex flex-col space-y-2">
          <button
            onClick={() => navigate('/')}
            className={`p-3 rounded-lg transition-colors ${
              isActive('/')
                ? 'bg-purple-500/20 backdrop-blur-sm text-purple-400 border border-purple-500/30'
                : 'text-gray-400 hover:bg-white/10 backdrop-blur-sm'
            }`}
            aria-label="Home"
          >
            <FiHome size={24} />
          </button>

          <button
            onClick={() => navigate('/chat')}
            className={`p-3 rounded-lg transition-colors ${
              isActive('/chat')
                ? 'bg-purple-500/20 backdrop-blur-sm text-purple-400 border border-purple-500/30'
                : 'text-gray-400 hover:bg-white/10 backdrop-blur-sm'
            }`}
            aria-label="Chat"
          >
            <FiMessageSquare size={24} />
          </button>

          <button
            onClick={() => navigate('/masterplans')}
            className={`p-3 rounded-lg transition-colors ${
              isActive('/masterplans')
                ? 'bg-purple-500/20 backdrop-blur-sm text-purple-400 border border-purple-500/30'
                : 'text-gray-400 hover:bg-white/10 backdrop-blur-sm'
            }`}
            aria-label="Masterplans"
          >
            <FiTarget size={24} />
          </button>

          <button
            onClick={() => navigate('/review')}
            className={`p-3 rounded-lg transition-colors ${
              isActive('/review')
                ? 'bg-purple-500/20 backdrop-blur-sm text-purple-400 border border-purple-500/30'
                : 'text-gray-400 hover:bg-white/10 backdrop-blur-sm'
            }`}
            aria-label="Review Queue"
          >
            <FiCheckCircle size={24} />
          </button>

          <button
            onClick={() => navigate('/settings')}
            className={`p-3 rounded-lg transition-colors ${
              isActive('/settings')
                ? 'bg-purple-500/20 backdrop-blur-sm text-purple-400 border border-purple-500/30'
                : 'text-gray-400 hover:bg-white/10 backdrop-blur-sm'
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
                  ? 'bg-purple-500/20 backdrop-blur-sm text-purple-400 border border-purple-500/30'
                  : 'text-gray-400 hover:bg-white/10 backdrop-blur-sm'
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
              className="p-3 rounded-lg text-gray-400 hover:bg-white/10 backdrop-blur-sm transition-colors"
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
                <div className="absolute bottom-full left-16 mb-2 w-64 bg-gray-900/95 backdrop-blur-md rounded-lg border border-white/10 shadow-xl z-20">
                  <div className="p-4 border-b border-white/10">
                    <p className="font-medium text-white">
                      {user.username}
                    </p>
                    <p className="text-sm text-gray-400">
                      {user.email}
                    </p>
                  </div>
                  <div className="p-2">
                    <button
                      onClick={() => {
                        navigate('/profile')
                        setShowUserMenu(false)
                      }}
                      className="w-full flex items-center gap-3 px-4 py-2 text-left text-gray-300 hover:bg-white/10 backdrop-blur-sm rounded-lg transition-colors"
                    >
                      <FiUser size={18} />
                      <span>Profile</span>
                    </button>
                    <button
                      onClick={handleLogout}
                      className="w-full flex items-center gap-3 px-4 py-2 text-left text-red-400 hover:bg-red-500/20 backdrop-blur-sm rounded-lg transition-colors"
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
                <h1 className="text-4xl font-bold text-purple-100 mb-4">
                  Welcome to DevMatrix
                </h1>
                <p className="text-lg text-purple-300 mb-8">
                  AI-powered development environment with multi-agent orchestration
                </p>
                <button
                  onClick={() => navigate('/chat')}
                  className="px-6 py-3 bg-gradient-to-r from-purple-600/90 to-blue-600/90 text-white rounded-lg hover:from-purple-700/90 hover:to-blue-700/90 transition-colors font-medium backdrop-blur-sm border border-purple-400/30 shadow-lg shadow-purple-500/20"
                >
                  Start Chat
                </button>
              </div>
            </div>
          } />

          {/* Protected Routes */}
          <Route path="/chat" element={
            <ProtectedRoute>
              <div className="flex-1 p-8 bg-transparent">
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
                <h2 className="text-2xl font-bold text-purple-100 mb-6">
                  Settings
                </h2>

                {/* Theme Settings */}
                <div className="bg-gradient-to-br from-gray-900/40 via-purple-900/20 to-blue-900/20 backdrop-blur-xl rounded-lg border border-purple-500/20 p-6 mb-6 shadow-xl shadow-purple-500/10">
                  <h3 className="text-lg font-semibold text-purple-100 mb-4">
                    Appearance
                  </h3>
                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-purple-200 mb-2">
                        Theme
                      </label>
                      <div className="flex gap-2">
                        <button
                          onClick={() => setTheme('light')}
                          className={`flex-1 p-4 rounded-lg border-2 transition-colors ${
                            theme === 'light'
                              ? 'border-purple-400 bg-purple-500/20 backdrop-blur-sm'
                              : 'border-purple-500/20 bg-white/5 backdrop-blur-sm'
                          }`}
                        >
                          <FiSun className="mx-auto mb-2 text-purple-300" size={24} />
                          <p className="text-sm font-medium text-purple-200">Light</p>
                        </button>
                        <button
                          onClick={() => setTheme('dark')}
                          className={`flex-1 p-4 rounded-lg border-2 transition-colors ${
                            theme === 'dark'
                              ? 'border-purple-400 bg-purple-500/20 backdrop-blur-sm'
                              : 'border-purple-500/20 bg-white/5 backdrop-blur-sm'
                          }`}
                        >
                          <FiMoon className="mx-auto mb-2 text-purple-300" size={24} />
                          <p className="text-sm font-medium text-purple-200">Dark</p>
                        </button>
                        <button
                          onClick={() => setTheme('system')}
                          className={`flex-1 p-4 rounded-lg border-2 transition-colors ${
                            theme === 'system'
                              ? 'border-purple-400 bg-purple-500/20 backdrop-blur-sm'
                              : 'border-purple-500/20 bg-white/5 backdrop-blur-sm'
                          }`}
                        >
                          <FiMonitor className="mx-auto mb-2 text-purple-300" size={24} />
                          <p className="text-sm font-medium text-purple-200">System</p>
                        </button>
                      </div>
                      {theme === 'system' && (
                        <p className="text-xs text-purple-400 mt-2">
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
