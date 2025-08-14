import { useState, useEffect } from 'react'
import { useAuth } from '@/hooks/use-auth'
import { Navigate, useNavigate } from 'react-router-dom'
import { mockBusinessesWithCampaigns, mockUsers } from '@/data/mockData'
import CustomerProfileManager from '@/components/Customer/CustomerProfileManager'
import Header from '@/components/Header'
import { 
  Building2, ArrowLeft, ExternalLink, BarChart3, Settings, 
  Users, TrendingUp, Zap, Calendar, CheckCircle, Clock, AlertTriangle
} from 'lucide-react'

export default function BusinessesPage() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const [selectedBusiness, setSelectedBusiness] = useState<any>(null)
  const [businesses, setBusinesses] = useState<any[]>([])

  // If not authenticated, redirect to login
  if (!user) {
    return <Navigate to="/login" replace />
  }

  useEffect(() => {
    // Get businesses for this user
    const userBusinesses = mockBusinessesWithCampaigns.filter(business => 
      business.email === user.email
    )
    setBusinesses(userBusinesses)
  }, [user.email])

  if (selectedBusiness) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Header />
        
        <div className="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8">
          {/* Back Navigation */}
          <div className="mb-6">
            <button
              onClick={() => setSelectedBusiness(null)}
              className="flex items-center text-florida-blue-600 hover:text-florida-blue-700 font-medium"
            >
              <ArrowLeft className="w-4 h-4 mr-2" />
              Back to All Businesses
            </button>
          </div>

          {/* Business Header */}
          <div className="bg-white rounded-lg shadow-md p-6 mb-6">
            <div className="flex items-center justify-between">
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
          </div>

          {/* SEO Services Management */}
          <CustomerProfileManager customerId={selectedBusiness.id} />
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Header />
      
      <div className="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">My Businesses</h1>
          <p className="text-gray-600 mt-2">Manage SEO services for all your business accounts</p>
        </div>

        {businesses.length === 0 ? (
          <div className="bg-white rounded-lg shadow-md p-8 text-center">
            <Building2 className="w-16 h-16 text-gray-400 mx-auto mb-4" />
            <h2 className="text-xl font-semibold text-gray-900 mb-2">No Businesses Found</h2>
            <p className="text-gray-600 mb-4">
              We couldn't find any businesses associated with your account.
            </p>
            <button className="px-4 py-2 bg-florida-blue-600 text-white rounded-md hover:bg-florida-blue-700 transition-colors">
              Contact Support
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {businesses.map((business) => (
              <div
                key={business.id}
                className="bg-white rounded-lg shadow-md hover:shadow-lg transition-shadow cursor-pointer border border-gray-200"
                onClick={() => setSelectedBusiness(business)}
              >
                <div className="p-6">
                  {/* Business Header */}
                  <div className="flex items-center space-x-3 mb-4">
                    <div className="w-10 h-10 bg-florida-blue-100 rounded-lg flex items-center justify-center">
                      <Building2 className="w-5 h-5 text-florida-blue-600" />
                    </div>
                    <div className="flex-1">
                      <h3 className="font-semibold text-gray-900">{business.name}</h3>
                      <p className="text-sm text-gray-600">{business.industry}</p>
                    </div>
                  </div>

                  {/* Business Stats */}
                  <div className="grid grid-cols-2 gap-4 mb-4">
                    <div className="text-center p-3 bg-gray-50 rounded-lg">
                      <div className="text-lg font-bold text-gray-900">{business.seoScore}</div>
                      <div className="text-xs text-gray-500">SEO Score</div>
                    </div>
                    <div className="text-center p-3 bg-gray-50 rounded-lg">
                      <div className="text-lg font-bold text-gray-900">39</div>
                      <div className="text-xs text-gray-500">SEO Services</div>
                    </div>
                  </div>

                  {/* Plan Badge */}
                  <div className="flex items-center justify-between mb-4">
                    <span className={`px-3 py-1 rounded-full text-xs font-medium ${
                      business.plan?.toLowerCase().includes('enterprise') 
                        ? 'bg-purple-100 text-purple-700'
                        : business.plan?.toLowerCase().includes('growth') 
                        ? 'bg-blue-100 text-blue-700'
                        : 'bg-green-100 text-green-700'
                    }`}>
                      {business.plan} Plan
                    </span>
                    <span className="text-xs text-gray-500">{business.location}</span>
                  </div>

                  {/* Quick Stats */}
                  <div className="space-y-2">
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-gray-600">Monthly Traffic</span>
                      <span className="font-medium text-gray-900">{business.organicTraffic?.toLocaleString()}</span>
                    </div>
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-gray-600">Keywords</span>
                      <span className="font-medium text-gray-900">{business.keywordCount}</span>
                    </div>
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-gray-600">Monthly Leads</span>
                      <span className="font-medium text-gray-900">{business.monthlyLeads}</span>
                    </div>
                  </div>

                  {/* Action Buttons */}
                  <div className="mt-6 flex space-x-2">
                    <button className="flex-1 px-3 py-2 bg-florida-blue-600 text-white text-sm font-medium rounded-md hover:bg-florida-blue-700 transition-colors flex items-center justify-center">
                      <Zap className="w-4 h-4 mr-1" />
                      Manage Services
                    </button>
                    <button className="px-3 py-2 border border-gray-300 text-gray-700 text-sm font-medium rounded-md hover:bg-gray-50 transition-colors">
                      <BarChart3 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}