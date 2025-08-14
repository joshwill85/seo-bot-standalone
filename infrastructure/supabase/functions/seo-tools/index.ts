import { serve } from 'https://deno.land/std@0.208.0/http/server.ts'
import { createDatabaseClient, logSeoAction } from '../_shared/database.ts'
import { authenticateRequest, requireBusinessAccess } from '../_shared/auth.ts'
import { validateSEOReportData } from '../_shared/validation.ts'
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
    const action = pathParts[pathParts.length - 2] // audit, keywords, reports, logs
    const businessId = pathParts[pathParts.length - 1]

    switch (action) {
      case 'audit':
        return await handleRunAudit(req, Number(businessId), origin)
      case 'keywords':
        return await handleKeywordResearch(req, Number(businessId), origin)
      case 'reports':
        return await handleGetReports(req, Number(businessId), origin)
      case 'logs':
        return await handleGetLogs(req, Number(businessId), origin)
      default:
        // Handle single report retrieval
        if (pathParts.includes('reports') && !isNaN(Number(businessId))) {
          return await handleGetReport(req, Number(businessId), origin)
        }
        return createErrorResponse('Not found', 404, origin)
    }
  } catch (error) {
    console.error('SEO tools function error:', error)
    
    if (error instanceof AppError) {
      return createErrorResponse(error.message, error.statusCode, origin, error.details)
    }
    
    return createErrorResponse('Internal server error', 500, origin)
  }
})

async function handleRunAudit(req: Request, businessId: number, origin?: string) {
  if (req.method !== 'POST') {
    return createErrorResponse('Method not allowed', 405, origin)
  }

  const context = await authenticateRequest(req)
  await requireBusinessAccess(businessId, context)

  const supabase = createDatabaseClient()

  // Get business details
  const { data: business, error: businessError } = await supabase
    .from('businesses')
    .select('*')
    .eq('id', businessId)
    .single()

  if (businessError || !business) {
    return createErrorResponse('Business not found', 404, origin)
  }

  // Create SEO report record
  const { data: report, error: reportError } = await supabase
    .from('seo_reports')
    .insert({
      business_id: businessId,
      report_type: 'full_audit',
      status: 'pending',
    })
    .select()
    .single()

  if (reportError) {
    throw new AppError(`Failed to create report: ${reportError.message}`, 'REPORT_CREATION_ERROR', 500)
  }

  // Log audit start
  await logSeoAction(
    businessId,
    'audit_started',
    'Full SEO audit initiated',
    'full_audit',
    undefined,
    undefined,
    context.userId!,
    context.ipAddress,
    context.userAgent
  )

  // Start audit in background (simplified version)
  runAuditInBackground(businessId, report.id, business)

  return createResponse({
    message: 'SEO audit started',
    report_id: report.id,
    status: 'pending',
  }, 202, origin)
}

async function handleKeywordResearch(req: Request, businessId: number, origin?: string) {
  if (req.method !== 'POST') {
    return createErrorResponse('Method not allowed', 405, origin)
  }

  const context = await authenticateRequest(req)
  await requireBusinessAccess(businessId, context)

  const data = await req.json()
  const keywords = data.keywords || []

  if (!keywords.length) {
    return createErrorResponse('Keywords required', 400, origin)
  }

  const supabase = createDatabaseClient()

  // Get business details
  const { data: business, error: businessError } = await supabase
    .from('businesses')
    .select('*')
    .eq('id', businessId)
    .single()

  if (businessError || !business) {
    return createErrorResponse('Business not found', 404, origin)
  }

  // Create keyword research report
  const { data: report, error: reportError } = await supabase
    .from('seo_reports')
    .insert({
      business_id: businessId,
      report_type: 'keyword_research',
      status: 'pending',
    })
    .select()
    .single()

  if (reportError) {
    throw new AppError(`Failed to create report: ${reportError.message}`, 'REPORT_CREATION_ERROR', 500)
  }

  // Log keyword research start
  await logSeoAction(
    businessId,
    'keyword_research_started',
    `Keyword research for: ${keywords.join(', ')}`,
    'keyword_research',
    undefined,
    undefined,
    context.userId!,
    context.ipAddress,
    context.userAgent
  )

  // Start keyword research in background
  runKeywordResearchInBackground(businessId, report.id, keywords, business)

  return createResponse({
    message: 'Keyword research started',
    report_id: report.id,
    status: 'pending',
  }, 202, origin)
}

async function handleGetReports(req: Request, businessId: number, origin?: string) {
  if (req.method !== 'GET') {
    return createErrorResponse('Method not allowed', 405, origin)
  }

  const context = await authenticateRequest(req)
  await requireBusinessAccess(businessId, context)

  const supabase = createDatabaseClient()

  const { data: reports, error } = await supabase
    .from('seo_reports')
    .select('*')
    .eq('business_id', businessId)
    .order('created_at', { ascending: false })

  if (error) {
    throw new AppError(`Failed to get reports: ${error.message}`, 'REPORTS_FETCH_ERROR', 500)
  }

  return createResponse({
    reports,
  }, 200, origin)
}

async function handleGetReport(req: Request, reportId: number, origin?: string) {
  if (req.method !== 'GET') {
    return createErrorResponse('Method not allowed', 405, origin)
  }

  const context = await authenticateRequest(req)
  const supabase = createDatabaseClient()

  const { data: report, error } = await supabase
    .from('seo_reports')
    .select('*, businesses!inner(user_id)')
    .eq('id', reportId)
    .single()

  if (error || !report) {
    return createErrorResponse('Report not found', 404, origin)
  }

  // Check access
  if (context.userRole !== 'admin' && report.businesses.user_id !== context.userId) {
    return createErrorResponse('Access denied', 403, origin)
  }

  return createResponse({
    report,
  }, 200, origin)
}

async function handleGetLogs(req: Request, businessId: number, origin?: string) {
  if (req.method !== 'GET') {
    return createErrorResponse('Method not allowed', 405, origin)
  }

  const context = await authenticateRequest(req)
  await requireBusinessAccess(businessId, context)

  const url = new URL(req.url)
  const page = parseInt(url.searchParams.get('page') || '1')
  const perPage = parseInt(url.searchParams.get('per_page') || '50')
  const offset = (page - 1) * perPage

  const supabase = createDatabaseClient()

  // Get total count
  const { count } = await supabase
    .from('seo_logs')
    .select('*', { count: 'exact', head: true })
    .eq('business_id', businessId)

  // Get logs with pagination
  const { data: logs, error } = await supabase
    .from('seo_logs')
    .select('*')
    .eq('business_id', businessId)
    .order('created_at', { ascending: false })
    .range(offset, offset + perPage - 1)

  if (error) {
    throw new AppError(`Failed to get logs: ${error.message}`, 'LOGS_FETCH_ERROR', 500)
  }

  const totalPages = Math.ceil((count || 0) / perPage)

  return createResponse({
    logs,
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

// Background processing functions (simplified)
async function runAuditInBackground(businessId: number, reportId: number, business: any) {
  const supabase = createDatabaseClient()

  try {
    // Update status to running
    await supabase
      .from('seo_reports')
      .update({ status: 'running' })
      .eq('id', reportId)

    // Simulate audit processing
    await new Promise(resolve => setTimeout(resolve, 2000))

    // Mock audit results
    const auditResults = {
      website_audit: {
        overall_score: Math.floor(Math.random() * 40) + 60, // 60-100
        technical_score: Math.floor(Math.random() * 30) + 70,
        content_score: Math.floor(Math.random() * 30) + 70,
        performance_score: Math.floor(Math.random() * 30) + 70,
        issues_count: Math.floor(Math.random() * 10) + 1,
        recommendations: [
          {
            category: 'Technical SEO',
            priority: 'high',
            description: 'Fix technical SEO issues to improve crawlability'
          },
          {
            category: 'Performance',
            priority: 'medium',
            description: 'Optimize images and reduce load times'
          }
        ]
      }
    }

    const overallScore = auditResults.website_audit.overall_score
    const executionTime = Math.floor(Math.random() * 5000) + 2000 // 2-7 seconds

    // Update report with results
    await supabase
      .from('seo_reports')
      .update({
        status: 'completed',
        results: JSON.stringify(auditResults),
        score: overallScore,
        issues_found: auditResults.website_audit.issues_count,
        recommendations: JSON.stringify(auditResults.website_audit.recommendations),
        execution_time_ms: executionTime,
        tools_used: JSON.stringify(['website_audit', 'performance_audit']),
        completed_at: new Date().toISOString(),
      })
      .eq('id', reportId)

    // Log completion
    await logSeoAction(
      businessId,
      'audit_completed',
      `Full SEO audit completed with score ${overallScore}`,
      'full_audit',
      undefined,
      JSON.stringify({ score: overallScore, issues: auditResults.website_audit.issues_count })
    )

  } catch (error) {
    console.error('Audit processing failed:', error)
    
    await supabase
      .from('seo_reports')
      .update({
        status: 'failed',
        results: JSON.stringify({ error: 'Audit processing failed' }),
      })
      .eq('id', reportId)

    await logSeoAction(
      businessId,
      'audit_failed',
      `SEO audit failed: ${error.message}`,
      'full_audit'
    )
  }
}

async function runKeywordResearchInBackground(
  businessId: number, 
  reportId: number, 
  keywords: string[], 
  business: any
) {
  const supabase = createDatabaseClient()

  try {
    // Update status to running
    await supabase
      .from('seo_reports')
      .update({ status: 'running' })
      .eq('id', reportId)

    // Simulate keyword research processing
    await new Promise(resolve => setTimeout(resolve, 3000))

    // Mock keyword research results
    const keywordResults = {
      keywords: keywords.map(keyword => ({
        keyword,
        search_volume: Math.floor(Math.random() * 10000) + 100,
        difficulty: Math.floor(Math.random() * 100),
        intent: ['informational', 'commercial', 'transactional', 'navigational'][Math.floor(Math.random() * 4)],
        position: Math.floor(Math.random() * 100) + 1,
      })),
      opportunities: keywords.slice(0, Math.min(5, keywords.length)).map(keyword => ({
        keyword,
        search_volume: Math.floor(Math.random() * 5000) + 500,
        difficulty: Math.floor(Math.random() * 50) + 10,
        potential_traffic: Math.floor(Math.random() * 1000) + 100,
      })),
      total_keywords: keywords.length,
      clusters: [
        {
          name: 'Primary Keywords',
          keywords: keywords.slice(0, Math.ceil(keywords.length / 2)),
        },
        {
          name: 'Long-tail Keywords',
          keywords: keywords.slice(Math.ceil(keywords.length / 2)),
        },
      ],
    }

    const score = keywordResults.opportunities.length * 10
    const executionTime = Math.floor(Math.random() * 8000) + 3000 // 3-11 seconds

    // Update report with results
    await supabase
      .from('seo_reports')
      .update({
        status: 'completed',
        results: JSON.stringify(keywordResults),
        score: Math.min(score, 100),
        issues_found: 0,
        recommendations: JSON.stringify([
          {
            category: 'Keywords',
            priority: 'medium',
            description: `Target ${keywordResults.opportunities.length} opportunity keywords`,
          },
        ]),
        execution_time_ms: executionTime,
        tools_used: JSON.stringify(['keyword_research', 'keyword_clustering']),
        completed_at: new Date().toISOString(),
      })
      .eq('id', reportId)

    // Log completion
    await logSeoAction(
      businessId,
      'keyword_research_completed',
      `Found ${keywordResults.total_keywords} keywords with ${keywordResults.opportunities.length} opportunities`,
      'keyword_research',
      undefined,
      JSON.stringify({
        total_keywords: keywordResults.total_keywords,
        opportunities: keywordResults.opportunities.length,
      })
    )

  } catch (error) {
    console.error('Keyword research processing failed:', error)
    
    await supabase
      .from('seo_reports')
      .update({
        status: 'failed',
        results: JSON.stringify({ error: 'Keyword research processing failed' }),
      })
      .eq('id', reportId)

    await logSeoAction(
      businessId,
      'keyword_research_failed',
      `Keyword research failed: ${error.message}`,
      'keyword_research'
    )
  }
}