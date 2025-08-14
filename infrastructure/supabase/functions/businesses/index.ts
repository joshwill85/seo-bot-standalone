import { serve } from 'https://deno.land/std@0.208.0/http/server.ts'
import { createDatabaseClient, logSeoAction } from '../_shared/database.ts'
import { authenticateRequest, requireBusinessAccess } from '../_shared/auth.ts'
import { validateBusinessData } from '../_shared/validation.ts'
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
    const businessId = pathParts[pathParts.length - 1]

    // Route requests
    if (req.method === 'GET' && businessId && !isNaN(Number(businessId))) {
      return await handleGetBusiness(req, Number(businessId), origin)
    } else if (req.method === 'GET') {
      return await handleListBusinesses(req, origin)
    } else if (req.method === 'POST') {
      return await handleCreateBusiness(req, origin)
    } else if (req.method === 'PUT' && businessId && !isNaN(Number(businessId))) {
      return await handleUpdateBusiness(req, Number(businessId), origin)
    } else if (url.pathname.includes('/analytics')) {
      const businessId = pathParts[pathParts.length - 2]
      return await handleGetAnalytics(req, Number(businessId), origin)
    } else {
      return createErrorResponse('Not found', 404, origin)
    }
  } catch (error) {
    console.error('Business function error:', error)
    
    if (error instanceof AppError) {
      return createErrorResponse(error.message, error.statusCode, origin, error.details)
    }
    
    return createErrorResponse('Internal server error', 500, origin)
  }
})

async function handleCreateBusiness(req: Request, origin?: string) {
  const context = await authenticateRequest(req)
  const data = await req.json()

  // Validate input
  validateBusinessData(data)

  const supabase = createDatabaseClient()

  // Add user ID and defaults
  const businessData = {
    user_id: context.userId!,
    business_name: data.business_name,
    website_url: data.website_url || null,
    industry: data.industry || null,
    business_type: data.business_type || 'local',
    address: data.address || null,
    city: data.city,
    state: data.state || 'Florida',
    zip_code: data.zip_code || null,
    phone: data.phone || null,
    target_keywords: data.target_keywords ? JSON.stringify(data.target_keywords) : null,
    competitors: data.competitors ? JSON.stringify(data.competitors) : null,
    plan_tier: data.plan_tier,
    subscription_status: 'trial',
    billing_cycle: 'monthly',
    trial_ends_at: new Date(Date.now() + 14 * 24 * 60 * 60 * 1000).toISOString(), // 14 days
  }

  const { data: business, error } = await supabase
    .from('businesses')
    .insert(businessData)
    .select()
    .single()

  if (error) {
    throw new AppError(`Failed to create business: ${error.message}`, 'BUSINESS_CREATION_ERROR', 500)
  }

  // Log business creation
  await logSeoAction(
    business.id,
    'business_created',
    `Business profile created: ${business.business_name}`,
    undefined,
    undefined,
    JSON.stringify(business),
    context.userId!,
    context.ipAddress,
    context.userAgent
  )

  return createResponse({
    message: 'Business created successfully',
    business,
  }, 201, origin)
}

async function handleListBusinesses(req: Request, origin?: string) {
  const context = await authenticateRequest(req)
  const supabase = createDatabaseClient()

  let query = supabase.from('businesses').select('*')

  // Business owners can only see their own businesses
  if (context.userRole !== 'admin') {
    query = query.eq('user_id', context.userId!)
  }

  const { data: businesses, error } = await query.order('created_at', { ascending: false })

  if (error) {
    throw new AppError(`Failed to get businesses: ${error.message}`, 'BUSINESSES_FETCH_ERROR', 500)
  }

  return createResponse({
    businesses,
  }, 200, origin)
}

async function handleGetBusiness(req: Request, businessId: number, origin?: string) {
  const context = await authenticateRequest(req)
  await requireBusinessAccess(businessId, context)

  const supabase = createDatabaseClient()

  const { data: business, error } = await supabase
    .from('businesses')
    .select('*')
    .eq('id', businessId)
    .single()

  if (error || !business) {
    return createErrorResponse('Business not found', 404, origin)
  }

  return createResponse({
    business,
  }, 200, origin)
}

async function handleUpdateBusiness(req: Request, businessId: number, origin?: string) {
  const context = await authenticateRequest(req)
  await requireBusinessAccess(businessId, context)

  const data = await req.json()
  const supabase = createDatabaseClient()

  // Get current business data for logging
  const { data: oldBusiness } = await supabase
    .from('businesses')
    .select('*')
    .eq('id', businessId)
    .single()

  // Prepare update data
  const updateData: any = {
    updated_at: new Date().toISOString(),
  }

  // Only update provided fields
  const allowedFields = [
    'business_name', 'website_url', 'industry', 'business_type',
    'address', 'city', 'state', 'zip_code', 'phone'
  ]

  for (const field of allowedFields) {
    if (data[field] !== undefined) {
      updateData[field] = data[field]
    }
  }

  // Handle arrays
  if (data.target_keywords !== undefined) {
    updateData.target_keywords = Array.isArray(data.target_keywords) 
      ? JSON.stringify(data.target_keywords)
      : data.target_keywords
  }

  if (data.competitors !== undefined) {
    updateData.competitors = Array.isArray(data.competitors)
      ? JSON.stringify(data.competitors)
      : data.competitors
  }

  const { data: business, error } = await supabase
    .from('businesses')
    .update(updateData)
    .eq('id', businessId)
    .select()
    .single()

  if (error) {
    throw new AppError(`Failed to update business: ${error.message}`, 'BUSINESS_UPDATE_ERROR', 500)
  }

  // Log business update
  await logSeoAction(
    businessId,
    'business_updated',
    `Business profile updated: ${business.business_name}`,
    undefined,
    oldBusiness ? JSON.stringify(oldBusiness) : undefined,
    JSON.stringify(business),
    context.userId!,
    context.ipAddress,
    context.userAgent
  )

  return createResponse({
    message: 'Business updated successfully',
    business,
  }, 200, origin)
}

async function handleGetAnalytics(req: Request, businessId: number, origin?: string) {
  const context = await authenticateRequest(req)
  await requireBusinessAccess(businessId, context)

  const supabase = createDatabaseClient()

  // Get business analytics using the database function
  const { data: insights, error: insightsError } = await supabase
    .rpc('get_business_insights', { business_id_param: businessId })

  if (insightsError) {
    console.error('Failed to get business insights:', insightsError)
  }

  // Get recent reports
  const { data: reports, error: reportsError } = await supabase
    .from('seo_reports')
    .select('*')
    .eq('business_id', businessId)
    .order('created_at', { ascending: false })
    .limit(10)

  if (reportsError) {
    throw new AppError(`Failed to get reports: ${reportsError.message}`, 'REPORTS_FETCH_ERROR', 500)
  }

  // Get recent activity logs
  const { data: logs, error: logsError } = await supabase
    .from('seo_logs')
    .select('*')
    .eq('business_id', businessId)
    .order('created_at', { ascending: false })
    .limit(20)

  if (logsError) {
    throw new AppError(`Failed to get logs: ${logsError.message}`, 'LOGS_FETCH_ERROR', 500)
  }

  // Calculate basic analytics
  const reportStats = reports.reduce((acc: any, report) => {
    acc[report.report_type] = (acc[report.report_type] || 0) + 1
    return acc
  }, {})

  const latestScores = reports
    .filter(r => r.score !== null)
    .reduce((acc: any, report) => {
      if (!acc[report.report_type] || report.created_at > acc[report.report_type].created_at) {
        acc[report.report_type] = {
          score: report.score,
          created_at: report.created_at,
        }
      }
      return acc
    }, {})

  const analytics = {
    business_id: businessId,
    report_counts: reportStats,
    latest_scores: latestScores,
    total_reports: reports.length,
    recent_activity: logs.slice(0, 10).map(log => ({
      action_type: log.action_type,
      description: log.action_description,
      created_at: log.created_at,
    })),
    insights: insights || {},
  }

  return createResponse({
    analytics,
  }, 200, origin)
}