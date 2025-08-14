-- Initial schema for SEO Bot application
-- Create all the tables needed for the SEO platform

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Projects table
CREATE TABLE IF NOT EXISTS projects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    domain VARCHAR(255) NOT NULL UNIQUE,
    base_url VARCHAR(500) NOT NULL,
    language VARCHAR(10) DEFAULT 'en',
    country VARCHAR(10) DEFAULT 'US',
    cms_type VARCHAR(50) DEFAULT 'markdown',
    status VARCHAR(50) DEFAULT 'active',
    config JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Clusters table
CREATE TABLE IF NOT EXISTS clusters (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(255) NOT NULL,
    cluster_type VARCHAR(50) DEFAULT 'hub',
    parent_cluster_id UUID REFERENCES clusters(id),
    priority_score REAL DEFAULT 0.0,
    estimated_traffic INTEGER DEFAULT 0,
    content_brief_created BOOLEAN DEFAULT FALSE,
    content_written BOOLEAN DEFAULT FALSE,
    content_published BOOLEAN DEFAULT FALSE,
    entities JSONB DEFAULT '[]',
    embedding_vector JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(project_id, slug)
);

-- Authors table
CREATE TABLE IF NOT EXISTS authors (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    bio TEXT,
    credentials JSONB DEFAULT '[]',
    expertise_areas JSONB DEFAULT '[]',
    photo_url VARCHAR(500),
    linkedin_url VARCHAR(500),
    twitter_url VARCHAR(500),
    website_url VARCHAR(500),
    articles_written INTEGER DEFAULT 0,
    avg_quality_score REAL DEFAULT 0.0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(project_id, slug)
);

-- Keywords table
CREATE TABLE IF NOT EXISTS keywords (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    cluster_id UUID REFERENCES clusters(id),
    query VARCHAR(500) NOT NULL,
    intent VARCHAR(50),
    value_score REAL DEFAULT 0.0,
    difficulty_proxy REAL DEFAULT 0.0,
    search_volume INTEGER,
    cpc REAL,
    competition REAL,
    serp_features JSONB DEFAULT '[]',
    source VARCHAR(100),
    language VARCHAR(10) DEFAULT 'en',
    country VARCHAR(10) DEFAULT 'US',
    top_results_analyzed BOOLEAN DEFAULT FALSE,
    gap_analysis JSONB DEFAULT '{}',
    content_requirements JSONB DEFAULT '[]',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(project_id, query)
);

-- Pages table
CREATE TABLE IF NOT EXISTS pages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    cluster_id UUID REFERENCES clusters(id),
    author_id UUID REFERENCES authors(id),
    title VARCHAR(500) NOT NULL,
    slug VARCHAR(255) NOT NULL,
    url VARCHAR(1000),
    canonical_url VARCHAR(1000),
    content_type VARCHAR(50) DEFAULT 'article',
    word_count INTEGER DEFAULT 0,
    reading_time_minutes INTEGER DEFAULT 0,
    language VARCHAR(10) DEFAULT 'en',
    meta_title VARCHAR(500),
    meta_description VARCHAR(500),
    target_keywords JSONB DEFAULT '[]',
    schema_type VARCHAR(100),
    info_gain_score REAL DEFAULT 0.0,
    info_gain_elements JSONB DEFAULT '[]',
    task_completers JSONB DEFAULT '[]',
    citations JSONB DEFAULT '[]',
    quality_score REAL DEFAULT 0.0,
    readability_score REAL DEFAULT 0.0,
    status VARCHAR(50) DEFAULT 'draft',
    cms_post_id VARCHAR(100),
    published_at TIMESTAMPTZ,
    last_modified TIMESTAMPTZ,
    indexed_at TIMESTAMPTZ,
    last_crawled TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(project_id, slug)
);

-- Internal links table
CREATE TABLE IF NOT EXISTS internal_links (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    from_page_id UUID NOT NULL REFERENCES pages(id) ON DELETE CASCADE,
    to_page_id UUID NOT NULL REFERENCES pages(id) ON DELETE CASCADE,
    anchor_text VARCHAR(500) NOT NULL,
    link_context TEXT,
    link_position VARCHAR(50),
    is_exact_match BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    last_validated TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(from_page_id, to_page_id, anchor_text)
);

-- Performance metrics table
CREATE TABLE IF NOT EXISTS performance_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    page_id UUID NOT NULL REFERENCES pages(id) ON DELETE CASCADE,
    lcp_ms INTEGER,
    inp_ms INTEGER,
    cls REAL,
    fcp_ms INTEGER,
    ttfb_ms INTEGER,
    total_size_kb INTEGER,
    js_size_kb INTEGER,
    css_size_kb INTEGER,
    image_size_kb INTEGER,
    performance_score INTEGER,
    accessibility_score INTEGER,
    best_practices_score INTEGER,
    seo_score INTEGER,
    device VARCHAR(20) DEFAULT 'mobile',
    source VARCHAR(50) DEFAULT 'psi',
    test_url VARCHAR(1000),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- CTR tests table
CREATE TABLE IF NOT EXISTS ctr_tests (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    page_id UUID NOT NULL REFERENCES pages(id) ON DELETE CASCADE,
    test_name VARCHAR(255) NOT NULL,
    test_type VARCHAR(50) DEFAULT 'title',
    control_title VARCHAR(500),
    control_meta_description VARCHAR(500),
    variant_title VARCHAR(500),
    variant_meta_description VARCHAR(500),
    status VARCHAR(50) DEFAULT 'planned',
    started_at TIMESTAMPTZ,
    ended_at TIMESTAMPTZ,
    duration_days INTEGER DEFAULT 14,
    control_impressions INTEGER DEFAULT 0,
    control_clicks INTEGER DEFAULT 0,
    control_ctr REAL DEFAULT 0.0,
    control_avg_position REAL DEFAULT 0.0,
    variant_impressions INTEGER DEFAULT 0,
    variant_clicks INTEGER DEFAULT 0,
    variant_ctr REAL DEFAULT 0.0,
    variant_avg_position REAL DEFAULT 0.0,
    confidence_level REAL DEFAULT 0.95,
    p_value REAL,
    is_significant BOOLEAN DEFAULT FALSE,
    ctr_improvement REAL DEFAULT 0.0,
    winner VARCHAR(20),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- GSC data table
CREATE TABLE IF NOT EXISTS gsc_data (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    date TIMESTAMPTZ NOT NULL,
    page VARCHAR(1000),
    query VARCHAR(500),
    country VARCHAR(10),
    device VARCHAR(20),
    clicks INTEGER DEFAULT 0,
    impressions INTEGER DEFAULT 0,
    ctr REAL DEFAULT 0.0,
    position REAL DEFAULT 0.0,
    data_freshness VARCHAR(20),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(project_id, date, page, query, country, device)
);

-- Content briefs table
CREATE TABLE IF NOT EXISTS content_briefs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    cluster_id UUID REFERENCES clusters(id),
    assigned_author_id UUID REFERENCES authors(id),
    title VARCHAR(500) NOT NULL,
    slug VARCHAR(255) NOT NULL,
    content_type VARCHAR(50) DEFAULT 'article',
    target_audience VARCHAR(255),
    user_intent VARCHAR(100),
    primary_keyword VARCHAR(500),
    secondary_keywords JSONB DEFAULT '[]',
    outline JSONB DEFAULT '[]',
    info_gain_requirements JSONB DEFAULT '[]',
    task_completer_specs JSONB DEFAULT '[]',
    word_count_target INTEGER DEFAULT 1000,
    competitor_analysis JSONB DEFAULT '{}',
    content_gaps JSONB DEFAULT '[]',
    differentiation_strategy JSONB DEFAULT '[]',
    expert_quotes_needed BOOLEAN DEFAULT FALSE,
    original_research_needed BOOLEAN DEFAULT FALSE,
    citations_required JSONB DEFAULT '[]',
    internal_link_targets JSONB DEFAULT '[]',
    schema_type VARCHAR(100),
    technical_requirements JSONB DEFAULT '{}',
    status VARCHAR(50) DEFAULT 'draft',
    reviewed_by VARCHAR(255),
    approved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(project_id, slug)
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_keywords_project_id ON keywords(project_id);
CREATE INDEX IF NOT EXISTS idx_keywords_cluster_id ON keywords(cluster_id);
CREATE INDEX IF NOT EXISTS idx_keywords_intent ON keywords(intent);
CREATE INDEX IF NOT EXISTS idx_keywords_query ON keywords USING gin(to_tsvector('english', query));

CREATE INDEX IF NOT EXISTS idx_pages_project_id ON pages(project_id);
CREATE INDEX IF NOT EXISTS idx_pages_cluster_id ON pages(cluster_id);
CREATE INDEX IF NOT EXISTS idx_pages_status ON pages(status);
CREATE INDEX IF NOT EXISTS idx_pages_published_at ON pages(published_at);

CREATE INDEX IF NOT EXISTS idx_clusters_project_id ON clusters(project_id);
CREATE INDEX IF NOT EXISTS idx_clusters_type ON clusters(cluster_type);

CREATE INDEX IF NOT EXISTS idx_gsc_data_project_date ON gsc_data(project_id, date);
CREATE INDEX IF NOT EXISTS idx_gsc_data_page ON gsc_data(page);
CREATE INDEX IF NOT EXISTS idx_gsc_data_query ON gsc_data USING gin(to_tsvector('english', query));

CREATE INDEX IF NOT EXISTS idx_performance_metrics_page_id ON performance_metrics(page_id);
CREATE INDEX IF NOT EXISTS idx_performance_metrics_created_at ON performance_metrics(created_at);

-- Enable Row Level Security (RLS) for all tables
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE clusters ENABLE ROW LEVEL SECURITY;
ALTER TABLE authors ENABLE ROW LEVEL SECURITY;
ALTER TABLE keywords ENABLE ROW LEVEL SECURITY;
ALTER TABLE pages ENABLE ROW LEVEL SECURITY;
ALTER TABLE internal_links ENABLE ROW LEVEL SECURITY;
ALTER TABLE performance_metrics ENABLE ROW LEVEL SECURITY;
ALTER TABLE ctr_tests ENABLE ROW LEVEL SECURITY;
ALTER TABLE gsc_data ENABLE ROW LEVEL SECURITY;
ALTER TABLE content_briefs ENABLE ROW LEVEL SECURITY;

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Add updated_at triggers to all tables
CREATE TRIGGER update_projects_updated_at BEFORE UPDATE ON projects FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_clusters_updated_at BEFORE UPDATE ON clusters FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_authors_updated_at BEFORE UPDATE ON authors FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_keywords_updated_at BEFORE UPDATE ON keywords FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_pages_updated_at BEFORE UPDATE ON pages FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_internal_links_updated_at BEFORE UPDATE ON internal_links FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_performance_metrics_updated_at BEFORE UPDATE ON performance_metrics FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_ctr_tests_updated_at BEFORE UPDATE ON ctr_tests FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_gsc_data_updated_at BEFORE UPDATE ON gsc_data FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_content_briefs_updated_at BEFORE UPDATE ON content_briefs FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();