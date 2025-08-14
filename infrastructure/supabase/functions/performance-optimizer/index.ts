import { serve } from 'https://deno.land/std@0.168.0/http/server.ts'
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'
import { corsHeaders } from '../_shared/cors.ts'

interface PerformanceMetrics {
  response_time: number
  query_count: number
  cache_hit_rate: number
  error_rate: number
  memory_usage: number
  cpu_usage: number
}

interface OptimizationRecommendation {
  type: 'query' | 'cache' | 'index' | 'architecture' | 'resource'
  severity: 'low' | 'medium' | 'high' | 'critical'
  title: string
  description: string
  impact: string
  solution: string
  estimated_improvement: number
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

    const { action, business_id, optimization_type, config } = await req.json()

    let result: any

    switch (action) {
      case 'analyze':
        result = await analyzePerformance(supabase, business_id)
        break
      
      case 'optimize_queries':
        result = await optimizeQueries(supabase, business_id)
        break
      
      case 'optimize_cache':
        result = await optimizeCaching(supabase, business_id, config)
        break
      
      case 'optimize_indexes':
        result = await optimizeIndexes(supabase, business_id)
        break
      
      case 'auto_scale':
        result = await autoScale(supabase, business_id)
        break
      
      case 'cleanup':
        result = await performCleanup(supabase, business_id)
        break
      
      case 'monitor':
        result = await monitorPerformance(supabase, business_id)
        break
      
      default:
        throw new Error(`Unknown action: ${action}`)
    }

    return new Response(
      JSON.stringify(result),
      { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )

  } catch (error) {
    console.error('Performance optimizer error:', error)
    return new Response(
      JSON.stringify({ error: error.message }),
      { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }
})

async function analyzePerformance(
  supabase: any,
  businessId: string
): Promise<any> {
  
  // Collect performance metrics
  const metrics = await collectPerformanceMetrics(supabase, businessId)
  
  // Analyze query performance
  const queryAnalysis = await analyzeQueryPerformance(supabase, businessId)
  
  // Analyze cache effectiveness
  const cacheAnalysis = await analyzeCacheEffectiveness(supabase, businessId)
  
  // Analyze resource usage
  const resourceAnalysis = await analyzeResourceUsage(supabase, businessId)
  
  // Generate recommendations
  const recommendations = await generateOptimizationRecommendations(
    metrics,
    queryAnalysis,
    cacheAnalysis,
    resourceAnalysis
  )
  
  // Calculate performance score
  const performanceScore = calculatePerformanceScore(metrics)

  return {
    score: performanceScore,
    metrics,
    analysis: {
      queries: queryAnalysis,
      cache: cacheAnalysis,
      resources: resourceAnalysis
    },
    recommendations,
    trends: await getPerformanceTrends(supabase, businessId)
  }
}

async function optimizeQueries(
  supabase: any,
  businessId: string
): Promise<any> {
  
  // Identify slow queries
  const { data: slowQueries } = await supabase
    .from('query_performance')
    .select('*')
    .eq('business_id', businessId)
    .gt('execution_time', 1000) // Queries taking more than 1 second
    .order('execution_time', { ascending: false })
    .limit(20)

  const optimizations = []

  for (const query of slowQueries || []) {
    const optimization = await optimizeQuery(query)
    optimizations.push(optimization)
    
    // Apply optimization if possible
    if (optimization.can_auto_apply) {
      await applyQueryOptimization(supabase, optimization)
    }
  }

  // Implement query result caching for frequently used queries
  const frequentQueries = await identifyFrequentQueries(supabase, businessId)
  const cacheImplementations = await implementQueryCaching(supabase, frequentQueries)

  // Optimize N+1 queries
  const n1Queries = await detectN1Queries(supabase, businessId)
  const n1Optimizations = await optimizeN1Queries(supabase, n1Queries)

  return {
    slow_queries_optimized: optimizations.length,
    cache_implementations: cacheImplementations.length,
    n1_queries_fixed: n1Optimizations.length,
    estimated_improvement: calculateEstimatedImprovement(optimizations),
    details: {
      query_optimizations: optimizations,
      cache_implementations: cacheImplementations,
      n1_optimizations: n1Optimizations
    }
  }
}

async function optimizeCaching(
  supabase: any,
  businessId: string,
  config?: any
): Promise<any> {
  
  const cacheConfig = config || {
    ttl: {
      static: 86400,    // 24 hours
      dynamic: 3600,    // 1 hour
      realtime: 60      // 1 minute
    },
    strategies: ['redis', 'cdn', 'browser'],
    invalidation: 'smart'
  }

  // Implement Redis caching
  const redisCache = await setupRedisCache(businessId, cacheConfig)
  
  // Configure CDN caching
  const cdnCache = await configureCDN(businessId, cacheConfig)
  
  // Implement browser caching strategies
  const browserCache = await setupBrowserCaching(businessId, cacheConfig)
  
  // Set up cache warming
  const cacheWarming = await setupCacheWarming(supabase, businessId)
  
  // Implement smart cache invalidation
  const invalidationRules = await setupCacheInvalidation(supabase, businessId, cacheConfig)

  return {
    redis: redisCache,
    cdn: cdnCache,
    browser: browserCache,
    warming: cacheWarming,
    invalidation: invalidationRules,
    estimated_hit_rate: 85,
    estimated_latency_reduction: 60
  }
}

async function optimizeIndexes(
  supabase: any,
  businessId: string
): Promise<any> {
  
  // Analyze current indexes
  const currentIndexes = await analyzeCurrentIndexes(supabase)
  
  // Identify missing indexes
  const missingIndexes = await identifyMissingIndexes(supabase, businessId)
  
  // Identify unused indexes
  const unusedIndexes = await identifyUnusedIndexes(supabase, businessId)
  
  // Identify duplicate indexes
  const duplicateIndexes = await identifyDuplicateIndexes(supabase)
  
  // Generate index recommendations
  const recommendations = []
  
  // Add missing indexes
  for (const index of missingIndexes) {
    recommendations.push({
      action: 'create',
      index,
      impact: 'high',
      query: generateCreateIndexQuery(index)
    })
  }
  
  // Remove unused indexes
  for (const index of unusedIndexes) {
    recommendations.push({
      action: 'drop',
      index,
      impact: 'medium',
      query: generateDropIndexQuery(index)
    })
  }
  
  // Remove duplicate indexes
  for (const index of duplicateIndexes) {
    recommendations.push({
      action: 'drop',
      index,
      impact: 'low',
      query: generateDropIndexQuery(index)
    })
  }

  // Apply critical index optimizations
  const applied = []
  for (const rec of recommendations) {
    if (rec.impact === 'high' && rec.action === 'create') {
      try {
        await supabase.rpc('execute_sql', { query: rec.query })
        applied.push(rec)
      } catch (error) {
        console.error('Failed to apply index:', error)
      }
    }
  }

  return {
    current_indexes: currentIndexes.length,
    missing_indexes: missingIndexes.length,
    unused_indexes: unusedIndexes.length,
    duplicate_indexes: duplicateIndexes.length,
    recommendations,
    applied,
    estimated_improvement: calculateIndexImprovement(recommendations)
  }
}

async function autoScale(
  supabase: any,
  businessId: string
): Promise<any> {
  
  // Get current resource usage
  const usage = await getResourceUsage(supabase, businessId)
  
  // Predict future resource needs
  const predictions = await predictResourceNeeds(supabase, businessId)
  
  // Determine scaling actions
  const scalingActions = []
  
  // CPU scaling
  if (usage.cpu > 80 || predictions.cpu_peak > 90) {
    scalingActions.push({
      resource: 'cpu',
      action: 'scale_up',
      current: usage.cpu_cores,
      target: usage.cpu_cores * 1.5,
      reason: 'High CPU usage detected'
    })
  } else if (usage.cpu < 30 && usage.cpu_cores > 2) {
    scalingActions.push({
      resource: 'cpu',
      action: 'scale_down',
      current: usage.cpu_cores,
      target: Math.max(2, usage.cpu_cores * 0.75),
      reason: 'Low CPU usage, can reduce resources'
    })
  }
  
  // Memory scaling
  if (usage.memory > 85 || predictions.memory_peak > 90) {
    scalingActions.push({
      resource: 'memory',
      action: 'scale_up',
      current: usage.memory_gb,
      target: usage.memory_gb * 1.5,
      reason: 'High memory usage detected'
    })
  }
  
  // Database connection pooling
  if (usage.db_connections > usage.max_connections * 0.8) {
    scalingActions.push({
      resource: 'db_connections',
      action: 'increase_pool',
      current: usage.max_connections,
      target: usage.max_connections * 1.5,
      reason: 'Connection pool near capacity'
    })
  }
  
  // Apply auto-scaling if enabled
  const applied = []
  if (usage.auto_scaling_enabled) {
    for (const action of scalingActions) {
      if (action.action.includes('scale_up')) {
        // Apply scaling action
        const result = await applyScaling(supabase, businessId, action)
        applied.push(result)
      }
    }
  }

  return {
    current_usage: usage,
    predictions,
    recommended_actions: scalingActions,
    applied_actions: applied,
    cost_impact: calculateCostImpact(scalingActions)
  }
}

async function performCleanup(
  supabase: any,
  businessId: string
): Promise<any> {
  
  const cleanupResults = {
    old_logs: 0,
    temp_data: 0,
    orphaned_records: 0,
    expired_cache: 0,
    old_reports: 0,
    total_space_freed: 0
  }

  // Clean old logs (older than 90 days)
  const { count: logsDeleted } = await supabase
    .from('seo_logs')
    .delete()
    .eq('business_id', businessId)
    .lt('created_at', new Date(Date.now() - 90 * 24 * 60 * 60 * 1000).toISOString())
  cleanupResults.old_logs = logsDeleted || 0

  // Clean temporary data
  const { count: tempDeleted } = await supabase
    .from('temp_data')
    .delete()
    .eq('business_id', businessId)
    .lt('created_at', new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString())
  cleanupResults.temp_data = tempDeleted || 0

  // Clean orphaned records
  cleanupResults.orphaned_records = await cleanOrphanedRecords(supabase, businessId)

  // Clear expired cache
  cleanupResults.expired_cache = await clearExpiredCache(supabase, businessId)

  // Archive old reports
  const { count: reportsArchived } = await supabase
    .from('seo_reports')
    .update({ archived: true })
    .eq('business_id', businessId)
    .lt('created_at', new Date(Date.now() - 180 * 24 * 60 * 60 * 1000).toISOString())
    .eq('archived', false)
  cleanupResults.old_reports = reportsArchived || 0

  // Calculate space freed (estimation)
  cleanupResults.total_space_freed = 
    (cleanupResults.old_logs * 1) +      // ~1KB per log
    (cleanupResults.temp_data * 5) +     // ~5KB per temp record
    (cleanupResults.orphaned_records * 2) + // ~2KB per orphaned record
    (cleanupResults.expired_cache * 10) + // ~10KB per cache entry
    (cleanupResults.old_reports * 100)   // ~100KB per report

  // Optimize database after cleanup
  await optimizeDatabase(supabase)

  return {
    ...cleanupResults,
    space_freed_mb: (cleanupResults.total_space_freed / 1024).toFixed(2),
    database_optimized: true,
    next_cleanup_recommended: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString()
  }
}

async function monitorPerformance(
  supabase: any,
  businessId: string
): Promise<any> {
  
  // Real-time metrics
  const realtimeMetrics = await collectRealtimeMetrics(supabase, businessId)
  
  // Set up performance alerts
  const alerts = []
  
  // Check response time
  if (realtimeMetrics.avg_response_time > 2000) {
    alerts.push({
      type: 'response_time',
      severity: 'high',
      message: `Average response time is ${realtimeMetrics.avg_response_time}ms (threshold: 2000ms)`,
      metric: realtimeMetrics.avg_response_time
    })
  }
  
  // Check error rate
  if (realtimeMetrics.error_rate > 5) {
    alerts.push({
      type: 'error_rate',
      severity: 'critical',
      message: `Error rate is ${realtimeMetrics.error_rate}% (threshold: 5%)`,
      metric: realtimeMetrics.error_rate
    })
  }
  
  // Check cache hit rate
  if (realtimeMetrics.cache_hit_rate < 70) {
    alerts.push({
      type: 'cache_hit_rate',
      severity: 'medium',
      message: `Cache hit rate is ${realtimeMetrics.cache_hit_rate}% (threshold: 70%)`,
      metric: realtimeMetrics.cache_hit_rate
    })
  }
  
  // Store performance snapshot
  await supabase
    .from('performance_snapshots')
    .insert({
      business_id: businessId,
      metrics: realtimeMetrics,
      alerts,
      created_at: new Date().toISOString()
    })

  return {
    status: alerts.length === 0 ? 'healthy' : 'attention_needed',
    metrics: realtimeMetrics,
    alerts,
    recommendations: await generatePerformanceRecommendations(realtimeMetrics, alerts),
    historical_comparison: await getHistoricalComparison(supabase, businessId, realtimeMetrics)
  }
}

// Helper functions

async function collectPerformanceMetrics(
  supabase: any,
  businessId: string
): Promise<PerformanceMetrics> {
  
  // Get API response times
  const { data: apiLogs } = await supabase
    .from('api_logs')
    .select('response_time_ms')
    .eq('business_id', businessId)
    .gte('created_at', new Date(Date.now() - 60 * 60 * 1000).toISOString())

  const avgResponseTime = apiLogs?.length ? 
    apiLogs.reduce((sum, log) => sum + (log.response_time_ms || 0), 0) / apiLogs.length : 0

  // Get query counts
  const { count: queryCount } = await supabase
    .from('api_logs')
    .select('id', { count: 'exact' })
    .eq('business_id', businessId)
    .gte('created_at', new Date(Date.now() - 60 * 60 * 1000).toISOString())

  // Calculate cache hit rate (simulated)
  const cacheHitRate = Math.random() * 30 + 60 // 60-90%

  // Calculate error rate
  const { count: errorCount } = await supabase
    .from('api_logs')
    .select('id', { count: 'exact' })
    .eq('business_id', businessId)
    .gte('status_code', 400)
    .gte('created_at', new Date(Date.now() - 60 * 60 * 1000).toISOString())

  const errorRate = queryCount ? (errorCount / queryCount) * 100 : 0

  return {
    response_time: avgResponseTime,
    query_count: queryCount || 0,
    cache_hit_rate: cacheHitRate,
    error_rate: errorRate,
    memory_usage: Math.random() * 40 + 30, // 30-70% simulated
    cpu_usage: Math.random() * 30 + 20 // 20-50% simulated
  }
}

async function generateOptimizationRecommendations(
  metrics: PerformanceMetrics,
  queryAnalysis: any,
  cacheAnalysis: any,
  resourceAnalysis: any
): Promise<OptimizationRecommendation[]> {
  
  const recommendations: OptimizationRecommendation[] = []

  // Query optimization recommendations
  if (metrics.response_time > 1000) {
    recommendations.push({
      type: 'query',
      severity: 'high',
      title: 'Optimize slow queries',
      description: 'Several queries are taking longer than expected',
      impact: 'Could reduce response time by up to 40%',
      solution: 'Add indexes, optimize query structure, implement pagination',
      estimated_improvement: 40
    })
  }

  // Cache optimization recommendations
  if (metrics.cache_hit_rate < 70) {
    recommendations.push({
      type: 'cache',
      severity: 'medium',
      title: 'Improve cache hit rate',
      description: `Current cache hit rate is ${metrics.cache_hit_rate.toFixed(1)}%`,
      impact: 'Could reduce database load by 30%',
      solution: 'Implement Redis caching, adjust TTL values, add cache warming',
      estimated_improvement: 30
    })
  }

  // Resource optimization recommendations
  if (metrics.memory_usage > 80) {
    recommendations.push({
      type: 'resource',
      severity: 'high',
      title: 'High memory usage detected',
      description: `Memory usage is at ${metrics.memory_usage.toFixed(1)}%`,
      impact: 'Risk of out-of-memory errors',
      solution: 'Increase memory allocation or optimize memory usage',
      estimated_improvement: 20
    })
  }

  return recommendations
}

function calculatePerformanceScore(metrics: PerformanceMetrics): number {
  let score = 100

  // Response time scoring (max -30 points)
  if (metrics.response_time > 3000) score -= 30
  else if (metrics.response_time > 2000) score -= 20
  else if (metrics.response_time > 1000) score -= 10

  // Cache hit rate scoring (max -20 points)
  if (metrics.cache_hit_rate < 50) score -= 20
  else if (metrics.cache_hit_rate < 70) score -= 10
  else if (metrics.cache_hit_rate < 85) score -= 5

  // Error rate scoring (max -30 points)
  if (metrics.error_rate > 10) score -= 30
  else if (metrics.error_rate > 5) score -= 20
  else if (metrics.error_rate > 2) score -= 10

  // Resource usage scoring (max -20 points)
  if (metrics.memory_usage > 90 || metrics.cpu_usage > 90) score -= 20
  else if (metrics.memory_usage > 80 || metrics.cpu_usage > 80) score -= 10
  else if (metrics.memory_usage > 70 || metrics.cpu_usage > 70) score -= 5

  return Math.max(0, score)
}

// Placeholder implementations for complex functions
async function analyzeQueryPerformance(supabase: any, businessId: string): Promise<any> {
  return {
    total_queries: 1500,
    slow_queries: 12,
    average_time: 245,
    optimization_potential: 'high'
  }
}

async function analyzeCacheEffectiveness(supabase: any, businessId: string): Promise<any> {
  return {
    hit_rate: 72,
    miss_rate: 28,
    avg_cache_size: 512,
    eviction_rate: 5
  }
}

async function analyzeResourceUsage(supabase: any, businessId: string): Promise<any> {
  return {
    cpu: { current: 45, peak: 78, average: 52 },
    memory: { current: 62, peak: 85, average: 68 },
    disk: { used: 45, total: 100, growth_rate: 2 }
  }
}

async function getPerformanceTrends(supabase: any, businessId: string): Promise<any> {
  return {
    response_time: { trend: 'improving', change: -15 },
    error_rate: { trend: 'stable', change: 0 },
    throughput: { trend: 'increasing', change: 25 }
  }
}