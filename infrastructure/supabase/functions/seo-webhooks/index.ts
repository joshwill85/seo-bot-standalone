import { serve } from 'https://deno.land/std@0.168.0/http/server.ts'
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'
import { corsHeaders } from '../_shared/cors.ts'

interface WebhookRequest {
  business_id: string
  action: 'configure' | 'test' | 'send' | 'list' | 'delete'
  webhook_config?: WebhookConfiguration
  webhook_id?: string
  notification_data?: NotificationData
}

interface WebhookConfiguration {
  name: string
  webhook_type: 'slack' | 'discord' | 'teams' | 'email' | 'custom'
  webhook_url?: string
  email_config?: {
    smtp_host: string
    smtp_port: number
    smtp_user: string
    smtp_password: string
    from_email: string
    from_name: string
  }
  slack_config?: {
    webhook_url: string
    channel: string
    username?: string
    icon_emoji?: string
  }
  discord_config?: {
    webhook_url: string
    username?: string
    avatar_url?: string
  }
  teams_config?: {
    webhook_url: string
  }
  trigger_events: string[]
  is_active: boolean
  filters?: {
    severity_levels?: string[]
    alert_types?: string[]
    campaign_ids?: string[]
  }
}

interface NotificationData {
  event_type: string
  severity: 'low' | 'medium' | 'high' | 'critical'
  title: string
  message: string
  data: any
  business_name: string
  timestamp: string
  action_url?: string
}

interface SlackPayload {
  text?: string
  attachments?: {
    color: string
    title: string
    text: string
    fields: { title: string; value: string; short: boolean }[]
    footer: string
    ts: number
  }[]
  username?: string
  icon_emoji?: string
  channel?: string
}

interface DiscordPayload {
  content?: string
  embeds?: {
    title: string
    description: string
    color: number
    fields: { name: string; value: string; inline: boolean }[]
    footer: { text: string }
    timestamp: string
  }[]
  username?: string
  avatar_url?: string
}

interface TeamsPayload {
  '@type': string
  '@context': string
  summary: string
  themeColor: string
  sections: {
    activityTitle: string
    activitySubtitle: string
    facts: { name: string; value: string }[]
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
      action,
      webhook_config,
      webhook_id,
      notification_data
    }: WebhookRequest = await req.json()

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
      .select('id, business_name')
      .eq('id', business_id)
      .single()

    if (!business) {
      return new Response(
        JSON.stringify({ error: 'Business not found' }),
        { status: 404, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    switch (action) {
      case 'configure':
        return await handleConfigureWebhook(supabase, business_id, webhook_config)
      case 'test':
        return await handleTestWebhook(supabase, business, webhook_id)
      case 'send':
        return await handleSendNotification(supabase, business, notification_data)
      case 'list':
        return await handleListWebhooks(supabase, business_id)
      case 'delete':
        return await handleDeleteWebhook(supabase, business_id, webhook_id)
      default:
        return new Response(
          JSON.stringify({ error: 'Invalid action' }),
          { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
        )
    }

  } catch (error) {
    console.error('Webhook integration error:', error)
    return new Response(
      JSON.stringify({ error: 'Internal server error', details: error.message }),
      { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }
})

async function handleConfigureWebhook(supabase: any, business_id: string, webhook_config?: WebhookConfiguration) {
  if (!webhook_config) {
    return new Response(
      JSON.stringify({ error: 'webhook_config is required' }),
      { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }

  // Validate webhook configuration
  const validationResult = validateWebhookConfig(webhook_config)
  if (!validationResult.valid) {
    return new Response(
      JSON.stringify({ error: 'Invalid webhook configuration', details: validationResult.errors }),
      { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }

  // Store webhook configuration
  const { data: webhook, error } = await supabase
    .from('webhook_configurations')
    .upsert({
      business_id,
      name: webhook_config.name,
      webhook_type: webhook_config.webhook_type,
      webhook_url: webhook_config.webhook_url,
      email_config: webhook_config.email_config,
      slack_config: webhook_config.slack_config,
      discord_config: webhook_config.discord_config,
      teams_config: webhook_config.teams_config,
      trigger_events: webhook_config.trigger_events,
      filters: webhook_config.filters,
      is_active: webhook_config.is_active,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    }, {
      onConflict: 'business_id,name'
    })
    .select()
    .single()

  if (error) {
    return new Response(
      JSON.stringify({ error: 'Failed to configure webhook', details: error.message }),
      { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }

  // Log the configuration
  await supabase
    .from('seo_logs')
    .insert({
      business_id,
      action_type: 'webhook_configured',
      action_description: `Webhook "${webhook_config.name}" configured for ${webhook_config.webhook_type}`,
      new_data: JSON.stringify({
        webhook_id: webhook.id,
        webhook_type: webhook_config.webhook_type,
        trigger_events: webhook_config.trigger_events
      })
    })

  return new Response(
    JSON.stringify({
      success: true,
      message: 'Webhook configured successfully',
      webhook_id: webhook.id,
      webhook_type: webhook_config.webhook_type
    }),
    { 
      status: 200, 
      headers: { ...corsHeaders, 'Content-Type': 'application/json' } 
    }
  )
}

async function handleTestWebhook(supabase: any, business: any, webhook_id?: string) {
  if (!webhook_id) {
    return new Response(
      JSON.stringify({ error: 'webhook_id is required' }),
      { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }

  // Get webhook configuration
  const { data: webhook } = await supabase
    .from('webhook_configurations')
    .select('*')
    .eq('id', webhook_id)
    .eq('business_id', business.id)
    .single()

  if (!webhook) {
    return new Response(
      JSON.stringify({ error: 'Webhook configuration not found' }),
      { status: 404, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }

  // Create test notification
  const testNotification: NotificationData = {
    event_type: 'webhook_test',
    severity: 'low',
    title: 'Webhook Test',
    message: 'This is a test notification to verify webhook integration is working correctly.',
    data: {
      test: true,
      webhook_type: webhook.webhook_type,
      configured_at: webhook.created_at
    },
    business_name: business.business_name,
    timestamp: new Date().toISOString(),
    action_url: `${Deno.env.get('SUPABASE_URL')}/dashboard/${business.id}`
  }

  // Send test notification
  const result = await sendWebhookNotification(webhook, testNotification)

  // Log the test
  await supabase
    .from('seo_logs')
    .insert({
      business_id: business.id,
      action_type: 'webhook_tested',
      action_description: `Test notification sent to ${webhook.name} (${webhook.webhook_type})`,
      new_data: JSON.stringify({
        webhook_id: webhook.id,
        success: result.success,
        response_status: result.status
      })
    })

  return new Response(
    JSON.stringify({
      success: result.success,
      message: result.success ? 'Test notification sent successfully' : 'Test notification failed',
      webhook_name: webhook.name,
      webhook_type: webhook.webhook_type,
      response_status: result.status,
      error: result.error
    }),
    { 
      status: result.success ? 200 : 500, 
      headers: { ...corsHeaders, 'Content-Type': 'application/json' } 
    }
  )
}

async function handleSendNotification(supabase: any, business: any, notification_data?: NotificationData) {
  if (!notification_data) {
    return new Response(
      JSON.stringify({ error: 'notification_data is required' }),
      { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }

  // Get all active webhooks for this business that match the event type
  const { data: webhooks } = await supabase
    .from('webhook_configurations')
    .select('*')
    .eq('business_id', business.id)
    .eq('is_active', true)

  if (!webhooks || webhooks.length === 0) {
    return new Response(
      JSON.stringify({
        success: true,
        message: 'No active webhooks configured',
        notifications_sent: 0
      }),
      { 
        status: 200, 
        headers: { ...corsHeaders, 'Content-Type': 'application/json' } 
      }
    )
  }

  // Filter webhooks based on trigger events and filters
  const relevantWebhooks = webhooks.filter(webhook => {
    // Check if this event type is in trigger events
    if (!webhook.trigger_events.includes(notification_data.event_type)) {
      return false
    }

    // Apply filters if configured
    if (webhook.filters) {
      if (webhook.filters.severity_levels && 
          !webhook.filters.severity_levels.includes(notification_data.severity)) {
        return false
      }
      
      if (webhook.filters.alert_types && 
          notification_data.data?.alert_type &&
          !webhook.filters.alert_types.includes(notification_data.data.alert_type)) {
        return false
      }
    }

    return true
  })

  // Send notifications to all relevant webhooks
  const results = []
  for (const webhook of relevantWebhooks) {
    const result = await sendWebhookNotification(webhook, notification_data)
    results.push({
      webhook_name: webhook.name,
      webhook_type: webhook.webhook_type,
      success: result.success,
      status: result.status,
      error: result.error
    })
  }

  const successCount = results.filter(r => r.success).length

  // Log the notification
  await supabase
    .from('seo_logs')
    .insert({
      business_id: business.id,
      action_type: 'notification_sent',
      action_description: `Notification "${notification_data.title}" sent to ${successCount} webhooks`,
      new_data: JSON.stringify({
        event_type: notification_data.event_type,
        severity: notification_data.severity,
        webhooks_attempted: results.length,
        webhooks_successful: successCount,
        results
      })
    })

  return new Response(
    JSON.stringify({
      success: true,
      message: `Notification sent to ${successCount} of ${results.length} webhooks`,
      notifications_sent: successCount,
      total_webhooks: results.length,
      results
    }),
    { 
      status: 200, 
      headers: { ...corsHeaders, 'Content-Type': 'application/json' } 
    }
  )
}

async function handleListWebhooks(supabase: any, business_id: string) {
  const { data: webhooks } = await supabase
    .from('webhook_configurations')
    .select('id, name, webhook_type, trigger_events, is_active, created_at, updated_at')
    .eq('business_id', business_id)
    .order('created_at', { ascending: false })

  return new Response(
    JSON.stringify({
      success: true,
      webhooks: webhooks || [],
      total_webhooks: webhooks?.length || 0
    }),
    { 
      status: 200, 
      headers: { ...corsHeaders, 'Content-Type': 'application/json' } 
    }
  )
}

async function handleDeleteWebhook(supabase: any, business_id: string, webhook_id?: string) {
  if (!webhook_id) {
    return new Response(
      JSON.stringify({ error: 'webhook_id is required' }),
      { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }

  const { data: webhook, error } = await supabase
    .from('webhook_configurations')
    .delete()
    .eq('id', webhook_id)
    .eq('business_id', business_id)
    .select()
    .single()

  if (error || !webhook) {
    return new Response(
      JSON.stringify({ error: 'Webhook not found or could not be deleted' }),
      { status: 404, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }

  // Log the deletion
  await supabase
    .from('seo_logs')
    .insert({
      business_id,
      action_type: 'webhook_deleted',
      action_description: `Webhook "${webhook.name}" deleted`,
      new_data: JSON.stringify({
        webhook_id: webhook.id,
        webhook_type: webhook.webhook_type
      })
    })

  return new Response(
    JSON.stringify({
      success: true,
      message: 'Webhook deleted successfully',
      webhook_name: webhook.name
    }),
    { 
      status: 200, 
      headers: { ...corsHeaders, 'Content-Type': 'application/json' } 
    }
  )
}

function validateWebhookConfig(config: WebhookConfiguration): { valid: boolean; errors: string[] } {
  const errors: string[] = []

  if (!config.name || config.name.trim().length === 0) {
    errors.push('Webhook name is required')
  }

  if (!config.webhook_type) {
    errors.push('Webhook type is required')
  }

  if (!config.trigger_events || config.trigger_events.length === 0) {
    errors.push('At least one trigger event is required')
  }

  // Validate type-specific configurations
  switch (config.webhook_type) {
    case 'slack':
      if (!config.slack_config?.webhook_url) {
        errors.push('Slack webhook URL is required')
      }
      break
    case 'discord':
      if (!config.discord_config?.webhook_url) {
        errors.push('Discord webhook URL is required')
      }
      break
    case 'teams':
      if (!config.teams_config?.webhook_url) {
        errors.push('Teams webhook URL is required')
      }
      break
    case 'email':
      if (!config.email_config) {
        errors.push('Email configuration is required')
      } else {
        if (!config.email_config.smtp_host) errors.push('SMTP host is required')
        if (!config.email_config.smtp_user) errors.push('SMTP user is required')
        if (!config.email_config.from_email) errors.push('From email is required')
      }
      break
    case 'custom':
      if (!config.webhook_url) {
        errors.push('Webhook URL is required for custom webhooks')
      }
      break
  }

  return {
    valid: errors.length === 0,
    errors
  }
}

async function sendWebhookNotification(webhook: any, notification: NotificationData): Promise<{ success: boolean; status?: number; error?: string }> {
  try {
    switch (webhook.webhook_type) {
      case 'slack':
        return await sendSlackNotification(webhook.slack_config, notification)
      case 'discord':
        return await sendDiscordNotification(webhook.discord_config, notification)
      case 'teams':
        return await sendTeamsNotification(webhook.teams_config, notification)
      case 'email':
        return await sendEmailNotification(webhook.email_config, notification)
      case 'custom':
        return await sendCustomWebhook(webhook.webhook_url, notification)
      default:
        return { success: false, error: 'Unknown webhook type' }
    }
  } catch (error) {
    console.error(`Webhook notification failed for ${webhook.name}:`, error)
    return { success: false, error: error.message }
  }
}

async function sendSlackNotification(config: any, notification: NotificationData): Promise<{ success: boolean; status?: number; error?: string }> {
  const color = getSeverityColor(notification.severity)
  
  const payload: SlackPayload = {
    text: `SEO Alert: ${notification.title}`,
    attachments: [{
      color,
      title: notification.title,
      text: notification.message,
      fields: [
        { title: 'Business', value: notification.business_name, short: true },
        { title: 'Severity', value: notification.severity.toUpperCase(), short: true },
        { title: 'Event Type', value: notification.event_type, short: true },
        { title: 'Timestamp', value: new Date(notification.timestamp).toLocaleString(), short: true }
      ],
      footer: 'SEO Bot Notification',
      ts: Math.floor(new Date(notification.timestamp).getTime() / 1000)
    }],
    username: config.username || 'SEO Bot',
    icon_emoji: config.icon_emoji || ':chart_with_upwards_trend:',
    channel: config.channel
  }

  const response = await fetch(config.webhook_url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  })

  return {
    success: response.ok,
    status: response.status,
    error: response.ok ? undefined : `HTTP ${response.status}: ${response.statusText}`
  }
}

async function sendDiscordNotification(config: any, notification: NotificationData): Promise<{ success: boolean; status?: number; error?: string }> {
  const color = getSeverityColorHex(notification.severity)
  
  const payload: DiscordPayload = {
    embeds: [{
      title: notification.title,
      description: notification.message,
      color,
      fields: [
        { name: 'Business', value: notification.business_name, inline: true },
        { name: 'Severity', value: notification.severity.toUpperCase(), inline: true },
        { name: 'Event Type', value: notification.event_type, inline: true }
      ],
      footer: { text: 'SEO Bot Notification' },
      timestamp: notification.timestamp
    }],
    username: config.username || 'SEO Bot',
    avatar_url: config.avatar_url
  }

  const response = await fetch(config.webhook_url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  })

  return {
    success: response.ok,
    status: response.status,
    error: response.ok ? undefined : `HTTP ${response.status}: ${response.statusText}`
  }
}

async function sendTeamsNotification(config: any, notification: NotificationData): Promise<{ success: boolean; status?: number; error?: string }> {
  const themeColor = getSeverityColorHex(notification.severity).toString(16).padStart(6, '0')
  
  const payload: TeamsPayload = {
    '@type': 'MessageCard',
    '@context': 'http://schema.org/extensions',
    summary: notification.title,
    themeColor,
    sections: [{
      activityTitle: notification.title,
      activitySubtitle: notification.message,
      facts: [
        { name: 'Business', value: notification.business_name },
        { name: 'Severity', value: notification.severity.toUpperCase() },
        { name: 'Event Type', value: notification.event_type },
        { name: 'Timestamp', value: new Date(notification.timestamp).toLocaleString() }
      ]
    }]
  }

  const response = await fetch(config.webhook_url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  })

  return {
    success: response.ok,
    status: response.status,
    error: response.ok ? undefined : `HTTP ${response.status}: ${response.statusText}`
  }
}

async function sendEmailNotification(config: any, notification: NotificationData): Promise<{ success: boolean; status?: number; error?: string }> {
  // In a real implementation, this would use an SMTP client or email service API
  // For now, we'll simulate email sending
  console.log(`Sending email notification: ${notification.title}`)
  
  const emailHTML = generateEmailHTML(notification)
  
  // Simulate email service call
  const simulatedResponse = {
    ok: true,
    status: 200
  }
  
  return {
    success: simulatedResponse.ok,
    status: simulatedResponse.status,
    error: simulatedResponse.ok ? undefined : 'Email delivery failed'
  }
}

async function sendCustomWebhook(webhookUrl: string, notification: NotificationData): Promise<{ success: boolean; status?: number; error?: string }> {
  const payload = {
    event_type: notification.event_type,
    severity: notification.severity,
    title: notification.title,
    message: notification.message,
    business_name: notification.business_name,
    timestamp: notification.timestamp,
    data: notification.data,
    action_url: notification.action_url
  }

  const response = await fetch(webhookUrl, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  })

  return {
    success: response.ok,
    status: response.status,
    error: response.ok ? undefined : `HTTP ${response.status}: ${response.statusText}`
  }
}

function getSeverityColor(severity: string): string {
  switch (severity) {
    case 'critical': return 'danger'
    case 'high': return 'warning'
    case 'medium': return '#ff9500'
    case 'low': return 'good'
    default: return '#36a64f'
  }
}

function getSeverityColorHex(severity: string): number {
  switch (severity) {
    case 'critical': return 0xff0000 // Red
    case 'high': return 0xff9500 // Orange
    case 'medium': return 0xffff00 // Yellow
    case 'low': return 0x00ff00 // Green
    default: return 0x36a64f // Default green
  }
}

function generateEmailHTML(notification: NotificationData): string {
  return `
    <!DOCTYPE html>
    <html>
    <head>
      <style>
        body { font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; }
        .header { background-color: #f8f9fa; padding: 20px; text-align: center; }
        .content { padding: 20px; }
        .severity-${notification.severity} { border-left: 4px solid ${getSeverityColor(notification.severity)}; padding-left: 10px; }
        .footer { background-color: #f8f9fa; padding: 10px; text-align: center; font-size: 12px; }
      </style>
    </head>
    <body>
      <div class="header">
        <h2>SEO Alert Notification</h2>
      </div>
      <div class="content severity-${notification.severity}">
        <h3>${notification.title}</h3>
        <p><strong>Business:</strong> ${notification.business_name}</p>
        <p><strong>Severity:</strong> ${notification.severity.toUpperCase()}</p>
        <p><strong>Event Type:</strong> ${notification.event_type}</p>
        <p><strong>Message:</strong></p>
        <p>${notification.message}</p>
        <p><strong>Timestamp:</strong> ${new Date(notification.timestamp).toLocaleString()}</p>
        ${notification.action_url ? `<p><a href="${notification.action_url}">View Details</a></p>` : ''}
      </div>
      <div class="footer">
        <p>This is an automated notification from SEO Bot</p>
      </div>
    </body>
    </html>
  `
}