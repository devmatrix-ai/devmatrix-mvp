/**
 * Email Verification Pending Page
 *
 * Shown after registration or when user needs to verify their email.
 * Allows resending the verification email.
 */

import { useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { authService } from '../services/authService'
import { FiMail, FiCheck, FiAlertCircle } from 'react-icons/fi'

export function VerifyEmailPendingPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const emailFromState = (location.state as any)?.email || ''

  const [email, setEmail] = useState(emailFromState)
  const [status, setStatus] = useState<'idle' | 'sending' | 'success' | 'error'>('idle')
  const [errorMessage, setErrorMessage] = useState('')

  const handleResendEmail = async () => {
    if (!email) {
      setStatus('error')
      setErrorMessage('Please enter your email address')
      return
    }

    setStatus('sending')
    setErrorMessage('')

    try {
      await authService.resendVerification(email)
      setStatus('success')
    } catch (error) {
      setStatus('error')
      setErrorMessage(error instanceof Error ? error.message : 'Failed to resend verification email')
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center p-4">
      <div className="max-w-md w-full">
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-8">
          {/* Header */}
          <div className="text-center mb-6">
            <div className="flex justify-center mb-4">
              <div className="p-4 bg-primary-100 dark:bg-primary-900/20 rounded-full">
                <FiMail className="text-primary-600 dark:text-primary-400" size={48} />
              </div>
            </div>
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
              Verify Your Email
            </h2>
            <p className="text-gray-600 dark:text-gray-400">
              We've sent a verification link to your email address. Please check your inbox and click the link to verify your account.
            </p>
          </div>

          {/* Success Message */}
          {status === 'success' && (
            <div className="mb-6 p-4 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg flex items-start gap-3">
              <FiCheck className="text-green-600 dark:text-green-400 mt-0.5" size={20} />
              <div>
                <p className="font-medium text-green-900 dark:text-green-100">Email Sent!</p>
                <p className="text-sm text-green-700 dark:text-green-300">
                  Please check your inbox and spam folder.
                </p>
              </div>
            </div>
          )}

          {/* Error Message */}
          {status === 'error' && errorMessage && (
            <div className="mb-6 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg flex items-start gap-3">
              <FiAlertCircle className="text-red-600 dark:text-red-400 mt-0.5" size={20} />
              <div>
                <p className="font-medium text-red-900 dark:text-red-100">Error</p>
                <p className="text-sm text-red-700 dark:text-red-300">{errorMessage}</p>
              </div>
            </div>
          )}

          {/* Instructions */}
          <div className="mb-6 space-y-3">
            <div className="flex items-start gap-3 text-sm text-gray-600 dark:text-gray-400">
              <div className="flex-shrink-0 w-6 h-6 flex items-center justify-center bg-gray-100 dark:bg-gray-700 rounded-full font-medium">
                1
              </div>
              <p>Check your email inbox (and spam folder)</p>
            </div>
            <div className="flex items-start gap-3 text-sm text-gray-600 dark:text-gray-400">
              <div className="flex-shrink-0 w-6 h-6 flex items-center justify-center bg-gray-100 dark:bg-gray-700 rounded-full font-medium">
                2
              </div>
              <p>Click the verification link in the email</p>
            </div>
            <div className="flex items-start gap-3 text-sm text-gray-600 dark:text-gray-400">
              <div className="flex-shrink-0 w-6 h-6 flex items-center justify-center bg-gray-100 dark:bg-gray-700 rounded-full font-medium">
                3
              </div>
              <p>You'll be redirected to login</p>
            </div>
          </div>

          {/* Resend Section */}
          <div className="border-t border-gray-200 dark:border-gray-700 pt-6">
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-3 text-center">
              Didn't receive the email?
            </p>
            <div className="space-y-3">
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="Enter your email"
                className="w-full px-4 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
              <button
                onClick={handleResendEmail}
                disabled={status === 'sending' || !email}
                className="w-full px-6 py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors font-medium"
              >
                {status === 'sending' ? 'Sending...' : 'Resend Verification Email'}
              </button>
            </div>
          </div>

          {/* Back to Login */}
          <div className="mt-6 text-center">
            <button
              onClick={() => navigate('/login')}
              className="text-primary-600 dark:text-primary-400 hover:text-primary-700 dark:hover:text-primary-300 font-medium"
            >
              Back to Login
            </button>
          </div>
        </div>

        {/* Additional Help */}
        <div className="mt-4 text-center text-sm text-gray-600 dark:text-gray-400">
          <p>
            Having trouble?{' '}
            <a href="mailto:support@devmatrix.ai" className="text-primary-600 dark:text-primary-400 hover:underline">
              Contact Support
            </a>
          </p>
        </div>
      </div>
    </div>
  )
}
