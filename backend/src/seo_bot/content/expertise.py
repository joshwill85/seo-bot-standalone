"""E-E-A-T (Experience, Expertise, Authoritativeness, Trustworthiness) trust signal system."""

import json
import re
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union
from urllib.parse import urlparse

import httpx
from sqlalchemy.orm import Session

from ..config import TrustSignalsConfig, settings
from ..db import get_db_session
from ..logging import get_logger, LoggerMixin
from ..models import Author, ContentBrief, Page, Project


@dataclass
class AuthorValidation:
    """Author validation result."""
    has_byline: bool
    has_bio: bool
    has_photo: bool
    has_credentials: bool
    has_social_profiles: bool
    bio_word_count: int
    credentials_count: int
    expertise_match_score: float  # How well author expertise matches content topic
    validation_score: float  # Overall validation score 0-10


@dataclass
class CitationValidation:
    """Citation validation result."""
    citation_url: str
    citation_text: str
    is_primary_source: bool
    is_authoritative: bool
    domain_authority_score: float
    relevance_score: float
    publication_date: Optional[datetime]
    validation_status: str  # "valid", "questionable", "invalid"


@dataclass
class TrustSignalAssessment:
    """Complete trust signal assessment for a page."""
    page_id: str
    content_type: str
    is_ymyl: bool  # Your Money or Your Life content
    
    # Author signals
    author_validation: Optional[AuthorValidation]
    
    # Citation signals
    citations: List[CitationValidation]
    citation_density: float  # Citations per 1000 words
    primary_source_ratio: float
    
    # Schema markup
    has_author_schema: bool
    has_organization_schema: bool
    has_article_schema: bool
    
    # Trust indicators
    has_publish_date: bool
    has_update_date: bool
    content_freshness_days: int
    
    # Review status
    expert_reviewed: bool
    reviewed_by: Optional[str]
    review_date: Optional[datetime]
    
    # Final scores
    trust_signal_score: float  # Overall score 0-10
    compliance_status: str  # "compliant", "needs_review", "non_compliant"
    required_actions: List[str]


class AuthorValidator:
    """Validates author attribution and credentials."""
    
    def __init__(self):
        """Initialize author validator."""
        self.logger = get_logger(self.__class__.__name__)
    
    def validate_author(self, author: Author, content_topic: str) -> AuthorValidation:
        """
        Validate author credentials and attribution.
        
        Args:
            author: Author to validate
            content_topic: Main topic of the content
            
        Returns:
            Author validation result
        """
        has_byline = bool(author.name and len(author.name.strip()) > 2)
        has_bio = bool(author.bio and len(author.bio.strip()) > 50)
        has_photo = bool(author.photo_url)
        has_credentials = bool(author.credentials and len(author.credentials) > 0)
        has_social_profiles = any([author.linkedin_url, author.twitter_url, author.website_url])
        
        bio_word_count = len(author.bio.split()) if author.bio else 0
        credentials_count = len(author.credentials) if author.credentials else 0
        
        # Calculate expertise match score
        expertise_match_score = self._calculate_expertise_match(author, content_topic)
        
        # Calculate overall validation score
        validation_score = self._calculate_author_score(
            has_byline, has_bio, has_photo, has_credentials, 
            has_social_profiles, bio_word_count, credentials_count, expertise_match_score
        )
        
        return AuthorValidation(
            has_byline=has_byline,
            has_bio=has_bio,
            has_photo=has_photo,
            has_credentials=has_credentials,
            has_social_profiles=has_social_profiles,
            bio_word_count=bio_word_count,
            credentials_count=credentials_count,
            expertise_match_score=expertise_match_score,
            validation_score=validation_score
        )
    
    def _calculate_expertise_match(self, author: Author, content_topic: str) -> float:
        """Calculate how well author expertise matches content topic."""
        if not author.expertise_areas or not content_topic:
            return 0.0
        
        content_topic_lower = content_topic.lower()
        match_score = 0.0
        
        for expertise in author.expertise_areas:
            expertise_lower = expertise.lower()
            
            # Direct match
            if expertise_lower in content_topic_lower or content_topic_lower in expertise_lower:
                match_score += 1.0
            # Partial match (shared words)
            else:
                expertise_words = set(expertise_lower.split())
                topic_words = set(content_topic_lower.split())
                overlap = len(expertise_words.intersection(topic_words))
                if overlap > 0:
                    match_score += overlap / max(len(expertise_words), len(topic_words))
        
        # Normalize by number of expertise areas
        if author.expertise_areas:
            match_score /= len(author.expertise_areas)
        
        return min(1.0, match_score)
    
    def _calculate_author_score(
        self, 
        has_byline: bool, 
        has_bio: bool, 
        has_photo: bool, 
        has_credentials: bool,
        has_social_profiles: bool, 
        bio_word_count: int, 
        credentials_count: int, 
        expertise_match_score: float
    ) -> float:
        """Calculate overall author validation score."""
        score = 0.0
        
        # Essential requirements (60% of score)
        if has_byline:
            score += 2.0
        if has_bio:
            score += 2.0
        if has_photo:
            score += 2.0
        
        # Additional signals (40% of score)
        if has_credentials:
            score += 1.0
        if has_social_profiles:
            score += 0.5
        
        # Bio quality bonus
        if bio_word_count >= 100:
            score += 0.5
        elif bio_word_count >= 50:
            score += 0.25
        
        # Credentials bonus
        if credentials_count >= 3:
            score += 0.5
        elif credentials_count >= 1:
            score += 0.25
        
        # Expertise match bonus
        score += expertise_match_score * 1.5
        
        return min(10.0, score)


class CitationValidator:
    """Validates citations and sources."""
    
    # Authoritative domains for different topics
    AUTHORITATIVE_DOMAINS = {
        'government': [
            'gov', 'nih.gov', 'cdc.gov', 'fda.gov', 'nist.gov', 'census.gov'
        ],
        'academic': [
            'edu', 'pubmed.ncbi.nlm.nih.gov', 'scholar.google.com', 'researchgate.net',
            'springer.com', 'nature.com', 'sciencedirect.com', 'wiley.com'
        ],
        'news': [
            'reuters.com', 'apnews.com', 'bbc.com', 'npr.org', 'pbs.org'
        ],
        'finance': [
            'sec.gov', 'federalreserve.gov', 'investopedia.com', 'bloomberg.com',
            'wsj.com', 'ft.com'
        ],
        'health': [
            'who.int', 'mayoclinic.org', 'webmd.com', 'healthline.com', 'nih.gov'
        ]
    }
    
    def __init__(self):
        """Initialize citation validator."""
        self.logger = get_logger(self.__class__.__name__)
        self.session = httpx.Client(timeout=10)
    
    def validate_citation(self, citation_url: str, citation_text: str, content_topic: str) -> CitationValidation:
        """
        Validate a single citation.
        
        Args:
            citation_url: URL of the citation
            citation_text: Anchor text or description
            content_topic: Topic of the content
            
        Returns:
            Citation validation result
        """
        domain = urlparse(citation_url).netloc.lower()
        
        # Check if it's a primary source
        is_primary_source = self._is_primary_source(domain, content_topic)
        
        # Check if it's authoritative
        is_authoritative = self._is_authoritative_domain(domain, content_topic)
        
        # Calculate domain authority score
        domain_authority_score = self._calculate_domain_authority(domain)
        
        # Calculate relevance score
        relevance_score = self._calculate_citation_relevance(citation_text, content_topic)
        
        # Try to get publication date
        publication_date = self._extract_publication_date(citation_url)
        
        # Determine validation status
        validation_status = self._determine_validation_status(
            is_primary_source, is_authoritative, domain_authority_score, relevance_score
        )
        
        return CitationValidation(
            citation_url=citation_url,
            citation_text=citation_text,
            is_primary_source=is_primary_source,
            is_authoritative=is_authoritative,
            domain_authority_score=domain_authority_score,
            relevance_score=relevance_score,
            publication_date=publication_date,
            validation_status=validation_status
        )
    
    def _is_primary_source(self, domain: str, content_topic: str) -> bool:
        """Check if domain is likely a primary source for the topic."""
        topic_lower = content_topic.lower()
        
        # Government sources are primary for policy/regulation content
        if any(gov_domain in domain for gov_domain in self.AUTHORITATIVE_DOMAINS['government']):
            if any(keyword in topic_lower for keyword in ['regulation', 'law', 'policy', 'government', 'official']):
                return True
        
        # Academic sources are primary for research content
        if any(domain.endswith(edu_domain) for edu_domain in self.AUTHORITATIVE_DOMAINS['academic']):
            if any(keyword in topic_lower for keyword in ['research', 'study', 'analysis', 'scientific']):
                return True
        
        # Company sources are primary for their own products/services
        if 'investor' in domain or 'ir.' in domain or domain.endswith('.com'):
            return False  # Most commercial sources are secondary
        
        return False
    
    def _is_authoritative_domain(self, domain: str, content_topic: str) -> bool:
        """Check if domain is authoritative for the content topic."""
        for topic_category, domains in self.AUTHORITATIVE_DOMAINS.items():
            if any(auth_domain in domain for auth_domain in domains):
                return True
        
        # Check for other indicators of authority
        authority_indicators = [
            '.gov', '.edu', '.org',
            'wikipedia.org', 'britannica.com'
        ]
        
        return any(indicator in domain for indicator in authority_indicators)
    
    def _calculate_domain_authority(self, domain: str) -> float:
        """Calculate domain authority score (simplified)."""
        # This is a simplified scoring system
        # In production, you might integrate with tools like Moz or Ahrefs
        
        score = 5.0  # Base score
        
        # Government domains
        if '.gov' in domain:
            score = 9.5
        # Educational domains
        elif '.edu' in domain:
            score = 9.0
        # Non-profit organizations
        elif '.org' in domain:
            score = 7.0
        # Well-known authoritative sites
        elif any(auth in domain for auth in ['wikipedia', 'britannica', 'reuters', 'bbc']):
            score = 8.5
        # Academic publishers
        elif any(pub in domain for pub in ['nature.com', 'springer.com', 'sciencedirect.com']):
            score = 9.0
        
        return score
    
    def _calculate_citation_relevance(self, citation_text: str, content_topic: str) -> float:
        """Calculate how relevant the citation is to the content topic."""
        if not citation_text or not content_topic:
            return 0.5
        
        citation_lower = citation_text.lower()
        topic_lower = content_topic.lower()
        
        # Direct topic mention
        if topic_lower in citation_lower:
            return 1.0
        
        # Calculate word overlap
        citation_words = set(citation_lower.split())
        topic_words = set(topic_lower.split())
        overlap = len(citation_words.intersection(topic_words))
        
        if overlap > 0:
            return overlap / max(len(citation_words), len(topic_words))
        
        return 0.3  # Default relevance for unmatched citations
    
    def _extract_publication_date(self, url: str) -> Optional[datetime]:
        """Try to extract publication date from URL or page metadata."""
        # This is a simplified implementation
        # In production, you might parse the actual page content
        
        # Look for date patterns in URL
        date_pattern = re.compile(r'/(\d{4})/(\d{1,2})/(\d{1,2})/')
        match = date_pattern.search(url)
        
        if match:
            try:
                year, month, day = map(int, match.groups())
                return datetime(year, month, day, tzinfo=timezone.utc)
            except ValueError:
                pass
        
        return None
    
    def _determine_validation_status(
        self, 
        is_primary_source: bool, 
        is_authoritative: bool, 
        domain_authority_score: float, 
        relevance_score: float
    ) -> str:
        """Determine overall validation status of citation."""
        if is_primary_source and is_authoritative and relevance_score > 0.7:
            return "valid"
        elif is_authoritative and domain_authority_score > 7.0 and relevance_score > 0.5:
            return "valid"
        elif domain_authority_score > 5.0 and relevance_score > 0.3:
            return "questionable"
        else:
            return "invalid"


class ExpertReviewManager:
    """Manages expert review workflows."""
    
    def __init__(self):
        """Initialize expert review manager."""
        self.logger = get_logger(self.__class__.__name__)
    
    def requires_expert_review(self, content_type: str, topic: str, trust_config: TrustSignalsConfig) -> bool:
        """
        Determine if content requires expert review.
        
        Args:
            content_type: Type of content
            topic: Content topic
            trust_config: Trust signals configuration
            
        Returns:
            Whether expert review is required
        """
        # Always require review if configured
        if trust_config.review_by_expert:
            return True
        
        # YMYL content always requires review
        if self._is_ymyl_content(topic):
            return True
        
        # Specific content types that need review
        review_required_types = ['medical', 'financial', 'legal', 'safety']
        topic_lower = topic.lower()
        
        return any(req_type in topic_lower for req_type in review_required_types)
    
    def _is_ymyl_content(self, topic: str) -> bool:
        """Check if content is YMYL (Your Money or Your Life)."""
        topic_lower = topic.lower()
        
        ymyl_keywords = [
            'health', 'medical', 'medicine', 'doctor', 'treatment', 'disease', 'symptoms',
            'financial', 'money', 'investment', 'loan', 'credit', 'insurance', 'tax',
            'legal', 'law', 'attorney', 'lawsuit', 'rights',
            'safety', 'security', 'emergency', 'dangerous'
        ]
        
        return any(keyword in topic_lower for keyword in ymyl_keywords)
    
    def create_review_requirement(self, page_id: str, reason: str, priority: str = "normal") -> Dict:
        """Create a review requirement for a page."""
        return {
            'page_id': page_id,
            'reason': reason,
            'priority': priority,
            'created_at': datetime.now(timezone.utc),
            'status': 'pending',
            'assigned_to': None,
            'review_notes': None
        }


class TrustSignalAnalyzer(LoggerMixin):
    """Main trust signal analysis and compliance system."""
    
    def __init__(self, trust_config: Optional[TrustSignalsConfig] = None):
        """Initialize trust signal analyzer."""
        self.trust_config = trust_config or TrustSignalsConfig()
        self.author_validator = AuthorValidator()
        self.citation_validator = CitationValidator()
        self.review_manager = ExpertReviewManager()
    
    def assess_trust_signals(self, page: Page, author: Optional[Author] = None) -> TrustSignalAssessment:
        """
        Perform comprehensive trust signal assessment for a page.
        
        Args:
            page: Page to assess
            author: Author of the page (optional)
            
        Returns:
            Complete trust signal assessment
        """
        self.logger.info(f"Assessing trust signals for page: {page.title}")
        
        # Determine if YMYL content
        is_ymyl = self.review_manager._is_ymyl_content(page.title + " " + (page.meta_description or ""))
        
        # Validate author if provided
        author_validation = None
        if author and self.trust_config.require_author:
            content_topic = self._extract_content_topic(page)
            author_validation = self.author_validator.validate_author(author, content_topic)
        
        # Validate citations
        citations = self._extract_and_validate_citations(page)
        citation_density = self._calculate_citation_density(citations, page.word_count)
        primary_source_ratio = self._calculate_primary_source_ratio(citations)
        
        # Check schema markup
        has_author_schema = self._check_author_schema(page)
        has_organization_schema = self._check_organization_schema(page)
        has_article_schema = self._check_article_schema(page)
        
        # Check dates
        has_publish_date = bool(page.published_at)
        has_update_date = bool(page.last_modified)
        content_freshness_days = self._calculate_content_freshness(page)
        
        # Check expert review
        expert_reviewed = self._check_expert_review(page)
        reviewed_by = None  # Would be stored in page metadata
        review_date = None  # Would be stored in page metadata
        
        # Calculate overall trust signal score
        trust_signal_score = self._calculate_trust_score(
            author_validation, citations, citation_density, primary_source_ratio,
            has_author_schema, has_organization_schema, has_article_schema,
            has_publish_date, has_update_date, content_freshness_days,
            expert_reviewed, is_ymyl
        )
        
        # Determine compliance status and required actions
        compliance_status, required_actions = self._determine_compliance(
            author_validation, citations, citation_density, has_publish_date, 
            expert_reviewed, is_ymyl, trust_signal_score
        )
        
        assessment = TrustSignalAssessment(
            page_id=page.id,
            content_type=page.content_type,
            is_ymyl=is_ymyl,
            author_validation=author_validation,
            citations=citations,
            citation_density=citation_density,
            primary_source_ratio=primary_source_ratio,
            has_author_schema=has_author_schema,
            has_organization_schema=has_organization_schema,
            has_article_schema=has_article_schema,
            has_publish_date=has_publish_date,
            has_update_date=has_update_date,
            content_freshness_days=content_freshness_days,
            expert_reviewed=expert_reviewed,
            reviewed_by=reviewed_by,
            review_date=review_date,
            trust_signal_score=trust_signal_score,
            compliance_status=compliance_status,
            required_actions=required_actions
        )
        
        self.logger.info(
            f"Trust signal assessment completed",
            page_id=page.id,
            trust_score=trust_signal_score,
            compliance_status=compliance_status,
            required_actions_count=len(required_actions)
        )
        
        return assessment
    
    def _extract_content_topic(self, page: Page) -> str:
        """Extract main topic from page content."""
        # Simple topic extraction - could be enhanced with NLP
        topic_sources = [page.title, page.meta_description or ""]
        if page.target_keywords:
            topic_sources.extend(page.target_keywords)
        
        return " ".join(topic_sources)
    
    def _extract_and_validate_citations(self, page: Page) -> List[CitationValidation]:
        """Extract and validate citations from page."""
        citations = []
        
        if page.citations:
            content_topic = self._extract_content_topic(page)
            
            for citation_data in page.citations:
                if isinstance(citation_data, dict) and 'url' in citation_data:
                    citation_url = citation_data['url']
                    citation_text = citation_data.get('text', '')
                    
                    validation = self.citation_validator.validate_citation(
                        citation_url, citation_text, content_topic
                    )
                    citations.append(validation)
        
        return citations
    
    def _calculate_citation_density(self, citations: List[CitationValidation], word_count: int) -> float:
        """Calculate citations per 1000 words."""
        if word_count == 0:
            return 0.0
        
        return (len(citations) / word_count) * 1000
    
    def _calculate_primary_source_ratio(self, citations: List[CitationValidation]) -> float:
        """Calculate ratio of primary sources to total citations."""
        if not citations:
            return 0.0
        
        primary_count = sum(1 for c in citations if c.is_primary_source)
        return primary_count / len(citations)
    
    def _check_author_schema(self, page: Page) -> bool:
        """Check if page has proper author schema markup."""
        # This would check the actual page content for schema markup
        # For now, return True if author is assigned
        return bool(page.author_id)
    
    def _check_organization_schema(self, page: Page) -> bool:
        """Check if page has organization schema markup."""
        # This would check for Organization schema in the page
        # Simplified implementation
        return page.schema_type is not None
    
    def _check_article_schema(self, page: Page) -> bool:
        """Check if page has article schema markup."""
        return page.schema_type == "Article"
    
    def _calculate_content_freshness(self, page: Page) -> int:
        """Calculate content freshness in days."""
        if page.last_modified:
            delta = datetime.now(timezone.utc) - page.last_modified
            return delta.days
        elif page.published_at:
            delta = datetime.now(timezone.utc) - page.published_at
            return delta.days
        else:
            return 999  # Very old/unknown
    
    def _check_expert_review(self, page: Page) -> bool:
        """Check if page has been reviewed by an expert."""
        # This would check review metadata
        # Simplified implementation
        return False
    
    def _calculate_trust_score(
        self,
        author_validation: Optional[AuthorValidation],
        citations: List[CitationValidation],
        citation_density: float,
        primary_source_ratio: float,
        has_author_schema: bool,
        has_organization_schema: bool,
        has_article_schema: bool,
        has_publish_date: bool,
        has_update_date: bool,
        content_freshness_days: int,
        expert_reviewed: bool,
        is_ymyl: bool
    ) -> float:
        """Calculate overall trust signal score."""
        score = 0.0
        
        # Author signals (30% of score)
        if author_validation:
            score += (author_validation.validation_score / 10) * 3.0
        elif not self.trust_config.require_author:
            score += 2.0  # Partial credit if author not required
        
        # Citation signals (30% of score)
        if citations:
            valid_citations = sum(1 for c in citations if c.validation_status == "valid")
            citation_score = min(3.0, valid_citations * 0.5)
            score += citation_score
            
            # Bonus for primary sources
            if primary_source_ratio > 0.5:
                score += 0.5
        
        # Schema markup (15% of score)
        schema_score = 0.0
        if has_author_schema:
            schema_score += 0.5
        if has_organization_schema:
            schema_score += 0.5
        if has_article_schema:
            schema_score += 0.5
        score += schema_score
        
        # Freshness and dates (15% of score)
        date_score = 0.0
        if has_publish_date:
            date_score += 0.75
        if has_update_date:
            date_score += 0.25
        
        # Freshness penalty
        if content_freshness_days > 365:
            date_score *= 0.5
        elif content_freshness_days > 180:
            date_score *= 0.8
        
        score += date_score
        
        # Expert review (10% of score)
        if expert_reviewed:
            score += 1.0
        elif is_ymyl:
            score -= 1.0  # Penalty for YMYL content without expert review
        
        return min(10.0, score)
    
    def _determine_compliance(
        self,
        author_validation: Optional[AuthorValidation],
        citations: List[CitationValidation],
        citation_density: float,
        has_publish_date: bool,
        expert_reviewed: bool,
        is_ymyl: bool,
        trust_signal_score: float
    ) -> Tuple[str, List[str]]:
        """Determine compliance status and required actions."""
        required_actions = []
        
        # Author validation requirements
        if self.trust_config.require_author and not author_validation:
            required_actions.append("Add author attribution")
        elif author_validation and author_validation.validation_score < 6.0:
            if not author_validation.has_bio:
                required_actions.append("Add author bio")
            if not author_validation.has_photo and self.trust_config.require_author_photo:
                required_actions.append("Add author photo")
            if not author_validation.has_credentials:
                required_actions.append("Add author credentials")
        
        # Citation requirements
        if self.trust_config.require_citations:
            min_citations = self.trust_config.min_citations_per_page
            if len(citations) < min_citations:
                required_actions.append(f"Add at least {min_citations} citations")
            
            valid_citations = sum(1 for c in citations if c.validation_status == "valid")
            if valid_citations < min_citations:
                required_actions.append("Improve citation quality with more authoritative sources")
        
        # Date requirements
        if self.trust_config.require_publish_date and not has_publish_date:
            required_actions.append("Add publish date")
        
        # Expert review requirements
        if is_ymyl and not expert_reviewed:
            required_actions.append("Require expert review for YMYL content")
        
        # Determine overall compliance status
        if trust_signal_score >= 8.0 and not required_actions:
            compliance_status = "compliant"
        elif trust_signal_score >= 6.0 and len(required_actions) <= 2:
            compliance_status = "needs_review"
        else:
            compliance_status = "non_compliant"
        
        return compliance_status, required_actions
    
    def export_assessment(self, assessment: TrustSignalAssessment, output_path: str) -> None:
        """Export trust signal assessment to JSON file."""
        try:
            assessment_dict = asdict(assessment)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(assessment_dict, f, indent=2, ensure_ascii=False, default=str)
            
            self.logger.info(f"Trust signal assessment exported to {output_path}")
        
        except Exception as e:
            self.logger.error(f"Failed to export assessment: {e}")


def create_trust_analyzer(project_id: str) -> TrustSignalAnalyzer:
    """Create a trust signal analyzer for a specific project."""
    with get_db_session() as session:
        project = session.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise ValueError(f"Project {project_id} not found")
        
        # Get trust signals config from project config
        trust_config = TrustSignalsConfig()
        if project.config and 'trust_signals' in project.config:
            trust_config = TrustSignalsConfig(**project.config['trust_signals'])
        
        return TrustSignalAnalyzer(trust_config)