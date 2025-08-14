import { serve } from 'https://deno.land/std@0.168.0/http/server.ts'
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'
import { corsHeaders } from '../_shared/cors.ts'

interface GSCRequest {
  business_id: string
  campaign_id?: string
  action: 'authenticate' | 'sync' | 'query' | 'configure'
  auth_code?: string
  site_url?: string
  date_range?: 'last_7_days' | 'last_30_days' | 'last_90_days'
  query_type?: 'search_analytics' | 'pages' | 'queries' | 'countries' | 'devices'
  filters?: any[]
}

interface GSCSearchAnalytics {
  query: string
  page: string
  country: string
  device: string
  clicks: number
  impressions: number
  ctr: number
  position: number
  date: string
}

interface GSCConfig {
  site_url: string
  access_token: string
  refresh_token: string
  token_expires_at: string
  verification_status: 'verified' | 'unverified' | 'pending'
  permission_level: 'owner' | 'full_user' | 'restricted_user'
  last_sync: string
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
      auth_code,
      site_url,
      date_range = 'last_30_days',
      query_type = 'search_analytics',
      filters = []
    }: GSCRequest = await req.json()

    // Validate required fields
    if (!business_id || !action) {
      return new Response(
        JSON.stringify({ error: 'business_id and action are required' }),
        { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    // Validate business exists
    const { data: business } = await supabase
      .from('businesses')
      .select('id, business_name, website_url')
      .eq('id', business_id)
      .single()

    if (!business) {
      return new Response(
        JSON.stringify({ error: 'Business not found' }),
        { status: 404, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    switch (action) {
      case 'authenticate':
        return await handleGSCAuthentication(supabase, business, auth_code, site_url)
      case 'sync':
        return await handleGSCSync(supabase, business, campaign_id, date_range)
      case 'query':
        return await handleGSCQuery(supabase, business, query_type, date_range, filters)
      case 'configure':
        return await handleGSCConfiguration(supabase, business, site_url)
      default:
        return new Response(
          JSON.stringify({ error: 'Invalid action' }),
          { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
        )
    }

  } catch (error) {
    console.error('GSC integration error:', error)
    return new Response(
      JSON.stringify({ error: 'Internal server error', details: error.message }),
      { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }
})

async function handleGSCAuthentication(supabase: any, business: any, auth_code?: string, site_url?: string) {
  if (!auth_code || !site_url) {
    // Return OAuth URL for authentication
    const authUrl = generateGSCAuthUrl(business.id, site_url || business.website_url)
    
    return new Response(
      JSON.stringify({
        success: true,
        auth_required: true,
        auth_url: authUrl,
        instructions: 'Visit the auth_url to authorize Google Search Console access'
      }),
      { 
        status: 200, 
        headers: { ...corsHeaders, 'Content-Type': 'application/json' } 
      }
    )
  }

  // Exchange auth code for tokens (simulated)
  const tokenData = await exchangeAuthCodeForTokens(auth_code)
  
  // Store GSC configuration
  const { data: gscConfig, error } = await supabase
    .from('gsc_configurations')
    .upsert({
      business_id: business.id,
      site_url: site_url,
      access_token: tokenData.access_token,
      refresh_token: tokenData.refresh_token,
      token_expires_at: tokenData.expires_at,
      verification_status: 'verified',
      permission_level: 'full_user',
      last_sync: null,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    }, {
      onConflict: 'business_id,site_url'
    })
    .select()
    .single()

  if (error) {
    return new Response(
      JSON.stringify({ error: 'Failed to store GSC configuration', details: error.message }),
      { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }

  // Log the authentication
  await supabase
    .from('seo_logs')
    .insert({
      business_id: business.id,
      action_type: 'gsc_authenticated',
      action_description: `Google Search Console authenticated for ${site_url}`,
      new_data: JSON.stringify({
        site_url,
        verification_status: 'verified',
        permission_level: 'full_user'
      })
    })

  return new Response(
    JSON.stringify({
      success: true,
      message: 'Google Search Console authenticated successfully',
      site_url: site_url,
      verification_status: 'verified',
      config_id: gscConfig.id
    }),
    { 
      status: 200, 
      headers: { ...corsHeaders, 'Content-Type': 'application/json' } 
    }
  )
}

async function handleGSCSync(supabase: any, business: any, campaign_id?: string, date_range?: string) {
  // Get GSC configuration
  const { data: gscConfig } = await supabase
    .from('gsc_configurations')
    .select('*')
    .eq('business_id', business.id)
    .single()

  if (!gscConfig) {
    return new Response(
      JSON.stringify({ 
        error: 'Google Search Console not configured. Please authenticate first.',
        auth_required: true 
      }),
      { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }

  // Check if token needs refresh
  const tokenValid = await ensureValidToken(supabase, gscConfig)
  if (!tokenValid) {
    return new Response(
      JSON.stringify({ 
        error: 'Token expired. Please re-authenticate.',
        auth_required: true 
      }),
      { status: 401, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }

  // Fetch data from GSC API (simulated)
  const searchAnalyticsData = await fetchGSCSearchAnalytics(
    gscConfig,
    date_range,
    campaign_id
  )

  const indexingData = await fetchGSCIndexingData(gscConfig)
  const sitemapData = await fetchGSCSitemapData(gscConfig)

  // Store the data
  const syncResults = {
    search_analytics: 0,
    indexing_issues: 0,
    sitemap_pages: 0
  }

  // Store search analytics data
  if (searchAnalyticsData.length > 0) {
    const { data: insertedData } = await supabase
      .from('gsc_search_analytics')
      .upsert(
        searchAnalyticsData.map(item => ({
          business_id: business.id,
          campaign_id,
          site_url: gscConfig.site_url,
          query: item.query,
          page: item.page,
          country: item.country,
          device: item.device,
          clicks: item.clicks,
          impressions: item.impressions,
          ctr: item.ctr,
          position: item.position,
          date: item.date,
          synced_at: new Date().toISOString()
        })),
        { onConflict: 'business_id,site_url,query,page,date,device,country' }
      )
      .select()

    syncResults.search_analytics = insertedData?.length || 0
  }

  // Store indexing data
  if (indexingData.length > 0) {
    const { data: indexingInserted } = await supabase
      .from('gsc_indexing_status')
      .upsert(
        indexingData.map(item => ({
          business_id: business.id,
          site_url: gscConfig.site_url,
          page_url: item.page_url,
          coverage_status: item.coverage_status,
          indexing_status: item.indexing_status,
          last_crawled: item.last_crawled,
          issues: item.issues,
          synced_at: new Date().toISOString()
        })),
        { onConflict: 'business_id,site_url,page_url' }
      )
      .select()

    syncResults.indexing_issues = indexingInserted?.length || 0
  }

  // Update last sync time
  await supabase
    .from('gsc_configurations')
    .update({
      last_sync: new Date().toISOString(),
      updated_at: new Date().toISOString()
    })
    .eq('id', gscConfig.id)

  // Log the sync
  await supabase
    .from('seo_logs')
    .insert({
      business_id: business.id,
      action_type: 'gsc_sync',
      action_description: `GSC data synced: ${syncResults.search_analytics} analytics records`,
      new_data: JSON.stringify({
        site_url: gscConfig.site_url,
        date_range,
        sync_results: syncResults
      })
    })

  return new Response(
    JSON.stringify({
      success: true,
      message: 'Google Search Console data synced successfully',
      site_url: gscConfig.site_url,
      date_range,
      sync_results: syncResults,
      last_sync: new Date().toISOString()
    }),
    { 
      status: 200, 
      headers: { ...corsHeaders, 'Content-Type': 'application/json' } 
    }
  )
}

async function handleGSCQuery(supabase: any, business: any, query_type: string, date_range: string, filters: any[]) {
  let query = supabase
    .from('gsc_search_analytics')
    .select('*')
    .eq('business_id', business.id)

  // Apply date range filter
  const dateFilter = calculateDateRange(date_range)
  query = query.gte('date', dateFilter.start).lte('date', dateFilter.end)

  // Apply additional filters
  for (const filter of filters) {
    if (filter.field && filter.value) {
      query = query.eq(filter.field, filter.value)
    }
  }

  const { data: results } = await query
    .order('clicks', { ascending: false })
    .limit(1000)

  // Aggregate data based on query type
  let aggregatedData
  switch (query_type) {
    case 'queries':
      aggregatedData = aggregateByQueries(results || [])
      break
    case 'pages':
      aggregatedData = aggregateByPages(results || [])
      break
    case 'countries':
      aggregatedData = aggregateByCountries(results || [])
      break
    case 'devices':
      aggregatedData = aggregateByDevices(results || [])
      break
    default:
      aggregatedData = results || []
  }

  const summary = {
    total_records: results?.length || 0,
    total_clicks: results?.reduce((sum, r) => sum + r.clicks, 0) || 0,
    total_impressions: results?.reduce((sum, r) => sum + r.impressions, 0) || 0,
    average_ctr: results?.length ? 
      (results.reduce((sum, r) => sum + r.ctr, 0) / results.length).toFixed(2) : 0,
    average_position: results?.length ? 
      (results.reduce((sum, r) => sum + r.position, 0) / results.length).toFixed(1) : 0
  }

  return new Response(
    JSON.stringify({
      success: true,
      query_type,
      date_range,
      summary,
      data: aggregatedData.slice(0, 100) // Limit response size
    }),
    { 
      status: 200, 
      headers: { ...corsHeaders, 'Content-Type': 'application/json' } 
    }
  )
}

async function handleGSCConfiguration(supabase: any, business: any, site_url?: string) {
  const { data: configs } = await supabase
    .from('gsc_configurations')
    .select('*')
    .eq('business_id', business.id)

  if (site_url) {
    // Update specific configuration
    const config = configs?.find(c => c.site_url === site_url)
    if (!config) {
      return new Response(
        JSON.stringify({ error: 'Configuration not found for site' }),
        { status: 404, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    return new Response(
      JSON.stringify({
        success: true,
        configuration: config
      }),
      { 
        status: 200, 
        headers: { ...corsHeaders, 'Content-Type': 'application/json' } 
      }
    )
  }

  return new Response(
    JSON.stringify({
      success: true,
      configurations: configs || [],
      total_sites: configs?.length || 0
    }),
    { 
      status: 200, 
      headers: { ...corsHeaders, 'Content-Type': 'application/json' } 
    }
  )
}

function generateGSCAuthUrl(businessId: string, siteUrl: string): string {
  // In a real implementation, this would generate the actual Google OAuth URL
  const clientId = Deno.env.get('GOOGLE_CLIENT_ID') || 'your-google-client-id'
  const redirectUri = `${Deno.env.get('SUPABASE_URL')}/functions/v1/gsc-integration/callback`
  const scope = 'https://www.googleapis.com/auth/webmasters.readonly'
  const state = `${businessId}:${siteUrl}`
  
  return `https://accounts.google.com/o/oauth2/v2/auth?` +
    `client_id=${clientId}&` +
    `redirect_uri=${encodeURIComponent(redirectUri)}&` +
    `scope=${encodeURIComponent(scope)}&` +
    `response_type=code&` +
    `state=${encodeURIComponent(state)}&` +
    `access_type=offline&` +
    `prompt=consent`
}

async function exchangeAuthCodeForTokens(authCode: string): Promise<any> {
  // Simulate token exchange (in real implementation, call Google OAuth API)
  return {
    access_token: `gsc_access_token_${Date.now()}`,
    refresh_token: `gsc_refresh_token_${Date.now()}`,
    expires_at: new Date(Date.now() + 3600 * 1000).toISOString(), // 1 hour
    token_type: 'Bearer',
    scope: 'https://www.googleapis.com/auth/webmasters.readonly'
  }
}

async function ensureValidToken(supabase: any, gscConfig: any): Promise<boolean> {
  const now = new Date()
  const expiresAt = new Date(gscConfig.token_expires_at)
  
  if (now < expiresAt) {
    return true // Token is still valid
  }
  
  // Token expired, attempt refresh (simulated)
  try {
    const newTokenData = await refreshGSCToken(gscConfig.refresh_token)
    
    await supabase
      .from('gsc_configurations')
      .update({
        access_token: newTokenData.access_token,
        token_expires_at: newTokenData.expires_at,
        updated_at: new Date().toISOString()
      })
      .eq('id', gscConfig.id)
    
    return true
  } catch (error) {
    console.error('Failed to refresh GSC token:', error)
    return false
  }
}

async function refreshGSCToken(refreshToken: string): Promise<any> {
  // Simulate token refresh (in real implementation, call Google OAuth API)
  return {
    access_token: `gsc_access_token_${Date.now()}`,
    expires_at: new Date(Date.now() + 3600 * 1000).toISOString()
  }
}

async function fetchGSCSearchAnalytics(gscConfig: any, dateRange: string, campaignId?: string): Promise<GSCSearchAnalytics[]> {
  // Simulate GSC API call to fetch search analytics data
  const { start, end } = calculateDateRange(dateRange)
  const mockData: GSCSearchAnalytics[] = []
  
  // Generate realistic search analytics data
  const sampleQueries = [
    'restaurant near me', 'best restaurant orlando', 'seafood restaurant',
    'waterfront dining', 'orlando dining', 'restaurant reservations',
    'fine dining orlando', 'family restaurant', 'italian restaurant',
    'steakhouse orlando', 'outdoor dining', 'restaurant reviews'
  ]
  
  const samplePages = [
    '/', '/menu', '/reservations', '/about', '/contact',
    '/blog/best-seafood-orlando', '/blog/waterfront-dining-guide',
    '/catering', '/events', '/reviews'
  ]
  
  for (let i = 0; i < 100; i++) {
    const query = sampleQueries[Math.floor(Math.random() * sampleQueries.length)]
    const page = samplePages[Math.floor(Math.random() * samplePages.length)]
    const clicks = Math.floor(Math.random() * 50) + 1
    const impressions = clicks * (Math.floor(Math.random() * 10) + 5)
    
    mockData.push({
      query,
      page: `${gscConfig.site_url}${page}`,
      country: 'USA',
      device: Math.random() > 0.7 ? 'MOBILE' : 'DESKTOP',
      clicks,
      impressions,
      ctr: (clicks / impressions) * 100,
      position: Math.floor(Math.random() * 20) + 1,
      date: generateRandomDateInRange(start, end)
    })
  }
  
  return mockData
}

async function fetchGSCIndexingData(gscConfig: any): Promise<any[]> {
  // Simulate indexing status data
  const mockIndexingData = [
    {
      page_url: `${gscConfig.site_url}/`,
      coverage_status: 'Valid',
      indexing_status: 'Indexed',
      last_crawled: new Date(Date.now() - Math.random() * 7 * 24 * 60 * 60 * 1000).toISOString(),
      issues: []
    },
    {
      page_url: `${gscConfig.site_url}/menu`,
      coverage_status: 'Valid',
      indexing_status: 'Indexed',
      last_crawled: new Date(Date.now() - Math.random() * 7 * 24 * 60 * 60 * 1000).toISOString(),
      issues: []
    },
    {
      page_url: `${gscConfig.site_url}/old-page`,
      coverage_status: 'Error',
      indexing_status: 'Not indexed',
      last_crawled: new Date(Date.now() - Math.random() * 30 * 24 * 60 * 60 * 1000).toISOString(),
      issues: ['404 Not Found']
    }
  ]
  
  return mockIndexingData
}

async function fetchGSCSitemapData(gscConfig: any): Promise<any[]> {
  // Simulate sitemap data
  return [
    {
      sitemap_url: `${gscConfig.site_url}/sitemap.xml`,
      submitted_pages: 25,
      indexed_pages: 23,
      last_submitted: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString()
    }
  ]
}

function calculateDateRange(dateRange: string): { start: string; end: string } {
  const end = new Date()
  let start = new Date()
  
  switch (dateRange) {
    case 'last_7_days':
      start.setDate(end.getDate() - 7)
      break
    case 'last_30_days':
      start.setDate(end.getDate() - 30)
      break
    case 'last_90_days':
      start.setDate(end.getDate() - 90)
      break
    default:
      start.setDate(end.getDate() - 30)
  }
  
  return {
    start: start.toISOString().split('T')[0],
    end: end.toISOString().split('T')[0]
  }
}

function generateRandomDateInRange(start: string, end: string): string {
  const startDate = new Date(start)
  const endDate = new Date(end)
  const randomTime = startDate.getTime() + Math.random() * (endDate.getTime() - startDate.getTime())
  return new Date(randomTime).toISOString().split('T')[0]
}

function aggregateByQueries(data: GSCSearchAnalytics[]): any[] {
  const queryMap = new Map()
  
  for (const item of data) {
    if (!queryMap.has(item.query)) {
      queryMap.set(item.query, {
        query: item.query,
        clicks: 0,
        impressions: 0,
        ctr: 0,
        position: 0,
        pages: new Set()
      })
    }
    
    const aggregated = queryMap.get(item.query)
    aggregated.clicks += item.clicks
    aggregated.impressions += item.impressions
    aggregated.pages.add(item.page)
  }
  
  return Array.from(queryMap.values())
    .map(item => ({
      ...item,
      ctr: item.impressions > 0 ? (item.clicks / item.impressions) * 100 : 0,
      pages: item.pages.size
    }))
    .sort((a, b) => b.clicks - a.clicks)
}

function aggregateByPages(data: GSCSearchAnalytics[]): any[] {
  const pageMap = new Map()
  
  for (const item of data) {
    if (!pageMap.has(item.page)) {
      pageMap.set(item.page, {
        page: item.page,
        clicks: 0,
        impressions: 0,
        ctr: 0,
        position: 0,
        queries: new Set()
      })
    }
    
    const aggregated = pageMap.get(item.page)
    aggregated.clicks += item.clicks
    aggregated.impressions += item.impressions
    aggregated.queries.add(item.query)
  }
  
  return Array.from(pageMap.values())
    .map(item => ({
      ...item,
      ctr: item.impressions > 0 ? (item.clicks / item.impressions) * 100 : 0,
      queries: item.queries.size
    }))
    .sort((a, b) => b.clicks - a.clicks)
}

function aggregateByCountries(data: GSCSearchAnalytics[]): any[] {
  const countryMap = new Map()
  
  for (const item of data) {
    if (!countryMap.has(item.country)) {
      countryMap.set(item.country, {
        country: item.country,
        clicks: 0,
        impressions: 0,
        ctr: 0
      })
    }
    
    const aggregated = countryMap.get(item.country)
    aggregated.clicks += item.clicks
    aggregated.impressions += item.impressions
  }
  
  return Array.from(countryMap.values())
    .map(item => ({
      ...item,
      ctr: item.impressions > 0 ? (item.clicks / item.impressions) * 100 : 0
    }))
    .sort((a, b) => b.clicks - a.clicks)
}

function aggregateByDevices(data: GSCSearchAnalytics[]): any[] {
  const deviceMap = new Map()
  
  for (const item of data) {
    if (!deviceMap.has(item.device)) {
      deviceMap.set(item.device, {
        device: item.device,
        clicks: 0,
        impressions: 0,
        ctr: 0
      })
    }
    
    const aggregated = deviceMap.get(item.device)
    aggregated.clicks += item.clicks
    aggregated.impressions += item.impressions
  }
  
  return Array.from(deviceMap.values())
    .map(item => ({
      ...item,
      ctr: item.impressions > 0 ? (item.clicks / item.impressions) * 100 : 0
    }))
    .sort((a, b) => b.clicks - a.clicks)
}