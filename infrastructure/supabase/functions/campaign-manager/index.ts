import { serve } from 'https://deno.land/std@0.168.0/http/server.ts'
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'
import { corsHeaders } from '../_shared/cors.ts'

interface Campaign {
  id?: string
  business_id: string
  name: string
  description: string
  status: 'draft' | 'active' | 'paused' | 'completed'
  type: 'seo' | 'content' | 'link_building' | 'technical' | 'local' | 'multi_channel'
  goals: {
    target_rankings?: number
    target_traffic?: number
    target_conversions?: number
    target_revenue?: number
    timeline_days?: number
  }
  budget?: {
    total: number
    allocated: number
    spent: number
    currency: string
  }
  settings: {
    auto_optimize?: boolean
    alert_thresholds?: any
    reporting_frequency?: string
    team_members?: string[]
  }
  performance?: {
    current_rankings?: number
    traffic_gained?: number
    conversions?: number
    revenue?: number
    roi?: number
    completion_percentage?: number
  }
}

interface CampaignTask {
  id?: string
  campaign_id: string
  task_type: string
  status: 'pending' | 'in_progress' | 'completed' | 'failed'
  priority: 'low' | 'medium' | 'high' | 'critical'
  assigned_to?: string
  due_date?: string
  completed_at?: string
  details: any
  results?: any
}

interface CampaignKeyword {
  campaign_id: string
  keyword_id: string
  target_position?: number
  current_position?: number
  priority: number
  strategy?: string
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

    const { 
      action, 
      business_id, 
      user_id,
      campaign_id,
      campaign_data,
      filters,
      pagination
    } = await req.json()

    let result: any

    switch (action) {
      case 'list':
        result = await listCampaigns(supabase, business_id, filters, pagination)
        break
      
      case 'create':
        result = await createCampaign(supabase, business_id, campaign_data, user_id)
        break
      
      case 'update':
        result = await updateCampaign(supabase, campaign_id, campaign_data)
        break
      
      case 'delete':
        result = await deleteCampaign(supabase, campaign_id)
        break
      
      case 'details':
        result = await getCampaignDetails(supabase, campaign_id)
        break
      
      case 'tasks':
        result = await manageCampaignTasks(supabase, campaign_id, filters)
        break
      
      case 'keywords':
        result = await manageCampaignKeywords(supabase, campaign_id, filters)
        break
      
      case 'performance':
        result = await getCampaignPerformance(supabase, campaign_id)
        break
      
      case 'optimize':
        result = await optimizeCampaign(supabase, campaign_id)
        break
      
      default:
        throw new Error(`Unknown action: ${action}`)
    }

    return new Response(
      JSON.stringify(result),
      { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )

  } catch (error) {
    console.error('Campaign manager error:', error)
    return new Response(
      JSON.stringify({ error: error.message }),
      { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }
})

async function listCampaigns(
  supabase: any, 
  businessId: string, 
  filters?: any,
  pagination?: any
): Promise<Campaign[]> {
  
  let query = supabase
    .from('campaigns')
    .select(`
      *,
      campaign_keywords(count),
      campaign_tasks(count),
      campaign_content(count)
    `)
    .eq('business_id', businessId)

  // Apply filters
  if (filters?.status) {
    query = query.eq('status', filters.status)
  }
  if (filters?.type) {
    query = query.eq('type', filters.type)
  }
  if (filters?.date_from) {
    query = query.gte('created_at', filters.date_from)
  }
  if (filters?.date_to) {
    query = query.lte('created_at', filters.date_to)
  }

  // Apply pagination
  if (pagination) {
    const { page = 1, limit = 20 } = pagination
    const start = (page - 1) * limit
    query = query.range(start, start + limit - 1)
  }

  const { data, error } = await query

  if (error) throw error

  // Calculate performance metrics for each campaign
  const campaignsWithPerformance = await Promise.all(
    data.map(async (campaign: any) => {
      const performance = await calculateCampaignPerformance(supabase, campaign.id)
      return {
        ...campaign,
        performance,
        keyword_count: campaign.campaign_keywords[0]?.count || 0,
        task_count: campaign.campaign_tasks[0]?.count || 0,
        content_count: campaign.campaign_content[0]?.count || 0
      }
    })
  )

  return campaignsWithPerformance
}

async function createCampaign(
  supabase: any,
  businessId: string,
  campaignData: Campaign,
  userId: string
): Promise<Campaign> {
  
  // Create campaign
  const { data: campaign, error: campaignError } = await supabase
    .from('campaigns')
    .insert({
      business_id: businessId,
      name: campaignData.name,
      description: campaignData.description,
      status: campaignData.status || 'draft',
      type: campaignData.type,
      goals: campaignData.goals,
      budget: campaignData.budget,
      settings: campaignData.settings,
      created_by: userId,
      created_at: new Date().toISOString()
    })
    .select()
    .single()

  if (campaignError) throw campaignError

  // Create initial tasks based on campaign type
  const initialTasks = await createInitialTasks(supabase, campaign.id, campaignData.type)

  // Set up monitoring if active
  if (campaign.status === 'active') {
    await setupCampaignMonitoring(supabase, campaign.id, campaignData.settings)
  }

  // Log activity
  await supabase
    .from('activity_logs')
    .insert({
      business_id: businessId,
      user_id: userId,
      action: 'campaign_created',
      resource_type: 'campaign',
      resource_id: campaign.id,
      details: { campaign_name: campaign.name },
      created_at: new Date().toISOString()
    })

  return {
    ...campaign,
    tasks: initialTasks
  }
}

async function updateCampaign(
  supabase: any,
  campaignId: string,
  updates: Partial<Campaign>
): Promise<Campaign> {
  
  const { data, error } = await supabase
    .from('campaigns')
    .update({
      ...updates,
      updated_at: new Date().toISOString()
    })
    .eq('id', campaignId)
    .select()
    .single()

  if (error) throw error

  // Update monitoring if status changed
  if (updates.status) {
    if (updates.status === 'active') {
      await setupCampaignMonitoring(supabase, campaignId, data.settings)
    } else if (updates.status === 'paused' || updates.status === 'completed') {
      await pauseCampaignMonitoring(supabase, campaignId)
    }
  }

  return data
}

async function deleteCampaign(
  supabase: any,
  campaignId: string
): Promise<{ success: boolean }> {
  
  // Soft delete - mark as deleted
  const { error } = await supabase
    .from('campaigns')
    .update({
      status: 'deleted',
      deleted_at: new Date().toISOString()
    })
    .eq('id', campaignId)

  if (error) throw error

  // Pause all monitoring
  await pauseCampaignMonitoring(supabase, campaignId)

  return { success: true }
}

async function getCampaignDetails(
  supabase: any,
  campaignId: string
): Promise<any> {
  
  // Get campaign with all related data
  const { data: campaign, error } = await supabase
    .from('campaigns')
    .select(`
      *,
      campaign_keywords(
        *,
        keywords(*)
      ),
      campaign_tasks(*),
      campaign_content(
        *,
        content_briefs(*)
      ),
      campaign_competitors(
        *,
        competitors(*)
      )
    `)
    .eq('id', campaignId)
    .single()

  if (error) throw error

  // Get performance metrics
  const performance = await calculateCampaignPerformance(supabase, campaignId)

  // Get activity timeline
  const { data: activities } = await supabase
    .from('activity_logs')
    .select('*')
    .eq('resource_type', 'campaign')
    .eq('resource_id', campaignId)
    .order('created_at', { ascending: false })
    .limit(50)

  // Get team members
  const teamMembers = await getCampaignTeamMembers(supabase, campaignId, campaign.settings?.team_members)

  return {
    ...campaign,
    performance,
    activities,
    team_members: teamMembers,
    statistics: {
      total_keywords: campaign.campaign_keywords?.length || 0,
      active_tasks: campaign.campaign_tasks?.filter((t: any) => t.status === 'in_progress').length || 0,
      completed_tasks: campaign.campaign_tasks?.filter((t: any) => t.status === 'completed').length || 0,
      content_pieces: campaign.campaign_content?.length || 0
    }
  }
}

async function manageCampaignTasks(
  supabase: any,
  campaignId: string,
  filters?: any
): Promise<CampaignTask[]> {
  
  let query = supabase
    .from('campaign_tasks')
    .select('*')
    .eq('campaign_id', campaignId)

  if (filters?.status) {
    query = query.eq('status', filters.status)
  }
  if (filters?.priority) {
    query = query.eq('priority', filters.priority)
  }
  if (filters?.assigned_to) {
    query = query.eq('assigned_to', filters.assigned_to)
  }

  query = query.order('priority', { ascending: false })
    .order('due_date', { ascending: true })

  const { data, error } = await query

  if (error) throw error

  return data
}

async function manageCampaignKeywords(
  supabase: any,
  campaignId: string,
  filters?: any
): Promise<any[]> {
  
  let query = supabase
    .from('campaign_keywords')
    .select(`
      *,
      keywords(
        *,
        keyword_rankings(
          position,
          search_volume,
          created_at
        )
      )
    `)
    .eq('campaign_id', campaignId)

  if (filters?.priority) {
    query = query.eq('priority', filters.priority)
  }

  query = query.order('priority', { ascending: false })

  const { data, error } = await query

  if (error) throw error

  // Calculate progress for each keyword
  const keywordsWithProgress = data.map((ck: any) => {
    const latestRanking = ck.keywords?.keyword_rankings?.[0]
    const progress = calculateKeywordProgress(
      ck.target_position,
      latestRanking?.position
    )

    return {
      ...ck,
      current_position: latestRanking?.position,
      progress,
      trend: calculateKeywordTrend(ck.keywords?.keyword_rankings)
    }
  })

  return keywordsWithProgress
}

async function getCampaignPerformance(
  supabase: any,
  campaignId: string
): Promise<any> {
  
  const performance = await calculateCampaignPerformance(supabase, campaignId)
  
  // Get historical data for charts
  const historicalData = await getHistoricalPerformance(supabase, campaignId)
  
  // Get ROI calculation
  const roi = await calculateCampaignROI(supabase, campaignId)
  
  // Get competitor comparison
  const competitorComparison = await getCompetitorComparison(supabase, campaignId)

  return {
    current: performance,
    historical: historicalData,
    roi,
    competitor_comparison: competitorComparison,
    recommendations: await generatePerformanceRecommendations(performance)
  }
}

async function optimizeCampaign(
  supabase: any,
  campaignId: string
): Promise<any> {
  
  // Analyze current performance
  const performance = await calculateCampaignPerformance(supabase, campaignId)
  
  // Generate optimization recommendations
  const recommendations = []

  // Check keyword performance
  const { data: keywords } = await supabase
    .from('campaign_keywords')
    .select(`
      *,
      keywords(
        *,
        keyword_rankings(*)
      )
    `)
    .eq('campaign_id', campaignId)

  // Identify underperforming keywords
  const underperformingKeywords = keywords.filter((k: any) => {
    const currentPos = k.keywords?.keyword_rankings?.[0]?.position || 100
    return k.target_position && currentPos > k.target_position * 1.5
  })

  if (underperformingKeywords.length > 0) {
    recommendations.push({
      type: 'keywords',
      priority: 'high',
      action: 'optimize_content',
      details: `${underperformingKeywords.length} keywords need content optimization`,
      keywords: underperformingKeywords.map((k: any) => k.keywords.keyword)
    })
  }

  // Check content freshness
  const { data: content } = await supabase
    .from('campaign_content')
    .select('*')
    .eq('campaign_id', campaignId)
    .lt('updated_at', new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString())

  if (content.length > 0) {
    recommendations.push({
      type: 'content',
      priority: 'medium',
      action: 'update_content',
      details: `${content.length} content pieces need updating`,
      content_ids: content.map((c: any) => c.id)
    })
  }

  // Check budget utilization
  const { data: campaign } = await supabase
    .from('campaigns')
    .select('budget')
    .eq('id', campaignId)
    .single()

  if (campaign?.budget) {
    const utilizationRate = (campaign.budget.spent / campaign.budget.allocated) * 100
    if (utilizationRate < 50) {
      recommendations.push({
        type: 'budget',
        priority: 'low',
        action: 'increase_spending',
        details: `Only ${utilizationRate.toFixed(1)}% of budget utilized`,
        suggestion: 'Consider increasing content production or paid promotion'
      })
    }
  }

  // Apply automatic optimizations if enabled
  const { data: settings } = await supabase
    .from('campaigns')
    .select('settings')
    .eq('id', campaignId)
    .single()

  if (settings?.settings?.auto_optimize) {
    // Apply optimizations
    for (const rec of recommendations) {
      if (rec.priority === 'high') {
        await applyOptimization(supabase, campaignId, rec)
      }
    }
  }

  return {
    recommendations,
    auto_applied: settings?.settings?.auto_optimize ? 
      recommendations.filter(r => r.priority === 'high') : [],
    performance_impact: await estimateOptimizationImpact(recommendations)
  }
}

// Helper functions

async function calculateCampaignPerformance(
  supabase: any,
  campaignId: string
): Promise<any> {
  
  // Get campaign goals
  const { data: campaign } = await supabase
    .from('campaigns')
    .select('goals, created_at')
    .eq('id', campaignId)
    .single()

  // Get keyword rankings
  const { data: keywords } = await supabase
    .from('campaign_keywords')
    .select(`
      target_position,
      keywords(
        keyword_rankings(position)
      )
    `)
    .eq('campaign_id', campaignId)

  // Calculate average position and improvement
  let totalPosition = 0
  let rankedKeywords = 0
  let targetsMet = 0

  keywords?.forEach((k: any) => {
    const currentPos = k.keywords?.keyword_rankings?.[0]?.position
    if (currentPos) {
      totalPosition += currentPos
      rankedKeywords++
      if (k.target_position && currentPos <= k.target_position) {
        targetsMet++
      }
    }
  })

  const avgPosition = rankedKeywords > 0 ? totalPosition / rankedKeywords : 0

  // Get traffic data (would integrate with GA)
  const trafficGained = Math.floor(Math.random() * 10000) // Placeholder

  // Get conversion data
  const conversions = Math.floor(Math.random() * 100) // Placeholder
  const revenue = Math.floor(Math.random() * 50000) // Placeholder

  // Calculate completion percentage
  const daysElapsed = Math.floor(
    (Date.now() - new Date(campaign.created_at).getTime()) / (1000 * 60 * 60 * 24)
  )
  const timelineProgress = campaign.goals?.timeline_days ? 
    (daysElapsed / campaign.goals.timeline_days) * 100 : 0

  const goalsProgress = []
  if (campaign.goals?.target_rankings) {
    goalsProgress.push((avgPosition / campaign.goals.target_rankings) * 100)
  }
  if (campaign.goals?.target_traffic) {
    goalsProgress.push((trafficGained / campaign.goals.target_traffic) * 100)
  }
  if (campaign.goals?.target_conversions) {
    goalsProgress.push((conversions / campaign.goals.target_conversions) * 100)
  }

  const completionPercentage = goalsProgress.length > 0 ?
    goalsProgress.reduce((a, b) => a + b, 0) / goalsProgress.length : 0

  return {
    current_rankings: avgPosition,
    traffic_gained: trafficGained,
    conversions,
    revenue,
    roi: revenue > 0 ? ((revenue - 10000) / 10000) * 100 : 0, // Placeholder calculation
    completion_percentage: Math.min(completionPercentage, 100),
    targets_met: targetsMet,
    total_targets: keywords?.length || 0,
    days_elapsed: daysElapsed,
    timeline_progress: Math.min(timelineProgress, 100)
  }
}

async function createInitialTasks(
  supabase: any,
  campaignId: string,
  campaignType: string
): Promise<CampaignTask[]> {
  
  const taskTemplates: Record<string, CampaignTask[]> = {
    seo: [
      {
        campaign_id: campaignId,
        task_type: 'keyword_research',
        status: 'pending',
        priority: 'high',
        details: { description: 'Conduct comprehensive keyword research' }
      },
      {
        campaign_id: campaignId,
        task_type: 'competitor_analysis',
        status: 'pending',
        priority: 'high',
        details: { description: 'Analyze top 5 competitors' }
      },
      {
        campaign_id: campaignId,
        task_type: 'technical_audit',
        status: 'pending',
        priority: 'medium',
        details: { description: 'Run full technical SEO audit' }
      },
      {
        campaign_id: campaignId,
        task_type: 'content_strategy',
        status: 'pending',
        priority: 'medium',
        details: { description: 'Develop content strategy and calendar' }
      }
    ],
    content: [
      {
        campaign_id: campaignId,
        task_type: 'content_audit',
        status: 'pending',
        priority: 'high',
        details: { description: 'Audit existing content' }
      },
      {
        campaign_id: campaignId,
        task_type: 'topic_research',
        status: 'pending',
        priority: 'high',
        details: { description: 'Research content topics and gaps' }
      },
      {
        campaign_id: campaignId,
        task_type: 'content_calendar',
        status: 'pending',
        priority: 'medium',
        details: { description: 'Create content publishing calendar' }
      }
    ],
    link_building: [
      {
        campaign_id: campaignId,
        task_type: 'backlink_audit',
        status: 'pending',
        priority: 'high',
        details: { description: 'Audit current backlink profile' }
      },
      {
        campaign_id: campaignId,
        task_type: 'prospect_research',
        status: 'pending',
        priority: 'high',
        details: { description: 'Research link building prospects' }
      },
      {
        campaign_id: campaignId,
        task_type: 'outreach_strategy',
        status: 'pending',
        priority: 'medium',
        details: { description: 'Develop outreach strategy and templates' }
      }
    ]
  }

  const tasks = taskTemplates[campaignType] || taskTemplates.seo

  const { data, error } = await supabase
    .from('campaign_tasks')
    .insert(tasks)
    .select()

  if (error) throw error

  return data
}

async function setupCampaignMonitoring(
  supabase: any,
  campaignId: string,
  settings: any
): Promise<void> {
  
  // Set up automated monitoring tasks
  const monitoringTasks = [
    {
      campaign_id: campaignId,
      task_type: 'monitor_rankings',
      schedule: 'daily',
      config: {
        alert_threshold: settings?.alert_thresholds?.ranking_drop || 5
      }
    },
    {
      campaign_id: campaignId,
      task_type: 'monitor_traffic',
      schedule: 'weekly',
      config: {
        alert_threshold: settings?.alert_thresholds?.traffic_drop || 20
      }
    },
    {
      campaign_id: campaignId,
      task_type: 'monitor_competitors',
      schedule: 'weekly',
      config: {}
    }
  ]

  // Schedule monitoring tasks
  for (const task of monitoringTasks) {
    await supabase
      .from('scheduled_tasks')
      .insert({
        business_id: campaignId, // Using campaign_id as reference
        task_type: task.task_type,
        schedule: task.schedule,
        config: task.config,
        status: 'active',
        created_at: new Date().toISOString()
      })
  }
}

async function pauseCampaignMonitoring(
  supabase: any,
  campaignId: string
): Promise<void> {
  
  await supabase
    .from('scheduled_tasks')
    .update({ status: 'paused' })
    .eq('business_id', campaignId) // Using campaign_id as reference
}

async function getCampaignTeamMembers(
  supabase: any,
  campaignId: string,
  memberIds?: string[]
): Promise<any[]> {
  
  if (!memberIds || memberIds.length === 0) {
    return []
  }

  const { data } = await supabase
    .from('users')
    .select('id, email, full_name, role')
    .in('id', memberIds)

  return data || []
}

async function calculateKeywordProgress(
  targetPosition?: number,
  currentPosition?: number
): number {
  if (!targetPosition || !currentPosition) return 0
  
  if (currentPosition <= targetPosition) return 100
  
  const progress = ((100 - currentPosition) / (100 - targetPosition)) * 100
  return Math.max(0, Math.min(100, progress))
}

async function calculateKeywordTrend(rankings: any[]): string {
  if (!rankings || rankings.length < 2) return 'stable'
  
  const recent = rankings[0].position
  const previous = rankings[1].position
  
  if (recent < previous) return 'improving'
  if (recent > previous) return 'declining'
  return 'stable'
}

async function getHistoricalPerformance(
  supabase: any,
  campaignId: string
): Promise<any> {
  // This would fetch historical data from analytics
  // Placeholder implementation
  return {
    rankings: [],
    traffic: [],
    conversions: []
  }
}

async function calculateCampaignROI(
  supabase: any,
  campaignId: string
): Promise<any> {
  // Calculate actual ROI based on budget and revenue
  // Placeholder implementation
  return {
    investment: 10000,
    revenue: 25000,
    roi_percentage: 150,
    payback_period_days: 45
  }
}

async function getCompetitorComparison(
  supabase: any,
  campaignId: string
): Promise<any> {
  // Compare campaign performance with competitors
  // Placeholder implementation
  return {
    ranking_comparison: 'above_average',
    traffic_share: 25,
    visibility_score: 75
  }
}

async function generatePerformanceRecommendations(
  performance: any
): Promise<string[]> {
  const recommendations = []
  
  if (performance.current_rankings > 20) {
    recommendations.push('Focus on improving content quality for top keywords')
  }
  
  if (performance.completion_percentage < 50) {
    recommendations.push('Increase campaign activity to meet timeline goals')
  }
  
  if (performance.roi < 100) {
    recommendations.push('Review budget allocation and optimize spending')
  }
  
  return recommendations
}

async function applyOptimization(
  supabase: any,
  campaignId: string,
  recommendation: any
): Promise<void> {
  // Apply automatic optimizations based on recommendation type
  switch (recommendation.type) {
    case 'keywords':
      // Create content optimization tasks
      for (const keyword of recommendation.keywords) {
        await supabase
          .from('campaign_tasks')
          .insert({
            campaign_id: campaignId,
            task_type: 'optimize_content',
            status: 'pending',
            priority: 'high',
            details: {
              keyword,
              action: 'Optimize content for better ranking'
            },
            created_at: new Date().toISOString()
          })
      }
      break
    
    case 'content':
      // Schedule content updates
      for (const contentId of recommendation.content_ids) {
        await supabase
          .from('campaign_tasks')
          .insert({
            campaign_id: campaignId,
            task_type: 'update_content',
            status: 'pending',
            priority: 'medium',
            details: {
              content_id: contentId,
              action: 'Update and refresh content'
            },
            created_at: new Date().toISOString()
          })
      }
      break
  }
}

async function estimateOptimizationImpact(
  recommendations: any[]
): Promise<any> {
  // Estimate the potential impact of optimizations
  let estimatedRankingImprovement = 0
  let estimatedTrafficIncrease = 0
  
  recommendations.forEach(rec => {
    switch (rec.type) {
      case 'keywords':
        estimatedRankingImprovement += 5
        estimatedTrafficIncrease += 15
        break
      case 'content':
        estimatedRankingImprovement += 3
        estimatedTrafficIncrease += 10
        break
      case 'budget':
        estimatedTrafficIncrease += 20
        break
    }
  })
  
  return {
    ranking_improvement: estimatedRankingImprovement,
    traffic_increase: estimatedTrafficIncrease,
    confidence: 'medium'
  }
}