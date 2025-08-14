import type { Database } from './supabase'

// Supabase table types
export type User = Database['public']['Tables']['users']['Row']
export type UserInsert = Database['public']['Tables']['users']['Insert']
export type UserUpdate = Database['public']['Tables']['users']['Update']

export type Business = Database['public']['Tables']['businesses']['Row']
export type BusinessInsert = Database['public']['Tables']['businesses']['Insert']
export type BusinessUpdate = Database['public']['Tables']['businesses']['Update']

export type SEOReport = Database['public']['Tables']['seo_reports']['Row']
export type SEOReportInsert = Database['public']['Tables']['seo_reports']['Insert']
export type SEOReportUpdate = Database['public']['Tables']['seo_reports']['Update']

export type SEOLog = Database['public']['Tables']['seo_logs']['Row']
export type SEOLogInsert = Database['public']['Tables']['seo_logs']['Insert']
export type SEOLogUpdate = Database['public']['Tables']['seo_logs']['Update']

export type BusinessAnalytics = Database['public']['Views']['business_analytics']['Row']

// Auth types
export interface AuthUser {
  id: string
  email: string
  firstName: string
  lastName: string
  role: 'admin' | 'business_owner'
  isActive: boolean
  emailVerified: boolean
  createdAt: string
  lastLogin?: string
}

export interface LoginCredentials {
  email: string
  password: string
}

export interface RegisterData {
  email: string
  password: string
  firstName: string
  lastName: string
  phone?: string
}

// Business types
export interface BusinessWithOwner extends Business {
  owner?: Pick<User, 'id' | 'email' | 'first_name' | 'last_name'>
}

export interface BusinessInsights {
  businessId: number
  totalReports: number
  reportsByType: Record<string, number>
  avgScoresByType: Record<string, number>
  recentActivity: Array<{
    actionType: string
    description: string
    createdAt: string
  }>
  performanceTrend: Array<{
    date: string
    score: number
    reportType: string
  }>
}

// SEO Report types
export interface SEOReportWithBusiness extends SEOReport {
  business?: Pick<Business, 'id' | 'business_name' | 'website_url'>
}

export interface SEOReportResults {
  auditResult?: {
    technicalScore: number
    contentScore: number
    performanceScore: number
    issues: Array<{
      severity: 'low' | 'medium' | 'high' | 'critical'
      message: string
      element?: string
    }>
  }
  performanceResult?: {
    coreWebVitals: {
      lcp: number
      fid: number
      cls: number
    }
    recommendations: Array<{
      metric: string
      current: string
      target: string
      priority: 'low' | 'medium' | 'high'
      suggestions: string[]
    }>
  }
  keywordResult?: {
    keywords: Array<{
      keyword: string
      searchVolume: number
      difficulty: number
      position?: number
    }>
    opportunities: Array<{
      keyword: string
      searchVolume: number
      difficulty: number
      potentialTraffic: number
    }>
  }
}

// Pricing types
export interface PricingPlan {
  id: 'professional' | 'business' | 'enterprise'
  name: string
  monthlyPrice: number
  yearlyPrice: number
  features: string[]
  limits: {
    seoServices: number
    keywordsPerResearch: number | 'unlimited'
    businesses: number
    automationLevel: 'basic' | 'full' | 'white-label'
  }
  popular?: boolean
}

export interface Subscription {
  businessId: number
  planTier: 'professional' | 'business' | 'enterprise'
  billingCycle: 'monthly' | 'yearly'
  subscriptionStatus: 'trial' | 'active' | 'suspended' | 'cancelled' | 'past_due' | 'incomplete'
  trialEndsAt?: string
  planDetails: PricingPlan
  isTrial: boolean
  isActive: boolean
  currentPeriodStart?: number
  currentPeriodEnd?: number
  cancelAtPeriodEnd?: boolean
}

// API Response types
export interface ApiResponse<T = any> {
  data?: T
  error?: string
  message?: string
}

export interface PaginatedResponse<T = any> {
  data: T[]
  pagination: {
    page: number
    perPage: number
    total: number
    pages: number
    hasNext: boolean
    hasPrev: boolean
  }
}

// Form types
export interface BusinessFormData {
  businessName: string
  websiteUrl?: string
  industry?: string
  businessType: 'local' | 'national' | 'ecommerce'
  address?: string
  city: string
  state: string
  zipCode?: string
  phone?: string
  targetKeywords?: string[]
  competitors?: string[]
  planTier: 'professional' | 'business' | 'enterprise'
}

// Analytics types
export interface DashboardMetrics {
  totalBusinesses: number
  businessesByPlan: Record<string, number>
  businessesByStatus: Record<string, number>
  recentSignups: Array<{
    businessName: string
    planTier: string
    createdAt: string
  }>
  revenueSummary: {
    monthlyRecurring: number
    trialBusinesses: number
    activeSubscriptions: number
  }
}

// Error types
export interface AppError {
  code?: string
  message: string
  details?: any
}

// Theme types
export type Theme = 'light' | 'dark' | 'system'

// Notification types
export interface Notification {
  id: string
  type: 'success' | 'error' | 'warning' | 'info'
  title: string
  message?: string
  duration?: number
}

// Search/Filter types
export interface SearchFilters {
  query?: string
  status?: string[]
  planTier?: string[]
  dateRange?: {
    from: Date
    to: Date
  }
  sortBy?: string
  sortOrder?: 'asc' | 'desc'
}

// Export combined database type
export type { Database }