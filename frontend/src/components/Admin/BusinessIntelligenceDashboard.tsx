import { useState, useEffect } from 'react'
import { 
  TrendingUp, DollarSign, Users, AlertTriangle, CheckCircle, Clock, 
  BarChart3, PieChart, Calendar, FileText, Zap, Target, Award,
  ArrowUpRight, ArrowDownRight, Filter, Download, RefreshCw,
  Bell, MessageSquare, Phone, Mail, ExternalLink
} from 'lucide-react'
import ClientServiceHistory from './ClientServiceHistory'

interface BusinessMetrics {
  // Realistic - Your billing/subscription data
  totalRevenue: number
  monthlyRecurring: number
  activeClients: number
  newClientsThisMonth: number
  avgClientValue: number
  
  // Realistic - Your service tracking
  servicesExecuted: number
  failedServices: number
  avgExecutionTime: number
  
  // Realistic - Client plan distribution
  professionalClients: number
  businessClients: number
  enterpriseClients: number
}

interface ClientInsight {
  clientId: string
  clientName: string
  plan: 'professional' | 'business' | 'enterprise'
  monthlyValue: number
  
  // Realistic - Your service tracking data
  lastServiceRun: string
  nextBilling: string
  servicesActive: number
  successfulRuns: number
  failedRuns: number
  
  // Realistic - SEO tool data (if you have API access)
  avgKeywordPosition?: number
  trackedKeywords?: number
  technicalIssues?: number
  
  // Realistic - Payment/billing status
  paymentStatus: 'current' | 'overdue' | 'failed'
  serviceStatus: 'active' | 'paused' | 'cancelled'
  
  // Realistic - Your observations/notes
  notes: string[]
  alertsEnabled: boolean
}

const BusinessIntelligenceDashboard = () => {
  const [timeRange, setTimeRange] = useState('30d')
  const [selectedMetric, setSelectedMetric] = useState('revenue')
  const [selectedClient, setSelectedClient] = useState<ClientInsight | null>(null)
  const [showServiceHistory, setShowServiceHistory] = useState(false)
  
  // Realistic business metrics - based on your billing and service data
  const businessMetrics: BusinessMetrics = {
    // Your billing system data
    totalRevenue: 127450,
    monthlyRecurring: 24800,
    activeClients: 28,
    newClientsThisMonth: 6,
    avgClientValue: 885, // MRR / active clients
    
    // Your service execution tracking
    servicesExecuted: 342,
    failedServices: 12,
    avgExecutionTime: 45, // minutes
    
    // Client plan distribution
    professionalClients: 15,
    businessClients: 10,
    enterpriseClients: 3
  }

  // Realistic client insights - based on your actual tracking capabilities
  const clientInsights: ClientInsight[] = [
    {
      clientId: '1',
      clientName: 'Tampa Bay Law Group',
      plan: 'enterprise',
      monthlyValue: 599,
      lastServiceRun: '2024-08-14T10:30:00Z',
      nextBilling: '2024-09-15',
      servicesActive: 25,
      successfulRuns: 78,
      failedRuns: 2,
      avgKeywordPosition: 12.4,
      trackedKeywords: 247,
      technicalIssues: 3,
      paymentStatus: 'current',
      serviceStatus: 'active',
      notes: ['Client very responsive to recommendations', 'Considering expansion to PPC'],
      alertsEnabled: true
    },
    {
      clientId: '2',
      clientName: 'Sunset Grill Orlando',
      plan: 'business',
      monthlyValue: 299,
      lastServiceRun: '2024-08-14T09:15:00Z',
      nextBilling: '2024-09-10',
      servicesActive: 15,
      successfulRuns: 45,
      failedRuns: 1,
      avgKeywordPosition: 18.7,
      trackedKeywords: 156,
      technicalIssues: 8,
      paymentStatus: 'current',
      serviceStatus: 'active',
      notes: ['Website speed issues need addressing', 'Good engagement with monthly reports'],
      alertsEnabled: true
    },
    {
      clientId: '3',
      clientName: 'Prestige Dental Care',
      plan: 'professional',
      monthlyValue: 149,
      lastServiceRun: '2024-08-13T14:20:00Z',
      nextBilling: '2024-08-25',
      servicesActive: 8,
      successfulRuns: 22,
      failedRuns: 5,
      avgKeywordPosition: 35.2,
      trackedKeywords: 89,
      technicalIssues: 15,
      paymentStatus: 'overdue',
      serviceStatus: 'paused',
      notes: ['Payment issues - following up', 'Site has technical problems', 'May need plan downgrade'],
      alertsEnabled: false
    }
  ]

  const getPaymentStatusColor = (status: ClientInsight['paymentStatus']) => {
    switch (status) {
      case 'current': return 'bg-green-100 text-green-800 border-green-200'
      case 'overdue': return 'bg-yellow-100 text-yellow-800 border-yellow-200'
      case 'failed': return 'bg-red-100 text-red-800 border-red-200'
    }
  }

  const getServiceStatusColor = (status: ClientInsight['serviceStatus']) => {
    switch (status) {
      case 'active': return 'bg-green-100 text-green-800 border-green-200'
      case 'paused': return 'bg-yellow-100 text-yellow-800 border-yellow-200'
      case 'cancelled': return 'bg-red-100 text-red-800 border-red-200'
    }
  }

  const MetricCard = ({ title, value, change, icon: Icon, prefix = '', suffix = '', format = 'number' }: {
    title: string
    value: number
    change?: number
    icon: any
    prefix?: string
    suffix?: string
    format?: 'number' | 'currency' | 'percentage'
  }) => {
    const formatValue = (val: number) => {
      switch (format) {
        case 'currency': return `$${val.toLocaleString()}`
        case 'percentage': return `${val}%`
        default: return val.toLocaleString()
      }
    }

    const isPositive = change && change > 0
    const isNegative = change && change < 0

    return (
      <div className="bg-white rounded-lg shadow-md p-6 border border-gray-200">
        <div className="flex items-center justify-between">
          <div className="flex-1">
            <p className="text-sm font-medium text-gray-600">{title}</p>
            <p className="text-2xl font-bold text-gray-900 mt-1">
              {prefix}{formatValue(value)}{suffix}
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
                <span className="ml-1">vs last month</span>
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

  return (
    <div className="space-y-6">
      {/* Business Overview Header */}
      <div className="bg-white rounded-lg shadow-md p-6 border border-gray-200">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold text-gray-900">Business Intelligence Dashboard</h2>
            <p className="text-gray-600 mt-1">Complete overview of your SEO service business performance</p>
          </div>
          <div className="flex items-center space-x-3">
            <select
              value={timeRange}
              onChange={(e) => setTimeRange(e.target.value)}
              className="border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-florida-blue-500"
            >
              <option value="7d">Last 7 days</option>
              <option value="30d">Last 30 days</option>
              <option value="90d">Last 90 days</option>
              <option value="1y">Last year</option>
            </select>
            <button className="flex items-center px-4 py-2 bg-florida-blue-600 text-white rounded-md hover:bg-florida-blue-700 text-sm">
              <Download className="w-4 h-4 mr-2" />
              Export Report
            </button>
          </div>
        </div>
      </div>

      {/* Key Business Metrics - Realistic Data */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <MetricCard
          title="Monthly Recurring Revenue"
          value={businessMetrics.monthlyRecurring}
          change={18.5}
          icon={DollarSign}
          format="currency"
        />
        <MetricCard
          title="Active Clients"
          value={businessMetrics.activeClients}
          change={12.0}
          icon={Users}
          format="number"
        />
        <MetricCard
          title="Average Client Value"
          value={businessMetrics.avgClientValue}
          change={8.2}
          icon={Target}
          format="currency"
        />
        <MetricCard
          title="Service Success Rate"
          value={Math.round((businessMetrics.servicesExecuted - businessMetrics.failedServices) / businessMetrics.servicesExecuted * 100)}
          change={2.1}
          icon={CheckCircle}
          format="percentage"
        />
      </div>

      {/* Client Health Overview */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-lg shadow-md p-6 border border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Client Plan Distribution</h3>
          <div className="grid grid-cols-3 gap-4">
            <div className="text-center p-4 bg-purple-50 rounded-lg">
              <div className="text-2xl font-bold text-purple-600">{businessMetrics.enterpriseClients}</div>
              <div className="text-sm text-purple-700">Enterprise</div>
              <div className="text-xs text-gray-500 mt-1">$599/month</div>
            </div>
            <div className="text-center p-4 bg-blue-50 rounded-lg">
              <div className="text-2xl font-bold text-blue-600">{businessMetrics.businessClients}</div>
              <div className="text-sm text-blue-700">Business</div>
              <div className="text-xs text-gray-500 mt-1">$299/month</div>
            </div>
            <div className="text-center p-4 bg-green-50 rounded-lg">
              <div className="text-2xl font-bold text-green-600">{businessMetrics.professionalClients}</div>
              <div className="text-sm text-green-700">Professional</div>
              <div className="text-xs text-gray-500 mt-1">$149/month</div>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow-md p-6 border border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Service Performance</h3>
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600">Services Executed This Month</span>
              <span className="text-lg font-bold text-gray-900">{businessMetrics.servicesExecuted}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600">Failed Services</span>
              <span className="text-lg font-bold text-red-600">{businessMetrics.failedServices}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600">Avg Execution Time</span>
              <span className="text-lg font-bold text-blue-600">{businessMetrics.avgExecutionTime}min</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600">New Clients This Month</span>
              <span className="text-lg font-bold text-green-600">{businessMetrics.newClientsThisMonth}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Client Intelligence Cards */}
      <div className="bg-white rounded-lg shadow-md p-6 border border-gray-200">
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-lg font-semibold text-gray-900">Client Intelligence & Action Items</h3>
          <div className="flex items-center space-x-2">
            <Filter className="w-4 h-4 text-gray-400" />
            <select className="border border-gray-300 rounded-md px-3 py-1 text-sm">
              <option>All Clients</option>
              <option>High Priority</option>
              <option>At Risk</option>
              <option>Growth Opportunities</option>
            </select>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
          {clientInsights.map((client) => (
            <div key={client.clientId} className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow">
              {/* Client Header */}
              <div className="flex items-center justify-between mb-3">
                <div>
                  <h4 className="font-semibold text-gray-900">{client.clientName}</h4>
                  <p className="text-sm text-gray-600">${client.monthlyValue}/month • {client.plan}</p>
                </div>
                <div className="flex flex-col space-y-1">
                  <span className={`px-2 py-1 rounded-full text-xs font-medium border ${getPaymentStatusColor(client.paymentStatus)}`}>
                    {client.paymentStatus}
                  </span>
                  <span className={`px-2 py-1 rounded-full text-xs font-medium border ${getServiceStatusColor(client.serviceStatus)}`}>
                    {client.serviceStatus}
                  </span>
                </div>
              </div>

              {/* Key Metrics - Realistic Data */}
              <div className="grid grid-cols-2 gap-2 mb-3">
                <div className="text-center p-2 bg-gray-50 rounded">
                  <div className="text-sm font-bold text-gray-900">{client.servicesActive}</div>
                  <div className="text-xs text-gray-500">Active Services</div>
                </div>
                <div className="text-center p-2 bg-gray-50 rounded">
                  <div className="text-sm font-bold text-gray-900">{Math.round((client.successfulRuns / (client.successfulRuns + client.failedRuns)) * 100)}%</div>
                  <div className="text-xs text-gray-500">Success Rate</div>
                </div>
              </div>
              
              {/* SEO Data (if available) */}
              {(client.trackedKeywords || client.avgKeywordPosition) && (
                <div className="grid grid-cols-2 gap-2 mb-3">
                  {client.trackedKeywords && (
                    <div className="text-center p-2 bg-blue-50 rounded">
                      <div className="text-sm font-bold text-blue-900">{client.trackedKeywords}</div>
                      <div className="text-xs text-gray-500">Keywords Tracked</div>
                    </div>
                  )}
                  {client.avgKeywordPosition && (
                    <div className="text-center p-2 bg-blue-50 rounded">
                      <div className="text-sm font-bold text-blue-900">{client.avgKeywordPosition}</div>
                      <div className="text-xs text-gray-500">Avg Position</div>
                    </div>
                  )}
                </div>
              )}
              
              {/* Technical Issues */}
              {client.technicalIssues && client.technicalIssues > 0 && (
                <div className="mb-3 p-2 bg-yellow-50 rounded">
                  <div className="text-sm font-medium text-yellow-800">{client.technicalIssues} Technical Issues</div>
                  <div className="text-xs text-yellow-600">Need attention</div>
                </div>
              )}

              {/* Client Notes */}
              {client.notes.length > 0 && (
                <div className="mb-3">
                  <div className="text-xs font-medium text-gray-700 mb-1">📝 Notes:</div>
                  {client.notes.map((note, idx) => (
                    <div key={idx} className="text-xs text-gray-600 bg-gray-50 px-2 py-1 rounded mb-1">
                      {note}
                    </div>
                  ))}
                </div>
              )}

              {/* Service Timing */}
              <div className="mb-3 text-xs text-gray-500">
                <div>Last Service: {new Date(client.lastServiceRun).toLocaleDateString()}</div>
                <div>Next Billing: {new Date(client.nextBilling).toLocaleDateString()}</div>
              </div>

              {/* Action Buttons */}
              <div className="flex items-center space-x-2 mt-4">
                <button 
                  onClick={() => {
                    setSelectedClient(client)
                    setShowServiceHistory(true)
                  }}
                  className="flex-1 px-3 py-1 bg-florida-blue-600 text-white text-xs rounded hover:bg-florida-blue-700"
                >
                  <FileText className="w-3 h-3 inline mr-1" />
                  Service History
                </button>
                <button className="px-3 py-1 bg-gray-100 text-gray-700 text-xs rounded hover:bg-gray-200">
                  <MessageSquare className="w-3 h-3 inline mr-1" />
                  Contact
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Service History Modal */}
      {showServiceHistory && selectedClient && (
        <ClientServiceHistory
          clientId={selectedClient.clientId}
          clientName={selectedClient.clientName}
          onClose={() => {
            setShowServiceHistory(false)
            setSelectedClient(null)
          }}
        />
      )}
    </div>
  )
}

export default BusinessIntelligenceDashboard