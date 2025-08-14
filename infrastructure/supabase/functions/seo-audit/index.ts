import { serve } from 'https://deno.land/std@0.168.0/http/server.ts'
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'
import { corsHeaders } from '../_shared/cors.ts'

interface TechnicalAuditRequest {
  business_id: string
  urls?: string[]
  audit_type?: 'full_site' | 'page_sample' | 'specific_urls'
  max_pages?: number
}

interface AuditIssue {
  type: 'critical' | 'warning' | 'info'
  category: 'performance' | 'seo' | 'accessibility' | 'best_practices'
  title: string
  description: string
  affected_urls: string[]
  fix_priority: number
  estimated_impact: string
}

interface AuditResult {
  performance_score: number
  accessibility_score: number
  best_practices_score: number
  seo_score: number
  core_web_vitals: {
    lcp: number
    inp: number
    cls: number
    fcp: number
    ttfb: number
  }
  issues: AuditIssue[]
  recommendations: any[]
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

    const { business_id, urls = [], audit_type = 'page_sample', max_pages = 10 }: TechnicalAuditRequest = await req.json()

    // Validate input
    if (!business_id) {
      return new Response(
        JSON.stringify({ error: 'business_id is required' }),
        { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    // Get business details
    const { data: business } = await supabase
      .from('businesses')
      .select('business_name, website_url, industry')
      .eq('id', business_id)
      .single()

    if (!business) {
      return new Response(
        JSON.stringify({ error: 'Business not found' }),
        { status: 404, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    // Determine URLs to audit
    let urlsToAudit: string[] = []
    
    if (audit_type === 'specific_urls' && urls.length > 0) {
      urlsToAudit = urls
    } else if (business.website_url) {
      urlsToAudit = [business.website_url]
      
      // Add common pages for full site audit
      if (audit_type === 'full_site') {
        const commonPages = [
          '/about', '/services', '/contact', '/blog',
          '/pricing', '/portfolio', '/testimonials'
        ]
        
        for (const page of commonPages) {
          urlsToAudit.push(new URL(page, business.website_url).toString())
        }
      }
    } else {
      return new Response(
        JSON.stringify({ error: 'No website URL found for business' }),
        { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    // Limit URLs
    urlsToAudit = urlsToAudit.slice(0, max_pages)

    // Run audit simulation (in real implementation, this would use Lighthouse/PageSpeed API)
    const auditResult = await simulateTechnicalAudit(urlsToAudit, business)

    // Store audit results
    const { data: auditRecord } = await supabase
      .from('technical_audits')
      .insert({
        business_id,
        audit_type,
        urls_audited: urlsToAudit,
        performance_score: auditResult.performance_score,
        accessibility_score: auditResult.accessibility_score,
        best_practices_score: auditResult.best_practices_score,
        seo_score: auditResult.seo_score,
        avg_lcp: auditResult.core_web_vitals.lcp,
        avg_inp: auditResult.core_web_vitals.inp,
        avg_cls: auditResult.core_web_vitals.cls,
        avg_fcp: auditResult.core_web_vitals.fcp,
        avg_ttfb: auditResult.core_web_vitals.ttfb,
        issues_found: auditResult.issues,
        critical_issues: auditResult.issues.filter(i => i.type === 'critical').length,
        warning_issues: auditResult.issues.filter(i => i.type === 'warning').length,
        info_issues: auditResult.issues.filter(i => i.type === 'info').length,
        recommendations: auditResult.recommendations,
        audit_tool: 'custom_simulation',
        pages_analyzed: urlsToAudit.length,
        status: 'completed'
      })
      .select()
      .single()

    // Log the audit
    await supabase
      .from('seo_logs')
      .insert({
        business_id,
        action_type: 'technical_audit',
        action_description: `Technical audit completed for ${urlsToAudit.length} URLs`,
        new_data: JSON.stringify({
          audit_id: auditRecord?.id,
          performance_score: auditResult.performance_score,
          issues_found: auditResult.issues.length
        })
      })

    return new Response(
      JSON.stringify({
        success: true,
        audit_id: auditRecord?.id,
        urls_audited: urlsToAudit.length,
        performance_score: auditResult.performance_score,
        accessibility_score: auditResult.accessibility_score,
        best_practices_score: auditResult.best_practices_score,
        seo_score: auditResult.seo_score,
        core_web_vitals: auditResult.core_web_vitals,
        issues_summary: {
          critical: auditResult.issues.filter(i => i.type === 'critical').length,
          warning: auditResult.issues.filter(i => i.type === 'warning').length,
          info: auditResult.issues.filter(i => i.type === 'info').length
        },
        issues: auditResult.issues,
        recommendations: auditResult.recommendations
      }),
      { 
        status: 200, 
        headers: { ...corsHeaders, 'Content-Type': 'application/json' } 
      }
    )

  } catch (error) {
    console.error('Technical audit error:', error)
    return new Response(
      JSON.stringify({ error: 'Internal server error', details: error.message }),
      { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }
})

// Simulate technical audit (replace with real Lighthouse/PageSpeed API calls)
async function simulateTechnicalAudit(urls: string[], business: any): Promise<AuditResult> {
  // Simulate performance scores with some realistic variance
  const basePerformance = 70 + Math.random() * 25
  const baseAccessibility = 80 + Math.random() * 15
  const baseBestPractices = 75 + Math.random() * 20
  const baseSEO = 65 + Math.random() * 30

  // Simulate Core Web Vitals
  const coreWebVitals = {
    lcp: 1800 + Math.random() * 2000, // 1.8-3.8s
    inp: 150 + Math.random() * 200,   // 150-350ms
    cls: 0.05 + Math.random() * 0.15, // 0.05-0.2
    fcp: 1200 + Math.random() * 1000, // 1.2-2.2s
    ttfb: 400 + Math.random() * 800    // 400-1200ms
  }

  // Generate realistic issues
  const issues: AuditIssue[] = []

  // Performance issues
  if (basePerformance < 80) {
    issues.push({
      type: 'warning',
      category: 'performance',
      title: 'Optimize images',
      description: 'Images are not optimized for web delivery. Consider using WebP format and proper sizing.',
      affected_urls: urls.slice(0, Math.ceil(urls.length * 0.7)),
      fix_priority: 8,
      estimated_impact: 'Could improve load time by 20-30%'
    })
  }

  if (coreWebVitals.lcp > 2500) {
    issues.push({
      type: 'critical',
      category: 'performance', 
      title: 'Poor Largest Contentful Paint (LCP)',
      description: 'LCP is above 2.5 seconds. Optimize critical rendering path and reduce server response times.',
      affected_urls: urls,
      fix_priority: 10,
      estimated_impact: 'Critical for Core Web Vitals score'
    })
  }

  // SEO issues
  if (baseSEO < 75) {
    issues.push({
      type: 'warning',
      category: 'seo',
      title: 'Missing meta descriptions',
      description: 'Several pages are missing meta descriptions or have descriptions that are too short.',
      affected_urls: urls.slice(0, Math.ceil(urls.length * 0.4)),
      fix_priority: 7,
      estimated_impact: 'May improve click-through rates from search results'
    })

    issues.push({
      type: 'info',
      category: 'seo',
      title: 'Heading structure',
      description: 'Some pages have heading structure issues (missing H1 or skipping heading levels).',
      affected_urls: urls.slice(0, 2),
      fix_priority: 5,
      estimated_impact: 'Improves content accessibility and SEO'
    })
  }

  // Accessibility issues
  if (baseAccessibility < 85) {
    issues.push({
      type: 'warning',
      category: 'accessibility',
      title: 'Missing alt text for images',
      description: 'Some images are missing alternative text for screen readers.',
      affected_urls: urls.slice(0, Math.ceil(urls.length * 0.5)),
      fix_priority: 6,
      estimated_impact: 'Improves accessibility for visually impaired users'
    })
  }

  // Best practices issues
  if (baseBestPractices < 80) {
    issues.push({
      type: 'info',
      category: 'best_practices',
      title: 'HTTPS usage',
      description: 'Ensure all resources are loaded over HTTPS for security.',
      affected_urls: urls.slice(0, 1),
      fix_priority: 4,
      estimated_impact: 'Improves security and user trust'
    })
  }

  // Generate recommendations
  const recommendations = [
    {
      title: 'Enable compression',
      description: 'Enable gzip or brotli compression to reduce file sizes',
      priority: 'high',
      effort: 'low'
    },
    {
      title: 'Minimize JavaScript',
      description: 'Remove unused JavaScript and minimize remaining files',
      priority: 'medium', 
      effort: 'medium'
    },
    {
      title: 'Implement caching',
      description: 'Set appropriate cache headers for static resources',
      priority: 'high',
      effort: 'low'
    }
  ]

  return {
    performance_score: Math.round(basePerformance),
    accessibility_score: Math.round(baseAccessibility),
    best_practices_score: Math.round(baseBestPractices),
    seo_score: Math.round(baseSEO),
    core_web_vitals: {
      lcp: Math.round(coreWebVitals.lcp),
      inp: Math.round(coreWebVitals.inp),
      cls: Math.round(coreWebVitals.cls * 1000) / 1000,
      fcp: Math.round(coreWebVitals.fcp),
      ttfb: Math.round(coreWebVitals.ttfb)
    },
    issues,
    recommendations
  }
}