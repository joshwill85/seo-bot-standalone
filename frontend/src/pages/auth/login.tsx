import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Eye, EyeOff, LogIn } from 'lucide-react'
import { useAuth } from '@/hooks/use-auth'

export default function LoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const { signIn } = useAuth()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setIsLoading(true)

    const result = await signIn(email, password)
    
    if (result.error) {
      setError(result.error)
    }
    
    setIsLoading(false)
  }

  return (
    <>
      <title>Login - Central Florida SEO Services</title>
      <meta name="description" content="Sign in to your Central Florida SEO dashboard to view your campaigns, reports, and analytics." />
      
      <div className="min-h-screen bg-gradient-to-br from-florida-blue-50 to-white flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8">
        <div className="max-w-md w-full space-y-8">
          {/* Header */}
          <div className="text-center">
            <div className="mx-auto h-12 w-12 bg-florida-blue-600 rounded-lg flex items-center justify-center mb-4">
              <LogIn className="h-6 w-6 text-white" />
            </div>
            <h2 className="text-3xl font-bold text-gray-900">
              Welcome back
            </h2>
            <p className="mt-2 text-gray-600">
              Sign in to your SEO dashboard
            </p>
          </div>

          {/* Demo Credentials */}
          <div className="bg-florida-blue-50 border border-florida-blue-200 rounded-lg p-4">
            <h3 className="text-sm font-semibold text-florida-blue-900 mb-2">Demo Credentials</h3>
            <div className="space-y-2 text-sm text-florida-blue-800">
              <div>
                <strong>Admin Access:</strong>
                <br />
                Email: admin@demo.com
                <br />
                Password: admin123
              </div>
              <div>
                <strong>Business Owner:</strong>
                <br />
                Email: demo@business.com
                <br />
                Password: demo123
              </div>
            </div>
          </div>

          {/* Login Form */}
          <form className="bg-white p-8 rounded-xl shadow-lg space-y-6" onSubmit={handleSubmit}>
            {error && (
              <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
                {error}
              </div>
            )}

            <div>
              <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-2">
                Email address
              </label>
              <input
                id="email"
                name="email"
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="appearance-none relative block w-full px-3 py-3 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-lg focus:outline-none focus:ring-2 focus:ring-florida-blue-500 focus:border-florida-blue-500 focus:z-10"
                placeholder="Enter your email"
              />
            </div>

            <div>
              <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-2">
                Password
              </label>
              <div className="relative">
                <input
                  id="password"
                  name="password"
                  type={showPassword ? 'text' : 'password'}
                  autoComplete="current-password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="appearance-none relative block w-full px-3 py-3 pr-10 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-lg focus:outline-none focus:ring-2 focus:ring-florida-blue-500 focus:border-florida-blue-500 focus:z-10"
                  placeholder="Enter your password"
                />
                <button
                  type="button"
                  className="absolute inset-y-0 right-0 pr-3 flex items-center"
                  onClick={() => setShowPassword(!showPassword)}
                >
                  {showPassword ? (
                    <EyeOff className="h-5 w-5 text-gray-400" />
                  ) : (
                    <Eye className="h-5 w-5 text-gray-400" />
                  )}
                </button>
              </div>
            </div>

            <div className="flex items-center justify-between">
              <div className="flex items-center">
                <input
                  id="remember-me"
                  name="remember-me"
                  type="checkbox"
                  className="h-4 w-4 text-florida-blue-600 focus:ring-florida-blue-500 border-gray-300 rounded"
                />
                <label htmlFor="remember-me" className="ml-2 block text-sm text-gray-900">
                  Remember me
                </label>
              </div>

              <div className="text-sm">
                <a href="#" className="font-medium text-florida-blue-600 hover:text-florida-blue-500">
                  Forgot your password?
                </a>
              </div>
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className={`group relative w-full flex justify-center py-3 px-4 border border-transparent text-sm font-medium rounded-lg text-white ${
                isLoading 
                  ? 'bg-gray-400 cursor-not-allowed' 
                  : 'bg-florida-blue-600 hover:bg-florida-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-florida-blue-500'
              } transition-colors duration-200`}
            >
              {isLoading ? 'Signing in...' : 'Sign in'}
            </button>

            <div className="text-center">
              <span className="text-gray-600">Don't have an account? </span>
              <Link 
                to="/register" 
                className="font-medium text-florida-blue-600 hover:text-florida-blue-500"
              >
                Sign up here
              </Link>
            </div>
          </form>

          {/* Back to Home */}
          <div className="text-center">
            <Link 
              to="/" 
              className="text-sm text-gray-600 hover:text-gray-900"
            >
              ← Back to homepage
            </Link>
          </div>
        </div>
      </div>
    </>
  )
}