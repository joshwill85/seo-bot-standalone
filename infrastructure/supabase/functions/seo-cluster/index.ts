import { serve } from 'https://deno.land/std@0.168.0/http/server.ts'
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'
import { corsHeaders } from '../_shared/cors.ts'

interface KeywordClusteringRequest {
  business_id: string
  campaign_id: string
  clustering_method?: 'semantic' | 'intent' | 'topic' | 'hub_spoke'
  min_cluster_size?: number
  max_clusters?: number
}

interface KeywordData {
  id: string
  keyword: string
  intent: string
  search_volume: number
  keyword_difficulty: number
  value_score: number
}

interface KeywordCluster {
  name: string
  cluster_type: 'hub' | 'spoke' | 'support'
  primary_intent: string
  keywords: KeywordData[]
  parent_cluster_id?: string
  total_keywords: number
  avg_search_volume: number
  avg_difficulty: number
  priority_score: number
  content_type: string
  content_status: 'not_started' | 'planned' | 'written' | 'published'
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
      clustering_method = 'semantic',
      min_cluster_size = 3,
      max_clusters = 10
    }: KeywordClusteringRequest = await req.json()

    // Validate input
    if (!business_id || !campaign_id) {
      return new Response(
        JSON.stringify({ error: 'business_id and campaign_id are required' }),
        { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    // Get business and campaign details
    const { data: business } = await supabase
      .from('businesses')
      .select('business_name, industry, website_url')
      .eq('id', business_id)
      .single()

    const { data: campaign } = await supabase
      .from('seo_campaigns')
      .select('*')
      .eq('id', campaign_id)
      .single()

    if (!business || !campaign) {
      return new Response(
        JSON.stringify({ error: 'Business or campaign not found' }),
        { status: 404, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    // Get keywords for clustering
    const { data: keywords } = await supabase
      .from('keywords')
      .select('id, keyword, intent, search_volume, keyword_difficulty, value_score')
      .eq('campaign_id', campaign_id)
      .order('value_score', { ascending: false })

    if (!keywords || keywords.length < min_cluster_size) {
      return new Response(
        JSON.stringify({ error: `Not enough keywords for clustering. Minimum required: ${min_cluster_size}` }),
        { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    // Perform clustering
    const clusters = await performKeywordClustering(
      keywords,
      clustering_method,
      min_cluster_size,
      max_clusters,
      business
    )

    // Store clusters in database
    const clusterRecords = []
    for (const cluster of clusters) {
      const { data: clusterRecord } = await supabase
        .from('keyword_clusters')
        .insert({
          campaign_id,
          name: cluster.name,
          cluster_type: cluster.cluster_type,
          primary_intent: cluster.primary_intent,
          parent_cluster_id: cluster.parent_cluster_id,
          total_keywords: cluster.total_keywords,
          avg_search_volume: cluster.avg_search_volume,
          avg_difficulty: cluster.avg_difficulty,
          priority_score: cluster.priority_score,
          content_type: cluster.content_type,
          content_status: cluster.content_status,
          keyword_list: cluster.keywords.map(k => k.keyword),
          cluster_data: {
            keywords: cluster.keywords,
            clustering_method,
            created_at: new Date().toISOString()
          }
        })
        .select()
        .single()

      if (clusterRecord) {
        clusterRecords.push(clusterRecord)
        
        // Update keywords with cluster assignment
        const keywordIds = cluster.keywords.map(k => k.id)
        await supabase
          .from('keywords')
          .update({ 
            cluster_id: clusterRecord.id,
            cluster_name: cluster.name 
          })
          .in('id', keywordIds)
      }
    }

    // Update campaign with clustering completion
    await supabase
      .from('seo_campaigns')
      .update({
        clustering_completed_at: new Date().toISOString(),
        total_clusters: clusters.length
      })
      .eq('id', campaign_id)

    // Log the clustering operation
    await supabase
      .from('seo_logs')
      .insert({
        business_id,
        action_type: 'keyword_clustering',
        action_description: `Clustered ${keywords.length} keywords into ${clusters.length} groups using ${clustering_method} method`,
        new_data: JSON.stringify({
          campaign_id,
          keywords_processed: keywords.length,
          clusters_created: clusters.length,
          clustering_method
        })
      })

    return new Response(
      JSON.stringify({
        success: true,
        clusters_created: clusters.length,
        keywords_processed: keywords.length,
        clustering_method,
        clusters: clusters.map(cluster => ({
          name: cluster.name,
          type: cluster.cluster_type,
          keywords_count: cluster.total_keywords,
          priority_score: cluster.priority_score,
          primary_intent: cluster.primary_intent
        }))
      }),
      { 
        status: 200, 
        headers: { ...corsHeaders, 'Content-Type': 'application/json' } 
      }
    )

  } catch (error) {
    console.error('Keyword clustering error:', error)
    return new Response(
      JSON.stringify({ error: 'Internal server error', details: error.message }),
      { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }
})

async function performKeywordClustering(
  keywords: KeywordData[],
  method: string,
  minClusterSize: number,
  maxClusters: number,
  business: any
): Promise<KeywordCluster[]> {
  
  switch (method) {
    case 'semantic':
      return semanticClustering(keywords, minClusterSize, maxClusters, business)
    case 'intent':
      return intentBasedClustering(keywords, minClusterSize, maxClusters, business)
    case 'topic':
      return topicBasedClustering(keywords, minClusterSize, maxClusters, business)
    case 'hub_spoke':
      return hubSpokeClustering(keywords, minClusterSize, maxClusters, business)
    default:
      return semanticClustering(keywords, minClusterSize, maxClusters, business)
  }
}

function semanticClustering(
  keywords: KeywordData[], 
  minClusterSize: number, 
  maxClusters: number,
  business: any
): KeywordCluster[] {
  const clusters: KeywordCluster[] = []
  const usedKeywords = new Set<string>()
  
  // Group keywords by semantic similarity
  const semanticGroups = groupBySemanticsimilarity(keywords)
  
  for (const group of semanticGroups.slice(0, maxClusters)) {
    if (group.keywords.length >= minClusterSize) {
      const clusterName = generateClusterName(group.keywords, 'semantic', business)
      const cluster = createCluster(group.keywords, clusterName, 'hub', business)
      clusters.push(cluster)
      
      group.keywords.forEach(k => usedKeywords.add(k.id))
    }
  }
  
  // Handle remaining keywords
  const remainingKeywords = keywords.filter(k => !usedKeywords.has(k.id))
  if (remainingKeywords.length >= minClusterSize) {
    const miscCluster = createCluster(
      remainingKeywords, 
      'Additional Keywords', 
      'support',
      business
    )
    clusters.push(miscCluster)
  }
  
  return clusters
}

function intentBasedClustering(
  keywords: KeywordData[], 
  minClusterSize: number, 
  maxClusters: number,
  business: any
): KeywordCluster[] {
  const intentGroups = {
    transactional: keywords.filter(k => k.intent === 'transactional'),
    commercial: keywords.filter(k => k.intent === 'commercial'),
    informational: keywords.filter(k => k.intent === 'informational'),
    navigational: keywords.filter(k => k.intent === 'navigational')
  }
  
  const clusters: KeywordCluster[] = []
  
  for (const [intent, intentKeywords] of Object.entries(intentGroups)) {
    if (intentKeywords.length >= minClusterSize) {
      const clusterName = `${intent.charAt(0).toUpperCase() + intent.slice(1)} Keywords`
      const cluster = createCluster(intentKeywords, clusterName, 'hub', business)
      cluster.primary_intent = intent
      clusters.push(cluster)
    }
  }
  
  return clusters.slice(0, maxClusters)
}

function topicBasedClustering(
  keywords: KeywordData[], 
  minClusterSize: number, 
  maxClusters: number,
  business: any
): KeywordCluster[] {
  const topicGroups = groupByTopics(keywords, business)
  const clusters: KeywordCluster[] = []
  
  for (const group of topicGroups.slice(0, maxClusters)) {
    if (group.keywords.length >= minClusterSize) {
      const cluster = createCluster(group.keywords, group.topic, 'hub', business)
      clusters.push(cluster)
    }
  }
  
  return clusters
}

function hubSpokeClustering(
  keywords: KeywordData[], 
  minClusterSize: number, 
  maxClusters: number,
  business: any
): KeywordCluster[] {
  const clusters: KeywordCluster[] = []
  
  // Sort keywords by value score to identify hub keywords
  const sortedKeywords = [...keywords].sort((a, b) => b.value_score - a.value_score)
  
  // Create hub clusters with high-value keywords
  const hubKeywords = sortedKeywords.slice(0, Math.min(3, Math.floor(maxClusters / 2)))
  
  for (const hubKeyword of hubKeywords) {
    // Find related keywords for this hub
    const relatedKeywords = findRelatedKeywords(hubKeyword, keywords, 5)
    
    if (relatedKeywords.length >= minClusterSize) {
      const clusterName = generateClusterName([hubKeyword, ...relatedKeywords], 'hub', business)
      const hubCluster = createCluster([hubKeyword, ...relatedKeywords], clusterName, 'hub', business)
      clusters.push(hubCluster)
      
      // Create spoke clusters for each related keyword group
      const spokeGroups = groupSpokeKeywords(relatedKeywords)
      for (const spokeGroup of spokeGroups) {
        if (spokeGroup.length >= Math.max(2, minClusterSize - 1)) {
          const spokeName = generateClusterName(spokeGroup, 'spoke', business)
          const spokeCluster = createCluster(spokeGroup, spokeName, 'spoke', business)
          spokeCluster.parent_cluster_id = hubCluster.name // Will be updated with actual ID later
          clusters.push(spokeCluster)
        }
      }
    }
  }
  
  return clusters.slice(0, maxClusters)
}

function groupBySemanticsimilarity(keywords: KeywordData[]): { keywords: KeywordData[] }[] {
  const groups: { keywords: KeywordData[] }[] = []
  const processed = new Set<string>()
  
  for (const keyword of keywords) {
    if (processed.has(keyword.id)) continue
    
    const group = [keyword]
    processed.add(keyword.id)
    
    // Find semantically similar keywords
    for (const otherKeyword of keywords) {
      if (processed.has(otherKeyword.id)) continue
      
      if (areSemanticallyRelated(keyword.keyword, otherKeyword.keyword)) {
        group.push(otherKeyword)
        processed.add(otherKeyword.id)
      }
    }
    
    groups.push({ keywords: group })
  }
  
  return groups.sort((a, b) => b.keywords.length - a.keywords.length)
}

function groupByTopics(keywords: KeywordData[], business: any): { topic: string, keywords: KeywordData[] }[] {
  const topics = extractTopics(keywords, business)
  const groups: { topic: string, keywords: KeywordData[] }[] = []
  
  for (const topic of topics) {
    const topicKeywords = keywords.filter(k => 
      k.keyword.toLowerCase().includes(topic.toLowerCase()) ||
      isRelatedToTopic(k.keyword, topic)
    )
    
    if (topicKeywords.length > 0) {
      groups.push({ topic, keywords: topicKeywords })
    }
  }
  
  return groups.sort((a, b) => b.keywords.length - a.keywords.length)
}

function extractTopics(keywords: KeywordData[], business: any): string[] {
  const industry = business.industry?.toLowerCase() || ''
  const commonWords = new Map<string, number>()
  
  // Extract meaningful words from keywords
  keywords.forEach(k => {
    const words = k.keyword.toLowerCase()
      .split(/\s+/)
      .filter(word => 
        word.length > 3 && 
        !['near', 'best', 'good', 'great', 'top'].includes(word)
      )
    
    words.forEach(word => {
      commonWords.set(word, (commonWords.get(word) || 0) + 1)
    })
  })
  
  // Get most common meaningful words as topics
  const topics = Array.from(commonWords.entries())
    .filter(([word, count]) => count >= 2)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5)
    .map(([word]) => word)
  
  // Add industry-specific topics
  const industryTopics = getIndustryTopics(industry)
  
  return [...topics, ...industryTopics].slice(0, 8)
}

function getIndustryTopics(industry: string): string[] {
  const industryMap = {
    restaurant: ['menu', 'dining', 'food', 'cuisine', 'delivery'],
    legal: ['lawyer', 'attorney', 'legal', 'law', 'case'],
    healthcare: ['doctor', 'medical', 'health', 'treatment', 'care'],
    hvac: ['heating', 'cooling', 'repair', 'installation', 'maintenance'],
    'real estate': ['property', 'home', 'house', 'buying', 'selling']
  }
  
  for (const [key, topics] of Object.entries(industryMap)) {
    if (industry.includes(key)) {
      return topics
    }
  }
  
  return []
}

function findRelatedKeywords(targetKeyword: KeywordData, allKeywords: KeywordData[], maxCount: number): KeywordData[] {
  const related = allKeywords
    .filter(k => k.id !== targetKeyword.id)
    .map(k => ({
      keyword: k,
      similarity: calculateKeywordSimilarity(targetKeyword.keyword, k.keyword)
    }))
    .filter(item => item.similarity > 0.3)
    .sort((a, b) => b.similarity - a.similarity)
    .slice(0, maxCount)
    .map(item => item.keyword)
  
  return related
}

function groupSpokeKeywords(keywords: KeywordData[]): KeywordData[][] {
  const groups: KeywordData[][] = []
  const processed = new Set<string>()
  
  for (const keyword of keywords) {
    if (processed.has(keyword.id)) continue
    
    const group = [keyword]
    processed.add(keyword.id)
    
    // Find 2-3 closely related keywords for each spoke
    for (const otherKeyword of keywords) {
      if (processed.has(otherKeyword.id) || group.length >= 3) continue
      
      if (areSemanticallyRelated(keyword.keyword, otherKeyword.keyword)) {
        group.push(otherKeyword)
        processed.add(otherKeyword.id)
      }
    }
    
    groups.push(group)
  }
  
  return groups
}

function areSemanticallyRelated(keyword1: string, keyword2: string): boolean {
  const words1 = new Set(keyword1.toLowerCase().split(/\s+/))
  const words2 = new Set(keyword2.toLowerCase().split(/\s+/))
  
  const intersection = new Set([...words1].filter(x => words2.has(x)))
  const union = new Set([...words1, ...words2])
  
  const jaccardSimilarity = intersection.size / union.size
  return jaccardSimilarity > 0.3
}

function isRelatedToTopic(keyword: string, topic: string): boolean {
  const keywordLower = keyword.toLowerCase()
  const topicLower = topic.toLowerCase()
  
  // Check for variations and related terms
  const relatedTerms = getRelatedTerms(topicLower)
  
  return relatedTerms.some(term => keywordLower.includes(term))
}

function getRelatedTerms(topic: string): string[] {
  const relatedMap: { [key: string]: string[] } = {
    restaurant: ['dining', 'food', 'eat', 'meal', 'cuisine'],
    legal: ['law', 'attorney', 'lawyer', 'court', 'case'],
    medical: ['health', 'doctor', 'clinic', 'treatment', 'care'],
    repair: ['fix', 'service', 'maintenance', 'installation']
  }
  
  return relatedMap[topic] || [topic]
}

function calculateKeywordSimilarity(keyword1: string, keyword2: string): number {
  const words1 = keyword1.toLowerCase().split(/\s+/)
  const words2 = keyword2.toLowerCase().split(/\s+/)
  
  const sharedWords = words1.filter(word => words2.includes(word)).length
  const totalWords = new Set([...words1, ...words2]).size
  
  return sharedWords / totalWords
}

function generateClusterName(keywords: KeywordData[], type: string, business: any): string {
  if (keywords.length === 0) return 'Empty Cluster'
  
  // Find most common meaningful words
  const wordCounts = new Map<string, number>()
  
  keywords.forEach(k => {
    const words = k.keyword.toLowerCase()
      .split(/\s+/)
      .filter(word => 
        word.length > 3 && 
        !['near', 'best', 'good', 'great', 'top', 'the', 'and', 'for'].includes(word)
      )
    
    words.forEach(word => {
      wordCounts.set(word, (wordCounts.get(word) || 0) + 1)
    })
  })
  
  const topWords = Array.from(wordCounts.entries())
    .sort((a, b) => b[1] - a[1])
    .slice(0, 2)
    .map(([word]) => word)
  
  if (topWords.length === 0) {
    return `${business.industry || 'General'} Keywords`
  }
  
  const baseName = topWords
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ')
  
  const typeLabels = {
    hub: 'Hub',
    spoke: 'Cluster',
    semantic: 'Group',
    support: 'Support'
  }
  
  return `${baseName} ${typeLabels[type as keyof typeof typeLabels] || 'Cluster'}`
}

function createCluster(
  keywords: KeywordData[], 
  name: string, 
  type: 'hub' | 'spoke' | 'support',
  business: any
): KeywordCluster {
  const totalKeywords = keywords.length
  const avgSearchVolume = Math.round(
    keywords.reduce((sum, k) => sum + (k.search_volume || 0), 0) / totalKeywords
  )
  const avgDifficulty = Math.round(
    keywords.reduce((sum, k) => sum + (k.keyword_difficulty || 0), 0) / totalKeywords * 10
  ) / 10
  
  // Determine primary intent
  const intentCounts = keywords.reduce((acc, k) => {
    acc[k.intent] = (acc[k.intent] || 0) + 1
    return acc
  }, {} as { [key: string]: number })
  
  const primaryIntent = Object.entries(intentCounts)
    .sort((a, b) => b[1] - a[1])[0]?.[0] || 'commercial'
  
  // Calculate priority score
  const priorityScore = calculateClusterPriority(keywords, type, business)
  
  // Determine content type
  const contentType = determineContentType(keywords, primaryIntent, business)
  
  return {
    name,
    cluster_type: type,
    primary_intent: primaryIntent,
    keywords,
    total_keywords: totalKeywords,
    avg_search_volume: avgSearchVolume,
    avg_difficulty: avgDifficulty,
    priority_score: priorityScore,
    content_type: contentType,
    content_status: 'not_started'
  }
}

function calculateClusterPriority(keywords: KeywordData[], type: string, business: any): number {
  let score = 5.0
  
  // Base score adjustments
  const avgValueScore = keywords.reduce((sum, k) => sum + (k.value_score || 0), 0) / keywords.length
  score += (avgValueScore - 5.0) * 0.5
  
  // Type adjustments
  if (type === 'hub') score += 1.0
  if (type === 'spoke') score += 0.5
  
  // Size adjustments
  if (keywords.length > 10) score += 0.5
  if (keywords.length > 20) score += 0.5
  
  // Intent adjustments
  const transactionalCount = keywords.filter(k => k.intent === 'transactional').length
  score += (transactionalCount / keywords.length) * 2.0
  
  return Math.min(10.0, Math.max(1.0, score))
}

function determineContentType(keywords: KeywordData[], primaryIntent: string, business: any): string {
  const hasHowTo = keywords.some(k => k.keyword.toLowerCase().includes('how to'))
  const hasBest = keywords.some(k => k.keyword.toLowerCase().includes('best'))
  const hasVs = keywords.some(k => k.keyword.toLowerCase().includes('vs'))
  
  if (hasHowTo) return 'howto'
  if (hasVs) return 'comparison'
  if (hasBest) return 'listicle'
  if (primaryIntent === 'informational') return 'article'
  if (primaryIntent === 'transactional') return 'landing_page'
  
  return 'article'
}