/**
 * Email Verification Page
 *
 * Verifies user email using the token from the URL query parameter.
 * Handles success, failure, and loading states.
 */

import { useState, useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { authService } from '../services/authService'
import { FiCheckCircle, FiXCircle, FiLoader } from 'react-icons/fi'

export function VerifyEmailPage() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading')
  const [errorMessage, setErrorMessage] = useState<string>('')

  useEffect(() => {
    verifyEmail()
  }, [])

  const verifyEmail = async () => {
    const token = searchParams.get('token')

    if (!token) {
      setStatus('error')
      setErrorMessage('Invalid verification link. No token provided.')
      return
    }

    try {
      await authService.verifyEmail(token)
      setStatus('success')
      // Redirect to login after 3 seconds
      setTimeout(() => {
        navigate('/login')
      }, 3000)
    } catch (error) {
      setStatus('error')
      setErrorMessage(error instanceof Error ? error.message : 'Email verification failed')
    }
  }

  const handleRetry = () => {
    setStatus('loading')
    verifyEmail()
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-purple-900/20 to-blue-900/20 flex items-center justify-center p-4">
      <div className="max-w-md w-full">
        <div className="bg-gradient-to-br from-gray-900/40 via-purple-900/20 to-blue-900/20 backdrop-blur-xl rounded-lg border border-purple-500/20 p-8 text-center shadow-xl shadow-purple-500/10">
          {/* Loading State */}
          {status === 'loading' && (
            <div className="space-y-4">
              <div className="flex justify-center">
                <FiLoader className="text-purple-400 animate-spin" size={64} />
              </div>
              <h2 className="text-2xl font-bold text-purple-100">
                Verifying Email
              </h2>
              <p className="text-purple-300">
                Please wait while we verify your email address...
              </p>
            </div>
          )}

          {/* Success State */}
          {status === 'success' && (
            <div className="space-y-4">
              <div className="flex justify-center">
                <div className="p-4 bg-green-500/20 backdrop-blur-sm rounded-full">
                  <FiCheckCircle className="text-green-400" size={64} />
                </div>
              </div>
              <h2 className="text-2xl font-bold text-purple-100">
                Email Verified!
              </h2>
              <p className="text-purple-300">
                Your email has been successfully verified. You can now access all features.
              </p>
              <p className="text-sm text-purple-400">
                Redirecting to login page...
              </p>
              <button
                onClick={() => navigate('/login')}
                className="w-full px-6 py-3 bg-gradient-to-r from-purple-600/90 to-blue-600/90 text-white rounded-lg hover:from-purple-700/90 hover:to-blue-700/90 transition-colors font-medium backdrop-blur-sm border border-purple-400/30 shadow-lg shadow-purple-500/20"
              >
                Go to Login
              </button>
            </div>
          )}

          {/* Error State */}
          {status === 'error' && (
            <div className="space-y-4">
              <div className="flex justify-center">
                <div className="p-4 bg-red-500/20 backdrop-blur-sm rounded-full">
                  <FiXCircle className="text-red-400" size={64} />
                </div>
              </div>
              <h2 className="text-2xl font-bold text-purple-100">
                Verification Failed
              </h2>
              <p className="text-purple-300">
                {errorMessage}
              </p>
              <div className="space-y-2">
                <button
                  onClick={handleRetry}
                  className="w-full px-6 py-3 bg-gradient-to-r from-purple-600/90 to-blue-600/90 text-white rounded-lg hover:from-purple-700/90 hover:to-blue-700/90 transition-colors font-medium backdrop-blur-sm border border-purple-400/30 shadow-lg shadow-purple-500/20"
                >
                  Try Again
                </button>
                <button
                  onClick={() => navigate('/verify-email-pending')}
                  className="w-full px-6 py-3 bg-white/5 backdrop-blur-sm text-purple-200 rounded-lg hover:bg-white/10 transition-colors font-medium border border-purple-500/20"
                >
                  Resend Verification Email
                </button>
                <button
                  onClick={() => navigate('/login')}
                  className="w-full px-6 py-3 text-purple-400 hover:text-purple-300 transition-colors"
                >
                  Back to Login
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
