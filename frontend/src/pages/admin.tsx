import { Users, DollarSign, TrendingUp, Search, Globe, Star, ArrowUpRight, ArrowDownRight, Play, BarChart3, FileText, Zap, AlertCircle, CheckCircle, Settings, X, PieChart, Activity } from 'lucide-react'
import { mockBusinessesWithCampaigns, platformStats } from '@/data/mockData'
import { useState } from 'react'
import CustomerProfileManager from '@/components/Customer/CustomerProfileManager'
import BusinessIntelligenceDashboard from '@/components/Admin/BusinessIntelligenceDashboard'
import SEOExecutionLogs from '@/components/Admin/SEOExecutionLogs'

const StatCard = ({ title, value, change, icon: Icon, prefix = '', suffix = '' }: {
  title: string
  value: string | number
  change?: number
  icon: any
  prefix?: string
  suffix?: string
}) => {
  const isPositive = change && change > 0
  const isNegative = change && change < 0
  
  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-gray-600">{title}</p>
          <p className="text-3xl font-bold text-gray-900">
            {prefix}{typeof value === 'number' ? value.toLocaleString() : value}{suffix}
          </p>
          {change !== undefined && (
            <div className={`flex items-center mt-2 text-sm ${
              isPositive ? 'text-green-600' : isNegative ? 'text-red-600' : 'text-gray-600'
            }`}>
              {isPositive ? (
                <ArrowUpRight className="w-4 h-4 mr-1" />
              ) : isNegative ? (
                <ArrowDownRight className="w-4 h-4 mr-1" />
              ) : null}
              <span>{Math.abs(change)}%</span>
              <span className="ml-1">from last month</span>
            </div>
          )}
        </div>
        <div className="w-12 h-12 bg-florida-blue-100 rounded-lg flex items-center justify-center">
          <Icon className="w-6 h-6 text-florida-blue-600" />
        </div>
      </div>
    </div>
  )
}

const BusinessCard = ({ business, onManageCampaigns }: { business: any, onManageCampaigns: (business: any) => void }) => {
  const [isRunning, setIsRunning] = useState<Record<string, boolean>>({})
  
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active': return 'bg-green-100 text-green-800'
      case 'audit_complete': return 'bg-blue-100 text-blue-800'
      case 'paused': return 'bg-yellow-100 text-yellow-800'
      default: return 'bg-gray-100 text-gray-800'
    }
  }

  const getPlanColor = (plan: string) => {
    switch (plan) {
      case 'Enterprise SEO': return 'bg-purple-100 text-purple-800'
      case 'Growth SEO': return 'bg-florida-orange-100 text-florida-orange-800'
      case 'SEO Audit': return 'bg-florida-blue-100 text-florida-blue-800'
      default: return 'bg-gray-100 text-gray-800'
    }
  }

  const handleSEOAction = async (action: string) => {
    setIsRunning(prev => ({ ...prev, [action]: true }))
    
    try {
      let endpoint = ''
      let payload = { business_id: business.id }
      
      switch (action) {
        case 'discover':
          endpoint = '/functions/v1/seo-discover'
          break
        case 'audit':
          endpoint = '/functions/v1/seo-audit'
          break
        case 'brief':
          endpoint = '/functions/v1/seo-brief'
          payload = { 
            ...payload, 
            target_keyword: business.campaigns?.[0]?.seed_keywords?.[0] || `${business.industry?.toLowerCase()} ${business.location.split(',')[0].toLowerCase()}` 
          }
          break
        case 'cluster':
          endpoint = '/functions/v1/seo-cluster'
          break
      }
      
      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 2000))
      
      // In real implementation:
      // const response = await fetch(`${process.env.REACT_APP_SUPABASE_URL}${endpoint}`, {
      //   method: 'POST',
      //   headers: {
      //     'Content-Type': 'application/json',
      //     'Authorization': `Bearer ${process.env.REACT_APP_SUPABASE_ANON_KEY}`
      //   },
      //   body: JSON.stringify(payload)
      // })
      
      console.log(`SEO ${action} completed for ${business.name}`)
    } catch (error) {
      console.error(`SEO ${action} failed:`, error)
    } finally {
      setIsRunning(prev => ({ ...prev, [action]: false }))
    }
  }

  return (
    <div className="bg-white rounded-lg shadow-md p-6 hover:shadow-lg transition-shadow">
      <div className="flex items-start justify-between mb-4">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">{business.name}</h3>
          <p className="text-sm text-gray-600">{business.owner} • {business.location}</p>
          <p className="text-sm text-gray-500">{business.industry}</p>
        </div>
        <div className="flex flex-col space-y-2">
          <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(business.status)}`}>
            {business.status.replace('_', ' ')}
          </span>
          <span className={`px-2 py-1 rounded-full text-xs font-medium ${getPlanColor(business.plan)}`}>
            {business.plan}
          </span>
        </div>
      </div>
      
      <div className="grid grid-cols-2 gap-4 text-sm mb-4">
        <div>
          <span className="text-gray-600">Monthly Revenue:</span>
          <span className="font-semibold text-gray-900 ml-1">${business.monthlySpend}</span>
        </div>
        <div>
          <span className="text-gray-600">SEO Score:</span>
          <span className={`font-semibold ml-1 ${
            business.seoScore >= 80 ? 'text-green-600' : 
            business.seoScore >= 60 ? 'text-yellow-600' : 'text-red-600'
          }`}>
            {business.seoScore}/100
          </span>
        </div>
        <div>
          <span className="text-gray-600">Keywords:</span>
          <span className="font-semibold text-gray-900 ml-1">{business.keywordCount}</span>
        </div>
        <div>
          <span className="text-gray-600">Avg Position:</span>
          <span className="font-semibold text-gray-900 ml-1">{business.avgPosition}</span>
        </div>
        <div>
          <span className="text-gray-600">Monthly Traffic:</span>
          <span className="font-semibold text-gray-900 ml-1">{business.organicTraffic.toLocaleString()}</span>
        </div>
        <div>
          <span className="text-gray-600">Monthly Leads:</span>
          <span className="font-semibold text-gray-900 ml-1">{business.monthlyLeads}</span>
        </div>
      </div>
      
      {/* SEO Campaign Overview */}
      {business.campaigns && business.campaigns.length > 0 && (
        <div className="mb-4 p-3 bg-gray-50 rounded-lg">
          <div className="flex items-center justify-between mb-2">
            <h4 className="text-sm font-medium text-gray-900">Active Campaigns</h4>
            <span className="text-xs text-gray-500">{business.campaigns.length} campaigns</span>
          </div>
          <div className="grid grid-cols-3 gap-2 text-xs">
            <div className="text-center">
              <div className="font-semibold text-gray-900">{business.activeTasks || 0}</div>
              <div className="text-gray-500">Active Tasks</div>
            </div>
            <div className="text-center">
              <div className="font-semibold text-gray-900">{business.completedTasks || 0}</div>
              <div className="text-gray-500">Completed</div>
            </div>
            <div className="text-center">
              <div className="font-semibold text-gray-900">{business.contentBriefs || 0}</div>
              <div className="text-gray-500">Content Briefs</div>
            </div>
          </div>
        </div>
      )}
      
      {/* SEO Action Buttons */}
      <div className="space-y-2">
        <div className="text-xs font-medium text-gray-700 mb-2">SEO Actions</div>
        <div className="grid grid-cols-2 gap-2">
          <button
            onClick={() => handleSEOAction('discover')}
            disabled={isRunning.discover}
            className="flex items-center justify-center px-3 py-2 text-xs font-medium text-white bg-florida-blue-600 hover:bg-florida-blue-700 disabled:bg-gray-400 rounded-md transition-colors"
          >
            {isRunning.discover ? (
              <div className="animate-spin w-3 h-3 border border-white border-t-transparent rounded-full" />
            ) : (
              <>
                <Search className="w-3 h-3 mr-1" />
                Discover Keywords
              </>
            )}
          </button>
          
          <button
            onClick={() => handleSEOAction('audit')}
            disabled={isRunning.audit}
            className="flex items-center justify-center px-3 py-2 text-xs font-medium text-white bg-florida-orange-600 hover:bg-florida-orange-700 disabled:bg-gray-400 rounded-md transition-colors"
          >
            {isRunning.audit ? (
              <div className="animate-spin w-3 h-3 border border-white border-t-transparent rounded-full" />
            ) : (
              <>
                <BarChart3 className="w-3 h-3 mr-1" />
                Technical Audit
              </>
            )}
          </button>
          
          <button
            onClick={() => handleSEOAction('brief')}
            disabled={isRunning.brief}
            className="flex items-center justify-center px-3 py-2 text-xs font-medium text-white bg-florida-green-600 hover:bg-florida-green-700 disabled:bg-gray-400 rounded-md transition-colors"
          >
            {isRunning.brief ? (
              <div className="animate-spin w-3 h-3 border border-white border-t-transparent rounded-full" />
            ) : (
              <>
                <FileText className="w-3 h-3 mr-1" />
                Content Brief
              </>
            )}
          </button>
          
          <button
            onClick={() => handleSEOAction('cluster')}
            disabled={isRunning.cluster}
            className="flex items-center justify-center px-3 py-2 text-xs font-medium text-white bg-purple-600 hover:bg-purple-700 disabled:bg-gray-400 rounded-md transition-colors"
          >
            {isRunning.cluster ? (
              <div className="animate-spin w-3 h-3 border border-white border-t-transparent rounded-full" />
            ) : (
              <>
                <Zap className="w-3 h-3 mr-1" />
                Cluster Keywords
              </>
            )}
          </button>
        </div>
        
        {/* SEO Services Management Button */}
        <div className="mt-3 pt-3 border-t border-gray-200">
          <button
            onClick={() => onManageCampaigns(business)}
            className="w-full flex items-center justify-center px-3 py-2 text-xs font-medium text-white bg-florida-blue-600 hover:bg-florida-blue-700 rounded-md transition-colors"
          >
            <Zap className="w-3 h-3 mr-1" />
            Manage 39 SEO Services
          </button>
        </div>
      </div>
      
      <div className="mt-4 pt-4 border-t border-gray-200">
        <div className="flex items-center space-x-4 text-xs text-gray-500">
          <span>Started: {new Date(business.startDate).toLocaleDateString()}</span>
          <span>•</span>
          <a 
            href={`mailto:${business.email}`}
            className="text-florida-blue-600 hover:text-florida-blue-700"
          >
            {business.email}
          </a>
        </div>
      </div>
    </div>
  )
}

export default function AdminPage() {
  const [selectedBusiness, setSelectedBusiness] = useState<any>(null)
  const [showServiceManager, setShowServiceManager] = useState(false)
  const [activeTab, setActiveTab] = useState<'overview' | 'business-intelligence' | 'execution-logs' | 'client-management'>('overview')

  const handleManageCampaigns = (business: any) => {
    setSelectedBusiness(business)
    setShowServiceManager(true)
  }

  return (
    <>
      <title>Admin Dashboard - Central Florida SEO Platform</title>
      
      <div className="min-h-screen bg-gray-50">
        {/* Header */}
        <div className="bg-white shadow-sm border-b border-gray-200">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-3xl font-bold text-gray-900">Admin Dashboard</h1>
                <p className="text-gray-600 mt-1">Central Florida SEO Platform Overview</p>
              </div>
              <div className="text-right">
                <p className="text-sm text-gray-500">Last updated</p>
                <p className="text-lg font-semibold text-gray-900">
                  {new Date().toLocaleDateString()} {new Date().toLocaleTimeString()}
                </p>
              </div>
            </div>
          </div>
        </div>

        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {/* Navigation Tabs */}
          <div className="mb-8">
            <div className="border-b border-gray-200">
              <nav className="-mb-px flex space-x-8">
                <button
                  onClick={() => setActiveTab('overview')}
                  className={`py-2 px-1 border-b-2 font-medium text-sm ${
                    activeTab === 'overview' 
                      ? 'border-florida-blue-500 text-florida-blue-600' 
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
                >
                  <BarChart3 className="w-4 h-4 inline mr-2" />
                  Overview
                </button>
                <button
                  onClick={() => setActiveTab('business-intelligence')}
                  className={`py-2 px-1 border-b-2 font-medium text-sm ${
                    activeTab === 'business-intelligence' 
                      ? 'border-florida-blue-500 text-florida-blue-600' 
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
                >
                  <PieChart className="w-4 h-4 inline mr-2" />
                  Business Intelligence
                </button>
                <button
                  onClick={() => setActiveTab('execution-logs')}
                  className={`py-2 px-1 border-b-2 font-medium text-sm ${
                    activeTab === 'execution-logs' 
                      ? 'border-florida-blue-500 text-florida-blue-600' 
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
                >
                  <Activity className="w-4 h-4 inline mr-2" />
                  Execution Logs
                </button>
                <button
                  onClick={() => setActiveTab('client-management')}
                  className={`py-2 px-1 border-b-2 font-medium text-sm ${
                    activeTab === 'client-management' 
                      ? 'border-florida-blue-500 text-florida-blue-600' 
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
                >
                  <Users className="w-4 h-4 inline mr-2" />
                  Client Management
                </button>
              </nav>
            </div>
          </div>
          {/* Tab Content */}
          {activeTab === 'overview' && (
            <div>
              {/* Stats Overview */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
                <StatCard
                  title="Total Businesses"
                  value={platformStats.totalBusinesses}
                  change={15.2}
                  icon={Users}
                />
                <StatCard
                  title="Active Subscriptions"
                  value={platformStats.activeSubscriptions}
                  change={8.1}
                  icon={Star}
                />
                <StatCard
                  title="Monthly Revenue"
                  value={platformStats.monthlyRevenue}
                  change={12.5}
                  icon={DollarSign}
                  prefix="$"
                />
                <StatCard
                  title="Avg SEO Score"
                  value={platformStats.averageSEOScore}
                  change={6.7}
                  icon={TrendingUp}
                  suffix="/100"
                />
              </div>

              {/* Secondary Stats */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
                <StatCard
                  title="Keywords Tracked"
                  value={platformStats.totalKeywordsTracked}
                  change={23.4}
                  icon={Search}
                />
                <StatCard
                  title="Total Organic Traffic"
                  value={platformStats.totalOrganicTraffic}
                  change={18.9}
                  icon={Globe}
                />
                <StatCard
                  title="Active Campaigns"
                  value={platformStats.activeCampaigns}
                  change={5.3}
                  icon={Play}
                />
                <StatCard
                  title="Content Briefs"
                  value={platformStats.totalContentBriefs}
                  change={42.1}
                  icon={FileText}
                />
              </div>

              {/* Recent Performance */}
              <div className="bg-white rounded-lg shadow-md p-6 mb-8">
                <h2 className="text-xl font-bold text-gray-900 mb-6">Top Performing Businesses</h2>
                
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Business</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Plan</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">SEO Score</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Traffic</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Revenue</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-200">
                      {mockBusinessesWithCampaigns
                        .sort((a, b) => b.seoScore - a.seoScore)
                        .slice(0, 5)
                        .map((business) => (
                        <tr key={business.id} className="hover:bg-gray-50">
                          <td className="px-4 py-4">
                            <div>
                              <div className="text-sm font-medium text-gray-900">{business.name}</div>
                              <div className="text-sm text-gray-500">{business.owner}</div>
                            </div>
                          </td>
                          <td className="px-4 py-4">
                            <span className="text-sm text-gray-900">{business.plan}</span>
                          </td>
                          <td className="px-4 py-4">
                            <div className="flex items-center">
                              <div className={`text-sm font-medium ${
                                business.seoScore >= 80 ? 'text-green-600' : 
                                business.seoScore >= 60 ? 'text-yellow-600' : 'text-red-600'
                              }`}>
                                {business.seoScore}/100
                              </div>
                            </div>
                          </td>
                          <td className="px-4 py-4 text-sm text-gray-900">
                            {business.organicTraffic.toLocaleString()}
                          </td>
                          <td className="px-4 py-4 text-sm text-gray-900">
                            ${business.monthlySpend}/mo
                          </td>
                          <td className="px-4 py-4">
                            <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                              business.status === 'active' ? 'bg-green-100 text-green-800' :
                              business.status === 'audit_complete' ? 'bg-blue-100 text-blue-800' :
                              'bg-gray-100 text-gray-800'
                            }`}>
                              {business.status.replace('_', ' ')}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* SEO Platform Analytics */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
                {/* Platform Performance */}
                <div className="bg-white rounded-lg shadow-md p-6">
                  <h2 className="text-xl font-bold text-gray-900 mb-6">Platform Performance</h2>
                  
                  <div className="grid grid-cols-2 gap-4">
                    <div className="text-center p-4 bg-florida-blue-50 rounded-lg">
                      <div className="text-2xl font-bold text-florida-blue-900">67%</div>
                      <div className="text-sm text-gray-600">Avg Traffic Increase</div>
                      <div className="text-xs text-gray-500 mt-1">Past 6 months</div>
                    </div>
                    
                    <div className="text-center p-4 bg-florida-orange-50 rounded-lg">
                      <div className="text-2xl font-bold text-florida-orange-900">4.2</div>
                      <div className="text-sm text-gray-600">Customer Rating</div>
                      <div className="text-xs text-gray-500 mt-1">Out of 5 stars</div>
                    </div>
                    
                    <div className="text-center p-4 bg-florida-green-50 rounded-lg">
                      <div className="text-2xl font-bold text-florida-green-900">94%</div>
                      <div className="text-sm text-gray-600">Customer Retention</div>
                      <div className="text-xs text-gray-500 mt-1">12-month period</div>
                    </div>
                    
                    <div className="text-center p-4 bg-purple-50 rounded-lg">
                      <div className="text-2xl font-bold text-purple-900">{platformStats.publishedContent}</div>
                      <div className="text-sm text-gray-600">Published Content</div>
                      <div className="text-xs text-gray-500 mt-1">This month</div>
                    </div>
                  </div>
                </div>
                
                {/* Current SEO Tasks */}
                <div className="bg-white rounded-lg shadow-md p-6">
                  <h2 className="text-xl font-bold text-gray-900 mb-6">SEO Automation Status</h2>
                  
                  <div className="space-y-4">
                    <div className="flex items-center justify-between p-3 bg-green-50 rounded-lg">
                      <div className="flex items-center">
                        <CheckCircle className="w-5 h-5 text-green-600 mr-3" />
                        <div>
                          <div className="text-sm font-medium text-gray-900">Running Tasks</div>
                          <div className="text-xs text-gray-500">{platformStats.runningTasks} currently active</div>
                        </div>
                      </div>
                      <div className="text-lg font-bold text-green-600">{platformStats.runningTasks}</div>
                    </div>
                    
                    <div className="flex items-center justify-between p-3 bg-yellow-50 rounded-lg">
                      <div className="flex items-center">
                        <AlertCircle className="w-5 h-5 text-yellow-600 mr-3" />
                        <div>
                          <div className="text-sm font-medium text-gray-900">Pending Tasks</div>
                          <div className="text-xs text-gray-500">{platformStats.pendingTasks} in queue</div>
                        </div>
                      </div>
                      <div className="text-lg font-bold text-yellow-600">{platformStats.pendingTasks}</div>
                    </div>
                    
                    <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                      <div className="flex items-center">
                        <Zap className="w-5 h-5 text-gray-600 mr-3" />
                        <div>
                          <div className="text-sm font-medium text-gray-900">Total Campaigns</div>
                          <div className="text-xs text-gray-500">{platformStats.activeCampaigns} active campaigns</div>
                        </div>
                      </div>
                      <div className="text-lg font-bold text-gray-600">{platformStats.activeCampaigns}</div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'business-intelligence' && <BusinessIntelligenceDashboard />}

          {activeTab === 'execution-logs' && <SEOExecutionLogs />}

          {activeTab === 'client-management' && (
            <div className="mb-8">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-bold text-gray-900">All Customer Accounts</h2>
                <div className="text-sm text-gray-500">
                  {mockBusinessesWithCampaigns.length} businesses • {mockBusinessesWithCampaigns.filter(b => b.status === 'active').length} active
                </div>
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {mockBusinessesWithCampaigns.map((business) => (
                  <BusinessCard key={business.id} business={business} onManageCampaigns={handleManageCampaigns} />
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* SEO Services Manager Modal */}
      {showServiceManager && selectedBusiness && (
        <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-lg max-w-7xl w-full max-h-[95vh] overflow-hidden flex flex-col">
            {/* Modal Header */}
            <div className="flex items-center justify-between p-6 border-b border-gray-200">
              <div>
                <h2 className="text-2xl font-bold text-gray-900">SEO Services Management</h2>
                <p className="text-gray-600 mt-1">Managing services for {selectedBusiness.name}</p>
              </div>
              <button
                onClick={() => {
                  setShowServiceManager(false)
                  setSelectedBusiness(null)
                }}
                className="p-2 text-gray-400 hover:text-gray-600 transition-colors"
              >
                <X className="w-6 h-6" />
              </button>
            </div>
            
            {/* Modal Content */}
            <div className="flex-1 overflow-auto p-6">
              <CustomerProfileManager customerId={selectedBusiness.id} />
            </div>
          </div>
        </div>
      )}
    </>
  )
}