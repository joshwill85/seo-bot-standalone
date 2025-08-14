export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[]

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
    Views: {
      business_analytics: {
        Row: {
          business_id: number | null
          business_name: string | null
          city: string | null
          state: string | null
          plan_tier: string | null
          subscription_status: string | null
          business_created_at: string | null
          owner_email: string | null
          first_name: string | null
          last_name: string | null
          total_reports: number | null
          reports_last_30_days: number | null
          avg_audit_score: number | null
          last_report_date: string | null
          total_log_entries: number | null
        }
      }
    }
    Functions: {
      get_business_insights: {
        Args: {
          business_id_param: number
        }
        Returns: Json
      }
    }
  }
}