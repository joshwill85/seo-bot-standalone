import { useEffect, useState } from 'react'
import { useAuth } from '@/hooks/useAuth'
import { Navigate } from 'react-router-dom'
import { mockBusinessesWithCampaigns, mockUsers } from '@/data/mockData'
import SEODashboard from '@/components/SEODashboard'
import { Building2, User, Settings, LogOut, ExternalLink } from 'lucide-react'

export default function DashboardPage() {
  const { user, signOut } = useAuth()
  const [selectedBusiness, setSelectedBusiness] = useState<any>(null)

  // If not authenticated, redirect to login
  if (!user) {
    return <Navigate to="/login" replace />
  }

  // Get user profile information
  const userProfile = mockUsers.find(u => u.email === user.email)
  
  // Get businesses for this user
  const userBusinesses = mockBusinessesWithCampaigns.filter(business => 
    business.email === user.email
  )

  // Auto-select first business if only one, or if none selected
  useEffect(() => {
    if (userBusinesses.length === 1 && !selectedBusiness) {
      setSelectedBusiness(userBusinesses[0])
    }
  }, [userBusinesses, selectedBusiness])

  const handleSignOut = async () => {
    try {
      await signOut()
    } catch (error) {
      console.error('Error signing out:', error)
    }
  }

  return (
    <>
      <title>
        {selectedBusiness ? `${selectedBusiness.name} - SEO Dashboard` : 'SEO Dashboard'} - Central Florida SEO
      </title>
      
      <div className="min-h-screen bg-gray-50">
        {/* Header */}
        <div className="bg-white shadow-sm border-b border-gray-200">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex items-center justify-between h-16">
              {/* Logo & Navigation */}
              <div className="flex items-center space-x-8">
                <div className="flex items-center">
                  <Building2 className="w-8 h-8 text-florida-blue-600 mr-2" />
                  <span className="text-xl font-bold text-gray-900">Central Florida SEO</span>
                </div>
                
                {/* Business Selector */}
                {userBusinesses.length > 1 && (
                  <div className="relative">
                    <select
                      value={selectedBusiness?.id || ''}
                      onChange={(e) => {
                        const business = userBusinesses.find(b => b.id === e.target.value)
                        setSelectedBusiness(business)
                      }}
                      className="appearance-none bg-white border border-gray-300 rounded-md py-2 pl-3 pr-10 text-sm leading-5 text-gray-900 focus:outline-none focus:ring-1 focus:ring-florida-blue-500 focus:border-florida-blue-500"
                    >
                      <option value="">Select Business</option>
                      {userBusinesses.map((business) => (
                        <option key={business.id} value={business.id}>
                          {business.name}
                        </option>
                      ))}
                    </select>
                  </div>
                )}
              </div>

              {/* User Menu */}
              <div className="flex items-center space-x-4">
                <div className="flex items-center space-x-3">
                  <div className="w-8 h-8 bg-florida-blue-100 rounded-full flex items-center justify-center">
                    <User className="w-4 h-4 text-florida-blue-600" />
                  </div>
                  <div className="hidden md:block">
                    <div className="text-sm font-medium text-gray-900">
                      {userProfile?.firstName} {userProfile?.lastName}
                    </div>
                    <div className="text-xs text-gray-500">{user.email}</div>
                  </div>
                </div>
                
                <div className="flex items-center space-x-2">
                  <button className="p-2 text-gray-400 hover:text-gray-600 transition-colors">
                    <Settings className="w-4 h-4" />
                  </button>
                  <button
                    onClick={handleSignOut}
                    className="p-2 text-gray-400 hover:text-gray-600 transition-colors"
                  >
                    <LogOut className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Main Content */}
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {userBusinesses.length === 0 ? (
            /* No Businesses */
            <div className="text-center py-12">
              <Building2 className="w-16 h-16 text-gray-400 mx-auto mb-4" />
              <h2 className="text-xl font-semibold text-gray-900 mb-2">No Businesses Found</h2>
              <p className="text-gray-600 mb-4">
                We couldn't find any businesses associated with your account.
              </p>
              <div className="space-y-3">
                <button className="px-4 py-2 bg-florida-blue-600 text-white rounded-md hover:bg-florida-blue-700 transition-colors">
                  Contact Support
                </button>
                <div className="text-sm text-gray-500">
                  Need help setting up your SEO campaigns? Our team is here to help.
                </div>
              </div>
            </div>
          ) : !selectedBusiness ? (
            /* Business Selection Required */
            <div className="text-center py-12">
              <Building2 className="w-16 h-16 text-gray-400 mx-auto mb-4" />
              <h2 className="text-xl font-semibold text-gray-900 mb-2">Select a Business</h2>
              <p className="text-gray-600 mb-6">
                Choose a business from the dropdown above to view your SEO dashboard.
              </p>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 max-w-4xl mx-auto">
                {userBusinesses.map((business) => (
                  <button
                    key={business.id}
                    onClick={() => setSelectedBusiness(business)}
                    className="p-4 text-left border border-gray-200 rounded-lg hover:border-florida-blue-300 hover:bg-florida-blue-50 transition-colors"
                  >
                    <div className="font-medium text-gray-900">{business.name}</div>
                    <div className="text-sm text-gray-600">{business.industry}</div>
                    <div className="text-sm text-gray-500">{business.location}</div>
                    <div className="mt-2 text-xs text-florida-blue-600">
                      View Dashboard →
                    </div>
                  </button>
                ))}
              </div>
            </div>
          ) : (
            /* SEO Dashboard */
            <div>
              {/* Business Header */}
              <div className="flex items-center justify-between mb-8">
                <div className="flex items-center space-x-4">
                  <div className="w-12 h-12 bg-florida-blue-100 rounded-lg flex items-center justify-center">
                    <Building2 className="w-6 h-6 text-florida-blue-600" />
                  </div>
                  <div>
                    <h1 className="text-2xl font-bold text-gray-900">{selectedBusiness.name}</h1>
                    <div className="flex items-center space-x-4 text-sm text-gray-600">
                      <span>{selectedBusiness.industry}</span>
                      <span>•</span>
                      <span>{selectedBusiness.location}</span>
                      <span>•</span>
                      <span className="capitalize">{selectedBusiness.plan}</span>
                    </div>
                  </div>
                </div>
                
                <div className="flex items-center space-x-3">
                  {selectedBusiness.website && (
                    <a
                      href={selectedBusiness.website}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center px-3 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 transition-colors"
                    >
                      <ExternalLink className="w-4 h-4 mr-1" />
                      Visit Website
                    </a>
                  )}
                  <div className="text-right">
                    <div className="text-sm text-gray-500">SEO Score</div>
                    <div className={`text-lg font-bold ${
                      selectedBusiness.seoScore >= 80 ? 'text-green-600' : 
                      selectedBusiness.seoScore >= 60 ? 'text-yellow-600' : 'text-red-600'
                    }`}>
                      {selectedBusiness.seoScore}/100
                    </div>
                  </div>
                </div>
              </div>

              {/* SEO Dashboard Component */}
              <SEODashboard 
                businessId={selectedBusiness.id} 
                businessName={selectedBusiness.name}
              />
            </div>
          )}
        </div>
      </div>
    </>
  )
}