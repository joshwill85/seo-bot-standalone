import { serve } from 'https://deno.land/std@0.168.0/http/server.ts'
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'
import { corsHeaders } from '../_shared/cors.ts'

interface GARequest {
  business_id: string
  campaign_id?: string
  action: 'authenticate' | 'sync' | 'query' | 'configure' | 'goals'
  auth_code?: string
  property_id?: string
  view_id?: string
  date_range?: 'last_7_days' | 'last_30_days' | 'last_90_days' | 'last_12_months'
  metrics?: string[]
  dimensions?: string[]
  filters?: any[]
  goal_config?: GoalConfiguration
}

interface GAMetrics {
  date: string
  property_id: string
  view_id: string
  sessions: number
  users: number
  new_users: number
  page_views: number
  avg_session_duration: number
  bounce_rate: number
  goal_completions: number
  conversion_rate: number
  organic_traffic: number
  organic_sessions: number
  pages_per_session: number
}

interface GAPageData {
  page_path: string
  page_title: string
  page_views: number
  unique_page_views: number
  avg_time_on_page: number
  bounce_rate: number
  exit_rate: number
  entrances: number
  goal_completions: number
  organic_traffic: number
}

interface GATrafficSource {
  source: string
  medium: string
  campaign: string
  sessions: number
  users: number
  new_users: number
  goal_completions: number
  conversion_rate: number
  avg_session_duration: number
}

interface GAConfig {
  property_id: string
  view_id: string
  access_token: string
  refresh_token: string
  token_expires_at: string
  account_id: string
  property_name: string
  view_name: string
  timezone: string
  currency: string
  last_sync: string
}

interface GoalConfiguration {
  goal_name: string
  goal_type: 'destination' | 'duration' | 'pages_per_session' | 'event'
  goal_details: {
    destination_url?: string
    duration_threshold?: number
    pages_threshold?: number
    event_category?: string
    event_action?: string
    event_label?: string
  }
  goal_value?: number
  funnel_steps?: {
    step_name: string
    step_url: string
    required: boolean
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
      action,
      auth_code,
      property_id,
      view_id,
      date_range = 'last_30_days',
      metrics = ['sessions', 'users', 'pageviews'],
      dimensions = ['date'],
      filters = [],
      goal_config
    }: GARequest = await req.json()

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
        return await handleGAAuthentication(supabase, business, auth_code, property_id, view_id)
      case 'sync':
        return await handleGASync(supabase, business, campaign_id, date_range)
      case 'query':
        return await handleGAQuery(supabase, business, metrics, dimensions, date_range, filters)
      case 'configure':
        return await handleGAConfiguration(supabase, business)
      case 'goals':
        return await handleGAGoals(supabase, business_id, goal_config)
      default:
        return new Response(
          JSON.stringify({ error: 'Invalid action' }),
          { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
        )
    }

  } catch (error) {
    console.error('GA integration error:', error)
    return new Response(
      JSON.stringify({ error: 'Internal server error', details: error.message }),
      { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }
})

async function handleGAAuthentication(supabase: any, business: any, auth_code?: string, property_id?: string, view_id?: string) {
  if (!auth_code || !property_id || !view_id) {
    // Return OAuth URL for authentication
    const authUrl = generateGAAuthUrl(business.id, business.website_url)
    
    return new Response(
      JSON.stringify({
        success: true,
        auth_required: true,
        auth_url: authUrl,
        instructions: 'Visit the auth_url to authorize Google Analytics access',
        next_steps: [
          'After authorization, you will receive an auth_code',
          'Use the Management API to get your property_id and view_id',
          'Call this endpoint again with auth_code, property_id, and view_id'
        ]
      }),
      { 
        status: 200, 
        headers: { ...corsHeaders, 'Content-Type': 'application/json' } 
      }
    )
  }

  // Exchange auth code for tokens (simulated)
  const tokenData = await exchangeAuthCodeForTokens(auth_code)
  
  // Get account and property information (simulated)
  const accountInfo = await getGAAccountInfo(tokenData.access_token, property_id, view_id)
  
  // Store GA configuration
  const { data: gaConfig, error } = await supabase
    .from('ga_configurations')
    .upsert({
      business_id: business.id,
      property_id: property_id,
      view_id: view_id,
      access_token: tokenData.access_token,
      refresh_token: tokenData.refresh_token,
      token_expires_at: tokenData.expires_at,
      account_id: accountInfo.account_id,
      property_name: accountInfo.property_name,
      view_name: accountInfo.view_name,
      timezone: accountInfo.timezone,
      currency: accountInfo.currency,
      last_sync: null,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    }, {
      onConflict: 'business_id,property_id,view_id'
    })
    .select()
    .single()

  if (error) {
    return new Response(
      JSON.stringify({ error: 'Failed to store GA configuration', details: error.message }),
      { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }

  // Log the authentication
  await supabase
    .from('seo_logs')
    .insert({
      business_id: business.id,
      action_type: 'ga_authenticated',
      action_description: `Google Analytics authenticated for property ${property_id}`,
      new_data: JSON.stringify({
        property_id,
        view_id,
        property_name: accountInfo.property_name,
        view_name: accountInfo.view_name
      })
    })

  return new Response(
    JSON.stringify({
      success: true,
      message: 'Google Analytics authenticated successfully',
      property_id: property_id,
      view_id: view_id,
      property_name: accountInfo.property_name,
      view_name: accountInfo.view_name,
      config_id: gaConfig.id
    }),
    { 
      status: 200, 
      headers: { ...corsHeaders, 'Content-Type': 'application/json' } 
    }
  )
}

async function handleGASync(supabase: any, business: any, campaign_id?: string, date_range?: string) {
  // Get GA configuration
  const { data: gaConfig } = await supabase
    .from('ga_configurations')
    .select('*')
    .eq('business_id', business.id)
    .single()

  if (!gaConfig) {
    return new Response(
      JSON.stringify({ 
        error: 'Google Analytics not configured. Please authenticate first.',
        auth_required: true 
      }),
      { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }

  // Check if token needs refresh
  const tokenValid = await ensureValidToken(supabase, gaConfig)
  if (!tokenValid) {
    return new Response(
      JSON.stringify({ 
        error: 'Token expired. Please re-authenticate.',
        auth_required: true 
      }),
      { status: 401, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }

  // Fetch data from GA API (simulated)
  const metricsData = await fetchGAMetrics(gaConfig, date_range)
  const pageData = await fetchGAPageData(gaConfig, date_range)
  const trafficSourceData = await fetchGATrafficSources(gaConfig, date_range)
  const goalData = await fetchGAGoalData(gaConfig, date_range)

  // Store the data
  const syncResults = {
    metrics_records: 0,
    page_records: 0,
    traffic_source_records: 0,
    goal_records: 0
  }

  // Store metrics data
  if (metricsData.length > 0) {
    const { data: insertedMetrics } = await supabase
      .from('ga_metrics')
      .upsert(
        metricsData.map(item => ({
          business_id: business.id,
          campaign_id,
          property_id: gaConfig.property_id,
          view_id: gaConfig.view_id,
          date: item.date,
          sessions: item.sessions,
          users: item.users,
          new_users: item.new_users,
          page_views: item.page_views,
          avg_session_duration: item.avg_session_duration,
          bounce_rate: item.bounce_rate,
          goal_completions: item.goal_completions,
          conversion_rate: item.conversion_rate,
          organic_traffic: item.organic_traffic,
          organic_sessions: item.organic_sessions,
          pages_per_session: item.pages_per_session,
          synced_at: new Date().toISOString()
        })),
        { onConflict: 'business_id,property_id,view_id,date' }
      )
      .select()

    syncResults.metrics_records = insertedMetrics?.length || 0
  }

  // Store page data
  if (pageData.length > 0) {
    const { data: insertedPages } = await supabase
      .from('ga_page_data')
      .upsert(
        pageData.map(item => ({
          business_id: business.id,
          campaign_id,
          property_id: gaConfig.property_id,
          view_id: gaConfig.view_id,
          page_path: item.page_path,
          page_title: item.page_title,
          page_views: item.page_views,
          unique_page_views: item.unique_page_views,
          avg_time_on_page: item.avg_time_on_page,
          bounce_rate: item.bounce_rate,
          exit_rate: item.exit_rate,
          entrances: item.entrances,
          goal_completions: item.goal_completions,
          organic_traffic: item.organic_traffic,
          date_range: date_range,
          synced_at: new Date().toISOString()
        })),
        { onConflict: 'business_id,property_id,view_id,page_path,date_range' }
      )
      .select()

    syncResults.page_records = insertedPages?.length || 0
  }

  // Store traffic source data
  if (trafficSourceData.length > 0) {
    const { data: insertedSources } = await supabase
      .from('ga_traffic_sources')
      .upsert(
        trafficSourceData.map(item => ({
          business_id: business.id,
          campaign_id,
          property_id: gaConfig.property_id,
          view_id: gaConfig.view_id,
          source: item.source,
          medium: item.medium,
          campaign: item.campaign,
          sessions: item.sessions,
          users: item.users,
          new_users: item.new_users,
          goal_completions: item.goal_completions,
          conversion_rate: item.conversion_rate,
          avg_session_duration: item.avg_session_duration,
          date_range: date_range,
          synced_at: new Date().toISOString()
        })),
        { onConflict: 'business_id,property_id,view_id,source,medium,campaign,date_range' }
      )
      .select()

    syncResults.traffic_source_records = insertedSources?.length || 0
  }

  // Update last sync time
  await supabase
    .from('ga_configurations')
    .update({
      last_sync: new Date().toISOString(),
      updated_at: new Date().toISOString()
    })
    .eq('id', gaConfig.id)

  // Log the sync
  await supabase
    .from('seo_logs')
    .insert({
      business_id: business.id,
      action_type: 'ga_sync',
      action_description: `GA data synced: ${syncResults.metrics_records} metrics, ${syncResults.page_records} pages`,
      new_data: JSON.stringify({
        property_id: gaConfig.property_id,
        view_id: gaConfig.view_id,
        date_range,
        sync_results: syncResults
      })
    })

  return new Response(
    JSON.stringify({
      success: true,
      message: 'Google Analytics data synced successfully',
      property_id: gaConfig.property_id,
      view_id: gaConfig.view_id,
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

async function handleGAQuery(supabase: any, business: any, metrics: string[], dimensions: string[], date_range: string, filters: any[]) {
  let query = supabase
    .from('ga_metrics')
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
    .order('date', { ascending: false })
    .limit(1000)

  // Aggregate data based on requested metrics and dimensions
  const aggregatedData = aggregateGAData(results || [], metrics, dimensions)

  const summary = {
    total_records: results?.length || 0,
    date_range: date_range,
    total_sessions: results?.reduce((sum, r) => sum + (r.sessions || 0), 0) || 0,
    total_users: results?.reduce((sum, r) => sum + (r.users || 0), 0) || 0,
    total_pageviews: results?.reduce((sum, r) => sum + (r.page_views || 0), 0) || 0,
    avg_bounce_rate: results?.length ? 
      (results.reduce((sum, r) => sum + (r.bounce_rate || 0), 0) / results.length).toFixed(2) : 0,
    avg_session_duration: results?.length ? 
      (results.reduce((sum, r) => sum + (r.avg_session_duration || 0), 0) / results.length).toFixed(2) : 0
  }

  return new Response(
    JSON.stringify({
      success: true,
      requested_metrics: metrics,
      requested_dimensions: dimensions,
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

async function handleGAConfiguration(supabase: any, business: any) {
  const { data: configs } = await supabase
    .from('ga_configurations')
    .select('*')
    .eq('business_id', business.id)

  return new Response(
    JSON.stringify({
      success: true,
      configurations: configs || [],
      total_properties: configs?.length || 0
    }),
    { 
      status: 200, 
      headers: { ...corsHeaders, 'Content-Type': 'application/json' } 
    }
  )
}

async function handleGAGoals(supabase: any, business_id: string, goal_config?: GoalConfiguration) {
  if (!goal_config) {
    // Return existing goals
    const { data: goals } = await supabase
      .from('ga_goals')
      .select('*')
      .eq('business_id', business_id)

    return new Response(
      JSON.stringify({
        success: true,
        goals: goals || []
      }),
      { 
        status: 200, 
        headers: { ...corsHeaders, 'Content-Type': 'application/json' } 
      }
    )
  }

  // Create or update goal
  const { data: goal, error } = await supabase
    .from('ga_goals')
    .upsert({
      business_id,
      goal_name: goal_config.goal_name,
      goal_type: goal_config.goal_type,
      goal_details: goal_config.goal_details,
      goal_value: goal_config.goal_value,
      funnel_steps: goal_config.funnel_steps,
      is_active: true,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    }, {
      onConflict: 'business_id,goal_name'
    })
    .select()
    .single()

  if (error) {
    return new Response(
      JSON.stringify({ error: 'Failed to configure goal', details: error.message }),
      { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }

  return new Response(
    JSON.stringify({
      success: true,
      message: 'Goal configured successfully',
      goal_id: goal.id
    }),
    { 
      status: 200, 
      headers: { ...corsHeaders, 'Content-Type': 'application/json' } 
    }
  )
}

function generateGAAuthUrl(businessId: string, websiteUrl: string): string {
  // In a real implementation, this would generate the actual Google OAuth URL
  const clientId = Deno.env.get('GOOGLE_CLIENT_ID') || 'your-google-client-id'
  const redirectUri = `${Deno.env.get('SUPABASE_URL')}/functions/v1/ga-integration/callback`
  const scope = 'https://www.googleapis.com/auth/analytics.readonly'
  const state = `${businessId}:${websiteUrl}`
  
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
    access_token: `ga_access_token_${Date.now()}`,
    refresh_token: `ga_refresh_token_${Date.now()}`,
    expires_at: new Date(Date.now() + 3600 * 1000).toISOString(), // 1 hour
    token_type: 'Bearer',
    scope: 'https://www.googleapis.com/auth/analytics.readonly'
  }
}

async function getGAAccountInfo(accessToken: string, propertyId: string, viewId: string): Promise<any> {
  // Simulate account info retrieval
  return {
    account_id: `account_${Date.now()}`,
    property_name: 'Website Property',
    view_name: 'All Website Data',
    timezone: 'America/New_York',
    currency: 'USD'
  }
}

async function ensureValidToken(supabase: any, gaConfig: any): Promise<boolean> {
  const now = new Date()
  const expiresAt = new Date(gaConfig.token_expires_at)
  
  if (now < expiresAt) {
    return true // Token is still valid
  }
  
  // Token expired, attempt refresh (simulated)
  try {
    const newTokenData = await refreshGAToken(gaConfig.refresh_token)
    
    await supabase
      .from('ga_configurations')
      .update({
        access_token: newTokenData.access_token,
        token_expires_at: newTokenData.expires_at,
        updated_at: new Date().toISOString()
      })
      .eq('id', gaConfig.id)
    
    return true
  } catch (error) {
    console.error('Failed to refresh GA token:', error)
    return false
  }
}

async function refreshGAToken(refreshToken: string): Promise<any> {
  // Simulate token refresh (in real implementation, call Google OAuth API)
  return {
    access_token: `ga_access_token_${Date.now()}`,
    expires_at: new Date(Date.now() + 3600 * 1000).toISOString()
  }
}

async function fetchGAMetrics(gaConfig: any, dateRange: string): Promise<GAMetrics[]> {
  // Simulate GA API call to fetch metrics data
  const { start, end } = calculateDateRange(dateRange)
  const mockData: GAMetrics[] = []
  
  // Generate daily metrics for the date range
  const startDate = new Date(start)
  const endDate = new Date(end)
  
  for (let d = new Date(startDate); d <= endDate; d.setDate(d.getDate() + 1)) {
    const baseSessions = 100 + Math.floor(Math.random() * 400)
    const users = Math.floor(baseSessions * (0.7 + Math.random() * 0.3))
    const newUsers = Math.floor(users * (0.3 + Math.random() * 0.4))
    const pageViews = Math.floor(baseSessions * (1.5 + Math.random() * 2.5))
    
    mockData.push({
      date: d.toISOString().split('T')[0],
      property_id: gaConfig.property_id,
      view_id: gaConfig.view_id,
      sessions: baseSessions,
      users,
      new_users: newUsers,
      page_views: pageViews,
      avg_session_duration: Math.round((120 + Math.random() * 240) * 10) / 10,
      bounce_rate: Math.round((40 + Math.random() * 30) * 10) / 10,
      goal_completions: Math.floor(baseSessions * (0.02 + Math.random() * 0.05)),
      conversion_rate: Math.round((2 + Math.random() * 3) * 100) / 100,
      organic_traffic: Math.floor(baseSessions * (0.4 + Math.random() * 0.3)),
      organic_sessions: Math.floor(baseSessions * (0.4 + Math.random() * 0.3)),
      pages_per_session: Math.round((1.5 + Math.random() * 2.5) * 100) / 100
    })
  }
  
  return mockData
}

async function fetchGAPageData(gaConfig: any, dateRange: string): Promise<GAPageData[]> {
  // Simulate page performance data
  const samplePages = [
    { path: '/', title: 'Home Page' },
    { path: '/about', title: 'About Us' },
    { path: '/services', title: 'Our Services' },
    { path: '/contact', title: 'Contact Us' },
    { path: '/blog', title: 'Blog' },
    { path: '/products', title: 'Products' },
    { path: '/pricing', title: 'Pricing' },
    { path: '/testimonials', title: 'Testimonials' },
    { path: '/faq', title: 'FAQ' },
    { path: '/support', title: 'Support' }
  ]
  
  return samplePages.map(page => ({
    page_path: page.path,
    page_title: page.title,
    page_views: 100 + Math.floor(Math.random() * 900),
    unique_page_views: 80 + Math.floor(Math.random() * 720),
    avg_time_on_page: Math.round((30 + Math.random() * 180) * 10) / 10,
    bounce_rate: Math.round((30 + Math.random() * 40) * 10) / 10,
    exit_rate: Math.round((20 + Math.random() * 50) * 10) / 10,
    entrances: 50 + Math.floor(Math.random() * 450),
    goal_completions: Math.floor(Math.random() * 20),
    organic_traffic: 40 + Math.floor(Math.random() * 360)
  }))
}

async function fetchGATrafficSources(gaConfig: any, dateRange: string): Promise<GATrafficSource[]> {
  // Simulate traffic source data
  const sources = [
    { source: 'google', medium: 'organic' },
    { source: 'facebook', medium: 'social' },
    { source: 'direct', medium: '(none)' },
    { source: 'bing', medium: 'organic' },
    { source: 'linkedin', medium: 'social' },
    { source: 'twitter', medium: 'social' },
    { source: 'newsletter', medium: 'email' },
    { source: 'google', medium: 'cpc' }
  ]
  
  return sources.map(source => ({
    source: source.source,
    medium: source.medium,
    campaign: source.medium === 'cpc' ? 'google_ads_campaign' : '(not set)',
    sessions: 50 + Math.floor(Math.random() * 200),
    users: 40 + Math.floor(Math.random() * 160),
    new_users: 20 + Math.floor(Math.random() * 80),
    goal_completions: Math.floor(Math.random() * 10),
    conversion_rate: Math.round((1 + Math.random() * 4) * 100) / 100,
    avg_session_duration: Math.round((90 + Math.random() * 180) * 10) / 10
  }))
}

async function fetchGAGoalData(gaConfig: any, dateRange: string): Promise<any[]> {
  // Simulate goal completion data
  return [
    {
      goal_name: 'Contact Form Submission',
      goal_completions: 15 + Math.floor(Math.random() * 25),
      goal_value: 50,
      conversion_rate: Math.round((2 + Math.random() * 3) * 100) / 100
    },
    {
      goal_name: 'Newsletter Signup',
      goal_completions: 25 + Math.floor(Math.random() * 35),
      goal_value: 10,
      conversion_rate: Math.round((3 + Math.random() * 4) * 100) / 100
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
    case 'last_12_months':
      start.setFullYear(end.getFullYear() - 1)
      break
    default:
      start.setDate(end.getDate() - 30)
  }
  
  return {
    start: start.toISOString().split('T')[0],
    end: end.toISOString().split('T')[0]
  }
}

function aggregateGAData(data: any[], metrics: string[], dimensions: string[]): any[] {
  if (!data || data.length === 0) return []
  
  // For simplicity, return data as-is with requested fields
  return data.map(item => {
    const result: any = {}
    
    // Include requested dimensions
    for (const dimension of dimensions) {
      if (item[dimension] !== undefined) {
        result[dimension] = item[dimension]
      }
    }
    
    // Include requested metrics
    for (const metric of metrics) {
      if (item[metric] !== undefined) {
        result[metric] = item[metric]
      }
    }
    
    return result
  })
}