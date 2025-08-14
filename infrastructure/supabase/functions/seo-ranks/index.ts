import { serve } from 'https://deno.land/std@0.168.0/http/server.ts'
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'
import { corsHeaders } from '../_shared/cors.ts'

interface RankTrackingRequest {
  business_id: string
  campaign_id?: string
  keywords?: string[]
  location?: string
  device?: 'desktop' | 'mobile'
  search_engine?: 'google' | 'bing' | 'yahoo'
  tracking_frequency?: 'daily' | 'weekly' | 'monthly'
}

interface KeywordRanking {
  keyword: string
  current_position: number
  previous_position?: number
  change: number
  url: string
  search_volume: number
  difficulty: number
  intent: string
  serp_features: string[]
  competitor_positions: {
    domain: string
    position: number
    url: string
  }[]
  local_pack_position?: number
  featured_snippet: boolean
}

interface RankingReport {
  tracking_date: string
  total_keywords: number
  average_position: number
  position_changes: {
    improved: number
    declined: number
    unchanged: number
  }
  visibility_score: number
  keyword_rankings: KeywordRanking[]
  top_performers: KeywordRanking[]
  biggest_movers: {
    gainers: KeywordRanking[]
    losers: KeywordRanking[]
  }
  serp_features_found: {
    feature: string
    count: number
    keywords: string[]
  }[]
  competitor_analysis: {
    domain: string
    average_position: number
    keywords_ranking: number
    visibility_share: number
  }[]
  recommendations: {
    title: string
    description: string
    keywords_affected: string[]
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
      keywords = [],
      location = 'United States',
      device = 'desktop',
      search_engine = 'google',
      tracking_frequency = 'weekly'
    }: RankTrackingRequest = await req.json()

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
      .select('business_name, industry, website_url, city, state')
      .eq('id', business_id)
      .single()

    if (!business) {
      return new Response(
        JSON.stringify({ error: 'Business not found' }),
        { status: 404, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    // Get keywords to track
    let keywordsToTrack: any[] = []
    
    if (campaign_id) {
      const { data: campaignKeywords } = await supabase
        .from('keywords')
        .select('keyword, intent, search_volume, keyword_difficulty, current_position')
        .eq('campaign_id', campaign_id)
        .order('value_score', { ascending: false })
        .limit(100)
      
      keywordsToTrack = campaignKeywords || []
    } else if (keywords.length > 0) {
      // Create keyword objects from provided list
      keywordsToTrack = keywords.map(keyword => ({
        keyword,
        intent: 'commercial',
        search_volume: 1000,
        keyword_difficulty: 50,
        current_position: null
      }))
    } else {
      return new Response(
        JSON.stringify({ error: 'Either campaign_id or keywords array is required' }),
        { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    // Get previous rankings for comparison
    const { data: previousRankings } = await supabase
      .from('rank_tracking')
      .select('keyword, position, tracked_at')
      .eq('business_id', business_id)
      .gte('tracked_at', new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString())
      .order('tracked_at', { ascending: false })

    // Perform rank tracking
    const rankingReport = await performRankTracking(
      keywordsToTrack,
      business,
      location,
      device,
      search_engine,
      previousRankings || []
    )

    // Store ranking data
    const rankingRecords = []
    for (const ranking of rankingReport.keyword_rankings) {
      const { data: rankRecord } = await supabase
        .from('rank_tracking')
        .insert({
          business_id,
          campaign_id,
          keyword: ranking.keyword,
          position: ranking.current_position,
          previous_position: ranking.previous_position,
          change: ranking.change,
          url: ranking.url,
          search_engine,
          device,
          location,
          serp_features: ranking.serp_features,
          competitor_data: ranking.competitor_positions,
          local_pack_position: ranking.local_pack_position,
          featured_snippet: ranking.featured_snippet,
          tracked_at: new Date().toISOString()
        })
        .select()
        .single()

      if (rankRecord) {
        rankingRecords.push(rankRecord)
        
        // Update keyword current position if campaign_id exists
        if (campaign_id) {
          await supabase
            .from('keywords')
            .update({ 
              current_position: ranking.current_position,
              last_tracked: new Date().toISOString(),
              position_change: ranking.change
            })
            .eq('campaign_id', campaign_id)
            .eq('keyword', ranking.keyword)
        }
      }
    }

    // Update campaign with tracking completion
    if (campaign_id) {
      await supabase
        .from('seo_campaigns')
        .update({
          last_rank_check: new Date().toISOString(),
          avg_position: rankingReport.average_position,
          visibility_score: rankingReport.visibility_score
        })
        .eq('id', campaign_id)
    }

    // Log the rank tracking
    await supabase
      .from('seo_logs')
      .insert({
        business_id,
        action_type: 'rank_tracking',
        action_description: `Rank tracking completed for ${rankingReport.total_keywords} keywords`,
        new_data: JSON.stringify({
          campaign_id,
          keywords_tracked: rankingReport.total_keywords,
          average_position: rankingReport.average_position,
          improved_positions: rankingReport.position_changes.improved,
          declined_positions: rankingReport.position_changes.declined
        })
      })

    return new Response(
      JSON.stringify({
        success: true,
        tracking_date: rankingReport.tracking_date,
        keywords_tracked: rankingReport.total_keywords,
        average_position: rankingReport.average_position,
        visibility_score: rankingReport.visibility_score,
        position_changes: rankingReport.position_changes,
        records_stored: rankingRecords.length,
        summary: {
          top_performers: rankingReport.top_performers.slice(0, 5),
          biggest_gainers: rankingReport.biggest_movers.gainers.slice(0, 3),
          biggest_losers: rankingReport.biggest_movers.losers.slice(0, 3),
          serp_features: rankingReport.serp_features_found.slice(0, 5),
          recommendations: rankingReport.recommendations
        }
      }),
      { 
        status: 200, 
        headers: { ...corsHeaders, 'Content-Type': 'application/json' } 
      }
    )

  } catch (error) {
    console.error('Rank tracking error:', error)
    return new Response(
      JSON.stringify({ error: 'Internal server error', details: error.message }),
      { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }
})

async function performRankTracking(
  keywords: any[],
  business: any,
  location: string,
  device: string,
  searchEngine: string,
  previousRankings: any[]
): Promise<RankingReport> {
  
  const trackingDate = new Date().toISOString()
  const keywordRankings: KeywordRanking[] = []
  
  // Simulate rank checking for each keyword
  for (const keyword of keywords) {
    const ranking = await simulateKeywordRanking(
      keyword,
      business,
      location,
      device,
      searchEngine,
      previousRankings
    )
    keywordRankings.push(ranking)
  }
  
  // Calculate metrics
  const totalKeywords = keywordRankings.length
  const averagePosition = keywordRankings.reduce((sum, r) => sum + r.current_position, 0) / totalKeywords
  
  // Calculate position changes
  const positionChanges = {
    improved: keywordRankings.filter(r => r.change < 0).length,
    declined: keywordRankings.filter(r => r.change > 0).length,
    unchanged: keywordRankings.filter(r => r.change === 0).length
  }
  
  // Calculate visibility score
  const visibilityScore = calculateVisibilityScore(keywordRankings)
  
  // Identify top performers (position 1-10)
  const topPerformers = keywordRankings
    .filter(r => r.current_position <= 10)
    .sort((a, b) => a.current_position - b.current_position)
  
  // Find biggest movers
  const biggestMovers = {
    gainers: keywordRankings
      .filter(r => r.change < -2)
      .sort((a, b) => a.change - b.change)
      .slice(0, 10),
    losers: keywordRankings
      .filter(r => r.change > 2)
      .sort((a, b) => b.change - a.change)
      .slice(0, 10)
  }
  
  // Analyze SERP features
  const serpFeatures = analyzeSerpFeatures(keywordRankings)
  
  // Analyze competitors
  const competitorAnalysis = analyzeCompetitors(keywordRankings)
  
  // Generate recommendations
  const recommendations = generateRankingRecommendations(
    keywordRankings,
    positionChanges,
    serpFeatures,
    business
  )

  return {
    tracking_date: trackingDate,
    total_keywords: totalKeywords,
    average_position: Math.round(averagePosition * 10) / 10,
    position_changes: positionChanges,
    visibility_score: visibilityScore,
    keyword_rankings: keywordRankings,
    top_performers: topPerformers,
    biggest_movers: biggestMovers,
    serp_features_found: serpFeatures,
    competitor_analysis: competitorAnalysis,
    recommendations: recommendations
  }
}

async function simulateKeywordRanking(
  keyword: any,
  business: any,
  location: string,
  device: string,
  searchEngine: string,
  previousRankings: any[]
): Promise<KeywordRanking> {
  
  // Find previous position for this keyword
  const previousRank = previousRankings.find(r => r.keyword === keyword.keyword)
  const previousPosition = previousRank?.position || null
  
  // Simulate current position (realistic movement from previous position)
  let currentPosition: number
  
  if (previousPosition) {
    // Simulate realistic position changes (-10 to +10 positions)
    const maxChange = Math.min(10, Math.floor(previousPosition * 0.2))
    const change = Math.floor(Math.random() * (maxChange * 2 + 1)) - maxChange
    currentPosition = Math.max(1, Math.min(100, previousPosition + change))
  } else {
    // New keyword - simulate position based on difficulty and business factors
    const baseDifficulty = keyword.keyword_difficulty || 50
    const industryBonus = getIndustryPositionBonus(business.industry, keyword.intent)
    currentPosition = Math.max(1, Math.min(100, baseDifficulty - industryBonus + Math.floor(Math.random() * 20) - 10))
  }
  
  const change = previousPosition ? currentPosition - previousPosition : 0
  
  // Simulate URL ranking
  const url = generateRankingUrl(business.website_url, keyword.keyword)
  
  // Simulate SERP features
  const serpFeatures = generateSerpFeatures(keyword, currentPosition)
  
  // Simulate competitor positions
  const competitorPositions = generateCompetitorPositions(keyword, currentPosition, business)
  
  // Check for local pack and featured snippet
  const localPackPosition = keyword.keyword.includes('near me') && Math.random() > 0.7 ? 
    Math.floor(Math.random() * 3) + 1 : undefined
  
  const featuredSnippet = currentPosition <= 5 && Math.random() > 0.9

  return {
    keyword: keyword.keyword,
    current_position: currentPosition,
    previous_position: previousPosition,
    change: change,
    url: url,
    search_volume: keyword.search_volume || 0,
    difficulty: keyword.keyword_difficulty || 0,
    intent: keyword.intent || 'commercial',
    serp_features: serpFeatures,
    competitor_positions: competitorPositions,
    local_pack_position: localPackPosition,
    featured_snippet: featuredSnippet
  }
}

function getIndustryPositionBonus(industry: string, intent: string): number {
  let bonus = 0
  
  // Industry-specific bonuses
  const industryBonuses: { [key: string]: number } = {
    restaurant: 15,
    legal: 10,
    healthcare: 12,
    hvac: 18,
    'real estate': 8
  }
  
  for (const [key, value] of Object.entries(industryBonuses)) {
    if (industry?.toLowerCase().includes(key)) {
      bonus += value
      break
    }
  }
  
  // Intent-based bonuses
  if (intent === 'transactional') bonus += 5
  if (intent === 'commercial') bonus += 3
  
  return bonus
}

function generateRankingUrl(websiteUrl: string, keyword: string): string {
  // Simulate which page ranks for the keyword
  const pageTypes = [
    '',  // homepage
    '/services',
    '/about',
    `/blog/${keyword.toLowerCase().replace(/\s+/g, '-')}`,
    '/contact'
  ]
  
  const randomPage = pageTypes[Math.floor(Math.random() * pageTypes.length)]
  return `${websiteUrl}${randomPage}`
}

function generateSerpFeatures(keyword: any, position: number): string[] {
  const features: string[] = []
  
  // More likely to have features for commercial/informational keywords
  const featureProbability = keyword.intent === 'informational' ? 0.7 : 0.4
  
  if (Math.random() < featureProbability) {
    const possibleFeatures = [
      'People Also Ask',
      'Related Searches',
      'Local Pack',
      'Knowledge Panel',
      'Featured Snippet',
      'Image Pack',
      'Video Results',
      'Reviews',
      'Sitelinks'
    ]
    
    const numFeatures = Math.floor(Math.random() * 3) + 1
    for (let i = 0; i < numFeatures; i++) {
      const feature = possibleFeatures[Math.floor(Math.random() * possibleFeatures.length)]
      if (!features.includes(feature)) {
        features.push(feature)
      }
    }
  }
  
  return features
}

function generateCompetitorPositions(keyword: any, currentPosition: number, business: any): any[] {
  const competitors = [
    'competitor1.com',
    'competitor2.com',
    'majorchain.com',
    'localcompetitor.com',
    'industry-leader.com'
  ]
  
  const competitorPositions = []
  const usedPositions = new Set([currentPosition])
  
  for (let i = 0; i < Math.min(3, competitors.length); i++) {
    let position: number
    do {
      position = Math.floor(Math.random() * 20) + 1
    } while (usedPositions.has(position))
    
    usedPositions.add(position)
    
    competitorPositions.push({
      domain: competitors[i],
      position: position,
      url: `https://${competitors[i]}/${keyword.keyword.replace(/\s+/g, '-').toLowerCase()}`
    })
  }
  
  return competitorPositions.sort((a, b) => a.position - b.position)
}

function calculateVisibilityScore(rankings: KeywordRanking[]): number {
  let totalScore = 0
  
  for (const ranking of rankings) {
    let positionScore = 0
    
    // Position-based scoring (position 1 = 100 points, decreasing)
    if (ranking.current_position === 1) positionScore = 100
    else if (ranking.current_position <= 3) positionScore = 85 - (ranking.current_position - 1) * 10
    else if (ranking.current_position <= 10) positionScore = 60 - (ranking.current_position - 4) * 5
    else if (ranking.current_position <= 20) positionScore = 25 - (ranking.current_position - 11) * 2
    else if (ranking.current_position <= 50) positionScore = 10 - (ranking.current_position - 21) * 0.3
    else positionScore = 1
    
    // Weight by search volume
    const volumeWeight = Math.log(ranking.search_volume + 1) / Math.log(10000)
    totalScore += positionScore * Math.min(1, volumeWeight)
  }
  
  return Math.round((totalScore / rankings.length) * 10) / 10
}

function analyzeSerpFeatures(rankings: KeywordRanking[]): any[] {
  const featureCounts = new Map<string, { count: number; keywords: string[] }>()
  
  for (const ranking of rankings) {
    for (const feature of ranking.serp_features) {
      if (!featureCounts.has(feature)) {
        featureCounts.set(feature, { count: 0, keywords: [] })
      }
      const featureData = featureCounts.get(feature)!
      featureData.count++
      featureData.keywords.push(ranking.keyword)
    }
  }
  
  return Array.from(featureCounts.entries())
    .map(([feature, data]) => ({
      feature,
      count: data.count,
      keywords: data.keywords.slice(0, 5) // Limit to first 5 keywords
    }))
    .sort((a, b) => b.count - a.count)
}

function analyzeCompetitors(rankings: KeywordRanking[]): any[] {
  const competitorData = new Map<string, { positions: number[]; keywords: number }>()
  
  for (const ranking of rankings) {
    for (const competitor of ranking.competitor_positions) {
      if (!competitorData.has(competitor.domain)) {
        competitorData.set(competitor.domain, { positions: [], keywords: 0 })
      }
      const data = competitorData.get(competitor.domain)!
      data.positions.push(competitor.position)
      data.keywords++
    }
  }
  
  const totalKeywords = rankings.length
  
  return Array.from(competitorData.entries())
    .map(([domain, data]) => {
      const averagePosition = data.positions.reduce((sum, pos) => sum + pos, 0) / data.positions.length
      const visibilityShare = (data.keywords / totalKeywords) * 100
      
      return {
        domain,
        average_position: Math.round(averagePosition * 10) / 10,
        keywords_ranking: data.keywords,
        visibility_share: Math.round(visibilityShare * 10) / 10
      }
    })
    .sort((a, b) => a.average_position - b.average_position)
}

function generateRankingRecommendations(
  rankings: KeywordRanking[],
  positionChanges: any,
  serpFeatures: any[],
  business: any
): any[] {
  const recommendations = []
  
  // Keywords in positions 11-20 (optimize to page 1)
  const page2Keywords = rankings.filter(r => r.current_position >= 11 && r.current_position <= 20)
  if (page2Keywords.length > 0) {
    recommendations.push({
      title: 'Optimize Page 2 Keywords',
      description: `${page2Keywords.length} keywords are ranking on page 2 (positions 11-20) and could be optimized to reach page 1`,
      keywords_affected: page2Keywords.slice(0, 5).map(r => r.keyword),
      priority: 'high'
    })
  }
  
  // Keywords that declined significantly
  const declinedKeywords = rankings.filter(r => r.change > 5)
  if (declinedKeywords.length > 0) {
    recommendations.push({
      title: 'Address Ranking Declines',
      description: `${declinedKeywords.length} keywords have dropped significantly in rankings and need immediate attention`,
      keywords_affected: declinedKeywords.slice(0, 5).map(r => r.keyword),
      priority: 'high'
    })
  }
  
  // Featured snippet opportunities
  const snippetOpportunities = rankings.filter(r => 
    r.current_position >= 2 && r.current_position <= 5 && 
    r.serp_features.includes('Featured Snippet')
  )
  if (snippetOpportunities.length > 0) {
    recommendations.push({
      title: 'Featured Snippet Optimization',
      description: `${snippetOpportunities.length} keywords show featured snippet opportunities for positions 2-5`,
      keywords_affected: snippetOpportunities.slice(0, 5).map(r => r.keyword),
      priority: 'medium'
    })
  }
  
  // Local pack opportunities
  const localKeywords = rankings.filter(r => 
    r.keyword.includes('near me') && !r.local_pack_position
  )
  if (localKeywords.length > 0) {
    recommendations.push({
      title: 'Local SEO Optimization',
      description: `${localKeywords.length} local keywords could benefit from local pack optimization`,
      keywords_affected: localKeywords.slice(0, 5).map(r => r.keyword),
      priority: 'medium'
    })
  }
  
  // Content optimization for informational keywords
  const informationalKeywords = rankings.filter(r => 
    r.intent === 'informational' && r.current_position > 10
  )
  if (informationalKeywords.length > 0) {
    recommendations.push({
      title: 'Content Optimization for Informational Keywords',
      description: `${informationalKeywords.length} informational keywords need content depth and structure improvements`,
      keywords_affected: informationalKeywords.slice(0, 5).map(r => r.keyword),
      priority: 'medium'
    })
  }
  
  return recommendations
}