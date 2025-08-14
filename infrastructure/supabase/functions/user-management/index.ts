import { serve } from 'https://deno.land/std@0.168.0/http/server.ts'
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'
import { corsHeaders } from '../_shared/cors.ts'
import * as bcrypt from 'https://deno.land/x/bcrypt@v0.4.1/mod.ts'

interface UserProfile {
  id: string
  email: string
  full_name?: string
  role: 'admin' | 'user' | 'viewer'
  avatar_url?: string
  phone?: string
  timezone?: string
  language?: string
  notifications: {
    email: boolean
    sms: boolean
    push: boolean
    frequency: 'instant' | 'daily' | 'weekly'
    types: string[]
  }
  preferences: {
    dashboard_layout?: string
    default_business_id?: string
    theme?: 'light' | 'dark' | 'auto'
    date_format?: string
    currency?: string
  }
  metadata?: any
}

interface UserSettings {
  user_id: string
  api_keys?: {
    openai?: string
    google?: string
    semrush?: string
    ahrefs?: string
  }
  integrations?: {
    google_analytics?: boolean
    search_console?: boolean
    slack?: boolean
    discord?: boolean
  }
  limits?: {
    max_businesses?: number
    max_keywords?: number
    max_campaigns?: number
    api_calls_per_day?: number
  }
  features?: {
    ai_optimization?: boolean
    competitor_tracking?: boolean
    automated_reporting?: boolean
    white_label?: boolean
  }
}

interface Business {
  id: string
  user_id: string
  name: string
  domain: string
  industry?: string
  description?: string
  settings?: any
  status: 'active' | 'inactive' | 'suspended'
  subscription?: {
    plan: 'free' | 'starter' | 'pro' | 'enterprise'
    status: 'active' | 'trialing' | 'past_due' | 'canceled'
    current_period_end?: string
    features?: string[]
  }
}

interface Permission {
  user_id: string
  business_id: string
  role: 'owner' | 'admin' | 'editor' | 'viewer'
  permissions: string[]
  granted_by?: string
  granted_at?: string
}

serve(async (req) => {
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders })
  }

  try {
    const supabase = createClient(
      Deno.env.get('SUPABASE_URL') ?? '',
      Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') ?? ''
    )

    const { 
      action, 
      user_id,
      data,
      business_id,
      filters
    } = await req.json()

    let result: any

    switch (action) {
      case 'profile':
        result = await getUserProfile(supabase, user_id)
        break
      
      case 'update_profile':
        result = await updateUserProfile(supabase, user_id, data)
        break
      
      case 'settings':
        result = await getUserSettings(supabase, user_id)
        break
      
      case 'update_settings':
        result = await updateUserSettings(supabase, user_id, data)
        break
      
      case 'businesses':
        result = await getUserBusinesses(supabase, user_id)
        break
      
      case 'create_business':
        result = await createBusiness(supabase, user_id, data)
        break
      
      case 'update_business':
        result = await updateBusiness(supabase, business_id, data)
        break
      
      case 'permissions':
        result = await getUserPermissions(supabase, user_id, business_id)
        break
      
      case 'grant_permission':
        result = await grantPermission(supabase, data)
        break
      
      case 'revoke_permission':
        result = await revokePermission(supabase, data)
        break
      
      case 'team_members':
        result = await getTeamMembers(supabase, business_id)
        break
      
      case 'invite_member':
        result = await inviteTeamMember(supabase, business_id, data)
        break
      
      case 'usage_stats':
        result = await getUserUsageStats(supabase, user_id)
        break
      
      case 'billing':
        result = await getBillingInfo(supabase, user_id)
        break
      
      case 'notifications':
        result = await getUserNotifications(supabase, user_id, filters)
        break
      
      case 'activity_log':
        result = await getUserActivityLog(supabase, user_id, filters)
        break
      
      default:
        throw new Error(`Unknown action: ${action}`)
    }

    return new Response(
      JSON.stringify(result),
      { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )

  } catch (error) {
    console.error('User management error:', error)
    return new Response(
      JSON.stringify({ error: error.message }),
      { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }
})

async function getUserProfile(
  supabase: any,
  userId: string
): Promise<UserProfile> {
  
  const { data, error } = await supabase
    .from('users')
    .select('*')
    .eq('id', userId)
    .single()

  if (error) throw error

  // Get additional profile data
  const { data: preferences } = await supabase
    .from('user_preferences')
    .select('*')
    .eq('user_id', userId)
    .single()

  const { data: notifications } = await supabase
    .from('user_notifications')
    .select('*')
    .eq('user_id', userId)
    .single()

  return {
    ...data,
    preferences: preferences || {},
    notifications: notifications || {
      email: true,
      sms: false,
      push: true,
      frequency: 'daily',
      types: ['alerts', 'reports']
    }
  }
}

async function updateUserProfile(
  supabase: any,
  userId: string,
  updates: Partial<UserProfile>
): Promise<UserProfile> {
  
  // Update main user record
  const { data: user, error: userError } = await supabase
    .from('users')
    .update({
      full_name: updates.full_name,
      avatar_url: updates.avatar_url,
      phone: updates.phone,
      timezone: updates.timezone,
      language: updates.language,
      updated_at: new Date().toISOString()
    })
    .eq('id', userId)
    .select()
    .single()

  if (userError) throw userError

  // Update preferences
  if (updates.preferences) {
    await supabase
      .from('user_preferences')
      .upsert({
        user_id: userId,
        ...updates.preferences,
        updated_at: new Date().toISOString()
      })
  }

  // Update notification settings
  if (updates.notifications) {
    await supabase
      .from('user_notifications')
      .upsert({
        user_id: userId,
        ...updates.notifications,
        updated_at: new Date().toISOString()
      })
  }

  return getUserProfile(supabase, userId)
}

async function getUserSettings(
  supabase: any,
  userId: string
): Promise<UserSettings> {
  
  const { data, error } = await supabase
    .from('user_settings')
    .select('*')
    .eq('user_id', userId)
    .single()

  if (error && error.code !== 'PGRST116') throw error

  // Return default settings if none exist
  if (!data) {
    return {
      user_id: userId,
      api_keys: {},
      integrations: {
        google_analytics: false,
        search_console: false,
        slack: false,
        discord: false
      },
      limits: {
        max_businesses: 3,
        max_keywords: 100,
        max_campaigns: 10,
        api_calls_per_day: 1000
      },
      features: {
        ai_optimization: true,
        competitor_tracking: true,
        automated_reporting: true,
        white_label: false
      }
    }
  }

  return data
}

async function updateUserSettings(
  supabase: any,
  userId: string,
  updates: Partial<UserSettings>
): Promise<UserSettings> {
  
  // Encrypt API keys before storing
  const encryptedSettings = { ...updates }
  if (updates.api_keys) {
    encryptedSettings.api_keys = await encryptApiKeys(updates.api_keys)
  }

  const { data, error } = await supabase
    .from('user_settings')
    .upsert({
      user_id: userId,
      ...encryptedSettings,
      updated_at: new Date().toISOString()
    })
    .select()
    .single()

  if (error) throw error

  return data
}

async function getUserBusinesses(
  supabase: any,
  userId: string
): Promise<Business[]> {
  
  // Get owned businesses
  const { data: ownedBusinesses, error: ownedError } = await supabase
    .from('businesses')
    .select('*')
    .eq('user_id', userId)

  if (ownedError) throw ownedError

  // Get businesses with permissions
  const { data: permissions, error: permError } = await supabase
    .from('business_permissions')
    .select(`
      business_id,
      role,
      permissions,
      businesses(*)
    `)
    .eq('user_id', userId)

  if (permError) throw permError

  const sharedBusinesses = permissions?.map((p: any) => ({
    ...p.businesses,
    user_role: p.role,
    user_permissions: p.permissions
  })) || []

  // Combine and deduplicate
  const allBusinesses = [...ownedBusinesses, ...sharedBusinesses]
  const uniqueBusinesses = Array.from(
    new Map(allBusinesses.map(b => [b.id, b])).values()
  )

  // Get subscription info for each business
  const businessesWithSubs = await Promise.all(
    uniqueBusinesses.map(async (business) => {
      const { data: subscription } = await supabase
        .from('subscriptions')
        .select('*')
        .eq('business_id', business.id)
        .single()

      return {
        ...business,
        subscription: subscription || {
          plan: 'free',
          status: 'active'
        }
      }
    })
  )

  return businessesWithSubs
}

async function createBusiness(
  supabase: any,
  userId: string,
  businessData: Business
): Promise<Business> {
  
  // Check user limits
  const settings = await getUserSettings(supabase, userId)
  const existingBusinesses = await getUserBusinesses(supabase, userId)
  
  if (existingBusinesses.length >= (settings.limits?.max_businesses || 3)) {
    throw new Error('Business limit reached for your account')
  }

  // Create business
  const { data: business, error } = await supabase
    .from('businesses')
    .insert({
      user_id: userId,
      name: businessData.name,
      domain: businessData.domain,
      industry: businessData.industry,
      description: businessData.description,
      settings: businessData.settings || {},
      status: 'active',
      created_at: new Date().toISOString()
    })
    .select()
    .single()

  if (error) throw error

  // Create default subscription
  await supabase
    .from('subscriptions')
    .insert({
      business_id: business.id,
      plan: 'free',
      status: 'active',
      created_at: new Date().toISOString()
    })

  // Log activity
  await supabase
    .from('activity_logs')
    .insert({
      business_id: business.id,
      user_id: userId,
      action: 'business_created',
      resource_type: 'business',
      resource_id: business.id,
      details: { business_name: business.name },
      created_at: new Date().toISOString()
    })

  return business
}

async function updateBusiness(
  supabase: any,
  businessId: string,
  updates: Partial<Business>
): Promise<Business> {
  
  const { data, error } = await supabase
    .from('businesses')
    .update({
      ...updates,
      updated_at: new Date().toISOString()
    })
    .eq('id', businessId)
    .select()
    .single()

  if (error) throw error

  return data
}

async function getUserPermissions(
  supabase: any,
  userId: string,
  businessId?: string
): Promise<Permission[]> {
  
  let query = supabase
    .from('business_permissions')
    .select(`
      *,
      businesses(name, domain)
    `)
    .eq('user_id', userId)

  if (businessId) {
    query = query.eq('business_id', businessId)
  }

  const { data, error } = await query

  if (error) throw error

  return data
}

async function grantPermission(
  supabase: any,
  permissionData: Permission
): Promise<Permission> {
  
  const { data, error } = await supabase
    .from('business_permissions')
    .insert({
      ...permissionData,
      granted_at: new Date().toISOString()
    })
    .select()
    .single()

  if (error) throw error

  // Send notification to user
  await sendPermissionNotification(supabase, permissionData.user_id, 'granted', permissionData)

  return data
}

async function revokePermission(
  supabase: any,
  permissionData: { user_id: string, business_id: string }
): Promise<{ success: boolean }> {
  
  const { error } = await supabase
    .from('business_permissions')
    .delete()
    .eq('user_id', permissionData.user_id)
    .eq('business_id', permissionData.business_id)

  if (error) throw error

  // Send notification to user
  await sendPermissionNotification(supabase, permissionData.user_id, 'revoked', permissionData)

  return { success: true }
}

async function getTeamMembers(
  supabase: any,
  businessId: string
): Promise<any[]> {
  
  // Get business owner
  const { data: business } = await supabase
    .from('businesses')
    .select('user_id')
    .eq('id', businessId)
    .single()

  // Get all users with permissions
  const { data: permissions } = await supabase
    .from('business_permissions')
    .select(`
      *,
      users(id, email, full_name, avatar_url, role)
    `)
    .eq('business_id', businessId)

  // Combine owner and team members
  const { data: owner } = await supabase
    .from('users')
    .select('id, email, full_name, avatar_url, role')
    .eq('id', business.user_id)
    .single()

  const teamMembers = [
    {
      ...owner,
      business_role: 'owner',
      permissions: ['all']
    },
    ...(permissions?.map((p: any) => ({
      ...p.users,
      business_role: p.role,
      permissions: p.permissions,
      granted_at: p.granted_at
    })) || [])
  ]

  return teamMembers
}

async function inviteTeamMember(
  supabase: any,
  businessId: string,
  inviteData: {
    email: string,
    role: string,
    permissions: string[],
    invited_by: string
  }
): Promise<any> {
  
  // Check if user exists
  const { data: existingUser } = await supabase
    .from('users')
    .select('id')
    .eq('email', inviteData.email)
    .single()

  if (existingUser) {
    // Grant permission directly
    return grantPermission(supabase, {
      user_id: existingUser.id,
      business_id: businessId,
      role: inviteData.role as any,
      permissions: inviteData.permissions,
      granted_by: inviteData.invited_by,
      granted_at: new Date().toISOString()
    })
  }

  // Create invitation
  const { data: invitation, error } = await supabase
    .from('invitations')
    .insert({
      business_id: businessId,
      email: inviteData.email,
      role: inviteData.role,
      permissions: inviteData.permissions,
      invited_by: inviteData.invited_by,
      status: 'pending',
      token: generateInviteToken(),
      expires_at: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString(),
      created_at: new Date().toISOString()
    })
    .select()
    .single()

  if (error) throw error

  // Send invitation email
  await sendInvitationEmail(inviteData.email, invitation)

  return invitation
}

async function getUserUsageStats(
  supabase: any,
  userId: string
): Promise<any> {
  
  // Get usage statistics
  const now = new Date()
  const startOfMonth = new Date(now.getFullYear(), now.getMonth(), 1)
  const startOfDay = new Date(now.getFullYear(), now.getMonth(), now.getDate())

  // API calls
  const { data: apiCalls } = await supabase
    .from('api_logs')
    .select('id')
    .eq('user_id', userId)
    .gte('created_at', startOfDay.toISOString())

  // Keywords tracked
  const { data: keywords } = await supabase
    .from('keywords')
    .select('id')
    .eq('user_id', userId)

  // Active campaigns
  const { data: campaigns } = await supabase
    .from('campaigns')
    .select('id')
    .in('business_id', 
      (await getUserBusinesses(supabase, userId)).map(b => b.id)
    )
    .eq('status', 'active')

  // Content created this month
  const { data: content } = await supabase
    .from('content_briefs')
    .select('id')
    .eq('created_by', userId)
    .gte('created_at', startOfMonth.toISOString())

  const settings = await getUserSettings(supabase, userId)

  return {
    api_calls: {
      today: apiCalls?.length || 0,
      limit: settings.limits?.api_calls_per_day || 1000,
      percentage: ((apiCalls?.length || 0) / (settings.limits?.api_calls_per_day || 1000)) * 100
    },
    keywords: {
      total: keywords?.length || 0,
      limit: settings.limits?.max_keywords || 100,
      percentage: ((keywords?.length || 0) / (settings.limits?.max_keywords || 100)) * 100
    },
    campaigns: {
      active: campaigns?.length || 0,
      limit: settings.limits?.max_campaigns || 10,
      percentage: ((campaigns?.length || 0) / (settings.limits?.max_campaigns || 10)) * 100
    },
    content: {
      this_month: content?.length || 0
    },
    storage: {
      used_mb: Math.floor(Math.random() * 500), // Placeholder
      limit_mb: 1000,
      percentage: Math.floor(Math.random() * 50)
    }
  }
}

async function getBillingInfo(
  supabase: any,
  userId: string
): Promise<any> {
  
  const businesses = await getUserBusinesses(supabase, userId)
  
  const billingInfo = await Promise.all(
    businesses.map(async (business) => {
      const { data: subscription } = await supabase
        .from('subscriptions')
        .select('*')
        .eq('business_id', business.id)
        .single()

      const { data: invoices } = await supabase
        .from('invoices')
        .select('*')
        .eq('business_id', business.id)
        .order('created_at', { ascending: false })
        .limit(5)

      return {
        business_id: business.id,
        business_name: business.name,
        subscription: subscription || { plan: 'free', status: 'active' },
        invoices: invoices || [],
        next_billing_date: subscription?.current_period_end,
        payment_method: await getPaymentMethod(supabase, business.id)
      }
    })
  )

  return {
    businesses: billingInfo,
    total_monthly_cost: calculateTotalMonthlyCost(billingInfo),
    payment_methods: await getPaymentMethods(supabase, userId)
  }
}

async function getUserNotifications(
  supabase: any,
  userId: string,
  filters?: any
): Promise<any[]> {
  
  let query = supabase
    .from('notifications')
    .select('*')
    .eq('user_id', userId)

  if (filters?.unread_only) {
    query = query.eq('read', false)
  }
  if (filters?.type) {
    query = query.eq('type', filters.type)
  }
  if (filters?.date_from) {
    query = query.gte('created_at', filters.date_from)
  }

  query = query.order('created_at', { ascending: false })
    .limit(filters?.limit || 50)

  const { data, error } = await query

  if (error) throw error

  return data
}

async function getUserActivityLog(
  supabase: any,
  userId: string,
  filters?: any
): Promise<any[]> {
  
  const businesses = await getUserBusinesses(supabase, userId)
  const businessIds = businesses.map(b => b.id)

  let query = supabase
    .from('activity_logs')
    .select('*')
    .or(`user_id.eq.${userId},business_id.in.(${businessIds.join(',')})`)

  if (filters?.action) {
    query = query.eq('action', filters.action)
  }
  if (filters?.resource_type) {
    query = query.eq('resource_type', filters.resource_type)
  }
  if (filters?.date_from) {
    query = query.gte('created_at', filters.date_from)
  }
  if (filters?.date_to) {
    query = query.lte('created_at', filters.date_to)
  }

  query = query.order('created_at', { ascending: false })
    .limit(filters?.limit || 100)

  const { data, error } = await query

  if (error) throw error

  return data
}

// Helper functions

async function encryptApiKeys(apiKeys: any): Promise<any> {
  const encrypted: any = {}
  
  for (const [key, value] of Object.entries(apiKeys)) {
    if (value) {
      // In production, use proper encryption
      encrypted[key] = await bcrypt.hash(value as string, 10)
    }
  }
  
  return encrypted
}

async function sendPermissionNotification(
  supabase: any,
  userId: string,
  action: 'granted' | 'revoked',
  permission: any
): Promise<void> {
  
  await supabase
    .from('notifications')
    .insert({
      user_id: userId,
      type: 'permission',
      title: `Permission ${action}`,
      message: `Your access to business has been ${action}`,
      data: permission,
      read: false,
      created_at: new Date().toISOString()
    })
}

function generateInviteToken(): string {
  return crypto.randomUUID()
}

async function sendInvitationEmail(
  email: string,
  invitation: any
): Promise<void> {
  // Send invitation email using email service
  console.log(`Sending invitation to ${email}`, invitation)
}

async function getPaymentMethod(
  supabase: any,
  businessId: string
): Promise<any> {
  // Get payment method for business
  // Placeholder implementation
  return {
    type: 'card',
    last4: '4242',
    brand: 'Visa'
  }
}

async function getPaymentMethods(
  supabase: any,
  userId: string
): Promise<any[]> {
  // Get all payment methods for user
  // Placeholder implementation
  return [
    {
      id: 'pm_1',
      type: 'card',
      last4: '4242',
      brand: 'Visa',
      is_default: true
    }
  ]
}

function calculateTotalMonthlyCost(billingInfo: any[]): number {
  const planCosts: Record<string, number> = {
    free: 0,
    starter: 29,
    pro: 99,
    enterprise: 299
  }
  
  return billingInfo.reduce((total, info) => {
    const plan = info.subscription?.plan || 'free'
    return total + (planCosts[plan] || 0)
  }, 0)
}