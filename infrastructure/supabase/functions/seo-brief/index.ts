import { serve } from 'https://deno.land/std@0.168.0/http/server.ts'
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'
import { corsHeaders } from '../_shared/cors.ts'

interface ContentBriefRequest {
  business_id: string
  campaign_id?: string
  target_keyword: string
  content_type?: 'article' | 'howto' | 'comparison' | 'listicle' | 'landing_page'
  word_count_target?: number
  secondary_keywords?: string[]
}

interface InfoGainItem {
  title: string
  description: string
  search_volume?: number
  competition_gap: boolean
  content_angle: string
}

interface ContentBrief {
  title: string
  slug: string
  target_keyword: string
  secondary_keywords: string[]
  content_type: string
  word_count_target: number
  meta_description: string
  h1_tag: string
  info_gain_items: InfoGainItem[]
  content_outline: {
    section: string
    subsections: string[]
    word_count: number
  }[]
  competitor_analysis: {
    url: string
    word_count: number
    headings: string[]
    missing_topics: string[]
  }[]
  internal_link_opportunities: string[]
  cta_recommendations: string[]
  content_gaps: string[]
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
      target_keyword, 
      content_type = 'article', 
      word_count_target = 1500,
      secondary_keywords = []
    }: ContentBriefRequest = await req.json()

    // Validate input
    if (!business_id || !target_keyword) {
      return new Response(
        JSON.stringify({ error: 'business_id and target_keyword are required' }),
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

    // Get campaign if specified
    let campaign = null
    if (campaign_id) {
      const { data } = await supabase
        .from('seo_campaigns')
        .select('*')
        .eq('id', campaign_id)
        .single()
      campaign = data
    }

    // Get related keywords from database
    const { data: relatedKeywords } = await supabase
      .from('keywords')
      .select('keyword, intent, search_volume, keyword_difficulty')
      .eq('campaign_id', campaign_id || '')
      .ilike('keyword', `%${target_keyword.split(' ')[0]}%`)
      .limit(20)

    // Generate content brief
    const contentBrief = await generateContentBrief(
      business,
      target_keyword,
      content_type,
      word_count_target,
      secondary_keywords,
      relatedKeywords || []
    )

    // Store content brief in database
    const { data: briefRecord } = await supabase
      .from('content_briefs')
      .insert({
        campaign_id: campaign_id || null,
        title: contentBrief.title,
        slug: contentBrief.slug,
        target_keyword: contentBrief.target_keyword,
        secondary_keywords: contentBrief.secondary_keywords,
        content_type: contentBrief.content_type,
        word_count_target: contentBrief.word_count_target,
        meta_description: contentBrief.meta_description,
        h1_tag: contentBrief.h1_tag,
        info_gain_items: contentBrief.info_gain_items,
        content_outline: contentBrief.content_outline,
        competitor_analysis: contentBrief.competitor_analysis,
        internal_link_opportunities: contentBrief.internal_link_opportunities,
        content_gaps: contentBrief.content_gaps,
        status: 'draft',
        priority_score: calculatePriorityScore(target_keyword, business.industry)
      })
      .select()
      .single()

    // Log the brief generation
    await supabase
      .from('seo_logs')
      .insert({
        business_id,
        action_type: 'content_brief',
        action_description: `Content brief generated for "${target_keyword}"`,
        new_data: JSON.stringify({
          brief_id: briefRecord?.id,
          target_keyword: target_keyword,
          content_type: content_type,
          word_count: word_count_target
        })
      })

    return new Response(
      JSON.stringify({
        success: true,
        brief_id: briefRecord?.id,
        content_brief: contentBrief
      }),
      { 
        status: 200, 
        headers: { ...corsHeaders, 'Content-Type': 'application/json' } 
      }
    )

  } catch (error) {
    console.error('Content brief generation error:', error)
    return new Response(
      JSON.stringify({ error: 'Internal server error', details: error.message }),
      { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }
})

async function generateContentBrief(
  business: any,
  targetKeyword: string,
  contentType: string,
  wordCountTarget: number,
  secondaryKeywords: string[],
  relatedKeywords: any[]
): Promise<ContentBrief> {
  
  // Generate title based on content type and keyword
  const title = generateTitle(targetKeyword, contentType, business)
  
  // Create URL-friendly slug
  const slug = title.toLowerCase()
    .replace(/[^a-z0-9\s-]/g, '')
    .replace(/\s+/g, '-')
    .substring(0, 60)

  // Generate meta description
  const metaDescription = generateMetaDescription(title, targetKeyword, business)

  // Create H1 tag
  const h1Tag = title.length > 60 ? 
    generateAlternativeH1(targetKeyword, business) : title

  // Generate info gain items (unique value propositions)
  const infoGainItems = generateInfoGainItems(targetKeyword, business, contentType)

  // Create content outline
  const contentOutline = generateContentOutline(targetKeyword, contentType, wordCountTarget, business)

  // Simulate competitor analysis
  const competitorAnalysis = await simulateCompetitorAnalysis(targetKeyword, business)

  // Generate internal linking opportunities
  const internalLinkOpportunities = generateInternalLinkOpportunities(targetKeyword, business)

  // Generate CTA recommendations
  const ctaRecommendations = generateCTARecommendations(contentType, business)

  // Identify content gaps
  const contentGaps = identifyContentGaps(targetKeyword, business, relatedKeywords)

  // Combine secondary keywords with related keywords
  const allSecondaryKeywords = [
    ...secondaryKeywords,
    ...relatedKeywords.slice(0, 5).map(k => k.keyword)
  ].filter((keyword, index, self) => self.indexOf(keyword) === index)

  return {
    title,
    slug,
    target_keyword: targetKeyword,
    secondary_keywords: allSecondaryKeywords,
    content_type: contentType,
    word_count_target: wordCountTarget,
    meta_description: metaDescription,
    h1_tag: h1Tag,
    info_gain_items: infoGainItems,
    content_outline: contentOutline,
    competitor_analysis: competitorAnalysis,
    internal_link_opportunities: internalLinkOpportunities,
    cta_recommendations: ctaRecommendations,
    content_gaps: contentGaps
  }
}

function generateTitle(keyword: string, contentType: string, business: any): string {
  const location = business.city || 'Florida'
  const year = new Date().getFullYear()
  
  const titleTemplates = {
    article: [
      `Complete Guide to ${keyword} in ${location} (${year})`,
      `Everything You Need to Know About ${keyword}`,
      `${keyword}: The Ultimate ${location} Guide`,
      `Top ${keyword} Tips for ${location} Residents`
    ],
    howto: [
      `How to Choose the Best ${keyword} in ${location}`,
      `Step-by-Step Guide: ${keyword} in ${location}`,
      `${keyword}: A Complete How-To Guide for ${location}`,
      `The Complete Process: ${keyword} Explained`
    ],
    comparison: [
      `${keyword} vs Alternatives: ${location} Comparison Guide`,
      `Best ${keyword} Options in ${location}: Detailed Comparison`,
      `Comparing ${keyword} Services in ${location}`,
      `${keyword} Comparison: Which is Right for You?`
    ],
    listicle: [
      `Top 10 ${keyword} Options in ${location} (${year})`,
      `Best ${keyword} Services: ${location} Edition`,
      `${location}'s Top ${keyword} Providers`,
      `10 Best ${keyword} Choices in ${location}`
    ],
    landing_page: [
      `Professional ${keyword} Services in ${location}`,
      `${keyword} - ${business.business_name}`,
      `Expert ${keyword} in ${location}`,
      `${location} ${keyword} Services`
    ]
  }

  const templates = titleTemplates[contentType as keyof typeof titleTemplates] || titleTemplates.article
  return templates[Math.floor(Math.random() * templates.length)]
    .replace(/\b\w/g, l => l.toUpperCase())
}

function generateMetaDescription(title: string, keyword: string, business: any): string {
  const location = business.city || 'Florida'
  
  const descriptions = [
    `Looking for ${keyword} in ${location}? Our comprehensive guide covers everything you need to know. Expert advice, local insights, and proven strategies.`,
    `Discover the best ${keyword} solutions in ${location}. Professional guidance, local expertise, and detailed information to help you make informed decisions.`,
    `Expert ${keyword} services in ${location}. Get professional advice, compare options, and find the perfect solution for your needs.`,
    `Complete ${keyword} guide for ${location} residents. Professional insights, expert tips, and local recommendations you can trust.`
  ]
  
  return descriptions[Math.floor(Math.random() * descriptions.length)]
    .substring(0, 155)
}

function generateAlternativeH1(keyword: string, business: any): string {
  const location = business.city || 'Florida'
  
  const h1Options = [
    `${keyword} in ${location}: Complete Guide`,
    `Professional ${keyword} Services`,
    `Your Guide to ${keyword}`,
    `${keyword}: Expert Solutions in ${location}`
  ]
  
  return h1Options[Math.floor(Math.random() * h1Options.length)]
}

function generateInfoGainItems(keyword: string, business: any, contentType: string): InfoGainItem[] {
  const location = business.city || 'Florida'
  const industry = business.industry || 'services'
  
  const baseItems = [
    {
      title: `${location}-Specific Requirements`,
      description: `Local regulations, permits, and requirements specific to ${location}`,
      competition_gap: true,
      content_angle: 'local_expertise'
    },
    {
      title: 'Cost Analysis Calculator',
      description: `Interactive tool to estimate ${keyword} costs in ${location}`,
      search_volume: 450,
      competition_gap: true,
      content_angle: 'interactive_tool'
    },
    {
      title: 'Step-by-Step Process Guide',
      description: `Detailed walkthrough of the ${keyword} process from start to finish`,
      competition_gap: false,
      content_angle: 'educational'
    },
    {
      title: 'Common Mistakes to Avoid',
      description: `Top 10 mistakes people make when choosing ${keyword} services`,
      search_volume: 280,
      competition_gap: true,
      content_angle: 'problem_solving'
    },
    {
      title: 'Before and After Examples',
      description: `Real ${location} case studies showing ${keyword} results`,
      competition_gap: true,
      content_angle: 'social_proof'
    }
  ]
  
  // Add industry-specific items
  if (industry.toLowerCase().includes('legal')) {
    baseItems.push({
      title: 'Legal Timeline and Process',
      description: `Expected timeline and legal procedures for ${keyword} cases`,
      competition_gap: true,
      content_angle: 'process_transparency'
    })
  }
  
  if (industry.toLowerCase().includes('restaurant') || industry.toLowerCase().includes('food')) {
    baseItems.push({
      title: 'Menu and Pricing Guide',
      description: `Detailed menu options and pricing for ${keyword}`,
      competition_gap: true,
      content_angle: 'transparency'
    })
  }
  
  return baseItems.slice(0, 5)
}

function generateContentOutline(keyword: string, contentType: string, wordCount: number, business: any): any[] {
  const location = business.city || 'Florida'
  
  const baseOutlines = {
    article: [
      {
        section: `Introduction to ${keyword}`,
        subsections: ['What is it?', 'Why it matters', `${location} context`],
        word_count: Math.round(wordCount * 0.15)
      },
      {
        section: `Understanding ${keyword} in ${location}`,
        subsections: ['Local regulations', 'Market overview', 'Key considerations'],
        word_count: Math.round(wordCount * 0.25)
      },
      {
        section: `How to Choose the Right ${keyword}`,
        subsections: ['Selection criteria', 'Questions to ask', 'Red flags to avoid'],
        word_count: Math.round(wordCount * 0.25)
      },
      {
        section: 'Cost and Pricing',
        subsections: ['Pricing factors', 'Average costs', 'Value considerations'],
        word_count: Math.round(wordCount * 0.15)
      },
      {
        section: 'Next Steps',
        subsections: ['Action plan', 'Getting started', 'Contact information'],
        word_count: Math.round(wordCount * 0.2)
      }
    ],
    howto: [
      {
        section: 'Getting Started',
        subsections: ['Prerequisites', 'What you need', 'Preparation steps'],
        word_count: Math.round(wordCount * 0.2)
      },
      {
        section: 'Step-by-Step Process',
        subsections: ['Step 1: Initial research', 'Step 2: Evaluation', 'Step 3: Decision'],
        word_count: Math.round(wordCount * 0.4)
      },
      {
        section: 'Common Challenges',
        subsections: ['Potential issues', 'How to overcome them', 'Expert tips'],
        word_count: Math.round(wordCount * 0.25)
      },
      {
        section: 'Final Steps',
        subsections: ['Verification', 'Follow-up', 'Maintenance'],
        word_count: Math.round(wordCount * 0.15)
      }
    ]
  }
  
  return baseOutlines[contentType as keyof typeof baseOutlines] || baseOutlines.article
}

async function simulateCompetitorAnalysis(keyword: string, business: any): Promise<any[]> {
  // Simulate competitor analysis (in real implementation, this would scrape competitor pages)
  const competitors = [
    {
      url: `https://competitor1-${business.industry?.toLowerCase()}.com`,
      word_count: 1200 + Math.floor(Math.random() * 800),
      headings: [
        `About ${keyword}`,
        'Our Services',
        'Why Choose Us',
        'Contact Information'
      ],
      missing_topics: ['Local regulations', 'Cost transparency', 'Process timeline']
    },
    {
      url: `https://competitor2-${business.industry?.toLowerCase()}.com`,
      word_count: 800 + Math.floor(Math.random() * 600),
      headings: [
        `${keyword} Services`,
        'Pricing',
        'Reviews'
      ],
      missing_topics: ['Step-by-step process', 'Common mistakes', 'Local expertise']
    }
  ]
  
  return competitors
}

function generateInternalLinkOpportunities(keyword: string, business: any): string[] {
  const basePages = [
    'About Us',
    'Services',
    'Contact',
    'Blog',
    'FAQ'
  ]
  
  const industrySpecific = {
    restaurant: ['Menu', 'Reservations', 'Events', 'Catering'],
    legal: ['Practice Areas', 'Attorney Profiles', 'Case Results', 'Resources'],
    healthcare: ['Services', 'Doctors', 'Insurance', 'Patient Portal'],
    hvac: ['Services', 'Emergency Repair', 'Maintenance', 'Installation']
  }
  
  const industry = business.industry?.toLowerCase() || ''
  const specificPages = Object.entries(industrySpecific).find(([key]) => 
    industry.includes(key)
  )?.[1] || []
  
  return [...basePages, ...specificPages].slice(0, 6)
}

function generateCTARecommendations(contentType: string, business: any): string[] {
  const baseCTAs = [
    'Contact us for a free consultation',
    'Get your personalized quote today',
    'Schedule your appointment now',
    'Call for expert advice'
  ]
  
  const industrySpecific = {
    restaurant: ['Make a reservation', 'Order online', 'View our menu', 'Book your event'],
    legal: ['Free case evaluation', 'Speak with an attorney', 'Schedule consultation', 'Get legal help now'],
    healthcare: ['Book appointment', 'Contact our office', 'Insurance verification', 'Patient portal login'],
    hvac: ['Emergency service call', 'Free estimate', 'Schedule maintenance', '24/7 repair service']
  }
  
  const industry = business.industry?.toLowerCase() || ''
  const specificCTAs = Object.entries(industrySpecific).find(([key]) => 
    industry.includes(key)
  )?.[1] || []
  
  return [...baseCTAs, ...specificCTAs].slice(0, 4)
}

function identifyContentGaps(keyword: string, business: any, relatedKeywords: any[]): string[] {
  const commonGaps = [
    'Mobile optimization considerations',
    'Local market trends and data',
    'Customer testimonials and reviews',
    'Comparison with alternatives',
    'Frequently asked questions',
    'Process timeline and expectations'
  ]
  
  // Add gaps based on related keywords
  const keywordGaps = relatedKeywords
    .filter(k => !k.keyword.includes(keyword))
    .slice(0, 3)
    .map(k => `Content about "${k.keyword}"`)
  
  return [...commonGaps, ...keywordGaps].slice(0, 6)
}

function calculatePriorityScore(keyword: string, industry?: string): number {
  let score = 5.0 // Base score
  
  // Adjust based on keyword characteristics
  if (keyword.includes('best') || keyword.includes('top')) score += 1.5
  if (keyword.includes('near me') || keyword.includes('local')) score += 1.0
  if (keyword.split(' ').length > 3) score += 0.5 // Long-tail bonus
  
  // Industry adjustments
  const highValueIndustries = ['legal', 'healthcare', 'finance', 'real estate']
  if (industry && highValueIndustries.some(i => industry.toLowerCase().includes(i))) {
    score += 1.0
  }
  
  return Math.min(10.0, score)
}