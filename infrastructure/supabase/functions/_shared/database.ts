import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'
import type { Database } from './types.ts'

export function createDatabaseClient() {
  const supabaseUrl = Deno.env.get('SUPABASE_URL')!
  const supabaseServiceKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!

  return createClient<Database>(supabaseUrl, supabaseServiceKey, {
    auth: {
      autoRefreshToken: false,
      persistSession: false,
    },
  })
}

export function createUserClient(authToken: string) {
  const supabaseUrl = Deno.env.get('SUPABASE_URL')!
  const supabaseAnonKey = Deno.env.get('SUPABASE_ANON_KEY')!

  const client = createClient<Database>(supabaseUrl, supabaseAnonKey, {
    auth: {
      autoRefreshToken: false,
      persistSession: false,
    },
    global: {
      headers: {
        Authorization: `Bearer ${authToken}`,
      },
    },
  })

  return client
}

export async function getUser(authToken: string) {
  const client = createUserClient(authToken)
  const { data: { user }, error } = await client.auth.getUser(authToken)
  
  if (error || !user) {
    throw new Error('Unauthorized')
  }

  return user
}

export async function getUserFromDatabase(userId: string, client = createDatabaseClient()) {
  const { data, error } = await client
    .from('users')
    .select('*')
    .eq('id', userId)
    .single()

  if (error) {
    throw new Error(`Failed to get user: ${error.message}`)
  }

  return data
}

export async function logSeoAction(
  businessId: number,
  actionType: string,
  description: string,
  toolName?: string,
  oldData?: string,
  newData?: string,
  userId?: number,
  ipAddress?: string,
  userAgent?: string,
  client = createDatabaseClient()
) {
  const { error } = await client
    .from('seo_logs')
    .insert({
      business_id: businessId,
      action_type: actionType,
      action_description: description,
      tool_name: toolName,
      old_data: oldData,
      new_data: newData,
      user_id: userId,
      ip_address: ipAddress,
      user_agent: userAgent,
    })

  if (error) {
    console.error('Failed to log SEO action:', error)
  }
}