import { useState } from 'react'
import { 
  Search, Target, FileText, MapPin, ExternalLink, BarChart3, Users, 
  Settings, Zap, Smartphone, Shield, Map, Bot, Copy, Server,
  Layers, Calendar, Mic, Tag, Link, Image, AlertCircle, RefreshCw,
  HelpCircle, Building2, Code, Star, Eye, Globe, MessageSquare,
  PieChart, Network, Code2, TrendingUp, CheckCircle, Clock,
  Filter, ChevronDown
} from 'lucide-react'
import { allSEOServices, seoServiceCategories, getServicesByCategory, getServicesByPlan } from '@/data/seoServices'

interface SEOServicesDashboardProps {
  businessId: string
  businessName: string
  planTier: 'professional' | 'business' | 'enterprise'
}

const iconMap: { [key: string]: any } = {
  Settings, Zap, Smartphone, Shield, Map, Bot, Copy, Server, Search, Layers,
  Target, TrendingUp, Calendar, Mic, FileText, Tag, Link, Image, AlertCircle,
  RefreshCw, HelpCircle, MapPin, Building2, Code, Star, Eye, ExternalLink,
  Globe, MessageSquare, BarChart3, PieChart, Users, Network, Code2
}

const ServiceCard = ({ service, userPlan }: { service: any, userPlan: string }) => {
  const Icon = iconMap[service.icon] || Settings
  const isAvailable = service.planTiers.includes(userPlan)
  const isActive = service.status === 'active' && isAvailable

  const getStatusColor = () => {
    if (!isAvailable) return 'bg-gray-100 text-gray-400 border-gray-200'
    if (service.status === 'active') return 'bg-green-50 text-green-700 border-green-200'
    if (service.status === 'pending') return 'bg-yellow-50 text-yellow-700 border-yellow-200'
    return 'bg-blue-50 text-blue-700 border-blue-200'
  }

  const getStatusBadge = () => {
    if (!isAvailable) return 'Not in Plan'
    if (service.status === 'active') return 'Active'
    if (service.status === 'pending') return 'Setting Up'
    return 'Available'
  }

  return (
    <div className={`p-4 border rounded-lg transition-all duration-200 ${getStatusColor()} ${isActive ? 'hover:shadow-md' : ''}`}>
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center space-x-3">
          <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
            isActive ? 'bg-florida-blue-100' : 'bg-gray-100'
          }`}>
            <Icon className={`w-5 h-5 ${isActive ? 'text-florida-blue-600' : 'text-gray-400'}`} />
          </div>
          <div>
            <h3 className={`font-semibold text-sm ${isActive ? 'text-gray-900' : 'text-gray-500'}`}>
              {service.name}
            </h3>
            <div className="flex items-center space-x-2 mt-1">
              <span className={`text-xs px-2 py-1 rounded-full font-medium ${
                isActive ? 'bg-green-100 text-green-700' : 
                !isAvailable ? 'bg-gray-100 text-gray-500' : 'bg-yellow-100 text-yellow-700'
              }`}>
                {getStatusBadge()}
              </span>
              <span className="text-xs text-gray-500 capitalize">{service.frequency}</span>
            </div>
          </div>
        </div>
      </div>
      <p className={`text-xs leading-relaxed ${isActive ? 'text-gray-600' : 'text-gray-400'}`}>
        {service.description}
      </p>
      {!isAvailable && (
        <div className="mt-2 text-xs text-gray-500">
          Available in: {service.planTiers.join(', ')} plans
        </div>
      )}
    </div>
  )
}

export default function SEOServicesDashboard({ businessId, businessName, planTier }: SEOServicesDashboardProps) {
  const [selectedCategory, setSelectedCategory] = useState<string>('all')
  const [showUpgradeOnly, setShowUpgradeOnly] = useState(false)

  const userServices = getServicesByPlan(planTier)
  const activeServices = userServices.filter(s => s.status === 'active')
  const availableServices = allSEOServices.filter(s => !s.planTiers.includes(planTier))

  const filteredServices = selectedCategory === 'all' 
    ? (showUpgradeOnly ? availableServices : allSEOServices)
    : (showUpgradeOnly ? availableServices.filter(s => s.category === selectedCategory) : getServicesByCategory(selectedCategory))

  const categoryStats = seoServiceCategories.map(category => {
    const categoryServices = getServicesByCategory(category)
    const userCategoryServices = categoryServices.filter(s => s.planTiers.includes(planTier))
    const activeCategoryServices = userCategoryServices.filter(s => s.status === 'active')
    
    return {
      name: category,
      total: categoryServices.length,
      available: userCategoryServices.length,
      active: activeCategoryServices.length
    }
  })

  return (
    <div className="space-y-6">
      {/* Header Stats */}
      <div className="bg-white rounded-lg shadow-md p-6 border border-gray-200">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">SEO Services Dashboard</h1>
            <p className="text-gray-600">Automated SEO services for {businessName}</p>
          </div>
          <div className="text-right">
            <div className="text-sm text-gray-500">Current Plan</div>
            <div className="text-lg font-semibold text-florida-blue-600 capitalize">{planTier}</div>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          <div className="text-center p-4 bg-green-50 rounded-lg">
            <div className="text-2xl font-bold text-green-600">{activeServices.length}</div>
            <div className="text-sm text-green-700">Active Services</div>
          </div>
          <div className="text-center p-4 bg-blue-50 rounded-lg">
            <div className="text-2xl font-bold text-blue-600">{userServices.length}</div>
            <div className="text-sm text-blue-700">Available in Plan</div>
          </div>
          <div className="text-center p-4 bg-purple-50 rounded-lg">
            <div className="text-2xl font-bold text-purple-600">{allSEOServices.length}</div>
            <div className="text-sm text-purple-700">Total Services</div>
          </div>
          <div className="text-center p-4 bg-orange-50 rounded-lg">
            <div className="text-2xl font-bold text-orange-600">{seoServiceCategories.length}</div>
            <div className="text-sm text-orange-700">Categories</div>
          </div>
        </div>
      </div>

      {/* Category Overview */}
      <div className="bg-white rounded-lg shadow-md p-6 border border-gray-200">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Services by Category</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {categoryStats.map((category) => (
            <div key={category.name} className="p-4 border border-gray-200 rounded-lg">
              <div className="flex items-center justify-between mb-2">
                <h3 className="font-medium text-gray-900 text-sm">{category.name}</h3>
                <span className="text-xs text-gray-500">{category.total} total</span>
              </div>
              <div className="flex items-center space-x-4 text-xs">
                <div className="flex items-center">
                  <div className="w-2 h-2 bg-green-500 rounded-full mr-1"></div>
                  <span className="text-green-700">{category.active} active</span>
                </div>
                <div className="flex items-center">
                  <div className="w-2 h-2 bg-blue-500 rounded-full mr-1"></div>
                  <span className="text-blue-700">{category.available} in plan</span>
                </div>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-1.5 mt-2">
                <div 
                  className="bg-green-500 h-1.5 rounded-full" 
                  style={{ width: `${(category.active / category.total) * 100}%` }}
                ></div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-lg shadow-md p-6 border border-gray-200">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-900">All SEO Services</h2>
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2">
              <input
                type="checkbox"
                id="upgrade-only"
                checked={showUpgradeOnly}
                onChange={(e) => setShowUpgradeOnly(e.target.checked)}
                className="rounded border-gray-300 text-florida-blue-600 focus:ring-florida-blue-500"
              />
              <label htmlFor="upgrade-only" className="text-sm text-gray-700">
                Show upgrade opportunities only
              </label>
            </div>
            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              className="text-sm border border-gray-300 rounded-md px-3 py-1 focus:outline-none focus:ring-1 focus:ring-florida-blue-500"
            >
              <option value="all">All Categories</option>
              {seoServiceCategories.map((category) => (
                <option key={category} value={category}>{category}</option>
              ))}
            </select>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredServices.map((service) => (
            <ServiceCard 
              key={service.id} 
              service={service} 
              userPlan={planTier}
            />
          ))}
        </div>

        {filteredServices.length === 0 && (
          <div className="text-center py-8 text-gray-500">
            <Settings className="w-12 h-12 mx-auto mb-4 text-gray-400" />
            <p>No services found matching your filters.</p>
          </div>
        )}
      </div>

      {/* Upgrade Prompt */}
      {availableServices.length > 0 && !showUpgradeOnly && (
        <div className="bg-gradient-to-r from-florida-blue-50 to-florida-orange-50 rounded-lg p-6 border border-florida-blue-200">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                Unlock {availableServices.length} More Services
              </h3>
              <p className="text-gray-600">
                Upgrade your plan to access our complete suite of {allSEOServices.length} automated SEO services.
              </p>
            </div>
            <div className="text-right">
              <button className="px-6 py-3 bg-florida-blue-600 text-white font-semibold rounded-lg hover:bg-florida-blue-700 transition-colors">
                Upgrade Plan
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}