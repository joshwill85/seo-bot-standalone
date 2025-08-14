import { serve } from 'https://deno.land/std@0.168.0/http/server.ts'
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'
import { corsHeaders } from '../_shared/cors.ts'

interface MonitoringRequest {
  business_id: string
  campaign_id?: string
  action: 'check' | 'configure' | 'acknowledge' | 'resolve' | 'list'
  alert_config?: AlertConfiguration
  alert_id?: string
  check_type?: 'rankings' | 'traffic' | 'competitors' | 'technical' | 'all'
}

interface AlertConfiguration {
  alert_type: string
  thresholds: {
    ranking_drop?: number // positions
    traffic_drop?: number // percentage
    traffic_spike?: number // percentage
    new_competitor_threshold?: number // DA score
    technical_score_drop?: number // percentage
  }
  frequency: 'real_time' | 'hourly' | 'daily' | 'weekly'
  severity_rules: {
    high_threshold?: number
    critical_threshold?: number
  }
  notification_channels: string[] // email, webhook, slack
}

interface AlertTrigger {
  alert_type: string
  severity: 'low' | 'medium' | 'high' | 'critical'
  title: string
  message: string
  trigger_data: any
  current_value: number
  previous_value?: number
  percentage_change?: number
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
      campaign_id,
      action,
      alert_config,
      alert_id,
      check_type = 'all'
    }: MonitoringRequest = await req.json()

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
      .select('id, business_name, website_url')
      .eq('id', business_id)
      .single()

    if (!business) {
      return new Response(
        JSON.stringify({ error: 'Business not found' }),
        { status: 404, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    switch (action) {
      case 'check':
        return await handleMonitoringCheck(supabase, business, campaign_id, check_type)
      case 'configure':
        return await handleAlertConfiguration(supabase, business_id, alert_config)
      case 'acknowledge':
        return await handleAcknowledgeAlert(supabase, business_id, alert_id)
      case 'resolve':
        return await handleResolveAlert(supabase, business_id, alert_id)
      case 'list':
        return await handleListAlerts(supabase, business_id, campaign_id)
      default:
        return new Response(
          JSON.stringify({ error: 'Invalid action' }),
          { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
        )
    }

  } catch (error) {
    console.error('Monitoring error:', error)
    return new Response(
      JSON.stringify({ error: 'Internal server error', details: error.message }),
      { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }
})

async function handleMonitoringCheck(supabase: any, business: any, campaign_id?: string, check_type?: string) {
  const alerts: AlertTrigger[] = []
  const checkResults = {
    rankings_checked: false,
    traffic_checked: false,
    competitors_checked: false,
    technical_checked: false
  }

  // Get alert configurations for this business
  const { data: alertConfigs } = await supabase
    .from('alert_configurations')
    .select('*')
    .eq('business_id', business.id)
    .eq('is_active', true)

  if (!alertConfigs || alertConfigs.length === 0) {
    // Create default alert configuration
    await createDefaultAlertConfig(supabase, business.id)
  }

  if (check_type === 'all' || check_type === 'rankings') {
    const rankingAlerts = await checkRankingChanges(supabase, business, campaign_id, alertConfigs)
    alerts.push(...rankingAlerts)
    checkResults.rankings_checked = true
  }

  if (check_type === 'all' || check_type === 'traffic') {
    const trafficAlerts = await checkTrafficChanges(supabase, business, campaign_id, alertConfigs)
    alerts.push(...trafficAlerts)
    checkResults.traffic_checked = true
  }

  if (check_type === 'all' || check_type === 'competitors') {
    const competitorAlerts = await checkCompetitorActivity(supabase, business, campaign_id, alertConfigs)
    alerts.push(...competitorAlerts)
    checkResults.competitors_checked = true
  }

  if (check_type === 'all' || check_type === 'technical') {
    const technicalAlerts = await checkTechnicalIssues(supabase, business, campaign_id, alertConfigs)
    alerts.push(...technicalAlerts)
    checkResults.technical_checked = true
  }

  // Store alerts in database
  const storedAlerts = []
  for (const alert of alerts) {
    const { data: storedAlert } = await supabase
      .from('monitoring_alerts')
      .insert({
        business_id: business.id,
        campaign_id,
        alert_type: alert.alert_type,
        severity: alert.severity,
        title: alert.title,
        message: alert.message,
        trigger_data: alert.trigger_data,
        current_value: alert.current_value,
        previous_value: alert.previous_value,
        percentage_change: alert.percentage_change,
        status: 'active'
      })
      .select()
      .single()

    if (storedAlert) {
      storedAlerts.push(storedAlert)
      
      // Send notifications if configured
      await sendAlertNotifications(supabase, storedAlert, alertConfigs)
    }
  }

  // Log monitoring check
  await supabase
    .from('seo_logs')
    .insert({
      business_id: business.id,
      action_type: 'monitoring_check',
      action_description: `Monitoring check completed: ${alerts.length} alerts generated`,
      new_data: JSON.stringify({
        campaign_id,
        check_type,
        alerts_generated: alerts.length,
        check_results
      })
    })

  return new Response(
    JSON.stringify({
      success: true,
      business_name: business.business_name,
      check_type,
      alerts_generated: alerts.length,
      alerts: alerts.map(alert => ({
        type: alert.alert_type,
        severity: alert.severity,
        title: alert.title,
        message: alert.message
      })),
      check_results
    }),
    { 
      status: 200, 
      headers: { ...corsHeaders, 'Content-Type': 'application/json' } 
    }
  )
}

async function checkRankingChanges(supabase: any, business: any, campaign_id?: string, alertConfigs?: any[]): Promise<AlertTrigger[]> {
  const alerts: AlertTrigger[] = []
  
  // Get recent rank tracking data
  const threeDaysAgo = new Date(Date.now() - 3 * 24 * 60 * 60 * 1000).toISOString()
  
  let query = supabase
    .from('rank_tracking')
    .select('*')
    .eq('business_id', business.id)
    .gte('tracked_at', threeDaysAgo)
    .order('tracked_at', { ascending: false })

  if (campaign_id) {
    query = query.eq('campaign_id', campaign_id)
  }

  const { data: rankingData } = await query.limit(1000)

  if (!rankingData || rankingData.length === 0) {
    return alerts
  }

  // Group by keyword and analyze changes
  const keywordGroups = new Map<string, any[]>()
  
  for (const ranking of rankingData) {
    const key = ranking.keyword
    if (!keywordGroups.has(key)) {
      keywordGroups.set(key, [])
    }
    keywordGroups.get(key)!.push(ranking)
  }

  // Analyze each keyword for significant changes
  for (const [keyword, rankings] of keywordGroups) {
    if (rankings.length < 2) continue

    const latest = rankings[0]
    const previous = rankings[1]
    
    const positionChange = latest.position - previous.position
    
    // Check for significant ranking drops
    const dropThreshold = getAlertThreshold(alertConfigs, 'ranking_drop', 5)
    
    if (positionChange >= dropThreshold) {
      alerts.push({
        alert_type: 'ranking_drop',
        severity: positionChange >= 10 ? 'high' : positionChange >= 7 ? 'medium' : 'low',
        title: `Ranking Drop: ${keyword}`,
        message: `Keyword "${keyword}" dropped ${positionChange} positions from ${previous.position} to ${latest.position}`,
        trigger_data: {
          keyword,
          previous_position: previous.position,
          current_position: latest.position,
          url: latest.url,
          search_engine: latest.search_engine
        },
        current_value: latest.position,
        previous_value: previous.position,
        percentage_change: previous.position > 0 ? 
          Math.round(((latest.position - previous.position) / previous.position) * 100) : 0
      })
    }

    // Check for significant ranking improvements
    if (positionChange <= -5) {
      alerts.push({
        alert_type: 'ranking_improvement',
        severity: 'low',
        title: `Ranking Improvement: ${keyword}`,
        message: `Keyword "${keyword}" improved ${Math.abs(positionChange)} positions from ${previous.position} to ${latest.position}`,
        trigger_data: {
          keyword,
          previous_position: previous.position,
          current_position: latest.position,
          url: latest.url,
          improvement: Math.abs(positionChange)
        },
        current_value: latest.position,
        previous_value: previous.position,
        percentage_change: previous.position > 0 ? 
          Math.round(((latest.position - previous.position) / previous.position) * 100) : 0
      })
    }
  }

  return alerts
}

async function checkTrafficChanges(supabase: any, business: any, campaign_id?: string, alertConfigs?: any[]): Promise<AlertTrigger[]> {
  const alerts: AlertTrigger[] = []
  
  // Get content performance data for the last 7 days
  const weekAgo = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString()
  
  let query = supabase
    .from('content_performance')
    .select('*')
    .eq('business_id', business.id)
    .gte('analysis_date', weekAgo)
    .order('analysis_date', { ascending: false })

  if (campaign_id) {
    query = query.eq('campaign_id', campaign_id)
  }

  const { data: performanceData } = await query.limit(500)

  if (!performanceData || performanceData.length < 2) {
    return alerts
  }

  // Group by URL and analyze traffic changes
  const urlGroups = new Map<string, any[]>()
  
  for (const performance of performanceData) {
    const key = performance.url
    if (!urlGroups.has(key)) {
      urlGroups.set(key, [])
    }
    urlGroups.get(key)!.push(performance)
  }

  // Analyze traffic changes for each URL
  for (const [url, performances] of urlGroups) {
    if (performances.length < 2) continue

    const latest = performances[0]
    const previous = performances[1]
    
    const trafficChange = ((latest.organic_traffic - previous.organic_traffic) / previous.organic_traffic) * 100
    
    // Check for significant traffic drops
    const dropThreshold = getAlertThreshold(alertConfigs, 'traffic_drop', -30)
    
    if (trafficChange <= dropThreshold) {
      alerts.push({
        alert_type: 'traffic_drop',
        severity: trafficChange <= -50 ? 'critical' : trafficChange <= -40 ? 'high' : 'medium',
        title: `Traffic Drop: ${latest.title || url}`,
        message: `Page "${latest.title || url}" experienced a ${Math.abs(trafficChange).toFixed(1)}% traffic drop (${previous.organic_traffic} → ${latest.organic_traffic})`,
        trigger_data: {
          url,
          title: latest.title,
          previous_traffic: previous.organic_traffic,
          current_traffic: latest.organic_traffic,
          analysis_dates: {
            previous: previous.analysis_date,
            current: latest.analysis_date
          }
        },
        current_value: latest.organic_traffic,
        previous_value: previous.organic_traffic,
        percentage_change: trafficChange
      })
    }

    // Check for significant traffic spikes
    const spikeThreshold = getAlertThreshold(alertConfigs, 'traffic_spike', 50)
    
    if (trafficChange >= spikeThreshold) {
      alerts.push({
        alert_type: 'traffic_spike',
        severity: 'low',
        title: `Traffic Spike: ${latest.title || url}`,
        message: `Page "${latest.title || url}" experienced a ${trafficChange.toFixed(1)}% traffic increase (${previous.organic_traffic} → ${latest.organic_traffic})`,
        trigger_data: {
          url,
          title: latest.title,
          previous_traffic: previous.organic_traffic,
          current_traffic: latest.organic_traffic,
          spike_percentage: trafficChange
        },
        current_value: latest.organic_traffic,
        previous_value: previous.organic_traffic,
        percentage_change: trafficChange
      })
    }
  }

  return alerts
}

async function checkCompetitorActivity(supabase: any, business: any, campaign_id?: string, alertConfigs?: any[]): Promise<AlertTrigger[]> {
  const alerts: AlertTrigger[] = []
  
  // Get recent competitor analysis data
  const { data: competitorData } = await supabase
    .from('competitor_analysis')
    .select('*')
    .eq('business_id', business.id)
    .gte('analysis_date', new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString())
    .order('analysis_date', { ascending: false })
    .limit(50)

  if (!competitorData || competitorData.length === 0) {
    return alerts
  }

  // Analyze competitor changes
  for (const analysis of competitorData) {
    if (!analysis.competitive_gaps) continue

    const gaps = analysis.competitive_gaps
    const highPriorityGaps = gaps.filter((gap: any) => gap.difficulty === 'low' && gap.type === 'keyword')

    if (highPriorityGaps.length > 3) {
      alerts.push({
        alert_type: 'new_opportunities',
        severity: 'medium',
        title: 'New Competitive Opportunities Detected',
        message: `${highPriorityGaps.length} new low-difficulty opportunities identified in competitor analysis`,
        trigger_data: {
          opportunities: highPriorityGaps.slice(0, 5),
          analysis_date: analysis.analysis_date,
          competitors_analyzed: analysis.competitors_analyzed
        },
        current_value: highPriorityGaps.length,
        previous_value: 0
      })
    }
  }

  return alerts
}

async function checkTechnicalIssues(supabase: any, business: any, campaign_id?: string, alertConfigs?: any[]): Promise<AlertTrigger[]> {
  const alerts: AlertTrigger[] = []
  
  // Get recent technical audit data
  const { data: auditData } = await supabase
    .from('technical_audits')
    .select('*')
    .eq('business_id', business.id)
    .gte('audit_date', new Date(Date.now() - 3 * 24 * 60 * 60 * 1000).toISOString())
    .order('audit_date', { ascending: false })
    .limit(10)

  if (!auditData || auditData.length < 2) {
    return alerts
  }

  const latest = auditData[0]
  const previous = auditData[1]

  // Check for performance score drops
  if (latest.performance_score < previous.performance_score - 10) {
    alerts.push({
      alert_type: 'performance_drop',
      severity: latest.performance_score < 50 ? 'high' : 'medium',
      title: 'Site Performance Declined',
      message: `Performance score dropped from ${previous.performance_score} to ${latest.performance_score}`,
      trigger_data: {
        previous_score: previous.performance_score,
        current_score: latest.performance_score,
        audit_url: latest.urls_audited?.[0],
        core_web_vitals: latest.avg_lcp
      },
      current_value: latest.performance_score,
      previous_value: previous.performance_score,
      percentage_change: ((latest.performance_score - previous.performance_score) / previous.performance_score) * 100
    })
  }

  // Check for new critical issues
  if (latest.critical_issues > previous.critical_issues) {
    alerts.push({
      alert_type: 'new_critical_issues',
      severity: 'high',
      title: 'New Critical Technical Issues',
      message: `${latest.critical_issues - previous.critical_issues} new critical issues detected`,
      trigger_data: {
        previous_critical: previous.critical_issues,
        current_critical: latest.critical_issues,
        new_issues: latest.critical_issues - previous.critical_issues,
        audit_date: latest.audit_date
      },
      current_value: latest.critical_issues,
      previous_value: previous.critical_issues
    })
  }

  return alerts
}

async function handleAlertConfiguration(supabase: any, business_id: string, alert_config?: AlertConfiguration) {
  if (!alert_config) {
    return new Response(
      JSON.stringify({ error: 'alert_config is required' }),
      { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }

  const { data: config, error } = await supabase
    .from('alert_configurations')
    .upsert({
      business_id,
      alert_type: alert_config.alert_type,
      thresholds: alert_config.thresholds,
      frequency: alert_config.frequency,
      severity_rules: alert_config.severity_rules,
      notification_channels: alert_config.notification_channels,
      is_active: true,
      updated_at: new Date().toISOString()
    }, {
      onConflict: 'business_id,alert_type'
    })
    .select()
    .single()

  if (error) {
    return new Response(
      JSON.stringify({ error: 'Failed to configure alerts', details: error.message }),
      { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }

  return new Response(
    JSON.stringify({
      success: true,
      message: 'Alert configuration updated',
      config_id: config.id
    }),
    { 
      status: 200, 
      headers: { ...corsHeaders, 'Content-Type': 'application/json' } 
    }
  )
}

async function handleAcknowledgeAlert(supabase: any, business_id: string, alert_id?: string) {
  if (!alert_id) {
    return new Response(
      JSON.stringify({ error: 'alert_id is required' }),
      { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }

  const { data: alert, error } = await supabase
    .from('monitoring_alerts')
    .update({
      status: 'acknowledged',
      acknowledged_at: new Date().toISOString(),
      acknowledged_by: 'user',
      updated_at: new Date().toISOString()
    })
    .eq('id', alert_id)
    .eq('business_id', business_id)
    .select()
    .single()

  if (error || !alert) {
    return new Response(
      JSON.stringify({ error: 'Alert not found or could not be acknowledged' }),
      { status: 404, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }

  return new Response(
    JSON.stringify({
      success: true,
      message: 'Alert acknowledged',
      alert_id: alert.id
    }),
    { 
      status: 200, 
      headers: { ...corsHeaders, 'Content-Type': 'application/json' } 
    }
  )
}

async function handleResolveAlert(supabase: any, business_id: string, alert_id?: string) {
  if (!alert_id) {
    return new Response(
      JSON.stringify({ error: 'alert_id is required' }),
      { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }

  const { data: alert, error } = await supabase
    .from('monitoring_alerts')
    .update({
      status: 'resolved',
      resolved_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    })
    .eq('id', alert_id)
    .eq('business_id', business_id)
    .select()
    .single()

  if (error || !alert) {
    return new Response(
      JSON.stringify({ error: 'Alert not found or could not be resolved' }),
      { status: 404, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }

  return new Response(
    JSON.stringify({
      success: true,
      message: 'Alert resolved',
      alert_id: alert.id
    }),
    { 
      status: 200, 
      headers: { ...corsHeaders, 'Content-Type': 'application/json' } 
    }
  )
}

async function handleListAlerts(supabase: any, business_id: string, campaign_id?: string) {
  let query = supabase
    .from('monitoring_alerts')
    .select('*')
    .eq('business_id', business_id)

  if (campaign_id) {
    query = query.eq('campaign_id', campaign_id)
  }

  const { data: alerts } = await query
    .order('created_at', { ascending: false })
    .limit(100)

  const summary = {
    total_alerts: alerts?.length || 0,
    active: alerts?.filter(a => a.status === 'active').length || 0,
    acknowledged: alerts?.filter(a => a.status === 'acknowledged').length || 0,
    resolved: alerts?.filter(a => a.status === 'resolved').length || 0,
    critical: alerts?.filter(a => a.severity === 'critical').length || 0,
    high: alerts?.filter(a => a.severity === 'high').length || 0
  }

  return new Response(
    JSON.stringify({
      success: true,
      summary,
      alerts: alerts || []
    }),
    { 
      status: 200, 
      headers: { ...corsHeaders, 'Content-Type': 'application/json' } 
    }
  )
}

async function createDefaultAlertConfig(supabase: any, business_id: string) {
  const defaultConfigs = [
    {
      business_id,
      alert_type: 'ranking_drop',
      thresholds: { ranking_drop: 5 },
      frequency: 'daily',
      severity_rules: { high_threshold: 10, critical_threshold: 15 },
      notification_channels: ['email'],
      is_active: true
    },
    {
      business_id,
      alert_type: 'traffic_drop',
      thresholds: { traffic_drop: -30 },
      frequency: 'daily',
      severity_rules: { high_threshold: -40, critical_threshold: -50 },
      notification_channels: ['email'],
      is_active: true
    },
    {
      business_id,
      alert_type: 'technical_issues',
      thresholds: { technical_score_drop: -10 },
      frequency: 'daily',
      severity_rules: { high_threshold: -20, critical_threshold: -30 },
      notification_channels: ['email'],
      is_active: true
    }
  ]

  await supabase
    .from('alert_configurations')
    .insert(defaultConfigs)
}

function getAlertThreshold(alertConfigs: any[], alertType: string, defaultValue: number): number {
  if (!alertConfigs) return defaultValue
  
  const config = alertConfigs.find(c => c.alert_type === alertType.split('_')[0])
  if (!config?.thresholds) return defaultValue
  
  return config.thresholds[alertType] || defaultValue
}

async function sendAlertNotifications(supabase: any, alert: any, alertConfigs: any[]) {
  // This would integrate with notification services
  // For now, just log the notification
  console.log(`Alert notification: ${alert.title} - ${alert.message}`)
  
  // In a real implementation:
  // - Send emails via SendGrid/AWS SES
  // - Send Slack/Discord webhooks
  // - Send SMS via Twilio
  // - Push to mobile apps
}