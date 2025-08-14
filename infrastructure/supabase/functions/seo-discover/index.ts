import { serve } from 'https://deno.land/std@0.168.0/http/server.ts'
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'
import { corsHeaders } from '../_shared/cors.ts'

interface KeywordDiscoveryRequest {
  business_id: string
  campaign_id?: string
  seed_keywords?: string[]
  method?: 'seed_expansion' | 'competitor_analysis' | 'gsc_import'
  max_keywords?: number
}

interface KeywordResult {
  keyword: string
  intent: 'informational' | 'commercial' | 'transactional' | 'navigational'
  search_volume?: number
  difficulty?: number
  value_score: number
  source: string
  discovery_method: string
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

    const { business_id, campaign_id, seed_keywords = [], method = 'seed_expansion', max_keywords = 100 }: KeywordDiscoveryRequest = await req.json()

    // Validate input
    if (!business_id) {
      return new Response(
        JSON.stringify({ error: 'business_id is required' }),
        { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    // Get business details for context
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

    // Get or create campaign
    let campaign
    if (campaign_id) {
      const { data } = await supabase
        .from('seo_campaigns')
        .select('*')
        .eq('id', campaign_id)
        .single()
      campaign = data
    } else {
      // Create new campaign
      const { data } = await supabase
        .from('seo_campaigns')
        .insert({
          business_id,
          name: `${business.business_name} SEO Campaign`,
          description: `Automated SEO campaign for ${business.business_name}`,
          seed_keywords: seed_keywords
        })
        .select()
        .single()
      campaign = data
    }

    // Keyword discovery logic
    const discoveredKeywords: KeywordResult[] = []

    if (method === 'seed_expansion') {
      // Expand seed keywords with modifiers
      const modifiers = [
        'near me', 'in ' + business.city, business.city,
        'best', 'top', 'affordable', 'professional',
        'reviews', 'services', 'company', 'business'
      ]

      const baseKeywords = seed_keywords.length > 0 ? seed_keywords : [
        business.business_name.toLowerCase(),
        business.industry?.toLowerCase() || 'services',
        `${business.industry?.toLowerCase() || 'services'} ${business.city?.toLowerCase()}`
      ]

      for (const baseKeyword of baseKeywords) {
        // Add base keyword
        discoveredKeywords.push({
          keyword: baseKeyword,
          intent: classifyIntent(baseKeyword),
          search_volume: estimateSearchVolume(baseKeyword, business.city),
          difficulty: estimateDifficulty(baseKeyword, business.industry),
          value_score: calculateValueScore(baseKeyword, business.industry),
          source: 'seed',
          discovery_method: method
        })

        // Add modified versions
        for (const modifier of modifiers) {
          const modifiedKeyword = `${modifier} ${baseKeyword}`.trim()
          if (modifiedKeyword.length > 3 && modifiedKeyword.length < 100) {
            discoveredKeywords.push({
              keyword: modifiedKeyword,
              intent: classifyIntent(modifiedKeyword),
              search_volume: estimateSearchVolume(modifiedKeyword, business.city),
              difficulty: estimateDifficulty(modifiedKeyword, business.industry),
              value_score: calculateValueScore(modifiedKeyword, business.industry),
              source: 'seed_expansion',
              discovery_method: method
            })
          }
        }
      }
    }

    // Limit results
    const limitedKeywords = discoveredKeywords
      .sort((a, b) => b.value_score - a.value_score)
      .slice(0, max_keywords)

    // Store keywords in database
    const keywordsToInsert = limitedKeywords.map(kw => ({
      campaign_id: campaign.id,
      keyword: kw.keyword,
      keyword_hash: generateKeywordHash(kw.keyword),
      intent: kw.intent,
      search_volume: kw.search_volume,
      keyword_difficulty: kw.difficulty,
      value_score: kw.value_score,
      source: kw.source,
      discovery_method: kw.discovery_method
    }))

    const { error: insertError } = await supabase
      .from('keywords')
      .upsert(keywordsToInsert, { 
        onConflict: 'campaign_id,keyword_hash',
        ignoreDuplicates: true 
      })

    if (insertError) {
      console.error('Error inserting keywords:', insertError)
    }

    // Update campaign stats
    await supabase
      .from('seo_campaigns')
      .update({
        total_keywords: limitedKeywords.length,
        discovery_completed_at: new Date().toISOString(),
        avg_keyword_difficulty: limitedKeywords.reduce((sum, kw) => sum + (kw.difficulty || 0), 0) / limitedKeywords.length
      })
      .eq('id', campaign.id)

    // Log the discovery
    await supabase
      .from('seo_logs')
      .insert({
        business_id,
        action_type: 'keyword_discovery',
        action_description: `Discovered ${limitedKeywords.length} keywords using ${method}`,
        new_data: JSON.stringify({
          campaign_id: campaign.id,
          keywords_found: limitedKeywords.length,
          method: method
        })
      })

    return new Response(
      JSON.stringify({
        success: true,
        campaign_id: campaign.id,
        keywords_discovered: limitedKeywords.length,
        keywords: limitedKeywords,
        method: method
      }),
      { 
        status: 200, 
        headers: { ...corsHeaders, 'Content-Type': 'application/json' } 
      }
    )

  } catch (error) {
    console.error('Keyword discovery error:', error)
    return new Response(
      JSON.stringify({ error: 'Internal server error', details: error.message }),
      { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }
})

// Helper functions
function classifyIntent(keyword: string): 'informational' | 'commercial' | 'transactional' | 'navigational' {
  const transactionalIndicators = ['buy', 'purchase', 'order', 'book', 'hire', 'contact', 'call', 'near me']
  const commercialIndicators = ['best', 'top', 'review', 'compare', 'vs', 'price', 'cost', 'affordable']
  const informationalIndicators = ['how', 'what', 'why', 'when', 'where', 'guide', 'tips', 'learn']
  
  const lowerKeyword = keyword.toLowerCase()
  
  if (transactionalIndicators.some(indicator => lowerKeyword.includes(indicator))) {
    return 'transactional'
  }
  if (commercialIndicators.some(indicator => lowerKeyword.includes(indicator))) {
    return 'commercial'
  }
  if (informationalIndicators.some(indicator => lowerKeyword.includes(indicator))) {
    return 'informational'
  }
  
  return 'commercial' // Default for business-related keywords
}

function estimateSearchVolume(keyword: string, city?: string): number {
  // Simple heuristic-based search volume estimation
  const baseVolume = Math.max(10, 1000 - (keyword.length * 20))
  const localMultiplier = city ? 0.3 : 1.0 // Local keywords typically have lower volume
  const intentMultiplier = keyword.includes('near me') ? 0.5 : 1.0
  
  return Math.round(baseVolume * localMultiplier * intentMultiplier * (0.8 + Math.random() * 0.4))
}

function estimateDifficulty(keyword: string, industry?: string): number {
  // Simple difficulty estimation based on keyword characteristics
  let difficulty = 30 // Base difficulty
  
  // Length factor
  if (keyword.split(' ').length === 1) difficulty += 30 // Single words are harder
  if (keyword.split(' ').length >= 4) difficulty -= 15 // Long-tail is easier
  
  // Local modifier
  if (keyword.includes('near me') || keyword.match(/\b\w+, (FL|Florida)\b/)) {
    difficulty -= 20 // Local keywords are easier
  }
  
  // Industry factor
  const competitiveIndustries = ['law', 'legal', 'insurance', 'finance', 'real estate']
  if (industry && competitiveIndustries.includes(industry.toLowerCase())) {
    difficulty += 25
  }
  
  return Math.max(5, Math.min(95, difficulty + Math.round((Math.random() - 0.5) * 20)))
}

function calculateValueScore(keyword: string, industry?: string): number {
  let score = 5.0 // Base score
  
  // Intent-based scoring
  const intent = classifyIntent(keyword)
  switch (intent) {
    case 'transactional': score += 3.0; break
    case 'commercial': score += 2.0; break
    case 'informational': score += 1.0; break
    case 'navigational': score += 0.5; break
  }
  
  // Local value boost
  if (keyword.includes('near me') || keyword.match(/\b\w+, (FL|Florida)\b/)) {
    score += 1.5
  }
  
  // High-value modifiers
  const highValueTerms = ['best', 'top', 'professional', 'emergency', 'urgent']
  if (highValueTerms.some(term => keyword.toLowerCase().includes(term))) {
    score += 1.0
  }
  
  return Math.min(10.0, score)
}

function generateKeywordHash(keyword: string): string {
  // Simple hash function for deduplication
  const normalized = keyword.toLowerCase().trim()
  let hash = 0
  for (let i = 0; i < normalized.length; i++) {
    const char = normalized.charCodeAt(i)
    hash = ((hash << 5) - hash) + char
    hash = hash & hash // Convert to 32-bit integer
  }
  return Math.abs(hash).toString(16)
}