// Shared types for Supabase Edge Functions

export interface Database {
  public: {
    Tables: {
      users: {
        Row: {
          id: number
          email: string
          password_hash: string
          first_name: string
          last_name: string
          phone: string | null
          role: 'admin' | 'business_owner'
          is_active: boolean
          email_verified: boolean
          stripe_customer_id: string | null
          created_at: string
          last_login: string | null
        }
        Insert: {
          id?: number
          email: string
          password_hash: string
          first_name: string
          last_name: string
          phone?: string | null
          role?: 'admin' | 'business_owner'
          is_active?: boolean
          email_verified?: boolean
          stripe_customer_id?: string | null
          created_at?: string
          last_login?: string | null
        }
        Update: {
          id?: number
          email?: string
          password_hash?: string
          first_name?: string
          last_name?: string
          phone?: string | null
          role?: 'admin' | 'business_owner'
          is_active?: boolean
          email_verified?: boolean
          stripe_customer_id?: string | null
          created_at?: string
          last_login?: string | null
        }
      }
      businesses: {
        Row: {
          id: number
          user_id: number
          business_name: string
          website_url: string | null
          industry: string | null
          business_type: 'local' | 'national' | 'ecommerce'
          address: string | null
          city: string
          state: string
          zip_code: string | null
          phone: string | null
          target_keywords: string | null
          competitors: string | null
          current_rankings: string | null
          plan_tier: 'starter' | 'professional' | 'enterprise'
          subscription_status: 'trial' | 'active' | 'suspended' | 'cancelled' | 'past_due' | 'incomplete'
          billing_cycle: 'monthly' | 'yearly'
          stripe_customer_id: string | null
          stripe_subscription_id: string | null
          trial_ends_at: string | null
          created_at: string
          updated_at: string
        }
        Insert: {
          id?: number
          user_id: number
          business_name: string
          website_url?: string | null
          industry?: string | null
          business_type?: 'local' | 'national' | 'ecommerce'
          address?: string | null
          city: string
          state?: string
          zip_code?: string | null
          phone?: string | null
          target_keywords?: string | null
          competitors?: string | null
          current_rankings?: string | null
          plan_tier: 'starter' | 'professional' | 'enterprise'
          subscription_status?: 'trial' | 'active' | 'suspended' | 'cancelled' | 'past_due' | 'incomplete'
          billing_cycle?: 'monthly' | 'yearly'
          stripe_customer_id?: string | null
          stripe_subscription_id?: string | null
          trial_ends_at?: string | null
          created_at?: string
          updated_at?: string
        }
        Update: {
          id?: number
          user_id?: number
          business_name?: string
          website_url?: string | null
          industry?: string | null
          business_type?: 'local' | 'national' | 'ecommerce'
          address?: string | null
          city?: string
          state?: string
          zip_code?: string | null
          phone?: string | null
          target_keywords?: string | null
          competitors?: string | null
          current_rankings?: string | null
          plan_tier?: 'starter' | 'professional' | 'enterprise'
          subscription_status?: 'trial' | 'active' | 'suspended' | 'cancelled' | 'past_due' | 'incomplete'
          billing_cycle?: 'monthly' | 'yearly'
          stripe_customer_id?: string | null
          stripe_subscription_id?: string | null
          trial_ends_at?: string | null
          created_at?: string
          updated_at?: string
        }
      }
      seo_reports: {
        Row: {
          id: number
          business_id: number
          report_type: 'full_audit' | 'keyword_research' | 'serp_analysis' | 'performance_audit' | 'accessibility_audit' | 'content_analysis'
          status: 'pending' | 'running' | 'completed' | 'failed'
          results: string | null
          score: number | null
          issues_found: number
          recommendations: string | null
          execution_time_ms: number | null
          tools_used: string | null
          created_at: string
          completed_at: string | null
        }
        Insert: {
          id?: number
          business_id: number
          report_type: 'full_audit' | 'keyword_research' | 'serp_analysis' | 'performance_audit' | 'accessibility_audit' | 'content_analysis'
          status?: 'pending' | 'running' | 'completed' | 'failed'
          results?: string | null
          score?: number | null
          issues_found?: number
          recommendations?: string | null
          execution_time_ms?: number | null
          tools_used?: string | null
          created_at?: string
          completed_at?: string | null
        }
        Update: {
          id?: number
          business_id?: number
          report_type?: 'full_audit' | 'keyword_research' | 'serp_analysis' | 'performance_audit' | 'accessibility_audit' | 'content_analysis'
          status?: 'pending' | 'running' | 'completed' | 'failed'
          results?: string | null
          score?: number | null
          issues_found?: number
          recommendations?: string | null
          execution_time_ms?: number | null
          tools_used?: string | null
          created_at?: string
          completed_at?: string | null
        }
      }
      seo_logs: {
        Row: {
          id: number
          business_id: number
          action_type: string
          action_description: string
          tool_name: string | null
          old_data: string | null
          new_data: string | null
          user_id: number | null
          ip_address: string | null
          user_agent: string | null
          created_at: string
        }
        Insert: {
          id?: number
          business_id: number
          action_type: string
          action_description: string
          tool_name?: string | null
          old_data?: string | null
          new_data?: string | null
          user_id?: number | null
          ip_address?: string | null
          user_agent?: string | null
          created_at?: string
        }
        Update: {
          id?: number
          business_id?: number
          action_type?: string
          action_description?: string
          tool_name?: string | null
          old_data?: string | null
          new_data?: string | null
          user_id?: number | null
          ip_address?: string | null
          user_agent?: string | null
          created_at?: string
        }
      }
    }
  }
}

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

export interface RequestContext {
  userId?: number
  userRole?: 'admin' | 'business_owner'
  ipAddress?: string
  userAgent?: string
}

export interface ValidationError {
  field: string
  message: string
}

export class AppError extends Error {
  constructor(
    message: string,
    public code: string = 'UNKNOWN_ERROR',
    public statusCode: number = 500,
    public details?: any
  ) {
    super(message)
    this.name = 'AppError'
  }
}

export class ValidationAppError extends AppError {
  constructor(message: string, public errors: ValidationError[]) {
    super(message, 'VALIDATION_ERROR', 400)
  }
}