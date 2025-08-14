import { createUserClient, getUser, getUserFromDatabase } from './database.ts'
import type { RequestContext } from './types.ts'

export async function authenticateRequest(request: Request): Promise<RequestContext> {
  const authHeader = request.headers.get('Authorization')
  
  if (!authHeader || !authHeader.startsWith('Bearer ')) {
    throw new Error('Missing or invalid authorization header')
  }

  const token = authHeader.substring(7)
  
  try {
    // Get user from Supabase Auth
    const authUser = await getUser(token)
    
    // Get user details from our database
    const dbUser = await getUserFromDatabase(authUser.id)
    
    if (!dbUser.is_active) {
      throw new Error('Account is deactivated')
    }

    return {
      userId: dbUser.id,
      userRole: dbUser.role,
      ipAddress: request.headers.get('CF-Connecting-IP') || 
                 request.headers.get('X-Forwarded-For') || 
                 'unknown',
      userAgent: request.headers.get('User-Agent') || 'unknown',
    }
  } catch (error) {
    throw new Error('Authentication failed')
  }
}

export function requireAdmin(context: RequestContext) {
  if (context.userRole !== 'admin') {
    throw new Error('Admin access required')
  }
}

export async function hasBusinessAccess(
  businessId: number, 
  context: RequestContext,
  client = createDatabaseClient()
): Promise<boolean> {
  if (context.userRole === 'admin') {
    return true
  }

  const { data, error } = await client
    .from('businesses')
    .select('user_id')
    .eq('id', businessId)
    .single()

  if (error || !data) {
    return false
  }

  return data.user_id === context.userId
}

export function requireBusinessAccess(businessId: number, context: RequestContext) {
  return hasBusinessAccess(businessId, context).then(hasAccess => {
    if (!hasAccess) {
      throw new Error('Access denied to this business')
    }
  })
}