"""Research data models and schemas."""

from datetime import datetime
from typing import Dict, List, Literal, Optional, Union
from pydantic import BaseModel, AnyUrl, Field
import hashlib


class Observation(BaseModel):
    """Individual data observation for research datasets."""
    dataset_id: str
    entity_id: str
    metric: Literal["price", "spec.version", "feature.flag", "release_date", "performance.score", "availability"]
    value: Union[str, float, int, bool]
    unit: Optional[str] = None
    observed_at: datetime
    source_url: AnyUrl
    hash: str = Field(default="")
    
    def __post_init__(self):
        """Generate content hash for idempotency."""
        if not self.hash:
            content = f"{self.dataset_id}:{self.entity_id}:{self.metric}:{self.value}:{self.observed_at.isoformat()}"
            self.hash = hashlib.sha256(content.encode()).hexdigest()[:16]


class Dataset(BaseModel):
    """Research dataset configuration and metadata."""
    id: str
    title: str
    description: str
    category: Literal["pricing", "specifications", "releases", "features", "performance"]
    entities: List[str]  # List of entity IDs to track
    metrics: List[str]   # List of metrics to collect
    collection_frequency: Literal["daily", "weekly", "monthly"]
    sources: List[Dict[str, str]]  # Source configurations
    schema_fields: Dict[str, str]  # JSON-LD schema additions
    created_at: datetime
    last_updated: datetime


class ResearchConfig(BaseModel):
    """Configuration for research collection system."""
    # Collection settings
    rate_limit_delay: float = 1.0  # Seconds between requests
    max_retries: int = 3
    timeout_seconds: int = 30
    respect_robots_txt: bool = True
    
    # Storage settings
    output_formats: List[Literal["csv", "parquet", "json"]] = ["csv", "parquet"]
    chart_formats: List[Literal["png", "svg", "html"]] = ["png", "html"]
    
    # Quality gates
    min_observations_per_dataset: int = 10
    max_staleness_days: int = 7
    data_completeness_threshold: float = 0.8
    
    # Schema.org Dataset fields
    dataset_license: str = "https://creativecommons.org/licenses/by/4.0/"
    dataset_citation: str = ""
    creator_name: str = ""
    creator_url: Optional[AnyUrl] = None


class SourceResult(BaseModel):
    """Result from a data source collection."""
    source_id: str
    success: bool
    observations: List[Observation] = []
    errors: List[str] = []
    collected_at: datetime
    next_collection: Optional[datetime] = None


class DatasetMetrics(BaseModel):
    """Metrics for dataset quality and performance."""
    total_observations: int
    unique_entities: int
    date_range_start: datetime
    date_range_end: datetime
    completeness_score: float  # 0-1
    freshness_score: float     # 0-1
    accuracy_confidence: float # 0-1
    natural_links_earned: int = 0
    download_count: int = 0
    last_updated: datetime