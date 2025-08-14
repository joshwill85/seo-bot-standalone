import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { useAuth } from '@/hooks/use-auth'
import { TrendingUp, Building2 } from 'lucide-react'

const Header = () => {
  const { user } = useAuth()
  return (
    <header className="border-b bg-white/80 backdrop-blur-sm sticky top-0 z-50">
      <div className="container mx-auto px-4 py-4 flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <div className="w-8 h-8 bg-gradient-to-br from-florida-blue-600 to-florida-orange-600 rounded-lg flex items-center justify-center">
            <TrendingUp className="w-5 h-5 text-white" />
          </div>
          <Link to="/" className="text-xl font-bold text-gray-900">Central Florida SEO</Link>
        </div>
        
        <nav className="hidden md:flex items-center space-x-6">
          {user ? (
            <>
              <Link to="/dashboard" className="text-gray-600 hover:text-gray-900 transition-colors">Dashboard</Link>
              {/* Admin-only navigation */}
              {user.email?.includes('admin') && (
                <Link to="/admin" className="flex items-center text-gray-600 hover:text-gray-900 transition-colors">
                  <Building2 className="w-4 h-4 mr-1" />
                  Admin Dashboard
                </Link>
              )}
            </>
          ) : (
            <>
              <Link to="/features" className="text-gray-600 hover:text-gray-900 transition-colors">Features</Link>
              <Link to="/pricing" className="text-gray-600 hover:text-gray-900 transition-colors">Pricing</Link>
              <Link to="/about" className="text-gray-600 hover:text-gray-900 transition-colors">About</Link>
              <Link to="/contact" className="text-gray-600 hover:text-gray-900 transition-colors">Contact</Link>
            </>
          )}
        </nav>

        <div className="flex items-center space-x-3">
          {user ? (
            <div className="flex items-center space-x-3">
              <span className="text-sm text-gray-700">Welcome, {user.email}</span>
              <Link to="/dashboard">
                <Button variant="florida">Dashboard</Button>
              </Link>
            </div>
          ) : (
            <>
              <Link to="/login">
                <Button variant="ghost">Sign In</Button>
              </Link>
              <Link to="/register">
                <Button variant="florida">Get Started</Button>
              </Link>
            </>
          )}
        </div>
      </div>
    </header>
  )
}

export default Header