import { serve } from 'https://deno.land/std@0.168.0/http/server.ts'
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'
import { corsHeaders } from '../_shared/cors.ts'

interface RealtimeEvent {
  type: 'ranking_change' | 'traffic_update' | 'task_complete' | 'alert' | 'competitor_update' | 'content_published'
  business_id: string
  data: any
  timestamp: string
  priority: 'low' | 'medium' | 'high' | 'critical'
}

interface WebSocketMessage {
  action: 'subscribe' | 'unsubscribe' | 'ping' | 'broadcast'
  channels?: string[]
  data?: any
}

// Store active WebSocket connections
const connections = new Map<string, WebSocket>()
const subscriptions = new Map<string, Set<string>>() // userId -> Set of channels

serve(async (req) => {
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders })
  }

  try {
    const url = new URL(req.url)
    
    // Handle WebSocket upgrade
    if (req.headers.get('upgrade') === 'websocket') {
      return handleWebSocketUpgrade(req)
    }

    // Handle HTTP requests for broadcasting events
    if (url.pathname === '/broadcast') {
      return handleBroadcast(req)
    }

    // Handle SSE (Server-Sent Events) as fallback
    if (url.pathname === '/events') {
      return handleSSE(req)
    }

    const supabase = createClient(
      Deno.env.get('SUPABASE_URL') ?? '',
      Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') ?? ''
    )

    const { action, user_id, business_id, event_type, filters } = await req.json()

    switch (action) {
      case 'get_events':
        const events = await getRecentEvents(supabase, business_id, filters)
        return new Response(
          JSON.stringify(events),
          { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
        )

      case 'create_event':
        const event = await createEvent(supabase, business_id, event_type, await req.json())
        await broadcastEvent(event)
        return new Response(
          JSON.stringify(event),
          { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
        )

      default:
        throw new Error(`Unknown action: ${action}`)
    }

  } catch (error) {
    console.error('Realtime updates error:', error)
    return new Response(
      JSON.stringify({ error: error.message }),
      { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }
})

function handleWebSocketUpgrade(req: Request): Response {
  const upgrade = req.headers.get('upgrade') || ''
  if (upgrade.toLowerCase() !== 'websocket') {
    return new Response('Expected websocket', { status: 426 })
  }

  const { socket, response } = Deno.upgradeWebSocket(req)
  const userId = new URL(req.url).searchParams.get('user_id') || ''

  socket.onopen = () => {
    console.log('WebSocket connection opened for user:', userId)
    connections.set(userId, socket)
    subscriptions.set(userId, new Set())
    
    // Send welcome message
    socket.send(JSON.stringify({
      type: 'connected',
      message: 'Connected to SEO Bot realtime updates',
      timestamp: new Date().toISOString()
    }))
  }

  socket.onmessage = async (e) => {
    try {
      const message: WebSocketMessage = JSON.parse(e.data)
      await handleWebSocketMessage(userId, message, socket)
    } catch (error) {
      console.error('WebSocket message error:', error)
      socket.send(JSON.stringify({
        type: 'error',
        message: 'Invalid message format'
      }))
    }
  }

  socket.onclose = () => {
    console.log('WebSocket connection closed for user:', userId)
    connections.delete(userId)
    subscriptions.delete(userId)
  }

  socket.onerror = (e) => {
    console.error('WebSocket error:', e)
  }

  return response
}

async function handleWebSocketMessage(
  userId: string, 
  message: WebSocketMessage,
  socket: WebSocket
): Promise<void> {
  switch (message.action) {
    case 'subscribe':
      if (message.channels) {
        const userSubs = subscriptions.get(userId) || new Set()
        message.channels.forEach(channel => userSubs.add(channel))
        subscriptions.set(userId, userSubs)
        
        socket.send(JSON.stringify({
          type: 'subscribed',
          channels: message.channels,
          timestamp: new Date().toISOString()
        }))
      }
      break

    case 'unsubscribe':
      if (message.channels) {
        const userSubs = subscriptions.get(userId)
        if (userSubs) {
          message.channels.forEach(channel => userSubs.delete(channel))
        }
        
        socket.send(JSON.stringify({
          type: 'unsubscribed',
          channels: message.channels,
          timestamp: new Date().toISOString()
        }))
      }
      break

    case 'ping':
      socket.send(JSON.stringify({
        type: 'pong',
        timestamp: new Date().toISOString()
      }))
      break

    case 'broadcast':
      if (message.data) {
        await broadcastToChannel(message.data.channel, message.data)
      }
      break
  }
}

async function handleBroadcast(req: Request): Promise<Response> {
  try {
    const event = await req.json()
    await broadcastEvent(event)
    
    return new Response(
      JSON.stringify({ success: true }),
      { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  } catch (error) {
    return new Response(
      JSON.stringify({ error: error.message }),
      { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }
}

async function handleSSE(req: Request): Promise<Response> {
  const stream = new TransformStream()
  const writer = stream.writable.getWriter()
  const encoder = new TextEncoder()

  const userId = new URL(req.url).searchParams.get('user_id') || ''
  const businessId = new URL(req.url).searchParams.get('business_id') || ''

  // Send initial connection message
  await writer.write(
    encoder.encode(`data: ${JSON.stringify({
      type: 'connected',
      timestamp: new Date().toISOString()
    })}\n\n`)
  )

  // Set up periodic updates
  const interval = setInterval(async () => {
    try {
      const supabase = createClient(
        Deno.env.get('SUPABASE_URL') ?? '',
        Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') ?? ''
      )

      const events = await getRecentEvents(supabase, businessId, { limit: 5 })
      
      for (const event of events) {
        await writer.write(
          encoder.encode(`data: ${JSON.stringify(event)}\n\n`)
        )
      }
    } catch (error) {
      console.error('SSE error:', error)
    }
  }, 5000) // Send updates every 5 seconds

  // Clean up on disconnect
  req.signal.addEventListener('abort', () => {
    clearInterval(interval)
    writer.close()
  })

  return new Response(stream.readable, {
    headers: {
      ...corsHeaders,
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      'Connection': 'keep-alive'
    }
  })
}

async function broadcastEvent(event: RealtimeEvent): Promise<void> {
  const channel = `business_${event.business_id}`
  await broadcastToChannel(channel, event)
  
  // Also broadcast to specific event type channels
  const typeChannel = `${channel}_${event.type}`
  await broadcastToChannel(typeChannel, event)
}

async function broadcastToChannel(channel: string, data: any): Promise<void> {
  // Send to all WebSocket connections subscribed to this channel
  for (const [userId, userChannels] of subscriptions.entries()) {
    if (userChannels.has(channel)) {
      const socket = connections.get(userId)
      if (socket && socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({
          type: 'event',
          channel,
          data,
          timestamp: new Date().toISOString()
        }))
      }
    }
  }
}

async function getRecentEvents(
  supabase: any,
  businessId: string,
  filters?: any
): Promise<RealtimeEvent[]> {
  const events: RealtimeEvent[] = []

  // Get recent ranking changes
  const { data: rankings } = await supabase
    .from('keyword_rankings')
    .select(`
      *,
      keywords(keyword)
    `)
    .eq('business_id', businessId)
    .order('created_at', { ascending: false })
    .limit(filters?.limit || 10)

  rankings?.forEach((ranking: any) => {
    if (ranking.position_change && Math.abs(ranking.position_change) >= 3) {
      events.push({
        type: 'ranking_change',
        business_id: businessId,
        data: {
          keyword: ranking.keywords.keyword,
          old_position: ranking.position + ranking.position_change,
          new_position: ranking.position,
          change: ranking.position_change
        },
        timestamp: ranking.created_at,
        priority: Math.abs(ranking.position_change) >= 10 ? 'high' : 'medium'
      })
    }
  })

  // Get recent alerts
  const { data: alerts } = await supabase
    .from('monitoring_alerts')
    .select('*')
    .eq('business_id', businessId)
    .eq('status', 'active')
    .order('created_at', { ascending: false })
    .limit(5)

  alerts?.forEach((alert: any) => {
    events.push({
      type: 'alert',
      business_id: businessId,
      data: alert,
      timestamp: alert.created_at,
      priority: alert.severity === 'critical' ? 'critical' : 
               alert.severity === 'warning' ? 'high' : 'medium'
    })
  })

  // Get recent task completions
  const { data: tasks } = await supabase
    .from('campaign_tasks')
    .select(`
      *,
      campaigns(name, business_id)
    `)
    .eq('status', 'completed')
    .eq('campaigns.business_id', businessId)
    .order('completed_at', { ascending: false })
    .limit(5)

  tasks?.forEach((task: any) => {
    if (task.campaigns) {
      events.push({
        type: 'task_complete',
        business_id: businessId,
        data: {
          task_id: task.id,
          task_type: task.task_type,
          campaign: task.campaigns.name,
          completed_at: task.completed_at
        },
        timestamp: task.completed_at,
        priority: task.priority === 'critical' ? 'high' : 'low'
      })
    }
  })

  // Sort events by timestamp
  events.sort((a, b) => 
    new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
  )

  return events.slice(0, filters?.limit || 10)
}

async function createEvent(
  supabase: any,
  businessId: string,
  eventType: string,
  data: any
): Promise<RealtimeEvent> {
  const event: RealtimeEvent = {
    type: eventType as any,
    business_id: businessId,
    data,
    timestamp: new Date().toISOString(),
    priority: data.priority || 'medium'
  }

  // Store event in database for history
  await supabase
    .from('realtime_events')
    .insert({
      business_id: businessId,
      event_type: eventType,
      event_data: data,
      priority: event.priority,
      created_at: event.timestamp
    })

  return event
}

// Monitor database changes and broadcast updates
async function setupDatabaseListeners(): Promise<void> {
  const supabase = createClient(
    Deno.env.get('SUPABASE_URL') ?? '',
    Deno.env.get('SUPABASE_ANON_KEY') ?? ''
  )

  // Listen for ranking changes
  supabase
    .channel('ranking_changes')
    .on('postgres_changes', {
      event: 'INSERT',
      schema: 'public',
      table: 'keyword_rankings'
    }, async (payload) => {
      const event: RealtimeEvent = {
        type: 'ranking_change',
        business_id: payload.new.business_id,
        data: payload.new,
        timestamp: new Date().toISOString(),
        priority: 'medium'
      }
      await broadcastEvent(event)
    })
    .subscribe()

  // Listen for new alerts
  supabase
    .channel('new_alerts')
    .on('postgres_changes', {
      event: 'INSERT',
      schema: 'public',
      table: 'monitoring_alerts'
    }, async (payload) => {
      const event: RealtimeEvent = {
        type: 'alert',
        business_id: payload.new.business_id,
        data: payload.new,
        timestamp: new Date().toISOString(),
        priority: payload.new.severity === 'critical' ? 'critical' : 'high'
      }
      await broadcastEvent(event)
    })
    .subscribe()

  // Listen for task completions
  supabase
    .channel('task_updates')
    .on('postgres_changes', {
      event: 'UPDATE',
      schema: 'public',
      table: 'campaign_tasks',
      filter: 'status=eq.completed'
    }, async (payload) => {
      if (payload.new.status === 'completed' && payload.old.status !== 'completed') {
        // Get campaign details
        const { data: campaign } = await supabase
          .from('campaigns')
          .select('name, business_id')
          .eq('id', payload.new.campaign_id)
          .single()

        if (campaign) {
          const event: RealtimeEvent = {
            type: 'task_complete',
            business_id: campaign.business_id,
            data: {
              ...payload.new,
              campaign_name: campaign.name
            },
            timestamp: new Date().toISOString(),
            priority: 'low'
          }
          await broadcastEvent(event)
        }
      }
    })
    .subscribe()
}

// Initialize database listeners on startup
setupDatabaseListeners()