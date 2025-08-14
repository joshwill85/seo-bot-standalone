import { serve } from 'https://deno.land/std@0.208.0/http/server.ts'
import { createDatabaseClient, logSeoAction } from '../_shared/database.ts'
import { authenticateRequest, requireBusinessAccess } from '../_shared/auth.ts'
import { handleCors, createResponse, createErrorResponse } from '../_shared/cors.ts'
import { AppError } from '../_shared/types.ts'

// Pricing configuration (20% below market rates)
const PRICING_PLANS = {
  starter: {
    name: 'Starter Plan',
    monthly_price: 6400, // $64.00 in cents
    yearly_price: 68800, // $688.00 in cents (10 months price)
    features: [
      'Basic SEO Audit',
      'Keyword Research (50 keywords)',
      'Monthly Reporting',
      'Basic Local SEO',
      'Google My Business Optimization'
    ],
    limits: {
      reports_per_month: 5,
      keywords_per_research: 50,
      businesses: 1
    }
  },
  professional: {
    name: 'Professional Plan',
    monthly_price: 24000, // $240.00 in cents
    yearly_price: 259200, // $2,592.00 in cents (10.8 months price)
    features: [
      'Comprehensive SEO Audit',
      'Advanced Keyword Research (500 keywords)',
      'Weekly Reporting',
      'Local SEO + Citations',
      'Competitor Analysis',
      'Content Optimization',
      'Performance Monitoring',
      'Priority Support'
    ],
    limits: {
      reports_per_month: 20,
      keywords_per_research: 500,
      businesses: 3
    }
  },
  enterprise: {
    name: 'Enterprise Plan',
    monthly_price: 48000, // $480.00 in cents
    yearly_price: 518400, // $5,184.00 in cents (10.8 months price)
    features: [
      'Full SEO Suite',
      'Unlimited Keyword Research',
      'Daily Reporting',
      'Advanced Local SEO',
      'Multi-location Management',
      'White-label Reports',
      'API Access',
      'Dedicated Account Manager',
      'Custom Integrations'
    ],
    limits: {
      reports_per_month: 100,
      keywords_per_research: 'unlimited',
      businesses: 10
    }
  }
}

serve(async (req) => {
  const origin = req.headers.get('Origin')

  // Handle CORS
  if (req.method === 'OPTIONS') {
    return new Response(null, { status: 200, headers: handleCors(req) })
  }

  try {
    const url = new URL(req.url)
    const pathParts = url.pathname.split('/').filter(Boolean)
    const action = pathParts[pathParts.length - 1]

    switch (action) {
      case 'plans':
        return handleGetPlans(req, origin)
      case 'create-payment-intent':
        return await handleCreatePaymentIntent(req, origin)
      case 'webhook':
        return await handleStripeWebhook(req, origin)
      default:
        // Handle subscription operations
        if (url.pathname.includes('/subscription/')) {
          const businessId = pathParts[pathParts.length - 1]
          if (req.method === 'GET') {
            return await handleGetSubscription(req, Number(businessId), origin)
          } else if (req.method === 'POST' && url.pathname.includes('/cancel')) {
            return await handleCancelSubscription(req, Number(businessId), origin)
          }
        }
        return createErrorResponse('Not found', 404, origin)
    }
  } catch (error) {
    console.error('Payments function error:', error)
    
    if (error instanceof AppError) {
      return createErrorResponse(error.message, error.statusCode, origin, error.details)
    }
    
    return createErrorResponse('Internal server error', 500, origin)
  }
})

function handleGetPlans(req: Request, origin?: string) {
  if (req.method !== 'GET') {
    return createErrorResponse('Method not allowed', 405, origin)
  }

  return createResponse({
    plans: PRICING_PLANS,
    currency: 'USD',
    trial_days: 14,
  }, 200, origin)
}

async function handleCreatePaymentIntent(req: Request, origin?: string) {
  if (req.method !== 'POST') {
    return createErrorResponse('Method not allowed', 405, origin)
  }

  const context = await authenticateRequest(req)
  const data = await req.json()

  const { plan_tier, billing_cycle = 'monthly' } = data

  if (!plan_tier || !(plan_tier in PRICING_PLANS)) {
    return createErrorResponse('Invalid plan tier', 400, origin)
  }

  if (!['monthly', 'yearly'].includes(billing_cycle)) {
    return createErrorResponse('Invalid billing cycle', 400, origin)
  }

  const plan = PRICING_PLANS[plan_tier as keyof typeof PRICING_PLANS]
  const amount = billing_cycle === 'yearly' ? plan.yearly_price : plan.monthly_price

  // In a real implementation, you would create a Stripe PaymentIntent here
  // For now, we'll return a mock response
  return createResponse({
    client_secret: 'pi_mock_client_secret',
    amount,
    currency: 'usd',
    plan: {
      tier: plan_tier,
      name: plan.name,
      billing_cycle,
      features: plan.features,
    },
  }, 200, origin)
}

async function handleGetSubscription(req: Request, businessId: number, origin?: string) {
  const context = await authenticateRequest(req)
  await requireBusinessAccess(businessId, context)

  const supabase = createDatabaseClient()

  const { data: business, error } = await supabase
    .from('businesses')
    .select('*')
    .eq('id', businessId)
    .single()

  if (error || !business) {
    return createErrorResponse('Business not found', 404, origin)
  }

  const planDetails = PRICING_PLANS[business.plan_tier as keyof typeof PRICING_PLANS] || {}

  const subscriptionInfo = {
    business_id: business.id,
    plan_tier: business.plan_tier,
    billing_cycle: business.billing_cycle,
    subscription_status: business.subscription_status,
    trial_ends_at: business.trial_ends_at,
    plan_details: planDetails,
    is_trial: business.subscription_status === 'trial',
    is_active: ['active', 'trial'].includes(business.subscription_status),
  }

  return createResponse({
    subscription: subscriptionInfo,
  }, 200, origin)
}

async function handleCancelSubscription(req: Request, businessId: number, origin?: string) {
  const context = await authenticateRequest(req)
  
  const supabase = createDatabaseClient()

  const { data: business, error } = await supabase
    .from('businesses')
    .select('*')
    .eq('id', businessId)
    .single()

  if (error || !business) {
    return createErrorResponse('Business not found', 404, origin)
  }

  // Check permissions
  if (business.user_id !== context.userId) {
    return createErrorResponse('Access denied', 403, origin)
  }

  if (!business.stripe_subscription_id) {
    return createErrorResponse('No active subscription found', 400, origin)
  }

  // In a real implementation, you would cancel the Stripe subscription here
  // For now, we'll just log the cancellation request
  await logSeoAction(
    businessId,
    'subscription_cancel_requested',
    `Subscription cancellation requested for ${business.plan_tier} plan`,
    'subscription',
    undefined,
    undefined,
    context.userId!,
    context.ipAddress,
    context.userAgent
  )

  return createResponse({
    message: 'Subscription cancellation requested. It will be cancelled at the end of the current billing period.',
  }, 200, origin)
}

async function handleStripeWebhook(req: Request, origin?: string) {
  if (req.method !== 'POST') {
    return createErrorResponse('Method not allowed', 405, origin)
  }

  // In a real implementation, you would:
  // 1. Verify the Stripe webhook signature
  // 2. Parse the event
  // 3. Handle different event types (payment succeeded, failed, subscription updated, etc.)
  // 4. Update the database accordingly

  const payload = await req.text()
  
  try {
    // Mock webhook processing
    console.log('Received Stripe webhook:', payload.substring(0, 100) + '...')
    
    // For now, just return success
    return createResponse({
      status: 'success',
      message: 'Webhook processed',
    }, 200, origin)
    
  } catch (error) {
    console.error('Webhook processing failed:', error)
    return createErrorResponse('Webhook processing failed', 400, origin)
  }
}

// Helper function to create Stripe customer (mock implementation)
async function createStripeCustomer(user: any) {
  // In a real implementation, you would use the Stripe API
  return {
    id: `cus_mock_${user.id}`,
    email: user.email,
    name: `${user.first_name} ${user.last_name}`,
  }
}

// Helper function to create Stripe subscription (mock implementation)
async function createStripeSubscription(customerId: string, planTier: string, billingCycle: string) {
  // In a real implementation, you would use the Stripe API
  const plan = PRICING_PLANS[planTier as keyof typeof PRICING_PLANS]
  
  return {
    id: `sub_mock_${Date.now()}`,
    customer: customerId,
    status: 'trialing',
    trial_end: Math.floor(Date.now() / 1000) + (14 * 24 * 60 * 60), // 14 days from now
    current_period_end: Math.floor(Date.now() / 1000) + (30 * 24 * 60 * 60), // 30 days from now
  }
}