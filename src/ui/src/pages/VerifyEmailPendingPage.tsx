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
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-purple-900/20 to-blue-900/20 flex items-center justify-center p-4">
      <div className="max-w-md w-full">
        <div className="bg-gradient-to-br from-gray-900/40 via-purple-900/20 to-blue-900/20 backdrop-blur-xl rounded-lg border border-purple-500/20 p-8 shadow-xl shadow-purple-500/10">
          {/* Header */}
          <div className="text-center mb-6">
            <div className="flex justify-center mb-4">
              <div className="p-4 bg-purple-500/20 backdrop-blur-sm rounded-full">
                <FiMail className="text-purple-400" size={48} />
              </div>
            </div>
            <h2 className="text-2xl font-bold text-purple-100 mb-2">
              Verify Your Email
            </h2>
            <p className="text-purple-300">
              We've sent a verification link to your email address. Please check your inbox and click the link to verify your account.
            </p>
          </div>

          {/* Success Message */}
          {status === 'success' && (
            <div className="mb-6 p-4 bg-green-500/20 backdrop-blur-sm border border-green-400/30 rounded-lg flex items-start gap-3">
              <FiCheck className="text-green-400 mt-0.5" size={20} />
              <div>
                <p className="font-medium text-green-300">Email Sent!</p>
                <p className="text-sm text-green-400">
                  Please check your inbox and spam folder.
                </p>
              </div>
            </div>
          )}

          {/* Error Message */}
          {status === 'error' && errorMessage && (
            <div className="mb-6 p-4 bg-red-500/20 backdrop-blur-sm border border-red-400/30 rounded-lg flex items-start gap-3">
              <FiAlertCircle className="text-red-400 mt-0.5" size={20} />
              <div>
                <p className="font-medium text-red-300">Error</p>
                <p className="text-sm text-red-400">{errorMessage}</p>
              </div>
            </div>
          )}

          {/* Instructions */}
          <div className="mb-6 space-y-3">
            <div className="flex items-start gap-3 text-sm text-purple-300">
              <div className="flex-shrink-0 w-6 h-6 flex items-center justify-center bg-purple-500/20 backdrop-blur-sm rounded-full font-medium text-purple-200">
                1
              </div>
              <p>Check your email inbox (and spam folder)</p>
            </div>
            <div className="flex items-start gap-3 text-sm text-purple-300">
              <div className="flex-shrink-0 w-6 h-6 flex items-center justify-center bg-purple-500/20 backdrop-blur-sm rounded-full font-medium text-purple-200">
                2
              </div>
              <p>Click the verification link in the email</p>
            </div>
            <div className="flex items-start gap-3 text-sm text-purple-300">
              <div className="flex-shrink-0 w-6 h-6 flex items-center justify-center bg-purple-500/20 backdrop-blur-sm rounded-full font-medium text-purple-200">
                3
              </div>
              <p>You'll be redirected to login</p>
            </div>
          </div>

          {/* Resend Section */}
          <div className="border-t border-purple-500/20 pt-6">
            <p className="text-sm text-purple-300 mb-3 text-center">
              Didn't receive the email?
            </p>
            <div className="space-y-3">
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="Enter your email"
                className="w-full px-4 py-2 bg-white/5 backdrop-blur-sm border border-purple-500/20 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500/50 text-purple-100 placeholder-purple-400/50"
              />
              <button
                onClick={handleResendEmail}
                disabled={status === 'sending' || !email}
                className="w-full px-6 py-3 bg-gradient-to-r from-purple-600/90 to-blue-600/90 text-white rounded-lg hover:from-purple-700/90 hover:to-blue-700/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium backdrop-blur-sm border border-purple-400/30 shadow-lg shadow-purple-500/20"
              >
                {status === 'sending' ? 'Sending...' : 'Resend Verification Email'}
              </button>
            </div>
          </div>

          {/* Back to Login */}
          <div className="mt-6 text-center">
            <button
              onClick={() => navigate('/login')}
              className="text-purple-400 hover:text-purple-300 font-medium transition-colors"
            >
              Back to Login
            </button>
          </div>
        </div>

        {/* Additional Help */}
        <div className="mt-4 text-center text-sm text-purple-300">
          <p>
            Having trouble?{' '}
            <a href="mailto:support@devmatrix.ai" className="text-purple-400 hover:text-purple-300 hover:underline transition-colors">
              Contact Support
            </a>
          </p>
        </div>
      </div>
    </div>
  )
}
