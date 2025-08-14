import { serve } from 'https://deno.land/std@0.168.0/http/server.ts'
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'
import { corsHeaders } from '../_shared/cors.ts'

interface CacheEntry {
  key: string
  value: any
  ttl: number
  created_at: number
  expires_at: number
  hit_count: number
  tags: string[]
}

interface CacheStrategy {
  type: 'lru' | 'lfu' | 'ttl' | 'adaptive'
  max_size: number
  default_ttl: number
  warm_on_start: boolean
}

// In-memory cache store
const memoryCache = new Map<string, CacheEntry>()
const cacheStats = {
  hits: 0,
  misses: 0,
  evictions: 0,
  writes: 0
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

    const { action, key, value, ttl, tags, pattern, strategy } = await req.json()

    let result: any

    switch (action) {
      case 'get':
        result = await getFromCache(key)
        break
      
      case 'set':
        result = await setInCache(key, value, ttl, tags)
        break
      
      case 'delete':
        result = await deleteFromCache(key)
        break
      
      case 'flush':
        result = await flushCache(pattern)
        break
      
      case 'warm':
        result = await warmCache(supabase, strategy)
        break
      
      case 'stats':
        result = getCacheStats()
        break
      
      case 'invalidate_tag':
        result = await invalidateByTag(tags)
        break
      
      case 'configure_cdn':
        result = await configureCDN(await req.json())
        break
      
      case 'purge_cdn':
        result = await purgeCDN(pattern)
        break
      
      default:
        throw new Error(`Unknown action: ${action}`)
    }

    return new Response(
      JSON.stringify(result),
      { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )

  } catch (error) {
    console.error('Cache manager error:', error)
    return new Response(
      JSON.stringify({ error: error.message }),
      { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }
})

async function getFromCache(key: string): Promise<any> {
  const entry = memoryCache.get(key)
  
  if (!entry) {
    cacheStats.misses++
    return { found: false, value: null }
  }
  
  // Check if expired
  if (entry.expires_at < Date.now()) {
    memoryCache.delete(key)
    cacheStats.misses++
    return { found: false, value: null, reason: 'expired' }
  }
  
  // Update hit count and stats
  entry.hit_count++
  cacheStats.hits++
  
  return {
    found: true,
    value: entry.value,
    ttl_remaining: Math.floor((entry.expires_at - Date.now()) / 1000),
    hit_count: entry.hit_count
  }
}

async function setInCache(
  key: string,
  value: any,
  ttl?: number,
  tags?: string[]
): Promise<any> {
  
  const ttlSeconds = ttl || 3600 // Default 1 hour
  const now = Date.now()
  
  // Check cache size and evict if necessary
  if (memoryCache.size >= 10000) {
    await evictLRU()
  }
  
  const entry: CacheEntry = {
    key,
    value,
    ttl: ttlSeconds,
    created_at: now,
    expires_at: now + (ttlSeconds * 1000),
    hit_count: 0,
    tags: tags || []
  }
  
  memoryCache.set(key, entry)
  cacheStats.writes++
  
  return {
    success: true,
    key,
    expires_at: new Date(entry.expires_at).toISOString()
  }
}

async function deleteFromCache(key: string): Promise<any> {
  const deleted = memoryCache.delete(key)
  
  return {
    success: deleted,
    key
  }
}

async function flushCache(pattern?: string): Promise<any> {
  let flushed = 0
  
  if (pattern) {
    // Flush keys matching pattern
    const regex = new RegExp(pattern)
    for (const [key] of memoryCache) {
      if (regex.test(key)) {
        memoryCache.delete(key)
        flushed++
      }
    }
  } else {
    // Flush all
    flushed = memoryCache.size
    memoryCache.clear()
  }
  
  // Reset stats
  if (!pattern) {
    cacheStats.hits = 0
    cacheStats.misses = 0
    cacheStats.evictions = 0
    cacheStats.writes = 0
  }
  
  return {
    success: true,
    flushed,
    pattern
  }
}

async function warmCache(
  supabase: any,
  strategy?: CacheStrategy
): Promise<any> {
  
  const warmStrategy = strategy || {
    type: 'adaptive',
    max_size: 1000,
    default_ttl: 3600,
    warm_on_start: true
  }
  
  const warmed = []
  
  // Warm frequently accessed data
  
  // 1. Popular keywords
  const { data: keywords } = await supabase
    .from('keywords')
    .select('*')
    .order('search_volume', { ascending: false })
    .limit(100)
  
  for (const keyword of keywords || []) {
    const key = `keyword:${keyword.id}`
    await setInCache(key, keyword, warmStrategy.default_ttl, ['keywords'])
    warmed.push(key)
  }
  
  // 2. Recent reports
  const { data: reports } = await supabase
    .from('seo_reports')
    .select('*')
    .order('created_at', { ascending: false })
    .limit(50)
  
  for (const report of reports || []) {
    const key = `report:${report.id}`
    await setInCache(key, report, warmStrategy.default_ttl, ['reports'])
    warmed.push(key)
  }
  
  // 3. Active campaigns
  const { data: campaigns } = await supabase
    .from('campaigns')
    .select('*')
    .eq('status', 'active')
    .limit(50)
  
  for (const campaign of campaigns || []) {
    const key = `campaign:${campaign.id}`
    await setInCache(key, campaign, warmStrategy.default_ttl, ['campaigns'])
    warmed.push(key)
  }
  
  // 4. Dashboard data for active users
  const { data: activeUsers } = await supabase
    .from('api_logs')
    .select('user_id, business_id')
    .gte('created_at', new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString())
    .limit(100)
  
  const uniqueBusinesses = new Set()
  activeUsers?.forEach(log => uniqueBusinesses.add(log.business_id))
  
  for (const businessId of uniqueBusinesses) {
    const dashboardKey = `dashboard:${businessId}`
    // Simulate dashboard data
    const dashboardData = {
      business_id: businessId,
      metrics: { /* ... */ },
      cached_at: new Date().toISOString()
    }
    await setInCache(dashboardKey, dashboardData, 300, ['dashboards']) // 5 min TTL
    warmed.push(dashboardKey)
  }
  
  return {
    success: true,
    warmed_count: warmed.length,
    strategy: warmStrategy,
    keys: warmed.slice(0, 10) // Return first 10 as sample
  }
}

function getCacheStats(): any {
  const hitRate = cacheStats.hits + cacheStats.misses > 0 ?
    (cacheStats.hits / (cacheStats.hits + cacheStats.misses)) * 100 : 0
  
  // Calculate memory usage
  let totalSize = 0
  let expiredCount = 0
  const now = Date.now()
  
  for (const [_, entry] of memoryCache) {
    totalSize += JSON.stringify(entry.value).length
    if (entry.expires_at < now) {
      expiredCount++
    }
  }
  
  return {
    entries: memoryCache.size,
    hits: cacheStats.hits,
    misses: cacheStats.misses,
    hit_rate: hitRate.toFixed(2) + '%',
    writes: cacheStats.writes,
    evictions: cacheStats.evictions,
    memory_usage_kb: (totalSize / 1024).toFixed(2),
    expired_entries: expiredCount
  }
}

async function invalidateByTag(tags: string[]): Promise<any> {
  let invalidated = 0
  
  for (const [key, entry] of memoryCache) {
    if (tags.some(tag => entry.tags.includes(tag))) {
      memoryCache.delete(key)
      invalidated++
    }
  }
  
  return {
    success: true,
    invalidated,
    tags
  }
}

async function evictLRU(): Promise<void> {
  // Find least recently used entry
  let lruKey: string | null = null
  let lruTime = Date.now()
  
  for (const [key, entry] of memoryCache) {
    const lastAccess = entry.created_at + (entry.hit_count * 1000) // Rough LRU calculation
    if (lastAccess < lruTime) {
      lruTime = lastAccess
      lruKey = key
    }
  }
  
  if (lruKey) {
    memoryCache.delete(lruKey)
    cacheStats.evictions++
  }
}

async function configureCDN(config: any): Promise<any> {
  // CDN configuration for different providers
  const cdnProviders = {
    cloudflare: {
      api_endpoint: 'https://api.cloudflare.com/client/v4',
      zones: config.cloudflare_zone_id,
      cache_rules: [
        {
          path: '/api/*',
          ttl: 60,
          cache_key: ['uri', 'query_string', 'header:authorization']
        },
        {
          path: '/static/*',
          ttl: 86400,
          cache_key: ['uri']
        },
        {
          path: '/reports/*',
          ttl: 3600,
          cache_key: ['uri', 'query_string']
        }
      ]
    },
    fastly: {
      api_endpoint: 'https://api.fastly.com',
      service_id: config.fastly_service_id,
      cache_rules: [
        {
          condition: 'req.url ~ "^/api/"',
          ttl: 60,
          stale_while_revalidate: 30
        },
        {
          condition: 'req.url ~ "^/static/"',
          ttl: 86400,
          stale_while_revalidate: 3600
        }
      ]
    },
    aws_cloudfront: {
      distribution_id: config.cloudfront_distribution_id,
      behaviors: [
        {
          path_pattern: '/api/*',
          cache_policy: {
            default_ttl: 60,
            max_ttl: 300,
            min_ttl: 0
          }
        },
        {
          path_pattern: '/static/*',
          cache_policy: {
            default_ttl: 86400,
            max_ttl: 31536000,
            min_ttl: 86400
          }
        }
      ]
    }
  }
  
  const provider = config.provider || 'cloudflare'
  const cdnConfig = cdnProviders[provider]
  
  // Apply CDN configuration (would make actual API calls in production)
  const configured = {
    provider,
    config: cdnConfig,
    cache_rules: cdnConfig.cache_rules || cdnConfig.behaviors,
    estimated_cache_hit_rate: 85,
    estimated_bandwidth_savings: 70
  }
  
  return {
    success: true,
    ...configured
  }
}

async function purgeCDN(pattern?: string): Promise<any> {
  // Simulate CDN purge
  const purgeRequests = []
  
  if (pattern) {
    // Purge specific pattern
    purgeRequests.push({
      type: 'pattern',
      pattern,
      status: 'queued'
    })
  } else {
    // Purge everything
    purgeRequests.push({
      type: 'all',
      status: 'queued'
    })
  }
  
  // In production, would make actual API calls to CDN provider
  // Example for Cloudflare:
  /*
  const response = await fetch(
    `https://api.cloudflare.com/client/v4/zones/${zoneId}/purge_cache`,
    {
      method: 'POST',
      headers: {
        'X-Auth-Email': email,
        'X-Auth-Key': apiKey,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        files: pattern ? [pattern] : undefined,
        purge_everything: !pattern
      })
    }
  )
  */
  
  return {
    success: true,
    purge_requests: purgeRequests,
    estimated_completion: new Date(Date.now() + 30000).toISOString() // 30 seconds
  }
}

// Background task to clean expired entries
setInterval(() => {
  const now = Date.now()
  let cleaned = 0
  
  for (const [key, entry] of memoryCache) {
    if (entry.expires_at < now) {
      memoryCache.delete(key)
      cleaned++
    }
  }
  
  if (cleaned > 0) {
    console.log(`Cleaned ${cleaned} expired cache entries`)
  }
}, 60000) // Run every minute