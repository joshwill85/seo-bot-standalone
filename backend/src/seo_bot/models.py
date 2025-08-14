"""SQLAlchemy models for SEO-Bot."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4
from enum import Enum

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.types import TypeDecorator, VARCHAR


class AlertSeverity(Enum):
    """Alert severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IndexationStatus(Enum):
    """Page indexation status."""
    SUBMITTED = "submitted"
    INDEXED = "indexed"
    EXCLUDED = "excluded"
    ERROR = "error"
    PENDING = "pending"


class CoverageMetrics:
    """Simple data class for coverage metrics."""
    def __init__(self, 
                 total_pages: int = 0,
                 indexed_pages: int = 0,
                 submitted_pages: int = 0,
                 excluded_pages: int = 0,
                 error_pages: int = 0):
        self.total_pages = total_pages
        self.indexed_pages = indexed_pages
        self.submitted_pages = submitted_pages
        self.excluded_pages = excluded_pages
        self.error_pages = error_pages
    
    @property
    def indexation_rate(self) -> float:
        """Calculate indexation rate."""
        return self.indexed_pages / self.total_pages if self.total_pages > 0 else 0.0


class GUID(TypeDecorator):
    """Platform-independent GUID type."""
    
    impl = VARCHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(VARCHAR(36))
        else:
            return dialect.type_descriptor(VARCHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return str(value)
        else:
            return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        else:
            return str(value)


Base = declarative_base()


class TimestampMixin:
    """Mixin for created_at and updated_at timestamps."""
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True), 
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )


class Project(Base, TimestampMixin):
    """Project represents a website/domain being optimized."""
    
    __tablename__ = "projects"
    
    id = Column(GUID(), primary_key=True, default=lambda: str(uuid4()))
    name = Column(String(255), nullable=False)
    domain = Column(String(255), nullable=False, unique=True)
    base_url = Column(String(500), nullable=False)
    language = Column(String(10), default="en")
    country = Column(String(10), default="US")
    cms_type = Column(String(50), default="markdown")  # markdown, wordpress
    status = Column(String(50), default="active")  # active, paused, archived
    config = Column(JSON, default=dict)
    
    # Relationships
    keywords = relationship("Keyword", back_populates="project", cascade="all, delete-orphan")
    clusters = relationship("Cluster", back_populates="project", cascade="all, delete-orphan")
    pages = relationship("Page", back_populates="project", cascade="all, delete-orphan")
    authors = relationship("Author", back_populates="project", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Project(domain='{self.domain}', status='{self.status}')>"


class Keyword(Base, TimestampMixin):
    """Keyword represents a search query and its analysis."""
    
    __tablename__ = "keywords"
    
    id = Column(GUID(), primary_key=True, default=lambda: str(uuid4()))
    project_id = Column(GUID(), ForeignKey("projects.id"), nullable=False)
    cluster_id = Column(GUID(), ForeignKey("clusters.id"))
    query = Column(String(500), nullable=False)
    intent = Column(String(50))  # informational, navigational, transactional
    value_score = Column(Float, default=0.0)
    difficulty_proxy = Column(Float, default=0.0)
    search_volume = Column(Integer)
    cpc = Column(Float)
    competition = Column(Float)
    serp_features = Column(JSON, default=list)
    source = Column(String(100))  # gsc, seeds, autocomplete, competitors
    language = Column(String(10), default="en")
    country = Column(String(10), default="US")
    
    # Analysis results
    top_results_analyzed = Column(Boolean, default=False)
    gap_analysis = Column(JSON, default=dict)
    content_requirements = Column(JSON, default=list)
    
    # Relationships
    project = relationship("Project", back_populates="keywords")
    cluster = relationship("Cluster", back_populates="keywords")
    
    __table_args__ = (
        UniqueConstraint('project_id', 'query', name='_project_query_uc'),
    )
    
    def __repr__(self):
        return f"<Keyword(query='{self.query}', intent='{self.intent}')>"


class Cluster(Base, TimestampMixin):
    """Cluster represents a group of related keywords."""
    
    __tablename__ = "clusters"
    
    id = Column(GUID(), primary_key=True, default=lambda: str(uuid4()))
    project_id = Column(GUID(), ForeignKey("projects.id"), nullable=False)
    name = Column(String(255), nullable=False)
    slug = Column(String(255), nullable=False)
    cluster_type = Column(String(50), default="hub")  # hub, spoke
    parent_cluster_id = Column(GUID(), ForeignKey("clusters.id"))
    priority_score = Column(Float, default=0.0)
    estimated_traffic = Column(Integer, default=0)
    
    # Content planning
    content_brief_created = Column(Boolean, default=False)
    content_written = Column(Boolean, default=False)
    content_published = Column(Boolean, default=False)
    
    # Metadata
    entities = Column(JSON, default=list)  # Key entities/topics
    embedding_vector = Column(JSON)  # For similarity calculations
    
    # Relationships
    project = relationship("Project", back_populates="clusters")
    keywords = relationship("Keyword", back_populates="cluster")
    pages = relationship("Page", back_populates="cluster")
    parent_cluster = relationship("Cluster", remote_side=[id])
    child_clusters = relationship("Cluster")
    
    __table_args__ = (
        UniqueConstraint('project_id', 'slug', name='_project_slug_uc'),
    )
    
    def __repr__(self):
        return f"<Cluster(name='{self.name}', type='{self.cluster_type}')>"


class Author(Base, TimestampMixin):
    """Author represents content creators and experts."""
    
    __tablename__ = "authors"
    
    id = Column(GUID(), primary_key=True, default=lambda: str(uuid4()))
    project_id = Column(GUID(), ForeignKey("projects.id"), nullable=False)
    name = Column(String(255), nullable=False)
    slug = Column(String(255), nullable=False)
    email = Column(String(255))
    bio = Column(Text)
    credentials = Column(JSON, default=list)  # Certifications, degrees, etc.
    expertise_areas = Column(JSON, default=list)  # Topics they can write about
    
    # Profile information
    photo_url = Column(String(500))
    linkedin_url = Column(String(500))
    twitter_url = Column(String(500))
    website_url = Column(String(500))
    
    # Performance metrics
    articles_written = Column(Integer, default=0)
    avg_quality_score = Column(Float, default=0.0)
    
    # Relationships
    project = relationship("Project", back_populates="authors")
    pages = relationship("Page", back_populates="author")
    
    __table_args__ = (
        UniqueConstraint('project_id', 'slug', name='_project_author_slug_uc'),
    )
    
    def __repr__(self):
        return f"<Author(name='{self.name}', expertise={len(self.expertise_areas)})>"


class Page(Base, TimestampMixin):
    """Page represents content pages on the website."""
    
    __tablename__ = "pages"
    
    id = Column(GUID(), primary_key=True, default=lambda: str(uuid4()))
    project_id = Column(GUID(), ForeignKey("projects.id"), nullable=False)
    cluster_id = Column(GUID(), ForeignKey("clusters.id"))
    author_id = Column(GUID(), ForeignKey("authors.id"))
    
    # Page identification
    title = Column(String(500), nullable=False)
    slug = Column(String(255), nullable=False)
    url = Column(String(1000))
    canonical_url = Column(String(1000))
    
    # Content metadata
    content_type = Column(String(50), default="article")  # article, product, howto, comparison
    word_count = Column(Integer, default=0)
    reading_time_minutes = Column(Integer, default=0)
    language = Column(String(10), default="en")
    
    # SEO metadata
    meta_title = Column(String(500))
    meta_description = Column(String(500))
    target_keywords = Column(JSON, default=list)
    schema_type = Column(String(100))  # Article, Product, HowTo, etc.
    
    # Content quality metrics
    info_gain_score = Column(Float, default=0.0)
    info_gain_elements = Column(JSON, default=list)
    task_completers = Column(JSON, default=list)  # calculators, checklists, etc.
    citations = Column(JSON, default=list)  # Primary source citations
    quality_score = Column(Float, default=0.0)
    readability_score = Column(Float, default=0.0)
    
    # Publishing status
    status = Column(String(50), default="draft")  # draft, published, archived
    cms_post_id = Column(String(100))  # WordPress post ID, GitHub file path, etc.
    published_at = Column(DateTime(timezone=True))
    last_modified = Column(DateTime(timezone=True))
    
    # Performance tracking
    indexed_at = Column(DateTime(timezone=True))
    last_crawled = Column(DateTime(timezone=True))
    
    # Relationships
    project = relationship("Project", back_populates="pages")
    cluster = relationship("Cluster", back_populates="pages")
    author = relationship("Author", back_populates="pages")
    internal_links_out = relationship("InternalLink", foreign_keys="InternalLink.from_page_id", back_populates="from_page")
    internal_links_in = relationship("InternalLink", foreign_keys="InternalLink.to_page_id", back_populates="to_page")
    performance_metrics = relationship("PerformanceMetric", back_populates="page")
    ctr_tests = relationship("CTRTest", back_populates="page")
    
    __table_args__ = (
        UniqueConstraint('project_id', 'slug', name='_project_page_slug_uc'),
    )
    
    def __repr__(self):
        return f"<Page(title='{self.title}', status='{self.status}')>"


class InternalLink(Base, TimestampMixin):
    """InternalLink represents links between pages on the site."""
    
    __tablename__ = "internal_links"
    
    id = Column(GUID(), primary_key=True, default=lambda: str(uuid4()))
    from_page_id = Column(GUID(), ForeignKey("pages.id"), nullable=False)
    to_page_id = Column(GUID(), ForeignKey("pages.id"), nullable=False)
    
    anchor_text = Column(String(500), nullable=False)
    link_context = Column(Text)  # Surrounding text for context
    link_position = Column(String(50))  # header, content, footer, sidebar
    is_exact_match = Column(Boolean, default=False)
    
    # Status tracking
    is_active = Column(Boolean, default=True)
    last_validated = Column(DateTime(timezone=True))
    
    # Relationships
    from_page = relationship("Page", foreign_keys=[from_page_id], back_populates="internal_links_out")
    to_page = relationship("Page", foreign_keys=[to_page_id], back_populates="internal_links_in")
    
    __table_args__ = (
        UniqueConstraint('from_page_id', 'to_page_id', 'anchor_text', name='_unique_link_uc'),
    )
    
    def __repr__(self):
        return f"<InternalLink(anchor='{self.anchor_text}')>"


class PerformanceMetric(Base, TimestampMixin):
    """PerformanceMetric tracks technical performance of pages."""
    
    __tablename__ = "performance_metrics"
    
    id = Column(GUID(), primary_key=True, default=lambda: str(uuid4()))
    page_id = Column(GUID(), ForeignKey("pages.id"), nullable=False)
    
    # Core Web Vitals
    lcp_ms = Column(Integer)  # Largest Contentful Paint
    inp_ms = Column(Integer)  # Interaction to Next Paint
    cls = Column(Float)       # Cumulative Layout Shift
    fcp_ms = Column(Integer)  # First Contentful Paint
    ttfb_ms = Column(Integer) # Time to First Byte
    
    # Resource metrics
    total_size_kb = Column(Integer)
    js_size_kb = Column(Integer)
    css_size_kb = Column(Integer)
    image_size_kb = Column(Integer)
    
    # Scores
    performance_score = Column(Integer)  # Lighthouse performance score
    accessibility_score = Column(Integer)  # Lighthouse accessibility score
    best_practices_score = Column(Integer)
    seo_score = Column(Integer)
    
    # Device and source
    device = Column(String(20), default="mobile")  # mobile, desktop
    source = Column(String(50), default="psi")  # psi, lighthouse, crux
    test_url = Column(String(1000))
    
    # Relationships
    page = relationship("Page", back_populates="performance_metrics")
    
    def __repr__(self):
        return f"<PerformanceMetric(lcp={self.lcp_ms}ms, cls={self.cls})>"


class CTRTest(Base, TimestampMixin):
    """CTRTest tracks title/meta description testing."""
    
    __tablename__ = "ctr_tests"
    
    id = Column(GUID(), primary_key=True, default=lambda: str(uuid4()))
    page_id = Column(GUID(), ForeignKey("pages.id"), nullable=False)
    
    # Test configuration
    test_name = Column(String(255), nullable=False)
    test_type = Column(String(50), default="title")  # title, meta_description, both
    
    # Original version (control)
    control_title = Column(String(500))
    control_meta_description = Column(String(500))
    
    # Test version (variant)
    variant_title = Column(String(500))
    variant_meta_description = Column(String(500))
    
    # Test status and timing
    status = Column(String(50), default="planned")  # planned, running, completed, cancelled
    started_at = Column(DateTime(timezone=True))
    ended_at = Column(DateTime(timezone=True))
    duration_days = Column(Integer, default=14)
    
    # Results
    control_impressions = Column(Integer, default=0)
    control_clicks = Column(Integer, default=0)
    control_ctr = Column(Float, default=0.0)
    control_avg_position = Column(Float, default=0.0)
    
    variant_impressions = Column(Integer, default=0)
    variant_clicks = Column(Integer, default=0)
    variant_ctr = Column(Float, default=0.0)
    variant_avg_position = Column(Float, default=0.0)
    
    # Statistical analysis
    confidence_level = Column(Float, default=0.95)
    p_value = Column(Float)
    is_significant = Column(Boolean, default=False)
    ctr_improvement = Column(Float, default=0.0)
    winner = Column(String(20))  # control, variant, inconclusive
    
    # Relationships
    page = relationship("Page", back_populates="ctr_tests")
    
    def __repr__(self):
        return f"<CTRTest(name='{self.test_name}', status='{self.status}')>"


class GSCData(Base, TimestampMixin):
    """GSCData stores Google Search Console performance data."""
    
    __tablename__ = "gsc_data"
    
    id = Column(GUID(), primary_key=True, default=lambda: str(uuid4()))
    project_id = Column(GUID(), ForeignKey("projects.id"), nullable=False)
    
    # Dimensions
    date = Column(DateTime(timezone=True), nullable=False)
    page = Column(String(1000))
    query = Column(String(500))
    country = Column(String(10))
    device = Column(String(20))
    
    # Metrics
    clicks = Column(Integer, default=0)
    impressions = Column(Integer, default=0)
    ctr = Column(Float, default=0.0)
    position = Column(Float, default=0.0)
    
    # Data source metadata
    data_freshness = Column(String(20))  # fresh, stale
    
    # Relationships
    project = relationship("Project")
    
    __table_args__ = (
        UniqueConstraint('project_id', 'date', 'page', 'query', 'country', 'device', 
                        name='_gsc_unique_row_uc'),
    )
    
    def __repr__(self):
        return f"<GSCData(page='{self.page[:50]}...', query='{self.query}')>"


class ContentBrief(Base, TimestampMixin):
    """ContentBrief stores content planning and requirements."""
    
    __tablename__ = "content_briefs"
    
    id = Column(GUID(), primary_key=True, default=lambda: str(uuid4()))
    project_id = Column(GUID(), ForeignKey("projects.id"), nullable=False)
    cluster_id = Column(GUID(), ForeignKey("clusters.id"))
    
    # Brief metadata
    title = Column(String(500), nullable=False)
    slug = Column(String(255), nullable=False)
    content_type = Column(String(50), default="article")
    target_audience = Column(String(255))
    user_intent = Column(String(100))
    
    # Target keywords
    primary_keyword = Column(String(500))
    secondary_keywords = Column(JSON, default=list)
    
    # Content requirements
    outline = Column(JSON, default=list)  # List of sections/headings
    info_gain_requirements = Column(JSON, default=list)  # Required unique elements
    task_completer_specs = Column(JSON, default=list)  # Calculator, tool specs
    word_count_target = Column(Integer, default=1000)
    
    # Competitive analysis
    competitor_analysis = Column(JSON, default=dict)
    content_gaps = Column(JSON, default=list)
    differentiation_strategy = Column(JSON, default=list)
    
    # Research requirements
    expert_quotes_needed = Column(Boolean, default=False)
    original_research_needed = Column(Boolean, default=False)
    citations_required = Column(JSON, default=list)
    
    # Internal linking plan
    internal_link_targets = Column(JSON, default=list)
    
    # Schema and technical requirements
    schema_type = Column(String(100))
    technical_requirements = Column(JSON, default=dict)
    
    # Status
    status = Column(String(50), default="draft")  # draft, approved, in_progress, completed
    assigned_author_id = Column(GUID(), ForeignKey("authors.id"))
    reviewed_by = Column(String(255))
    approved_at = Column(DateTime(timezone=True))
    
    # Relationships
    project = relationship("Project")
    cluster = relationship("Cluster")
    assigned_author = relationship("Author")
    
    __table_args__ = (
        UniqueConstraint('project_id', 'slug', name='_project_brief_slug_uc'),
    )
    
    def __repr__(self):
        return f"<ContentBrief(title='{self.title}', status='{self.status}')>"