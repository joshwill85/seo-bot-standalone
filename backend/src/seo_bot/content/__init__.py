"""Content quality and trust signal modules for SEO-Bot."""

from .expertise import (
    TrustSignalAnalyzer,
    AuthorValidator,
    CitationValidator,
    ExpertReviewManager,
    AuthorValidation,
    CitationValidation,
    TrustSignalAssessment,
    create_trust_analyzer,
)

from .brief_generator import (
    ContentBriefGenerator,
    SERPAnalysisProcessor,
    TaskCompleterGenerator,
    InternalLinkingStrategy,
    ContentBriefRequirements,
    ContentOutlineSection,
    TaskCompleterSpec,
    CompetitiveAdvantage,
    create_brief_generator,
)

__all__ = [
    # Trust signal analysis
    "TrustSignalAnalyzer",
    "AuthorValidator", 
    "CitationValidator",
    "ExpertReviewManager",
    "create_trust_analyzer",
    
    # Content brief generation
    "ContentBriefGenerator",
    "SERPAnalysisProcessor",
    "TaskCompleterGenerator", 
    "InternalLinkingStrategy",
    "create_brief_generator",
    
    # Data classes
    "AuthorValidation",
    "CitationValidation", 
    "TrustSignalAssessment",
    "ContentBriefRequirements",
    "ContentOutlineSection",
    "TaskCompleterSpec",
    "CompetitiveAdvantage",
]