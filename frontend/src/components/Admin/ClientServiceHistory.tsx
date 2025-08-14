import { useState, useEffect } from 'react'
import { 
  Clock, CheckCircle, AlertCircle, XCircle, Calendar, FileText, 
  Search, Filter, Download, Eye, ChevronDown, ChevronRight,
  PlayCircle, PauseCircle, Settings, ExternalLink
} from 'lucide-react'

interface ServiceLog {
  id: string
  serviceName: string
  serviceCategory: string
  status: 'completed' | 'failed' | 'running' | 'scheduled'
  startTime: string
  endTime?: string
  duration?: number
  executedBy: 'automated' | 'manual'
  results?: {
    [key: string]: any
  }
  errors?: string[]
  logs: string[]
  cost: number
  billedToClient: boolean
}

interface ClientServiceHistoryProps {
  clientId: string
  clientName: string
  onClose: () => void
}

const ClientServiceHistory = ({ clientId, clientName, onClose }: ClientServiceHistoryProps) => {
  const [serviceLogs, setServiceLogs] = useState<ServiceLog[]>([])
  const [expandedLog, setExpandedLog] = useState<string | null>(null)
  const [filters, setFilters] = useState({
    status: 'all',
    service: 'all',
    dateRange: '30d',
    search: ''
  })
  const [selectedMonth, setSelectedMonth] = useState(new Date().toISOString().slice(0, 7))

  // Mock service history data - replace with real API call
  useEffect(() => {
    const mockServiceLogs: ServiceLog[] = [
      {
        id: 'svc-001',
        serviceName: 'Keyword Discovery',
        serviceCategory: 'Keyword Research',
        status: 'completed',
        startTime: '2024-08-14T10:30:00Z',
        endTime: '2024-08-14T10:45:00Z',
        duration: 15,
        executedBy: 'automated',
        results: {
          keywordsFound: 247,
          newKeywords: 23,
          topOpportunities: 12
        },
        logs: [
          '10:30:15 - Starting keyword discovery for client',
          '10:31:22 - Analyzing seed keywords and competitor data',
          '10:33:45 - Found 247 related keywords using semantic analysis',
          '10:35:12 - Filtering keywords by search volume and competition',
          '10:42:30 - Generated keyword clusters for content strategy',
          '10:44:15 - Updated keyword database and rankings',
          '10:45:00 - Keyword discovery completed successfully'
        ],
        cost: 12.50,
        billedToClient: true
      },
      {
        id: 'svc-002',
        serviceName: 'Technical SEO Audit',
        serviceCategory: 'Technical SEO',
        status: 'completed',
        startTime: '2024-08-13T09:15:00Z',
        endTime: '2024-08-13T09:35:00Z',
        duration: 20,
        executedBy: 'automated',
        results: {
          issuesFound: 23,
          criticalIssues: 5,
          fixedIssues: 18,
          pagesCrawled: 156
        },
        logs: [
          '09:15:30 - Starting comprehensive technical SEO audit',
          '09:16:45 - Crawling website structure and indexability',
          '09:18:20 - Found 23 technical issues to address',
          '09:22:15 - Fixed 18 issues automatically',
          '09:25:30 - Generated technical SEO report',
          '09:35:00 - Technical audit completed'
        ],
        cost: 25.00,
        billedToClient: true
      },
      {
        id: 'svc-003',
        serviceName: 'Content Brief Generation',
        serviceCategory: 'Content Strategy',
        status: 'failed',
        startTime: '2024-08-12T14:20:00Z',
        endTime: '2024-08-12T14:25:00Z',
        duration: 5,
        executedBy: 'automated',
        errors: [
          'API rate limit exceeded for competitor analysis',
          'Backup data source unavailable',
          'Service requires manual intervention'
        ],
        logs: [
          '14:20:15 - Starting content brief generation',
          '14:21:30 - Analyzing target keyword: dental implants',
          '14:22:45 - ERROR: Unable to access competitor analysis data',
          '14:23:00 - Retrying with alternative data source...',
          '14:24:15 - ERROR: API rate limit exceeded',
          '14:25:00 - Content brief generation failed'
        ],
        cost: 0.00,
        billedToClient: false
      },
      {
        id: 'svc-004',
        serviceName: 'Google My Business Optimization',
        serviceCategory: 'Local SEO',
        status: 'completed',
        startTime: '2024-08-11T16:00:00Z',
        endTime: '2024-08-11T16:30:00Z',
        duration: 30,
        executedBy: 'manual',
        results: {
          postsCreated: 3,
          photosOptimized: 8,
          hoursUpdated: true,
          reviewsResponded: 2
        },
        logs: [
          '16:00:00 - Manual GMB optimization started',
          '16:05:00 - Updated business hours and contact information',
          '16:10:00 - Optimized business description with target keywords',
          '16:15:00 - Uploaded and optimized 8 new photos',
          '16:20:00 - Created 3 engaging GMB posts',
          '16:25:00 - Responded to 2 recent customer reviews',
          '16:30:00 - GMB optimization completed'
        ],
        cost: 45.00,
        billedToClient: true
      },
      {
        id: 'svc-005',
        serviceName: 'Automated Site Monitoring',
        serviceCategory: 'Technical SEO',
        status: 'running',
        startTime: '2024-08-14T12:00:00Z',
        executedBy: 'automated',
        logs: [
          '12:00:00 - Starting daily site monitoring',
          '12:01:00 - Checking site uptime and performance',
          '12:02:30 - Monitoring Core Web Vitals metrics',
          '12:05:00 - Checking for broken links and 404 errors...'
        ],
        cost: 5.00,
        billedToClient: true
      }
    ]
    setServiceLogs(mockServiceLogs)
  }, [clientId])

  const getStatusIcon = (status: ServiceLog['status']) => {
    switch (status) {
      case 'completed': return <CheckCircle className="w-4 h-4 text-green-600" />
      case 'failed': return <XCircle className="w-4 h-4 text-red-600" />
      case 'running': return <PlayCircle className="w-4 h-4 text-blue-600" />
      case 'scheduled': return <Clock className="w-4 h-4 text-yellow-600" />
    }
  }

  const getStatusColor = (status: ServiceLog['status']) => {
    switch (status) {
      case 'completed': return 'bg-green-100 text-green-800 border-green-200'
      case 'failed': return 'bg-red-100 text-red-800 border-red-200'
      case 'running': return 'bg-blue-100 text-blue-800 border-blue-200'
      case 'scheduled': return 'bg-yellow-100 text-yellow-800 border-yellow-200'
    }
  }

  const formatDuration = (minutes: number) => {
    if (minutes < 60) return `${minutes}m`
    const hours = Math.floor(minutes / 60)
    const mins = minutes % 60
    return `${hours}h ${mins}m`
  }

  const exportServiceHistory = () => {
    const csvContent = [
      ['Date', 'Service', 'Status', 'Duration', 'Cost', 'Billed'].join(','),
      ...serviceLogs.map(log => [
        new Date(log.startTime).toLocaleDateString(),
        log.serviceName,
        log.status,
        log.duration ? formatDuration(log.duration) : 'In Progress',
        `$${log.cost.toFixed(2)}`,
        log.billedToClient ? 'Yes' : 'No'
      ].join(','))
    ].join('\n')

    const blob = new Blob([csvContent], { type: 'text/csv' })
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${clientName}-service-history-${new Date().toISOString().split('T')[0]}.csv`
    a.click()
  }

  const totalCost = serviceLogs.reduce((sum, log) => sum + log.cost, 0)
  const billedCost = serviceLogs.filter(log => log.billedToClient).reduce((sum, log) => sum + log.cost, 0)

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-lg max-w-6xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <div>
            <h2 className="text-2xl font-bold text-gray-900">Service History</h2>
            <p className="text-gray-600 mt-1">{clientName} - Complete service execution log</p>
          </div>
          <div className="flex items-center space-x-3">
            <button 
              onClick={exportServiceHistory}
              className="flex items-center px-4 py-2 bg-florida-blue-600 text-white rounded-md hover:bg-florida-blue-700 text-sm"
            >
              <Download className="w-4 h-4 mr-2" />
              Export History
            </button>
            <button
              onClick={onClose}
              className="p-2 text-gray-400 hover:text-gray-600"
            >
              ✕
            </button>
          </div>
        </div>

        {/* Summary Stats */}
        <div className="px-6 py-4 bg-gray-50 border-b border-gray-200">
          <div className="grid grid-cols-4 gap-4">
            <div className="text-center">
              <div className="text-xl font-bold text-gray-900">{serviceLogs.length}</div>
              <div className="text-sm text-gray-600">Total Services</div>
            </div>
            <div className="text-center">
              <div className="text-xl font-bold text-green-600">{serviceLogs.filter(log => log.status === 'completed').length}</div>
              <div className="text-sm text-gray-600">Completed</div>
            </div>
            <div className="text-center">
              <div className="text-xl font-bold text-red-600">{serviceLogs.filter(log => log.status === 'failed').length}</div>
              <div className="text-sm text-gray-600">Failed</div>
            </div>
            <div className="text-center">
              <div className="text-xl font-bold text-florida-blue-600">${billedCost.toFixed(2)}</div>
              <div className="text-sm text-gray-600">Total Billed</div>
            </div>
          </div>
        </div>

        {/* Filters */}
        <div className="px-6 py-4 border-b border-gray-200">
          <div className="grid grid-cols-4 gap-4">
            <div className="relative">
              <Search className="w-4 h-4 absolute left-3 top-3 text-gray-400" />
              <input
                type="text"
                placeholder="Search services..."
                value={filters.search}
                onChange={(e) => setFilters(prev => ({ ...prev, search: e.target.value }))}
                className="pl-10 w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-florida-blue-500"
              />
            </div>
            <select
              value={filters.status}
              onChange={(e) => setFilters(prev => ({ ...prev, status: e.target.value }))}
              className="border border-gray-300 rounded-md px-3 py-2 text-sm"
            >
              <option value="all">All Status</option>
              <option value="completed">Completed</option>
              <option value="failed">Failed</option>
              <option value="running">Running</option>
            </select>
            <select
              value={filters.service}
              onChange={(e) => setFilters(prev => ({ ...prev, service: e.target.value }))}
              className="border border-gray-300 rounded-md px-3 py-2 text-sm"
            >
              <option value="all">All Services</option>
              <option value="keyword">Keyword Research</option>
              <option value="technical">Technical SEO</option>
              <option value="content">Content Strategy</option>
            </select>
            <input
              type="month"
              value={selectedMonth}
              onChange={(e) => setSelectedMonth(e.target.value)}
              className="border border-gray-300 rounded-md px-3 py-2 text-sm"
            />
          </div>
        </div>

        {/* Service History Table */}
        <div className="flex-1 overflow-auto">
          <div className="space-y-2 p-6">
            {serviceLogs.map((log) => (
              <div key={log.id} className="border border-gray-200 rounded-lg">
                {/* Service Row */}
                <div 
                  className="p-4 hover:bg-gray-50 cursor-pointer flex items-center justify-between"
                  onClick={() => setExpandedLog(expandedLog === log.id ? null : log.id)}
                >
                  <div className="flex items-center space-x-4">
                    <button className="p-1">
                      {expandedLog === log.id ? 
                        <ChevronDown className="w-4 h-4 text-gray-400" /> : 
                        <ChevronRight className="w-4 h-4 text-gray-400" />
                      }
                    </button>
                    {getStatusIcon(log.status)}
                    <div>
                      <div className="font-medium text-gray-900">{log.serviceName}</div>
                      <div className="text-sm text-gray-500">{log.serviceCategory}</div>
                    </div>
                  </div>
                  
                  <div className="flex items-center space-x-6 text-sm">
                    <div>
                      <div className="text-gray-900">{new Date(log.startTime).toLocaleDateString()}</div>
                      <div className="text-gray-500">{new Date(log.startTime).toLocaleTimeString()}</div>
                    </div>
                    
                    <div className="text-center">
                      <span className={`px-2 py-1 rounded-full text-xs font-medium border ${getStatusColor(log.status)}`}>
                        {log.status}
                      </span>
                    </div>
                    
                    <div className="text-center min-w-16">
                      {log.duration ? formatDuration(log.duration) : 'Running'}
                    </div>
                    
                    <div className="text-center min-w-16">
                      <div className="font-medium">${log.cost.toFixed(2)}</div>
                      <div className="text-xs text-gray-500">
                        {log.billedToClient ? 'Billed' : 'Free'}
                      </div>
                    </div>
                    
                    <div className="text-center min-w-20">
                      <span className={`px-2 py-1 rounded text-xs ${
                        log.executedBy === 'automated' ? 'bg-blue-100 text-blue-800' : 'bg-purple-100 text-purple-800'
                      }`}>
                        {log.executedBy}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Expanded Details */}
                {expandedLog === log.id && (
                  <div className="border-t border-gray-200 p-4 bg-gray-50">
                    <div className="grid grid-cols-2 gap-6">
                      {/* Results */}
                      {log.results && (
                        <div>
                          <h4 className="font-medium text-gray-900 mb-2">Results</h4>
                          <div className="space-y-1 text-sm">
                            {Object.entries(log.results).map(([key, value]) => (
                              <div key={key} className="flex justify-between">
                                <span className="text-gray-600">{key}:</span>
                                <span className="font-medium">{value}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                      
                      {/* Execution Log */}
                      <div>
                        <h4 className="font-medium text-gray-900 mb-2">Execution Log</h4>
                        <div className="bg-gray-900 text-green-400 p-3 rounded text-xs font-mono max-h-32 overflow-y-auto">
                          {log.logs.map((logLine, index) => (
                            <div key={index} className="mb-1">{logLine}</div>
                          ))}
                        </div>
                      </div>
                    </div>
                    
                    {/* Errors */}
                    {log.errors && log.errors.length > 0 && (
                      <div className="mt-4">
                        <h4 className="font-medium text-gray-900 mb-2">Errors</h4>
                        <div className="space-y-2">
                          {log.errors.map((error, index) => (
                            <div key={index} className="bg-red-50 border border-red-200 text-red-700 p-2 rounded text-sm">
                              {error}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

export default ClientServiceHistory