import { serve } from 'https://deno.land/std@0.168.0/http/server.ts'
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'
import { corsHeaders } from '../_shared/cors.ts'

interface APIRequest {
  user_id?: string
  business_id?: string
  action: string
  resource: string
  method: 'GET' | 'POST' | 'PUT' | 'DELETE'
  params?: any
  filters?: any
  pagination?: {
    page: number
    limit: number
    sort_by?: string
    sort_order?: 'asc' | 'desc'
  }
}

interface APIResponse {
  success: boolean
  data?: any
  error?: string
  metadata?: {
    total_count?: number
    page?: number
    limit?: number
    has_more?: boolean
  }
  timestamp: string
}

// Route mapping to Edge Functions
const ROUTE_MAP = {
  // Dashboard endpoints
  'dashboard.overview': { function: 'dashboard-data', action: 'overview' },
  'dashboard.metrics': { function: 'dashboard-data', action: 'metrics' },
  'dashboard.alerts': { function: 'seo-monitor', action: 'list' },
  'dashboard.tasks': { function: 'seo-scheduler', action: 'status' },
  
  // Campaign management
  'campaigns.list': { function: 'campaign-manager', action: 'list' },
  'campaigns.create': { function: 'campaign-manager', action: 'create' },
  'campaigns.update': { function: 'campaign-manager', action: 'update' },
  'campaigns.delete': { function: 'campaign-manager', action: 'delete' },
  'campaigns.details': { function: 'campaign-manager', action: 'details' },
  
  // Keyword operations
  'keywords.discover': { function: 'seo-discover', action: 'discover' },
  'keywords.cluster': { function: 'seo-cluster', action: 'cluster' },
  'keywords.track': { function: 'seo-ranks', action: 'track' },
  'keywords.opportunities': { function: 'seo-ai-predict', action: 'opportunity_analysis' },
  
  // Content operations
  'content.briefs': { function: 'seo-brief', action: 'generate' },
  'content.optimize': { function: 'seo-ai-optimize', action: 'optimize_content' },
  'content.analyze': { function: 'seo-analytics', action: 'analyze' },
  'content.performance': { function: 'seo-analytics', action: 'performance' },
  
  // Technical SEO
  'technical.audit': { function: 'seo-audit', action: 'audit' },
  'technical.monitor': { function: 'seo-monitor', action: 'check' },
  'technical.issues': { function: 'seo-audit', action: 'issues' },
  
  // Competitor analysis
  'competitors.analyze': { function: 'seo-competitors', action: 'analyze' },
  'competitors.track': { function: 'seo-competitors', action: 'track' },
  'competitors.gaps': { function: 'seo-competitors', action: 'gaps' },
  
  // Reports
  'reports.generate': { function: 'seo-reports', action: 'generate' },
  'reports.list': { function: 'seo-reports', action: 'list' },
  'reports.schedule': { function: 'seo-reports', action: 'schedule' },
  'reports.download': { function: 'seo-reports', action: 'download' },
  
  // AI/ML operations
  'ai.predict': { function: 'seo-ai-predict', action: 'predict_rankings' },
  'ai.forecast': { function: 'seo-ai-predict', action: 'forecast_traffic' },
  'ai.optimize': { function: 'seo-ai-optimize', action: 'optimize_content' },
  'ai.risks': { function: 'seo-ai-predict', action: 'risk_assessment' },
  
  // Integrations
  'integrations.ga': { function: 'ga-integration', action: 'sync' },
  'integrations.gsc': { function: 'gsc-integration', action: 'sync' },
  'integrations.webhooks': { function: 'seo-webhooks', action: 'list' },
  
  // User management
  'users.profile': { function: 'user-management', action: 'profile' },
  'users.settings': { function: 'user-management', action: 'settings' },
  'users.businesses': { function: 'user-management', action: 'businesses' },
  'users.permissions': { function: 'user-management', action: 'permissions' }
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

    // Parse request
    const apiRequest: APIRequest = await req.json()
    
    // Validate authentication
    const authHeader = req.headers.get('Authorization')
    if (!authHeader) {
      return createErrorResponse('Missing authorization header', 401)
    }

    // Verify user session
    const { data: { user }, error: authError } = await supabase.auth.getUser(
      authHeader.replace('Bearer ', '')
    )

    if (authError || !user) {
      return createErrorResponse('Invalid authentication', 401)
    }

    // Check permissions
    const hasPermission = await checkUserPermission(
      supabase,
      user.id,
      apiRequest.business_id,
      apiRequest.resource,
      apiRequest.method
    )

    if (!hasPermission) {
      return createErrorResponse('Insufficient permissions', 403)
    }

    // Route to appropriate function
    const route = `${apiRequest.resource}.${apiRequest.action}`
    const routeConfig = ROUTE_MAP[route]

    if (!routeConfig) {
      return createErrorResponse(`Invalid route: ${route}`, 404)
    }

    // Call the appropriate Edge Function
    const functionUrl = `${Deno.env.get('SUPABASE_URL')}/functions/v1/${routeConfig.function}`
    
    // Prepare request payload
    const payload = {
      ...apiRequest.params,
      business_id: apiRequest.business_id,
      user_id: user.id,
      action: routeConfig.action,
      filters: apiRequest.filters,
      pagination: apiRequest.pagination
    }

    // Make request to Edge Function
    const response = await fetch(functionUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')}`
      },
      body: JSON.stringify(payload)
    })

    if (!response.ok) {
      const error = await response.text()
      return createErrorResponse(`Function error: ${error}`, response.status)
    }

    const data = await response.json()

    // Log API call
    await logAPICall(supabase, user.id, apiRequest, response.status)

    // Apply pagination if needed
    const paginatedData = applyPagination(data, apiRequest.pagination)

    // Return success response
    return createSuccessResponse(paginatedData, apiRequest.pagination)

  } catch (error) {
    console.error('API Gateway error:', error)
    return createErrorResponse('Internal server error', 500)
  }
})

async function checkUserPermission(
  supabase: any,
  userId: string,
  businessId: string | undefined,
  resource: string,
  method: string
): Promise<boolean> {
  
  // Check if user is admin
  const { data: user } = await supabase
    .from('users')
    .select('role')
    .eq('id', userId)
    .single()

  if (user?.role === 'admin') {
    return true
  }

  // Check business ownership
  if (businessId) {
    const { data: business } = await supabase
      .from('businesses')
      .select('user_id')
      .eq('id', businessId)
      .single()

    if (business?.user_id !== userId) {
      return false
    }
  }

  // Check resource-specific permissions
  const readOnlyResources = ['dashboard', 'reports', 'ai']
  const writeResources = ['campaigns', 'keywords', 'content', 'technical']

  if (method === 'GET') {
    return true // All authenticated users can read
  }

  if (method === 'POST' || method === 'PUT' || method === 'DELETE') {
    // Check if resource allows write operations
    const resourceBase = resource.split('.')[0]
    return writeResources.includes(resourceBase)
  }

  return false
}

async function logAPICall(
  supabase: any,
  userId: string,
  request: APIRequest,
  statusCode: number
): Promise<void> {
  try {
    await supabase
      .from('api_logs')
      .insert({
        user_id: userId,
        business_id: request.business_id,
        endpoint: `${request.resource}.${request.action}`,
        method: request.method,
        status_code: statusCode,
        request_params: request.params,
        created_at: new Date().toISOString()
      })
  } catch (error) {
    console.error('Failed to log API call:', error)
  }
}

function applyPagination(data: any, pagination?: any): any {
  if (!pagination || !Array.isArray(data)) {
    return data
  }

  const { page = 1, limit = 50, sort_by, sort_order = 'desc' } = pagination

  // Sort if needed
  if (sort_by && data.length > 0 && data[0][sort_by] !== undefined) {
    data.sort((a, b) => {
      const aVal = a[sort_by]
      const bVal = b[sort_by]
      
      if (sort_order === 'asc') {
        return aVal > bVal ? 1 : aVal < bVal ? -1 : 0
      } else {
        return aVal < bVal ? 1 : aVal > bVal ? -1 : 0
      }
    })
  }

  // Paginate
  const start = (page - 1) * limit
  const end = start + limit
  
  return {
    items: data.slice(start, end),
    total: data.length,
    page,
    limit,
    has_more: end < data.length
  }
}

function createSuccessResponse(data: any, pagination?: any): Response {
  const response: APIResponse = {
    success: true,
    data: pagination?.items || data,
    timestamp: new Date().toISOString()
  }

  if (pagination) {
    response.metadata = {
      total_count: pagination.total,
      page: pagination.page,
      limit: pagination.limit,
      has_more: pagination.has_more
    }
  }

  return new Response(
    JSON.stringify(response),
    { 
      status: 200, 
      headers: { ...corsHeaders, 'Content-Type': 'application/json' } 
    }
  )
}

function createErrorResponse(error: string, status: number): Response {
  const response: APIResponse = {
    success: false,
    error,
    timestamp: new Date().toISOString()
  }

  return new Response(
    JSON.stringify(response),
    { 
      status, 
      headers: { ...corsHeaders, 'Content-Type': 'application/json' } 
    }
  )
}