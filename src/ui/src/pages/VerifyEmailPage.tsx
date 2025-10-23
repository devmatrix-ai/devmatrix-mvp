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
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center p-4">
      <div className="max-w-md w-full">
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-8 text-center">
          {/* Loading State */}
          {status === 'loading' && (
            <div className="space-y-4">
              <div className="flex justify-center">
                <FiLoader className="text-primary-600 dark:text-primary-400 animate-spin" size={64} />
              </div>
              <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
                Verifying Email
              </h2>
              <p className="text-gray-600 dark:text-gray-400">
                Please wait while we verify your email address...
              </p>
            </div>
          )}

          {/* Success State */}
          {status === 'success' && (
            <div className="space-y-4">
              <div className="flex justify-center">
                <div className="p-4 bg-green-100 dark:bg-green-900/20 rounded-full">
                  <FiCheckCircle className="text-green-600 dark:text-green-400" size={64} />
                </div>
              </div>
              <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
                Email Verified!
              </h2>
              <p className="text-gray-600 dark:text-gray-400">
                Your email has been successfully verified. You can now access all features.
              </p>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Redirecting to login page...
              </p>
              <button
                onClick={() => navigate('/login')}
                className="w-full px-6 py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors font-medium"
              >
                Go to Login
              </button>
            </div>
          )}

          {/* Error State */}
          {status === 'error' && (
            <div className="space-y-4">
              <div className="flex justify-center">
                <div className="p-4 bg-red-100 dark:bg-red-900/20 rounded-full">
                  <FiXCircle className="text-red-600 dark:text-red-400" size={64} />
                </div>
              </div>
              <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
                Verification Failed
              </h2>
              <p className="text-gray-600 dark:text-gray-400">
                {errorMessage}
              </p>
              <div className="space-y-2">
                <button
                  onClick={handleRetry}
                  className="w-full px-6 py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors font-medium"
                >
                  Try Again
                </button>
                <button
                  onClick={() => navigate('/verify-email-pending')}
                  className="w-full px-6 py-3 bg-gray-200 dark:bg-gray-700 text-gray-900 dark:text-white rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors font-medium"
                >
                  Resend Verification Email
                </button>
                <button
                  onClick={() => navigate('/login')}
                  className="w-full px-6 py-3 text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white transition-colors"
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
