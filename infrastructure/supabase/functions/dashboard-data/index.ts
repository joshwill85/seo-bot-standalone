import { serve } from 'https://deno.land/std@0.168.0/http/server.ts'
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'
import { corsHeaders } from '../_shared/cors.ts'

interface DashboardRequest {
  business_id: string
  action: 'overview' | 'metrics' | 'charts' | 'activity' | 'performance'
  date_range?: {
    start_date: string
    end_date: string
  }
  campaign_id?: string
  refresh?: boolean
}

interface DashboardOverview {
  business_info: {
    name: string
    website: string
    industry: string
    created_date: string
  }
  quick_stats: {
    total_keywords: number
    avg_position: number
    total_traffic: number
    conversion_rate: number
    seo_score: number
    content_pieces: number
  }
  trends: {
    traffic_trend: number // percentage change
    ranking_trend: number
    conversion_trend: number
  }
  alerts: {
    critical: number
    high: number
    medium: number
    low: number
  }
  recent_activity: any[]
  top_opportunities: any[]
}

interface MetricsDashboard {
  rankings: {
    top_10: number
    top_20: number
    top_50: number
    not_ranking: number
    average_position: number
    position_changes: {
      improved: number
      declined: number
      stable: number
    }
  }
  traffic: {
    total_sessions: number
    organic_traffic: number
    direct_traffic: number
    referral_traffic: number
    social_traffic: number
    bounce_rate: number
    avg_session_duration: number
    pages_per_session: number
  }
  conversions: {
    total_conversions: number
    conversion_rate: number
    goal_completions: any[]
    revenue_estimate: number
  }
  technical: {
    seo_score: number
    performance_score: number
    mobile_score: number
    security_score: number
    critical_issues: number
    warnings: number
  }
  content: {
    total_pages: number
    optimized_pages: number
    blog_posts: number
    avg_word_count: number
    content_score: number
    fresh_content: number // published in last 30 days
  }
  competitors: {
    tracked_competitors: number
    competitive_position: number
    market_share: number
    gaps_identified: number
  }
}

interface ChartData {
  traffic_timeline: {
    labels: string[]
    datasets: {
      label: string
      data: number[]
      color?: string
    }[]
  }
  keyword_distribution: {
    labels: string[]
    data: number[]
  }
  top_pages: {
    page: string
    traffic: number
    conversions: number
    bounce_rate: number
  }[]
  competitive_analysis: {
    competitor: string
    metrics: {
      domain_authority: number
      organic_traffic: number
      keywords: number
    }
  }[]
}

serve(async (req) => {
  // Handle CORS preflight requests
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders })
  }

  try {
    const supabase = createClient(
      Deno.env.get('SUPABASE_URL') ?? '',
      Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') ?? ''
    )

    const {
      business_id,
      action,
      date_range,
      campaign_id,
      refresh = false
    }: DashboardRequest = await req.json()

    // Validate required fields
    if (!business_id || !action) {
      return new Response(
        JSON.stringify({ error: 'business_id and action are required' }),
        { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    // Get business details
    const { data: business } = await supabase
      .from('businesses')
      .select('*')
      .eq('id', business_id)
      .single()

    if (!business) {
      return new Response(
        JSON.stringify({ error: 'Business not found' }),
        { status: 404, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    // Check cache unless refresh requested
    if (!refresh) {
      const cached = await getCachedDashboard(supabase, business_id, action)
      if (cached) {
        return new Response(
          JSON.stringify({
            success: true,
            data: cached,
            cached: true,
            timestamp: new Date().toISOString()
          }),
          { 
            status: 200, 
            headers: { ...corsHeaders, 'Content-Type': 'application/json' } 
          }
        )
      }
    }

    // Calculate date range if not provided
    const dateRange = date_range || {
      start_date: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
      end_date: new Date().toISOString().split('T')[0]
    }

    let dashboardData: any

    switch (action) {
      case 'overview':
        dashboardData = await generateOverviewDashboard(
          supabase,
          business,
          dateRange,
          campaign_id
        )
        break
      case 'metrics':
        dashboardData = await generateMetricsDashboard(
          supabase,
          business_id,
          dateRange,
          campaign_id
        )
        break
      case 'charts':
        dashboardData = await generateChartData(
          supabase,
          business_id,
          dateRange,
          campaign_id
        )
        break
      case 'activity':
        dashboardData = await generateActivityFeed(
          supabase,
          business_id,
          50
        )
        break
      case 'performance':
        dashboardData = await generatePerformanceReport(
          supabase,
          business_id,
          dateRange,
          campaign_id
        )
        break
      default:
        return new Response(
          JSON.stringify({ error: 'Invalid action' }),
          { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
        )
    }

    // Cache the dashboard data
    await cacheDashboard(supabase, business_id, action, dashboardData)

    return new Response(
      JSON.stringify({
        success: true,
        data: dashboardData,
        cached: false,
        timestamp: new Date().toISOString()
      }),
      { 
        status: 200, 
        headers: { ...corsHeaders, 'Content-Type': 'application/json' } 
      }
    )

  } catch (error) {
    console.error('Dashboard data error:', error)
    return new Response(
      JSON.stringify({ error: 'Internal server error', details: error.message }),
      { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }
})

async function generateOverviewDashboard(
  supabase: any,
  business: any,
  dateRange: any,
  campaign_id?: string
): Promise<DashboardOverview> {
  
  // Fetch all necessary data in parallel
  const [
    keywords,
    rankings,
    traffic,
    technical,
    content,
    alerts,
    activities,
    predictions
  ] = await Promise.all([
    // Keywords
    supabase
      .from('keywords')
      .select('keyword, search_volume, difficulty')
      .eq('business_id', business.id)
      .limit(1000),
    
    // Recent rankings
    supabase
      .from('rank_tracking')
      .select('keyword, position, tracked_at')
      .eq('business_id', business.id)
      .gte('tracked_at', dateRange.start_date)
      .order('tracked_at', { ascending: false })
      .limit(500),
    
    // Traffic data
    supabase
      .from('ga_metrics')
      .select('sessions, users, goal_completions, conversion_rate')
      .eq('business_id', business.id)
      .gte('date', dateRange.start_date)
      .lte('date', dateRange.end_date),
    
    // Latest technical audit
    supabase
      .from('technical_audits')
      .select('seo_score, performance_score, critical_issues')
      .eq('business_id', business.id)
      .order('audit_date', { ascending: false })
      .limit(1)
      .single(),
    
    // Content count
    supabase
      .from('content_performance')
      .select('id')
      .eq('business_id', business.id),
    
    // Active alerts
    supabase
      .from('monitoring_alerts')
      .select('severity')
      .eq('business_id', business.id)
      .eq('status', 'active'),
    
    // Recent activities
    supabase
      .from('seo_logs')
      .select('action_type, action_description, created_at')
      .eq('business_id', business.id)
      .order('created_at', { ascending: false })
      .limit(10),
    
    // AI predictions for opportunities
    supabase
      .from('ai_predictions')
      .select('predictions')
      .eq('business_id', business.id)
      .eq('prediction_type', 'opportunity')
      .order('created_at', { ascending: false })
      .limit(1)
      .single()
  ])

  // Calculate metrics
  const totalKeywords = keywords.data?.length || 0
  const avgPosition = calculateAveragePosition(rankings.data)
  const totalTraffic = traffic.data?.reduce((sum: number, day: any) => sum + (day.sessions || 0), 0) || 0
  const totalConversions = traffic.data?.reduce((sum: number, day: any) => sum + (day.goal_completions || 0), 0) || 0
  const conversionRate = totalTraffic > 0 ? (totalConversions / totalTraffic) * 100 : 0

  // Calculate trends
  const trends = calculateTrends(rankings.data, traffic.data, dateRange)

  // Count alerts by severity
  const alertCounts = {
    critical: alerts.data?.filter((a: any) => a.severity === 'critical').length || 0,
    high: alerts.data?.filter((a: any) => a.severity === 'high').length || 0,
    medium: alerts.data?.filter((a: any) => a.severity === 'medium').length || 0,
    low: alerts.data?.filter((a: any) => a.severity === 'low').length || 0
  }

  // Extract top opportunities
  const topOpportunities = predictions.data?.predictions?.slice(0, 5) || []

  return {
    business_info: {
      name: business.business_name,
      website: business.website_url,
      industry: business.industry,
      created_date: business.created_at
    },
    quick_stats: {
      total_keywords: totalKeywords,
      avg_position: avgPosition,
      total_traffic: totalTraffic,
      conversion_rate: conversionRate,
      seo_score: technical.data?.seo_score || 0,
      content_pieces: content.data?.length || 0
    },
    trends,
    alerts: alertCounts,
    recent_activity: activities.data || [],
    top_opportunities: topOpportunities
  }
}

async function generateMetricsDashboard(
  supabase: any,
  business_id: string,
  dateRange: any,
  campaign_id?: string
): Promise<MetricsDashboard> {
  
  // Fetch comprehensive metrics data
  const [
    rankingData,
    trafficData,
    conversionData,
    technicalData,
    contentData,
    competitorData
  ] = await Promise.all([
    // Rankings data
    getRankingsMetrics(supabase, business_id, dateRange, campaign_id),
    // Traffic data
    getTrafficMetrics(supabase, business_id, dateRange),
    // Conversion data
    getConversionMetrics(supabase, business_id, dateRange),
    // Technical data
    getTechnicalMetrics(supabase, business_id),
    // Content data
    getContentMetrics(supabase, business_id, dateRange),
    // Competitor data
    getCompetitorMetrics(supabase, business_id)
  ])

  return {
    rankings: rankingData,
    traffic: trafficData,
    conversions: conversionData,
    technical: technicalData,
    content: contentData,
    competitors: competitorData
  }
}

async function generateChartData(
  supabase: any,
  business_id: string,
  dateRange: any,
  campaign_id?: string
): Promise<ChartData> {
  
  // Get traffic timeline
  const { data: trafficData } = await supabase
    .from('ga_metrics')
    .select('date, sessions, organic_traffic, users')
    .eq('business_id', business_id)
    .gte('date', dateRange.start_date)
    .lte('date', dateRange.end_date)
    .order('date')

  // Get keyword distribution
  const { data: keywordData } = await supabase
    .from('rank_tracking')
    .select('position')
    .eq('business_id', business_id)
    .gte('tracked_at', dateRange.start_date)

  // Get top pages
  const { data: pageData } = await supabase
    .from('ga_page_data')
    .select('page_path, page_views, goal_completions, bounce_rate')
    .eq('business_id', business_id)
    .order('page_views', { ascending: false })
    .limit(10)

  // Get competitor comparison
  const { data: competitorAnalysis } = await supabase
    .from('competitor_analysis')
    .select('domain_authority_data, traffic_data')
    .eq('business_id', business_id)
    .order('analysis_date', { ascending: false })
    .limit(1)
    .single()

  // Format traffic timeline
  const trafficTimeline = {
    labels: trafficData?.map(d => d.date) || [],
    datasets: [
      {
        label: 'Total Sessions',
        data: trafficData?.map(d => d.sessions) || [],
        color: '#3B82F6'
      },
      {
        label: 'Organic Traffic',
        data: trafficData?.map(d => d.organic_traffic) || [],
        color: '#10B981'
      },
      {
        label: 'Users',
        data: trafficData?.map(d => d.users) || [],
        color: '#F59E0B'
      }
    ]
  }

  // Calculate keyword distribution
  const distribution = calculateKeywordDistribution(keywordData)

  // Format top pages
  const topPages = pageData?.map(page => ({
    page: page.page_path,
    traffic: page.page_views,
    conversions: page.goal_completions || 0,
    bounce_rate: page.bounce_rate
  })) || []

  // Format competitive analysis
  const competitiveAnalysis = competitorAnalysis?.domain_authority_data?.map((comp: any) => ({
    competitor: comp.domain,
    metrics: {
      domain_authority: comp.authority,
      organic_traffic: competitorAnalysis.traffic_data?.find((t: any) => 
        t.domain === comp.domain
      )?.traffic || 0,
      keywords: comp.keywords || 0
    }
  })) || []

  return {
    traffic_timeline: trafficTimeline,
    keyword_distribution: distribution,
    top_pages: topPages,
    competitive_analysis: competitiveAnalysis
  }
}

async function generateActivityFeed(
  supabase: any,
  business_id: string,
  limit: number = 50
): Promise<any[]> {
  
  // Get recent activities from multiple sources
  const [logs, alerts, tasks, reports] = await Promise.all([
    // SEO logs
    supabase
      .from('seo_logs')
      .select('*')
      .eq('business_id', business_id)
      .order('created_at', { ascending: false })
      .limit(limit),
    
    // Recent alerts
    supabase
      .from('monitoring_alerts')
      .select('*')
      .eq('business_id', business_id)
      .order('created_at', { ascending: false })
      .limit(20),
    
    // Task executions
    supabase
      .from('seo_tasks')
      .select('*')
      .eq('business_id', business_id)
      .in('status', ['completed', 'failed'])
      .order('completed_at', { ascending: false })
      .limit(20),
    
    // Generated reports
    supabase
      .from('seo_reports')
      .select('id, report_type, generated_at')
      .eq('business_id', business_id)
      .order('generated_at', { ascending: false })
      .limit(10)
  ])

  // Combine and format activities
  const activities = []

  // Add logs
  for (const log of logs.data || []) {
    activities.push({
      type: 'log',
      category: log.action_type,
      title: log.action_description,
      timestamp: log.created_at,
      data: log.new_data,
      icon: getActivityIcon(log.action_type)
    })
  }

  // Add alerts
  for (const alert of alerts.data || []) {
    activities.push({
      type: 'alert',
      category: alert.alert_type,
      title: alert.title,
      message: alert.message,
      severity: alert.severity,
      timestamp: alert.created_at,
      icon: 'alert'
    })
  }

  // Add task completions
  for (const task of tasks.data || []) {
    activities.push({
      type: 'task',
      category: task.task_type,
      title: `Task ${task.status}: ${task.task_name}`,
      status: task.status,
      timestamp: task.completed_at || task.created_at,
      icon: task.status === 'completed' ? 'check' : 'x'
    })
  }

  // Add reports
  for (const report of reports.data || []) {
    activities.push({
      type: 'report',
      category: 'report',
      title: `${report.report_type} report generated`,
      timestamp: report.generated_at,
      report_id: report.id,
      icon: 'document'
    })
  }

  // Sort by timestamp
  activities.sort((a, b) => 
    new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
  )

  return activities.slice(0, limit)
}

async function generatePerformanceReport(
  supabase: any,
  business_id: string,
  dateRange: any,
  campaign_id?: string
): Promise<any> {
  
  // Get performance metrics
  const [current, previous] = await Promise.all([
    getPerformanceMetrics(supabase, business_id, dateRange, campaign_id),
    getPerformanceMetrics(supabase, business_id, getPreviousPeriod(dateRange), campaign_id)
  ])

  // Calculate changes
  const changes = calculatePerformanceChanges(current, previous)

  // Get top performers and underperformers
  const [topKeywords, topContent, issues] = await Promise.all([
    getTopPerformingKeywords(supabase, business_id, dateRange, 10),
    getTopPerformingContent(supabase, business_id, dateRange, 10),
    getPerformanceIssues(supabase, business_id)
  ])

  return {
    current_period: current,
    previous_period: previous,
    changes,
    top_keywords: topKeywords,
    top_content: topContent,
    issues,
    summary: generatePerformanceSummary(current, changes),
    recommendations: generatePerformanceRecommendations(current, changes, issues)
  }
}

// Helper functions

function calculateAveragePosition(rankings: any[]): number {
  if (!rankings || rankings.length === 0) return 0
  
  const positions = rankings.map(r => r.position).filter(p => p > 0)
  if (positions.length === 0) return 0
  
  return Math.round(positions.reduce((sum, pos) => sum + pos, 0) / positions.length * 10) / 10
}

function calculateTrends(rankings: any[], traffic: any[], dateRange: any): any {
  // Calculate midpoint of date range
  const midDate = new Date(
    new Date(dateRange.start_date).getTime() + 
    (new Date(dateRange.end_date).getTime() - new Date(dateRange.start_date).getTime()) / 2
  )

  // Traffic trend
  let trafficTrend = 0
  if (traffic && traffic.length > 1) {
    const firstHalf = traffic.filter(t => new Date(t.date) < midDate)
    const secondHalf = traffic.filter(t => new Date(t.date) >= midDate)
    
    const firstHalfAvg = firstHalf.reduce((sum, t) => sum + (t.sessions || 0), 0) / (firstHalf.length || 1)
    const secondHalfAvg = secondHalf.reduce((sum, t) => sum + (t.sessions || 0), 0) / (secondHalf.length || 1)
    
    trafficTrend = firstHalfAvg > 0 ? ((secondHalfAvg - firstHalfAvg) / firstHalfAvg) * 100 : 0
  }

  // Ranking trend (lower is better, so invert)
  let rankingTrend = 0
  if (rankings && rankings.length > 1) {
    const firstHalf = rankings.filter(r => new Date(r.tracked_at) < midDate)
    const secondHalf = rankings.filter(r => new Date(r.tracked_at) >= midDate)
    
    const firstHalfAvg = calculateAveragePosition(firstHalf)
    const secondHalfAvg = calculateAveragePosition(secondHalf)
    
    rankingTrend = firstHalfAvg > 0 ? ((firstHalfAvg - secondHalfAvg) / firstHalfAvg) * 100 : 0
  }

  // Conversion trend
  let conversionTrend = 0
  if (traffic && traffic.length > 1) {
    const firstHalf = traffic.filter(t => new Date(t.date) < midDate)
    const secondHalf = traffic.filter(t => new Date(t.date) >= midDate)
    
    const firstHalfConv = firstHalf.reduce((sum, t) => sum + (t.conversion_rate || 0), 0) / (firstHalf.length || 1)
    const secondHalfConv = secondHalf.reduce((sum, t) => sum + (t.conversion_rate || 0), 0) / (secondHalf.length || 1)
    
    conversionTrend = firstHalfConv > 0 ? ((secondHalfConv - firstHalfConv) / firstHalfConv) * 100 : 0
  }

  return {
    traffic_trend: Math.round(trafficTrend * 10) / 10,
    ranking_trend: Math.round(rankingTrend * 10) / 10,
    conversion_trend: Math.round(conversionTrend * 10) / 10
  }
}

async function getRankingsMetrics(supabase: any, business_id: string, dateRange: any, campaign_id?: string): Promise<any> {
  // Get latest rankings
  const { data: rankings } = await supabase
    .from('rank_tracking')
    .select('keyword, position')
    .eq('business_id', business_id)
    .gte('tracked_at', dateRange.start_date)
    .order('tracked_at', { ascending: false })

  // Group by position ranges
  const top10 = rankings?.filter(r => r.position > 0 && r.position <= 10).length || 0
  const top20 = rankings?.filter(r => r.position > 10 && r.position <= 20).length || 0
  const top50 = rankings?.filter(r => r.position > 20 && r.position <= 50).length || 0
  const notRanking = rankings?.filter(r => r.position > 50 || r.position === 0).length || 0

  // Get position changes
  const changes = await calculatePositionChanges(supabase, business_id, dateRange)

  return {
    top_10: top10,
    top_20: top20,
    top_50: top50,
    not_ranking: notRanking,
    average_position: calculateAveragePosition(rankings),
    position_changes: changes
  }
}

async function getTrafficMetrics(supabase: any, business_id: string, dateRange: any): Promise<any> {
  const { data: metrics } = await supabase
    .from('ga_metrics')
    .select('*')
    .eq('business_id', business_id)
    .gte('date', dateRange.start_date)
    .lte('date', dateRange.end_date)

  const { data: sources } = await supabase
    .from('ga_traffic_sources')
    .select('*')
    .eq('business_id', business_id)

  if (!metrics || metrics.length === 0) {
    return {
      total_sessions: 0,
      organic_traffic: 0,
      direct_traffic: 0,
      referral_traffic: 0,
      social_traffic: 0,
      bounce_rate: 0,
      avg_session_duration: 0,
      pages_per_session: 0
    }
  }

  // Aggregate metrics
  const totals = metrics.reduce((acc, day) => ({
    sessions: acc.sessions + (day.sessions || 0),
    organic: acc.organic + (day.organic_traffic || 0),
    bounce: acc.bounce + (day.bounce_rate || 0),
    duration: acc.duration + (day.avg_session_duration || 0),
    pages: acc.pages + (day.pages_per_session || 0)
  }), { sessions: 0, organic: 0, bounce: 0, duration: 0, pages: 0 })

  // Traffic sources
  const sourceData = sources?.reduce((acc, source) => {
    if (source.medium === '(none)') acc.direct += source.sessions
    else if (source.medium === 'organic') acc.organic += source.sessions
    else if (source.medium === 'referral') acc.referral += source.sessions
    else if (source.medium === 'social') acc.social += source.sessions
    return acc
  }, { direct: 0, organic: 0, referral: 0, social: 0 }) || { direct: 0, organic: 0, referral: 0, social: 0 }

  return {
    total_sessions: totals.sessions,
    organic_traffic: totals.organic,
    direct_traffic: sourceData.direct,
    referral_traffic: sourceData.referral,
    social_traffic: sourceData.social,
    bounce_rate: metrics.length > 0 ? totals.bounce / metrics.length : 0,
    avg_session_duration: metrics.length > 0 ? totals.duration / metrics.length : 0,
    pages_per_session: metrics.length > 0 ? totals.pages / metrics.length : 0
  }
}

async function getConversionMetrics(supabase: any, business_id: string, dateRange: any): Promise<any> {
  const { data: metrics } = await supabase
    .from('ga_metrics')
    .select('goal_completions, conversion_rate, sessions')
    .eq('business_id', business_id)
    .gte('date', dateRange.start_date)
    .lte('date', dateRange.end_date)

  const { data: goals } = await supabase
    .from('ga_goals')
    .select('*')
    .eq('business_id', business_id)
    .eq('is_active', true)

  const totalConversions = metrics?.reduce((sum, m) => sum + (m.goal_completions || 0), 0) || 0
  const totalSessions = metrics?.reduce((sum, m) => sum + (m.sessions || 0), 0) || 0
  const conversionRate = totalSessions > 0 ? (totalConversions / totalSessions) * 100 : 0

  // Estimate revenue (simplified)
  const revenuePerConversion = 100 // Default value
  const revenueEstimate = totalConversions * revenuePerConversion

  return {
    total_conversions: totalConversions,
    conversion_rate: Math.round(conversionRate * 100) / 100,
    goal_completions: goals || [],
    revenue_estimate: revenueEstimate
  }
}

async function getTechnicalMetrics(supabase: any, business_id: string): Promise<any> {
  const { data: audit } = await supabase
    .from('technical_audits')
    .select('*')
    .eq('business_id', business_id)
    .order('audit_date', { ascending: false })
    .limit(1)
    .single()

  if (!audit) {
    return {
      seo_score: 0,
      performance_score: 0,
      mobile_score: 0,
      security_score: 0,
      critical_issues: 0,
      warnings: 0
    }
  }

  return {
    seo_score: audit.seo_score || 0,
    performance_score: audit.performance_score || 0,
    mobile_score: audit.mobile_score || 0,
    security_score: audit.security_score || 0,
    critical_issues: audit.critical_issues || 0,
    warnings: audit.warnings || 0
  }
}

async function getContentMetrics(supabase: any, business_id: string, dateRange: any): Promise<any> {
  const { data: content } = await supabase
    .from('content_performance')
    .select('*')
    .eq('business_id', business_id)

  const thirtyDaysAgo = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000)
  const freshContent = content?.filter(c => new Date(c.analysis_date) > thirtyDaysAgo).length || 0

  const totalPages = content?.length || 0
  const optimizedPages = content?.filter(c => c.seo_score > 70).length || 0
  const blogPosts = content?.filter(c => c.url?.includes('/blog')).length || 0
  const avgWordCount = totalPages > 0 ? 
    content.reduce((sum, c) => sum + (c.word_count || 0), 0) / totalPages : 0
  const avgContentScore = totalPages > 0 ?
    content.reduce((sum, c) => sum + (c.seo_score || 0), 0) / totalPages : 0

  return {
    total_pages: totalPages,
    optimized_pages: optimizedPages,
    blog_posts: blogPosts,
    avg_word_count: Math.round(avgWordCount),
    content_score: Math.round(avgContentScore),
    fresh_content: freshContent
  }
}

async function getCompetitorMetrics(supabase: any, business_id: string): Promise<any> {
  const { data: analysis } = await supabase
    .from('competitor_analysis')
    .select('*')
    .eq('business_id', business_id)
    .order('analysis_date', { ascending: false })
    .limit(1)
    .single()

  if (!analysis) {
    return {
      tracked_competitors: 0,
      competitive_position: 0,
      market_share: 0,
      gaps_identified: 0
    }
  }

  const competitorsCount = analysis.competitors_analyzed?.length || 0
  const gaps = analysis.competitive_gaps?.length || 0

  // Calculate competitive position (simplified)
  const position = analysis.domain_authority_data?.findIndex((d: any) => 
    d.domain?.includes('business')
  ) + 1 || 0

  // Calculate market share (simplified)
  const marketShare = 100 / (competitorsCount + 1)

  return {
    tracked_competitors: competitorsCount,
    competitive_position: position,
    market_share: Math.round(marketShare),
    gaps_identified: gaps
  }
}

function calculateKeywordDistribution(keywordData: any): any {
  const ranges = {
    '1-3': 0,
    '4-10': 0,
    '11-20': 0,
    '21-50': 0,
    '51-100': 0,
    '100+': 0
  }

  for (const item of keywordData || []) {
    const pos = item.position
    if (pos >= 1 && pos <= 3) ranges['1-3']++
    else if (pos <= 10) ranges['4-10']++
    else if (pos <= 20) ranges['11-20']++
    else if (pos <= 50) ranges['21-50']++
    else if (pos <= 100) ranges['51-100']++
    else ranges['100+']++
  }

  return {
    labels: Object.keys(ranges),
    data: Object.values(ranges)
  }
}

function getActivityIcon(actionType: string): string {
  const iconMap: { [key: string]: string } = {
    keyword_discovery: 'search',
    content_optimization: 'document',
    rank_tracking: 'trending-up',
    technical_audit: 'settings',
    competitor_analysis: 'users',
    report_generated: 'chart',
    alert_triggered: 'bell'
  }
  
  return iconMap[actionType] || 'activity'
}

async function calculatePositionChanges(supabase: any, business_id: string, dateRange: any): Promise<any> {
  // Get rankings from start and end of period
  const { data: startRankings } = await supabase
    .from('rank_tracking')
    .select('keyword, position')
    .eq('business_id', business_id)
    .gte('tracked_at', dateRange.start_date)
    .lte('tracked_at', new Date(new Date(dateRange.start_date).getTime() + 3 * 24 * 60 * 60 * 1000).toISOString())

  const { data: endRankings } = await supabase
    .from('rank_tracking')
    .select('keyword, position')
    .eq('business_id', business_id)
    .gte('tracked_at', new Date(new Date(dateRange.end_date).getTime() - 3 * 24 * 60 * 60 * 1000).toISOString())
    .lte('tracked_at', dateRange.end_date)

  // Compare positions
  let improved = 0
  let declined = 0
  let stable = 0

  const startMap = new Map(startRankings?.map(r => [r.keyword, r.position]))
  
  for (const ranking of endRankings || []) {
    const startPos = startMap.get(ranking.keyword)
    if (startPos) {
      const change = startPos - ranking.position
      if (change > 2) improved++
      else if (change < -2) declined++
      else stable++
    }
  }

  return { improved, declined, stable }
}

function getPreviousPeriod(dateRange: any): any {
  const start = new Date(dateRange.start_date)
  const end = new Date(dateRange.end_date)
  const duration = end.getTime() - start.getTime()
  
  return {
    start_date: new Date(start.getTime() - duration).toISOString().split('T')[0],
    end_date: new Date(start.getTime() - 1).toISOString().split('T')[0]
  }
}

async function getPerformanceMetrics(supabase: any, business_id: string, dateRange: any, campaign_id?: string): Promise<any> {
  // Aggregate performance metrics for the period
  const [traffic, rankings, conversions] = await Promise.all([
    getTrafficMetrics(supabase, business_id, dateRange),
    getRankingsMetrics(supabase, business_id, dateRange, campaign_id),
    getConversionMetrics(supabase, business_id, dateRange)
  ])

  return {
    traffic,
    rankings,
    conversions
  }
}

function calculatePerformanceChanges(current: any, previous: any): any {
  const changes: any = {}

  // Traffic changes
  if (previous.traffic && current.traffic) {
    const prevSessions = previous.traffic.total_sessions || 1
    changes.traffic_change = ((current.traffic.total_sessions - prevSessions) / prevSessions) * 100
  }

  // Ranking changes
  if (previous.rankings && current.rankings) {
    const prevAvg = previous.rankings.average_position || 100
    const currAvg = current.rankings.average_position || 100
    changes.ranking_change = ((prevAvg - currAvg) / prevAvg) * 100 // Inverted because lower is better
  }

  // Conversion changes
  if (previous.conversions && current.conversions) {
    const prevRate = previous.conversions.conversion_rate || 0
    changes.conversion_change = current.conversions.conversion_rate - prevRate
  }

  return changes
}

async function getTopPerformingKeywords(supabase: any, business_id: string, dateRange: any, limit: number): Promise<any[]> {
  const { data } = await supabase
    .from('gsc_search_analytics')
    .select('query, clicks, impressions, position')
    .eq('business_id', business_id)
    .gte('date', dateRange.start_date)
    .lte('date', dateRange.end_date)
    .order('clicks', { ascending: false })
    .limit(limit)

  return data || []
}

async function getTopPerformingContent(supabase: any, business_id: string, dateRange: any, limit: number): Promise<any[]> {
  const { data } = await supabase
    .from('content_performance')
    .select('url, title, organic_traffic, engagement_rate')
    .eq('business_id', business_id)
    .gte('analysis_date', dateRange.start_date)
    .order('organic_traffic', { ascending: false })
    .limit(limit)

  return data || []
}

async function getPerformanceIssues(supabase: any, business_id: string): Promise<any[]> {
  const issues = []

  // Check for ranking drops
  const { data: alerts } = await supabase
    .from('monitoring_alerts')
    .select('*')
    .eq('business_id', business_id)
    .eq('status', 'active')
    .in('alert_type', ['ranking_drop', 'traffic_drop', 'performance_drop'])

  for (const alert of alerts || []) {
    issues.push({
      type: alert.alert_type,
      severity: alert.severity,
      description: alert.message,
      detected: alert.created_at
    })
  }

  return issues
}

function generatePerformanceSummary(metrics: any, changes: any): string {
  const parts = []

  if (changes.traffic_change > 10) {
    parts.push(`Traffic increased by ${Math.round(changes.traffic_change)}%`)
  } else if (changes.traffic_change < -10) {
    parts.push(`Traffic decreased by ${Math.abs(Math.round(changes.traffic_change))}%`)
  }

  if (changes.ranking_change > 5) {
    parts.push(`Rankings improved by ${Math.round(changes.ranking_change)}%`)
  } else if (changes.ranking_change < -5) {
    parts.push(`Rankings declined by ${Math.abs(Math.round(changes.ranking_change))}%`)
  }

  if (changes.conversion_change > 0.5) {
    parts.push(`Conversion rate up ${changes.conversion_change.toFixed(1)}%`)
  } else if (changes.conversion_change < -0.5) {
    parts.push(`Conversion rate down ${Math.abs(changes.conversion_change).toFixed(1)}%`)
  }

  return parts.length > 0 ? parts.join('. ') : 'Performance is stable across all metrics.'
}

function generatePerformanceRecommendations(metrics: any, changes: any, issues: any): string[] {
  const recommendations = []

  if (changes.traffic_change < -5) {
    recommendations.push('Focus on content optimization to recover traffic')
  }

  if (changes.ranking_change < -5) {
    recommendations.push('Review and strengthen keyword targeting strategy')
  }

  if (metrics.conversions?.conversion_rate < 2) {
    recommendations.push('Optimize landing pages for better conversion rates')
  }

  if (issues.length > 3) {
    recommendations.push('Address critical performance issues immediately')
  }

  return recommendations
}

async function getCachedDashboard(supabase: any, business_id: string, action: string): Promise<any> {
  const cacheKey = `dashboard_${business_id}_${action}`
  const fiveMinutesAgo = new Date(Date.now() - 5 * 60 * 1000).toISOString()

  const { data } = await supabase
    .from('dashboard_cache')
    .select('data')
    .eq('cache_key', cacheKey)
    .gte('created_at', fiveMinutesAgo)
    .single()

  return data?.data
}

async function cacheDashboard(supabase: any, business_id: string, action: string, data: any): Promise<void> {
  const cacheKey = `dashboard_${business_id}_${action}`

  try {
    await supabase
      .from('dashboard_cache')
      .upsert({
        cache_key: cacheKey,
        data: data,
        created_at: new Date().toISOString()
      }, {
        onConflict: 'cache_key'
      })
  } catch (error) {
    console.error('Failed to cache dashboard data:', error)
  }
}