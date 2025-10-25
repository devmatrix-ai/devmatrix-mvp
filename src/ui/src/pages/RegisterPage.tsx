/**
 * Registration Page
 *
 * Allows new users to create an account.
 */

import { useState, FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { FiMail, FiLock, FiUser, FiAlertCircle, FiCheckCircle } from 'react-icons/fi'

export function RegisterPage() {
  const navigate = useNavigate()
  const { register } = useAuth()

  const [formData, setFormData] = useState({
    email: '',
    username: '',
    password: '',
    confirmPassword: '',
  })
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  // Password validation
  const passwordIsValid = formData.password.length >= 8
  const passwordsMatch = formData.password === formData.confirmPassword
  const canSubmit = passwordIsValid && passwordsMatch && formData.email && formData.username

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError('')

    if (!passwordsMatch) {
      setError('Passwords do not match')
      return
    }

    if (!passwordIsValid) {
      setError('Password must be at least 8 characters')
      return
    }

    setIsLoading(true)

    try {
      await register({
        email: formData.email,
        username: formData.username,
        password: formData.password,
      })
      // Redirect to email verification page after successful registration
      navigate('/verify-email-pending', {
        replace: true,
        state: { email: formData.email }
      })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Registration failed')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-gray-900 via-purple-900/20 to-blue-900/20 px-4 py-12">
      <div className="w-full max-w-md">
        {/* Logo/Brand */}
        <div className="text-center mb-8">
          <div className="inline-flex h-20 w-20 items-center justify-center rounded-2xl bg-gradient-to-br from-purple-600 to-blue-600 text-white font-bold text-3xl mb-4 shadow-lg shadow-purple-500/20">
            <img src="/DOCS/img/devmatrix-icon.svg" alt="DevMatrix" className="h-12 w-12" />
          </div>
          <h1 className="text-3xl font-bold text-purple-100">
            Create your account
          </h1>
          <p className="mt-2 text-sm text-purple-300">
            Start building with DevMatrix
          </p>
        </div>

        {/* Registration Form */}
        <div className="bg-gradient-to-br from-gray-900/40 via-purple-900/20 to-blue-900/20 backdrop-blur-xl rounded-lg border border-purple-500/20 p-8 shadow-xl shadow-purple-500/10">
          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Error Message */}
            {error && (
              <div className="flex items-center gap-2 p-4 bg-red-500/20 backdrop-blur-sm border border-red-400/30 rounded-lg text-red-200 text-sm">
                <FiAlertCircle className="flex-shrink-0" />
                <span>{error}</span>
              </div>
            )}

            {/* Email Field */}
            <div>
              <label
                htmlFor="email"
                className="block text-sm font-medium text-purple-200 mb-2"
              >
                Email
              </label>
              <div className="relative">
                <FiMail className="absolute left-3 top-1/2 -translate-y-1/2 text-purple-300" />
                <input
                  id="email"
                  type="email"
                  required
                  value={formData.email}
                  onChange={(e) =>
                    setFormData({ ...formData, email: e.target.value })
                  }
                  className="w-full pl-10 pr-4 py-2 border border-purple-500/20 rounded-lg focus:ring-2 focus:ring-purple-500/50 focus:border-purple-500/50 bg-white/5 backdrop-blur-sm text-purple-100 placeholder-purple-400/50"
                  placeholder="you@example.com"
                  autoComplete="email"
                />
              </div>
            </div>

            {/* Username Field */}
            <div>
              <label
                htmlFor="username"
                className="block text-sm font-medium text-purple-200 mb-2"
              >
                Username
              </label>
              <div className="relative">
                <FiUser className="absolute left-3 top-1/2 -translate-y-1/2 text-purple-300" />
                <input
                  id="username"
                  type="text"
                  required
                  value={formData.username}
                  onChange={(e) =>
                    setFormData({ ...formData, username: e.target.value })
                  }
                  className="w-full pl-10 pr-4 py-2 border border-purple-500/20 rounded-lg focus:ring-2 focus:ring-purple-500/50 focus:border-purple-500/50 bg-white/5 backdrop-blur-sm text-purple-100 placeholder-purple-400/50"
                  placeholder="johndoe"
                  autoComplete="username"
                />
              </div>
            </div>

            {/* Password Field */}
            <div>
              <label
                htmlFor="password"
                className="block text-sm font-medium text-purple-200 mb-2"
              >
                Password
              </label>
              <div className="relative">
                <FiLock className="absolute left-3 top-1/2 -translate-y-1/2 text-purple-300" />
                <input
                  id="password"
                  type="password"
                  required
                  value={formData.password}
                  onChange={(e) =>
                    setFormData({ ...formData, password: e.target.value })
                  }
                  className="w-full pl-10 pr-4 py-2 border border-purple-500/20 rounded-lg focus:ring-2 focus:ring-purple-500/50 focus:border-purple-500/50 bg-white/5 backdrop-blur-sm text-purple-100 placeholder-purple-400/50"
                  placeholder="••••••••"
                  autoComplete="new-password"
                />
              </div>
              {formData.password && (
                <div className="mt-2 flex items-center gap-2 text-xs">
                  {passwordIsValid ? (
                    <><FiCheckCircle className="text-green-400" />
                    <span className="text-green-300">Strong password</span></>
                  ) : (
                    <><FiAlertCircle className="text-orange-400" />
                    <span className="text-orange-300">At least 8 characters required</span></>
                  )}
                </div>
              )}
            </div>

            {/* Confirm Password Field */}
            <div>
              <label
                htmlFor="confirmPassword"
                className="block text-sm font-medium text-purple-200 mb-2"
              >
                Confirm Password
              </label>
              <div className="relative">
                <FiLock className="absolute left-3 top-1/2 -translate-y-1/2 text-purple-300" />
                <input
                  id="confirmPassword"
                  type="password"
                  required
                  value={formData.confirmPassword}
                  onChange={(e) =>
                    setFormData({ ...formData, confirmPassword: e.target.value })
                  }
                  className="w-full pl-10 pr-4 py-2 border border-purple-500/20 rounded-lg focus:ring-2 focus:ring-purple-500/50 focus:border-purple-500/50 bg-white/5 backdrop-blur-sm text-purple-100 placeholder-purple-400/50"
                  placeholder="••••••••"
                  autoComplete="new-password"
                />
              </div>
              {formData.confirmPassword && (
                <div className="mt-2 flex items-center gap-2 text-xs">
                  {passwordsMatch ? (
                    <><FiCheckCircle className="text-green-400" />
                    <span className="text-green-300">Passwords match</span></>
                  ) : (
                    <><FiAlertCircle className="text-red-400" />
                    <span className="text-red-300">Passwords do not match</span></>
                  )}
                </div>
              )}
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={isLoading || !canSubmit}
              className="w-full py-2.5 px-4 bg-gradient-to-r from-purple-600/90 to-blue-600/90 hover:from-purple-700/90 hover:to-blue-700/90 disabled:opacity-50 disabled:cursor-not-allowed text-white font-medium rounded-lg transition-colors backdrop-blur-sm border border-purple-400/30 shadow-lg shadow-purple-500/20"
            >
              {isLoading ? 'Creating account...' : 'Create account'}
            </button>
          </form>

          {/* Login Link */}
          <div className="mt-6 text-center text-sm text-purple-300">
            Already have an account?{' '}
            <Link
              to="/login"
              className="font-medium text-purple-400 hover:text-purple-300 transition-colors"
            >
              Sign in
            </Link>
          </div>
        </div>
      </div>
    </div>
  )
}
