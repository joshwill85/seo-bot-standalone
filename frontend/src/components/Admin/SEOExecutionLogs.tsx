import { useState, useEffect } from 'react'
import { 
  Clock, CheckCircle, AlertCircle, XCircle, Play, Pause, RotateCcw,
  Filter, Search, Download, ExternalLink, Eye, FileText, Zap,
  Calendar, User, Target, BarChart3, TrendingUp, AlertTriangle
} from 'lucide-react'

interface SEOExecutionLog {
  id: string
  clientId: string
  clientName: string
  serviceName: string
  serviceCategory: string
  status: 'running' | 'completed' | 'failed' | 'queued' | 'cancelled'
  startTime: string
  endTime?: string
  duration?: number
  results?: {
    keywordsFound?: number
    issuesFixed?: number
    contentGenerated?: number
    linksBuilt?: number
    trafficIncrease?: number
    rankingImprovements?: number
    [key: string]: any
  }
  logs: string[]
  errors?: string[]
  progress: number
  executedBy: string
  priority: 'low' | 'medium' | 'high' | 'urgent'
  automated: boolean
}

const SEOExecutionLogs = () => {
  const [logs, setLogs] = useState<SEOExecutionLog[]>([])
  const [filteredLogs, setFilteredLogs] = useState<SEOExecutionLog[]>([])
  const [selectedLog, setSelectedLog] = useState<SEOExecutionLog | null>(null)
  const [filters, setFilters] = useState({
    status: 'all',
    client: 'all',
    service: 'all',
    timeRange: '24h',
    search: ''
  })

  // Mock execution logs - replace with real data
  useEffect(() => {
    const mockLogs: SEOExecutionLog[] = [
      {
        id: 'log-001',
        clientId: '1',
        clientName: 'Tampa Bay Law Group',
        serviceName: 'Keyword Discovery',
        serviceCategory: 'Keyword Research',
        status: 'completed',
        startTime: '2024-08-14T10:30:00Z',
        endTime: '2024-08-14T10:45:00Z',
        duration: 15,
        results: {
          keywordsFound: 247,
          trafficIncrease: 12,
          rankingImprovements: 15
        },
        logs: [
          '10:30:15 - Starting keyword discovery for Tampa Bay Law Group',
          '10:31:22 - Analyzing seed keywords: personal injury lawyer, car accident attorney',
          '10:33:45 - Found 247 related keywords using semantic analysis',
          '10:35:12 - Filtering keywords by search volume and competition',
          '10:42:30 - Generated keyword clusters for content strategy',
          '10:44:15 - Updated keyword database and rankings',
          '10:45:00 - Keyword discovery completed successfully'
        ],
        progress: 100,
        executedBy: 'Auto-Scheduler',
        priority: 'medium',
        automated: true
      },
      {
        id: 'log-002',
        clientId: '2',
        clientName: 'Sunset Grill Orlando',
        serviceName: 'Technical SEO Audit',
        serviceCategory: 'Technical SEO',
        status: 'running',
        startTime: '2024-08-14T11:15:00Z',
        results: {
          issuesFixed: 12
        },
        logs: [
          '11:15:30 - Starting comprehensive technical SEO audit',
          '11:16:45 - Crawling website structure and indexability',
          '11:18:20 - Found 23 technical issues to address',
          '11:22:15 - Fixed 12 critical issues automatically',
          '11:25:30 - Analyzing Core Web Vitals and page speed...'
        ],
        progress: 65,
        executedBy: 'admin@centralfloridaseo.com',
        priority: 'high',
        automated: false
      },
      {
        id: 'log-003',
        clientId: '3',
        clientName: 'Prestige Dental Care',
        serviceName: 'Content Brief Generation',
        serviceCategory: 'Content Strategy',
        status: 'failed',
        startTime: '2024-08-14T09:00:00Z',
        endTime: '2024-08-14T09:05:00Z',
        duration: 5,
        logs: [
          '09:00:15 - Starting content brief generation',
          '09:01:30 - Analyzing target keyword: dental implants orlando',
          '09:02:45 - ERROR: Unable to access competitor analysis data',
          '09:03:00 - Retrying with alternative data source...',
          '09:04:15 - ERROR: API rate limit exceeded',
          '09:05:00 - Content brief generation failed'
        ],
        errors: [
          'API rate limit exceeded for competitor analysis',
          'Backup data source unavailable',
          'Service requires manual intervention'
        ],
        progress: 30,
        executedBy: 'Auto-Scheduler',
        priority: 'medium',
        automated: true
      },
      {
        id: 'log-004',
        clientId: '1',
        clientName: 'Tampa Bay Law Group',
        serviceName: 'Link Building Campaign',
        serviceCategory: 'Link Building',
        status: 'queued',
        startTime: '2024-08-14T12:00:00Z',
        logs: [
          '12:00:00 - Service queued for execution',
          '12:00:01 - Waiting for competitor backlink analysis to complete'
        ],
        progress: 0,
        executedBy: 'Auto-Scheduler',
        priority: 'low',
        automated: true
      }
    ]
    
    setLogs(mockLogs)
    setFilteredLogs(mockLogs)
  }, [])

  // Filter logs based on current filters
  useEffect(() => {
    let filtered = logs

    if (filters.status !== 'all') {
      filtered = filtered.filter(log => log.status === filters.status)
    }

    if (filters.client !== 'all') {
      filtered = filtered.filter(log => log.clientId === filters.client)
    }

    if (filters.search) {
      filtered = filtered.filter(log => 
        log.serviceName.toLowerCase().includes(filters.search.toLowerCase()) ||
        log.clientName.toLowerCase().includes(filters.search.toLowerCase()) ||
        log.serviceCategory.toLowerCase().includes(filters.search.toLowerCase())
      )
    }

    setFilteredLogs(filtered)
  }, [logs, filters])

  const getStatusIcon = (status: SEOExecutionLog['status']) => {
    switch (status) {
      case 'completed': return <CheckCircle className="w-4 h-4 text-green-600" />
      case 'running': return <Play className="w-4 h-4 text-blue-600" />
      case 'failed': return <XCircle className="w-4 h-4 text-red-600" />
      case 'queued': return <Clock className="w-4 h-4 text-yellow-600" />
      case 'cancelled': return <Pause className="w-4 h-4 text-gray-600" />
      default: return <AlertCircle className="w-4 h-4 text-gray-600" />
    }
  }

  const getStatusColor = (status: SEOExecutionLog['status']) => {
    switch (status) {
      case 'completed': return 'bg-green-100 text-green-800 border-green-200'
      case 'running': return 'bg-blue-100 text-blue-800 border-blue-200'
      case 'failed': return 'bg-red-100 text-red-800 border-red-200'
      case 'queued': return 'bg-yellow-100 text-yellow-800 border-yellow-200'
      case 'cancelled': return 'bg-gray-100 text-gray-800 border-gray-200'
      default: return 'bg-gray-100 text-gray-800 border-gray-200'
    }
  }

  const getPriorityColor = (priority: SEOExecutionLog['priority']) => {
    switch (priority) {
      case 'urgent': return 'bg-red-500'
      case 'high': return 'bg-orange-500'
      case 'medium': return 'bg-yellow-500'
      case 'low': return 'bg-green-500'
      default: return 'bg-gray-500'
    }
  }

  const formatDuration = (minutes: number) => {
    if (minutes < 60) return `${minutes}m`
    const hours = Math.floor(minutes / 60)
    const mins = minutes % 60
    return `${hours}h ${mins}m`
  }

  const exportLogs = () => {
    const csvContent = [
      ['Client', 'Service', 'Status', 'Start Time', 'Duration', 'Results'].join(','),
      ...filteredLogs.map(log => [
        log.clientName,
        log.serviceName,
        log.status,
        new Date(log.startTime).toLocaleString(),
        log.duration ? formatDuration(log.duration) : 'In Progress',
        Object.keys(log.results || {}).length
      ].join(','))
    ].join('\n')

    const blob = new Blob([csvContent], { type: 'text/csv' })
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `seo-execution-logs-${new Date().toISOString().split('T')[0]}.csv`
    a.click()
  }

  return (
    <div className="space-y-6">
      {/* Header & Filters */}
      <div className="bg-white rounded-lg shadow-md p-6 border border-gray-200">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-2xl font-bold text-gray-900">SEO Service Execution Logs</h2>
            <p className="text-gray-600 mt-1">Real-time monitoring of all SEO service executions</p>
          </div>
          <button 
            onClick={exportLogs}
            className="flex items-center px-4 py-2 bg-florida-blue-600 text-white rounded-md hover:bg-florida-blue-700"
          >
            <Download className="w-4 h-4 mr-2" />
            Export Logs
          </button>
        </div>

        {/* Filters */}
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
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
            className="border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-florida-blue-500"
          >
            <option value="all">All Status</option>
            <option value="running">Running</option>
            <option value="completed">Completed</option>
            <option value="failed">Failed</option>
            <option value="queued">Queued</option>
          </select>

          <select
            value={filters.client}
            onChange={(e) => setFilters(prev => ({ ...prev, client: e.target.value }))}
            className="border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-florida-blue-500"
          >
            <option value="all">All Clients</option>
            <option value="1">Tampa Bay Law Group</option>
            <option value="2">Sunset Grill Orlando</option>
            <option value="3">Prestige Dental Care</option>
          </select>

          <select
            value={filters.service}
            onChange={(e) => setFilters(prev => ({ ...prev, service: e.target.value }))}
            className="border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-florida-blue-500"
          >
            <option value="all">All Services</option>
            <option value="keyword">Keyword Research</option>
            <option value="technical">Technical SEO</option>
            <option value="content">Content Strategy</option>
            <option value="link">Link Building</option>
          </select>

          <select
            value={filters.timeRange}
            onChange={(e) => setFilters(prev => ({ ...prev, timeRange: e.target.value }))}
            className="border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-florida-blue-500"
          >
            <option value="1h">Last Hour</option>
            <option value="24h">Last 24 Hours</option>
            <option value="7d">Last 7 Days</option>
            <option value="30d">Last 30 Days</option>
          </select>
        </div>
      </div>

      {/* Execution Logs Table */}
      <div className="bg-white rounded-lg shadow-md border border-gray-200 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Service</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Client</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Progress</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Duration</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Results</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {filteredLogs.map((log) => (
                <tr key={log.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4">
                    <div className="flex items-center">
                      <div className={`w-3 h-3 rounded-full mr-3 ${getPriorityColor(log.priority)}`}></div>
                      <div>
                        <div className="text-sm font-medium text-gray-900">{log.serviceName}</div>
                        <div className="text-sm text-gray-500">{log.serviceCategory}</div>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="text-sm text-gray-900">{log.clientName}</div>
                    <div className="text-sm text-gray-500">{log.automated ? 'Automated' : 'Manual'}</div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center">
                      {getStatusIcon(log.status)}
                      <span className={`ml-2 px-2 py-1 text-xs font-medium rounded-full border ${getStatusColor(log.status)}`}>
                        {log.status}
                      </span>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div 
                        className={`h-2 rounded-full ${
                          log.status === 'completed' ? 'bg-green-500' :
                          log.status === 'failed' ? 'bg-red-500' :
                          log.status === 'running' ? 'bg-blue-500' : 'bg-gray-400'
                        }`}
                        style={{ width: `${log.progress}%` }}
                      ></div>
                    </div>
                    <div className="text-xs text-gray-500 mt-1">{log.progress}%</div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="text-sm text-gray-900">
                      {log.duration ? formatDuration(log.duration) : 'In Progress'}
                    </div>
                    <div className="text-sm text-gray-500">
                      {new Date(log.startTime).toLocaleTimeString()}
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    {log.results && Object.keys(log.results).length > 0 ? (
                      <div className="text-sm">
                        {Object.entries(log.results).map(([key, value]) => (
                          <div key={key} className="text-gray-600">
                            {key}: <span className="font-medium text-gray-900">{value}</span>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <span className="text-sm text-gray-500">No results yet</span>
                    )}
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center space-x-2">
                      <button 
                        onClick={() => setSelectedLog(log)}
                        className="text-florida-blue-600 hover:text-florida-blue-700"
                      >
                        <Eye className="w-4 h-4" />
                      </button>
                      <button className="text-gray-400 hover:text-gray-600">
                        <ExternalLink className="w-4 h-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Detailed Log Modal */}
      {selectedLog && (
        <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-lg max-w-4xl w-full max-h-[90vh] overflow-hidden">
            <div className="flex items-center justify-between p-6 border-b border-gray-200">
              <div>
                <h3 className="text-lg font-semibold text-gray-900">{selectedLog.serviceName} - Execution Details</h3>
                <p className="text-sm text-gray-600">{selectedLog.clientName}</p>
              </div>
              <button 
                onClick={() => setSelectedLog(null)}
                className="text-gray-400 hover:text-gray-600"
              >
                ✕
              </button>
            </div>
            
            <div className="p-6 overflow-y-auto max-h-[70vh]">
              <div className="grid grid-cols-2 gap-6 mb-6">
                <div>
                  <h4 className="text-sm font-medium text-gray-900 mb-2">Execution Info</h4>
                  <div className="space-y-2 text-sm">
                    <div>Status: <span className={`px-2 py-1 rounded text-xs ${getStatusColor(selectedLog.status)}`}>{selectedLog.status}</span></div>
                    <div>Started: {new Date(selectedLog.startTime).toLocaleString()}</div>
                    {selectedLog.endTime && <div>Ended: {new Date(selectedLog.endTime).toLocaleString()}</div>}
                    <div>Duration: {selectedLog.duration ? formatDuration(selectedLog.duration) : 'In Progress'}</div>
                    <div>Executed By: {selectedLog.executedBy}</div>
                    <div>Priority: <span className={`px-2 py-1 rounded text-xs text-white ${getPriorityColor(selectedLog.priority)}`}>{selectedLog.priority}</span></div>
                  </div>
                </div>
                
                {selectedLog.results && (
                  <div>
                    <h4 className="text-sm font-medium text-gray-900 mb-2">Results</h4>
                    <div className="space-y-2 text-sm">
                      {Object.entries(selectedLog.results).map(([key, value]) => (
                        <div key={key}>{key}: <span className="font-medium">{value}</span></div>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              <div className="mb-6">
                <h4 className="text-sm font-medium text-gray-900 mb-2">Execution Log</h4>
                <div className="bg-gray-900 text-green-400 p-4 rounded-lg font-mono text-sm max-h-60 overflow-y-auto">
                  {selectedLog.logs.map((logLine, index) => (
                    <div key={index} className="mb-1">{logLine}</div>
                  ))}
                </div>
              </div>

              {selectedLog.errors && selectedLog.errors.length > 0 && (
                <div>
                  <h4 className="text-sm font-medium text-gray-900 mb-2">Errors</h4>
                  <div className="space-y-2">
                    {selectedLog.errors.map((error, index) => (
                      <div key={index} className="bg-red-50 border border-red-200 text-red-700 p-3 rounded text-sm">
                        {error}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default SEOExecutionLogs