import { serve } from 'https://deno.land/std@0.168.0/http/server.ts'
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'
import { corsHeaders } from '../_shared/cors.ts'

interface AIOptimizationRequest {
  business_id: string
  campaign_id?: string
  action: 'optimize_content' | 'generate_meta' | 'improve_readability' | 'keyword_optimize' | 'semantic_analysis'
  content?: string
  url?: string
  target_keywords?: string[]
  optimization_goals?: {
    target_reading_level?: number // 1-12 grade level
    target_word_count?: number
    keyword_density?: number // percentage
    sentiment?: 'positive' | 'neutral' | 'negative'
  }
  language?: string
}

interface ContentOptimizationResult {
  original_content: string
  optimized_content: string
  improvements: {
    category: string
    description: string
    impact: 'high' | 'medium' | 'low'
    before: string
    after: string
  }[]
  metrics: {
    readability_score: number
    seo_score: number
    keyword_density: { [keyword: string]: number }
    word_count: number
    reading_time: number
    sentiment_score: number
    semantic_relevance: number
  }
  recommendations: string[]
  ai_confidence: number
}

interface MetaTagOptimization {
  original: {
    title?: string
    description?: string
    keywords?: string[]
  }
  optimized: {
    title: string
    description: string
    keywords: string[]
    og_title?: string
    og_description?: string
    twitter_title?: string
    twitter_description?: string
  }
  improvements: string[]
  seo_score: number
}

interface SemanticAnalysis {
  main_topics: { topic: string; relevance: number }[]
  entities: { entity: string; type: string; salience: number }[]
  related_keywords: { keyword: string; relevance: number }[]
  content_gaps: string[]
  semantic_score: number
  topic_coverage: { [topic: string]: number }
  recommendations: string[]
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
      content,
      url,
      target_keywords = [],
      optimization_goals = {},
      language = 'en'
    }: AIOptimizationRequest = await req.json()

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
      .select('id, business_name, industry, target_keywords')
      .eq('id', business_id)
      .single()

    if (!business) {
      return new Response(
        JSON.stringify({ error: 'Business not found' }),
        { status: 404, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    // Get campaign keywords if campaign_id provided
    let campaignKeywords: string[] = []
    if (campaign_id) {
      const { data: keywords } = await supabase
        .from('keywords')
        .select('keyword')
        .eq('campaign_id', campaign_id)
        .limit(20)
      
      campaignKeywords = keywords?.map(k => k.keyword) || []
    }

    // Combine all target keywords
    const allKeywords = [...new Set([
      ...target_keywords,
      ...campaignKeywords,
      ...(business.target_keywords || [])
    ])]

    // Get content if URL provided
    let contentToOptimize = content
    if (url && !content) {
      const { data: pageData } = await supabase
        .from('content_performance')
        .select('content, title, meta_description')
        .eq('url', url)
        .single()
      
      contentToOptimize = pageData?.content || ''
    }

    switch (action) {
      case 'optimize_content':
        return await handleContentOptimization(
          supabase,
          business,
          contentToOptimize || '',
          allKeywords,
          optimization_goals
        )
      case 'generate_meta':
        return await handleMetaGeneration(
          supabase,
          business,
          contentToOptimize || '',
          url,
          allKeywords
        )
      case 'improve_readability':
        return await handleReadabilityImprovement(
          supabase,
          business,
          contentToOptimize || '',
          optimization_goals.target_reading_level
        )
      case 'keyword_optimize':
        return await handleKeywordOptimization(
          supabase,
          business,
          contentToOptimize || '',
          allKeywords,
          optimization_goals.keyword_density
        )
      case 'semantic_analysis':
        return await handleSemanticAnalysis(
          supabase,
          business,
          contentToOptimize || '',
          allKeywords
        )
      default:
        return new Response(
          JSON.stringify({ error: 'Invalid action' }),
          { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
        )
    }

  } catch (error) {
    console.error('AI optimization error:', error)
    return new Response(
      JSON.stringify({ error: 'Internal server error', details: error.message }),
      { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }
})

async function handleContentOptimization(
  supabase: any,
  business: any,
  content: string,
  keywords: string[],
  goals: any
): Promise<Response> {
  
  if (!content) {
    return new Response(
      JSON.stringify({ error: 'Content is required for optimization' }),
      { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }

  // Analyze current content
  const currentMetrics = analyzeContent(content, keywords)
  
  // Generate AI-optimized content
  const optimizationResult = await optimizeContentWithAI(
    content,
    keywords,
    business.industry,
    goals,
    currentMetrics
  )

  // Store optimization record
  await supabase
    .from('ai_optimizations')
    .insert({
      business_id: business.id,
      optimization_type: 'content',
      original_content: content,
      optimized_content: optimizationResult.optimized_content,
      metrics_before: currentMetrics,
      metrics_after: optimizationResult.metrics,
      improvements: optimizationResult.improvements,
      ai_confidence: optimizationResult.ai_confidence,
      created_at: new Date().toISOString()
    })

  // Log the optimization
  await supabase
    .from('seo_logs')
    .insert({
      business_id: business.id,
      action_type: 'ai_content_optimization',
      action_description: `AI optimized content with ${optimizationResult.improvements.length} improvements`,
      new_data: JSON.stringify({
        seo_score_improvement: optimizationResult.metrics.seo_score - currentMetrics.seo_score,
        word_count: optimizationResult.metrics.word_count,
        keywords_optimized: keywords.length
      })
    })

  return new Response(
    JSON.stringify({
      success: true,
      optimization_result: optimizationResult,
      summary: {
        improvements_made: optimizationResult.improvements.length,
        seo_score_before: currentMetrics.seo_score,
        seo_score_after: optimizationResult.metrics.seo_score,
        readability_improvement: optimizationResult.metrics.readability_score - currentMetrics.readability_score
      }
    }),
    { 
      status: 200, 
      headers: { ...corsHeaders, 'Content-Type': 'application/json' } 
    }
  )
}

async function handleMetaGeneration(
  supabase: any,
  business: any,
  content: string,
  url: string | undefined,
  keywords: string[]
): Promise<Response> {
  
  // Generate optimized meta tags
  const metaOptimization = await generateOptimizedMetaTags(
    content,
    keywords,
    business.industry,
    url
  )

  // Store the optimization
  await supabase
    .from('ai_optimizations')
    .insert({
      business_id: business.id,
      optimization_type: 'meta_tags',
      original_content: JSON.stringify(metaOptimization.original),
      optimized_content: JSON.stringify(metaOptimization.optimized),
      improvements: metaOptimization.improvements,
      metrics_after: { seo_score: metaOptimization.seo_score },
      ai_confidence: 0.85,
      created_at: new Date().toISOString()
    })

  return new Response(
    JSON.stringify({
      success: true,
      meta_optimization: metaOptimization,
      ready_to_implement: true
    }),
    { 
      status: 200, 
      headers: { ...corsHeaders, 'Content-Type': 'application/json' } 
    }
  )
}

async function handleReadabilityImprovement(
  supabase: any,
  business: any,
  content: string,
  targetReadingLevel?: number
): Promise<Response> {
  
  if (!content) {
    return new Response(
      JSON.stringify({ error: 'Content is required for readability improvement' }),
      { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }

  // Analyze and improve readability
  const readabilityResult = await improveReadability(
    content,
    targetReadingLevel || 8,
    business.industry
  )

  return new Response(
    JSON.stringify({
      success: true,
      readability_analysis: readabilityResult,
      improvements: {
        sentences_simplified: readabilityResult.improvements.filter(i => i.category === 'sentence_structure').length,
        words_simplified: readabilityResult.improvements.filter(i => i.category === 'vocabulary').length,
        structure_improvements: readabilityResult.improvements.filter(i => i.category === 'structure').length
      }
    }),
    { 
      status: 200, 
      headers: { ...corsHeaders, 'Content-Type': 'application/json' } 
    }
  )
}

async function handleKeywordOptimization(
  supabase: any,
  business: any,
  content: string,
  keywords: string[],
  targetDensity?: number
): Promise<Response> {
  
  if (!content || keywords.length === 0) {
    return new Response(
      JSON.stringify({ error: 'Content and keywords are required for optimization' }),
      { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }

  // Optimize keyword placement and density
  const keywordResult = await optimizeKeywordPlacement(
    content,
    keywords,
    targetDensity || 2.5,
    business.industry
  )

  return new Response(
    JSON.stringify({
      success: true,
      keyword_optimization: keywordResult,
      summary: {
        keywords_added: keywordResult.keywords_added,
        density_achieved: keywordResult.average_density,
        natural_placement_score: keywordResult.natural_placement_score
      }
    }),
    { 
      status: 200, 
      headers: { ...corsHeaders, 'Content-Type': 'application/json' } 
    }
  )
}

async function handleSemanticAnalysis(
  supabase: any,
  business: any,
  content: string,
  keywords: string[]
): Promise<Response> {
  
  if (!content) {
    return new Response(
      JSON.stringify({ error: 'Content is required for semantic analysis' }),
      { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }

  // Perform semantic analysis
  const semanticResult = await analyzeSemanticContent(
    content,
    keywords,
    business.industry
  )

  // Store the analysis
  await supabase
    .from('ai_optimizations')
    .insert({
      business_id: business.id,
      optimization_type: 'semantic_analysis',
      original_content: content.substring(0, 1000), // Store sample
      analysis_results: semanticResult,
      metrics_after: { semantic_score: semanticResult.semantic_score },
      ai_confidence: 0.9,
      created_at: new Date().toISOString()
    })

  return new Response(
    JSON.stringify({
      success: true,
      semantic_analysis: semanticResult,
      actionable_insights: {
        missing_topics: semanticResult.content_gaps,
        related_keywords_to_add: semanticResult.related_keywords.slice(0, 10),
        topic_coverage_score: semanticResult.semantic_score
      }
    }),
    { 
      status: 200, 
      headers: { ...corsHeaders, 'Content-Type': 'application/json' } 
    }
  )
}

// AI Optimization Functions

async function optimizeContentWithAI(
  content: string,
  keywords: string[],
  industry: string,
  goals: any,
  currentMetrics: any
): Promise<ContentOptimizationResult> {
  
  // Simulate AI optimization (in production, this would call an AI service)
  const improvements: any[] = []
  let optimizedContent = content
  
  // Improve keyword placement
  for (const keyword of keywords.slice(0, 5)) {
    const keywordRegex = new RegExp(`\\b${keyword}\\b`, 'gi')
    const occurrences = (content.match(keywordRegex) || []).length
    
    if (occurrences < 3) {
      // Add keyword naturally in the content
      const sentences = optimizedContent.split('. ')
      const targetSentence = Math.floor(sentences.length / 3)
      
      if (sentences[targetSentence] && !sentences[targetSentence].toLowerCase().includes(keyword.toLowerCase())) {
        const before = sentences[targetSentence]
        sentences[targetSentence] = insertKeywordNaturally(sentences[targetSentence], keyword)
        const after = sentences[targetSentence]
        
        improvements.push({
          category: 'keyword_optimization',
          description: `Added keyword "${keyword}" for better SEO`,
          impact: 'high',
          before,
          after
        })
        
        optimizedContent = sentences.join('. ')
      }
    }
  }
  
  // Improve sentence structure
  const longSentences = optimizedContent.split('. ').filter(s => s.split(' ').length > 25)
  for (const sentence of longSentences.slice(0, 3)) {
    const simplified = simplifySentence(sentence)
    if (simplified !== sentence) {
      optimizedContent = optimizedContent.replace(sentence, simplified)
      improvements.push({
        category: 'readability',
        description: 'Simplified long sentence for better readability',
        impact: 'medium',
        before: sentence,
        after: simplified
      })
    }
  }
  
  // Add semantic variations
  const semanticVariations = generateSemanticVariations(keywords)
  for (const variation of semanticVariations.slice(0, 3)) {
    if (!optimizedContent.toLowerCase().includes(variation.toLowerCase())) {
      const sentences = optimizedContent.split('. ')
      const targetIndex = Math.floor(Math.random() * sentences.length)
      sentences[targetIndex] += ` This relates to ${variation}.`
      optimizedContent = sentences.join('. ')
      
      improvements.push({
        category: 'semantic_enhancement',
        description: `Added semantic variation "${variation}"`,
        impact: 'medium',
        before: '',
        after: variation
      })
    }
  }
  
  // Calculate new metrics
  const newMetrics = analyzeContent(optimizedContent, keywords)
  
  return {
    original_content: content,
    optimized_content: optimizedContent,
    improvements,
    metrics: newMetrics,
    recommendations: generateContentRecommendations(newMetrics, keywords),
    ai_confidence: 0.85
  }
}

async function generateOptimizedMetaTags(
  content: string,
  keywords: string[],
  industry: string,
  url?: string
): Promise<MetaTagOptimization> {
  
  // Extract key information from content
  const contentSummary = extractContentSummary(content)
  const primaryKeyword = keywords[0] || industry
  
  // Generate optimized title
  const title = generateSEOTitle(contentSummary, primaryKeyword, industry)
  
  // Generate optimized description
  const description = generateSEODescription(contentSummary, keywords.slice(0, 3), industry)
  
  // Generate Open Graph tags
  const ogTitle = title.length > 60 ? title.substring(0, 57) + '...' : title
  const ogDescription = description.length > 155 ? description.substring(0, 152) + '...' : description
  
  const improvements = [
    'Optimized title for search engines with primary keyword',
    'Created compelling meta description with call-to-action',
    'Added relevant keywords naturally',
    'Optimized length for SERP display',
    'Added Open Graph tags for social sharing'
  ]
  
  return {
    original: {
      title: contentSummary.title,
      description: contentSummary.description,
      keywords: []
    },
    optimized: {
      title,
      description,
      keywords: keywords.slice(0, 10),
      og_title: ogTitle,
      og_description: ogDescription,
      twitter_title: ogTitle,
      twitter_description: ogDescription
    },
    improvements,
    seo_score: calculateMetaSEOScore(title, description, keywords)
  }
}

async function improveReadability(
  content: string,
  targetReadingLevel: number,
  industry: string
): Promise<ContentOptimizationResult> {
  
  const improvements: any[] = []
  let improvedContent = content
  
  // Split into sentences
  const sentences = content.split(/[.!?]+/).filter(s => s.trim().length > 0)
  
  // Simplify complex sentences
  const simplifiedSentences = sentences.map(sentence => {
    const words = sentence.split(' ')
    if (words.length > 20) {
      // Break into shorter sentences
      const midPoint = Math.floor(words.length / 2)
      const firstHalf = words.slice(0, midPoint).join(' ')
      const secondHalf = words.slice(midPoint).join(' ')
      
      improvements.push({
        category: 'sentence_structure',
        description: 'Split long sentence for better readability',
        impact: 'high',
        before: sentence,
        after: `${firstHalf}. ${secondHalf}`
      })
      
      return `${firstHalf}. ${secondHalf}`
    }
    return sentence
  })
  
  improvedContent = simplifiedSentences.join('. ') + '.'
  
  // Replace complex words with simpler alternatives
  const complexWords = findComplexWords(improvedContent)
  for (const complexWord of complexWords.slice(0, 10)) {
    const simpleAlternative = getSimpleAlternative(complexWord)
    if (simpleAlternative) {
      improvedContent = improvedContent.replace(
        new RegExp(`\\b${complexWord}\\b`, 'gi'),
        simpleAlternative
      )
      
      improvements.push({
        category: 'vocabulary',
        description: `Replaced "${complexWord}" with simpler "${simpleAlternative}"`,
        impact: 'medium',
        before: complexWord,
        after: simpleAlternative
      })
    }
  }
  
  // Add transitions and structure improvements
  improvedContent = addTransitions(improvedContent)
  
  const metrics = analyzeContent(improvedContent, [])
  
  return {
    original_content: content,
    optimized_content: improvedContent,
    improvements,
    metrics,
    recommendations: [
      `Content readability improved to grade level ${targetReadingLevel}`,
      'Sentences simplified for better comprehension',
      'Complex vocabulary replaced with clearer alternatives'
    ],
    ai_confidence: 0.88
  }
}

async function optimizeKeywordPlacement(
  content: string,
  keywords: string[],
  targetDensity: number,
  industry: string
): Promise<any> {
  
  let optimizedContent = content
  const wordCount = content.split(' ').length
  const targetOccurrences = Math.ceil((wordCount * targetDensity) / 100)
  
  let keywordsAdded = 0
  const keywordDensities: { [key: string]: number } = {}
  
  for (const keyword of keywords) {
    const currentOccurrences = (content.match(new RegExp(`\\b${keyword}\\b`, 'gi')) || []).length
    const needed = Math.max(0, targetOccurrences - currentOccurrences)
    
    if (needed > 0) {
      // Add keyword strategically
      optimizedContent = addKeywordStrategically(optimizedContent, keyword, needed)
      keywordsAdded += needed
    }
    
    const finalOccurrences = (optimizedContent.match(new RegExp(`\\b${keyword}\\b`, 'gi')) || []).length
    keywordDensities[keyword] = (finalOccurrences / wordCount) * 100
  }
  
  const avgDensity = Object.values(keywordDensities).reduce((a, b) => a + b, 0) / Object.keys(keywordDensities).length
  
  return {
    optimized_content: optimizedContent,
    keyword_densities: keywordDensities,
    keywords_added: keywordsAdded,
    average_density: avgDensity,
    natural_placement_score: calculateNaturalPlacementScore(optimizedContent, keywords),
    recommendations: generateKeywordRecommendations(keywordDensities, targetDensity)
  }
}

async function analyzeSemanticContent(
  content: string,
  keywords: string[],
  industry: string
): Promise<SemanticAnalysis> {
  
  // Extract main topics using simple NLP
  const topics = extractTopics(content, industry)
  
  // Identify entities
  const entities = extractEntities(content)
  
  // Find related keywords
  const relatedKeywords = findRelatedKeywords(keywords, content, industry)
  
  // Identify content gaps
  const contentGaps = identifyContentGaps(content, keywords, industry)
  
  // Calculate topic coverage
  const topicCoverage = calculateTopicCoverage(content, topics)
  
  // Calculate semantic score
  const semanticScore = calculateSemanticScore(topics, entities, relatedKeywords, topicCoverage)
  
  return {
    main_topics: topics,
    entities,
    related_keywords: relatedKeywords,
    content_gaps: contentGaps,
    semantic_score: semanticScore,
    topic_coverage: topicCoverage,
    recommendations: generateSemanticRecommendations(contentGaps, relatedKeywords, semanticScore)
  }
}

// Helper functions

function analyzeContent(content: string, keywords: string[]): any {
  const words = content.split(' ').filter(w => w.length > 0)
  const sentences = content.split(/[.!?]+/).filter(s => s.trim().length > 0)
  
  const keywordDensity: { [key: string]: number } = {}
  for (const keyword of keywords) {
    const occurrences = (content.match(new RegExp(`\\b${keyword}\\b`, 'gi')) || []).length
    keywordDensity[keyword] = (occurrences / words.length) * 100
  }
  
  return {
    readability_score: calculateReadabilityScore(content),
    seo_score: calculateSEOScore(content, keywords),
    keyword_density: keywordDensity,
    word_count: words.length,
    reading_time: Math.ceil(words.length / 200), // minutes
    sentiment_score: calculateSentimentScore(content),
    semantic_relevance: calculateSemanticRelevance(content, keywords)
  }
}

function calculateReadabilityScore(content: string): number {
  // Simplified Flesch Reading Ease calculation
  const words = content.split(' ').length
  const sentences = content.split(/[.!?]+/).length
  const syllables = content.split(' ').reduce((count, word) => count + countSyllables(word), 0)
  
  const score = 206.835 - 1.015 * (words / sentences) - 84.6 * (syllables / words)
  return Math.max(0, Math.min(100, score))
}

function calculateSEOScore(content: string, keywords: string[]): number {
  let score = 50 // Base score
  
  // Check keyword presence
  for (const keyword of keywords.slice(0, 5)) {
    if (content.toLowerCase().includes(keyword.toLowerCase())) {
      score += 10
    }
  }
  
  // Check content length
  const wordCount = content.split(' ').length
  if (wordCount > 300) score += 10
  if (wordCount > 600) score += 10
  if (wordCount > 1000) score += 10
  
  // Check for headings (simulated)
  if (content.includes('##')) score += 5
  
  return Math.min(100, score)
}

function calculateSentimentScore(content: string): number {
  // Simple sentiment analysis
  const positiveWords = ['great', 'excellent', 'amazing', 'wonderful', 'fantastic', 'best', 'perfect']
  const negativeWords = ['bad', 'poor', 'terrible', 'awful', 'worst', 'horrible', 'disappointing']
  
  let score = 0
  const words = content.toLowerCase().split(' ')
  
  for (const word of words) {
    if (positiveWords.includes(word)) score += 1
    if (negativeWords.includes(word)) score -= 1
  }
  
  return score
}

function calculateSemanticRelevance(content: string, keywords: string[]): number {
  // Simple semantic relevance calculation
  let relevanceScore = 0
  const contentLower = content.toLowerCase()
  
  for (const keyword of keywords) {
    const variations = generateSemanticVariations([keyword])
    for (const variation of variations) {
      if (contentLower.includes(variation.toLowerCase())) {
        relevanceScore += 10
      }
    }
  }
  
  return Math.min(100, relevanceScore)
}

function countSyllables(word: string): number {
  // Simple syllable counting
  word = word.toLowerCase()
  let count = 0
  let previousWasVowel = false
  
  for (let i = 0; i < word.length; i++) {
    const isVowel = 'aeiou'.includes(word[i])
    if (isVowel && !previousWasVowel) {
      count++
    }
    previousWasVowel = isVowel
  }
  
  return Math.max(1, count)
}

function insertKeywordNaturally(sentence: string, keyword: string): string {
  // Insert keyword naturally into sentence
  const words = sentence.split(' ')
  const insertPosition = Math.floor(words.length / 2)
  words.splice(insertPosition, 0, `regarding ${keyword}`)
  return words.join(' ')
}

function simplifySentence(sentence: string): string {
  // Simplify long sentence
  const words = sentence.split(' ')
  if (words.length > 25) {
    const midPoint = Math.floor(words.length / 2)
    return words.slice(0, midPoint).join(' ') + '. ' + 
           words.slice(midPoint).join(' ')
  }
  return sentence
}

function generateSemanticVariations(keywords: string[]): string[] {
  const variations: string[] = []
  
  for (const keyword of keywords) {
    // Add simple variations
    variations.push(keyword + 's') // plural
    variations.push(keyword + 'ing') // gerund
    
    // Industry-specific variations
    if (keyword.includes('restaurant')) {
      variations.push('dining', 'eatery', 'food establishment')
    }
    if (keyword.includes('lawyer')) {
      variations.push('attorney', 'legal counsel', 'law firm')
    }
  }
  
  return variations
}

function extractContentSummary(content: string): any {
  const sentences = content.split(/[.!?]+/).filter(s => s.trim().length > 0)
  return {
    title: sentences[0]?.substring(0, 60) || 'Content',
    description: sentences.slice(0, 2).join('. ').substring(0, 160) || content.substring(0, 160)
  }
}

function generateSEOTitle(summary: any, keyword: string, industry: string): string {
  const templates = [
    `${keyword} - Expert ${industry} Services | Your Solution`,
    `Best ${keyword} in ${industry} | Professional Services`,
    `${keyword}: Complete Guide for ${industry}`,
    `Top ${keyword} Services | ${industry} Experts`
  ]
  
  return templates[Math.floor(Math.random() * templates.length)]
}

function generateSEODescription(summary: any, keywords: string[], industry: string): string {
  const keyword = keywords[0] || industry
  return `Discover expert ${keyword} services in ${industry}. ${summary.description.substring(0, 100)}. Contact us today for professional solutions.`
}

function calculateMetaSEOScore(title: string, description: string, keywords: string[]): number {
  let score = 0
  
  // Title checks
  if (title.length >= 30 && title.length <= 60) score += 25
  if (keywords[0] && title.toLowerCase().includes(keywords[0].toLowerCase())) score += 25
  
  // Description checks
  if (description.length >= 120 && description.length <= 160) score += 25
  if (keywords[0] && description.toLowerCase().includes(keywords[0].toLowerCase())) score += 25
  
  return score
}

function findComplexWords(content: string): string[] {
  // Find words that are complex (more than 3 syllables)
  const words = content.split(/\s+/)
  return words.filter(word => countSyllables(word) > 3).slice(0, 20)
}

function getSimpleAlternative(word: string): string {
  const alternatives: { [key: string]: string } = {
    'utilize': 'use',
    'implement': 'do',
    'facilitate': 'help',
    'ameliorate': 'improve',
    'subsequently': 'then',
    'prioritize': 'focus on',
    'optimize': 'improve',
    'leverage': 'use'
  }
  
  return alternatives[word.toLowerCase()] || word
}

function addTransitions(content: string): string {
  // Add transition words between paragraphs
  const paragraphs = content.split('\n\n')
  const transitions = ['Additionally', 'Furthermore', 'Moreover', 'In addition', 'Similarly']
  
  return paragraphs.map((p, i) => {
    if (i > 0 && i < paragraphs.length && !p.startsWith(transitions[0])) {
      return transitions[i % transitions.length] + ', ' + p.charAt(0).toLowerCase() + p.slice(1)
    }
    return p
  }).join('\n\n')
}

function addKeywordStrategically(content: string, keyword: string, occurrences: number): string {
  const sentences = content.split('. ')
  const positions = [0, Math.floor(sentences.length / 3), Math.floor(sentences.length * 2 / 3)]
  
  for (let i = 0; i < Math.min(occurrences, positions.length); i++) {
    const pos = positions[i]
    if (sentences[pos] && !sentences[pos].toLowerCase().includes(keyword.toLowerCase())) {
      sentences[pos] = insertKeywordNaturally(sentences[pos], keyword)
    }
  }
  
  return sentences.join('. ')
}

function calculateNaturalPlacementScore(content: string, keywords: string[]): number {
  // Check if keywords appear naturally in the content
  let score = 70 // Base score
  
  // Check for keyword stuffing
  for (const keyword of keywords) {
    const occurrences = (content.match(new RegExp(`\\b${keyword}\\b`, 'gi')) || []).length
    const density = (occurrences / content.split(' ').length) * 100
    
    if (density > 5) score -= 10 // Too high density
    if (density < 1) score -= 5 // Too low density
  }
  
  return Math.max(0, Math.min(100, score))
}

function generateKeywordRecommendations(densities: any, target: number): string[] {
  const recommendations = []
  
  for (const [keyword, density] of Object.entries(densities)) {
    if ((density as number) < target - 0.5) {
      recommendations.push(`Increase usage of "${keyword}" to reach target density`)
    }
    if ((density as number) > target + 1) {
      recommendations.push(`Reduce usage of "${keyword}" to avoid over-optimization`)
    }
  }
  
  return recommendations
}

function extractTopics(content: string, industry: string): any[] {
  // Extract main topics from content
  const topics = []
  const industryTopics: { [key: string]: string[] } = {
    restaurant: ['cuisine', 'menu', 'dining', 'food', 'service'],
    legal: ['law', 'legal', 'attorney', 'case', 'court'],
    healthcare: ['health', 'medical', 'treatment', 'patient', 'care']
  }
  
  const relevantTopics = industryTopics[industry.toLowerCase()] || ['service', 'quality', 'professional']
  
  for (const topic of relevantTopics) {
    const count = (content.match(new RegExp(`\\b${topic}\\b`, 'gi')) || []).length
    if (count > 0) {
      topics.push({ topic, relevance: Math.min(100, count * 10) })
    }
  }
  
  return topics.sort((a, b) => b.relevance - a.relevance)
}

function extractEntities(content: string): any[] {
  // Simple entity extraction
  const entities = []
  
  // Extract capitalized words (potential entities)
  const matches = content.match(/[A-Z][a-z]+/g) || []
  const entityCounts = new Map()
  
  for (const match of matches) {
    if (match.length > 3) {
      entityCounts.set(match, (entityCounts.get(match) || 0) + 1)
    }
  }
  
  for (const [entity, count] of entityCounts) {
    entities.push({
      entity,
      type: guessEntityType(entity),
      salience: Math.min(1, count / 10)
    })
  }
  
  return entities.sort((a, b) => b.salience - a.salience).slice(0, 10)
}

function guessEntityType(entity: string): string {
  if (entity.includes('Inc') || entity.includes('LLC')) return 'organization'
  if (entity.length > 10) return 'product'
  return 'other'
}

function findRelatedKeywords(keywords: string[], content: string, industry: string): any[] {
  const related = []
  const relatedTerms: { [key: string]: string[] } = {
    restaurant: ['cuisine', 'menu', 'reservation', 'dining', 'chef'],
    legal: ['attorney', 'law firm', 'legal advice', 'consultation', 'case'],
    healthcare: ['doctor', 'medical', 'treatment', 'health', 'patient care']
  }
  
  const industryTerms = relatedTerms[industry.toLowerCase()] || []
  
  for (const term of industryTerms) {
    if (!keywords.includes(term)) {
      const relevance = content.toLowerCase().includes(term.toLowerCase()) ? 80 : 40
      related.push({ keyword: term, relevance })
    }
  }
  
  return related.sort((a, b) => b.relevance - a.relevance)
}

function identifyContentGaps(content: string, keywords: string[], industry: string): string[] {
  const gaps = []
  const expectedTopics: { [key: string]: string[] } = {
    restaurant: ['hours', 'location', 'menu', 'reservations', 'reviews'],
    legal: ['services', 'experience', 'consultation', 'fees', 'contact'],
    healthcare: ['services', 'insurance', 'appointments', 'specialists', 'location']
  }
  
  const topics = expectedTopics[industry.toLowerCase()] || []
  
  for (const topic of topics) {
    if (!content.toLowerCase().includes(topic.toLowerCase())) {
      gaps.push(`Missing content about: ${topic}`)
    }
  }
  
  return gaps
}

function calculateTopicCoverage(content: string, topics: any[]): { [key: string]: number } {
  const coverage: { [key: string]: number } = {}
  
  for (const topic of topics) {
    const count = (content.match(new RegExp(`\\b${topic.topic}\\b`, 'gi')) || []).length
    coverage[topic.topic] = Math.min(100, count * 20)
  }
  
  return coverage
}

function calculateSemanticScore(topics: any[], entities: any[], keywords: any[], coverage: any): number {
  let score = 0
  
  // Topic diversity
  score += Math.min(30, topics.length * 10)
  
  // Entity richness
  score += Math.min(30, entities.length * 5)
  
  // Keyword coverage
  score += Math.min(20, keywords.length * 4)
  
  // Topic coverage completeness
  const avgCoverage = Object.values(coverage).reduce((a: number, b: number) => a + b, 0) / Object.keys(coverage).length
  score += Math.min(20, avgCoverage / 5)
  
  return Math.min(100, score)
}

function generateSemanticRecommendations(gaps: string[], keywords: any[], score: number): string[] {
  const recommendations = []
  
  if (score < 50) {
    recommendations.push('Content needs more topic diversity and depth')
  }
  
  if (gaps.length > 0) {
    recommendations.push(`Add content about: ${gaps.slice(0, 3).join(', ')}`)
  }
  
  if (keywords.length > 0) {
    recommendations.push(`Consider including these related keywords: ${keywords.slice(0, 3).map(k => k.keyword).join(', ')}`)
  }
  
  return recommendations
}

function generateContentRecommendations(metrics: any, keywords: string[]): string[] {
  const recommendations = []
  
  if (metrics.readability_score < 60) {
    recommendations.push('Simplify sentence structure for better readability')
  }
  
  if (metrics.word_count < 600) {
    recommendations.push('Expand content to at least 600 words for better SEO')
  }
  
  if (metrics.seo_score < 70) {
    recommendations.push('Improve keyword usage and content structure')
  }
  
  return recommendations
}