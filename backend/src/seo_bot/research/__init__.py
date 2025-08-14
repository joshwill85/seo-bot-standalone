"""First-Party Research Layer - Automated dataset generation and publishing."""

from .sources import (
    ResearchSourceManager,
    PriceTracker,
    SpecDiffCollector,
    ReleaseTimelineCollector,
    ChangelogCollector
)
from .normalize import DataNormalizer, ObservationSchema
from .publish import ResearchPublisher, DatasetRenderer
from .models import Observation, Dataset, ResearchConfig

__all__ = [
    "ResearchSourceManager",
    "PriceTracker", 
    "SpecDiffCollector",
    "ReleaseTimelineCollector",
    "ChangelogCollector",
    "DataNormalizer",
    "ObservationSchema",
    "ResearchPublisher",
    "DatasetRenderer",
    "Observation",
    "Dataset",
    "ResearchConfig",
]