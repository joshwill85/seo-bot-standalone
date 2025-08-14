import { TrendingUp, Search, FileText, Target, BarChart3, AlertCircle, CheckCircle, Clock, Globe, Users } from 'lucide-react'
import { mockCampaigns, mockSEOTasks, mockContentBriefs, mockKeywordClusters } from '@/data/mockData'

interface SEODashboardProps {
  businessId: string
  businessName: string
}

const MetricCard = ({ title, value, change, icon: Icon, suffix = '', status = 'neutral' }: {
  title: string
  value: string | number
  change?: number
  icon: any
  suffix?: string
  status?: 'positive' | 'negative' | 'neutral'
}) => {
  const getStatusColor = () => {
    switch (status) {
      case 'positive': return 'text-green-600'
      case 'negative': return 'text-red-600'
      default: return 'text-gray-600'
    }
  }

  return (
    <div className="bg-white rounded-lg shadow-md p-6 border border-gray-200">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-gray-600">{title}</p>
          <p className="text-2xl font-bold text-gray-900">
            {typeof value === 'number' ? value.toLocaleString() : value}{suffix}
          </p>
          {change !== undefined && (
            <div className={`flex items-center mt-1 text-sm ${getStatusColor()}`}>
              <span>{change > 0 ? '+' : ''}{change}%</span>
              <span className="ml-1 text-gray-500">vs last month</span>
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

const TaskStatusBadge = ({ status }: { status: string }) => {
  const getStatusStyle = () => {
    switch (status) {
      case 'completed': return 'bg-green-100 text-green-800'
      case 'running': return 'bg-blue-100 text-blue-800'
      case 'pending': return 'bg-yellow-100 text-yellow-800'
      case 'failed': return 'bg-red-100 text-red-800'
      default: return 'bg-gray-100 text-gray-800'
    }
  }

  const getStatusIcon = () => {
    switch (status) {
      case 'completed': return <CheckCircle className="w-3 h-3" />
      case 'running': return <Clock className="w-3 h-3" />
      case 'pending': return <AlertCircle className="w-3 h-3" />
      default: return null
    }
  }

  return (
    <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${getStatusStyle()}`}>
      {getStatusIcon()}
      <span className="ml-1">{status.charAt(0).toUpperCase() + status.slice(1)}</span>
    </span>
  )
}

export default function SEODashboard({ businessId, businessName }: SEODashboardProps) {
  // Get SEO project data for this business
  const campaigns = mockCampaigns.filter(c => c.business_id === businessId)
  const mainProject = campaigns[0]
  
  // Get related data
  const tasks = mockSEOTasks.filter(t => t.business_id === businessId)
  const contentBriefs = mockContentBriefs.filter(b => 
    campaigns.some(c => c.id === b.campaign_id)
  )
  const clusters = mockKeywordClusters.filter(c => 
    campaigns.some(campaign => campaign.id === c.campaign_id)
  )

  if (!mainProject) {
    return (
      <div className="bg-white rounded-lg shadow-md p-8 text-center">
        <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
          <Search className="w-8 h-8 text-gray-400" />
        </div>
        <h3 className="text-lg font-semibold text-gray-900 mb-2">SEO Services Starting Soon</h3>
        <p className="text-gray-600 mb-4">
          Your SEO automation services for {businessName} are being set up.
        </p>
        <button className="px-4 py-2 bg-florida-blue-600 text-white rounded-md hover:bg-florida-blue-700 transition-colors">
          Contact Support
        </button>
      </div>
    )
  }

  const completedTasks = tasks.filter(t => t.status === 'completed').length
  const runningTasks = tasks.filter(t => t.status === 'running').length
  const pendingTasks = tasks.filter(t => t.status === 'pending').length

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white rounded-lg shadow-md p-6 border border-gray-200">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">SEO Performance Overview</h1>
            <p className="text-gray-600 mt-1">Real-time insights and automated task tracking for {businessName}</p>
          </div>
          <div className="text-right">
            <div className="text-sm text-gray-500">SEO Services Status</div>
            <div className="text-lg font-semibold text-green-600 capitalize">{mainProject.status}</div>
          </div>
        </div>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <MetricCard
          title="Total Keywords"
          value={mainProject.total_keywords}
          change={15.2}
          icon={Search}
          status="positive"
        />
        <MetricCard
          title="Avg Difficulty"
          value={mainProject.avg_keyword_difficulty.toFixed(1)}
          change={-5.3}
          icon={Target}
          suffix="/100"
          status="positive"
        />
        <MetricCard
          title="Content Pieces"
          value={`${mainProject.content_pieces_published}/${mainProject.content_pieces_planned}`}
          icon={FileText}
        />
        <MetricCard
          title="Monthly Traffic"
          value={mainProject.estimated_monthly_traffic}
          change={23.1}
          icon={Globe}
          status="positive"
        />
      </div>

      {/* SEO Progress & Tasks */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* SEO Progress */}
        <div className="bg-white rounded-lg shadow-md p-6 border border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">SEO Progress</h2>
          
          <div className="space-y-4">
            {/* Content Progress */}
            <div>
              <div className="flex justify-between text-sm mb-1">
                <span className="text-gray-600">Content Published</span>
                <span className="font-medium">{mainProject.content_pieces_published}/{mainProject.content_pieces_planned}</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div 
                  className="bg-florida-green-600 h-2 rounded-full" 
                  style={{ width: `${(mainProject.content_pieces_published / mainProject.content_pieces_planned) * 100}%` }}
                ></div>
              </div>
            </div>

            {/* Task Summary */}
            <div className="grid grid-cols-3 gap-4 pt-4 border-t border-gray-200">
              <div className="text-center">
                <div className="text-2xl font-bold text-green-600">{completedTasks}</div>
                <div className="text-xs text-gray-500">Completed</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-blue-600">{runningTasks}</div>
                <div className="text-xs text-gray-500">Running</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-yellow-600">{pendingTasks}</div>
                <div className="text-xs text-gray-500">Pending</div>
              </div>
            </div>
          </div>
        </div>

        {/* Recent SEO Tasks */}
        <div className="bg-white rounded-lg shadow-md p-6 border border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Recent Automated Tasks</h2>
          
          <div className="space-y-3">
            {tasks.slice(0, 4).map((task) => (
              <div key={task.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                <div className="flex-1">
                  <div className="text-sm font-medium text-gray-900">{task.task_name}</div>
                  <div className="text-xs text-gray-500 capitalize">{task.task_type.replace('_', ' ')}</div>
                </div>
                <div className="flex items-center space-x-2">
                  <div className="text-xs text-gray-500">Priority: {task.priority}</div>
                  <TaskStatusBadge status={task.status} />
                </div>
              </div>
            ))}
            
            {tasks.length === 0 && (
              <div className="text-center py-4 text-gray-500">
                <Clock className="w-8 h-8 mx-auto mb-2 text-gray-400" />
                <p className="text-sm">No SEO tasks yet</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Content Briefs & Keyword Clusters */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Content Briefs */}
        <div className="bg-white rounded-lg shadow-md p-6 border border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Content Briefs</h2>
          
          <div className="space-y-3">
            {contentBriefs.slice(0, 3).map((brief) => (
              <div key={brief.id} className="p-4 border border-gray-200 rounded-lg">
                <div className="flex items-start justify-between mb-2">
                  <h3 className="text-sm font-medium text-gray-900 line-clamp-2">{brief.title}</h3>
                  <TaskStatusBadge status={brief.status} />
                </div>
                <div className="text-xs text-gray-600 mb-2">
                  Target: <span className="font-medium">{brief.target_keyword}</span>
                </div>
                <div className="text-xs text-gray-500">
                  {brief.word_count_target.toLocaleString()} words • {brief.content_type}
                </div>
              </div>
            ))}
            
            {contentBriefs.length === 0 && (
              <div className="text-center py-4 text-gray-500">
                <FileText className="w-8 h-8 mx-auto mb-2 text-gray-400" />
                <p className="text-sm">No content briefs created yet</p>
              </div>
            )}
          </div>
        </div>

        {/* Keyword Clusters */}
        <div className="bg-white rounded-lg shadow-md p-6 border border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Keyword Clusters</h2>
          
          <div className="space-y-3">
            {clusters.slice(0, 3).map((cluster) => (
              <div key={cluster.id} className="p-4 border border-gray-200 rounded-lg">
                <div className="flex items-start justify-between mb-2">
                  <h3 className="text-sm font-medium text-gray-900">{cluster.name}</h3>
                  <span className="text-xs px-2 py-1 bg-purple-100 text-purple-800 rounded-full">
                    {cluster.cluster_type}
                  </span>
                </div>
                <div className="grid grid-cols-2 gap-2 text-xs text-gray-600">
                  <div>Keywords: <span className="font-medium">{cluster.total_keywords}</span></div>
                  <div>Priority: <span className="font-medium">{cluster.priority_score}/10</span></div>
                  <div>Volume: <span className="font-medium">{cluster.avg_search_volume.toLocaleString()}</span></div>
                  <div>Difficulty: <span className="font-medium">{cluster.avg_difficulty.toFixed(1)}</span></div>
                </div>
              </div>
            ))}
            
            {clusters.length === 0 && (
              <div className="text-center py-4 text-gray-500">
                <BarChart3 className="w-8 h-8 mx-auto mb-2 text-gray-400" />
                <p className="text-sm">No keyword clusters created yet</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* SEO Project Details */}
      <div className="bg-white rounded-lg shadow-md p-6 border border-gray-200">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">SEO Project Details</h2>
        
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          <div>
            <h3 className="text-sm font-medium text-gray-700 mb-2">Target Keywords</h3>
            <div className="space-y-1">
              {mainProject.seed_keywords.map((keyword, index) => (
                <span key={index} className="inline-block px-2 py-1 text-xs bg-florida-blue-100 text-florida-blue-800 rounded-full mr-1 mb-1">
                  {keyword}
                </span>
              ))}
            </div>
          </div>
          
          <div>
            <h3 className="text-sm font-medium text-gray-700 mb-2">Competitors</h3>
            <div className="space-y-1">
              {mainProject.competitors?.map((competitor, index) => (
                <div key={index} className="text-xs text-gray-600 truncate">
                  {competitor}
                </div>
              )) || <div className="text-xs text-gray-500">No competitors tracked</div>}
            </div>
          </div>
          
          <div>
            <h3 className="text-sm font-medium text-gray-700 mb-2">Project Info</h3>
            <div className="space-y-1 text-xs text-gray-600">
              <div>Started: {new Date(mainProject.created_at).toLocaleDateString()}</div>
              <div>Status: <span className="capitalize">{mainProject.status}</span></div>
              <div>Total Keywords: {mainProject.total_keywords}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}