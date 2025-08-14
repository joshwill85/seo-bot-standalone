import { serve } from 'https://deno.land/std@0.168.0/http/server.ts'
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'
import { corsHeaders } from '../_shared/cors.ts'

interface InternalLinkingRequest {
  business_id: string
  campaign_id?: string
  website_url: string
  analysis_type?: 'full_site' | 'specific_pages' | 'content_gaps'
  target_pages?: string[]
  max_recommendations?: number
}

interface LinkOpportunity {
  source_page: string
  target_page: string
  anchor_text: string
  relevance_score: number
  link_value: number
  context: string
  priority: 'high' | 'medium' | 'low'
  link_type: 'contextual' | 'navigational' | 'footer' | 'sidebar'
  expected_impact: string
}

interface InternalLinkReport {
  total_opportunities: number
  high_priority_links: number
  content_gaps_found: number
  page_authority_distribution: {
    page: string
    authority_score: number
    incoming_links: number
    outgoing_links: number
  }[]
  link_opportunities: LinkOpportunity[]
  recommendations: {
    title: string
    description: string
    priority: string
    pages_affected: number
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
      website_url,
      analysis_type = 'full_site',
      target_pages = [],
      max_recommendations = 50
    }: InternalLinkingRequest = await req.json()

    // Validate input
    if (!business_id || !website_url) {
      return new Response(
        JSON.stringify({ error: 'business_id and website_url are required' }),
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

    // Get campaign keywords for context
    let campaignKeywords: any[] = []
    if (campaign_id) {
      const { data: keywords } = await supabase
        .from('keywords')
        .select('keyword, intent, search_volume, keyword_difficulty')
        .eq('campaign_id', campaign_id)
        .order('value_score', { ascending: false })
        .limit(100)
      
      campaignKeywords = keywords || []
    }

    // Get existing content briefs for link opportunities
    const { data: contentBriefs } = await supabase
      .from('content_briefs')
      .select('title, slug, target_keyword, status')
      .eq('campaign_id', campaign_id || '')
      .limit(50)

    // Perform internal linking analysis
    const linkingReport = await analyzeInternalLinking(
      website_url,
      business,
      campaignKeywords,
      contentBriefs || [],
      analysis_type,
      target_pages,
      max_recommendations
    )

    // Store linking opportunities in database
    const linkRecords = []
    for (const opportunity of linkingReport.link_opportunities.slice(0, 20)) {
      const { data: linkRecord } = await supabase
        .from('internal_links')
        .insert({
          business_id,
          campaign_id,
          source_page: opportunity.source_page,
          target_page: opportunity.target_page,
          anchor_text: opportunity.anchor_text,
          relevance_score: opportunity.relevance_score,
          link_value: opportunity.link_value,
          priority: opportunity.priority,
          link_type: opportunity.link_type,
          context: opportunity.context,
          expected_impact: opportunity.expected_impact,
          status: 'pending',
          analysis_type
        })
        .select()
        .single()

      if (linkRecord) {
        linkRecords.push(linkRecord)
      }
    }

    // Log the analysis
    await supabase
      .from('seo_logs')
      .insert({
        business_id,
        action_type: 'internal_linking',
        action_description: `Internal linking analysis completed. Found ${linkingReport.total_opportunities} opportunities`,
        new_data: JSON.stringify({
          campaign_id,
          website_url,
          analysis_type,
          total_opportunities: linkingReport.total_opportunities,
          high_priority_links: linkingReport.high_priority_links
        })
      })

    return new Response(
      JSON.stringify({
        success: true,
        analysis_type,
        website_analyzed: website_url,
        opportunities_found: linkingReport.total_opportunities,
        high_priority_count: linkingReport.high_priority_links,
        records_stored: linkRecords.length,
        report: {
          summary: {
            total_opportunities: linkingReport.total_opportunities,
            high_priority_links: linkingReport.high_priority_links,
            content_gaps_found: linkingReport.content_gaps_found
          },
          page_authority: linkingReport.page_authority_distribution.slice(0, 10),
          top_opportunities: linkingReport.link_opportunities.slice(0, 10),
          recommendations: linkingReport.recommendations
        }
      }),
      { 
        status: 200, 
        headers: { ...corsHeaders, 'Content-Type': 'application/json' } 
      }
    )

  } catch (error) {
    console.error('Internal linking analysis error:', error)
    return new Response(
      JSON.stringify({ error: 'Internal server error', details: error.message }),
      { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }
})

async function analyzeInternalLinking(
  websiteUrl: string,
  business: any,
  keywords: any[],
  contentBriefs: any[],
  analysisType: string,
  targetPages: string[],
  maxRecommendations: number
): Promise<InternalLinkReport> {
  
  // Simulate website crawling and analysis
  const sitePages = await simulateWebsiteCrawl(websiteUrl, business, analysisType, targetPages)
  
  // Analyze page authority distribution
  const pageAuthority = calculatePageAuthority(sitePages)
  
  // Find linking opportunities
  const linkOpportunities = findLinkingOpportunities(
    sitePages,
    keywords,
    contentBriefs,
    business,
    maxRecommendations
  )
  
  // Identify content gaps
  const contentGaps = identifyContentGaps(sitePages, keywords, business)
  
  // Generate strategic recommendations
  const recommendations = generateLinkingRecommendations(
    linkOpportunities,
    pageAuthority,
    contentGaps,
    business
  )

  const highPriorityLinks = linkOpportunities.filter(link => link.priority === 'high').length

  return {
    total_opportunities: linkOpportunities.length,
    high_priority_links: highPriorityLinks,
    content_gaps_found: contentGaps.length,
    page_authority_distribution: pageAuthority,
    link_opportunities: linkOpportunities,
    recommendations
  }
}

async function simulateWebsiteCrawl(
  websiteUrl: string,
  business: any,
  analysisType: string,
  targetPages: string[]
): Promise<any[]> {
  
  // Simulate common website pages based on industry
  const basePages = [
    { url: websiteUrl, title: `${business.business_name} - Home`, type: 'homepage' },
    { url: `${websiteUrl}/about`, title: 'About Us', type: 'about' },
    { url: `${websiteUrl}/services`, title: 'Our Services', type: 'services' },
    { url: `${websiteUrl}/contact`, title: 'Contact Us', type: 'contact' },
    { url: `${websiteUrl}/blog`, title: 'Blog', type: 'blog' }
  ]

  // Add industry-specific pages
  const industryPages = getIndustrySpecificPages(websiteUrl, business.industry)
  
  // Add content brief pages
  const contentPages = getContentBriefPages(websiteUrl, business)
  
  // Combine all pages
  let allPages = [...basePages, ...industryPages, ...contentPages]
  
  // Filter based on analysis type
  if (analysisType === 'specific_pages' && targetPages.length > 0) {
    allPages = allPages.filter(page => 
      targetPages.some(target => page.url.includes(target))
    )
  }
  
  // Simulate page content and metadata
  return allPages.map(page => ({
    ...page,
    word_count: 500 + Math.floor(Math.random() * 1500),
    headings: generatePageHeadings(page.title, page.type, business),
    meta_description: `${page.title} - Professional ${business.industry} services.`,
    internal_links: Math.floor(Math.random() * 8) + 2,
    external_links: Math.floor(Math.random() * 5),
    images: Math.floor(Math.random() * 10) + 1,
    last_modified: new Date(Date.now() - Math.random() * 90 * 24 * 60 * 60 * 1000).toISOString()
  }))
}

function getIndustrySpecificPages(websiteUrl: string, industry: string): any[] {
  const industryMap: { [key: string]: any[] } = {
    restaurant: [
      { url: `${websiteUrl}/menu`, title: 'Menu', type: 'menu' },
      { url: `${websiteUrl}/reservations`, title: 'Reservations', type: 'reservations' },
      { url: `${websiteUrl}/catering`, title: 'Catering Services', type: 'services' },
      { url: `${websiteUrl}/events`, title: 'Private Events', type: 'services' }
    ],
    legal: [
      { url: `${websiteUrl}/practice-areas`, title: 'Practice Areas', type: 'services' },
      { url: `${websiteUrl}/attorneys`, title: 'Our Attorneys', type: 'team' },
      { url: `${websiteUrl}/case-results`, title: 'Case Results', type: 'results' },
      { url: `${websiteUrl}/resources`, title: 'Legal Resources', type: 'resources' }
    ],
    healthcare: [
      { url: `${websiteUrl}/services`, title: 'Medical Services', type: 'services' },
      { url: `${websiteUrl}/doctors`, title: 'Our Doctors', type: 'team' },
      { url: `${websiteUrl}/insurance`, title: 'Insurance Information', type: 'insurance' },
      { url: `${websiteUrl}/patient-portal`, title: 'Patient Portal', type: 'portal' }
    ],
    hvac: [
      { url: `${websiteUrl}/repair`, title: 'HVAC Repair', type: 'services' },
      { url: `${websiteUrl}/installation`, title: 'Installation Services', type: 'services' },
      { url: `${websiteUrl}/maintenance`, title: 'Maintenance Plans', type: 'services' },
      { url: `${websiteUrl}/emergency`, title: '24/7 Emergency Service', type: 'emergency' }
    ]
  }
  
  const industryKey = Object.keys(industryMap).find(key => 
    industry.toLowerCase().includes(key)
  )
  
  return industryMap[industryKey] || []
}

function getContentBriefPages(websiteUrl: string, business: any): any[] {
  // Simulate existing content pages
  const contentPages = [
    { url: `${websiteUrl}/blog/guide-to-services`, title: `Complete Guide to ${business.industry} Services`, type: 'blog_post' },
    { url: `${websiteUrl}/blog/choosing-the-right-provider`, title: 'How to Choose the Right Provider', type: 'blog_post' },
    { url: `${websiteUrl}/blog/cost-factors`, title: 'Understanding Cost Factors', type: 'blog_post' },
    { url: `${websiteUrl}/blog/local-insights`, title: 'Local Market Insights', type: 'blog_post' }
  ]
  
  return contentPages
}

function generatePageHeadings(title: string, type: string, business: any): string[] {
  const baseHeadings = [title]
  
  const headingTemplates: { [key: string]: string[] } = {
    homepage: ['Welcome', 'Our Services', 'Why Choose Us', 'Contact Information'],
    about: ['Our Story', 'Our Mission', 'Our Team', 'Our Values'],
    services: ['Service Overview', 'What We Offer', 'Service Areas', 'Get Started'],
    contact: ['Contact Information', 'Office Hours', 'Service Areas', 'Get In Touch'],
    blog_post: ['Introduction', 'Key Points', 'Benefits', 'Conclusion'],
    team: ['Meet Our Team', 'Experience', 'Qualifications', 'Contact']
  }
  
  const templateHeadings = headingTemplates[type] || headingTemplates.services
  return [...baseHeadings, ...templateHeadings]
}

function calculatePageAuthority(pages: any[]): any[] {
  return pages.map(page => {
    // Simulate page authority calculation
    let authorityScore = 50 // Base score
    
    // Adjust based on page type
    if (page.type === 'homepage') authorityScore += 30
    if (page.type === 'services') authorityScore += 20
    if (page.type === 'about') authorityScore += 15
    if (page.type === 'blog_post') authorityScore += 10
    
    // Adjust based on content
    if (page.word_count > 1000) authorityScore += 10
    if (page.word_count > 2000) authorityScore += 5
    
    // Add some randomness
    authorityScore += Math.floor(Math.random() * 20) - 10
    
    return {
      page: page.url,
      authority_score: Math.max(10, Math.min(100, authorityScore)),
      incoming_links: page.internal_links || 0,
      outgoing_links: Math.floor(Math.random() * 12) + 3
    }
  }).sort((a, b) => b.authority_score - a.authority_score)
}

function findLinkingOpportunities(
  pages: any[],
  keywords: any[],
  contentBriefs: any[],
  business: any,
  maxRecommendations: number
): LinkOpportunity[] {
  
  const opportunities: LinkOpportunity[] = []
  
  // Cross-link content pages
  for (const sourcePage of pages) {
    for (const targetPage of pages) {
      if (sourcePage.url === targetPage.url) continue
      
      const relevanceScore = calculatePageRelevance(sourcePage, targetPage, keywords)
      if (relevanceScore > 0.3) {
        const opportunity = createLinkOpportunity(
          sourcePage, 
          targetPage, 
          relevanceScore, 
          keywords,
          business
        )
        opportunities.push(opportunity)
      }
    }
  }
  
  // Link to high-authority pages
  const highAuthorityPages = pages
    .filter(page => ['homepage', 'services', 'about'].includes(page.type))
    .slice(0, 5)
  
  for (const contentPage of pages.filter(p => p.type === 'blog_post')) {
    for (const authorityPage of highAuthorityPages) {
      const opportunity = createLinkOpportunity(
        contentPage,
        authorityPage,
        0.7,
        keywords,
        business
      )
      opportunity.link_type = 'navigational'
      opportunity.priority = 'high'
      opportunities.push(opportunity)
    }
  }
  
  // Create hub page opportunities
  const hubOpportunities = createHubPageOpportunities(pages, keywords, business)
  opportunities.push(...hubOpportunities)
  
  return opportunities
    .sort((a, b) => b.link_value - a.link_value)
    .slice(0, maxRecommendations)
}

function calculatePageRelevance(sourcePage: any, targetPage: any, keywords: any[]): number {
  let relevance = 0
  
  // Topic similarity
  const sourceWords = extractWords(sourcePage.title)
  const targetWords = extractWords(targetPage.title)
  const commonWords = sourceWords.filter(word => targetWords.includes(word))
  
  if (commonWords.length > 0) {
    relevance += 0.4
  }
  
  // Page type relationships
  const typeRelations: { [key: string]: string[] } = {
    homepage: ['services', 'about', 'contact'],
    services: ['blog_post', 'contact', 'about'],
    blog_post: ['services', 'contact', 'homepage'],
    about: ['services', 'contact', 'team']
  }
  
  if (typeRelations[sourcePage.type]?.includes(targetPage.type)) {
    relevance += 0.3
  }
  
  // Keyword relevance
  const pageKeywords = keywords.filter(k => 
    sourcePage.title.toLowerCase().includes(k.keyword.toLowerCase()) ||
    targetPage.title.toLowerCase().includes(k.keyword.toLowerCase())
  )
  
  if (pageKeywords.length > 0) {
    relevance += 0.3
  }
  
  return Math.min(1.0, relevance)
}

function createLinkOpportunity(
  sourcePage: any,
  targetPage: any,
  relevanceScore: number,
  keywords: any[],
  business: any
): LinkOpportunity {
  
  const anchorText = generateAnchorText(targetPage, keywords, business)
  const linkValue = calculateLinkValue(sourcePage, targetPage, relevanceScore)
  const priority = linkValue > 0.7 ? 'high' : linkValue > 0.4 ? 'medium' : 'low'
  
  return {
    source_page: sourcePage.url,
    target_page: targetPage.url,
    anchor_text: anchorText,
    relevance_score: relevanceScore,
    link_value: linkValue,
    context: generateLinkContext(sourcePage, targetPage, business),
    priority,
    link_type: 'contextual',
    expected_impact: generateExpectedImpact(linkValue, targetPage.type)
  }
}

function generateAnchorText(targetPage: any, keywords: any[], business: any): string {
  const anchorOptions = [
    targetPage.title,
    `${business.business_name} ${targetPage.type}`,
    `Learn more about ${targetPage.title.toLowerCase()}`,
    `Our ${targetPage.type} page`
  ]
  
  // Add keyword-based anchors
  const relevantKeywords = keywords.filter(k => 
    targetPage.title.toLowerCase().includes(k.keyword.toLowerCase())
  )
  
  if (relevantKeywords.length > 0) {
    anchorOptions.push(relevantKeywords[0].keyword)
  }
  
  return anchorOptions[Math.floor(Math.random() * anchorOptions.length)]
}

function calculateLinkValue(sourcePage: any, targetPage: any, relevanceScore: number): number {
  let value = relevanceScore * 0.5
  
  // Source page value
  if (sourcePage.type === 'homepage') value += 0.3
  if (sourcePage.type === 'services') value += 0.2
  if (sourcePage.word_count > 1000) value += 0.1
  
  // Target page value
  if (targetPage.type === 'services') value += 0.2
  if (targetPage.type === 'blog_post') value += 0.1
  
  // Freshness factor
  const daysOld = (Date.now() - new Date(targetPage.last_modified).getTime()) / (1000 * 60 * 60 * 24)
  if (daysOld < 30) value += 0.1
  
  return Math.min(1.0, value)
}

function generateLinkContext(sourcePage: any, targetPage: any, business: any): string {
  const contexts = [
    `Link from ${sourcePage.type} to ${targetPage.type} for improved navigation`,
    `Contextual link about ${business.industry} services`,
    `Reference to detailed information on ${targetPage.title}`,
    `Cross-reference to related content`,
    `Call-to-action linking to ${targetPage.type}`
  ]
  
  return contexts[Math.floor(Math.random() * contexts.length)]
}

function generateExpectedImpact(linkValue: number, targetPageType: string): string {
  if (linkValue > 0.7) {
    return `High impact: Significant boost to ${targetPageType} page authority and user engagement`
  } else if (linkValue > 0.4) {
    return `Medium impact: Moderate improvement in page authority and user flow`
  } else {
    return `Low impact: Minor improvement in internal linking structure`
  }
}

function createHubPageOpportunities(pages: any[], keywords: any[], business: any): LinkOpportunity[] {
  const hubOpportunities: LinkOpportunity[] = []
  
  // Identify potential hub pages
  const servicesPage = pages.find(p => p.type === 'services')
  const blogPosts = pages.filter(p => p.type === 'blog_post')
  
  if (servicesPage && blogPosts.length > 0) {
    for (const blogPost of blogPosts) {
      const opportunity: LinkOpportunity = {
        source_page: blogPost.url,
        target_page: servicesPage.url,
        anchor_text: `Our ${business.industry} Services`,
        relevance_score: 0.8,
        link_value: 0.9,
        context: 'Hub page linking strategy to consolidate page authority',
        priority: 'high',
        link_type: 'contextual',
        expected_impact: 'High impact: Consolidates authority to main services page'
      }
      
      hubOpportunities.push(opportunity)
    }
  }
  
  return hubOpportunities
}

function identifyContentGaps(pages: any[], keywords: any[], business: any): string[] {
  const existingTopics = new Set(
    pages.map(page => extractWords(page.title)).flat()
  )
  
  const missingTopics = keywords
    .filter(k => !Array.from(existingTopics).some(topic => 
      k.keyword.toLowerCase().includes(topic.toLowerCase())
    ))
    .slice(0, 10)
    .map(k => k.keyword)
  
  return missingTopics
}

function generateLinkingRecommendations(
  opportunities: LinkOpportunity[],
  pageAuthority: any[],
  contentGaps: string[],
  business: any
): any[] {
  
  const recommendations = []
  
  // High-priority linking recommendation
  const highPriorityCount = opportunities.filter(op => op.priority === 'high').length
  if (highPriorityCount > 0) {
    recommendations.push({
      title: 'Implement High-Priority Internal Links',
      description: `${highPriorityCount} high-value linking opportunities identified that could significantly improve page authority distribution`,
      priority: 'high',
      pages_affected: highPriorityCount
    })
  }
  
  // Hub page strategy
  const hubOpportunities = opportunities.filter(op => op.context.includes('hub'))
  if (hubOpportunities.length > 3) {
    recommendations.push({
      title: 'Implement Hub Page Strategy',
      description: 'Create topic clusters by linking related content to main service pages to consolidate authority',
      priority: 'high',
      pages_affected: hubOpportunities.length
    })
  }
  
  // Content gap recommendations
  if (contentGaps.length > 0) {
    recommendations.push({
      title: 'Address Content Gaps',
      description: `Create content for ${contentGaps.length} missing topics to capture additional keyword opportunities`,
      priority: 'medium',
      pages_affected: contentGaps.length
    })
  }
  
  // Page authority distribution
  const lowAuthorityPages = pageAuthority.filter(p => p.authority_score < 30).length
  if (lowAuthorityPages > 0) {
    recommendations.push({
      title: 'Boost Low Authority Pages',
      description: `${lowAuthorityPages} pages have low authority scores and could benefit from strategic internal linking`,
      priority: 'medium',
      pages_affected: lowAuthorityPages
    })
  }
  
  return recommendations
}

function extractWords(text: string): string[] {
  return text.toLowerCase()
    .split(/\s+/)
    .filter(word => word.length > 3 && !['the', 'and', 'for', 'with'].includes(word))
}