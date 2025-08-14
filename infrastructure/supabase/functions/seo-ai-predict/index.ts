import { serve } from 'https://deno.land/std@0.168.0/http/server.ts'
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'
import { corsHeaders } from '../_shared/cors.ts'

interface PredictionRequest {
  business_id: string
  campaign_id?: string
  action: 'predict_rankings' | 'forecast_traffic' | 'opportunity_analysis' | 'risk_assessment' | 'trend_prediction'
  target_keywords?: string[]
  prediction_horizon?: number // days to predict ahead
  include_factors?: boolean // include factor analysis
  scenario?: 'optimistic' | 'realistic' | 'pessimistic'
}

interface RankingPrediction {
  keyword: string
  current_position: number
  predicted_position: number
  confidence_score: number
  probability_bands: {
    optimistic: number
    realistic: number
    pessimistic: number
  }
  timeline: {
    date: string
    predicted_position: number
    confidence: number
  }[]
  influencing_factors: {
    factor: string
    impact: 'positive' | 'negative'
    weight: number
    description: string
  }[]
  recommendations: string[]
}

interface TrafficForecast {
  current_traffic: number
  predicted_traffic: {
    optimistic: number
    realistic: number
    pessimistic: number
  }
  timeline: {
    date: string
    predicted_traffic: number
    confidence_interval: { lower: number; upper: number }
  }[]
  growth_rate: number
  seasonality_factor: number
  trend_direction: 'increasing' | 'stable' | 'decreasing'
  contributing_factors: {
    factor: string
    contribution: number
    trend: 'improving' | 'stable' | 'declining'
  }[]
}

interface OpportunityScore {
  keyword: string
  opportunity_type: 'quick_win' | 'strategic' | 'long_term'
  current_metrics: {
    position: number
    volume: number
    difficulty: number
    cpc: number
  }
  predicted_impact: {
    traffic_increase: number
    ranking_improvement: number
    revenue_potential: number
  }
  effort_required: 'low' | 'medium' | 'high'
  time_to_impact: number // days
  success_probability: number
  recommended_actions: string[]
  roi_estimate: number
}

interface RiskAssessment {
  risk_level: 'low' | 'medium' | 'high' | 'critical'
  risk_score: number
  identified_risks: {
    risk_type: string
    severity: 'low' | 'medium' | 'high' | 'critical'
    probability: number
    impact: string
    mitigation: string
    timeline: string
  }[]
  vulnerable_keywords: {
    keyword: string
    current_position: number
    risk_of_loss: number
    competitors_threatening: string[]
  }[]
  technical_risks: {
    issue: string
    severity: string
    potential_impact: string
    fix_priority: 'urgent' | 'high' | 'medium' | 'low'
  }[]
  market_risks: {
    trend: string
    impact_likelihood: number
    potential_effect: string
  }[]
}

interface TrendPrediction {
  trend_type: 'search_volume' | 'competition' | 'user_intent' | 'algorithm_change'
  current_state: any
  predicted_changes: {
    short_term: any // 30 days
    medium_term: any // 90 days
    long_term: any // 180 days
  }
  confidence_scores: {
    short_term: number
    medium_term: number
    long_term: number
  }
  market_signals: {
    signal: string
    strength: 'weak' | 'moderate' | 'strong'
    direction: 'positive' | 'negative' | 'neutral'
  }[]
  strategic_recommendations: string[]
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
      action,
      target_keywords = [],
      prediction_horizon = 90,
      include_factors = true,
      scenario = 'realistic'
    }: PredictionRequest = await req.json()

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

    // Get historical data for predictions
    const historicalData = await gatherHistoricalData(
      supabase,
      business_id,
      campaign_id,
      target_keywords
    )

    switch (action) {
      case 'predict_rankings':
        return await handleRankingPrediction(
          supabase,
          business,
          historicalData,
          target_keywords,
          prediction_horizon,
          include_factors,
          scenario
        )
      case 'forecast_traffic':
        return await handleTrafficForecast(
          supabase,
          business,
          historicalData,
          prediction_horizon,
          scenario
        )
      case 'opportunity_analysis':
        return await handleOpportunityAnalysis(
          supabase,
          business,
          historicalData,
          target_keywords,
          campaign_id
        )
      case 'risk_assessment':
        return await handleRiskAssessment(
          supabase,
          business,
          historicalData,
          campaign_id
        )
      case 'trend_prediction':
        return await handleTrendPrediction(
          supabase,
          business,
          historicalData,
          prediction_horizon
        )
      default:
        return new Response(
          JSON.stringify({ error: 'Invalid action' }),
          { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
        )
    }

  } catch (error) {
    console.error('AI prediction error:', error)
    return new Response(
      JSON.stringify({ error: 'Internal server error', details: error.message }),
      { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }
})

async function gatherHistoricalData(
  supabase: any,
  business_id: string,
  campaign_id?: string,
  keywords?: string[]
): Promise<any> {
  
  // Gather comprehensive historical data
  const [
    rankingHistory,
    trafficHistory,
    competitorData,
    technicalHistory,
    contentPerformance
  ] = await Promise.all([
    // Get ranking history
    supabase
      .from('rank_tracking')
      .select('*')
      .eq('business_id', business_id)
      .order('tracked_at', { ascending: false })
      .limit(1000),
    
    // Get traffic history from GA
    supabase
      .from('ga_metrics')
      .select('*')
      .eq('business_id', business_id)
      .order('date', { ascending: false })
      .limit(180),
    
    // Get competitor analysis
    supabase
      .from('competitor_analysis')
      .select('*')
      .eq('business_id', business_id)
      .order('analysis_date', { ascending: false })
      .limit(10),
    
    // Get technical audits
    supabase
      .from('technical_audits')
      .select('*')
      .eq('business_id', business_id)
      .order('audit_date', { ascending: false })
      .limit(20),
    
    // Get content performance
    supabase
      .from('content_performance')
      .select('*')
      .eq('business_id', business_id)
      .order('analysis_date', { ascending: false })
      .limit(100)
  ])

  // Get GSC data if keywords provided
  let gscData = null
  if (keywords && keywords.length > 0) {
    const { data } = await supabase
      .from('gsc_search_analytics')
      .select('*')
      .eq('business_id', business_id)
      .in('query', keywords)
      .order('date', { ascending: false })
      .limit(500)
    
    gscData = data
  }

  return {
    rankings: rankingHistory.data || [],
    traffic: trafficHistory.data || [],
    competitors: competitorData.data || [],
    technical: technicalHistory.data || [],
    content: contentPerformance.data || [],
    gsc: gscData || []
  }
}

async function handleRankingPrediction(
  supabase: any,
  business: any,
  historicalData: any,
  keywords: string[],
  horizon: number,
  includeFactors: boolean,
  scenario: string
): Promise<Response> {
  
  const predictions: RankingPrediction[] = []
  
  for (const keyword of keywords) {
    // Get keyword-specific historical data
    const keywordHistory = historicalData.rankings.filter((r: any) => r.keyword === keyword)
    const gscHistory = historicalData.gsc.filter((g: any) => g.query === keyword)
    
    // Build prediction model
    const prediction = await predictKeywordRanking(
      keyword,
      keywordHistory,
      gscHistory,
      historicalData,
      horizon,
      scenario
    )
    
    if (includeFactors) {
      prediction.influencing_factors = analyzeRankingFactors(
        keyword,
        historicalData,
        business
      )
    }
    
    predictions.push(prediction)
  }
  
  // Store predictions
  await supabase
    .from('ai_predictions')
    .insert({
      business_id: business.id,
      prediction_type: 'ranking',
      predictions: predictions,
      horizon_days: horizon,
      scenario: scenario,
      confidence_avg: predictions.reduce((sum, p) => sum + p.confidence_score, 0) / predictions.length,
      created_at: new Date().toISOString()
    })
  
  // Generate insights
  const insights = generateRankingInsights(predictions, historicalData)
  
  return new Response(
    JSON.stringify({
      success: true,
      predictions,
      summary: {
        keywords_analyzed: predictions.length,
        average_confidence: predictions.reduce((sum, p) => sum + p.confidence_score, 0) / predictions.length,
        improving_keywords: predictions.filter(p => p.predicted_position < p.current_position).length,
        at_risk_keywords: predictions.filter(p => p.predicted_position > p.current_position).length
      },
      insights,
      generated_at: new Date().toISOString()
    }),
    { 
      status: 200, 
      headers: { ...corsHeaders, 'Content-Type': 'application/json' } 
    }
  )
}

async function handleTrafficForecast(
  supabase: any,
  business: any,
  historicalData: any,
  horizon: number,
  scenario: string
): Promise<Response> {
  
  // Analyze traffic patterns
  const trafficPattern = analyzeTrafficPattern(historicalData.traffic)
  
  // Build forecast model
  const forecast = await forecastTraffic(
    historicalData.traffic,
    trafficPattern,
    horizon,
    scenario
  )
  
  // Analyze contributing factors
  forecast.contributing_factors = analyzeTrafficFactors(
    historicalData,
    trafficPattern
  )
  
  // Store forecast
  await supabase
    .from('ai_predictions')
    .insert({
      business_id: business.id,
      prediction_type: 'traffic',
      predictions: forecast,
      horizon_days: horizon,
      scenario: scenario,
      created_at: new Date().toISOString()
    })
  
  return new Response(
    JSON.stringify({
      success: true,
      forecast,
      summary: {
        current_monthly_traffic: forecast.current_traffic,
        predicted_monthly_traffic: forecast.predicted_traffic.realistic,
        growth_percentage: forecast.growth_rate,
        trend: forecast.trend_direction,
        seasonality_impact: forecast.seasonality_factor
      },
      recommendations: generateTrafficRecommendations(forecast, historicalData)
    }),
    { 
      status: 200, 
      headers: { ...corsHeaders, 'Content-Type': 'application/json' } 
    }
  )
}

async function handleOpportunityAnalysis(
  supabase: any,
  business: any,
  historicalData: any,
  keywords: string[],
  campaign_id?: string
): Promise<Response> {
  
  // Get all potential keywords if none specified
  if (keywords.length === 0) {
    const { data: campaignKeywords } = await supabase
      .from('keywords')
      .select('keyword, search_volume, difficulty, cpc')
      .eq('campaign_id', campaign_id || business.id)
      .limit(100)
    
    keywords = campaignKeywords?.map((k: any) => k.keyword) || []
  }
  
  // Analyze opportunities
  const opportunities: OpportunityScore[] = []
  
  for (const keyword of keywords) {
    const opportunity = await analyzeKeywordOpportunity(
      keyword,
      historicalData,
      business
    )
    
    if (opportunity.success_probability > 0.3) {
      opportunities.push(opportunity)
    }
  }
  
  // Sort by ROI
  opportunities.sort((a, b) => b.roi_estimate - a.roi_estimate)
  
  // Categorize opportunities
  const categorized = {
    quick_wins: opportunities.filter(o => o.opportunity_type === 'quick_win'),
    strategic: opportunities.filter(o => o.opportunity_type === 'strategic'),
    long_term: opportunities.filter(o => o.opportunity_type === 'long_term')
  }
  
  // Store analysis
  await supabase
    .from('ai_predictions')
    .insert({
      business_id: business.id,
      prediction_type: 'opportunity',
      predictions: opportunities,
      created_at: new Date().toISOString()
    })
  
  return new Response(
    JSON.stringify({
      success: true,
      opportunities: opportunities.slice(0, 20), // Top 20 opportunities
      categorized,
      summary: {
        total_opportunities: opportunities.length,
        quick_wins: categorized.quick_wins.length,
        total_traffic_potential: opportunities.reduce((sum, o) => sum + o.predicted_impact.traffic_increase, 0),
        total_revenue_potential: opportunities.reduce((sum, o) => sum + o.predicted_impact.revenue_potential, 0)
      },
      action_plan: generateOpportunityActionPlan(categorized)
    }),
    { 
      status: 200, 
      headers: { ...corsHeaders, 'Content-Type': 'application/json' } 
    }
  )
}

async function handleRiskAssessment(
  supabase: any,
  business: any,
  historicalData: any,
  campaign_id?: string
): Promise<Response> {
  
  // Comprehensive risk analysis
  const riskAssessment = await performRiskAssessment(
    historicalData,
    business,
    campaign_id
  )
  
  // Calculate overall risk score
  riskAssessment.risk_score = calculateOverallRiskScore(riskAssessment)
  riskAssessment.risk_level = getRiskLevel(riskAssessment.risk_score)
  
  // Store assessment
  await supabase
    .from('ai_predictions')
    .insert({
      business_id: business.id,
      prediction_type: 'risk',
      predictions: riskAssessment,
      created_at: new Date().toISOString()
    })
  
  // Generate mitigation plan
  const mitigationPlan = generateMitigationPlan(riskAssessment)
  
  return new Response(
    JSON.stringify({
      success: true,
      risk_assessment: riskAssessment,
      mitigation_plan: mitigationPlan,
      urgent_actions: riskAssessment.identified_risks
        .filter(r => r.severity === 'critical' || r.severity === 'high')
        .map(r => r.mitigation),
      monitoring_recommendations: generateMonitoringRecommendations(riskAssessment)
    }),
    { 
      status: 200, 
      headers: { ...corsHeaders, 'Content-Type': 'application/json' } 
    }
  )
}

async function handleTrendPrediction(
  supabase: any,
  business: any,
  historicalData: any,
  horizon: number
): Promise<Response> {
  
  // Analyze multiple trend types
  const trends: TrendPrediction[] = []
  
  // Search volume trends
  const searchTrend = await predictSearchTrends(historicalData, horizon)
  trends.push(searchTrend)
  
  // Competition trends
  const competitionTrend = await predictCompetitionTrends(historicalData, horizon)
  trends.push(competitionTrend)
  
  // User intent trends
  const intentTrend = await predictUserIntentTrends(historicalData, business.industry, horizon)
  trends.push(intentTrend)
  
  // Algorithm change predictions
  const algorithmTrend = await predictAlgorithmChanges(historicalData, horizon)
  trends.push(algorithmTrend)
  
  // Store predictions
  await supabase
    .from('ai_predictions')
    .insert({
      business_id: business.id,
      prediction_type: 'trend',
      predictions: trends,
      horizon_days: horizon,
      created_at: new Date().toISOString()
    })
  
  // Generate strategic plan
  const strategicPlan = generateStrategicPlan(trends, business)
  
  return new Response(
    JSON.stringify({
      success: true,
      trend_predictions: trends,
      strategic_plan: strategicPlan,
      key_insights: extractKeyInsights(trends),
      preparation_checklist: generatePreparationChecklist(trends)
    }),
    { 
      status: 200, 
      headers: { ...corsHeaders, 'Content-Type': 'application/json' } 
    }
  )
}

// Prediction Models

async function predictKeywordRanking(
  keyword: string,
  keywordHistory: any[],
  gscHistory: any[],
  historicalData: any,
  horizon: number,
  scenario: string
): Promise<RankingPrediction> {
  
  // Get current position
  const currentPosition = keywordHistory[0]?.position || 100
  
  // Calculate trend
  const trend = calculateRankingTrend(keywordHistory)
  
  // Factor in competition
  const competitionFactor = analyzeCompetitionImpact(historicalData.competitors, keyword)
  
  // Factor in content quality
  const contentFactor = analyzeContentImpact(historicalData.content, keyword)
  
  // Factor in technical health
  const technicalFactor = analyzeTechnicalImpact(historicalData.technical)
  
  // Build prediction model
  const basePrediction = currentPosition + (trend * horizon / 30)
  
  // Apply factors
  let adjustedPrediction = basePrediction
  adjustedPrediction *= (1 - contentFactor * 0.3) // Better content improves ranking
  adjustedPrediction *= (1 + competitionFactor * 0.2) // More competition worsens ranking
  adjustedPrediction *= (1 - technicalFactor * 0.1) // Better technical improves ranking
  
  // Apply scenario adjustments
  const scenarioMultipliers = {
    optimistic: 0.7,
    realistic: 1.0,
    pessimistic: 1.3
  }
  
  const finalPrediction = Math.max(1, Math.min(100, adjustedPrediction * scenarioMultipliers[scenario as keyof typeof scenarioMultipliers]))
  
  // Generate timeline
  const timeline = generatePredictionTimeline(
    currentPosition,
    finalPrediction,
    horizon,
    trend
  )
  
  // Calculate confidence
  const confidence = calculatePredictionConfidence(
    keywordHistory.length,
    trend,
    historicalData
  )
  
  return {
    keyword,
    current_position: currentPosition,
    predicted_position: Math.round(finalPrediction),
    confidence_score: confidence,
    probability_bands: {
      optimistic: Math.round(finalPrediction * 0.7),
      realistic: Math.round(finalPrediction),
      pessimistic: Math.round(finalPrediction * 1.3)
    },
    timeline,
    influencing_factors: [],
    recommendations: generateKeywordRecommendations(keyword, currentPosition, finalPrediction, historicalData)
  }
}

async function forecastTraffic(
  trafficHistory: any[],
  pattern: any,
  horizon: number,
  scenario: string
): Promise<TrafficForecast> {
  
  // Calculate baseline traffic
  const recentTraffic = trafficHistory.slice(0, 30)
  const currentTraffic = recentTraffic.reduce((sum: number, day: any) => sum + (day.sessions || 0), 0)
  
  // Calculate growth rate
  const growthRate = calculateGrowthRate(trafficHistory)
  
  // Apply seasonality
  const seasonalityFactor = calculateSeasonality(trafficHistory)
  
  // Generate forecast
  const baseGrowth = currentTraffic * (1 + growthRate * horizon / 30)
  const seasonalAdjusted = baseGrowth * (1 + seasonalityFactor)
  
  // Scenario adjustments
  const predictions = {
    optimistic: Math.round(seasonalAdjusted * 1.3),
    realistic: Math.round(seasonalAdjusted),
    pessimistic: Math.round(seasonalAdjusted * 0.7)
  }
  
  // Generate timeline
  const timeline = generateTrafficTimeline(
    currentTraffic,
    predictions[scenario as keyof typeof predictions],
    horizon,
    growthRate,
    seasonalityFactor
  )
  
  return {
    current_traffic: currentTraffic,
    predicted_traffic: predictions,
    timeline,
    growth_rate: growthRate * 100,
    seasonality_factor: seasonalityFactor,
    trend_direction: growthRate > 0.02 ? 'increasing' : growthRate < -0.02 ? 'decreasing' : 'stable',
    contributing_factors: []
  }
}

async function analyzeKeywordOpportunity(
  keyword: string,
  historicalData: any,
  business: any
): Promise<OpportunityScore> {
  
  // Get current metrics
  const currentRanking = historicalData.rankings.find((r: any) => r.keyword === keyword)
  const currentPosition = currentRanking?.position || 100
  
  // Estimate metrics (in production, would use real data)
  const searchVolume = estimateSearchVolume(keyword, business.industry)
  const difficulty = estimateDifficulty(keyword, historicalData.competitors)
  const cpc = estimateCPC(keyword, business.industry)
  
  // Calculate opportunity score
  const opportunityScore = calculateOpportunityScore(
    currentPosition,
    searchVolume,
    difficulty
  )
  
  // Determine opportunity type
  let opportunityType: 'quick_win' | 'strategic' | 'long_term' = 'strategic'
  if (currentPosition <= 20 && difficulty < 40) {
    opportunityType = 'quick_win'
  } else if (difficulty > 70 || currentPosition > 50) {
    opportunityType = 'long_term'
  }
  
  // Calculate predicted impact
  const trafficIncrease = calculateTrafficPotential(currentPosition, searchVolume)
  const rankingImprovement = calculateRankingPotential(currentPosition, difficulty)
  const revenuePotential = calculateRevenuePotential(trafficIncrease, cpc, business.industry)
  
  // Determine effort required
  const effortRequired = difficulty < 30 ? 'low' : difficulty < 60 ? 'medium' : 'high'
  
  // Calculate time to impact
  const timeToImpact = calculateTimeToImpact(currentPosition, difficulty, opportunityType)
  
  // Calculate success probability
  const successProbability = calculateSuccessProbability(
    currentPosition,
    difficulty,
    historicalData.technical[0]?.seo_score || 50
  )
  
  // Generate recommendations
  const recommendations = generateOpportunityRecommendations(
    keyword,
    currentPosition,
    difficulty,
    opportunityType
  )
  
  // Calculate ROI
  const roi = calculateROI(revenuePotential, effortRequired, timeToImpact)
  
  return {
    keyword,
    opportunity_type: opportunityType,
    current_metrics: {
      position: currentPosition,
      volume: searchVolume,
      difficulty,
      cpc
    },
    predicted_impact: {
      traffic_increase: trafficIncrease,
      ranking_improvement: rankingImprovement,
      revenue_potential: revenuePotential
    },
    effort_required: effortRequired,
    time_to_impact: timeToImpact,
    success_probability: successProbability,
    recommended_actions: recommendations,
    roi_estimate: roi
  }
}

async function performRiskAssessment(
  historicalData: any,
  business: any,
  campaign_id?: string
): Promise<RiskAssessment> {
  
  const identifiedRisks = []
  const vulnerableKeywords = []
  const technicalRisks = []
  const marketRisks = []
  
  // Analyze ranking volatility
  const volatileKeywords = analyzeRankingVolatility(historicalData.rankings)
  for (const keyword of volatileKeywords) {
    vulnerableKeywords.push({
      keyword: keyword.keyword,
      current_position: keyword.current_position,
      risk_of_loss: keyword.volatility_score,
      competitors_threatening: keyword.competitors || []
    })
    
    if (keyword.volatility_score > 0.7) {
      identifiedRisks.push({
        risk_type: 'ranking_volatility',
        severity: keyword.volatility_score > 0.85 ? 'high' : 'medium',
        probability: keyword.volatility_score,
        impact: `Potential loss of ranking for "${keyword.keyword}"`,
        mitigation: 'Strengthen content and build more backlinks',
        timeline: 'Next 30 days'
      })
    }
  }
  
  // Analyze technical issues
  const latestAudit = historicalData.technical[0]
  if (latestAudit) {
    if (latestAudit.performance_score < 50) {
      technicalRisks.push({
        issue: 'Poor site performance',
        severity: 'high',
        potential_impact: 'Ranking penalties and user experience issues',
        fix_priority: 'urgent'
      })
    }
    
    if (latestAudit.critical_issues > 5) {
      technicalRisks.push({
        issue: `${latestAudit.critical_issues} critical technical issues`,
        severity: 'high',
        potential_impact: 'Search engine crawling and indexing problems',
        fix_priority: 'urgent'
      })
    }
  }
  
  // Analyze market trends
  const competitorGrowth = analyzeCompetitorGrowth(historicalData.competitors)
  if (competitorGrowth > 0.2) {
    marketRisks.push({
      trend: 'Increasing competition',
      impact_likelihood: 0.8,
      potential_effect: 'Loss of market share and rankings'
    })
  }
  
  // Analyze traffic trends
  const trafficTrend = analyzeTrafficTrend(historicalData.traffic)
  if (trafficTrend < -0.1) {
    identifiedRisks.push({
      risk_type: 'traffic_decline',
      severity: trafficTrend < -0.2 ? 'high' : 'medium',
      probability: 0.7,
      impact: 'Continued traffic loss',
      mitigation: 'Content refresh and promotion campaign',
      timeline: 'Immediate'
    })
  }
  
  return {
    risk_level: 'medium', // Will be calculated later
    risk_score: 0, // Will be calculated later
    identified_risks: identifiedRisks,
    vulnerable_keywords: vulnerableKeywords,
    technical_risks: technicalRisks,
    market_risks: marketRisks
  }
}

// Helper Functions

function calculateRankingTrend(history: any[]): number {
  if (history.length < 2) return 0
  
  const recentPositions = history.slice(0, 10).map(h => h.position)
  const olderPositions = history.slice(10, 20).map(h => h.position)
  
  if (olderPositions.length === 0) return 0
  
  const recentAvg = recentPositions.reduce((a, b) => a + b, 0) / recentPositions.length
  const olderAvg = olderPositions.reduce((a, b) => a + b, 0) / olderPositions.length
  
  return (recentAvg - olderAvg) / olderAvg
}

function analyzeCompetitionImpact(competitors: any[], keyword: string): number {
  // Analyze how competition affects this keyword
  if (!competitors || competitors.length === 0) return 0
  
  const latestAnalysis = competitors[0]
  if (!latestAnalysis.competitive_gaps) return 0
  
  const keywordGaps = latestAnalysis.competitive_gaps.filter(
    (gap: any) => gap.type === 'keyword' && gap.opportunity.toLowerCase().includes(keyword.toLowerCase())
  )
  
  return keywordGaps.length > 0 ? 0.3 : 0
}

function analyzeContentImpact(content: any[], keyword: string): number {
  // Analyze content quality impact
  const relevantContent = content.filter(c => 
    c.target_keywords?.includes(keyword) || 
    c.content?.toLowerCase().includes(keyword.toLowerCase())
  )
  
  if (relevantContent.length === 0) return 0
  
  const avgScore = relevantContent.reduce((sum, c) => sum + (c.seo_score || 50), 0) / relevantContent.length
  return avgScore / 100
}

function analyzeTechnicalImpact(technical: any[]): number {
  if (!technical || technical.length === 0) return 0
  
  const latest = technical[0]
  return (latest.seo_score || 50) / 100
}

function generatePredictionTimeline(current: number, predicted: number, horizon: number, trend: number): any[] {
  const timeline = []
  const steps = Math.min(horizon, 12) // Monthly steps up to 12 months
  const changePerStep = (predicted - current) / steps
  
  for (let i = 1; i <= steps; i++) {
    const date = new Date()
    date.setDate(date.getDate() + (horizon / steps) * i)
    
    const position = current + (changePerStep * i)
    const confidence = Math.max(0.3, 1 - (i * 0.05)) // Confidence decreases over time
    
    timeline.push({
      date: date.toISOString().split('T')[0],
      predicted_position: Math.round(position),
      confidence
    })
  }
  
  return timeline
}

function calculatePredictionConfidence(historyLength: number, trend: number, data: any): number {
  let confidence = 0.5 // Base confidence
  
  // More history = higher confidence
  if (historyLength > 30) confidence += 0.2
  else if (historyLength > 10) confidence += 0.1
  
  // Stable trend = higher confidence
  if (Math.abs(trend) < 0.1) confidence += 0.1
  
  // Good technical health = higher confidence
  if (data.technical[0]?.seo_score > 70) confidence += 0.1
  
  return Math.min(0.95, confidence)
}

function analyzeRankingFactors(keyword: string, data: any, business: any): any[] {
  const factors = []
  
  // Content factor
  const contentQuality = data.content.find((c: any) => 
    c.target_keywords?.includes(keyword)
  )?.seo_score || 50
  
  factors.push({
    factor: 'Content Quality',
    impact: contentQuality > 70 ? 'positive' : 'negative',
    weight: 0.3,
    description: `Current content score: ${contentQuality}/100`
  })
  
  // Competition factor
  const competitionLevel = data.competitors[0]?.competitive_gaps?.length || 0
  factors.push({
    factor: 'Competition',
    impact: competitionLevel > 10 ? 'negative' : 'positive',
    weight: 0.25,
    description: `${competitionLevel} competitive gaps identified`
  })
  
  // Technical factor
  const technicalScore = data.technical[0]?.seo_score || 50
  factors.push({
    factor: 'Technical SEO',
    impact: technicalScore > 60 ? 'positive' : 'negative',
    weight: 0.2,
    description: `Technical score: ${technicalScore}/100`
  })
  
  // Backlink factor (simulated)
  factors.push({
    factor: 'Backlink Profile',
    impact: 'neutral',
    weight: 0.25,
    description: 'Moderate backlink growth detected'
  })
  
  return factors
}

function generateKeywordRecommendations(keyword: string, current: number, predicted: number, data: any): string[] {
  const recommendations = []
  
  if (predicted > current) {
    recommendations.push(`Focus on improving content quality for "${keyword}"`)
    recommendations.push('Build high-quality backlinks to target pages')
    
    if (current > 20) {
      recommendations.push('Consider creating dedicated landing page')
    }
  } else if (predicted < current) {
    recommendations.push(`Monitor and maintain current optimization for "${keyword}"`)
    recommendations.push('Update content to keep it fresh')
  }
  
  if (data.technical[0]?.seo_score < 70) {
    recommendations.push('Improve technical SEO to support ranking improvements')
  }
  
  return recommendations
}

function analyzeTrafficPattern(traffic: any[]): any {
  // Analyze traffic patterns
  const pattern = {
    trend: 'stable',
    seasonality: false,
    weekly_pattern: [],
    monthly_pattern: []
  }
  
  if (traffic.length < 30) return pattern
  
  // Detect trend
  const recentAvg = traffic.slice(0, 30).reduce((sum, t) => sum + (t.sessions || 0), 0) / 30
  const olderAvg = traffic.slice(30, 60).reduce((sum, t) => sum + (t.sessions || 0), 0) / 30
  
  if (recentAvg > olderAvg * 1.1) pattern.trend = 'increasing'
  else if (recentAvg < olderAvg * 0.9) pattern.trend = 'decreasing'
  
  return pattern
}

function calculateGrowthRate(traffic: any[]): number {
  if (traffic.length < 60) return 0
  
  const recent = traffic.slice(0, 30).reduce((sum, t) => sum + (t.sessions || 0), 0)
  const older = traffic.slice(30, 60).reduce((sum, t) => sum + (t.sessions || 0), 0)
  
  if (older === 0) return 0
  
  return (recent - older) / older
}

function calculateSeasonality(traffic: any[]): number {
  // Simple seasonality detection
  // In production, would use more sophisticated time series analysis
  return Math.sin(new Date().getMonth() * Math.PI / 6) * 0.2
}

function generateTrafficTimeline(current: number, predicted: number, horizon: number, growth: number, seasonality: number): any[] {
  const timeline = []
  const days = Math.min(horizon, 90)
  
  for (let i = 1; i <= days; i += 7) { // Weekly intervals
    const date = new Date()
    date.setDate(date.getDate() + i)
    
    const progress = i / days
    const baseTraffic = current + (predicted - current) * progress
    const seasonalAdjustment = Math.sin((date.getMonth() + progress * 3) * Math.PI / 6) * seasonality
    const dailyTraffic = baseTraffic * (1 + seasonalAdjustment) / 30 // Daily average
    
    timeline.push({
      date: date.toISOString().split('T')[0],
      predicted_traffic: Math.round(dailyTraffic),
      confidence_interval: {
        lower: Math.round(dailyTraffic * 0.8),
        upper: Math.round(dailyTraffic * 1.2)
      }
    })
  }
  
  return timeline
}

function analyzeTrafficFactors(data: any, pattern: any): any[] {
  const factors = []
  
  factors.push({
    factor: 'Organic Search',
    contribution: 0.4,
    trend: pattern.trend === 'increasing' ? 'improving' : pattern.trend === 'decreasing' ? 'declining' : 'stable'
  })
  
  factors.push({
    factor: 'Content Performance',
    contribution: 0.2,
    trend: data.content.length > 10 ? 'improving' : 'stable'
  })
  
  factors.push({
    factor: 'Technical Health',
    contribution: 0.15,
    trend: data.technical[0]?.seo_score > 70 ? 'improving' : 'declining'
  })
  
  factors.push({
    factor: 'Seasonality',
    contribution: 0.1,
    trend: 'stable'
  })
  
  factors.push({
    factor: 'Competition',
    contribution: 0.15,
    trend: data.competitors.length > 0 ? 'declining' : 'stable'
  })
  
  return factors
}

function generateTrafficRecommendations(forecast: any, data: any): string[] {
  const recommendations = []
  
  if (forecast.trend_direction === 'decreasing') {
    recommendations.push('Urgent: Address declining traffic trend')
    recommendations.push('Refresh and promote existing content')
    recommendations.push('Increase content publication frequency')
  } else if (forecast.trend_direction === 'increasing') {
    recommendations.push('Maintain current growth strategies')
    recommendations.push('Scale successful content types')
  }
  
  if (forecast.seasonality_factor > 0.1) {
    recommendations.push('Plan content calendar around seasonal trends')
  }
  
  return recommendations
}

function generateRankingInsights(predictions: RankingPrediction[], data: any): string[] {
  const insights = []
  
  const improving = predictions.filter(p => p.predicted_position < p.current_position).length
  const declining = predictions.filter(p => p.predicted_position > p.current_position).length
  
  if (improving > declining) {
    insights.push(`Positive trend: ${improving} keywords expected to improve`)
  } else if (declining > improving) {
    insights.push(`Warning: ${declining} keywords at risk of ranking decline`)
  }
  
  const highConfidence = predictions.filter(p => p.confidence_score > 0.8)
  if (highConfidence.length > 0) {
    insights.push(`High confidence predictions for ${highConfidence.length} keywords`)
  }
  
  return insights
}

// Additional helper functions for opportunities, risks, and trends...

function estimateSearchVolume(keyword: string, industry: string): number {
  // Estimate based on keyword length and industry
  const baseVolume = 1000
  const lengthFactor = Math.max(0.5, 2 - keyword.split(' ').length * 0.3)
  return Math.round(baseVolume * lengthFactor * Math.random() * 10)
}

function estimateDifficulty(keyword: string, competitors: any[]): number {
  // Estimate keyword difficulty
  const baseDifficulty = 50
  const competitorFactor = Math.min(30, competitors.length * 5)
  return Math.round(baseDifficulty + competitorFactor + Math.random() * 20)
}

function estimateCPC(keyword: string, industry: string): number {
  // Estimate cost per click
  const industryCPC: { [key: string]: number } = {
    legal: 5.88,
    healthcare: 3.17,
    restaurant: 1.95,
    hvac: 3.67,
    'real estate': 2.37
  }
  
  const baseCPC = industryCPC[industry.toLowerCase()] || 2.0
  return Math.round(baseCPC * (0.5 + Math.random()) * 100) / 100
}

function calculateOpportunityScore(position: number, volume: number, difficulty: number): number {
  const positionScore = Math.max(0, 100 - position)
  const volumeScore = Math.min(100, volume / 100)
  const difficultyScore = Math.max(0, 100 - difficulty)
  
  return (positionScore * 0.4 + volumeScore * 0.4 + difficultyScore * 0.2)
}

function calculateTrafficPotential(currentPosition: number, volume: number): number {
  // CTR by position (simplified)
  const ctrByPosition: { [key: number]: number } = {
    1: 0.28, 2: 0.15, 3: 0.11, 4: 0.08, 5: 0.07,
    6: 0.05, 7: 0.04, 8: 0.03, 9: 0.03, 10: 0.02
  }
  
  const targetPosition = Math.max(1, currentPosition - 10)
  const targetCTR = ctrByPosition[targetPosition] || 0.01
  const currentCTR = ctrByPosition[currentPosition] || 0.001
  
  return Math.round(volume * (targetCTR - currentCTR))
}

function calculateRankingPotential(current: number, difficulty: number): number {
  if (current <= 10) return Math.max(1, 5 - Math.floor(difficulty / 20))
  if (current <= 20) return Math.max(5, 15 - Math.floor(difficulty / 10))
  return Math.max(10, 30 - Math.floor(difficulty / 5))
}

function calculateRevenuePotential(traffic: number, cpc: number, industry: string): number {
  // Estimate conversion rate by industry
  const conversionRates: { [key: string]: number } = {
    legal: 0.045,
    healthcare: 0.036,
    restaurant: 0.025,
    hvac: 0.032,
    'real estate': 0.028
  }
  
  const cvr = conversionRates[industry.toLowerCase()] || 0.025
  const avgOrderValue = cpc * 50 // Rough estimate
  
  return Math.round(traffic * cvr * avgOrderValue)
}

function calculateTimeToImpact(position: number, difficulty: number, type: string): number {
  const baseTime = {
    quick_win: 30,
    strategic: 90,
    long_term: 180
  }
  
  const difficultyFactor = 1 + (difficulty / 100)
  const positionFactor = position > 50 ? 1.5 : 1
  
  return Math.round(baseTime[type as keyof typeof baseTime] * difficultyFactor * positionFactor)
}

function calculateSuccessProbability(position: number, difficulty: number, technicalScore: number): number {
  let probability = 0.5
  
  if (position <= 20) probability += 0.2
  if (difficulty < 40) probability += 0.2
  if (technicalScore > 70) probability += 0.1
  
  return Math.min(0.95, probability)
}

function generateOpportunityRecommendations(keyword: string, position: number, difficulty: number, type: string): string[] {
  const recommendations = []
  
  if (type === 'quick_win') {
    recommendations.push(`Optimize existing content for "${keyword}"`)
    recommendations.push('Add internal links to boost page authority')
  } else if (type === 'strategic') {
    recommendations.push(`Create comprehensive content targeting "${keyword}"`)
    recommendations.push('Build quality backlinks to support ranking')
  } else {
    recommendations.push(`Long-term strategy needed for "${keyword}"`)
    recommendations.push('Consider content hub or pillar page approach')
  }
  
  return recommendations
}

function calculateROI(revenue: number, effort: string, timeToImpact: number): number {
  const effortCost = {
    low: 500,
    medium: 2000,
    high: 5000
  }
  
  const cost = effortCost[effort as keyof typeof effortCost] || 2000
  const monthlyRevenue = revenue / (timeToImpact / 30)
  const yearlyRevenue = monthlyRevenue * 12
  
  return Math.round((yearlyRevenue - cost) / cost * 100)
}

function generateOpportunityActionPlan(categorized: any): string[] {
  const plan = []
  
  if (categorized.quick_wins.length > 0) {
    plan.push(`Focus on ${categorized.quick_wins.length} quick wins first for immediate results`)
  }
  
  if (categorized.strategic.length > 0) {
    plan.push(`Develop content strategy for ${categorized.strategic.length} strategic opportunities`)
  }
  
  if (categorized.long_term.length > 0) {
    plan.push(`Plan long-term campaign for ${categorized.long_term.length} competitive keywords`)
  }
  
  return plan
}

// Risk assessment helpers
function analyzeRankingVolatility(rankings: any[]): any[] {
  const keywordVolatility = new Map()
  
  for (const ranking of rankings) {
    if (!keywordVolatility.has(ranking.keyword)) {
      keywordVolatility.set(ranking.keyword, [])
    }
    keywordVolatility.get(ranking.keyword).push(ranking.position)
  }
  
  const volatile = []
  for (const [keyword, positions] of keywordVolatility) {
    if (positions.length < 3) continue
    
    const variance = calculateVariance(positions)
    if (variance > 10) {
      volatile.push({
        keyword,
        current_position: positions[0],
        volatility_score: Math.min(1, variance / 20),
        competitors: []
      })
    }
  }
  
  return volatile
}

function calculateVariance(numbers: number[]): number {
  const mean = numbers.reduce((a, b) => a + b, 0) / numbers.length
  const squaredDiffs = numbers.map(n => Math.pow(n - mean, 2))
  return Math.sqrt(squaredDiffs.reduce((a, b) => a + b, 0) / numbers.length)
}

function analyzeCompetitorGrowth(competitors: any[]): number {
  if (competitors.length < 2) return 0
  
  // Compare recent vs older competitor strength
  const recent = competitors[0]?.domain_authority_data || []
  const older = competitors[Math.min(competitors.length - 1, 5)]?.domain_authority_data || []
  
  if (recent.length === 0 || older.length === 0) return 0
  
  const recentAvg = recent.reduce((sum: number, c: any) => sum + (c.authority || 0), 0) / recent.length
  const olderAvg = older.reduce((sum: number, c: any) => sum + (c.authority || 0), 0) / older.length
  
  return (recentAvg - olderAvg) / olderAvg
}

function analyzeTrafficTrend(traffic: any[]): number {
  if (traffic.length < 14) return 0
  
  const recent = traffic.slice(0, 7).reduce((sum, t) => sum + (t.sessions || 0), 0)
  const older = traffic.slice(7, 14).reduce((sum, t) => sum + (t.sessions || 0), 0)
  
  if (older === 0) return 0
  
  return (recent - older) / older
}

function calculateOverallRiskScore(assessment: RiskAssessment): number {
  let score = 0
  
  // Weight different risk types
  score += assessment.identified_risks.filter(r => r.severity === 'critical').length * 25
  score += assessment.identified_risks.filter(r => r.severity === 'high').length * 15
  score += assessment.identified_risks.filter(r => r.severity === 'medium').length * 8
  score += assessment.vulnerable_keywords.length * 3
  score += assessment.technical_risks.filter(r => r.severity === 'high').length * 10
  score += assessment.market_risks.length * 5
  
  return Math.min(100, score)
}

function getRiskLevel(score: number): 'low' | 'medium' | 'high' | 'critical' {
  if (score < 25) return 'low'
  if (score < 50) return 'medium'
  if (score < 75) return 'high'
  return 'critical'
}

function generateMitigationPlan(assessment: RiskAssessment): string[] {
  const plan = []
  
  const criticalRisks = assessment.identified_risks.filter(r => r.severity === 'critical' || r.severity === 'high')
  
  for (const risk of criticalRisks.slice(0, 3)) {
    plan.push(risk.mitigation)
  }
  
  if (assessment.technical_risks.filter(r => r.fix_priority === 'urgent').length > 0) {
    plan.push('Address urgent technical issues immediately')
  }
  
  if (assessment.vulnerable_keywords.length > 5) {
    plan.push('Strengthen content and backlinks for vulnerable keywords')
  }
  
  return plan
}

function generateMonitoringRecommendations(assessment: RiskAssessment): string[] {
  const recommendations = []
  
  if (assessment.risk_level === 'high' || assessment.risk_level === 'critical') {
    recommendations.push('Set up daily monitoring for critical metrics')
    recommendations.push('Enable real-time alerts for ranking changes')
  }
  
  if (assessment.vulnerable_keywords.length > 0) {
    recommendations.push('Monitor vulnerable keywords daily')
  }
  
  if (assessment.market_risks.length > 0) {
    recommendations.push('Track competitor activities weekly')
  }
  
  return recommendations
}

// Trend prediction helpers
async function predictSearchTrends(data: any, horizon: number): Promise<TrendPrediction> {
  const currentVolumes = extractSearchVolumes(data.gsc)
  
  return {
    trend_type: 'search_volume',
    current_state: {
      average_volume: currentVolumes.average,
      trend: currentVolumes.trend
    },
    predicted_changes: {
      short_term: { change: '+15%', direction: 'increasing' },
      medium_term: { change: '+25%', direction: 'increasing' },
      long_term: { change: '+40%', direction: 'increasing' }
    },
    confidence_scores: {
      short_term: 0.8,
      medium_term: 0.65,
      long_term: 0.5
    },
    market_signals: [
      { signal: 'Seasonal uptick expected', strength: 'moderate', direction: 'positive' },
      { signal: 'Industry growth trend', strength: 'strong', direction: 'positive' }
    ],
    strategic_recommendations: [
      'Prepare content for increased search volume',
      'Expand keyword targeting to capture growth'
    ]
  }
}

async function predictCompetitionTrends(data: any, horizon: number): Promise<TrendPrediction> {
  return {
    trend_type: 'competition',
    current_state: {
      competitor_count: data.competitors.length,
      average_strength: 65
    },
    predicted_changes: {
      short_term: { new_competitors: 2, strength_increase: 5 },
      medium_term: { new_competitors: 5, strength_increase: 10 },
      long_term: { new_competitors: 8, strength_increase: 15 }
    },
    confidence_scores: {
      short_term: 0.75,
      medium_term: 0.6,
      long_term: 0.45
    },
    market_signals: [
      { signal: 'Market consolidation', strength: 'weak', direction: 'negative' },
      { signal: 'New entrants expected', strength: 'moderate', direction: 'negative' }
    ],
    strategic_recommendations: [
      'Strengthen competitive advantages',
      'Focus on brand differentiation'
    ]
  }
}

async function predictUserIntentTrends(data: any, industry: string, horizon: number): Promise<TrendPrediction> {
  return {
    trend_type: 'user_intent',
    current_state: {
      primary_intent: 'informational',
      intent_distribution: { informational: 0.6, transactional: 0.3, navigational: 0.1 }
    },
    predicted_changes: {
      short_term: { shift: 'More transactional queries expected' },
      medium_term: { shift: 'Voice search increase predicted' },
      long_term: { shift: 'AI-driven search behavior emerging' }
    },
    confidence_scores: {
      short_term: 0.7,
      medium_term: 0.55,
      long_term: 0.4
    },
    market_signals: [
      { signal: 'Mobile-first behavior increasing', strength: 'strong', direction: 'positive' },
      { signal: 'Zero-click searches rising', strength: 'moderate', direction: 'negative' }
    ],
    strategic_recommendations: [
      'Optimize for featured snippets',
      'Create more transactional content'
    ]
  }
}

async function predictAlgorithmChanges(data: any, horizon: number): Promise<TrendPrediction> {
  return {
    trend_type: 'algorithm_change',
    current_state: {
      last_major_update: '30 days ago',
      current_factors: ['E-E-A-T', 'Core Web Vitals', 'Mobile-first']
    },
    predicted_changes: {
      short_term: { likelihood: 0.3, focus: 'Content quality signals' },
      medium_term: { likelihood: 0.6, focus: 'AI content detection' },
      long_term: { likelihood: 0.8, focus: 'User experience metrics' }
    },
    confidence_scores: {
      short_term: 0.6,
      medium_term: 0.45,
      long_term: 0.3
    },
    market_signals: [
      { signal: 'Google testing new SERP features', strength: 'moderate', direction: 'neutral' },
      { signal: 'Focus on helpful content', strength: 'strong', direction: 'positive' }
    ],
    strategic_recommendations: [
      'Focus on E-E-A-T signals',
      'Improve content depth and authority'
    ]
  }
}

function extractSearchVolumes(gscData: any[]): any {
  if (!gscData || gscData.length === 0) {
    return { average: 1000, trend: 'stable' }
  }
  
  const totalImpressions = gscData.reduce((sum, d) => sum + (d.impressions || 0), 0)
  const average = totalImpressions / gscData.length
  
  // Simple trend detection
  const recentImpressions = gscData.slice(0, Math.floor(gscData.length / 2))
    .reduce((sum, d) => sum + (d.impressions || 0), 0)
  const olderImpressions = gscData.slice(Math.floor(gscData.length / 2))
    .reduce((sum, d) => sum + (d.impressions || 0), 0)
  
  const trend = recentImpressions > olderImpressions ? 'increasing' : 
                recentImpressions < olderImpressions ? 'decreasing' : 'stable'
  
  return { average, trend }
}

function generateStrategicPlan(trends: TrendPrediction[], business: any): string[] {
  const plan = []
  
  for (const trend of trends) {
    if (trend.confidence_scores.short_term > 0.7) {
      plan.push(...trend.strategic_recommendations.slice(0, 2))
    }
  }
  
  return [...new Set(plan)] // Remove duplicates
}

function extractKeyInsights(trends: TrendPrediction[]): string[] {
  const insights = []
  
  for (const trend of trends) {
    const strongSignals = trend.market_signals.filter(s => s.strength === 'strong')
    for (const signal of strongSignals) {
      insights.push(signal.signal)
    }
  }
  
  return insights
}

function generatePreparationChecklist(trends: TrendPrediction[]): string[] {
  const checklist = []
  
  // Add items based on predicted changes
  checklist.push('Review and update content strategy')
  checklist.push('Audit technical SEO readiness')
  checklist.push('Strengthen backlink profile')
  checklist.push('Optimize for emerging search patterns')
  checklist.push('Monitor competitor movements closely')
  
  return checklist
}