"""SEO-Bot: AI-powered SEO automation platform."""

__version__ = "0.1.0"
__author__ = "SEO Bot Team"
__email__ = "hello@seobot.ai"

# Core module imports for easy access
from .keywords import (
    SERPGapAnalyzer,
    KeywordClusterManager,
    create_cluster_manager,
)

from .content import (
    TrustSignalAnalyzer,
    ContentBriefGenerator,
    create_trust_analyzer,
    create_brief_generator,
)

from .linking import (
    EntityLinkingManager,
    create_entity_manager,
)

__all__ = [
    # Version info
    "__version__",
    "__author__", 
    "__email__",
    
    # SERP and keyword analysis
    "SERPGapAnalyzer",
    "KeywordClusterManager",
    "create_cluster_manager",
    
    # Content analysis and generation
    "TrustSignalAnalyzer",
    "ContentBriefGenerator", 
    "create_trust_analyzer",
    "create_brief_generator",
    
    # Entity linking and knowledge graph
    "EntityLinkingManager",
    "create_entity_manager",
]