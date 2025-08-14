import { serve } from 'https://deno.land/std@0.168.0/http/server.ts'
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'
import { corsHeaders } from '../_shared/cors.ts'

interface ContentAnalyticsRequest {
  business_id: string
  campaign_id?: string
  date_range?: 'last_7_days' | 'last_30_days' | 'last_90_days' | 'last_year'
  content_types?: string[]
  metrics?: string[]
  include_competitors?: boolean
}

interface ContentMetrics {
  url: string
  title: string
  content_type: string
  target_keyword: string
  publish_date: string
  word_count: number
  organic_traffic: number
  impressions: number
  clicks: number
  ctr: number
  average_position: number
  bounce_rate: number
  time_on_page: number
  pages_per_session: number
  conversions: number
  conversion_rate: number
  social_shares: number
  backlinks: number
  internal_links: number
  page_load_speed: number
  core_web_vitals: {
    lcp: number
    inp: number
    cls: number
  }
}

interface PerformanceReport {
  analysis_date: string
  date_range: string
  total_content_pieces: number
  total_organic_traffic: number
  average_position: number
  total_impressions: number
  total_clicks: number
  overall_ctr: number
  top_performing_content: ContentMetrics[]
  underperforming_content: ContentMetrics[]
  content_by_type: {
    type: string
    count: number
    avg_traffic: number
    avg_position: number
    total_conversions: number
  }[]
  keyword_performance: {
    keyword: string
    content_pieces: number
    total_traffic: number
    avg_position: number
    trend: 'improving' | 'declining' | 'stable'
  }[]
  content_gaps: {
    topic: string
    search_volume: number
    competition: string
    opportunity_score: number
  }[]
  optimization_opportunities: {
    url: string
    issues: string[]
    potential_impact: string
    priority: 'high' | 'medium' | 'low'
  }[]
  recommendations: {
    title: string
    description: string
    affected_pages: number
    expected_impact: string
    priority: string
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
      campaign_id,
      date_range = 'last_30_days',
      content_types = ['article', 'howto', 'comparison', 'listicle', 'landing_page'],
      metrics = ['traffic', 'rankings', 'engagement', 'conversions'],
      include_competitors = false
    }: ContentAnalyticsRequest = await req.json()

    // Validate input
    if (!business_id) {
      return new Response(
        JSON.stringify({ error: 'business_id is required' }),
        { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    // Get business details
    const { data: business } = await supabase
      .from('businesses')
      .select('business_name, industry, website_url')
      .eq('id', business_id)
      .single()

    if (!business) {
      return new Response(
        JSON.stringify({ error: 'Business not found' }),
        { status: 404, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    // Get content briefs for analysis
    let contentQuery = supabase
      .from('content_briefs')
      .select('*')
    
    if (campaign_id) {
      contentQuery = contentQuery.eq('campaign_id', campaign_id)
    }
    
    const { data: contentBriefs } = await contentQuery
      .in('content_type', content_types)
      .order('created_at', { ascending: false })
      .limit(100)

    // Get existing performance data
    const { data: existingPerformance } = await supabase
      .from('content_performance')
      .select('*')
      .eq('business_id', business_id)
      .gte('analysis_date', getDateRangeStart(date_range))
      .order('analysis_date', { ascending: false })

    // Perform content analytics
    const performanceReport = await analyzeContentPerformance(
      business,
      contentBriefs || [],
      existingPerformance || [],
      date_range,
      metrics,
      include_competitors
    )

    // Store updated performance data
    const performanceRecords = []
    for (const content of performanceReport.top_performing_content.slice(0, 50)) {
      const { data: perfRecord } = await supabase
        .from('content_performance')
        .upsert({
          business_id,
          campaign_id,
          url: content.url,
          title: content.title,
          content_type: content.content_type,
          target_keyword: content.target_keyword,
          organic_traffic: content.organic_traffic,
          impressions: content.impressions,
          clicks: content.clicks,
          ctr: content.ctr,
          average_position: content.average_position,
          bounce_rate: content.bounce_rate,
          time_on_page: content.time_on_page,
          conversions: content.conversions,
          conversion_rate: content.conversion_rate,
          social_shares: content.social_shares,
          backlinks: content.backlinks,
          page_load_speed: content.page_load_speed,
          core_web_vitals: content.core_web_vitals,
          analysis_date: new Date().toISOString()
        }, {
          onConflict: 'business_id,url,analysis_date'
        })
        .select()
        .single()

      if (perfRecord) {
        performanceRecords.push(perfRecord)
      }
    }

    // Update campaign with analytics completion
    if (campaign_id) {
      await supabase
        .from('seo_campaigns')
        .update({
          last_analytics_check: new Date().toISOString(),
          total_organic_traffic: performanceReport.total_organic_traffic,
          avg_ctr: performanceReport.overall_ctr
        })
        .eq('id', campaign_id)
    }

    // Log the analytics operation
    await supabase
      .from('seo_logs')
      .insert({
        business_id,
        action_type: 'content_analytics',
        action_description: `Content performance analysis completed for ${performanceReport.total_content_pieces} pieces`,
        new_data: JSON.stringify({
          campaign_id,
          date_range,
          content_analyzed: performanceReport.total_content_pieces,
          total_traffic: performanceReport.total_organic_traffic,
          avg_position: performanceReport.average_position
        })
      })

    return new Response(
      JSON.stringify({
        success: true,
        analysis_date: performanceReport.analysis_date,
        date_range: performanceReport.date_range,
        content_analyzed: performanceReport.total_content_pieces,
        total_traffic: performanceReport.total_organic_traffic,
        average_position: performanceReport.average_position,
        records_updated: performanceRecords.length,
        summary: {
          traffic_summary: {
            total_organic_traffic: performanceReport.total_organic_traffic,
            total_impressions: performanceReport.total_impressions,
            total_clicks: performanceReport.total_clicks,
            overall_ctr: performanceReport.overall_ctr
          },
          top_content: performanceReport.top_performing_content.slice(0, 5),
          content_by_type: performanceReport.content_by_type,
          optimization_opportunities: performanceReport.optimization_opportunities.slice(0, 5),
          recommendations: performanceReport.recommendations
        }
      }),
      { 
        status: 200, 
        headers: { ...corsHeaders, 'Content-Type': 'application/json' } 
      }
    )

  } catch (error) {
    console.error('Content analytics error:', error)
    return new Response(
      JSON.stringify({ error: 'Internal server error', details: error.message }),
      { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }
})

function getDateRangeStart(dateRange: string): string {
  const now = new Date()
  let daysBack = 30
  
  switch (dateRange) {
    case 'last_7_days': daysBack = 7; break
    case 'last_30_days': daysBack = 30; break
    case 'last_90_days': daysBack = 90; break
    case 'last_year': daysBack = 365; break
  }
  
  return new Date(now.getTime() - daysBack * 24 * 60 * 60 * 1000).toISOString()
}

async function analyzeContentPerformance(
  business: any,
  contentBriefs: any[],
  existingPerformance: any[],
  dateRange: string,
  metrics: string[],
  includeCompetitors: boolean
): Promise<PerformanceReport> {
  
  const analysisDate = new Date().toISOString()
  
  // Generate performance metrics for each content piece
  const contentMetrics: ContentMetrics[] = []
  
  for (const brief of contentBriefs) {
    const metrics = await generateContentMetrics(brief, business, dateRange)
    contentMetrics.push(metrics)
  }
  
  // Calculate aggregate metrics
  const totalContentPieces = contentMetrics.length
  const totalOrganicTraffic = contentMetrics.reduce((sum, c) => sum + c.organic_traffic, 0)
  const totalImpressions = contentMetrics.reduce((sum, c) => sum + c.impressions, 0)
  const totalClicks = contentMetrics.reduce((sum, c) => sum + c.clicks, 0)
  const overallCTR = totalImpressions > 0 ? (totalClicks / totalImpressions) * 100 : 0
  const averagePosition = contentMetrics.reduce((sum, c) => sum + c.average_position, 0) / totalContentPieces
  
  // Identify top and underperforming content
  const sortedByTraffic = [...contentMetrics].sort((a, b) => b.organic_traffic - a.organic_traffic)
  const topPerforming = sortedByTraffic.slice(0, 10)
  const underperforming = sortedByTraffic
    .filter(c => c.organic_traffic < totalOrganicTraffic / totalContentPieces * 0.5)
    .slice(0, 10)
  
  // Analyze content by type
  const contentByType = analyzeContentByType(contentMetrics)
  
  // Analyze keyword performance
  const keywordPerformance = analyzeKeywordPerformance(contentMetrics, existingPerformance)
  
  // Identify content gaps
  const contentGaps = identifyContentGaps(contentMetrics, business)
  
  // Find optimization opportunities
  const optimizationOpportunities = findOptimizationOpportunities(contentMetrics)
  
  // Generate recommendations
  const recommendations = generateAnalyticsRecommendations(
    contentMetrics,
    contentByType,
    optimizationOpportunities,
    business
  )

  return {
    analysis_date: analysisDate,
    date_range: dateRange,
    total_content_pieces: totalContentPieces,
    total_organic_traffic: Math.round(totalOrganicTraffic),
    average_position: Math.round(averagePosition * 10) / 10,
    total_impressions: Math.round(totalImpressions),
    total_clicks: Math.round(totalClicks),
    overall_ctr: Math.round(overallCTR * 100) / 100,
    top_performing_content: topPerforming,
    underperforming_content: underperforming,
    content_by_type: contentByType,
    keyword_performance: keywordPerformance,
    content_gaps: contentGaps,
    optimization_opportunities: optimizationOpportunities,
    recommendations: recommendations
  }
}

async function generateContentMetrics(brief: any, business: any, dateRange: string): Promise<ContentMetrics> {
  const baseUrl = business.website_url || 'https://example.com'
  const url = `${baseUrl}/blog/${brief.slug || brief.title.toLowerCase().replace(/\s+/g, '-')}`
  
  // Simulate realistic performance metrics
  const wordCount = brief.word_count_target || 1500
  const contentAge = Math.floor((Date.now() - new Date(brief.created_at).getTime()) / (1000 * 60 * 60 * 24))
  
  // Traffic simulation based on content quality factors
  let baseTraffic = 100
  if (brief.status === 'published') baseTraffic *= 3
  if (brief.content_type === 'howto') baseTraffic *= 1.5
  if (brief.content_type === 'comparison') baseTraffic *= 1.3
  if (wordCount > 2000) baseTraffic *= 1.2
  if (contentAge > 30) baseTraffic *= 1.4 // Aged content bonus
  
  const organicTraffic = Math.round(baseTraffic * (0.8 + Math.random() * 0.4))
  const impressions = Math.round(organicTraffic * (8 + Math.random() * 12))
  const clicks = Math.round(impressions * (0.02 + Math.random() * 0.08))
  const ctr = impressions > 0 ? (clicks / impressions) * 100 : 0
  
  // Position simulation
  const averagePosition = Math.max(1, Math.min(100, 
    15 + Math.random() * 30 - (brief.priority_score || 5)
  ))
  
  // Engagement metrics
  const bounceRate = Math.round((35 + Math.random() * 30) * 100) / 100
  const timeOnPage = Math.round((120 + Math.random() * 300) * 100) / 100
  const pagesPerSession = Math.round((1.2 + Math.random() * 1.8) * 100) / 100
  
  // Conversion metrics
  const conversions = Math.round(organicTraffic * (0.01 + Math.random() * 0.04))
  const conversionRate = organicTraffic > 0 ? (conversions / organicTraffic) * 100 : 0
  
  // Social and technical metrics
  const socialShares = Math.round(organicTraffic * (0.001 + Math.random() * 0.01))
  const backlinks = Math.round(Math.random() * 15) + 1
  const internalLinks = Math.round(Math.random() * 10) + 3
  const pageLoadSpeed = Math.round((1.5 + Math.random() * 2.5) * 100) / 100
  
  return {
    url,
    title: brief.title,
    content_type: brief.content_type,
    target_keyword: brief.target_keyword,
    publish_date: brief.created_at,
    word_count: wordCount,
    organic_traffic: organicTraffic,
    impressions,
    clicks,
    ctr: Math.round(ctr * 100) / 100,
    average_position: Math.round(averagePosition * 10) / 10,
    bounce_rate: bounceRate,
    time_on_page: timeOnPage,
    pages_per_session: pagesPerSession,
    conversions,
    conversion_rate: Math.round(conversionRate * 100) / 100,
    social_shares: socialShares,
    backlinks,
    internal_links: internalLinks,
    page_load_speed: pageLoadSpeed,
    core_web_vitals: {
      lcp: Math.round((1.5 + Math.random() * 2) * 1000) / 1000,
      inp: Math.round((100 + Math.random() * 200) * 10) / 10,
      cls: Math.round((0.05 + Math.random() * 0.15) * 1000) / 1000
    }
  }
}

function analyzeContentByType(contentMetrics: ContentMetrics[]): any[] {
  const typeMap = new Map<string, {
    count: number
    totalTraffic: number
    totalPosition: number
    totalConversions: number
  }>()
  
  for (const content of contentMetrics) {
    if (!typeMap.has(content.content_type)) {
      typeMap.set(content.content_type, {
        count: 0,
        totalTraffic: 0,
        totalPosition: 0,
        totalConversions: 0
      })
    }
    
    const typeData = typeMap.get(content.content_type)!
    typeData.count++
    typeData.totalTraffic += content.organic_traffic
    typeData.totalPosition += content.average_position
    typeData.totalConversions += content.conversions
  }
  
  return Array.from(typeMap.entries()).map(([type, data]) => ({
    type,
    count: data.count,
    avg_traffic: Math.round(data.totalTraffic / data.count),
    avg_position: Math.round((data.totalPosition / data.count) * 10) / 10,
    total_conversions: data.totalConversions
  })).sort((a, b) => b.avg_traffic - a.avg_traffic)
}

function analyzeKeywordPerformance(contentMetrics: ContentMetrics[], existingPerformance: any[]): any[] {
  const keywordMap = new Map<string, {
    contentPieces: number
    totalTraffic: number
    totalPosition: number
    previousTraffic: number
  }>()
  
  // Analyze current performance
  for (const content of contentMetrics) {
    const keyword = content.target_keyword
    if (!keywordMap.has(keyword)) {
      keywordMap.set(keyword, {
        contentPieces: 0,
        totalTraffic: 0,
        totalPosition: 0,
        previousTraffic: 0
      })
    }
    
    const keywordData = keywordMap.get(keyword)!
    keywordData.contentPieces++
    keywordData.totalTraffic += content.organic_traffic
    keywordData.totalPosition += content.average_position
  }
  
  // Add historical data for trend analysis
  for (const historical of existingPerformance) {
    if (keywordMap.has(historical.target_keyword)) {
      const keywordData = keywordMap.get(historical.target_keyword)!
      keywordData.previousTraffic += historical.organic_traffic || 0
    }
  }
  
  return Array.from(keywordMap.entries()).map(([keyword, data]) => {
    const avgPosition = data.totalPosition / data.contentPieces
    const trafficChange = data.previousTraffic > 0 ? 
      ((data.totalTraffic - data.previousTraffic) / data.previousTraffic) : 0
    
    let trend: 'improving' | 'declining' | 'stable' = 'stable'
    if (trafficChange > 0.1) trend = 'improving'
    else if (trafficChange < -0.1) trend = 'declining'
    
    return {
      keyword,
      content_pieces: data.contentPieces,
      total_traffic: data.totalTraffic,
      avg_position: Math.round(avgPosition * 10) / 10,
      trend
    }
  }).sort((a, b) => b.total_traffic - a.total_traffic)
}

function identifyContentGaps(contentMetrics: ContentMetrics[], business: any): any[] {
  // Simulate content gap analysis
  const industryGaps = getIndustryContentGaps(business.industry)
  
  const gaps = industryGaps.map(gap => ({
    ...gap,
    search_volume: 500 + Math.floor(Math.random() * 2000),
    competition: ['low', 'medium', 'high'][Math.floor(Math.random() * 3)],
    opportunity_score: Math.round((5 + Math.random() * 5) * 10) / 10
  }))
  
  return gaps.sort((a, b) => b.opportunity_score - a.opportunity_score).slice(0, 10)
}

function getIndustryContentGaps(industry: string): any[] {
  const gapMap: { [key: string]: string[] } = {
    restaurant: [
      'Menu nutrition information',
      'Allergen guides',
      'Private dining options',
      'Catering packages',
      'Seasonal menu highlights'
    ],
    legal: [
      'Legal process timelines',
      'Fee structure transparency',
      'Case study examples',
      'Legal document templates',
      'Client testimonials'
    ],
    healthcare: [
      'Treatment procedure guides',
      'Insurance coverage details',
      'Patient preparation instructions',
      'Recovery timeline expectations',
      'Specialist referral process'
    ],
    hvac: [
      'Energy efficiency guides',
      'Maintenance schedule templates',
      'Emergency repair procedures',
      'Equipment comparison guides',
      'Warranty information'
    ]
  }
  
  const industryKey = Object.keys(gapMap).find(key => 
    industry?.toLowerCase().includes(key)
  )
  
  const topics = gapMap[industryKey] || [
    'Service area coverage',
    'Pricing transparency',
    'Customer testimonials',
    'Process explanations',
    'FAQ sections'
  ]
  
  return topics.map(topic => ({ topic }))
}

function findOptimizationOpportunities(contentMetrics: ContentMetrics[]): any[] {
  const opportunities = []
  
  for (const content of contentMetrics) {
    const issues: string[] = []
    let priority: 'high' | 'medium' | 'low' = 'low'
    
    // Technical issues
    if (content.page_load_speed > 3) {
      issues.push('Slow page load speed')
      priority = 'high'
    }
    
    if (content.core_web_vitals.lcp > 2500) {
      issues.push('Poor Largest Contentful Paint')
      priority = 'high'
    }
    
    if (content.core_web_vitals.cls > 0.1) {
      issues.push('Layout shift issues')
      priority = priority === 'high' ? 'high' : 'medium'
    }
    
    // Content issues
    if (content.bounce_rate > 70) {
      issues.push('High bounce rate')
      priority = priority === 'high' ? 'high' : 'medium'
    }
    
    if (content.time_on_page < 60) {
      issues.push('Low time on page')
      priority = priority === 'high' ? 'high' : 'medium'
    }
    
    if (content.ctr < 2) {
      issues.push('Low click-through rate')
      priority = priority === 'high' ? 'high' : 'medium'
    }
    
    // SEO issues
    if (content.average_position > 10 && content.impressions > 1000) {
      issues.push('High impressions but poor position')
      priority = priority === 'high' ? 'high' : 'medium'
    }
    
    if (content.internal_links < 3) {
      issues.push('Insufficient internal linking')
      if (priority === 'low') priority = 'medium'
    }
    
    if (issues.length > 0) {
      opportunities.push({
        url: content.url,
        issues,
        potential_impact: generatePotentialImpact(issues, content),
        priority
      })
    }
  }
  
  return opportunities.sort((a, b) => {
    const priorityOrder = { high: 3, medium: 2, low: 1 }
    return priorityOrder[b.priority] - priorityOrder[a.priority]
  }).slice(0, 20)
}

function generatePotentialImpact(issues: string[], content: ContentMetrics): string {
  const highImpactIssues = [
    'Slow page load speed',
    'Poor Largest Contentful Paint',
    'High impressions but poor position'
  ]
  
  const hasHighImpactIssue = issues.some(issue => highImpactIssues.includes(issue))
  
  if (hasHighImpactIssue) {
    return `Could increase traffic by 25-40% (${Math.round(content.organic_traffic * 0.3)} additional visits/month)`
  } else if (issues.length > 2) {
    return `Could increase traffic by 15-25% (${Math.round(content.organic_traffic * 0.2)} additional visits/month)`
  } else {
    return `Could increase traffic by 5-15% (${Math.round(content.organic_traffic * 0.1)} additional visits/month)`
  }
}

function generateAnalyticsRecommendations(
  contentMetrics: ContentMetrics[],
  contentByType: any[],
  opportunities: any[],
  business: any
): any[] {
  const recommendations = []
  
  // High traffic content optimization
  const highTrafficContent = contentMetrics.filter(c => c.organic_traffic > 500)
  if (highTrafficContent.length > 0) {
    recommendations.push({
      title: 'Optimize High-Traffic Content',
      description: `${highTrafficContent.length} high-traffic pages could benefit from additional optimization to maximize their potential`,
      affected_pages: highTrafficContent.length,
      expected_impact: 'Could increase overall traffic by 20-30%',
      priority: 'high'
    })
  }
  
  // Underperforming content
  const underperforming = contentMetrics.filter(c => 
    c.organic_traffic < 50 && c.average_position > 20
  )
  if (underperforming.length > 0) {
    recommendations.push({
      title: 'Improve Underperforming Content',
      description: `${underperforming.length} pages are underperforming and need content updates, better targeting, or technical improvements`,
      affected_pages: underperforming.length,
      expected_impact: 'Could improve average position by 5-10 positions',
      priority: 'medium'
    })
  }
  
  // Technical optimization opportunities
  const technicalIssues = opportunities.filter(o => 
    o.issues.some((issue: string) => issue.includes('load speed') || issue.includes('Contentful Paint'))
  )
  if (technicalIssues.length > 0) {
    recommendations.push({
      title: 'Address Technical Performance Issues',
      description: `${technicalIssues.length} pages have technical performance issues affecting user experience and rankings`,
      affected_pages: technicalIssues.length,
      expected_impact: 'Could improve Core Web Vitals scores and rankings',
      priority: 'high'
    })
  }
  
  // Content type optimization
  const bestPerformingType = contentByType[0]
  if (bestPerformingType && contentByType.length > 1) {
    recommendations.push({
      title: `Focus on ${bestPerformingType.type} Content`,
      description: `${bestPerformingType.type} content performs best (avg. ${bestPerformingType.avg_traffic} traffic). Consider creating more of this type`,
      affected_pages: 0,
      expected_impact: 'Could improve content strategy ROI',
      priority: 'medium'
    })
  }
  
  // Internal linking opportunities
  const poorInternalLinking = contentMetrics.filter(c => c.internal_links < 3)
  if (poorInternalLinking.length > 0) {
    recommendations.push({
      title: 'Improve Internal Linking',
      description: `${poorInternalLinking.length} pages have insufficient internal links, missing opportunities for better page authority distribution`,
      affected_pages: poorInternalLinking.length,
      expected_impact: 'Could improve overall site authority',
      priority: 'medium'
    })
  }
  
  return recommendations
}