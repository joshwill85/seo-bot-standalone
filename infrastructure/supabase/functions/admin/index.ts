import { serve } from 'https://deno.land/std@0.208.0/http/server.ts'
import { createDatabaseClient } from '../_shared/database.ts'
import { authenticateRequest, requireAdmin } from '../_shared/auth.ts'
import { handleCors, createResponse, createErrorResponse } from '../_shared/cors.ts'
import { AppError } from '../_shared/types.ts'

serve(async (req) => {
  const origin = req.headers.get('Origin')

  // Handle CORS
  if (req.method === 'OPTIONS') {
    return new Response(null, { status: 200, headers: handleCors(req) })
  }

  try {
    const url = new URL(req.url)
    const pathParts = url.pathname.split('/').filter(Boolean)
    const action = pathParts[pathParts.length - 1]

    switch (action) {
      case 'dashboard':
        return await handleGetDashboard(req, origin)
      case 'businesses':
        return await handleGetAllBusinesses(req, origin)
      case 'users':
        return await handleGetAllUsers(req, origin)
      case 'reports':
        return await handleGetAllReports(req, origin)
      case 'analytics':
        return await handleGetSystemAnalytics(req, origin)
      default:
        return createErrorResponse('Not found', 404, origin)
    }
  } catch (error) {
    console.error('Admin function error:', error)
    
    if (error instanceof AppError) {
      return createErrorResponse(error.message, error.statusCode, origin, error.details)
    }
    
    return createErrorResponse('Internal server error', 500, origin)
  }
})

async function handleGetDashboard(req: Request, origin?: string) {
  if (req.method !== 'GET') {
    return createErrorResponse('Method not allowed', 405, origin)
  }

  const context = await authenticateRequest(req)
  requireAdmin(context)

  const supabase = createDatabaseClient()

  // Get all businesses with aggregated data
  const { data: businesses, error: businessError } = await supabase
    .from('businesses')
    .select('*')

  if (businessError) {
    throw new AppError(`Failed to get businesses: ${businessError.message}`, 'BUSINESSES_FETCH_ERROR', 500)
  }

  // Calculate dashboard metrics
  const dashboardData = {
    total_businesses: businesses.length,
    businesses_by_plan: {} as Record<string, number>,
    businesses_by_status: {} as Record<string, number>,
    recent_signups: [] as any[],
    revenue_summary: {
      monthly_recurring: 0,
      trial_businesses: 0,
      active_subscriptions: 0,
    },
  }

  const thirtyDaysAgo = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000)
  const planPrices = { starter: 64, professional: 240, enterprise: 480 }

  for (const business of businesses) {
    // Count by plan
    const plan = business.plan_tier || 'unknown'
    dashboardData.businesses_by_plan[plan] = (dashboardData.businesses_by_plan[plan] || 0) + 1

    // Count by status
    const status = business.subscription_status || 'unknown'
    dashboardData.businesses_by_status[status] = (dashboardData.businesses_by_status[status] || 0) + 1

    // Recent signups (last 30 days)
    const createdAt = new Date(business.created_at)
    if (createdAt >= thirtyDaysAgo) {
      dashboardData.recent_signups.push({
        business_name: business.business_name,
        plan_tier: business.plan_tier,
        created_at: business.created_at,
      })
    }

    // Revenue calculations
    if (status === 'trial') {
      dashboardData.revenue_summary.trial_businesses += 1
    } else if (status === 'active') {
      dashboardData.revenue_summary.active_subscriptions += 1
      
      // Estimate monthly revenue
      const price = planPrices[plan as keyof typeof planPrices] || 0
      dashboardData.revenue_summary.monthly_recurring += price
    }
  }

  // Sort recent signups by date
  dashboardData.recent_signups.sort((a, b) => 
    new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  )

  return createResponse({
    dashboard: dashboardData,
  }, 200, origin)
}

async function handleGetAllBusinesses(req: Request, origin?: string) {
  if (req.method !== 'GET') {
    return createErrorResponse('Method not allowed', 405, origin)
  }

  const context = await authenticateRequest(req)
  requireAdmin(context)

  const supabase = createDatabaseClient()

  // Get pagination parameters
  const url = new URL(req.url)
  const page = parseInt(url.searchParams.get('page') || '1')
  const perPage = Math.min(parseInt(url.searchParams.get('per_page') || '25'), 100)
  const offset = (page - 1) * perPage

  // Get search/filter parameters
  const search = url.searchParams.get('search')
  const planFilter = url.searchParams.get('plan')
  const statusFilter = url.searchParams.get('status')

  // Build query
  let query = supabase
    .from('businesses')
    .select(`
      *,
      users!inner(
        id,
        email,
        first_name,
        last_name
      )
    `)

  // Apply filters
  if (search) {
    query = query.or(`business_name.ilike.%${search}%,users.email.ilike.%${search}%`)
  }

  if (planFilter) {
    query = query.eq('plan_tier', planFilter)
  }

  if (statusFilter) {
    query = query.eq('subscription_status', statusFilter)
  }

  // Get total count
  const { count } = await query.select('*', { count: 'exact', head: true })

  // Get paginated results
  const { data: businesses, error } = await query
    .order('created_at', { ascending: false })
    .range(offset, offset + perPage - 1)

  if (error) {
    throw new AppError(`Failed to get businesses: ${error.message}`, 'BUSINESSES_FETCH_ERROR', 500)
  }

  const totalPages = Math.ceil((count || 0) / perPage)

  return createResponse({
    businesses,
    pagination: {
      page,
      per_page: perPage,
      total: count || 0,
      pages: totalPages,
      has_next: page < totalPages,
      has_prev: page > 1,
    },
  }, 200, origin)
}

async function handleGetAllUsers(req: Request, origin?: string) {
  if (req.method !== 'GET') {
    return createErrorResponse('Method not allowed', 405, origin)
  }

  const context = await authenticateRequest(req)
  requireAdmin(context)

  const supabase = createDatabaseClient()

  const { data: users, error } = await supabase
    .from('users')
    .select('id, email, first_name, last_name, role, is_active, email_verified, created_at, last_login')
    .order('created_at', { ascending: false })

  if (error) {
    throw new AppError(`Failed to get users: ${error.message}`, 'USERS_FETCH_ERROR', 500)
  }

  return createResponse({
    users,
  }, 200, origin)
}

async function handleGetAllReports(req: Request, origin?: string) {
  if (req.method !== 'GET') {
    return createErrorResponse('Method not allowed', 405, origin)
  }

  const context = await authenticateRequest(req)
  requireAdmin(context)

  const supabase = createDatabaseClient()

  // Get pagination parameters
  const url = new URL(req.url)
  const page = parseInt(url.searchParams.get('page') || '1')
  const perPage = Math.min(parseInt(url.searchParams.get('per_page') || '25'), 100)
  const offset = (page - 1) * perPage

  // Get filter parameters
  const reportType = url.searchParams.get('type')
  const status = url.searchParams.get('status')

  // Build query
  let query = supabase
    .from('seo_reports')
    .select(`
      *,
      businesses!inner(
        id,
        business_name,
        user_id
      )
    `)

  // Apply filters
  if (reportType) {
    query = query.eq('report_type', reportType)
  }

  if (status) {
    query = query.eq('status', status)
  }

  // Get total count
  const { count } = await query.select('*', { count: 'exact', head: true })

  // Get paginated results
  const { data: reports, error } = await query
    .order('created_at', { ascending: false })
    .range(offset, offset + perPage - 1)

  if (error) {
    throw new AppError(`Failed to get reports: ${error.message}`, 'REPORTS_FETCH_ERROR', 500)
  }

  const totalPages = Math.ceil((count || 0) / perPage)

  return createResponse({
    reports,
    pagination: {
      page,
      per_page: perPage,
      total: count || 0,
      pages: totalPages,
      has_next: page < totalPages,
      has_prev: page > 1,
    },
  }, 200, origin)
}

async function handleGetSystemAnalytics(req: Request, origin?: string) {
  if (req.method !== 'GET') {
    return createErrorResponse('Method not allowed', 405, origin)
  }

  const context = await authenticateRequest(req)
  requireAdmin(context)

  const supabase = createDatabaseClient()

  // Get date range
  const url = new URL(req.url)
  const days = parseInt(url.searchParams.get('days') || '30')
  const startDate = new Date(Date.now() - days * 24 * 60 * 60 * 1000).toISOString()

  // Get analytics data
  const [businessesResult, reportsResult, logsResult] = await Promise.all([
    // Businesses created over time
    supabase
      .from('businesses')
      .select('created_at, plan_tier')
      .gte('created_at', startDate)
      .order('created_at'),

    // Reports generated over time
    supabase
      .from('seo_reports')
      .select('created_at, report_type, status, score')
      .gte('created_at', startDate)
      .order('created_at'),

    // Activity logs
    supabase
      .from('seo_logs')
      .select('created_at, action_type')
      .gte('created_at', startDate)
      .order('created_at'),
  ])

  if (businessesResult.error || reportsResult.error || logsResult.error) {
    throw new AppError('Failed to get analytics data', 'ANALYTICS_FETCH_ERROR', 500)
  }

  // Process data for charts
  const businessSignups = processTimeSeriesData(businessesResult.data, 'created_at')
  const reportGeneration = processTimeSeriesData(reportsResult.data, 'created_at')
  const systemActivity = processTimeSeriesData(logsResult.data, 'created_at')

  // Calculate metrics
  const totalBusinesses = businessSignups.reduce((sum, item) => sum + item.count, 0)
  const totalReports = reportGeneration.reduce((sum, item) => sum + item.count, 0)
  const averageScore = reportsResult.data
    .filter(r => r.score !== null)
    .reduce((sum, r, _, arr) => sum + (r.score || 0) / arr.length, 0)

  const analytics = {
    summary: {
      total_businesses: totalBusinesses,
      total_reports: totalReports,
      average_score: Math.round(averageScore * 10) / 10,
      active_period_days: days,
    },
    charts: {
      business_signups: businessSignups,
      report_generation: reportGeneration,
      system_activity: systemActivity,
    },
    breakdowns: {
      reports_by_type: groupBy(reportsResult.data, 'report_type'),
      reports_by_status: groupBy(reportsResult.data, 'status'),
      businesses_by_plan: groupBy(businessesResult.data, 'plan_tier'),
    },
  }

  return createResponse({
    analytics,
  }, 200, origin)
}

// Helper functions
function processTimeSeriesData(data: any[], dateField: string) {
  const grouped = data.reduce((acc, item) => {
    const date = new Date(item[dateField]).toISOString().split('T')[0]
    acc[date] = (acc[date] || 0) + 1
    return acc
  }, {} as Record<string, number>)

  return Object.entries(grouped).map(([date, count]) => ({
    date,
    count,
  })).sort((a, b) => a.date.localeCompare(b.date))
}

function groupBy(data: any[], field: string) {
  return data.reduce((acc, item) => {
    const key = item[field] || 'unknown'
    acc[key] = (acc[key] || 0) + 1
    return acc
  }, {} as Record<string, number>)
}