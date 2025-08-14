import { serve } from 'https://deno.land/std@0.168.0/http/server.ts'
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'
import { corsHeaders } from '../_shared/cors.ts'

interface AnalyticsQuery {
  business_id: string
  metrics: string[]
  dimensions?: string[]
  date_range: {
    start: string
    end: string
  }
  granularity?: 'hour' | 'day' | 'week' | 'month'
  filters?: any
  comparison?: {
    type: 'period' | 'segment' | 'competitor'
    value: any
  }
}

interface AnalyticsResult {
  metrics: Record<string, any>
  dimensions?: Record<string, any[]>
  time_series?: any[]
  comparison?: any
  insights?: string[]
  visualizations?: any[]
}

serve(async (req) => {
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders })
  }

  try {
    const supabase = createClient(
      Deno.env.get('SUPABASE_URL') ?? '',
      Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') ?? ''
    )

    const { action, query, export_format } = await req.json()

    let result: any

    switch (action) {
      case 'query':
        result = await executeAnalyticsQuery(supabase, query)
        break
      
      case 'custom_report':
        result = await generateCustomReport(supabase, query)
        break
      
      case 'funnel_analysis':
        result = await analyzeFunnel(supabase, query)
        break
      
      case 'cohort_analysis':
        result = await analyzeCohorts(supabase, query)
        break
      
      case 'attribution_analysis':
        result = await analyzeAttribution(supabase, query)
        break
      
      case 'predictive_analysis':
        result = await runPredictiveAnalysis(supabase, query)
        break
      
      case 'anomaly_detection':
        result = await detectAnomalies(supabase, query)
        break
      
      case 'export':
        result = await exportAnalytics(supabase, query, export_format)
        break
      
      default:
        throw new Error(`Unknown action: ${action}`)
    }

    return new Response(
      JSON.stringify(result),
      { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )

  } catch (error) {
    console.error('Analytics engine error:', error)
    return new Response(
      JSON.stringify({ error: error.message }),
      { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }
})

async function executeAnalyticsQuery(
  supabase: any,
  query: AnalyticsQuery
): Promise<AnalyticsResult> {
  
  const result: AnalyticsResult = {
    metrics: {},
    dimensions: {},
    time_series: [],
    insights: []
  }

  // Process each requested metric
  for (const metric of query.metrics) {
    switch (metric) {
      case 'organic_traffic':
        result.metrics.organic_traffic = await getOrganicTraffic(supabase, query)
        break
      
      case 'keyword_rankings':
        result.metrics.keyword_rankings = await getKeywordRankings(supabase, query)
        break
      
      case 'conversion_rate':
        result.metrics.conversion_rate = await getConversionRate(supabase, query)
        break
      
      case 'page_performance':
        result.metrics.page_performance = await getPagePerformance(supabase, query)
        break
      
      case 'backlink_profile':
        result.metrics.backlink_profile = await getBacklinkProfile(supabase, query)
        break
      
      case 'content_performance':
        result.metrics.content_performance = await getContentPerformance(supabase, query)
        break
      
      case 'technical_health':
        result.metrics.technical_health = await getTechnicalHealth(supabase, query)
        break
      
      case 'competitor_visibility':
        result.metrics.competitor_visibility = await getCompetitorVisibility(supabase, query)
        break
    }
  }

  // Generate time series data
  if (query.granularity) {
    result.time_series = await generateTimeSeries(supabase, query)
  }

  // Add dimensions if requested
  if (query.dimensions) {
    for (const dimension of query.dimensions) {
      result.dimensions![dimension] = await getDimensionData(supabase, query, dimension)
    }
  }

  // Add comparison data if requested
  if (query.comparison) {
    result.comparison = await generateComparison(supabase, query)
  }

  // Generate insights
  result.insights = await generateInsights(result, query)

  // Generate visualization recommendations
  result.visualizations = generateVisualizationRecommendations(result, query)

  return result
}

async function generateCustomReport(
  supabase: any,
  query: any
): Promise<any> {
  
  const sections = []

  // Executive Summary
  const summary = await generateExecutiveSummary(supabase, query)
  sections.push({
    title: 'Executive Summary',
    type: 'summary',
    data: summary
  })

  // Traffic Analysis
  const traffic = await analyzeTrafficTrends(supabase, query)
  sections.push({
    title: 'Traffic Analysis',
    type: 'chart',
    chart_type: 'line',
    data: traffic
  })

  // Keyword Performance
  const keywords = await analyzeKeywordPerformance(supabase, query)
  sections.push({
    title: 'Keyword Performance',
    type: 'table',
    data: keywords
  })

  // Content Analysis
  const content = await analyzeContentMetrics(supabase, query)
  sections.push({
    title: 'Content Performance',
    type: 'mixed',
    data: content
  })

  // Competitor Comparison
  const competitors = await compareCompetitors(supabase, query)
  sections.push({
    title: 'Competitor Analysis',
    type: 'comparison',
    data: competitors
  })

  // Recommendations
  const recommendations = await generateRecommendations(supabase, query, sections)
  sections.push({
    title: 'Recommendations',
    type: 'list',
    data: recommendations
  })

  return {
    report_id: crypto.randomUUID(),
    generated_at: new Date().toISOString(),
    query_params: query,
    sections,
    export_formats: ['pdf', 'excel', 'powerpoint']
  }
}

async function analyzeFunnel(
  supabase: any,
  query: any
): Promise<any> {
  
  const funnel_stages = query.funnel_stages || [
    'impressions',
    'clicks',
    'sessions',
    'engaged_sessions',
    'conversions'
  ]

  const funnel_data = []
  let previous_count = 0

  for (const stage of funnel_stages) {
    const count = await getFunnelStageCount(supabase, query, stage)
    const conversion_rate = previous_count > 0 ? (count / previous_count) * 100 : 100
    
    funnel_data.push({
      stage,
      count,
      conversion_rate,
      drop_off: previous_count - count,
      drop_off_rate: previous_count > 0 ? ((previous_count - count) / previous_count) * 100 : 0
    })
    
    previous_count = count
  }

  // Calculate overall conversion rate
  const overall_conversion = funnel_data.length > 0 ? 
    (funnel_data[funnel_data.length - 1].count / funnel_data[0].count) * 100 : 0

  // Identify bottlenecks
  const bottlenecks = funnel_data
    .filter(stage => stage.drop_off_rate > 30)
    .map(stage => ({
      stage: stage.stage,
      drop_off_rate: stage.drop_off_rate,
      recommendation: generateBottleneckRecommendation(stage)
    }))

  return {
    funnel_data,
    overall_conversion,
    bottlenecks,
    visualization: {
      type: 'funnel',
      data: funnel_data
    }
  }
}

async function analyzeCohorts(
  supabase: any,
  query: any
): Promise<any> {
  
  const cohort_type = query.cohort_type || 'acquisition_date'
  const metric = query.cohort_metric || 'retention'
  const periods = query.periods || 12

  const cohorts = []
  const start_date = new Date(query.date_range.start)
  
  for (let i = 0; i < periods; i++) {
    const cohort_date = new Date(start_date)
    cohort_date.setMonth(cohort_date.getMonth() + i)
    
    const cohort_data = await getCohortData(
      supabase,
      query.business_id,
      cohort_date,
      cohort_type,
      metric
    )
    
    cohorts.push({
      period: cohort_date.toISOString().slice(0, 7),
      size: cohort_data.size,
      metrics: cohort_data.metrics
    })
  }

  // Calculate retention curves
  const retention_curves = calculateRetentionCurves(cohorts)
  
  // Identify trends
  const trends = identifyCohortTrends(cohorts)

  return {
    cohorts,
    retention_curves,
    trends,
    visualization: {
      type: 'cohort_matrix',
      data: cohorts
    },
    insights: generateCohortInsights(cohorts, trends)
  }
}

async function analyzeAttribution(
  supabase: any,
  query: any
): Promise<any> {
  
  const attribution_model = query.attribution_model || 'last_click'
  
  // Get conversion paths
  const { data: paths } = await supabase
    .from('conversion_paths')
    .select('*')
    .eq('business_id', query.business_id)
    .gte('created_at', query.date_range.start)
    .lte('created_at', query.date_range.end)

  // Apply attribution model
  const attribution_results = applyAttributionModel(paths, attribution_model)
  
  // Calculate channel contributions
  const channel_contributions = calculateChannelContributions(attribution_results)
  
  // Analyze touchpoint effectiveness
  const touchpoint_analysis = analyzeTouchpoints(paths)
  
  // Generate path visualizations
  const path_visualizations = generatePathVisualizations(paths)

  return {
    model: attribution_model,
    channel_contributions,
    touchpoint_analysis,
    path_visualizations,
    top_conversion_paths: getTopConversionPaths(paths),
    recommendations: generateAttributionRecommendations(channel_contributions)
  }
}

async function runPredictiveAnalysis(
  supabase: any,
  query: any
): Promise<any> {
  
  // Get historical data
  const historical_data = await getHistoricalData(supabase, query)
  
  // Perform time series analysis
  const time_series_forecast = performTimeSeriesAnalysis(historical_data)
  
  // Calculate seasonality
  const seasonality = detectSeasonality(historical_data)
  
  // Identify trends
  const trends = identifyTrends(historical_data)
  
  // Generate predictions
  const predictions = {
    traffic: predictTraffic(historical_data, trends, seasonality),
    rankings: predictRankings(historical_data, trends),
    conversions: predictConversions(historical_data, trends, seasonality)
  }
  
  // Calculate confidence intervals
  const confidence_intervals = calculateConfidenceIntervals(predictions)
  
  // Identify risk factors
  const risk_factors = identifyRiskFactors(historical_data, predictions)

  return {
    predictions,
    confidence_intervals,
    seasonality,
    trends,
    risk_factors,
    visualization: {
      type: 'forecast',
      historical: historical_data,
      predicted: predictions
    }
  }
}

async function detectAnomalies(
  supabase: any,
  query: any
): Promise<any> {
  
  const metrics_data = await getMetricsData(supabase, query)
  const anomalies = []

  for (const metric of query.metrics) {
    const metric_data = metrics_data[metric]
    
    // Calculate statistical boundaries
    const stats = calculateStatistics(metric_data)
    const boundaries = {
      upper: stats.mean + (2 * stats.stdDev),
      lower: stats.mean - (2 * stats.stdDev)
    }
    
    // Detect anomalies
    const metric_anomalies = metric_data
      .filter((point: any) => 
        point.value > boundaries.upper || point.value < boundaries.lower
      )
      .map((point: any) => ({
        metric,
        timestamp: point.timestamp,
        value: point.value,
        expected_range: boundaries,
        deviation: Math.abs(point.value - stats.mean) / stats.stdDev,
        severity: calculateAnomalySeverity(point.value, boundaries, stats)
      }))
    
    anomalies.push(...metric_anomalies)
  }

  // Correlate anomalies across metrics
  const correlated_anomalies = correlateAnomalies(anomalies)
  
  // Generate alerts for significant anomalies
  const alerts = anomalies
    .filter(a => a.severity === 'high' || a.severity === 'critical')
    .map(a => ({
      type: 'anomaly_detected',
      metric: a.metric,
      severity: a.severity,
      message: generateAnomalyAlert(a),
      recommended_action: generateAnomalyRecommendation(a)
    }))

  return {
    anomalies,
    correlated_anomalies,
    alerts,
    visualization: {
      type: 'anomaly_chart',
      data: metrics_data,
      anomalies
    }
  }
}

async function exportAnalytics(
  supabase: any,
  query: any,
  format: string
): Promise<any> {
  
  // Generate the analytics data
  const analytics_data = await executeAnalyticsQuery(supabase, query)
  
  switch (format) {
    case 'csv':
      return exportToCSV(analytics_data)
    
    case 'excel':
      return exportToExcel(analytics_data)
    
    case 'json':
      return analytics_data
    
    case 'pdf':
      return await generatePDFReport(analytics_data, query)
    
    case 'powerpoint':
      return await generatePowerPointReport(analytics_data, query)
    
    default:
      throw new Error(`Unsupported export format: ${format}`)
  }
}

// Helper functions

async function getOrganicTraffic(supabase: any, query: any): Promise<any> {
  const { data } = await supabase
    .from('ga_metrics')
    .select('*')
    .eq('business_id', query.business_id)
    .gte('date', query.date_range.start)
    .lte('date', query.date_range.end)

  return {
    total: data?.reduce((sum: number, d: any) => sum + (d.organic_traffic || 0), 0) || 0,
    average: data?.length ? 
      data.reduce((sum: number, d: any) => sum + (d.organic_traffic || 0), 0) / data.length : 0,
    trend: calculateTrend(data?.map((d: any) => d.organic_traffic) || [])
  }
}

async function getKeywordRankings(supabase: any, query: any): Promise<any> {
  const { data } = await supabase
    .from('keyword_rankings')
    .select('*')
    .eq('business_id', query.business_id)
    .gte('created_at', query.date_range.start)
    .lte('created_at', query.date_range.end)

  const avgPosition = data?.length ? 
    data.reduce((sum: number, d: any) => sum + d.position, 0) / data.length : 0

  return {
    average_position: avgPosition,
    top_10: data?.filter((d: any) => d.position <= 10).length || 0,
    top_3: data?.filter((d: any) => d.position <= 3).length || 0,
    improved: data?.filter((d: any) => d.position_change < 0).length || 0,
    declined: data?.filter((d: any) => d.position_change > 0).length || 0
  }
}

async function getConversionRate(supabase: any, query: any): Promise<any> {
  const { data } = await supabase
    .from('ga_metrics')
    .select('sessions, conversions')
    .eq('business_id', query.business_id)
    .gte('date', query.date_range.start)
    .lte('date', query.date_range.end)

  const totalSessions = data?.reduce((sum: number, d: any) => sum + (d.sessions || 0), 0) || 0
  const totalConversions = data?.reduce((sum: number, d: any) => sum + (d.conversions || 0), 0) || 0

  return {
    rate: totalSessions > 0 ? (totalConversions / totalSessions) * 100 : 0,
    total_conversions: totalConversions,
    total_sessions: totalSessions
  }
}

async function generateTimeSeries(supabase: any, query: any): Promise<any[]> {
  const timeSeries = []
  const start = new Date(query.date_range.start)
  const end = new Date(query.date_range.end)
  
  const current = new Date(start)
  while (current <= end) {
    const period_start = new Date(current)
    const period_end = new Date(current)
    
    switch (query.granularity) {
      case 'hour':
        period_end.setHours(period_end.getHours() + 1)
        break
      case 'day':
        period_end.setDate(period_end.getDate() + 1)
        break
      case 'week':
        period_end.setDate(period_end.getDate() + 7)
        break
      case 'month':
        period_end.setMonth(period_end.getMonth() + 1)
        break
    }
    
    const period_data = await getPeriodMetrics(
      supabase,
      query.business_id,
      period_start.toISOString(),
      period_end.toISOString(),
      query.metrics
    )
    
    timeSeries.push({
      period: period_start.toISOString(),
      ...period_data
    })
    
    current.setTime(period_end.getTime())
  }
  
  return timeSeries
}

async function generateInsights(result: any, query: any): Promise<string[]> {
  const insights = []
  
  // Traffic insights
  if (result.metrics.organic_traffic) {
    const traffic = result.metrics.organic_traffic
    if (traffic.trend > 10) {
      insights.push(`Organic traffic is trending up by ${traffic.trend.toFixed(1)}%`)
    } else if (traffic.trend < -10) {
      insights.push(`⚠️ Organic traffic is declining by ${Math.abs(traffic.trend).toFixed(1)}%`)
    }
  }
  
  // Ranking insights
  if (result.metrics.keyword_rankings) {
    const rankings = result.metrics.keyword_rankings
    if (rankings.improved > rankings.declined * 2) {
      insights.push(`Strong ranking improvements: ${rankings.improved} keywords improved`)
    }
    if (rankings.top_3 > 10) {
      insights.push(`Excellent visibility: ${rankings.top_3} keywords in top 3 positions`)
    }
  }
  
  // Conversion insights
  if (result.metrics.conversion_rate) {
    const cvr = result.metrics.conversion_rate
    if (cvr.rate > 3) {
      insights.push(`High conversion rate of ${cvr.rate.toFixed(2)}%`)
    } else if (cvr.rate < 1) {
      insights.push(`⚠️ Low conversion rate of ${cvr.rate.toFixed(2)}% needs attention`)
    }
  }
  
  return insights
}

function generateVisualizationRecommendations(result: any, query: any): any[] {
  const visualizations = []
  
  // Time series visualization
  if (result.time_series && result.time_series.length > 0) {
    visualizations.push({
      type: 'line_chart',
      title: 'Metrics Over Time',
      data: result.time_series,
      config: {
        x_axis: 'period',
        y_axis: query.metrics,
        smooth: true
      }
    })
  }
  
  // Comparison visualization
  if (result.comparison) {
    visualizations.push({
      type: 'bar_chart',
      title: 'Period Comparison',
      data: result.comparison,
      config: {
        grouped: true,
        show_values: true
      }
    })
  }
  
  // Distribution visualization
  if (result.dimensions && Object.keys(result.dimensions).length > 0) {
    visualizations.push({
      type: 'pie_chart',
      title: 'Distribution by Dimension',
      data: result.dimensions,
      config: {
        show_percentages: true,
        legend_position: 'right'
      }
    })
  }
  
  return visualizations
}

function calculateTrend(values: number[]): number {
  if (values.length < 2) return 0
  
  const n = values.length
  const sumX = (n * (n - 1)) / 2
  const sumY = values.reduce((a, b) => a + b, 0)
  const sumXY = values.reduce((sum, y, x) => sum + x * y, 0)
  const sumX2 = (n * (n - 1) * (2 * n - 1)) / 6
  
  const slope = (n * sumXY - sumX * sumY) / (n * sumX2 - sumX * sumX)
  const intercept = (sumY - slope * sumX) / n
  
  // Calculate percentage change
  const firstValue = intercept
  const lastValue = slope * (n - 1) + intercept
  
  return firstValue !== 0 ? ((lastValue - firstValue) / firstValue) * 100 : 0
}

// Additional helper functions would be implemented here...
function calculateStatistics(data: any[]): any {
  const values = data.map(d => d.value)
  const mean = values.reduce((a, b) => a + b, 0) / values.length
  const variance = values.reduce((sum, val) => sum + Math.pow(val - mean, 2), 0) / values.length
  const stdDev = Math.sqrt(variance)
  
  return { mean, variance, stdDev }
}

function calculateAnomalySeverity(value: number, boundaries: any, stats: any): string {
  const deviation = Math.abs(value - stats.mean) / stats.stdDev
  
  if (deviation > 4) return 'critical'
  if (deviation > 3) return 'high'
  if (deviation > 2) return 'medium'
  return 'low'
}

// Placeholder functions for complex operations
async function getPagePerformance(supabase: any, query: any): Promise<any> {
  return { score: 85, load_time: 2.3, improvements_needed: 3 }
}

async function getBacklinkProfile(supabase: any, query: any): Promise<any> {
  return { total: 1250, quality_score: 72, new_this_period: 45 }
}

async function getContentPerformance(supabase: any, query: any): Promise<any> {
  return { engagement_rate: 4.5, avg_time_on_page: 180, bounce_rate: 35 }
}

async function getTechnicalHealth(supabase: any, query: any): Promise<any> {
  return { score: 92, issues: 8, critical_issues: 1 }
}

async function getCompetitorVisibility(supabase: any, query: any): Promise<any> {
  return { share_of_voice: 28, relative_visibility: 1.15, gap_keywords: 142 }
}