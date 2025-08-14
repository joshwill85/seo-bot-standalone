"""Configuration management for SEO-Bot."""

from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import yaml
from pydantic import BaseModel, Field, validator
from pydantic_settings import BaseSettings


class SiteConfig(BaseModel):
    """Site-specific configuration."""
    
    domain: str
    language: str = "en"
    country: str = "US"
    cms: str = Field(default="markdown", pattern="^(markdown|wordpress)$")
    content_dir: str = "./content"
    base_url: str
    timezone: str = "UTC"


class TrustSignalsConfig(BaseModel):
    """E-E-A-T and trust signal configuration."""
    
    require_author: bool = True
    require_citations: bool = True
    min_citations_per_page: int = 2
    author_bio_required: bool = True
    review_by_expert: bool = False
    require_author_photo: bool = True
    require_publish_date: bool = True
    require_update_date: bool = True


class ContentQualityConfig(BaseModel):
    """Content quality and validation settings."""
    
    min_info_gain_points: int = 5
    task_completers_required: int = 1
    word_count_bounds: List[int] = Field(default=[800, 2000])
    unique_value_threshold: float = Field(default=0.15, ge=0.0, le=1.0)
    similarity_threshold: float = Field(default=0.85, ge=0.0, le=1.0)
    min_readability_score: int = 60
    max_keyword_density: float = 0.03
    
    @validator('word_count_bounds')
    def validate_word_count_bounds(cls, v):
        if len(v) != 2 or v[0] >= v[1]:
            raise ValueError('word_count_bounds must be [min, max] with min < max')
        return v


class PerformanceBudget(BaseModel):
    """Performance budget for a specific template type."""
    
    lcp_ms: int = Field(default=2500, ge=0)
    inp_ms: int = Field(default=200, ge=0)
    cls: float = Field(default=0.1, ge=0.0)
    js_kb: int = Field(default=200, ge=0)
    css_kb: int = Field(default=100, ge=0)
    image_kb: int = Field(default=500, ge=0)


class PerformanceBudgetsConfig(BaseModel):
    """Performance budgets by template type."""
    
    article: PerformanceBudget = PerformanceBudget()
    product: PerformanceBudget = PerformanceBudget(lcp_ms=2200, inp_ms=120, js_kb=250)
    comparison: PerformanceBudget = PerformanceBudget(lcp_ms=2500, inp_ms=150, js_kb=300)
    calculator: PerformanceBudget = PerformanceBudget(lcp_ms=1800, inp_ms=80, js_kb=400)


class CTRTestingConfig(BaseModel):
    """CTR testing and optimization settings."""
    
    statistical_significance: float = Field(default=0.95, ge=0.0, le=1.0)
    min_sample_size: int = Field(default=200, ge=50)
    max_tests_per_week: int = Field(default=15, ge=1)
    min_improvement_threshold: float = Field(default=0.15, ge=0.0)
    test_duration_days: int = Field(default=14, ge=7)
    position_stability_threshold: float = Field(default=2.0, ge=0.0)


class KeywordsConfig(BaseModel):
    """Keyword discovery and analysis settings."""
    
    seed_terms: List[str] = []
    min_intent_score: float = Field(default=0.6, ge=0.0, le=1.0)
    difficulty_proxy_max: float = Field(default=0.7, ge=0.0, le=1.0)
    value_score_min: float = Field(default=1.0, ge=0.0)
    max_keywords_per_run: int = Field(default=10000, ge=100)


class ClusteringConfig(BaseModel):
    """Topic clustering configuration."""
    
    method: str = Field(default="hdbscan", pattern="^(hdbscan|kmeans|agglomerative)$")
    min_cluster_size: int = Field(default=6, ge=3)
    embedding_model: str = "all-MiniLM-L6-v2"
    similarity_threshold: float = Field(default=0.7, ge=0.0, le=1.0)


class ContentConfig(BaseModel):
    """Content generation settings."""
    
    hubs_per_run: int = Field(default=2, ge=1)
    max_spokes_per_hub: int = Field(default=40, ge=5)
    programmatic_min_unique_fields: int = Field(default=6, ge=3)
    templates_dir: str = "./templates"
    output_dir: str = "./out"


class InternalLinksConfig(BaseModel):
    """Internal linking configuration."""
    
    max_outlinks_per_page: int = Field(default=30, ge=5)
    target_inlinks_per_spoke: int = Field(default=8, ge=3)
    anchor_variants: int = Field(default=3, ge=1, le=5)
    max_exact_match_anchors: float = Field(default=0.3, ge=0.0, le=1.0)


class TechConfig(BaseModel):
    """Technical optimization settings."""
    
    image_max_width: int = Field(default=1400, ge=300)
    image_quality: int = Field(default=85, ge=10, le=100)
    enable_webp: bool = True
    enable_avif: bool = False
    lazy_load_images: bool = True
    minify_html: bool = True
    critical_css_inline: bool = True


class CoverageSLAConfig(BaseModel):
    """Coverage and freshness SLA settings."""
    
    indexation_target: float = Field(default=0.80, ge=0.0, le=1.0)
    indexation_timeframe_days: int = Field(default=14, ge=1)
    freshness_review_days: int = Field(default=90, ge=30)
    min_internal_links: int = Field(default=8, ge=1)
    max_orphan_pages: int = Field(default=0, ge=0)


class GovernanceConfig(BaseModel):
    """Quality governance and anti-spam settings."""
    
    max_programmatic_per_week: int = Field(default=500, ge=1)
    similarity_threshold: float = Field(default=0.85, ge=0.0, le=1.0)
    human_review_required: List[str] = ["ymyl", "legal", "medical"]
    quality_score_minimum: float = Field(default=7.0, ge=0.0, le=10.0)
    content_velocity_limit: int = Field(default=100, ge=1)  # pages per day


class MonitoringConfig(BaseModel):
    """Monitoring and alerting configuration."""
    
    alert_channels: List[str] = ["email"]
    critical_response_minutes: int = Field(default=30, ge=5)
    performance_review_frequency: str = Field(default="weekly", pattern="^(daily|weekly|monthly)$")
    enable_slack_alerts: bool = False
    enable_email_alerts: bool = True


class AdaptersConfig(BaseModel):
    """External service adapter configuration."""
    
    serp: str = Field(default="none", pattern="^(none|serpapi|dataforseo)$")
    embeddings: str = Field(default="local", pattern="^(local|openai)$")
    storage: str = Field(default="local", pattern="^(local|s3)$")
    cms: str = Field(default="markdown", pattern="^(markdown|wordpress)$")


class PublishingConfig(BaseModel):
    """Publishing and deployment settings."""
    
    dry_run: bool = True
    author: str = "Editorial Bot"
    category: str = "Guides"
    auto_publish: bool = False
    create_drafts: bool = True
    backup_before_publish: bool = True


class ProjectConfig(BaseModel):
    """Complete project configuration."""
    
    site: SiteConfig
    trust_signals: TrustSignalsConfig = TrustSignalsConfig()
    content_quality: ContentQualityConfig = ContentQualityConfig()
    performance_budgets: PerformanceBudgetsConfig = PerformanceBudgetsConfig()
    ctr_testing: CTRTestingConfig = CTRTestingConfig()
    keywords: KeywordsConfig = KeywordsConfig()
    clustering: ClusteringConfig = ClusteringConfig()
    content: ContentConfig = ContentConfig()
    internal_links: InternalLinksConfig = InternalLinksConfig()
    tech: TechConfig = TechConfig()
    coverage_sla: CoverageSLAConfig = CoverageSLAConfig()
    governance: GovernanceConfig = GovernanceConfig()
    monitoring: MonitoringConfig = MonitoringConfig()
    adapters: AdaptersConfig = AdaptersConfig()
    publishing: PublishingConfig = PublishingConfig()


class Settings(BaseSettings):
    """Application-wide settings from environment variables."""
    
    # Database
    database_url: str = "sqlite:///seo_bot.db"
    
    # Google APIs
    google_search_console_credentials_file: Optional[str] = None
    pagespeed_api_key: Optional[str] = None
    
    # OpenAI
    openai_api_key: Optional[str] = None
    
    # SERP APIs
    serp_api_key: Optional[str] = None
    dataforseo_login: Optional[str] = None
    dataforseo_password: Optional[str] = None
    
    # WordPress
    wordpress_url: Optional[str] = None
    wordpress_username: Optional[str] = None
    wordpress_app_password: Optional[str] = None
    
    # GitHub
    github_token: Optional[str] = None
    
    # Notifications
    slack_webhook_url: Optional[str] = None
    smtp_host: Optional[str] = None
    smtp_port: int = 587
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    
    # Redis/Celery
    redis_url: str = "redis://localhost:6379"
    celery_broker_url: Optional[str] = None
    
    # Logging
    log_level: str = "INFO"
    log_format: str = "json"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


def load_project_config(project_path: Union[str, Path]) -> ProjectConfig:
    """Load configuration for a specific project."""
    project_path = Path(project_path)
    config_file = project_path / "config.yml"
    
    if not config_file.exists():
        raise FileNotFoundError(f"Config file not found: {config_file}")
    
    with open(config_file, "r", encoding="utf-8") as f:
        config_data = yaml.safe_load(f)
    
    return ProjectConfig(**config_data)


def create_default_config(project_path: Union[str, Path], domain: str) -> ProjectConfig:
    """Create a default configuration for a new project."""
    config = ProjectConfig(
        site=SiteConfig(
            domain=domain,
            base_url=f"https://{domain}"
        )
    )
    
    project_path = Path(project_path)
    config_file = project_path / "config.yml"
    
    # Ensure directory exists
    project_path.mkdir(parents=True, exist_ok=True)
    
    # Write configuration
    config_dict = config.model_dump()
    with open(config_file, "w", encoding="utf-8") as f:
        yaml.dump(config_dict, f, default_flow_style=False, indent=2)
    
    return config


# Global settings instance
settings = Settings()