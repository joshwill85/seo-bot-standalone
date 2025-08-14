import { serve } from 'https://deno.land/std@0.168.0/http/server.ts'
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'
import { corsHeaders } from '../_shared/cors.ts'

interface TaskScheduleRequest {
  business_id: string
  campaign_id?: string
  schedule_type: 'immediate' | 'recurring' | 'conditional'
  task_type: 'keyword_discovery' | 'rank_tracking' | 'content_brief' | 'technical_audit' | 'competitor_analysis' | 'internal_linking' | 'content_analytics'
  frequency?: 'daily' | 'weekly' | 'monthly' | 'quarterly'
  schedule_time?: string // ISO string or cron expression
  conditions?: {
    trigger_type: 'ranking_change' | 'traffic_change' | 'new_content' | 'competitor_activity'
    threshold?: number
    comparison_period?: 'day' | 'week' | 'month'
  }
  task_config?: any
  priority?: 1 | 2 | 3 | 4 | 5
  auto_retry?: boolean
  max_retries?: number
}

interface ScheduledTask {
  id: string
  business_id: string
  campaign_id?: string
  task_type: string
  schedule_type: string
  frequency?: string
  next_run: string
  last_run?: string
  status: 'pending' | 'running' | 'completed' | 'failed' | 'paused'
  priority: number
  retry_count: number
  max_retries: number
  task_config: any
  conditions?: any
  created_at: string
  updated_at: string
}

interface AutomationRule {
  id: string
  business_id: string
  name: string
  description: string
  trigger_conditions: any
  actions: {
    task_type: string
    config: any
    delay_minutes?: number
  }[]
  is_active: boolean
  last_triggered?: string
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

    const url = new URL(req.url)
    const action = url.searchParams.get('action') || 'schedule'

    switch (action) {
      case 'schedule':
        return await handleScheduleTask(req, supabase)
      case 'execute':
        return await handleExecutePendingTasks(req, supabase)
      case 'status':
        return await handleGetTaskStatus(req, supabase)
      case 'automation':
        return await handleAutomationRules(req, supabase)
      case 'cancel':
        return await handleCancelTask(req, supabase)
      default:
        return new Response(
          JSON.stringify({ error: 'Invalid action' }),
          { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
        )
    }

  } catch (error) {
    console.error('Task scheduler error:', error)
    return new Response(
      JSON.stringify({ error: 'Internal server error', details: error.message }),
      { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }
})

async function handleScheduleTask(req: Request, supabase: any) {
  const {
    business_id,
    campaign_id,
    schedule_type,
    task_type,
    frequency,
    schedule_time,
    conditions,
    task_config = {},
    priority = 3,
    auto_retry = true,
    max_retries = 3
  }: TaskScheduleRequest = await req.json()

  // Validate required fields
  if (!business_id || !task_type || !schedule_type) {
    return new Response(
      JSON.stringify({ error: 'business_id, task_type, and schedule_type are required' }),
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

  // Calculate next run time
  const nextRun = calculateNextRun(schedule_type, frequency, schedule_time)

  // Create scheduled task
  const { data: scheduledTask, error } = await supabase
    .from('seo_tasks')
    .insert({
      business_id,
      campaign_id,
      task_type,
      task_name: generateTaskName(task_type, business.business_name),
      schedule_type,
      frequency,
      next_run: nextRun,
      status: schedule_type === 'immediate' ? 'pending' : 'scheduled',
      priority,
      retry_count: 0,
      max_retries,
      task_config,
      conditions,
      auto_retry,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    })
    .select()
    .single()

  if (error) {
    return new Response(
      JSON.stringify({ error: 'Failed to schedule task', details: error.message }),
      { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }

  // If immediate execution, add to execution queue
  if (schedule_type === 'immediate') {
    await executeTask(scheduledTask, supabase)
  }

  // Log the scheduling
  await supabase
    .from('seo_logs')
    .insert({
      business_id,
      action_type: 'task_scheduled',
      action_description: `Scheduled ${task_type} task`,
      new_data: JSON.stringify({
        task_id: scheduledTask.id,
        schedule_type,
        frequency,
        next_run: nextRun
      })
    })

  return new Response(
    JSON.stringify({
      success: true,
      task_id: scheduledTask.id,
      task_type,
      schedule_type,
      next_run: nextRun,
      status: scheduledTask.status
    }),
    { 
      status: 200, 
      headers: { ...corsHeaders, 'Content-Type': 'application/json' } 
    }
  )
}

async function handleExecutePendingTasks(req: Request, supabase: any) {
  const now = new Date().toISOString()
  
  // Get all pending tasks that are due
  const { data: pendingTasks } = await supabase
    .from('seo_tasks')
    .select('*')
    .in('status', ['pending', 'scheduled'])
    .lte('next_run', now)
    .order('priority', { ascending: false })
    .order('created_at', { ascending: true })
    .limit(50)

  if (!pendingTasks || pendingTasks.length === 0) {
    return new Response(
      JSON.stringify({
        success: true,
        message: 'No pending tasks to execute',
        tasks_executed: 0
      }),
      { 
        status: 200, 
        headers: { ...corsHeaders, 'Content-Type': 'application/json' } 
      }
    )
  }

  const executionResults = []
  
  // Execute tasks concurrently (but limit concurrency)
  const maxConcurrent = 5
  for (let i = 0; i < pendingTasks.length; i += maxConcurrent) {
    const batch = pendingTasks.slice(i, i + maxConcurrent)
    const batchPromises = batch.map(task => executeTask(task, supabase))
    const batchResults = await Promise.allSettled(batchPromises)
    
    batchResults.forEach((result, index) => {
      const task = batch[index]
      executionResults.push({
        task_id: task.id,
        task_type: task.task_type,
        status: result.status === 'fulfilled' ? 'completed' : 'failed',
        error: result.status === 'rejected' ? result.reason : null
      })
    })
  }

  const successCount = executionResults.filter(r => r.status === 'completed').length
  const failureCount = executionResults.filter(r => r.status === 'failed').length

  return new Response(
    JSON.stringify({
      success: true,
      tasks_executed: executionResults.length,
      successful: successCount,
      failed: failureCount,
      execution_results: executionResults
    }),
    { 
      status: 200, 
      headers: { ...corsHeaders, 'Content-Type': 'application/json' } 
    }
  )
}

async function executeTask(task: any, supabase: any): Promise<void> {
  try {
    // Update task status to running
    await supabase
      .from('seo_tasks')
      .update({
        status: 'running',
        started_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
      })
      .eq('id', task.id)

    // Execute the appropriate function based on task type
    let result
    const baseUrl = Deno.env.get('SUPABASE_URL')?.replace('/rest/v1', '') || ''
    
    const taskPayload = {
      business_id: task.business_id,
      campaign_id: task.campaign_id,
      ...task.task_config
    }

    const functionMap: { [key: string]: string } = {
      'keyword_discovery': 'seo-discover',
      'rank_tracking': 'seo-ranks',
      'content_brief': 'seo-brief',
      'technical_audit': 'seo-audit',
      'competitor_analysis': 'seo-competitors',
      'internal_linking': 'seo-links',
      'content_analytics': 'seo-analytics',
      'keyword_clustering': 'seo-cluster'
    }

    const functionName = functionMap[task.task_type]
    if (!functionName) {
      throw new Error(`Unknown task type: ${task.task_type}`)
    }

    // Call the appropriate Edge Function
    const response = await fetch(`${baseUrl}/functions/v1/${functionName}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')}`
      },
      body: JSON.stringify(taskPayload)
    })

    if (!response.ok) {
      throw new Error(`Function call failed: ${response.status} ${response.statusText}`)
    }

    result = await response.json()

    // Update task status to completed
    await supabase
      .from('seo_tasks')
      .update({
        status: 'completed',
        completed_at: new Date().toISOString(),
        result_data: result,
        updated_at: new Date().toISOString(),
        // Schedule next run if recurring
        next_run: task.schedule_type === 'recurring' ? 
          calculateNextRun('recurring', task.frequency) : null
      })
      .eq('id', task.id)

    // Log successful execution
    await supabase
      .from('seo_logs')
      .insert({
        business_id: task.business_id,
        action_type: 'task_executed',
        action_description: `Successfully executed ${task.task_type}`,
        new_data: JSON.stringify({
          task_id: task.id,
          execution_time: new Date().toISOString(),
          result_summary: result
        })
      })

  } catch (error) {
    console.error(`Task execution failed for task ${task.id}:`, error)
    
    // Handle retry logic
    const shouldRetry = task.auto_retry && task.retry_count < task.max_retries
    
    await supabase
      .from('seo_tasks')
      .update({
        status: shouldRetry ? 'pending' : 'failed',
        retry_count: task.retry_count + 1,
        error_message: error.message,
        updated_at: new Date().toISOString(),
        // Retry after exponential backoff
        next_run: shouldRetry ? 
          new Date(Date.now() + Math.pow(2, task.retry_count) * 60000).toISOString() : null
      })
      .eq('id', task.id)

    // Log execution failure
    await supabase
      .from('seo_logs')
      .insert({
        business_id: task.business_id,
        action_type: 'task_failed',
        action_description: `Failed to execute ${task.task_type}: ${error.message}`,
        new_data: JSON.stringify({
          task_id: task.id,
          error: error.message,
          retry_count: task.retry_count + 1,
          will_retry: shouldRetry
        })
      })

    if (!shouldRetry) {
      throw error
    }
  }
}

async function handleGetTaskStatus(req: Request, supabase: any) {
  const url = new URL(req.url)
  const business_id = url.searchParams.get('business_id')
  const task_id = url.searchParams.get('task_id')
  const limit = parseInt(url.searchParams.get('limit') || '50')

  if (!business_id) {
    return new Response(
      JSON.stringify({ error: 'business_id is required' }),
      { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }

  let query = supabase
    .from('seo_tasks')
    .select('*')
    .eq('business_id', business_id)

  if (task_id) {
    query = query.eq('id', task_id)
  }

  const { data: tasks } = await query
    .order('created_at', { ascending: false })
    .limit(limit)

  // Get summary statistics
  const summary = {
    total_tasks: tasks?.length || 0,
    pending: tasks?.filter(t => t.status === 'pending').length || 0,
    running: tasks?.filter(t => t.status === 'running').length || 0,
    completed: tasks?.filter(t => t.status === 'completed').length || 0,
    failed: tasks?.filter(t => t.status === 'failed').length || 0,
    scheduled: tasks?.filter(t => t.status === 'scheduled').length || 0
  }

  return new Response(
    JSON.stringify({
      success: true,
      summary,
      tasks: tasks || []
    }),
    { 
      status: 200, 
      headers: { ...corsHeaders, 'Content-Type': 'application/json' } 
    }
  )
}

async function handleAutomationRules(req: Request, supabase: any) {
  if (req.method === 'POST') {
    // Create new automation rule
    const ruleData = await req.json()
    
    const { data: rule, error } = await supabase
      .from('automation_rules')
      .insert({
        business_id: ruleData.business_id,
        name: ruleData.name,
        description: ruleData.description,
        trigger_conditions: ruleData.trigger_conditions,
        actions: ruleData.actions,
        is_active: ruleData.is_active ?? true,
        created_at: new Date().toISOString()
      })
      .select()
      .single()

    if (error) {
      return new Response(
        JSON.stringify({ error: 'Failed to create automation rule', details: error.message }),
        { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    return new Response(
      JSON.stringify({
        success: true,
        rule_id: rule.id,
        rule
      }),
      { 
        status: 200, 
        headers: { ...corsHeaders, 'Content-Type': 'application/json' } 
      }
    )
  } else {
    // Get automation rules
    const url = new URL(req.url)
    const business_id = url.searchParams.get('business_id')

    if (!business_id) {
      return new Response(
        JSON.stringify({ error: 'business_id is required' }),
        { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    const { data: rules } = await supabase
      .from('automation_rules')
      .select('*')
      .eq('business_id', business_id)
      .order('created_at', { ascending: false })

    return new Response(
      JSON.stringify({
        success: true,
        rules: rules || []
      }),
      { 
        status: 200, 
        headers: { ...corsHeaders, 'Content-Type': 'application/json' } 
      }
    )
  }
}

async function handleCancelTask(req: Request, supabase: any) {
  const { task_id, business_id } = await req.json()

  if (!task_id || !business_id) {
    return new Response(
      JSON.stringify({ error: 'task_id and business_id are required' }),
      { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }

  const { data: task, error } = await supabase
    .from('seo_tasks')
    .update({
      status: 'cancelled',
      updated_at: new Date().toISOString()
    })
    .eq('id', task_id)
    .eq('business_id', business_id)
    .select()
    .single()

  if (error || !task) {
    return new Response(
      JSON.stringify({ error: 'Task not found or could not be cancelled' }),
      { status: 404, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }

  return new Response(
    JSON.stringify({
      success: true,
      message: 'Task cancelled successfully',
      task_id: task.id
    }),
    { 
      status: 200, 
      headers: { ...corsHeaders, 'Content-Type': 'application/json' } 
    }
  )
}

function calculateNextRun(scheduleType: string, frequency?: string, scheduleTime?: string): string {
  const now = new Date()

  if (scheduleType === 'immediate') {
    return now.toISOString()
  }

  if (scheduleType === 'recurring' && frequency) {
    switch (frequency) {
      case 'daily':
        return new Date(now.getTime() + 24 * 60 * 60 * 1000).toISOString()
      case 'weekly':
        return new Date(now.getTime() + 7 * 24 * 60 * 60 * 1000).toISOString()
      case 'monthly':
        const nextMonth = new Date(now)
        nextMonth.setMonth(nextMonth.getMonth() + 1)
        return nextMonth.toISOString()
      case 'quarterly':
        const nextQuarter = new Date(now)
        nextQuarter.setMonth(nextQuarter.getMonth() + 3)
        return nextQuarter.toISOString()
    }
  }

  if (scheduleTime) {
    return new Date(scheduleTime).toISOString()
  }

  // Default to 1 hour from now
  return new Date(now.getTime() + 60 * 60 * 1000).toISOString()
}

function generateTaskName(taskType: string, businessName: string): string {
  const taskNames: { [key: string]: string } = {
    'keyword_discovery': 'Keyword Discovery',
    'rank_tracking': 'Rank Tracking',
    'content_brief': 'Content Brief Generation',
    'technical_audit': 'Technical SEO Audit',
    'competitor_analysis': 'Competitor Analysis',
    'internal_linking': 'Internal Link Analysis',
    'content_analytics': 'Content Performance Analysis',
    'keyword_clustering': 'Keyword Clustering'
  }

  const baseName = taskNames[taskType] || 'SEO Task'
  return `${baseName} - ${businessName}`
}