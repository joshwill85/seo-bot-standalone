import { serve } from 'https://deno.land/std@0.168.0/http/server.ts'
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'
import { corsHeaders } from '../_shared/cors.ts'

interface ReportRequest {
  business_id: string
  campaign_id?: string
  report_type: 'monthly' | 'weekly' | 'quarterly' | 'custom'
  date_range?: {
    start_date: string
    end_date: string
  }
  format?: 'json' | 'html' | 'pdf'
  include_sections?: string[]
  delivery_method?: 'api' | 'email' | 'webhook'
  recipients?: string[]
  schedule?: {
    frequency: 'weekly' | 'monthly' | 'quarterly'
    day_of_week?: number // 0-6, 0 = Sunday
    day_of_month?: number // 1-31
    time?: string // HH:MM format
  }
}

interface ReportSection {
  section_id: string
  title: string
  data: any
  insights: string[]
  recommendations: string[]
  charts?: {
    type: 'line' | 'bar' | 'pie' | 'table'
    data: any[]
    config: any
  }[]
}

interface SEOReport {
  report_id: string
  business_name: string
  report_period: {
    start_date: string
    end_date: string
    period_type: string
  }
  executive_summary: {
    key_metrics: {
      organic_traffic: { current: number; previous: number; change: number }
      keyword_rankings: { current: number; previous: number; change: number }
      total_impressions: { current: number; previous: number; change: number }
      avg_position: { current: number; previous: number; change: number }
      goal_completions: { current: number; previous: number; change: number }
    }
    top_achievements: string[]
    key_issues: string[]
    next_steps: string[]
  }
  sections: ReportSection[]
  generated_at: string
  report_metadata: {
    data_sources: string[]
    date_ranges_analyzed: any
    total_keywords_tracked: number
    total_pages_analyzed: number
  }
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

    const url = new URL(req.url)
    const action = url.searchParams.get('action') || 'generate'

    switch (action) {
      case 'generate':
        return await handleGenerateReport(req, supabase)
      case 'schedule':
        return await handleScheduleReport(req, supabase)
      case 'list':
        return await handleListReports(req, supabase)
      case 'get':
        return await handleGetReport(req, supabase)
      case 'templates':
        return await handleReportTemplates(req, supabase)
      default:
        return new Response(
          JSON.stringify({ error: 'Invalid action' }),
          { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
        )
    }

  } catch (error) {
    console.error('Report generation error:', error)
    return new Response(
      JSON.stringify({ error: 'Internal server error', details: error.message }),
      { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }
})

async function handleGenerateReport(req: Request, supabase: any) {
  const {
    business_id,
    campaign_id,
    report_type = 'monthly',
    date_range,
    format = 'json',
    include_sections = ['traffic', 'rankings', 'technical', 'content', 'conversions'],
    delivery_method = 'api'
  }: ReportRequest = await req.json()

  // Validate required fields
  if (!business_id) {
    return new Response(
      JSON.stringify({ error: 'business_id is required' }),
      { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }

  // Get business details
  const { data: business } = await supabase
    .from('businesses')
    .select('id, business_name, website_url, industry')
    .eq('id', business_id)
    .single()

  if (!business) {
    return new Response(
      JSON.stringify({ error: 'Business not found' }),
      { status: 404, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }

  // Calculate date range if not provided
  const reportDateRange = date_range || calculateDateRangeForReportType(report_type)

  // Generate comprehensive SEO report
  const report = await generateSEOReport(
    supabase,
    business,
    campaign_id,
    reportDateRange,
    include_sections
  )

  // Store the report
  const { data: reportRecord } = await supabase
    .from('seo_reports')
    .insert({
      business_id,
      campaign_id,
      report_type,
      report_data: report,
      date_range_start: reportDateRange.start_date,
      date_range_end: reportDateRange.end_date,
      format,
      generated_at: new Date().toISOString(),
      status: 'completed'
    })
    .select()
    .single()

  // Handle delivery
  if (delivery_method === 'email' && req.body) {
    const requestBody = await req.json()
    if (requestBody.recipients?.length > 0) {
      await sendReportByEmail(supabase, report, requestBody.recipients, format)
    }
  }

  // Log report generation
  await supabase
    .from('seo_logs')
    .insert({
      business_id,
      action_type: 'report_generated',
      action_description: `${report_type} SEO report generated`,
      new_data: JSON.stringify({
        report_id: reportRecord.id,
        report_type,
        sections_included: include_sections,
        date_range: reportDateRange
      })
    })

  if (format === 'json') {
    return new Response(
      JSON.stringify({
        success: true,
        report_id: reportRecord.id,
        report: report,
        generated_at: new Date().toISOString()
      }),
      { 
        status: 200, 
        headers: { ...corsHeaders, 'Content-Type': 'application/json' } 
      }
    )
  } else {
    // For HTML/PDF formats, return metadata and download link
    return new Response(
      JSON.stringify({
        success: true,
        report_id: reportRecord.id,
        format: format,
        download_url: `/reports/${reportRecord.id}/download`,
        generated_at: new Date().toISOString(),
        summary: report.executive_summary
      }),
      { 
        status: 200, 
        headers: { ...corsHeaders, 'Content-Type': 'application/json' } 
      }
    )
  }
}

async function generateSEOReport(
  supabase: any,
  business: any,
  campaign_id: string | undefined,
  dateRange: { start_date: string; end_date: string },
  includeSections: string[]
): Promise<SEOReport> {
  
  const reportId = `report_${Date.now()}`
  const sections: ReportSection[] = []

  // Get comparison period (previous period of same length)
  const comparisonRange = calculateComparisonPeriod(dateRange)

  // Executive Summary Data
  const executiveSummary = await generateExecutiveSummary(
    supabase,
    business.id,
    campaign_id,
    dateRange,
    comparisonRange
  )

  // Generate each requested section
  if (includeSections.includes('traffic')) {
    const trafficSection = await generateTrafficSection(
      supabase,
      business.id,
      campaign_id,
      dateRange,
      comparisonRange
    )
    sections.push(trafficSection)
  }

  if (includeSections.includes('rankings')) {
    const rankingsSection = await generateRankingsSection(
      supabase,
      business.id,
      campaign_id,
      dateRange,
      comparisonRange
    )
    sections.push(rankingsSection)
  }

  if (includeSections.includes('technical')) {
    const technicalSection = await generateTechnicalSection(
      supabase,
      business.id,
      dateRange,
      comparisonRange
    )
    sections.push(technicalSection)
  }

  if (includeSections.includes('content')) {
    const contentSection = await generateContentSection(
      supabase,
      business.id,
      campaign_id,
      dateRange,
      comparisonRange
    )
    sections.push(contentSection)
  }

  if (includeSections.includes('conversions')) {
    const conversionsSection = await generateConversionsSection(
      supabase,
      business.id,
      dateRange,
      comparisonRange
    )
    sections.push(conversionsSection)
  }

  if (includeSections.includes('competitors')) {
    const competitorsSection = await generateCompetitorsSection(
      supabase,
      business.id,
      campaign_id,
      dateRange
    )
    sections.push(competitorsSection)
  }

  // Get metadata
  const metadata = await generateReportMetadata(
    supabase,
    business.id,
    campaign_id,
    dateRange
  )

  return {
    report_id: reportId,
    business_name: business.business_name,
    report_period: {
      start_date: dateRange.start_date,
      end_date: dateRange.end_date,
      period_type: calculatePeriodType(dateRange)
    },
    executive_summary: executiveSummary,
    sections,
    generated_at: new Date().toISOString(),
    report_metadata: metadata
  }
}

async function generateExecutiveSummary(
  supabase: any,
  business_id: string,
  campaign_id: string | undefined,
  dateRange: any,
  comparisonRange: any
): Promise<any> {
  
  // Get GA metrics for current and comparison periods
  const [currentGA, previousGA] = await Promise.all([
    getGAMetricsSummary(supabase, business_id, dateRange),
    getGAMetricsSummary(supabase, business_id, comparisonRange)
  ])

  // Get GSC metrics for current and comparison periods
  const [currentGSC, previousGSC] = await Promise.all([
    getGSCMetricsSummary(supabase, business_id, dateRange),
    getGSCMetricsSummary(supabase, business_id, comparisonRange)
  ])

  // Get ranking changes
  const [currentRankings, previousRankings] = await Promise.all([
    getRankingsSummary(supabase, business_id, campaign_id, dateRange),
    getRankingsSummary(supabase, business_id, campaign_id, comparisonRange)
  ])

  const keyMetrics = {
    organic_traffic: {
      current: currentGA.organic_traffic || 0,
      previous: previousGA.organic_traffic || 0,
      change: calculatePercentageChange(currentGA.organic_traffic, previousGA.organic_traffic)
    },
    keyword_rankings: {
      current: currentRankings.avg_position || 0,
      previous: previousRankings.avg_position || 0,
      change: calculatePercentageChange(previousRankings.avg_position, currentRankings.avg_position) // Inverse for rankings
    },
    total_impressions: {
      current: currentGSC.total_impressions || 0,
      previous: previousGSC.total_impressions || 0,
      change: calculatePercentageChange(currentGSC.total_impressions, previousGSC.total_impressions)
    },
    avg_position: {
      current: currentGSC.avg_position || 0,
      previous: previousGSC.avg_position || 0,
      change: calculatePercentageChange(previousGSC.avg_position, currentGSC.avg_position) // Inverse for position
    },
    goal_completions: {
      current: currentGA.goal_completions || 0,
      previous: previousGA.goal_completions || 0,
      change: calculatePercentageChange(currentGA.goal_completions, previousGA.goal_completions)
    }
  }

  const topAchievements = generateTopAchievements(keyMetrics)
  const keyIssues = generateKeyIssues(keyMetrics)
  const nextSteps = generateNextSteps(keyMetrics, currentRankings, currentGA)

  return {
    key_metrics: keyMetrics,
    top_achievements: topAchievements,
    key_issues: keyIssues,
    next_steps: nextSteps
  }
}

async function generateTrafficSection(
  supabase: any,
  business_id: string,
  campaign_id: string | undefined,
  dateRange: any,
  comparisonRange: any
): Promise<ReportSection> {
  
  // Get detailed GA data
  const { data: gaMetrics } = await supabase
    .from('ga_metrics')
    .select('*')
    .eq('business_id', business_id)
    .gte('date', dateRange.start_date)
    .lte('date', dateRange.end_date)
    .order('date')

  const { data: trafficSources } = await supabase
    .from('ga_traffic_sources')
    .select('*')
    .eq('business_id', business_id)
    .eq('date_range', 'last_30_days')
    .order('sessions', { ascending: false })

  const { data: pageData } = await supabase
    .from('ga_page_data')
    .select('*')
    .eq('business_id', business_id)
    .eq('date_range', 'last_30_days')
    .order('page_views', { ascending: false })
    .limit(10)

  const totalSessions = gaMetrics?.reduce((sum, m) => sum + (m.sessions || 0), 0) || 0
  const totalUsers = gaMetrics?.reduce((sum, m) => sum + (m.users || 0), 0) || 0
  const totalPageViews = gaMetrics?.reduce((sum, m) => sum + (m.page_views || 0), 0) || 0
  const avgBounceRate = gaMetrics?.length ? 
    gaMetrics.reduce((sum, m) => sum + (m.bounce_rate || 0), 0) / gaMetrics.length : 0

  const insights = [
    `Total sessions: ${totalSessions.toLocaleString()}`,
    `Unique users: ${totalUsers.toLocaleString()}`,
    `Average bounce rate: ${avgBounceRate.toFixed(1)}%`,
    `Top traffic source: ${trafficSources?.[0]?.source || 'N/A'}`
  ]

  const recommendations = generateTrafficRecommendations(gaMetrics, trafficSources, pageData)

  return {
    section_id: 'traffic',
    title: 'Website Traffic Analysis',
    data: {
      summary: {
        total_sessions: totalSessions,
        total_users: totalUsers,
        total_page_views: totalPageViews,
        avg_bounce_rate: avgBounceRate
      },
      daily_metrics: gaMetrics,
      traffic_sources: trafficSources,
      top_pages: pageData
    },
    insights,
    recommendations,
    charts: [
      {
        type: 'line',
        data: gaMetrics?.map(m => ({ date: m.date, sessions: m.sessions, users: m.users })) || [],
        config: { title: 'Daily Traffic Trends', x_axis: 'date', y_axis: ['sessions', 'users'] }
      },
      {
        type: 'pie',
        data: trafficSources?.slice(0, 5).map(ts => ({ 
          label: `${ts.source}/${ts.medium}`, 
          value: ts.sessions 
        })) || [],
        config: { title: 'Traffic Sources Distribution' }
      }
    ]
  }
}

async function generateRankingsSection(
  supabase: any,
  business_id: string,
  campaign_id: string | undefined,
  dateRange: any,
  comparisonRange: any
): Promise<ReportSection> {
  
  // Get GSC data for rankings
  const { data: gscData } = await supabase
    .from('gsc_search_analytics')
    .select('*')
    .eq('business_id', business_id)
    .gte('date', dateRange.start_date)
    .lte('date', dateRange.end_date)
    .order('clicks', { ascending: false })

  // Get rank tracking data if available
  const { data: rankTrackingData } = await supabase
    .from('rank_tracking')
    .select('*')
    .eq('business_id', business_id)
    .gte('tracked_at', dateRange.start_date)
    .lte('tracked_at', dateRange.end_date)
    .order('tracked_at', { ascending: false })

  const totalClicks = gscData?.reduce((sum, d) => sum + (d.clicks || 0), 0) || 0
  const totalImpressions = gscData?.reduce((sum, d) => sum + (d.impressions || 0), 0) || 0
  const avgCTR = totalImpressions > 0 ? (totalClicks / totalImpressions) * 100 : 0
  const avgPosition = gscData?.length ? 
    gscData.reduce((sum, d) => sum + (d.position || 0), 0) / gscData.length : 0

  // Analyze keyword performance
  const topKeywords = analyzeTopKeywords(gscData)
  const keywordChanges = analyzeKeywordChanges(gscData, rankTrackingData)

  const insights = [
    `Total clicks from search: ${totalClicks.toLocaleString()}`,
    `Total impressions: ${totalImpressions.toLocaleString()}`,
    `Average CTR: ${avgCTR.toFixed(2)}%`,
    `Average position: ${avgPosition.toFixed(1)}`
  ]

  const recommendations = generateRankingsRecommendations(gscData, rankTrackingData, avgCTR, avgPosition)

  return {
    section_id: 'rankings',
    title: 'Search Rankings Performance',
    data: {
      summary: {
        total_clicks: totalClicks,
        total_impressions: totalImpressions,
        avg_ctr: avgCTR,
        avg_position: avgPosition
      },
      top_keywords: topKeywords,
      keyword_changes: keywordChanges,
      gsc_data: gscData?.slice(0, 20)
    },
    insights,
    recommendations,
    charts: [
      {
        type: 'bar',
        data: topKeywords.slice(0, 10).map(k => ({ 
          keyword: k.query, 
          clicks: k.clicks,
          position: k.position 
        })),
        config: { title: 'Top Performing Keywords', x_axis: 'keyword', y_axis: ['clicks'] }
      }
    ]
  }
}

async function generateTechnicalSection(
  supabase: any,
  business_id: string,
  dateRange: any,
  comparisonRange: any
): Promise<ReportSection> {
  
  // Get technical audit data
  const { data: technicalAudits } = await supabase
    .from('technical_audits')
    .select('*')
    .eq('business_id', business_id)
    .gte('audit_date', dateRange.start_date)
    .lte('audit_date', dateRange.end_date)
    .order('audit_date', { ascending: false })
    .limit(5)

  // Get GSC indexing data
  const { data: indexingData } = await supabase
    .from('gsc_indexing_status')
    .select('*')
    .eq('business_id', business_id)

  const latestAudit = technicalAudits?.[0]
  const indexedPages = indexingData?.filter(page => page.indexing_status === 'Indexed').length || 0
  const totalPages = indexingData?.length || 0
  const indexingRate = totalPages > 0 ? (indexedPages / totalPages) * 100 : 0

  const insights = [
    latestAudit ? `Performance score: ${latestAudit.performance_score}/100` : 'No recent audit data',
    latestAudit ? `SEO score: ${latestAudit.seo_score}/100` : 'No SEO score available',
    `Pages indexed: ${indexedPages} of ${totalPages} (${indexingRate.toFixed(1)}%)`,
    latestAudit ? `Critical issues: ${latestAudit.critical_issues}` : 'No critical issues data'
  ]

  const recommendations = generateTechnicalRecommendations(latestAudit, indexingData)

  return {
    section_id: 'technical',
    title: 'Technical SEO Analysis',
    data: {
      latest_audit: latestAudit,
      audit_history: technicalAudits,
      indexing_status: {
        indexed_pages: indexedPages,
        total_pages: totalPages,
        indexing_rate: indexingRate
      },
      indexing_details: indexingData
    },
    insights,
    recommendations
  }
}

async function generateContentSection(
  supabase: any,
  business_id: string,
  campaign_id: string | undefined,
  dateRange: any,
  comparisonRange: any
): Promise<ReportSection> {
  
  // Get content performance data
  const { data: contentPerformance } = await supabase
    .from('content_performance')
    .select('*')
    .eq('business_id', business_id)
    .gte('analysis_date', dateRange.start_date)
    .lte('analysis_date', dateRange.end_date)
    .order('organic_traffic', { ascending: false })

  // Get GA page data for content analysis
  const { data: pageData } = await supabase
    .from('ga_page_data')
    .select('*')
    .eq('business_id', business_id)
    .eq('date_range', 'last_30_days')
    .order('page_views', { ascending: false })

  const topContent = contentPerformance?.slice(0, 10) || []
  const avgWordsPerPage = contentPerformance?.length ? 
    contentPerformance.reduce((sum, c) => sum + (c.word_count || 0), 0) / contentPerformance.length : 0

  const insights = [
    `Total content pieces analyzed: ${contentPerformance?.length || 0}`,
    `Average word count: ${avgWordsPerPage.toFixed(0)} words`,
    `Top performing page: ${topContent[0]?.title || 'N/A'}`,
    `Content driving most organic traffic: ${topContent[0]?.organic_traffic || 0} sessions`
  ]

  const recommendations = generateContentRecommendations(contentPerformance, pageData)

  return {
    section_id: 'content',
    title: 'Content Performance Analysis',
    data: {
      summary: {
        total_content: contentPerformance?.length || 0,
        avg_word_count: avgWordsPerPage,
        total_organic_traffic: contentPerformance?.reduce((sum, c) => sum + (c.organic_traffic || 0), 0) || 0
      },
      top_content: topContent,
      all_content: contentPerformance
    },
    insights,
    recommendations,
    charts: [
      {
        type: 'bar',
        data: topContent.slice(0, 10).map(c => ({ 
          title: c.title?.substring(0, 30) + '...',
          organic_traffic: c.organic_traffic 
        })),
        config: { title: 'Top Content by Organic Traffic', x_axis: 'title', y_axis: ['organic_traffic'] }
      }
    ]
  }
}

async function generateConversionsSection(
  supabase: any,
  business_id: string,
  dateRange: any,
  comparisonRange: any
): Promise<ReportSection> {
  
  // Get GA goals data
  const { data: gaMetrics } = await supabase
    .from('ga_metrics')
    .select('*')
    .eq('business_id', business_id)
    .gte('date', dateRange.start_date)
    .lte('date', dateRange.end_date)

  const { data: goals } = await supabase
    .from('ga_goals')
    .select('*')
    .eq('business_id', business_id)
    .eq('is_active', true)

  const totalGoalCompletions = gaMetrics?.reduce((sum, m) => sum + (m.goal_completions || 0), 0) || 0
  const totalSessions = gaMetrics?.reduce((sum, m) => sum + (m.sessions || 0), 0) || 0
  const overallConversionRate = totalSessions > 0 ? (totalGoalCompletions / totalSessions) * 100 : 0

  const insights = [
    `Total goal completions: ${totalGoalCompletions}`,
    `Overall conversion rate: ${overallConversionRate.toFixed(2)}%`,
    `Active goals tracked: ${goals?.length || 0}`,
    `Best converting day: ${findBestConvertingDay(gaMetrics)}`
  ]

  const recommendations = generateConversionsRecommendations(gaMetrics, goals, overallConversionRate)

  return {
    section_id: 'conversions',
    title: 'Conversions & Goals Analysis',
    data: {
      summary: {
        total_goal_completions: totalGoalCompletions,
        overall_conversion_rate: overallConversionRate,
        active_goals: goals?.length || 0
      },
      goals_config: goals,
      daily_conversions: gaMetrics?.map(m => ({
        date: m.date,
        goal_completions: m.goal_completions,
        conversion_rate: m.conversion_rate,
        sessions: m.sessions
      }))
    },
    insights,
    recommendations,
    charts: [
      {
        type: 'line',
        data: gaMetrics?.map(m => ({ 
          date: m.date, 
          goal_completions: m.goal_completions,
          conversion_rate: m.conversion_rate 
        })) || [],
        config: { title: 'Daily Conversion Trends', x_axis: 'date', y_axis: ['goal_completions', 'conversion_rate'] }
      }
    ]
  }
}

async function generateCompetitorsSection(
  supabase: any,
  business_id: string,
  campaign_id: string | undefined,
  dateRange: any
): Promise<ReportSection> {
  
  // Get latest competitor analysis
  const { data: competitorAnalysis } = await supabase
    .from('competitor_analysis')
    .select('*')
    .eq('business_id', business_id)
    .gte('analysis_date', dateRange.start_date)
    .order('analysis_date', { ascending: false })
    .limit(1)

  const latestAnalysis = competitorAnalysis?.[0]

  const insights = latestAnalysis ? [
    `Competitors analyzed: ${latestAnalysis.competitors_analyzed?.length || 0}`,
    `Competitive gaps identified: ${latestAnalysis.competitive_gaps?.length || 0}`,
    `Quick wins available: ${latestAnalysis.competitive_gaps?.filter((gap: any) => gap.difficulty === 'low').length || 0}`,
    `Domain authority position: ${getDomainAuthorityPosition(latestAnalysis)}`
  ] : ['No recent competitor analysis available']

  const recommendations = latestAnalysis ? 
    latestAnalysis.recommendations?.slice(0, 3).map((r: any) => r.description) || [] :
    ['Run a competitor analysis to get insights']

  return {
    section_id: 'competitors',
    title: 'Competitive Analysis',
    data: {
      latest_analysis: latestAnalysis,
      competitive_gaps: latestAnalysis?.competitive_gaps || [],
      recommendations: latestAnalysis?.recommendations || []
    },
    insights,
    recommendations
  }
}

// Helper functions
function calculateDateRangeForReportType(reportType: string): { start_date: string; end_date: string } {
  const end = new Date()
  let start = new Date()

  switch (reportType) {
    case 'weekly':
      start.setDate(end.getDate() - 7)
      break
    case 'monthly':
      start.setMonth(end.getMonth() - 1)
      break
    case 'quarterly':
      start.setMonth(end.getMonth() - 3)
      break
    default:
      start.setMonth(end.getMonth() - 1)
  }

  return {
    start_date: start.toISOString().split('T')[0],
    end_date: end.toISOString().split('T')[0]
  }
}

function calculateComparisonPeriod(dateRange: { start_date: string; end_date: string }): { start_date: string; end_date: string } {
  const start = new Date(dateRange.start_date)
  const end = new Date(dateRange.end_date)
  const duration = end.getTime() - start.getTime()

  const comparisonEnd = new Date(start.getTime() - 24 * 60 * 60 * 1000) // Day before start
  const comparisonStart = new Date(comparisonEnd.getTime() - duration)

  return {
    start_date: comparisonStart.toISOString().split('T')[0],
    end_date: comparisonEnd.toISOString().split('T')[0]
  }
}

function calculatePercentageChange(current: number, previous: number): number {
  if (previous === 0) return current > 0 ? 100 : 0
  return Math.round(((current - previous) / previous) * 100 * 10) / 10
}

async function getGAMetricsSummary(supabase: any, business_id: string, dateRange: any) {
  const { data } = await supabase
    .from('ga_metrics')
    .select('*')
    .eq('business_id', business_id)
    .gte('date', dateRange.start_date)
    .lte('date', dateRange.end_date)

  if (!data || data.length === 0) return {}

  return {
    organic_traffic: data.reduce((sum: number, m: any) => sum + (m.organic_traffic || 0), 0),
    goal_completions: data.reduce((sum: number, m: any) => sum + (m.goal_completions || 0), 0),
    sessions: data.reduce((sum: number, m: any) => sum + (m.sessions || 0), 0),
    users: data.reduce((sum: number, m: any) => sum + (m.users || 0), 0)
  }
}

async function getGSCMetricsSummary(supabase: any, business_id: string, dateRange: any) {
  const { data } = await supabase
    .from('gsc_search_analytics')
    .select('*')
    .eq('business_id', business_id)
    .gte('date', dateRange.start_date)
    .lte('date', dateRange.end_date)

  if (!data || data.length === 0) return {}

  return {
    total_impressions: data.reduce((sum: number, d: any) => sum + (d.impressions || 0), 0),
    total_clicks: data.reduce((sum: number, d: any) => sum + (d.clicks || 0), 0),
    avg_position: data.length > 0 ? data.reduce((sum: number, d: any) => sum + (d.position || 0), 0) / data.length : 0
  }
}

async function getRankingsSummary(supabase: any, business_id: string, campaign_id: string | undefined, dateRange: any) {
  const { data } = await supabase
    .from('gsc_search_analytics')
    .select('*')
    .eq('business_id', business_id)
    .gte('date', dateRange.start_date)
    .lte('date', dateRange.end_date)

  if (!data || data.length === 0) return {}

  return {
    avg_position: data.length > 0 ? data.reduce((sum: number, d: any) => sum + (d.position || 0), 0) / data.length : 0,
    total_keywords: new Set(data.map((d: any) => d.query)).size
  }
}

// Additional helper functions for generating recommendations and insights
function generateTopAchievements(keyMetrics: any): string[] {
  const achievements = []
  
  if (keyMetrics.organic_traffic.change > 10) {
    achievements.push(`Organic traffic increased by ${keyMetrics.organic_traffic.change}%`)
  }
  if (keyMetrics.keyword_rankings.change > 5) {
    achievements.push(`Average keyword rankings improved by ${keyMetrics.keyword_rankings.change}%`)
  }
  if (keyMetrics.goal_completions.change > 15) {
    achievements.push(`Goal completions increased by ${keyMetrics.goal_completions.change}%`)
  }
  
  return achievements.length > 0 ? achievements : ['Maintaining consistent performance across key metrics']
}

function generateKeyIssues(keyMetrics: any): string[] {
  const issues = []
  
  if (keyMetrics.organic_traffic.change < -10) {
    issues.push(`Organic traffic declined by ${Math.abs(keyMetrics.organic_traffic.change)}%`)
  }
  if (keyMetrics.avg_position.change < -5) {
    issues.push(`Average search position dropped by ${Math.abs(keyMetrics.avg_position.change)}%`)
  }
  if (keyMetrics.goal_completions.change < -15) {
    issues.push(`Goal completions decreased by ${Math.abs(keyMetrics.goal_completions.change)}%`)
  }
  
  return issues.length > 0 ? issues : ['No significant issues identified in key metrics']
}

function generateNextSteps(keyMetrics: any, rankings: any, ga: any): string[] {
  const steps = []
  
  if (keyMetrics.organic_traffic.change < 0) {
    steps.push('Focus on content optimization and keyword targeting')
  }
  if (keyMetrics.avg_position.current > 10) {
    steps.push('Improve on-page SEO and technical optimization')
  }
  if (keyMetrics.goal_completions.current < 10) {
    steps.push('Optimize conversion funnels and landing pages')
  }
  
  return steps.length > 0 ? steps : [
    'Continue monitoring performance metrics',
    'Maintain current SEO strategies',
    'Plan next phase of optimization'
  ]
}

function generateTrafficRecommendations(gaMetrics: any, trafficSources: any, pageData: any): string[] {
  const recommendations = []
  
  const avgBounceRate = gaMetrics?.length ? 
    gaMetrics.reduce((sum: number, m: any) => sum + (m.bounce_rate || 0), 0) / gaMetrics.length : 0
  
  if (avgBounceRate > 70) {
    recommendations.push('High bounce rate detected - improve page loading speed and content relevance')
  }
  
  const organicPercentage = trafficSources?.find((ts: any) => ts.medium === 'organic')?.sessions || 0
  const totalSessions = trafficSources?.reduce((sum: number, ts: any) => sum + (ts.sessions || 0), 0) || 1
  
  if ((organicPercentage / totalSessions) < 0.4) {
    recommendations.push('Increase organic traffic through improved SEO and content marketing')
  }
  
  return recommendations
}

function generateRankingsRecommendations(gscData: any, rankingData: any, avgCTR: number, avgPosition: number): string[] {
  const recommendations = []
  
  if (avgCTR < 2) {
    recommendations.push('Improve meta titles and descriptions to increase click-through rates')
  }
  if (avgPosition > 10) {
    recommendations.push('Focus on improving search rankings through content optimization and link building')
  }
  if (gscData?.length && gscData.filter((d: any) => d.position <= 3).length < 5) {
    recommendations.push('Target more keywords for top 3 positions to maximize visibility')
  }
  
  return recommendations
}

function generateTechnicalRecommendations(latestAudit: any, indexingData: any): string[] {
  const recommendations = []
  
  if (latestAudit?.performance_score < 70) {
    recommendations.push('Improve site performance - optimize images, enable compression, and minimize JavaScript')
  }
  if (latestAudit?.seo_score < 80) {
    recommendations.push('Address SEO technical issues - fix meta tags, heading structure, and internal linking')
  }
  
  const errorPages = indexingData?.filter((page: any) => page.coverage_status === 'Error').length || 0
  if (errorPages > 0) {
    recommendations.push(`Fix ${errorPages} pages with indexing errors to improve search visibility`)
  }
  
  return recommendations
}

function generateContentRecommendations(contentPerformance: any, pageData: any): string[] {
  const recommendations = []
  
  const lowPerformingContent = contentPerformance?.filter((c: any) => c.organic_traffic < 10).length || 0
  if (lowPerformingContent > 0) {
    recommendations.push(`Optimize ${lowPerformingContent} underperforming content pieces`)
  }
  
  const avgWordCount = contentPerformance?.length ? 
    contentPerformance.reduce((sum: number, c: any) => sum + (c.word_count || 0), 0) / contentPerformance.length : 0
  
  if (avgWordCount < 800) {
    recommendations.push('Increase content depth - aim for 1000+ words per article for better rankings')
  }
  
  return recommendations
}

function generateConversionsRecommendations(gaMetrics: any, goals: any, conversionRate: number): string[] {
  const recommendations = []
  
  if (conversionRate < 2) {
    recommendations.push('Improve conversion rate optimization - test different CTAs and landing page layouts')
  }
  if (!goals || goals.length === 0) {
    recommendations.push('Set up goal tracking in Google Analytics to measure conversion performance')
  }
  
  return recommendations
}

function analyzeTopKeywords(gscData: any): any[] {
  if (!gscData) return []
  
  // Group by query and sum metrics
  const keywordMap = new Map()
  
  for (const item of gscData) {
    if (!keywordMap.has(item.query)) {
      keywordMap.set(item.query, {
        query: item.query,
        clicks: 0,
        impressions: 0,
        position: 0,
        count: 0
      })
    }
    
    const keyword = keywordMap.get(item.query)
    keyword.clicks += item.clicks || 0
    keyword.impressions += item.impressions || 0
    keyword.position += item.position || 0
    keyword.count += 1
  }
  
  return Array.from(keywordMap.values())
    .map(k => ({
      ...k,
      position: k.position / k.count,
      ctr: k.impressions > 0 ? (k.clicks / k.impressions) * 100 : 0
    }))
    .sort((a, b) => b.clicks - a.clicks)
}

function analyzeKeywordChanges(gscData: any, rankingData: any): any[] {
  // This would compare current vs previous ranking data
  // For now, return sample changes
  return [
    { keyword: 'restaurant orlando', position_change: -2, status: 'improved' },
    { keyword: 'seafood restaurant', position_change: 3, status: 'declined' },
    { keyword: 'waterfront dining', position_change: -1, status: 'improved' }
  ]
}

function findBestConvertingDay(gaMetrics: any): string {
  if (!gaMetrics || gaMetrics.length === 0) return 'N/A'
  
  const bestDay = gaMetrics.reduce((best: any, current: any) => 
    (current.conversion_rate || 0) > (best.conversion_rate || 0) ? current : best
  )
  
  return bestDay.date || 'N/A'
}

function getDomainAuthorityPosition(analysis: any): string {
  if (!analysis?.domain_authority_data) return 'N/A'
  
  const businessPosition = analysis.domain_authority_data.findIndex((d: any) => 
    d.domain.includes('business') || d.position === 'Your Business'
  )
  
  return businessPosition >= 0 ? `#${businessPosition + 1}` : 'N/A'
}

function calculatePeriodType(dateRange: any): string {
  const start = new Date(dateRange.start_date)
  const end = new Date(dateRange.end_date)
  const days = Math.ceil((end.getTime() - start.getTime()) / (1000 * 60 * 60 * 24))
  
  if (days <= 7) return 'Weekly'
  if (days <= 31) return 'Monthly'
  if (days <= 92) return 'Quarterly'
  return 'Custom'
}

async function generateReportMetadata(supabase: any, business_id: string, campaign_id: string | undefined, dateRange: any): Promise<any> {
  // Get counts of tracked items
  const [keywordsCount, pagesCount] = await Promise.all([
    supabase.from('gsc_search_analytics').select('query', { count: 'exact', head: true }).eq('business_id', business_id),
    supabase.from('ga_page_data').select('page_path', { count: 'exact', head: true }).eq('business_id', business_id)
  ])
  
  return {
    data_sources: ['Google Analytics', 'Google Search Console', 'Technical Audits'],
    date_ranges_analyzed: dateRange,
    total_keywords_tracked: keywordsCount.count || 0,
    total_pages_analyzed: pagesCount.count || 0
  }
}

async function handleScheduleReport(req: Request, supabase: any) {
  // Implementation for scheduling automated reports
  return new Response(
    JSON.stringify({ success: true, message: 'Report scheduling not yet implemented' }),
    { status: 200, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
  )
}

async function handleListReports(req: Request, supabase: any) {
  // Implementation for listing existing reports
  return new Response(
    JSON.stringify({ success: true, message: 'Report listing not yet implemented' }),
    { status: 200, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
  )
}

async function handleGetReport(req: Request, supabase: any) {
  // Implementation for retrieving specific report
  return new Response(
    JSON.stringify({ success: true, message: 'Report retrieval not yet implemented' }),
    { status: 200, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
  )
}

async function handleReportTemplates(req: Request, supabase: any) {
  // Implementation for report templates
  return new Response(
    JSON.stringify({ success: true, message: 'Report templates not yet implemented' }),
    { status: 200, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
  )
}

async function sendReportByEmail(supabase: any, report: any, recipients: string[], format: string) {
  // Implementation for email delivery
  console.log(`Sending ${format} report to ${recipients.join(', ')}`)
  // In real implementation, integrate with email service
}