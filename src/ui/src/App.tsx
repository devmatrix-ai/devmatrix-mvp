import { useState } from 'react'
import { ChatWindow } from './components/chat/ChatWindow'
import { useChatStore } from './stores/chatStore'
import { useTheme } from './contexts/ThemeContext'
import { FiMessageSquare, FiHome, FiSettings, FiSun, FiMoon, FiMonitor } from 'react-icons/fi'

function App() {
  const { workspaceId } = useChatStore()
  const { theme, setTheme, actualTheme } = useTheme()
  const [isMinimized, setIsMinimized] = useState(false)
  const [activeTab, setActiveTab] = useState<'home' | 'chat' | 'settings'>('chat')

  return (
    <div className="flex h-screen bg-gray-50 dark:bg-gray-900">
      {/* Sidebar */}
      <div className="w-16 bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 flex flex-col items-center py-4 space-y-4">
        <div className="w-10 h-10 bg-gradient-to-br from-primary-600 to-primary-700 rounded-lg flex items-center justify-center text-white font-bold text-lg">
          D
        </div>

        <div className="flex-1 flex flex-col space-y-2">
          <button
            onClick={() => setActiveTab('home')}
            className={`p-3 rounded-lg transition-colors ${
              activeTab === 'home'
                ? 'bg-primary-100 dark:bg-primary-900 text-primary-600 dark:text-primary-400'
                : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700'
            }`}
            aria-label="Home"
          >
            <FiHome size={24} />
          </button>

          <button
            onClick={() => setActiveTab('chat')}
            className={`p-3 rounded-lg transition-colors ${
              activeTab === 'chat'
                ? 'bg-primary-100 dark:bg-primary-900 text-primary-600 dark:text-primary-400'
                : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700'
            }`}
            aria-label="Chat"
          >
            <FiMessageSquare size={24} />
          </button>

          <button
            onClick={() => setActiveTab('settings')}
            className={`p-3 rounded-lg transition-colors ${
              activeTab === 'settings'
                ? 'bg-primary-100 dark:bg-primary-900 text-primary-600 dark:text-primary-400'
                : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700'
            }`}
            aria-label="Settings"
          >
            <FiSettings size={24} />
          </button>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col">
        {activeTab === 'home' && (
          <div className="flex-1 flex items-center justify-center p-8">
            <div className="text-center">
              <h1 className="text-4xl font-bold text-gray-900 dark:text-white mb-4">
                Welcome to DevMatrix
              </h1>
              <p className="text-lg text-gray-600 dark:text-gray-400 mb-8">
                AI-powered development environment with multi-agent orchestration
              </p>
              <button
                onClick={() => setActiveTab('chat')}
                className="px-6 py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors font-medium"
              >
                Start Chat
              </button>
            </div>
          </div>
        )}

        {activeTab === 'chat' && (
          <div className="flex-1 p-8">
            <ChatWindow
              workspaceId={workspaceId || undefined}
              isMinimized={isMinimized}
              onToggleMinimize={() => setIsMinimized(!isMinimized)}
            />
          </div>
        )}

        {activeTab === 'settings' && (
          <div className="flex-1 p-8">
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

              {/* More settings coming soon */}
              <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
                <p className="text-gray-600 dark:text-gray-400">
                  More settings coming soon...
                </p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default App
