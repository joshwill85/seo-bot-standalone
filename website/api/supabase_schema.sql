-- Central Florida SEO Services Database Schema for Supabase
-- Run this in your Supabase SQL editor to create the required tables

-- Enable Row Level Security
ALTER DATABASE postgres SET "app.jwt_secret" TO 'your-jwt-secret-key';

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id BIGSERIAL PRIMARY KEY,
    email VARCHAR(120) UNIQUE NOT NULL,
    password_hash VARCHAR(128) NOT NULL,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    phone VARCHAR(20),
    role VARCHAR(20) NOT NULL DEFAULT 'business_owner', -- admin, business_owner
    is_active BOOLEAN DEFAULT true,
    email_verified BOOLEAN DEFAULT false,
    stripe_customer_id VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_login TIMESTAMPTZ,
    
    CONSTRAINT check_role CHECK (role IN ('admin', 'business_owner'))
);

-- Create index on email for faster lookups
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);

-- Businesses table
CREATE TABLE IF NOT EXISTS businesses (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Business Information
    business_name VARCHAR(200) NOT NULL,
    website_url VARCHAR(255),
    industry VARCHAR(100),
    business_type VARCHAR(50) DEFAULT 'local', -- local, national, ecommerce
    
    -- Contact Information
    address VARCHAR(255),
    city VARCHAR(100) NOT NULL,
    state VARCHAR(50) NOT NULL DEFAULT 'Florida',
    zip_code VARCHAR(10),
    phone VARCHAR(20),
    
    -- SEO Details
    target_keywords TEXT, -- JSON array of keywords
    competitors TEXT, -- JSON array of competitor URLs
    current_rankings TEXT, -- JSON data
    
    -- Subscription
    plan_tier VARCHAR(20) NOT NULL, -- starter, professional, enterprise
    subscription_status VARCHAR(20) DEFAULT 'trial', -- trial, active, suspended, cancelled
    billing_cycle VARCHAR(20) DEFAULT 'monthly', -- monthly, yearly
    stripe_customer_id VARCHAR(100),
    stripe_subscription_id VARCHAR(100),
    trial_ends_at TIMESTAMPTZ,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT check_business_type CHECK (business_type IN ('local', 'national', 'ecommerce')),
    CONSTRAINT check_plan_tier CHECK (plan_tier IN ('starter', 'professional', 'enterprise')),
    CONSTRAINT check_subscription_status CHECK (subscription_status IN ('trial', 'active', 'suspended', 'cancelled', 'past_due', 'incomplete')),
    CONSTRAINT check_billing_cycle CHECK (billing_cycle IN ('monthly', 'yearly'))
);

-- Create indexes for businesses
CREATE INDEX IF NOT EXISTS idx_businesses_user_id ON businesses(user_id);
CREATE INDEX IF NOT EXISTS idx_businesses_city ON businesses(city);
CREATE INDEX IF NOT EXISTS idx_businesses_plan_tier ON businesses(plan_tier);
CREATE INDEX IF NOT EXISTS idx_businesses_subscription_status ON businesses(subscription_status);

-- SEO Reports table
CREATE TABLE IF NOT EXISTS seo_reports (
    id BIGSERIAL PRIMARY KEY,
    business_id BIGINT NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
    
    -- Report Details
    report_type VARCHAR(50) NOT NULL, -- audit, keywords, performance, accessibility, content
    status VARCHAR(20) DEFAULT 'pending', -- pending, running, completed, failed
    
    -- Report Data
    results TEXT, -- JSON results
    score DECIMAL(5,2), -- Overall score (0-100)
    issues_found INTEGER DEFAULT 0,
    recommendations TEXT, -- JSON array
    
    -- Execution Details
    execution_time_ms INTEGER,
    tools_used TEXT, -- JSON array of tool names
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    
    CONSTRAINT check_report_type CHECK (report_type IN ('full_audit', 'keyword_research', 'serp_analysis', 'performance_audit', 'accessibility_audit', 'content_analysis')),
    CONSTRAINT check_status CHECK (status IN ('pending', 'running', 'completed', 'failed')),
    CONSTRAINT check_score CHECK (score IS NULL OR (score >= 0 AND score <= 100))
);

-- Create indexes for SEO reports
CREATE INDEX IF NOT EXISTS idx_seo_reports_business_id ON seo_reports(business_id);
CREATE INDEX IF NOT EXISTS idx_seo_reports_type ON seo_reports(report_type);
CREATE INDEX IF NOT EXISTS idx_seo_reports_status ON seo_reports(status);
CREATE INDEX IF NOT EXISTS idx_seo_reports_created_at ON seo_reports(created_at DESC);

-- SEO Logs table for historical tracking
CREATE TABLE IF NOT EXISTS seo_logs (
    id BIGSERIAL PRIMARY KEY,
    business_id BIGINT NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
    
    -- Log Details
    action_type VARCHAR(50) NOT NULL, -- report_run, keyword_update, subscription_created, etc.
    action_description TEXT NOT NULL,
    tool_name VARCHAR(100),
    
    -- Data Changes
    old_data TEXT, -- JSON of previous state
    new_data TEXT, -- JSON of new state
    
    -- Metadata
    user_id BIGINT REFERENCES users(id),
    ip_address INET,
    user_agent TEXT,
    
    -- Timestamp
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for SEO logs
CREATE INDEX IF NOT EXISTS idx_seo_logs_business_id ON seo_logs(business_id);
CREATE INDEX IF NOT EXISTS idx_seo_logs_action_type ON seo_logs(action_type);
CREATE INDEX IF NOT EXISTS idx_seo_logs_created_at ON seo_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_seo_logs_user_id ON seo_logs(user_id);

-- Create a function to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger for businesses table
CREATE TRIGGER update_businesses_updated_at
    BEFORE UPDATE ON businesses
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Row Level Security (RLS) Policies

-- Enable RLS on all tables
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE businesses ENABLE ROW LEVEL SECURITY;
ALTER TABLE seo_reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE seo_logs ENABLE ROW LEVEL SECURITY;

-- Users can only see their own data
CREATE POLICY "Users can view own profile" ON users
    FOR SELECT USING (auth.uid()::text = id::text);

CREATE POLICY "Users can update own profile" ON users
    FOR UPDATE USING (auth.uid()::text = id::text);

-- Businesses: users can see their own, admins can see all
CREATE POLICY "Users can view own businesses" ON businesses
    FOR SELECT USING (
        user_id = (SELECT id FROM users WHERE auth.uid()::text = id::text)
        OR
        EXISTS (SELECT 1 FROM users WHERE auth.uid()::text = id::text AND role = 'admin')
    );

CREATE POLICY "Users can insert own businesses" ON businesses
    FOR INSERT WITH CHECK (user_id = (SELECT id FROM users WHERE auth.uid()::text = id::text));

CREATE POLICY "Users can update own businesses" ON businesses
    FOR UPDATE USING (
        user_id = (SELECT id FROM users WHERE auth.uid()::text = id::text)
        OR
        EXISTS (SELECT 1 FROM users WHERE auth.uid()::text = id::text AND role = 'admin')
    );

-- SEO Reports: users can see reports for their businesses, admins can see all
CREATE POLICY "Users can view reports for their businesses" ON seo_reports
    FOR SELECT USING (
        business_id IN (SELECT id FROM businesses WHERE user_id = (SELECT id FROM users WHERE auth.uid()::text = id::text))
        OR
        EXISTS (SELECT 1 FROM users WHERE auth.uid()::text = id::text AND role = 'admin')
    );

CREATE POLICY "System can insert SEO reports" ON seo_reports
    FOR INSERT WITH CHECK (true); -- Allow system to insert reports

CREATE POLICY "System can update SEO reports" ON seo_reports
    FOR UPDATE USING (true); -- Allow system to update reports

-- SEO Logs: users can see logs for their businesses, admins can see all
CREATE POLICY "Users can view logs for their businesses" ON seo_logs
    FOR SELECT USING (
        business_id IN (SELECT id FROM businesses WHERE user_id = (SELECT id FROM users WHERE auth.uid()::text = id::text))
        OR
        EXISTS (SELECT 1 FROM users WHERE auth.uid()::text = id::text AND role = 'admin')
    );

CREATE POLICY "System can insert SEO logs" ON seo_logs
    FOR INSERT WITH CHECK (true); -- Allow system to insert logs

-- Create analytics view for admin dashboard
CREATE OR REPLACE VIEW business_analytics AS
SELECT 
    b.id as business_id,
    b.business_name,
    b.city,
    b.state,
    b.plan_tier,
    b.subscription_status,
    b.created_at as business_created_at,
    u.email as owner_email,
    u.first_name,
    u.last_name,
    COUNT(DISTINCT sr.id) as total_reports,
    COUNT(DISTINCT CASE WHEN sr.created_at >= NOW() - INTERVAL '30 days' THEN sr.id END) as reports_last_30_days,
    AVG(CASE WHEN sr.report_type = 'full_audit' AND sr.score IS NOT NULL THEN sr.score END) as avg_audit_score,
    MAX(sr.created_at) as last_report_date,
    COUNT(DISTINCT sl.id) as total_log_entries
FROM businesses b
LEFT JOIN users u ON b.user_id = u.id
LEFT JOIN seo_reports sr ON b.id = sr.business_id
LEFT JOIN seo_logs sl ON b.id = sl.business_id
GROUP BY b.id, b.business_name, b.city, b.state, b.plan_tier, b.subscription_status, 
         b.created_at, u.email, u.first_name, u.last_name;

-- Create function for business insights
CREATE OR REPLACE FUNCTION get_business_insights(business_id_param BIGINT)
RETURNS JSON AS $$
DECLARE
    result JSON;
BEGIN
    SELECT json_build_object(
        'business_id', business_id_param,
        'total_reports', COUNT(DISTINCT sr.id),
        'reports_by_type', json_object_agg(sr.report_type, COUNT(sr.id)) FILTER (WHERE sr.report_type IS NOT NULL),
        'avg_scores_by_type', json_object_agg(sr.report_type, AVG(sr.score)) FILTER (WHERE sr.score IS NOT NULL),
        'recent_activity', (
            SELECT json_agg(
                json_build_object(
                    'action_type', sl.action_type,
                    'description', sl.action_description,
                    'created_at', sl.created_at
                )
            )
            FROM (
                SELECT action_type, action_description, created_at
                FROM seo_logs 
                WHERE business_id = business_id_param 
                ORDER BY created_at DESC 
                LIMIT 10
            ) sl
        ),
        'performance_trend', (
            SELECT json_agg(
                json_build_object(
                    'date', DATE(sr.created_at),
                    'score', sr.score,
                    'report_type', sr.report_type
                ) ORDER BY sr.created_at
            )
            FROM seo_reports sr
            WHERE sr.business_id = business_id_param 
            AND sr.score IS NOT NULL
            AND sr.created_at >= NOW() - INTERVAL '90 days'
        )
    ) INTO result
    FROM seo_reports sr
    WHERE sr.business_id = business_id_param;
    
    RETURN result;
END;
$$ LANGUAGE plpgsql;

-- Insert default admin user (update password hash as needed)
INSERT INTO users (email, password_hash, first_name, last_name, role, is_active, email_verified)
VALUES (
    'admin@centralfloridaseo.com',
    '$2b$12$dummy.hash.replace.with.real.hash', -- Replace with actual bcrypt hash
    'Admin',
    'User',
    'admin',
    true,
    true
) ON CONFLICT (email) DO NOTHING;

-- ================================
-- SEO AUTOMATION TABLES
-- ================================

-- SEO Campaigns - Core campaign management
CREATE TABLE IF NOT EXISTS seo_campaigns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id BIGINT NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
    
    -- Campaign Details
    name VARCHAR(200) NOT NULL,
    description TEXT,
    status VARCHAR(20) DEFAULT 'active', -- active, paused, completed, cancelled
    
    -- Configuration
    config JSONB DEFAULT '{}', -- Campaign-specific settings
    seed_keywords TEXT[], -- Array of seed keywords
    target_locations TEXT[], -- Geographic targeting
    competitors TEXT[], -- Competitor URLs/domains
    
    -- Progress Tracking
    discovery_completed_at TIMESTAMPTZ,
    clustering_completed_at TIMESTAMPTZ,
    content_pipeline_status VARCHAR(20) DEFAULT 'pending', -- pending, active, completed
    
    -- Performance Metrics
    total_keywords INTEGER DEFAULT 0,
    content_pieces_planned INTEGER DEFAULT 0,
    content_pieces_published INTEGER DEFAULT 0,
    avg_keyword_difficulty DECIMAL(5,2),
    estimated_monthly_traffic INTEGER DEFAULT 0,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT check_seo_campaign_status CHECK (status IN ('active', 'paused', 'completed', 'cancelled')),
    CONSTRAINT check_content_pipeline_status CHECK (content_pipeline_status IN ('pending', 'active', 'completed'))
);

-- Keywords - Comprehensive keyword tracking
CREATE TABLE IF NOT EXISTS keywords (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id UUID NOT NULL REFERENCES seo_campaigns(id) ON DELETE CASCADE,
    
    -- Keyword Data
    keyword TEXT NOT NULL,
    keyword_hash VARCHAR(64) NOT NULL, -- SHA256 hash for deduplication
    intent VARCHAR(20), -- informational, commercial, transactional, navigational
    search_volume INTEGER,
    keyword_difficulty INTEGER, -- 0-100
    value_score DECIMAL(5,2), -- Business value score
    cpc_estimate DECIMAL(8,2), -- Cost per click estimate
    
    -- SERP Analysis
    serp_features TEXT[], -- Array of SERP features present
    top_competing_domains TEXT[], -- Domains ranking in top 10
    serp_last_analyzed TIMESTAMPTZ,
    
    -- Ranking Data
    current_rank INTEGER,
    best_rank INTEGER,
    worst_rank INTEGER,
    rank_history JSONB DEFAULT '[]', -- Array of {date, rank, url} objects
    last_rank_check TIMESTAMPTZ,
    
    -- Content Planning
    cluster_id UUID, -- Reference to keyword cluster
    content_status VARCHAR(20) DEFAULT 'planned', -- planned, briefed, written, published, optimized
    target_url TEXT, -- URL this keyword targets
    
    -- Metadata
    source VARCHAR(50), -- gsc, serp_api, autocomplete, manual
    discovery_method VARCHAR(50), -- seed_expansion, competitor_analysis, gsc_import
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT check_keyword_intent CHECK (intent IN ('informational', 'commercial', 'transactional', 'navigational')),
    CONSTRAINT check_content_status CHECK (content_status IN ('planned', 'briefed', 'written', 'published', 'optimized')),
    CONSTRAINT unique_keyword_per_campaign UNIQUE (campaign_id, keyword_hash)
);

-- Keyword Clusters - Group related keywords
CREATE TABLE IF NOT EXISTS keyword_clusters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id UUID NOT NULL REFERENCES seo_campaigns(id) ON DELETE CASCADE,
    
    -- Cluster Details
    name VARCHAR(200) NOT NULL,
    cluster_type VARCHAR(20) DEFAULT 'hub', -- hub, spoke, supporting
    parent_cluster_id UUID REFERENCES keyword_clusters(id), -- For spoke clusters
    
    -- Cluster Analysis
    primary_intent VARCHAR(20),
    total_keywords INTEGER DEFAULT 0,
    avg_search_volume INTEGER DEFAULT 0,
    avg_difficulty DECIMAL(5,2),
    priority_score DECIMAL(5,2),
    
    -- Content Planning
    content_type VARCHAR(50), -- article, comparison, howto, product, review
    content_status VARCHAR(20) DEFAULT 'planned', -- planned, briefed, written, published
    target_word_count INTEGER,
    content_outline JSONB,
    
    -- Metadata
    clustering_method VARCHAR(50), -- semantic, manual, hdbscan
    embedding_model VARCHAR(100),
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT check_cluster_type CHECK (cluster_type IN ('hub', 'spoke', 'supporting')),
    CONSTRAINT check_cluster_intent CHECK (primary_intent IN ('informational', 'commercial', 'transactional', 'navigational')),
    CONSTRAINT check_cluster_content_status CHECK (content_status IN ('planned', 'briefed', 'written', 'published'))
);

-- Content Briefs - Detailed content specifications
CREATE TABLE IF NOT EXISTS content_briefs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id UUID NOT NULL REFERENCES seo_campaigns(id) ON DELETE CASCADE,
    cluster_id UUID REFERENCES keyword_clusters(id),
    
    -- Brief Details
    title VARCHAR(300) NOT NULL,
    slug VARCHAR(200) NOT NULL,
    meta_description VARCHAR(320),
    target_keyword TEXT NOT NULL,
    secondary_keywords TEXT[],
    
    -- Content Structure
    content_type VARCHAR(50) NOT NULL, -- article, comparison, howto, product
    outline JSONB NOT NULL, -- Detailed content outline
    info_gain_items TEXT[] DEFAULT '{}', -- Unique value propositions
    word_count_target INTEGER DEFAULT 1500,
    reading_level VARCHAR(20) DEFAULT 'general', -- elementary, middle, high, college, general
    
    -- SEO Requirements
    required_headers TEXT[], -- H2/H3 structure
    internal_link_targets TEXT[], -- URLs to link to internally
    external_citation_requirements TEXT[], -- Required authoritative sources
    schema_markup_type VARCHAR(50), -- Article, HowTo, Product, etc.
    
    -- Competitive Analysis
    competitor_analysis JSONB, -- Analysis of top-ranking content
    content_gaps TEXT[], -- What competitors are missing
    differentiation_strategy TEXT,
    
    -- Production Status
    status VARCHAR(20) DEFAULT 'draft', -- draft, approved, in_progress, completed, published
    assigned_writer VARCHAR(100),
    due_date TIMESTAMPTZ,
    
    -- Quality Gates
    min_info_gain_score INTEGER DEFAULT 5,
    requires_expert_review BOOLEAN DEFAULT false,
    compliance_notes TEXT,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    approved_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    
    CONSTRAINT check_brief_status CHECK (status IN ('draft', 'approved', 'in_progress', 'completed', 'published')),
    CONSTRAINT check_reading_level CHECK (reading_level IN ('elementary', 'middle', 'high', 'college', 'general')),
    CONSTRAINT unique_slug_per_campaign UNIQUE (campaign_id, slug)
);

-- Technical Audits - Comprehensive site health tracking
CREATE TABLE IF NOT EXISTS technical_audits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id BIGINT NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
    
    -- Audit Configuration
    audit_type VARCHAR(50) NOT NULL, -- full_site, page_sample, specific_urls
    urls_audited TEXT[], -- Array of URLs audited
    audit_config JSONB DEFAULT '{}', -- Audit-specific settings
    
    -- Performance Metrics
    performance_score INTEGER, -- 0-100
    accessibility_score INTEGER, -- 0-100
    best_practices_score INTEGER, -- 0-100
    seo_score INTEGER, -- 0-100
    pwa_score INTEGER, -- 0-100
    
    -- Core Web Vitals
    avg_lcp DECIMAL(8,2), -- Largest Contentful Paint (ms)
    avg_inp DECIMAL(8,2), -- Interaction to Next Paint (ms)
    avg_cls DECIMAL(5,3), -- Cumulative Layout Shift
    avg_fcp DECIMAL(8,2), -- First Contentful Paint (ms)
    avg_ttfb DECIMAL(8,2), -- Time to First Byte (ms)
    
    -- Technical Issues
    issues_found JSONB DEFAULT '[]', -- Array of issue objects
    critical_issues INTEGER DEFAULT 0,
    warning_issues INTEGER DEFAULT 0,
    info_issues INTEGER DEFAULT 0,
    
    -- Recommendations
    recommendations JSONB DEFAULT '[]', -- Array of recommendation objects
    priority_fixes TEXT[], -- Top priority fixes
    estimated_impact JSONB, -- Estimated impact of fixes
    
    -- Execution Details
    audit_tool VARCHAR(50), -- lighthouse, pagespeed, custom
    execution_time_seconds INTEGER,
    pages_analyzed INTEGER,
    
    -- Status
    status VARCHAR(20) DEFAULT 'completed', -- pending, running, completed, failed
    error_message TEXT,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    
    CONSTRAINT check_audit_status CHECK (status IN ('pending', 'running', 'completed', 'failed')),
    CONSTRAINT check_scores CHECK (
        (performance_score IS NULL OR performance_score BETWEEN 0 AND 100) AND
        (accessibility_score IS NULL OR accessibility_score BETWEEN 0 AND 100) AND
        (best_practices_score IS NULL OR best_practices_score BETWEEN 0 AND 100) AND
        (seo_score IS NULL OR seo_score BETWEEN 0 AND 100) AND
        (pwa_score IS NULL OR pwa_score BETWEEN 0 AND 100)
    )
);

-- Internal Links - Track and optimize internal linking
CREATE TABLE IF NOT EXISTS internal_links (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id UUID NOT NULL REFERENCES seo_campaigns(id) ON DELETE CASCADE,
    
    -- Link Details
    source_url TEXT NOT NULL,
    target_url TEXT NOT NULL,
    anchor_text TEXT NOT NULL,
    link_type VARCHAR(20) DEFAULT 'contextual', -- contextual, navigational, footer, sidebar
    
    -- Link Context
    source_page_type VARCHAR(50), -- homepage, category, article, product
    target_page_type VARCHAR(50),
    section_context TEXT, -- Which section of the page contains the link
    surrounding_text TEXT, -- Text around the link for context
    
    -- SEO Analysis
    link_relevance_score DECIMAL(5,2), -- How relevant is this link (0-10)
    anchor_text_optimization VARCHAR(20) DEFAULT 'good', -- poor, fair, good, excellent
    is_nofollow BOOLEAN DEFAULT false,
    
    -- Link Status
    status VARCHAR(20) DEFAULT 'active', -- active, broken, redirected, removed
    http_status INTEGER, -- Last known HTTP status
    last_checked TIMESTAMPTZ,
    
    -- Automation
    auto_generated BOOLEAN DEFAULT false,
    generation_method VARCHAR(50), -- manual, semantic_similarity, cluster_based
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT check_link_type CHECK (link_type IN ('contextual', 'navigational', 'footer', 'sidebar')),
    CONSTRAINT check_link_status CHECK (status IN ('active', 'broken', 'redirected', 'removed')),
    CONSTRAINT check_anchor_optimization CHECK (anchor_text_optimization IN ('poor', 'fair', 'good', 'excellent'))
);

-- Content Performance - Track content metrics
CREATE TABLE IF NOT EXISTS content_performance (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id UUID NOT NULL REFERENCES seo_campaigns(id) ON DELETE CASCADE,
    brief_id UUID REFERENCES content_briefs(id),
    
    -- Content Details
    url TEXT NOT NULL,
    title VARCHAR(300),
    publish_date TIMESTAMPTZ,
    last_updated TIMESTAMPTZ,
    word_count INTEGER,
    
    -- Performance Metrics
    organic_traffic INTEGER DEFAULT 0,
    impressions INTEGER DEFAULT 0,
    clicks INTEGER DEFAULT 0,
    ctr DECIMAL(5,4), -- Click-through rate
    avg_position DECIMAL(5,2), -- Average search position
    
    -- Engagement Metrics
    avg_time_on_page INTEGER, -- Seconds
    bounce_rate DECIMAL(5,4),
    pages_per_session DECIMAL(5,2),
    conversion_rate DECIMAL(5,4),
    goal_completions INTEGER DEFAULT 0,
    
    -- Ranking Performance
    featured_snippets INTEGER DEFAULT 0, -- Number of featured snippets earned
    top_10_keywords INTEGER DEFAULT 0,
    top_3_keywords INTEGER DEFAULT 0,
    ranking_keywords JSONB DEFAULT '[]', -- Array of ranking keyword objects
    
    -- Technical Performance
    page_speed_score INTEGER, -- 0-100
    mobile_usability_score INTEGER, -- 0-100
    core_web_vitals_status VARCHAR(20), -- good, needs_improvement, poor
    
    -- Content Quality Signals
    backlinks_earned INTEGER DEFAULT 0,
    social_shares INTEGER DEFAULT 0,
    internal_links_received INTEGER DEFAULT 0,
    content_freshness_score DECIMAL(5,2), -- Based on last update and topic
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_crawled TIMESTAMPTZ,
    
    CONSTRAINT check_web_vitals_status CHECK (core_web_vitals_status IN ('good', 'needs_improvement', 'poor', NULL))
);

-- SEO Tasks - Automated task queue
CREATE TABLE IF NOT EXISTS seo_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id UUID REFERENCES seo_campaigns(id) ON DELETE CASCADE,
    business_id BIGINT REFERENCES businesses(id) ON DELETE CASCADE,
    
    -- Task Details
    task_type VARCHAR(50) NOT NULL, -- keyword_discovery, content_brief, technical_audit, etc.
    task_name VARCHAR(200) NOT NULL,
    description TEXT,
    priority INTEGER DEFAULT 5, -- 1-10, 10 being highest
    
    -- Task Configuration
    task_config JSONB DEFAULT '{}', -- Task-specific parameters (renamed from config)
    dependencies UUID[], -- Array of task IDs this depends on
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    auto_retry BOOLEAN DEFAULT true,
    
    -- Scheduling and Automation
    schedule_type VARCHAR(20) DEFAULT 'immediate', -- immediate, recurring, conditional
    frequency VARCHAR(20), -- daily, weekly, monthly, quarterly
    next_run TIMESTAMPTZ,
    last_run TIMESTAMPTZ,
    conditions JSONB, -- Conditional trigger criteria
    
    -- Execution Details
    status VARCHAR(20) DEFAULT 'pending', -- pending, running, completed, failed, cancelled, scheduled
    assigned_to VARCHAR(100), -- System component or user
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    execution_time_seconds INTEGER,
    
    -- Results
    result_data JSONB,
    error_message TEXT,
    output_files TEXT[], -- Array of generated file paths
    
    -- Legacy Scheduling (keeping for compatibility)
    scheduled_for TIMESTAMPTZ,
    recurring_pattern VARCHAR(50), -- daily, weekly, monthly, custom
    next_run_at TIMESTAMPTZ,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT check_task_status CHECK (status IN ('pending', 'running', 'completed', 'failed', 'cancelled')),
    CONSTRAINT check_priority CHECK (priority BETWEEN 1 AND 10)
);

-- ================================
-- INDEXES FOR SEO TABLES
-- ================================

-- SEO Campaigns indexes
CREATE INDEX IF NOT EXISTS idx_seo_campaigns_business_id ON seo_campaigns(business_id);
CREATE INDEX IF NOT EXISTS idx_seo_campaigns_status ON seo_campaigns(status);
CREATE INDEX IF NOT EXISTS idx_seo_campaigns_created_at ON seo_campaigns(created_at DESC);

-- Keywords indexes
CREATE INDEX IF NOT EXISTS idx_keywords_campaign_id ON keywords(campaign_id);
CREATE INDEX IF NOT EXISTS idx_keywords_cluster_id ON keywords(cluster_id);
CREATE INDEX IF NOT EXISTS idx_keywords_keyword_hash ON keywords(keyword_hash);
CREATE INDEX IF NOT EXISTS idx_keywords_intent ON keywords(intent);
CREATE INDEX IF NOT EXISTS idx_keywords_content_status ON keywords(content_status);
CREATE INDEX IF NOT EXISTS idx_keywords_current_rank ON keywords(current_rank);
CREATE INDEX IF NOT EXISTS idx_keywords_search_volume ON keywords(search_volume DESC);

-- Keyword Clusters indexes
CREATE INDEX IF NOT EXISTS idx_keyword_clusters_campaign_id ON keyword_clusters(campaign_id);
CREATE INDEX IF NOT EXISTS idx_keyword_clusters_parent_id ON keyword_clusters(parent_cluster_id);
CREATE INDEX IF NOT EXISTS idx_keyword_clusters_priority ON keyword_clusters(priority_score DESC);

-- Content Briefs indexes
CREATE INDEX IF NOT EXISTS idx_content_briefs_campaign_id ON content_briefs(campaign_id);
CREATE INDEX IF NOT EXISTS idx_content_briefs_cluster_id ON content_briefs(cluster_id);
CREATE INDEX IF NOT EXISTS idx_content_briefs_status ON content_briefs(status);
CREATE INDEX IF NOT EXISTS idx_content_briefs_due_date ON content_briefs(due_date);

-- Technical Audits indexes
CREATE INDEX IF NOT EXISTS idx_technical_audits_business_id ON technical_audits(business_id);
CREATE INDEX IF NOT EXISTS idx_technical_audits_created_at ON technical_audits(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_technical_audits_performance_score ON technical_audits(performance_score DESC);

-- Internal Links indexes
CREATE INDEX IF NOT EXISTS idx_internal_links_campaign_id ON internal_links(campaign_id);
CREATE INDEX IF NOT EXISTS idx_internal_links_source_url ON internal_links(source_url);
CREATE INDEX IF NOT EXISTS idx_internal_links_target_url ON internal_links(target_url);
CREATE INDEX IF NOT EXISTS idx_internal_links_status ON internal_links(status);

-- Content Performance indexes
CREATE INDEX IF NOT EXISTS idx_content_performance_campaign_id ON content_performance(campaign_id);
CREATE INDEX IF NOT EXISTS idx_content_performance_brief_id ON content_performance(brief_id);
CREATE INDEX IF NOT EXISTS idx_content_performance_url ON content_performance(url);
CREATE INDEX IF NOT EXISTS idx_content_performance_organic_traffic ON content_performance(organic_traffic DESC);

-- SEO Tasks indexes
CREATE INDEX IF NOT EXISTS idx_seo_tasks_campaign_id ON seo_tasks(campaign_id);
CREATE INDEX IF NOT EXISTS idx_seo_tasks_business_id ON seo_tasks(business_id);
CREATE INDEX IF NOT EXISTS idx_seo_tasks_status ON seo_tasks(status);
CREATE INDEX IF NOT EXISTS idx_seo_tasks_priority ON seo_tasks(priority DESC);
CREATE INDEX IF NOT EXISTS idx_seo_tasks_scheduled_for ON seo_tasks(scheduled_for);

-- ================================
-- TRIGGERS FOR AUTO-UPDATES
-- ================================

-- Update triggers for all tables with updated_at
CREATE TRIGGER update_seo_campaigns_updated_at
    BEFORE UPDATE ON seo_campaigns
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_keywords_updated_at
    BEFORE UPDATE ON keywords
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_keyword_clusters_updated_at
    BEFORE UPDATE ON keyword_clusters
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_content_briefs_updated_at
    BEFORE UPDATE ON content_briefs
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_internal_links_updated_at
    BEFORE UPDATE ON internal_links
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_content_performance_updated_at
    BEFORE UPDATE ON content_performance
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_seo_tasks_updated_at
    BEFORE UPDATE ON seo_tasks
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ================================
-- ROW LEVEL SECURITY FOR SEO TABLES
-- ================================

-- Enable RLS on SEO tables
ALTER TABLE seo_campaigns ENABLE ROW LEVEL SECURITY;
ALTER TABLE keywords ENABLE ROW LEVEL SECURITY;
ALTER TABLE keyword_clusters ENABLE ROW LEVEL SECURITY;
ALTER TABLE content_briefs ENABLE ROW LEVEL SECURITY;
ALTER TABLE technical_audits ENABLE ROW LEVEL SECURITY;
ALTER TABLE internal_links ENABLE ROW LEVEL SECURITY;
ALTER TABLE content_performance ENABLE ROW LEVEL SECURITY;
ALTER TABLE seo_tasks ENABLE ROW LEVEL SECURITY;

-- SEO Campaigns policies
CREATE POLICY "Users can view campaigns for their businesses" ON seo_campaigns
    FOR SELECT USING (
        business_id IN (SELECT id FROM businesses WHERE user_id = (SELECT id FROM users WHERE auth.uid()::text = id::text))
        OR
        EXISTS (SELECT 1 FROM users WHERE auth.uid()::text = id::text AND role = 'admin')
    );

CREATE POLICY "System can manage SEO campaigns" ON seo_campaigns
    FOR ALL USING (true); -- Allow system operations

-- Keywords policies
CREATE POLICY "Users can view keywords for their campaigns" ON keywords
    FOR SELECT USING (
        campaign_id IN (
            SELECT sc.id FROM seo_campaigns sc 
            JOIN businesses b ON sc.business_id = b.id 
            WHERE b.user_id = (SELECT id FROM users WHERE auth.uid()::text = id::text)
        )
        OR
        EXISTS (SELECT 1 FROM users WHERE auth.uid()::text = id::text AND role = 'admin')
    );

CREATE POLICY "System can manage keywords" ON keywords
    FOR ALL USING (true);

-- Similar policies for other SEO tables
CREATE POLICY "Users can view clusters for their campaigns" ON keyword_clusters
    FOR SELECT USING (
        campaign_id IN (
            SELECT sc.id FROM seo_campaigns sc 
            JOIN businesses b ON sc.business_id = b.id 
            WHERE b.user_id = (SELECT id FROM users WHERE auth.uid()::text = id::text)
        )
        OR
        EXISTS (SELECT 1 FROM users WHERE auth.uid()::text = id::text AND role = 'admin')
    );

CREATE POLICY "System can manage clusters" ON keyword_clusters
    FOR ALL USING (true);

CREATE POLICY "Users can view briefs for their campaigns" ON content_briefs
    FOR SELECT USING (
        campaign_id IN (
            SELECT sc.id FROM seo_campaigns sc 
            JOIN businesses b ON sc.business_id = b.id 
            WHERE b.user_id = (SELECT id FROM users WHERE auth.uid()::text = id::text)
        )
        OR
        EXISTS (SELECT 1 FROM users WHERE auth.uid()::text = id::text AND role = 'admin')
    );

CREATE POLICY "System can manage briefs" ON content_briefs
    FOR ALL USING (true);

CREATE POLICY "Users can view technical audits for their businesses" ON technical_audits
    FOR SELECT USING (
        business_id IN (SELECT id FROM businesses WHERE user_id = (SELECT id FROM users WHERE auth.uid()::text = id::text))
        OR
        EXISTS (SELECT 1 FROM users WHERE auth.uid()::text = id::text AND role = 'admin')
    );

CREATE POLICY "System can manage technical audits" ON technical_audits
    FOR ALL USING (true);

CREATE POLICY "Users can view links for their campaigns" ON internal_links
    FOR SELECT USING (
        campaign_id IN (
            SELECT sc.id FROM seo_campaigns sc 
            JOIN businesses b ON sc.business_id = b.id 
            WHERE b.user_id = (SELECT id FROM users WHERE auth.uid()::text = id::text)
        )
        OR
        EXISTS (SELECT 1 FROM users WHERE auth.uid()::text = id::text AND role = 'admin')
    );

CREATE POLICY "System can manage internal links" ON internal_links
    FOR ALL USING (true);

CREATE POLICY "Users can view performance for their campaigns" ON content_performance
    FOR SELECT USING (
        campaign_id IN (
            SELECT sc.id FROM seo_campaigns sc 
            JOIN businesses b ON sc.business_id = b.id 
            WHERE b.user_id = (SELECT id FROM users WHERE auth.uid()::text = id::text)
        )
        OR
        EXISTS (SELECT 1 FROM users WHERE auth.uid()::text = id::text AND role = 'admin')
    );

CREATE POLICY "System can manage content performance" ON content_performance
    FOR ALL USING (true);

CREATE POLICY "Users can view tasks for their businesses" ON seo_tasks
    FOR SELECT USING (
        (business_id IN (SELECT id FROM businesses WHERE user_id = (SELECT id FROM users WHERE auth.uid()::text = id::text))
        OR
        campaign_id IN (
            SELECT sc.id FROM seo_campaigns sc 
            JOIN businesses b ON sc.business_id = b.id 
            WHERE b.user_id = (SELECT id FROM users WHERE auth.uid()::text = id::text)
        ))
        OR
        EXISTS (SELECT 1 FROM users WHERE auth.uid()::text = id::text AND role = 'admin')
    );

CREATE POLICY "System can manage SEO tasks" ON seo_tasks
    FOR ALL USING (true);

-- ================================
-- GOOGLE ANALYTICS INTEGRATION TABLES
-- ================================

-- Google Analytics Configurations
CREATE TABLE IF NOT EXISTS ga_configurations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id BIGINT NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
    property_id VARCHAR(50) NOT NULL,
    view_id VARCHAR(50) NOT NULL,
    access_token TEXT NOT NULL,
    refresh_token TEXT NOT NULL,
    token_expires_at TIMESTAMPTZ NOT NULL,
    account_id VARCHAR(50),
    property_name VARCHAR(200),
    view_name VARCHAR(200),
    timezone VARCHAR(50) DEFAULT 'America/New_York',
    currency VARCHAR(10) DEFAULT 'USD',
    last_sync TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(business_id, property_id, view_id)
);

-- Google Analytics Metrics
CREATE TABLE IF NOT EXISTS ga_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id BIGINT NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
    campaign_id UUID REFERENCES seo_campaigns(id) ON DELETE SET NULL,
    property_id VARCHAR(50) NOT NULL,
    view_id VARCHAR(50) NOT NULL,
    date DATE NOT NULL,
    sessions INTEGER DEFAULT 0,
    users INTEGER DEFAULT 0,
    new_users INTEGER DEFAULT 0,
    page_views INTEGER DEFAULT 0,
    avg_session_duration DECIMAL(10,2) DEFAULT 0,
    bounce_rate DECIMAL(5,2) DEFAULT 0,
    goal_completions INTEGER DEFAULT 0,
    conversion_rate DECIMAL(5,2) DEFAULT 0,
    organic_traffic INTEGER DEFAULT 0,
    organic_sessions INTEGER DEFAULT 0,
    pages_per_session DECIMAL(5,2) DEFAULT 0,
    synced_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(business_id, property_id, view_id, date)
);

-- Google Analytics Page Data
CREATE TABLE IF NOT EXISTS ga_page_data (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id BIGINT NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
    campaign_id UUID REFERENCES seo_campaigns(id) ON DELETE SET NULL,
    property_id VARCHAR(50) NOT NULL,
    view_id VARCHAR(50) NOT NULL,
    page_path VARCHAR(500) NOT NULL,
    page_title VARCHAR(500),
    page_views INTEGER DEFAULT 0,
    unique_page_views INTEGER DEFAULT 0,
    avg_time_on_page DECIMAL(10,2) DEFAULT 0,
    bounce_rate DECIMAL(5,2) DEFAULT 0,
    exit_rate DECIMAL(5,2) DEFAULT 0,
    entrances INTEGER DEFAULT 0,
    goal_completions INTEGER DEFAULT 0,
    organic_traffic INTEGER DEFAULT 0,
    date_range VARCHAR(50) NOT NULL,
    synced_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(business_id, property_id, view_id, page_path, date_range)
);

-- Google Analytics Traffic Sources
CREATE TABLE IF NOT EXISTS ga_traffic_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id BIGINT NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
    campaign_id UUID REFERENCES seo_campaigns(id) ON DELETE SET NULL,
    property_id VARCHAR(50) NOT NULL,
    view_id VARCHAR(50) NOT NULL,
    source VARCHAR(200) NOT NULL,
    medium VARCHAR(200) NOT NULL,
    campaign VARCHAR(200) DEFAULT '(not set)',
    sessions INTEGER DEFAULT 0,
    users INTEGER DEFAULT 0,
    new_users INTEGER DEFAULT 0,
    goal_completions INTEGER DEFAULT 0,
    conversion_rate DECIMAL(5,2) DEFAULT 0,
    avg_session_duration DECIMAL(10,2) DEFAULT 0,
    date_range VARCHAR(50) NOT NULL,
    synced_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(business_id, property_id, view_id, source, medium, campaign, date_range)
);

-- Google Analytics Goals
CREATE TABLE IF NOT EXISTS ga_goals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id BIGINT NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
    goal_name VARCHAR(200) NOT NULL,
    goal_type VARCHAR(50) NOT NULL CHECK (goal_type IN ('destination', 'duration', 'pages_per_session', 'event')),
    goal_details JSONB NOT NULL,
    goal_value DECIMAL(10,2),
    funnel_steps JSONB,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(business_id, goal_name)
);

-- Google Search Console Configurations (extend existing schema)
CREATE TABLE IF NOT EXISTS gsc_configurations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id BIGINT NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
    site_url VARCHAR(500) NOT NULL,
    access_token TEXT NOT NULL,
    refresh_token TEXT NOT NULL,
    token_expires_at TIMESTAMPTZ NOT NULL,
    verification_status VARCHAR(20) DEFAULT 'pending' CHECK (verification_status IN ('verified', 'unverified', 'pending')),
    permission_level VARCHAR(20) DEFAULT 'restricted_user' CHECK (permission_level IN ('owner', 'full_user', 'restricted_user')),
    last_sync TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(business_id, site_url)
);

-- Google Search Console Search Analytics
CREATE TABLE IF NOT EXISTS gsc_search_analytics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id BIGINT NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
    campaign_id UUID REFERENCES seo_campaigns(id) ON DELETE SET NULL,
    site_url VARCHAR(500) NOT NULL,
    query VARCHAR(500) NOT NULL,
    page VARCHAR(1000) NOT NULL,
    country VARCHAR(10) DEFAULT 'usa',
    device VARCHAR(20) DEFAULT 'desktop',
    clicks INTEGER DEFAULT 0,
    impressions INTEGER DEFAULT 0,
    ctr DECIMAL(8,4) DEFAULT 0,
    position DECIMAL(8,2) DEFAULT 0,
    date DATE NOT NULL,
    synced_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(business_id, site_url, query, page, date, device, country)
);

-- Google Search Console Indexing Status
CREATE TABLE IF NOT EXISTS gsc_indexing_status (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id BIGINT NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
    site_url VARCHAR(500) NOT NULL,
    page_url VARCHAR(1000) NOT NULL,
    coverage_status VARCHAR(50) NOT NULL,
    indexing_status VARCHAR(50) NOT NULL,
    last_crawled TIMESTAMPTZ,
    issues TEXT[],
    synced_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(business_id, site_url, page_url)
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_ga_metrics_business_date ON ga_metrics(business_id, date);
CREATE INDEX IF NOT EXISTS idx_ga_metrics_property_date ON ga_metrics(property_id, view_id, date);
CREATE INDEX IF NOT EXISTS idx_ga_page_data_business_page ON ga_page_data(business_id, page_path);
CREATE INDEX IF NOT EXISTS idx_ga_traffic_sources_business_source ON ga_traffic_sources(business_id, source, medium);
CREATE INDEX IF NOT EXISTS idx_gsc_analytics_business_query ON gsc_search_analytics(business_id, query);
CREATE INDEX IF NOT EXISTS idx_gsc_analytics_query_date ON gsc_search_analytics(query, date);
CREATE INDEX IF NOT EXISTS idx_gsc_indexing_business_url ON gsc_indexing_status(business_id, page_url);

-- Row Level Security Policies for GA Tables
ALTER TABLE ga_configurations ENABLE ROW LEVEL SECURITY;
ALTER TABLE ga_metrics ENABLE ROW LEVEL SECURITY;
ALTER TABLE ga_page_data ENABLE ROW LEVEL SECURITY;
ALTER TABLE ga_traffic_sources ENABLE ROW LEVEL SECURITY;
ALTER TABLE ga_goals ENABLE ROW LEVEL SECURITY;
ALTER TABLE gsc_configurations ENABLE ROW LEVEL SECURITY;
ALTER TABLE gsc_search_analytics ENABLE ROW LEVEL SECURITY;
ALTER TABLE gsc_indexing_status ENABLE ROW LEVEL SECURITY;

-- GA Configuration policies
CREATE POLICY "Users can view GA configs for their businesses" ON ga_configurations
    FOR SELECT USING (
        business_id IN (SELECT id FROM businesses WHERE user_id = (SELECT id FROM users WHERE auth.uid()::text = id::text))
        OR
        EXISTS (SELECT 1 FROM users WHERE auth.uid()::text = id::text AND role = 'admin')
    );

CREATE POLICY "System can manage GA configurations" ON ga_configurations
    FOR ALL USING (true);

-- GA Metrics policies
CREATE POLICY "Users can view GA metrics for their businesses" ON ga_metrics
    FOR SELECT USING (
        business_id IN (SELECT id FROM businesses WHERE user_id = (SELECT id FROM users WHERE auth.uid()::text = id::text))
        OR
        EXISTS (SELECT 1 FROM users WHERE auth.uid()::text = id::text AND role = 'admin')
    );

CREATE POLICY "System can manage GA metrics" ON ga_metrics
    FOR ALL USING (true);

-- GA Page Data policies
CREATE POLICY "Users can view GA page data for their businesses" ON ga_page_data
    FOR SELECT USING (
        business_id IN (SELECT id FROM businesses WHERE user_id = (SELECT id FROM users WHERE auth.uid()::text = id::text))
        OR
        EXISTS (SELECT 1 FROM users WHERE auth.uid()::text = id::text AND role = 'admin')
    );

CREATE POLICY "System can manage GA page data" ON ga_page_data
    FOR ALL USING (true);

-- GA Traffic Sources policies
CREATE POLICY "Users can view GA traffic sources for their businesses" ON ga_traffic_sources
    FOR SELECT USING (
        business_id IN (SELECT id FROM businesses WHERE user_id = (SELECT id FROM users WHERE auth.uid()::text = id::text))
        OR
        EXISTS (SELECT 1 FROM users WHERE auth.uid()::text = id::text AND role = 'admin')
    );

CREATE POLICY "System can manage GA traffic sources" ON ga_traffic_sources
    FOR ALL USING (true);

-- GA Goals policies
CREATE POLICY "Users can view GA goals for their businesses" ON ga_goals
    FOR SELECT USING (
        business_id IN (SELECT id FROM businesses WHERE user_id = (SELECT id FROM users WHERE auth.uid()::text = id::text))
        OR
        EXISTS (SELECT 1 FROM users WHERE auth.uid()::text = id::text AND role = 'admin')
    );

CREATE POLICY "System can manage GA goals" ON ga_goals
    FOR ALL USING (true);

-- GSC Configuration policies
CREATE POLICY "Users can view GSC configs for their businesses" ON gsc_configurations
    FOR SELECT USING (
        business_id IN (SELECT id FROM businesses WHERE user_id = (SELECT id FROM users WHERE auth.uid()::text = id::text))
        OR
        EXISTS (SELECT 1 FROM users WHERE auth.uid()::text = id::text AND role = 'admin')
    );

CREATE POLICY "System can manage GSC configurations" ON gsc_configurations
    FOR ALL USING (true);

-- GSC Search Analytics policies
CREATE POLICY "Users can view GSC analytics for their businesses" ON gsc_search_analytics
    FOR SELECT USING (
        business_id IN (SELECT id FROM businesses WHERE user_id = (SELECT id FROM users WHERE auth.uid()::text = id::text))
        OR
        EXISTS (SELECT 1 FROM users WHERE auth.uid()::text = id::text AND role = 'admin')
    );

CREATE POLICY "System can manage GSC analytics" ON gsc_search_analytics
    FOR ALL USING (true);

-- GSC Indexing Status policies
CREATE POLICY "Users can view GSC indexing for their businesses" ON gsc_indexing_status
    FOR SELECT USING (
        business_id IN (SELECT id FROM businesses WHERE user_id = (SELECT id FROM users WHERE auth.uid()::text = id::text))
        OR
        EXISTS (SELECT 1 FROM users WHERE auth.uid()::text = id::text AND role = 'admin')
    );

CREATE POLICY "System can manage GSC indexing" ON gsc_indexing_status
    FOR ALL USING (true);

-- ================================
-- AUTOMATED REPORTING TABLES
-- ================================

-- SEO Reports
CREATE TABLE IF NOT EXISTS seo_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id BIGINT NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
    campaign_id UUID REFERENCES seo_campaigns(id) ON DELETE SET NULL,
    report_type VARCHAR(50) NOT NULL CHECK (report_type IN ('weekly', 'monthly', 'quarterly', 'custom')),
    report_data JSONB NOT NULL,
    date_range_start DATE NOT NULL,
    date_range_end DATE NOT NULL,
    format VARCHAR(20) DEFAULT 'json' CHECK (format IN ('json', 'html', 'pdf')),
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'generating', 'completed', 'failed')),
    generated_at TIMESTAMPTZ DEFAULT NOW(),
    scheduled_delivery TIMESTAMPTZ,
    delivery_method VARCHAR(20) DEFAULT 'api' CHECK (delivery_method IN ('api', 'email', 'webhook')),
    recipients TEXT[], -- Email addresses for delivery
    error_message TEXT,
    file_path TEXT, -- For PDF/HTML files
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Report Schedules
CREATE TABLE IF NOT EXISTS report_schedules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id BIGINT NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
    campaign_id UUID REFERENCES seo_campaigns(id) ON DELETE SET NULL,
    schedule_name VARCHAR(200) NOT NULL,
    report_type VARCHAR(50) NOT NULL CHECK (report_type IN ('weekly', 'monthly', 'quarterly')),
    frequency VARCHAR(20) NOT NULL CHECK (frequency IN ('weekly', 'monthly', 'quarterly')),
    day_of_week INTEGER CHECK (day_of_week >= 0 AND day_of_week <= 6), -- 0 = Sunday
    day_of_month INTEGER CHECK (day_of_month >= 1 AND day_of_month <= 31),
    time_of_day TIME DEFAULT '09:00:00',
    timezone VARCHAR(50) DEFAULT 'America/New_York',
    format VARCHAR(20) DEFAULT 'pdf' CHECK (format IN ('json', 'html', 'pdf')),
    delivery_method VARCHAR(20) DEFAULT 'email' CHECK (delivery_method IN ('email', 'webhook')),
    recipients TEXT[] NOT NULL,
    include_sections TEXT[] DEFAULT ARRAY['traffic', 'rankings', 'technical', 'content', 'conversions'],
    is_active BOOLEAN DEFAULT true,
    last_generated TIMESTAMPTZ,
    next_generation TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Report Templates
CREATE TABLE IF NOT EXISTS report_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    template_name VARCHAR(200) NOT NULL,
    description TEXT,
    template_type VARCHAR(50) NOT NULL CHECK (template_type IN ('executive', 'technical', 'content', 'comprehensive')),
    sections_config JSONB NOT NULL,
    styling_config JSONB,
    is_default BOOLEAN DEFAULT false,
    is_public BOOLEAN DEFAULT true,
    created_by_business_id BIGINT REFERENCES businesses(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for reports
CREATE INDEX IF NOT EXISTS idx_seo_reports_business_date ON seo_reports(business_id, generated_at);
CREATE INDEX IF NOT EXISTS idx_seo_reports_status ON seo_reports(status);
CREATE INDEX IF NOT EXISTS idx_report_schedules_business_active ON report_schedules(business_id, is_active);
CREATE INDEX IF NOT EXISTS idx_report_schedules_next_generation ON report_schedules(next_generation) WHERE is_active = true;

-- Row Level Security for reports
ALTER TABLE seo_reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE report_schedules ENABLE ROW LEVEL SECURITY;
ALTER TABLE report_templates ENABLE ROW LEVEL SECURITY;

-- Reports policies
CREATE POLICY "Users can view reports for their businesses" ON seo_reports
    FOR SELECT USING (
        business_id IN (SELECT id FROM businesses WHERE user_id = (SELECT id FROM users WHERE auth.uid()::text = id::text))
        OR
        EXISTS (SELECT 1 FROM users WHERE auth.uid()::text = id::text AND role = 'admin')
    );

CREATE POLICY "System can manage reports" ON seo_reports
    FOR ALL USING (true);

-- Report schedules policies
CREATE POLICY "Users can view schedules for their businesses" ON report_schedules
    FOR SELECT USING (
        business_id IN (SELECT id FROM businesses WHERE user_id = (SELECT id FROM users WHERE auth.uid()::text = id::text))
        OR
        EXISTS (SELECT 1 FROM users WHERE auth.uid()::text = id::text AND role = 'admin')
    );

CREATE POLICY "Users can manage schedules for their businesses" ON report_schedules
    FOR ALL USING (
        business_id IN (SELECT id FROM businesses WHERE user_id = (SELECT id FROM users WHERE auth.uid()::text = id::text))
        OR
        EXISTS (SELECT 1 FROM users WHERE auth.uid()::text = id::text AND role = 'admin')
    );

-- Report templates policies
CREATE POLICY "Users can view public templates and their own" ON report_templates
    FOR SELECT USING (
        is_public = true
        OR
        created_by_business_id IN (SELECT id FROM businesses WHERE user_id = (SELECT id FROM users WHERE auth.uid()::text = id::text))
        OR
        EXISTS (SELECT 1 FROM users WHERE auth.uid()::text = id::text AND role = 'admin')
    );

CREATE POLICY "Users can manage their own templates" ON report_templates
    FOR ALL USING (
        created_by_business_id IN (SELECT id FROM businesses WHERE user_id = (SELECT id FROM users WHERE auth.uid()::text = id::text))
        OR
        EXISTS (SELECT 1 FROM users WHERE auth.uid()::text = id::text AND role = 'admin')
    );

-- ================================
-- WEBHOOK NOTIFICATIONS TABLES
-- ================================

-- Webhook Configurations
CREATE TABLE IF NOT EXISTS webhook_configurations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id BIGINT NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
    name VARCHAR(200) NOT NULL,
    webhook_type VARCHAR(50) NOT NULL CHECK (webhook_type IN ('slack', 'discord', 'teams', 'email', 'custom')),
    webhook_url TEXT,
    email_config JSONB,
    slack_config JSONB,
    discord_config JSONB,
    teams_config JSONB,
    trigger_events TEXT[] NOT NULL,
    filters JSONB,
    is_active BOOLEAN DEFAULT true,
    last_used TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(business_id, name)
);

-- Webhook Delivery Log
CREATE TABLE IF NOT EXISTS webhook_deliveries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id BIGINT NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
    webhook_configuration_id UUID REFERENCES webhook_configurations(id) ON DELETE CASCADE,
    event_type VARCHAR(100) NOT NULL,
    notification_data JSONB NOT NULL,
    delivery_status VARCHAR(20) NOT NULL CHECK (delivery_status IN ('success', 'failed', 'pending', 'retry')),
    http_status_code INTEGER,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    delivered_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Third-party Integration Configurations
CREATE TABLE IF NOT EXISTS integration_configurations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id BIGINT NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
    integration_type VARCHAR(50) NOT NULL CHECK (integration_type IN ('zapier', 'google_sheets', 'airtable', 'notion', 'hubspot', 'salesforce')),
    integration_name VARCHAR(200) NOT NULL,
    api_credentials JSONB NOT NULL, -- Encrypted credentials
    configuration JSONB NOT NULL,
    sync_frequency VARCHAR(20) DEFAULT 'daily' CHECK (sync_frequency IN ('realtime', 'hourly', 'daily', 'weekly')),
    last_sync TIMESTAMPTZ,
    sync_status VARCHAR(20) DEFAULT 'active' CHECK (sync_status IN ('active', 'paused', 'error')),
    error_details TEXT,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(business_id, integration_name)
);

-- Integration Sync Log
CREATE TABLE IF NOT EXISTS integration_sync_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id BIGINT NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
    integration_configuration_id UUID REFERENCES integration_configurations(id) ON DELETE CASCADE,
    sync_type VARCHAR(50) NOT NULL,
    data_synced JSONB,
    records_processed INTEGER DEFAULT 0,
    records_successful INTEGER DEFAULT 0,
    records_failed INTEGER DEFAULT 0,
    sync_status VARCHAR(20) NOT NULL CHECK (sync_status IN ('success', 'partial', 'failed')),
    error_details TEXT,
    started_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for webhooks and integrations
CREATE INDEX IF NOT EXISTS idx_webhook_configs_business_active ON webhook_configurations(business_id, is_active);
CREATE INDEX IF NOT EXISTS idx_webhook_deliveries_status ON webhook_deliveries(delivery_status, created_at);
CREATE INDEX IF NOT EXISTS idx_webhook_deliveries_business ON webhook_deliveries(business_id, created_at);
CREATE INDEX IF NOT EXISTS idx_integration_configs_business_active ON integration_configurations(business_id, is_active);
CREATE INDEX IF NOT EXISTS idx_integration_sync_log_business ON integration_sync_log(business_id, started_at);

-- Row Level Security for webhooks and integrations
ALTER TABLE webhook_configurations ENABLE ROW LEVEL SECURITY;
ALTER TABLE webhook_deliveries ENABLE ROW LEVEL SECURITY;
ALTER TABLE integration_configurations ENABLE ROW LEVEL SECURITY;
ALTER TABLE integration_sync_log ENABLE ROW LEVEL SECURITY;

-- Webhook configurations policies
CREATE POLICY "Users can view webhook configs for their businesses" ON webhook_configurations
    FOR SELECT USING (
        business_id IN (SELECT id FROM businesses WHERE user_id = (SELECT id FROM users WHERE auth.uid()::text = id::text))
        OR
        EXISTS (SELECT 1 FROM users WHERE auth.uid()::text = id::text AND role = 'admin')
    );

CREATE POLICY "Users can manage webhook configs for their businesses" ON webhook_configurations
    FOR ALL USING (
        business_id IN (SELECT id FROM businesses WHERE user_id = (SELECT id FROM users WHERE auth.uid()::text = id::text))
        OR
        EXISTS (SELECT 1 FROM users WHERE auth.uid()::text = id::text AND role = 'admin')
    );

-- Webhook deliveries policies
CREATE POLICY "Users can view webhook deliveries for their businesses" ON webhook_deliveries
    FOR SELECT USING (
        business_id IN (SELECT id FROM businesses WHERE user_id = (SELECT id FROM users WHERE auth.uid()::text = id::text))
        OR
        EXISTS (SELECT 1 FROM users WHERE auth.uid()::text = id::text AND role = 'admin')
    );

CREATE POLICY "System can manage webhook deliveries" ON webhook_deliveries
    FOR ALL USING (true);

-- Integration configurations policies
CREATE POLICY "Users can view integration configs for their businesses" ON integration_configurations
    FOR SELECT USING (
        business_id IN (SELECT id FROM businesses WHERE user_id = (SELECT id FROM users WHERE auth.uid()::text = id::text))
        OR
        EXISTS (SELECT 1 FROM users WHERE auth.uid()::text = id::text AND role = 'admin')
    );

CREATE POLICY "Users can manage integration configs for their businesses" ON integration_configurations
    FOR ALL USING (
        business_id IN (SELECT id FROM businesses WHERE user_id = (SELECT id FROM users WHERE auth.uid()::text = id::text))
        OR
        EXISTS (SELECT 1 FROM users WHERE auth.uid()::text = id::text AND role = 'admin')
    );

-- Integration sync log policies
CREATE POLICY "Users can view integration sync logs for their businesses" ON integration_sync_log
    FOR SELECT USING (
        business_id IN (SELECT id FROM businesses WHERE user_id = (SELECT id FROM users WHERE auth.uid()::text = id::text))
        OR
        EXISTS (SELECT 1 FROM users WHERE auth.uid()::text = id::text AND role = 'admin')
    );

CREATE POLICY "System can manage integration sync logs" ON integration_sync_log
    FOR ALL USING (true);

-- ================================
-- AI & MACHINE LEARNING TABLES
-- ================================

-- AI Optimizations
CREATE TABLE IF NOT EXISTS ai_optimizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id BIGINT NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
    campaign_id UUID REFERENCES seo_campaigns(id) ON DELETE SET NULL,
    optimization_type VARCHAR(50) NOT NULL CHECK (optimization_type IN ('content', 'meta_tags', 'readability', 'keywords', 'semantic_analysis')),
    original_content TEXT,
    optimized_content TEXT,
    improvements JSONB,
    metrics_before JSONB,
    metrics_after JSONB,
    analysis_results JSONB,
    ai_confidence DECIMAL(3,2) DEFAULT 0.50,
    applied BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    applied_at TIMESTAMPTZ
);

-- AI Predictions
CREATE TABLE IF NOT EXISTS ai_predictions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id BIGINT NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
    campaign_id UUID REFERENCES seo_campaigns(id) ON DELETE SET NULL,
    prediction_type VARCHAR(50) NOT NULL CHECK (prediction_type IN ('ranking', 'traffic', 'opportunity', 'risk', 'trend')),
    predictions JSONB NOT NULL,
    horizon_days INTEGER DEFAULT 90,
    scenario VARCHAR(20) DEFAULT 'realistic' CHECK (scenario IN ('optimistic', 'realistic', 'pessimistic')),
    confidence_avg DECIMAL(3,2) DEFAULT 0.50,
    accuracy_score DECIMAL(3,2), -- Calculated after prediction period
    created_at TIMESTAMPTZ DEFAULT NOW(),
    evaluated_at TIMESTAMPTZ
);

-- A/B Testing Framework
CREATE TABLE IF NOT EXISTS ab_tests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id BIGINT NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
    campaign_id UUID REFERENCES seo_campaigns(id) ON DELETE SET NULL,
    test_name VARCHAR(200) NOT NULL,
    test_type VARCHAR(50) NOT NULL CHECK (test_type IN ('content', 'title', 'meta', 'cta', 'layout')),
    variant_a JSONB NOT NULL,
    variant_b JSONB NOT NULL,
    metrics_tracked TEXT[] DEFAULT ARRAY['clicks', 'impressions', 'ctr', 'conversions'],
    traffic_split DECIMAL(3,2) DEFAULT 0.50 CHECK (traffic_split >= 0 AND traffic_split <= 1),
    status VARCHAR(20) DEFAULT 'draft' CHECK (status IN ('draft', 'running', 'paused', 'completed', 'cancelled')),
    winner VARCHAR(1) CHECK (winner IN ('A', 'B')),
    statistical_significance DECIMAL(3,2),
    started_at TIMESTAMPTZ,
    ended_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- A/B Test Results
CREATE TABLE IF NOT EXISTS ab_test_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ab_test_id UUID NOT NULL REFERENCES ab_tests(id) ON DELETE CASCADE,
    variant VARCHAR(1) NOT NULL CHECK (variant IN ('A', 'B')),
    date DATE NOT NULL,
    impressions INTEGER DEFAULT 0,
    clicks INTEGER DEFAULT 0,
    conversions INTEGER DEFAULT 0,
    ctr DECIMAL(8,4) DEFAULT 0,
    conversion_rate DECIMAL(8,4) DEFAULT 0,
    bounce_rate DECIMAL(8,4) DEFAULT 0,
    avg_time_on_page DECIMAL(10,2) DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(ab_test_id, variant, date)
);

-- Machine Learning Models
CREATE TABLE IF NOT EXISTS ml_models (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_name VARCHAR(200) NOT NULL,
    model_type VARCHAR(50) NOT NULL CHECK (model_type IN ('ranking_predictor', 'traffic_forecaster', 'content_scorer', 'keyword_classifier')),
    model_version VARCHAR(20) NOT NULL,
    training_data JSONB,
    model_parameters JSONB,
    accuracy_metrics JSONB,
    is_active BOOLEAN DEFAULT false,
    trained_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(model_name, model_version)
);

-- Model Training History
CREATE TABLE IF NOT EXISTS ml_training_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ml_model_id UUID NOT NULL REFERENCES ml_models(id) ON DELETE CASCADE,
    business_id BIGINT REFERENCES businesses(id) ON DELETE SET NULL,
    training_status VARCHAR(20) NOT NULL CHECK (training_status IN ('started', 'in_progress', 'completed', 'failed')),
    data_points_used INTEGER DEFAULT 0,
    training_duration_seconds INTEGER,
    accuracy_score DECIMAL(3,2),
    loss_score DECIMAL(10,6),
    validation_metrics JSONB,
    error_details TEXT,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

-- Create indexes for AI tables
CREATE INDEX IF NOT EXISTS idx_ai_optimizations_business ON ai_optimizations(business_id, created_at);
CREATE INDEX IF NOT EXISTS idx_ai_optimizations_type ON ai_optimizations(optimization_type, applied);
CREATE INDEX IF NOT EXISTS idx_ai_predictions_business ON ai_predictions(business_id, prediction_type);
CREATE INDEX IF NOT EXISTS idx_ai_predictions_created ON ai_predictions(created_at);
CREATE INDEX IF NOT EXISTS idx_ab_tests_business_status ON ab_tests(business_id, status);
CREATE INDEX IF NOT EXISTS idx_ab_test_results_test_variant ON ab_test_results(ab_test_id, variant);
CREATE INDEX IF NOT EXISTS idx_ml_models_active ON ml_models(is_active, model_type);

-- Row Level Security for AI tables
ALTER TABLE ai_optimizations ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_predictions ENABLE ROW LEVEL SECURITY;
ALTER TABLE ab_tests ENABLE ROW LEVEL SECURITY;
ALTER TABLE ab_test_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE ml_models ENABLE ROW LEVEL SECURITY;
ALTER TABLE ml_training_history ENABLE ROW LEVEL SECURITY;

-- AI Optimizations policies
CREATE POLICY "Users can view AI optimizations for their businesses" ON ai_optimizations
    FOR SELECT USING (
        business_id IN (SELECT id FROM businesses WHERE user_id = (SELECT id FROM users WHERE auth.uid()::text = id::text))
        OR
        EXISTS (SELECT 1 FROM users WHERE auth.uid()::text = id::text AND role = 'admin')
    );

CREATE POLICY "System can manage AI optimizations" ON ai_optimizations
    FOR ALL USING (true);

-- AI Predictions policies
CREATE POLICY "Users can view AI predictions for their businesses" ON ai_predictions
    FOR SELECT USING (
        business_id IN (SELECT id FROM businesses WHERE user_id = (SELECT id FROM users WHERE auth.uid()::text = id::text))
        OR
        EXISTS (SELECT 1 FROM users WHERE auth.uid()::text = id::text AND role = 'admin')
    );

CREATE POLICY "System can manage AI predictions" ON ai_predictions
    FOR ALL USING (true);

-- A/B Tests policies
CREATE POLICY "Users can view A/B tests for their businesses" ON ab_tests
    FOR SELECT USING (
        business_id IN (SELECT id FROM businesses WHERE user_id = (SELECT id FROM users WHERE auth.uid()::text = id::text))
        OR
        EXISTS (SELECT 1 FROM users WHERE auth.uid()::text = id::text AND role = 'admin')
    );

CREATE POLICY "Users can manage A/B tests for their businesses" ON ab_tests
    FOR ALL USING (
        business_id IN (SELECT id FROM businesses WHERE user_id = (SELECT id FROM users WHERE auth.uid()::text = id::text))
        OR
        EXISTS (SELECT 1 FROM users WHERE auth.uid()::text = id::text AND role = 'admin')
    );

-- A/B Test Results policies
CREATE POLICY "Users can view A/B test results" ON ab_test_results
    FOR SELECT USING (
        ab_test_id IN (
            SELECT id FROM ab_tests WHERE business_id IN (
                SELECT id FROM businesses WHERE user_id = (SELECT id FROM users WHERE auth.uid()::text = id::text)
            )
        )
        OR
        EXISTS (SELECT 1 FROM users WHERE auth.uid()::text = id::text AND role = 'admin')
    );

CREATE POLICY "System can manage A/B test results" ON ab_test_results
    FOR ALL USING (true);

-- ML Models policies
CREATE POLICY "All users can view active ML models" ON ml_models
    FOR SELECT USING (is_active = true);

CREATE POLICY "System can manage ML models" ON ml_models
    FOR ALL USING (true);

-- ML Training History policies
CREATE POLICY "Users can view training history for their data" ON ml_training_history
    FOR SELECT USING (
        business_id IN (SELECT id FROM businesses WHERE user_id = (SELECT id FROM users WHERE auth.uid()::text = id::text))
        OR
        business_id IS NULL
        OR
        EXISTS (SELECT 1 FROM users WHERE auth.uid()::text = id::text AND role = 'admin')
    );

CREATE POLICY "System can manage ML training history" ON ml_training_history
    FOR ALL USING (true);

-- ================================
-- UTILITY FUNCTIONS
-- ================================

-- Function to create a new SEO campaign
CREATE OR REPLACE FUNCTION create_seo_campaign(
    p_business_id BIGINT,
    p_name VARCHAR(200),
    p_description TEXT DEFAULT NULL,
    p_seed_keywords TEXT[] DEFAULT '{}',
    p_competitors TEXT[] DEFAULT '{}'
) RETURNS UUID AS $$
DECLARE
    campaign_id UUID;
BEGIN
    INSERT INTO seo_campaigns (
        business_id, 
        name, 
        description, 
        seed_keywords, 
        competitors
    ) VALUES (
        p_business_id,
        p_name,
        p_description,
        p_seed_keywords,
        p_competitors
    ) RETURNING id INTO campaign_id;
    
    -- Log the campaign creation
    INSERT INTO seo_logs (
        business_id,
        action_type,
        action_description,
        new_data
    ) VALUES (
        p_business_id,
        'campaign_created',
        'New SEO campaign created: ' || p_name,
        jsonb_build_object('campaign_id', campaign_id, 'campaign_name', p_name)
    );
    
    RETURN campaign_id;
END;
$$ LANGUAGE plpgsql;

-- Function to get campaign overview
CREATE OR REPLACE FUNCTION get_campaign_overview(p_campaign_id UUID)
RETURNS JSONB AS $$
DECLARE
    result JSONB;
BEGIN
    SELECT jsonb_build_object(
        'campaign_id', sc.id,
        'name', sc.name,
        'status', sc.status,
        'created_at', sc.created_at,
        'business_name', b.business_name,
        'total_keywords', COALESCE(kw.keyword_count, 0),
        'clusters', COALESCE(cl.cluster_count, 0),
        'content_briefs', COALESCE(cb.brief_count, 0),
        'published_content', COALESCE(cp.published_count, 0),
        'avg_keyword_rank', COALESCE(kw.avg_rank, 0),
        'total_organic_traffic', COALESCE(cp.total_traffic, 0),
        'recent_performance', cp.recent_performance
    ) INTO result
    FROM seo_campaigns sc
    JOIN businesses b ON sc.business_id = b.id
    LEFT JOIN (
        SELECT 
            campaign_id,
            COUNT(*) as keyword_count,
            AVG(current_rank) as avg_rank
        FROM keywords 
        WHERE campaign_id = p_campaign_id 
        GROUP BY campaign_id
    ) kw ON sc.id = kw.campaign_id
    LEFT JOIN (
        SELECT 
            campaign_id,
            COUNT(*) as cluster_count
        FROM keyword_clusters 
        WHERE campaign_id = p_campaign_id 
        GROUP BY campaign_id
    ) cl ON sc.id = cl.campaign_id
    LEFT JOIN (
        SELECT 
            campaign_id,
            COUNT(*) as brief_count
        FROM content_briefs 
        WHERE campaign_id = p_campaign_id 
        GROUP BY campaign_id
    ) cb ON sc.id = cb.campaign_id
    LEFT JOIN (
        SELECT 
            campaign_id,
            COUNT(*) FILTER (WHERE publish_date IS NOT NULL) as published_count,
            SUM(organic_traffic) as total_traffic,
            jsonb_agg(
                jsonb_build_object(
                    'url', url,
                    'traffic', organic_traffic,
                    'keywords', top_10_keywords
                ) ORDER BY organic_traffic DESC
            ) FILTER (WHERE organic_traffic > 0) as recent_performance
        FROM content_performance 
        WHERE campaign_id = p_campaign_id 
        GROUP BY campaign_id
    ) cp ON sc.id = cp.campaign_id
    WHERE sc.id = p_campaign_id;
    
    RETURN result;
END;
$$ LANGUAGE plpgsql;

-- ================================
-- PHASE 3: AUTOMATION & SCHEDULING TABLES
-- ================================

-- Automation Rules table - Define conditional automation
CREATE TABLE IF NOT EXISTS automation_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id BIGINT NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
    
    -- Rule Details
    name VARCHAR(200) NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT true,
    
    -- Trigger Conditions
    trigger_conditions JSONB NOT NULL, -- What conditions trigger this rule
    
    -- Actions to Execute
    actions JSONB NOT NULL, -- Array of tasks to execute when triggered
    
    -- Execution Tracking
    last_triggered TIMESTAMPTZ,
    trigger_count INTEGER DEFAULT 0,
    
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Task Execution History table - Detailed execution logs
CREATE TABLE IF NOT EXISTS task_execution_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID NOT NULL REFERENCES seo_tasks(id) ON DELETE CASCADE,
    business_id BIGINT NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
    
    -- Execution Details
    execution_start TIMESTAMPTZ NOT NULL,
    execution_end TIMESTAMPTZ,
    execution_duration_ms INTEGER,
    status VARCHAR(20) NOT NULL, -- completed, failed, timeout
    
    -- Results and Metrics
    function_called VARCHAR(100),
    input_data JSONB,
    output_data JSONB,
    error_details TEXT,
    performance_metrics JSONB,
    
    -- Resource Usage
    memory_used_mb DECIMAL(10,2),
    cpu_time_ms INTEGER,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT check_execution_status CHECK (status IN (
        'completed', 'failed', 'timeout', 'cancelled'
    ))
);

-- Rank Tracking table - Historical keyword position data
CREATE TABLE IF NOT EXISTS rank_tracking (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id BIGINT NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
    campaign_id UUID REFERENCES seo_campaigns(id) ON DELETE CASCADE,
    
    -- Keyword and Position Data
    keyword VARCHAR(255) NOT NULL,
    position INTEGER NOT NULL CHECK (position >= 1),
    previous_position INTEGER,
    change INTEGER DEFAULT 0, -- Calculated position change
    url TEXT NOT NULL,
    
    -- Search Context
    search_engine VARCHAR(20) DEFAULT 'google',
    device VARCHAR(20) DEFAULT 'desktop', -- desktop, mobile
    location VARCHAR(100) DEFAULT 'United States',
    
    -- SERP Features
    serp_features JSONB DEFAULT '[]',
    competitor_data JSONB DEFAULT '[]',
    local_pack_position INTEGER,
    featured_snippet BOOLEAN DEFAULT false,
    
    -- Tracking Metadata
    tracked_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT check_search_engine CHECK (search_engine IN (
        'google', 'bing', 'yahoo'
    )),
    CONSTRAINT check_device CHECK (device IN (
        'desktop', 'mobile'
    ))
);

-- Competitor Analysis table - Store competitor intelligence
CREATE TABLE IF NOT EXISTS competitor_analysis (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id BIGINT NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
    campaign_id UUID REFERENCES seo_campaigns(id) ON DELETE CASCADE,
    
    -- Analysis Configuration
    competitors_analyzed TEXT[] NOT NULL,
    analysis_depth VARCHAR(20) DEFAULT 'detailed',
    focus_areas TEXT[] DEFAULT ARRAY['keywords', 'content', 'technical', 'local'],
    
    -- Competitive Intelligence Data
    domain_authority_data JSONB,
    traffic_data JSONB,
    keyword_overlap JSONB,
    competitive_gaps JSONB,
    recommendations JSONB,
    
    -- Analysis Metadata
    analysis_date TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ DEFAULT (NOW() + INTERVAL '30 days'),
    
    CONSTRAINT check_analysis_depth CHECK (analysis_depth IN (
        'basic', 'detailed', 'comprehensive'
    ))
);

-- Alert Configurations table - Define alert thresholds and rules
CREATE TABLE IF NOT EXISTS alert_configurations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id BIGINT NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
    
    -- Alert Type and Settings
    alert_type VARCHAR(50) NOT NULL, -- ranking_drop, traffic_drop, technical_issues, etc.
    thresholds JSONB NOT NULL, -- Threshold values for triggering alerts
    frequency VARCHAR(20) DEFAULT 'daily', -- real_time, hourly, daily, weekly
    severity_rules JSONB DEFAULT '{}', -- Rules for determining alert severity
    
    -- Notification Settings
    notification_channels TEXT[] DEFAULT ARRAY['email'], -- email, webhook, slack, sms
    webhook_url TEXT,
    email_recipients TEXT[],
    
    -- Status
    is_active BOOLEAN DEFAULT true,
    
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Unique constraint to prevent duplicate configs
    UNIQUE(business_id, alert_type),
    
    CONSTRAINT check_alert_frequency CHECK (frequency IN (
        'real_time', 'hourly', 'daily', 'weekly'
    ))
);

-- Monitoring Alerts table - Real-time alert system
CREATE TABLE IF NOT EXISTS monitoring_alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id BIGINT NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
    campaign_id UUID REFERENCES seo_campaigns(id) ON DELETE CASCADE,
    
    -- Alert Details
    alert_type VARCHAR(50) NOT NULL, -- ranking_drop, traffic_spike, new_competitor, etc.
    severity VARCHAR(20) DEFAULT 'medium', -- low, medium, high, critical
    title VARCHAR(200) NOT NULL,
    message TEXT NOT NULL,
    
    -- Alert Data
    trigger_data JSONB, -- What triggered this alert
    threshold_config JSONB, -- Alert thresholds
    current_value DECIMAL(15,2),
    previous_value DECIMAL(15,2),
    percentage_change DECIMAL(10,2),
    
    -- Status and Actions
    status VARCHAR(20) DEFAULT 'active', -- active, acknowledged, resolved, false_positive
    acknowledged_by VARCHAR(100),
    acknowledged_at TIMESTAMPTZ,
    resolved_at TIMESTAMPTZ,
    actions_taken TEXT,
    
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT check_severity CHECK (severity IN (
        'low', 'medium', 'high', 'critical'
    )),
    CONSTRAINT check_alert_status CHECK (status IN (
        'active', 'acknowledged', 'resolved', 'false_positive'
    ))
);

-- ================================
-- INDEXES FOR PHASE 3 TABLES
-- ================================

-- Alert Configurations indexes
CREATE INDEX IF NOT EXISTS idx_alert_configurations_business_id ON alert_configurations(business_id);
CREATE INDEX IF NOT EXISTS idx_alert_configurations_alert_type ON alert_configurations(alert_type);
CREATE INDEX IF NOT EXISTS idx_alert_configurations_active ON alert_configurations(is_active);

-- Automation Rules indexes
CREATE INDEX IF NOT EXISTS idx_automation_rules_business_id ON automation_rules(business_id);
CREATE INDEX IF NOT EXISTS idx_automation_rules_active ON automation_rules(is_active);

-- Task Execution History indexes  
CREATE INDEX IF NOT EXISTS idx_task_execution_history_task_id ON task_execution_history(task_id);
CREATE INDEX IF NOT EXISTS idx_task_execution_history_business_id ON task_execution_history(business_id);
CREATE INDEX IF NOT EXISTS idx_task_execution_history_execution_start ON task_execution_history(execution_start);

-- Rank Tracking indexes
CREATE INDEX IF NOT EXISTS idx_rank_tracking_business_id ON rank_tracking(business_id);
CREATE INDEX IF NOT EXISTS idx_rank_tracking_campaign_id ON rank_tracking(campaign_id);
CREATE INDEX IF NOT EXISTS idx_rank_tracking_keyword ON rank_tracking(keyword);
CREATE INDEX IF NOT EXISTS idx_rank_tracking_tracked_at ON rank_tracking(tracked_at);

-- Competitor Analysis indexes
CREATE INDEX IF NOT EXISTS idx_competitor_analysis_business_id ON competitor_analysis(business_id);
CREATE INDEX IF NOT EXISTS idx_competitor_analysis_campaign_id ON competitor_analysis(campaign_id);
CREATE INDEX IF NOT EXISTS idx_competitor_analysis_date ON competitor_analysis(analysis_date);

-- Monitoring Alerts indexes
CREATE INDEX IF NOT EXISTS idx_monitoring_alerts_business_id ON monitoring_alerts(business_id);
CREATE INDEX IF NOT EXISTS idx_monitoring_alerts_campaign_id ON monitoring_alerts(campaign_id);
CREATE INDEX IF NOT EXISTS idx_monitoring_alerts_status ON monitoring_alerts(status);
CREATE INDEX IF NOT EXISTS idx_monitoring_alerts_severity ON monitoring_alerts(severity);
CREATE INDEX IF NOT EXISTS idx_monitoring_alerts_created_at ON monitoring_alerts(created_at);

-- ================================
-- ROW LEVEL SECURITY FOR PHASE 3 TABLES
-- ================================

-- Enable RLS on new tables
ALTER TABLE alert_configurations ENABLE ROW LEVEL SECURITY;
ALTER TABLE automation_rules ENABLE ROW LEVEL SECURITY;
ALTER TABLE task_execution_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE rank_tracking ENABLE ROW LEVEL SECURITY;
ALTER TABLE competitor_analysis ENABLE ROW LEVEL SECURITY;
ALTER TABLE monitoring_alerts ENABLE ROW LEVEL SECURITY;

-- Alert Configurations policies
CREATE POLICY "Users can manage alert configurations for their businesses" ON alert_configurations
    FOR ALL USING (
        business_id IN (SELECT id FROM businesses WHERE user_id = (SELECT id FROM users WHERE auth.uid()::text = id::text))
        OR
        EXISTS (SELECT 1 FROM users WHERE auth.uid()::text = id::text AND role = 'admin')
    );

-- Automation Rules policies
CREATE POLICY "Users can manage automation rules for their businesses" ON automation_rules
    FOR ALL USING (
        business_id IN (SELECT id FROM businesses WHERE user_id = (SELECT id FROM users WHERE auth.uid()::text = id::text))
        OR
        EXISTS (SELECT 1 FROM users WHERE auth.uid()::text = id::text AND role = 'admin')
    );

-- Task Execution History policies
CREATE POLICY "Users can view task execution history for their businesses" ON task_execution_history
    FOR SELECT USING (
        business_id IN (SELECT id FROM businesses WHERE user_id = (SELECT id FROM users WHERE auth.uid()::text = id::text))
        OR
        EXISTS (SELECT 1 FROM users WHERE auth.uid()::text = id::text AND role = 'admin')
    );

CREATE POLICY "System can manage task execution history" ON task_execution_history
    FOR ALL USING (true);

-- Rank Tracking policies
CREATE POLICY "Users can view rank tracking for their businesses" ON rank_tracking
    FOR SELECT USING (
        business_id IN (SELECT id FROM businesses WHERE user_id = (SELECT id FROM users WHERE auth.uid()::text = id::text))
        OR
        EXISTS (SELECT 1 FROM users WHERE auth.uid()::text = id::text AND role = 'admin')
    );

CREATE POLICY "System can manage rank tracking" ON rank_tracking
    FOR ALL USING (true);

-- Competitor Analysis policies
CREATE POLICY "Users can view competitor analysis for their businesses" ON competitor_analysis
    FOR SELECT USING (
        business_id IN (SELECT id FROM businesses WHERE user_id = (SELECT id FROM users WHERE auth.uid()::text = id::text))
        OR
        EXISTS (SELECT 1 FROM users WHERE auth.uid()::text = id::text AND role = 'admin')
    );

CREATE POLICY "System can manage competitor analysis" ON competitor_analysis
    FOR ALL USING (true);

-- Monitoring Alerts policies
CREATE POLICY "Users can manage alerts for their businesses" ON monitoring_alerts
    FOR ALL USING (
        business_id IN (SELECT id FROM businesses WHERE user_id = (SELECT id FROM users WHERE auth.uid()::text = id::text))
        OR
        EXISTS (SELECT 1 FROM users WHERE auth.uid()::text = id::text AND role = 'admin')
    );

-- ================================
-- CAMPAIGN MANAGEMENT TABLES
-- ================================

-- Campaigns table for managing SEO campaigns
CREATE TABLE IF NOT EXISTS campaigns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id BIGINT NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(50) DEFAULT 'draft' CHECK (status IN ('draft', 'active', 'paused', 'completed', 'deleted')),
    type VARCHAR(50) NOT NULL CHECK (type IN ('seo', 'content', 'link_building', 'technical', 'local', 'multi_channel')),
    goals JSONB,
    budget JSONB,
    settings JSONB,
    performance JSONB,
    created_by BIGINT REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

-- Campaign tasks for tracking work items
CREATE TABLE IF NOT EXISTS campaign_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id UUID REFERENCES campaigns(id) ON DELETE CASCADE,
    task_type VARCHAR(100) NOT NULL,
    status VARCHAR(50) DEFAULT 'pending' CHECK (status IN ('pending', 'in_progress', 'completed', 'failed')),
    priority VARCHAR(20) DEFAULT 'medium' CHECK (priority IN ('low', 'medium', 'high', 'critical')),
    assigned_to BIGINT REFERENCES users(id),
    due_date TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    details JSONB,
    results JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Campaign keywords mapping
CREATE TABLE IF NOT EXISTS campaign_keywords (
    campaign_id UUID REFERENCES campaigns(id) ON DELETE CASCADE,
    keyword_id BIGINT REFERENCES keywords(id) ON DELETE CASCADE,
    target_position INTEGER,
    current_position INTEGER,
    priority INTEGER DEFAULT 0,
    strategy TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (campaign_id, keyword_id)
);

-- Campaign content tracking
CREATE TABLE IF NOT EXISTS campaign_content (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id UUID REFERENCES campaigns(id) ON DELETE CASCADE,
    content_brief_id BIGINT REFERENCES content_briefs(id),
    title VARCHAR(255),
    url TEXT,
    status VARCHAR(50),
    performance JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Campaign competitors tracking
CREATE TABLE IF NOT EXISTS campaign_competitors (
    campaign_id UUID REFERENCES campaigns(id) ON DELETE CASCADE,
    competitor_id BIGINT REFERENCES competitors(id) ON DELETE CASCADE,
    tracking_metrics JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (campaign_id, competitor_id)
);

-- ================================
-- USER MANAGEMENT TABLES
-- ================================

-- User preferences
CREATE TABLE IF NOT EXISTS user_preferences (
    user_id BIGINT REFERENCES users(id) ON DELETE CASCADE PRIMARY KEY,
    dashboard_layout TEXT,
    default_business_id BIGINT REFERENCES businesses(id),
    theme VARCHAR(20) DEFAULT 'light' CHECK (theme IN ('light', 'dark', 'auto')),
    date_format VARCHAR(50),
    currency VARCHAR(10) DEFAULT 'USD',
    metadata JSONB,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- User notification settings
CREATE TABLE IF NOT EXISTS user_notifications (
    user_id BIGINT REFERENCES users(id) ON DELETE CASCADE PRIMARY KEY,
    email BOOLEAN DEFAULT true,
    sms BOOLEAN DEFAULT false,
    push BOOLEAN DEFAULT true,
    frequency VARCHAR(20) DEFAULT 'daily' CHECK (frequency IN ('instant', 'daily', 'weekly')),
    types TEXT[],
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- User settings
CREATE TABLE IF NOT EXISTS user_settings (
    user_id BIGINT REFERENCES users(id) ON DELETE CASCADE PRIMARY KEY,
    api_keys JSONB, -- Encrypted
    integrations JSONB,
    limits JSONB,
    features JSONB,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Business permissions
CREATE TABLE IF NOT EXISTS business_permissions (
    user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
    business_id BIGINT REFERENCES businesses(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL CHECK (role IN ('owner', 'admin', 'editor', 'viewer')),
    permissions TEXT[],
    granted_by BIGINT REFERENCES users(id),
    granted_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (user_id, business_id)
);

-- Team invitations
CREATE TABLE IF NOT EXISTS invitations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id BIGINT REFERENCES businesses(id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL,
    role VARCHAR(50),
    permissions TEXT[],
    invited_by BIGINT REFERENCES users(id),
    status VARCHAR(50) DEFAULT 'pending' CHECK (status IN ('pending', 'accepted', 'declined', 'expired')),
    token UUID DEFAULT gen_random_uuid(),
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- User notifications
CREATE TABLE IF NOT EXISTS notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
    type VARCHAR(50) NOT NULL,
    title VARCHAR(255),
    message TEXT,
    data JSONB,
    read BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- API usage logs
CREATE TABLE IF NOT EXISTS api_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id BIGINT REFERENCES users(id),
    business_id BIGINT REFERENCES businesses(id),
    endpoint VARCHAR(255),
    method VARCHAR(10),
    status_code INTEGER,
    request_params JSONB,
    response_time_ms INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Subscriptions
CREATE TABLE IF NOT EXISTS subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id BIGINT REFERENCES businesses(id) ON DELETE CASCADE,
    plan VARCHAR(50) DEFAULT 'free' CHECK (plan IN ('free', 'starter', 'pro', 'enterprise')),
    status VARCHAR(50) DEFAULT 'active' CHECK (status IN ('active', 'trialing', 'past_due', 'canceled')),
    current_period_start TIMESTAMPTZ,
    current_period_end TIMESTAMPTZ,
    features TEXT[],
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Invoices
CREATE TABLE IF NOT EXISTS invoices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id BIGINT REFERENCES businesses(id) ON DELETE CASCADE,
    subscription_id UUID REFERENCES subscriptions(id),
    amount DECIMAL(10,2),
    currency VARCHAR(10) DEFAULT 'USD',
    status VARCHAR(50),
    due_date TIMESTAMPTZ,
    paid_at TIMESTAMPTZ,
    pdf_url TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_campaigns_business_status ON campaigns(business_id, status);
CREATE INDEX IF NOT EXISTS idx_campaign_tasks_campaign_status ON campaign_tasks(campaign_id, status);
CREATE INDEX IF NOT EXISTS idx_campaign_keywords_campaign ON campaign_keywords(campaign_id);
CREATE INDEX IF NOT EXISTS idx_notifications_user_read ON notifications(user_id, read);
CREATE INDEX IF NOT EXISTS idx_api_logs_user_time ON api_logs(user_id, created_at);
CREATE INDEX IF NOT EXISTS idx_subscriptions_business ON subscriptions(business_id);

-- Row Level Security policies for campaigns
CREATE POLICY "Users can manage campaigns for their businesses" ON campaigns
    FOR ALL USING (
        business_id IN (SELECT id FROM businesses WHERE user_id = (SELECT id FROM users WHERE auth.uid()::text = id::text))
        OR
        EXISTS (SELECT 1 FROM users WHERE auth.uid()::text = id::text AND role = 'admin')
    );

CREATE POLICY "Users can manage campaign tasks for their campaigns" ON campaign_tasks
    FOR ALL USING (
        campaign_id IN (
            SELECT c.id FROM campaigns c 
            JOIN businesses b ON c.business_id = b.id 
            WHERE b.user_id = (SELECT id FROM users WHERE auth.uid()::text = id::text)
        )
        OR
        EXISTS (SELECT 1 FROM users WHERE auth.uid()::text = id::text AND role = 'admin')
    );

CREATE POLICY "Users can view their preferences" ON user_preferences
    FOR ALL USING (
        user_id = (SELECT id FROM users WHERE auth.uid()::text = id::text)
        OR
        EXISTS (SELECT 1 FROM users WHERE auth.uid()::text = id::text AND role = 'admin')
    );

CREATE POLICY "Users can manage their notifications" ON notifications
    FOR ALL USING (
        user_id = (SELECT id FROM users WHERE auth.uid()::text = id::text)
        OR
        EXISTS (SELECT 1 FROM users WHERE auth.uid()::text = id::text AND role = 'admin')
    );

CREATE POLICY "Users can view their API logs" ON api_logs
    FOR SELECT USING (
        user_id = (SELECT id FROM users WHERE auth.uid()::text = id::text)
        OR
        business_id IN (SELECT id FROM businesses WHERE user_id = (SELECT id FROM users WHERE auth.uid()::text = id::text))
        OR
        EXISTS (SELECT 1 FROM users WHERE auth.uid()::text = id::text AND role = 'admin')
    );

-- Grant necessary permissions
GRANT USAGE ON SCHEMA public TO anon, authenticated;
GRANT ALL ON ALL TABLES IN SCHEMA public TO anon, authenticated;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO anon, authenticated;
GRANT ALL ON ALL FUNCTIONS IN SCHEMA public TO anon, authenticated;