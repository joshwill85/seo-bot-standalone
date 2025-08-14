"""Anti-Spam & Quality Governance System.

Provides spam detection algorithms, quality scoring, automated review workflows,
content velocity limits, and YMYL content review queue management.
"""

import asyncio
import logging
import hashlib
import re
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Set, Tuple, Union
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import textstat

from ..config import GovernanceConfig, Settings
from ..models import AlertSeverity


logger = logging.getLogger(__name__)


class ContentQualityLevel(Enum):
    """Content quality levels."""
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    SPAM = "spam"


class ReviewPriority(Enum):
    """Review priority levels."""
    URGENT = "urgent"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ContentCategory(Enum):
    """Content categories for governance."""
    YMYL = "ymyl"  # Your Money or Your Life
    LEGAL = "legal"
    MEDICAL = "medical"
    FINANCIAL = "financial"
    GENERAL = "general"
    TECHNICAL = "technical"
    COMMERCIAL = "commercial"


class SpamSignal(Enum):
    """Types of spam signals detected."""
    KEYWORD_STUFFING = "keyword_stuffing"
    DUPLICATE_CONTENT = "duplicate_content"
    LOW_READABILITY = "low_readability"
    THIN_CONTENT = "thin_content"
    EXCESSIVE_LINKING = "excessive_linking"
    BOILERPLATE_TEXT = "boilerplate_text"
    AUTO_GENERATED = "auto_generated"
    IRRELEVANT_CONTENT = "irrelevant_content"


@dataclass
class QualityScore:
    """Comprehensive quality score breakdown."""
    overall_score: float  # 0-10 scale
    content_quality: float
    technical_quality: float
    trustworthiness: float
    user_experience: float
    seo_optimization: float
    
    # Detailed metrics
    word_count: int
    readability_score: float
    unique_information_score: float
    citation_score: float
    grammar_score: float
    originality_score: float
    
    # Quality level
    quality_level: ContentQualityLevel
    
    # Issues and recommendations
    issues: List[str]
    recommendations: List[str]
    spam_signals: List[SpamSignal]


@dataclass
class ContentSimilarity:
    """Content similarity analysis result."""
    similarity_score: float
    matching_content_id: Optional[str]
    matching_url: Optional[str]
    match_type: str  # exact, near_duplicate, similar
    similar_segments: List[str]
    recommendation: str


@dataclass
class ReviewTask:
    """Content review task."""
    id: str
    content_id: str
    content_url: str
    content_title: str
    category: ContentCategory
    priority: ReviewPriority
    assigned_reviewer: Optional[str]
    
    # Governance flags
    requires_expert_review: bool
    requires_fact_checking: bool
    requires_legal_review: bool
    
    # Metadata
    created_at: datetime
    due_date: datetime
    estimated_review_time: int  # minutes
    
    # Quality concerns
    quality_score: float
    spam_signals: List[SpamSignal]
    similarity_issues: List[ContentSimilarity]
    
    # Status
    status: str  # pending, in_review, approved, rejected, needs_revision
    reviewer_notes: Optional[str]
    resolution: Optional[str]


class ContentSimilarityDetector:
    """Detects duplicate and near-duplicate content."""
    
    def __init__(self, similarity_threshold: float = 0.85):
        """Initialize similarity detector.
        
        Args:
            similarity_threshold: Threshold for considering content similar
        """
        self.similarity_threshold = similarity_threshold
        self.vectorizer = TfidfVectorizer(
            max_features=10000,
            stop_words='english',
            ngram_range=(1, 3),
            max_df=0.8,
            min_df=2
        )
        self.content_vectors = {}
        self.content_metadata = {}
    
    def add_content(self, content_id: str, content: str, url: str = None):
        """Add content to similarity index."""
        try:
            # Preprocess content
            processed_content = self._preprocess_content(content)
            
            # Store metadata
            self.content_metadata[content_id] = {
                'url': url,
                'content_hash': hashlib.md5(content.encode()).hexdigest(),
                'word_count': len(content.split()),
                'added_at': datetime.now(timezone.utc)
            }
            
            # Vectorize and store
            if processed_content.strip():
                if not self.content_vectors:
                    # First content - fit vectorizer
                    vector = self.vectorizer.fit_transform([processed_content])
                else:
                    # Additional content - transform only
                    try:
                        vector = self.vectorizer.transform([processed_content])
                    except ValueError:
                        # Refit if vocabulary has changed significantly
                        all_content = [processed_content]
                        for cid, metadata in self.content_metadata.items():
                            if cid != content_id and cid in self.content_vectors:
                                # Would need to store original content for refitting
                                pass
                        vector = self.vectorizer.fit_transform(all_content)
                
                self.content_vectors[content_id] = vector
            
            logger.debug(f"Added content {content_id} to similarity index")
            
        except Exception as e:
            logger.error(f"Failed to add content to similarity index: {e}")
    
    def find_similar_content(self, content: str, content_id: str = None) -> List[ContentSimilarity]:
        """Find similar content in the index."""
        similar_content = []
        
        try:
            processed_content = self._preprocess_content(content)
            
            if not processed_content.strip() or not self.content_vectors:
                return similar_content
            
            # Vectorize new content
            query_vector = self.vectorizer.transform([processed_content])
            
            # Calculate similarities
            for stored_id, stored_vector in self.content_vectors.items():
                if stored_id == content_id:
                    continue
                
                similarity = cosine_similarity(query_vector, stored_vector)[0][0]
                
                if similarity >= self.similarity_threshold:
                    metadata = self.content_metadata.get(stored_id, {})
                    
                    # Determine match type
                    if similarity >= 0.95:
                        match_type = "exact"
                        recommendation = "Content appears to be duplicate - consider consolidating"
                    elif similarity >= 0.85:
                        match_type = "near_duplicate"
                        recommendation = "Content is very similar - ensure sufficient differentiation"
                    else:
                        match_type = "similar"
                        recommendation = "Content has similarities - verify uniqueness"
                    
                    similar_content.append(ContentSimilarity(
                        similarity_score=similarity,
                        matching_content_id=stored_id,
                        matching_url=metadata.get('url'),
                        match_type=match_type,
                        similar_segments=self._find_similar_segments(content, stored_id),
                        recommendation=recommendation
                    ))
            
            # Sort by similarity score
            similar_content.sort(key=lambda x: x.similarity_score, reverse=True)
            
        except Exception as e:
            logger.error(f"Failed to find similar content: {e}")
        
        return similar_content
    
    def _preprocess_content(self, content: str) -> str:
        """Preprocess content for similarity analysis."""
        # Remove HTML tags
        content = re.sub(r'<[^>]+>', '', content)
        
        # Remove extra whitespace
        content = re.sub(r'\s+', ' ', content)
        
        # Remove URLs
        content = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', content)
        
        # Convert to lowercase
        content = content.lower()
        
        return content.strip()
    
    def _find_similar_segments(self, content: str, stored_id: str) -> List[str]:
        """Find specific similar segments between content pieces."""
        # Simplified implementation - would use more sophisticated text alignment
        segments = []
        
        # Split content into sentences
        sentences = re.split(r'[.!?]+', content)
        
        # Find sentences that appear in both pieces
        for sentence in sentences:
            if len(sentence.strip()) > 50:  # Only check substantial sentences
                # In a real implementation, would check against stored content
                segments.append(sentence.strip()[:100] + "...")
        
        return segments[:5]  # Return top 5 similar segments


class SpamDetector:
    """Detects various spam signals in content."""
    
    def __init__(self, governance_config: GovernanceConfig):
        """Initialize spam detector."""
        self.governance_config = governance_config
        
        # Keyword stuffing patterns
        self.keyword_patterns = [
            r'(\b\w+\b)(?:\s+\1){3,}',  # Repeated words
            r'(\b\w+\b)(?:\s+\w+){0,2}\s+\1(?:\s+\w+){0,2}\s+\1',  # Close repetitions
        ]
        
        # Boilerplate patterns
        self.boilerplate_patterns = [
            r'click here for more information',
            r'this article will teach you',
            r'in this article, we will cover',
            r'if you liked this article',
            r'share this article',
            r'subscribe to our newsletter'
        ]
    
    def detect_spam_signals(self, content: str, target_keywords: List[str] = None) -> List[SpamSignal]:
        """Detect spam signals in content."""
        signals = []
        
        # Check keyword stuffing
        if self._detect_keyword_stuffing(content, target_keywords):
            signals.append(SpamSignal.KEYWORD_STUFFING)
        
        # Check readability
        if self._detect_poor_readability(content):
            signals.append(SpamSignal.LOW_READABILITY)
        
        # Check thin content
        if self._detect_thin_content(content):
            signals.append(SpamSignal.THIN_CONTENT)
        
        # Check excessive linking
        if self._detect_excessive_linking(content):
            signals.append(SpamSignal.EXCESSIVE_LINKING)
        
        # Check boilerplate text
        if self._detect_boilerplate(content):
            signals.append(SpamSignal.BOILERPLATE_TEXT)
        
        # Check auto-generated patterns
        if self._detect_auto_generated(content):
            signals.append(SpamSignal.AUTO_GENERATED)
        
        return signals
    
    def _detect_keyword_stuffing(self, content: str, target_keywords: List[str] = None) -> bool:
        """Detect keyword stuffing."""
        if not target_keywords:
            return False
        
        word_count = len(content.split())
        if word_count == 0:
            return False
        
        for keyword in target_keywords:
            keyword_lower = keyword.lower()
            content_lower = content.lower()
            
            # Count keyword occurrences
            keyword_count = content_lower.count(keyword_lower)
            keyword_density = keyword_count / word_count
            
            # Check density threshold (typically 2-3% max)
            if keyword_density > 0.03:
                return True
            
            # Check for unnatural repetition patterns
            for pattern in self.keyword_patterns:
                if re.search(pattern.replace(r'\b\w+\b', re.escape(keyword_lower)), content_lower):
                    return True
        
        return False
    
    def _detect_poor_readability(self, content: str) -> bool:
        """Detect poor readability."""
        try:
            # Remove HTML and clean content
            clean_content = re.sub(r'<[^>]+>', '', content)
            
            if len(clean_content.split()) < 100:
                return False  # Too short to assess
            
            # Flesch Reading Ease score
            flesch_score = textstat.flesch_reading_ease(clean_content)
            
            # Score below 30 is considered very difficult
            if flesch_score < 30:
                return True
            
            # Grade level too high
            grade_level = textstat.flesch_kincaid_grade(clean_content)
            if grade_level > 16:
                return True
            
            return False
            
        except Exception:
            return False
    
    def _detect_thin_content(self, content: str) -> bool:
        """Detect thin content."""
        # Remove HTML tags
        clean_content = re.sub(r'<[^>]+>', '', content)
        word_count = len(clean_content.split())
        
        # Check word count
        if word_count < 300:
            return True
        
        # Check for low information density
        sentences = re.split(r'[.!?]+', clean_content)
        if len(sentences) < 5:
            return True
        
        # Check average sentence length
        avg_sentence_length = word_count / len(sentences) if sentences else 0
        if avg_sentence_length < 8:  # Very short sentences may indicate thin content
            return True
        
        return False
    
    def _detect_excessive_linking(self, content: str) -> bool:
        """Detect excessive internal/external linking."""
        # Count links
        link_count = len(re.findall(r'<a\s+[^>]*href=', content, re.IGNORECASE))
        
        # Count words
        clean_content = re.sub(r'<[^>]+>', '', content)
        word_count = len(clean_content.split())
        
        if word_count == 0:
            return False
        
        # More than 1 link per 50 words is excessive
        link_ratio = link_count / word_count
        return link_ratio > 0.02
    
    def _detect_boilerplate(self, content: str) -> bool:
        """Detect boilerplate text patterns."""
        content_lower = content.lower()
        
        boilerplate_count = 0
        for pattern in self.boilerplate_patterns:
            if re.search(pattern, content_lower):
                boilerplate_count += 1
        
        # Too many boilerplate phrases
        return boilerplate_count >= 3
    
    def _detect_auto_generated(self, content: str) -> bool:
        """Detect auto-generated content patterns."""
        # Check for repetitive sentence structures
        sentences = re.split(r'[.!?]+', content)
        
        if len(sentences) < 5:
            return False
        
        # Check for similar sentence starts
        sentence_starts = []
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) > 10:
                # Get first 3 words
                words = sentence.split()[:3]
                if len(words) >= 2:
                    sentence_starts.append(' '.join(words).lower())
        
        # If more than 30% of sentences start similarly, flag as auto-generated
        if sentence_starts:
            unique_starts = len(set(sentence_starts))
            if unique_starts / len(sentence_starts) < 0.7:
                return True
        
        return False


class QualityScorer:
    """Calculates comprehensive quality scores for content."""
    
    def __init__(self, governance_config: GovernanceConfig):
        """Initialize quality scorer."""
        self.governance_config = governance_config
        self.spam_detector = SpamDetector(governance_config)
        self.similarity_detector = ContentSimilarityDetector(
            governance_config.similarity_threshold
        )
    
    def score_content(self, 
                      content: str,
                      title: str = "",
                      meta_description: str = "",
                      target_keywords: List[str] = None,
                      citations: List[str] = None,
                      author_credentials: List[str] = None,
                      content_category: ContentCategory = ContentCategory.GENERAL) -> QualityScore:
        """Calculate comprehensive quality score."""
        
        # Initialize scores
        content_quality = 0.0
        technical_quality = 0.0
        trustworthiness = 0.0
        user_experience = 0.0
        seo_optimization = 0.0
        
        issues = []
        recommendations = []
        
        # Content quality assessment
        content_metrics = self._assess_content_quality(content, title, target_keywords)
        content_quality = content_metrics['score']
        issues.extend(content_metrics['issues'])
        recommendations.extend(content_metrics['recommendations'])
        
        # Technical quality assessment
        technical_metrics = self._assess_technical_quality(content, title, meta_description)
        technical_quality = technical_metrics['score']
        issues.extend(technical_metrics['issues'])
        recommendations.extend(technical_metrics['recommendations'])
        
        # Trustworthiness assessment
        trust_metrics = self._assess_trustworthiness(
            content, citations, author_credentials, content_category
        )
        trustworthiness = trust_metrics['score']
        issues.extend(trust_metrics['issues'])
        recommendations.extend(trust_metrics['recommendations'])
        
        # User experience assessment
        ux_metrics = self._assess_user_experience(content)
        user_experience = ux_metrics['score']
        issues.extend(ux_metrics['issues'])
        recommendations.extend(ux_metrics['recommendations'])
        
        # SEO optimization assessment
        seo_metrics = self._assess_seo_optimization(content, title, meta_description, target_keywords)
        seo_optimization = seo_metrics['score']
        issues.extend(seo_metrics['issues'])
        recommendations.extend(seo_metrics['recommendations'])
        
        # Detect spam signals
        spam_signals = self.spam_detector.detect_spam_signals(content, target_keywords)
        
        # Calculate overall score (weighted average)
        overall_score = (
            content_quality * 0.3 +
            technical_quality * 0.2 +
            trustworthiness * 0.2 +
            user_experience * 0.15 +
            seo_optimization * 0.15
        )
        
        # Apply penalties for spam signals
        spam_penalty = len(spam_signals) * 0.5
        overall_score = max(0, overall_score - spam_penalty)
        
        # Determine quality level
        if spam_signals:
            quality_level = ContentQualityLevel.SPAM
        elif overall_score >= 8.5:
            quality_level = ContentQualityLevel.EXCELLENT
        elif overall_score >= 7.0:
            quality_level = ContentQualityLevel.GOOD
        elif overall_score >= 5.0:
            quality_level = ContentQualityLevel.FAIR
        else:
            quality_level = ContentQualityLevel.POOR
        
        return QualityScore(
            overall_score=overall_score,
            content_quality=content_quality,
            technical_quality=technical_quality,
            trustworthiness=trustworthiness,
            user_experience=user_experience,
            seo_optimization=seo_optimization,
            word_count=len(content.split()),
            readability_score=content_metrics.get('readability_score', 0),
            unique_information_score=content_metrics.get('unique_info_score', 0),
            citation_score=trust_metrics.get('citation_score', 0),
            grammar_score=content_metrics.get('grammar_score', 0),
            originality_score=content_metrics.get('originality_score', 0),
            quality_level=quality_level,
            issues=list(set(issues)),  # Remove duplicates
            recommendations=list(set(recommendations)),
            spam_signals=spam_signals
        )
    
    def _assess_content_quality(self, content: str, title: str, target_keywords: List[str]) -> Dict:
        """Assess content quality."""
        score = 0.0
        issues = []
        recommendations = []
        
        # Word count assessment
        word_count = len(content.split())
        if word_count < 300:
            issues.append("Content is too short (under 300 words)")
            score += 2.0
        elif word_count < 800:
            recommendations.append("Consider expanding content for better depth")
            score += 6.0
        elif word_count <= 2000:
            score += 9.0
        else:
            score += 8.0  # Very long content can be less engaging
        
        # Readability assessment
        try:
            clean_content = re.sub(r'<[^>]+>', '', content)
            readability_score = textstat.flesch_reading_ease(clean_content)
            
            if readability_score >= 60:
                score += 9.0
            elif readability_score >= 30:
                score += 7.0
                recommendations.append("Improve readability with shorter sentences")
            else:
                score += 4.0
                issues.append("Content is difficult to read")
        except:
            readability_score = 50
            score += 6.0
        
        # Content structure assessment
        headings = len(re.findall(r'<h[1-6][^>]*>', content, re.IGNORECASE))
        paragraphs = len(re.findall(r'<p[^>]*>', content, re.IGNORECASE))
        
        if headings >= 3 and paragraphs >= 5:
            score += 9.0
        elif headings >= 1 and paragraphs >= 3:
            score += 7.0
            recommendations.append("Add more headings for better structure")
        else:
            score += 4.0
            issues.append("Poor content structure - add headings and paragraphs")
        
        # Average the assessments
        final_score = score / 3
        
        return {
            'score': min(10.0, final_score),
            'issues': issues,
            'recommendations': recommendations,
            'readability_score': readability_score,
            'unique_info_score': 7.0,  # Would calculate based on comparison with competitors
            'grammar_score': 8.0,  # Would use grammar checking library
            'originality_score': 8.0  # Would calculate based on similarity analysis
        }
    
    def _assess_technical_quality(self, content: str, title: str, meta_description: str) -> Dict:
        """Assess technical SEO quality."""
        score = 0.0
        issues = []
        recommendations = []
        
        # Title assessment
        if not title:
            issues.append("Missing title tag")
            score += 0.0
        elif len(title) < 30:
            issues.append("Title too short")
            score += 4.0
        elif len(title) > 60:
            issues.append("Title too long - may be truncated in search results")
            score += 6.0
        else:
            score += 9.0
        
        # Meta description assessment
        if not meta_description:
            recommendations.append("Add meta description")
            score += 5.0
        elif len(meta_description) < 120:
            recommendations.append("Meta description could be longer")
            score += 7.0
        elif len(meta_description) > 160:
            issues.append("Meta description too long")
            score += 6.0
        else:
            score += 9.0
        
        # Image optimization
        images = re.findall(r'<img[^>]*>', content, re.IGNORECASE)
        images_with_alt = re.findall(r'<img[^>]*alt=', content, re.IGNORECASE)
        
        if images:
            alt_ratio = len(images_with_alt) / len(images)
            if alt_ratio >= 0.9:
                score += 9.0
            elif alt_ratio >= 0.7:
                score += 7.0
                recommendations.append("Add alt text to remaining images")
            else:
                score += 4.0
                issues.append("Many images missing alt text")
        else:
            score += 8.0  # No images to optimize
        
        # Average the assessments
        final_score = score / 3
        
        return {
            'score': min(10.0, final_score),
            'issues': issues,
            'recommendations': recommendations
        }
    
    def _assess_trustworthiness(self, 
                                content: str,
                                citations: List[str],
                                author_credentials: List[str],
                                content_category: ContentCategory) -> Dict:
        """Assess trustworthiness and E-A-T signals."""
        score = 0.0
        issues = []
        recommendations = []
        
        # Author credentials assessment
        if not author_credentials:
            if content_category in [ContentCategory.YMYL, ContentCategory.MEDICAL, ContentCategory.LEGAL]:
                issues.append("YMYL content requires author credentials")
                score += 2.0
            else:
                recommendations.append("Add author credentials for better trust")
                score += 6.0
        else:
            score += 9.0
        
        # Citations assessment
        citation_score = 0.0
        if not citations:
            if content_category in [ContentCategory.YMYL, ContentCategory.MEDICAL, ContentCategory.LEGAL]:
                issues.append("YMYL content requires authoritative citations")
                citation_score = 2.0
            else:
                recommendations.append("Add citations to support claims")
                citation_score = 6.0
        else:
            # Assess citation quality
            authoritative_domains = [
                'gov', 'edu', 'org', 'who.int', 'cdc.gov', 'nih.gov',
                'fda.gov', 'sec.gov', 'ftc.gov'
            ]
            
            authoritative_count = 0
            for citation in citations:
                for domain in authoritative_domains:
                    if domain in citation.lower():
                        authoritative_count += 1
                        break
            
            if authoritative_count >= len(citations) * 0.7:
                citation_score = 9.0
            elif authoritative_count >= len(citations) * 0.4:
                citation_score = 7.0
                recommendations.append("Add more authoritative sources")
            else:
                citation_score = 5.0
                issues.append("Citations lack authoritative sources")
        
        score += citation_score
        
        # Date freshness (if content includes dates)
        date_patterns = re.findall(r'\b(20\d{2})\b', content)
        if date_patterns:
            recent_dates = [int(year) for year in date_patterns if int(year) >= 2020]
            if recent_dates:
                score += 8.0
            else:
                recommendations.append("Update with recent information")
                score += 6.0
        else:
            score += 7.0  # Neutral if no dates found
        
        # Average the assessments
        final_score = score / 3
        
        return {
            'score': min(10.0, final_score),
            'issues': issues,
            'recommendations': recommendations,
            'citation_score': citation_score
        }
    
    def _assess_user_experience(self, content: str) -> Dict:
        """Assess user experience factors."""
        score = 0.0
        issues = []
        recommendations = []
        
        # Content formatting
        lists = len(re.findall(r'<[uo]l[^>]*>', content, re.IGNORECASE))
        bold_text = len(re.findall(r'<(b|strong)[^>]*>', content, re.IGNORECASE))
        
        if lists >= 2 and bold_text >= 3:
            score += 9.0
        elif lists >= 1 or bold_text >= 2:
            score += 7.0
            recommendations.append("Add more formatting for better readability")
        else:
            score += 5.0
            issues.append("Content lacks formatting (lists, bold text)")
        
        # Paragraph length assessment
        paragraphs = re.findall(r'<p[^>]*>(.*?)</p>', content, re.IGNORECASE | re.DOTALL)
        long_paragraphs = sum(1 for p in paragraphs if len(p.split()) > 100)
        
        if long_paragraphs == 0:
            score += 9.0
        elif long_paragraphs <= len(paragraphs) * 0.2:
            score += 7.0
            recommendations.append("Break up remaining long paragraphs")
        else:
            score += 5.0
            issues.append("Many paragraphs are too long")
        
        # Call-to-action presence
        cta_patterns = [
            r'learn more', r'read more', r'click here', r'download',
            r'subscribe', r'contact us', r'get started'
        ]
        
        has_cta = any(re.search(pattern, content, re.IGNORECASE) for pattern in cta_patterns)
        if has_cta:
            score += 8.0
        else:
            recommendations.append("Add clear call-to-action")
            score += 6.0
        
        # Average the assessments
        final_score = score / 3
        
        return {
            'score': min(10.0, final_score),
            'issues': issues,
            'recommendations': recommendations
        }
    
    def _assess_seo_optimization(self, 
                                 content: str,
                                 title: str,
                                 meta_description: str,
                                 target_keywords: List[str]) -> Dict:
        """Assess SEO optimization."""
        score = 0.0
        issues = []
        recommendations = []
        
        if not target_keywords:
            recommendations.append("Define target keywords for optimization")
            return {
                'score': 5.0,
                'issues': issues,
                'recommendations': recommendations
            }
        
        primary_keyword = target_keywords[0].lower()
        content_lower = content.lower()
        title_lower = title.lower()
        
        # Keyword in title
        if primary_keyword in title_lower:
            score += 9.0
        else:
            issues.append(f"Primary keyword '{primary_keyword}' not in title")
            score += 3.0
        
        # Keyword density
        word_count = len(content.split())
        keyword_count = content_lower.count(primary_keyword)
        
        if word_count > 0:
            keyword_density = keyword_count / word_count
            if 0.01 <= keyword_density <= 0.02:  # 1-2% is optimal
                score += 9.0
            elif keyword_density < 0.01:
                recommendations.append("Increase keyword usage naturally")
                score += 6.0
            elif keyword_density > 0.03:
                issues.append("Keyword density too high - reduce usage")
                score += 4.0
            else:
                score += 7.0
        else:
            score += 5.0
        
        # Internal linking
        internal_links = len(re.findall(r'<a[^>]*href="(?!http)', content, re.IGNORECASE))
        if internal_links >= 3:
            score += 9.0
        elif internal_links >= 1:
            score += 7.0
            recommendations.append("Add more internal links")
        else:
            score += 4.0
            issues.append("No internal links found")
        
        # Average the assessments
        final_score = score / 3
        
        return {
            'score': min(10.0, final_score),
            'issues': issues,
            'recommendations': recommendations
        }


class QualityGovernanceManager:
    """Manages quality governance and review workflows."""
    
    def __init__(self, 
                 settings: Settings,
                 governance_config: GovernanceConfig):
        """Initialize quality governance manager."""
        self.settings = settings
        self.governance_config = governance_config
        self.quality_scorer = QualityScorer(governance_config)
        self.similarity_detector = ContentSimilarityDetector(
            governance_config.similarity_threshold
        )
        
        # Track content velocity
        self.content_velocity_tracker = {}
        
        # Review queue
        self.review_queue = []
    
    async def assess_content_quality(self,
                                     content_id: str,
                                     content: str,
                                     title: str = "",
                                     meta_description: str = "",
                                     target_keywords: List[str] = None,
                                     citations: List[str] = None,
                                     author_credentials: List[str] = None,
                                     content_category: ContentCategory = ContentCategory.GENERAL) -> QualityScore:
        """Assess content quality and determine if review is needed."""
        
        logger.info(f"Assessing quality for content {content_id}")
        
        # Calculate quality score
        quality_score = self.quality_scorer.score_content(
            content=content,
            title=title,
            meta_description=meta_description,
            target_keywords=target_keywords,
            citations=citations,
            author_credentials=author_credentials,
            content_category=content_category
        )
        
        # Check for similarity with existing content
        similar_content = self.similarity_detector.find_similar_content(content, content_id)
        
        # Add content to similarity index
        self.similarity_detector.add_content(content_id, content, url="")
        
        # Determine if human review is required
        needs_review = self._requires_human_review(quality_score, content_category, similar_content)
        
        if needs_review:
            await self._add_to_review_queue(
                content_id, content, title, quality_score, content_category, similar_content
            )
        
        return quality_score
    
    def _requires_human_review(self,
                               quality_score: QualityScore,
                               content_category: ContentCategory,
                               similar_content: List[ContentSimilarity]) -> bool:
        """Determine if content requires human review."""
        
        # Always review YMYL content
        if content_category in [ContentCategory.YMYL, ContentCategory.MEDICAL, 
                               ContentCategory.LEGAL, ContentCategory.FINANCIAL]:
            return True
        
        # Review if quality score is below threshold
        if quality_score.overall_score < self.governance_config.quality_score_minimum:
            return True
        
        # Review if spam signals detected
        if quality_score.spam_signals:
            return True
        
        # Review if high similarity detected
        for similarity in similar_content:
            if similarity.similarity_score >= 0.9:
                return True
        
        return False
    
    async def _add_to_review_queue(self,
                                   content_id: str,
                                   content: str,
                                   title: str,
                                   quality_score: QualityScore,
                                   content_category: ContentCategory,
                                   similar_content: List[ContentSimilarity]):
        """Add content to review queue."""
        
        # Determine priority
        if quality_score.quality_level == ContentQualityLevel.SPAM:
            priority = ReviewPriority.URGENT
        elif content_category in [ContentCategory.YMYL, ContentCategory.MEDICAL, ContentCategory.LEGAL]:
            priority = ReviewPriority.HIGH
        elif quality_score.overall_score < 5.0:
            priority = ReviewPriority.MEDIUM
        else:
            priority = ReviewPriority.LOW
        
        # Estimate review time
        estimated_time = self._estimate_review_time(quality_score, content_category)
        
        # Create review task
        review_task = ReviewTask(
            id=f"review_{content_id}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
            content_id=content_id,
            content_url="",  # Would be populated from content metadata
            content_title=title,
            category=content_category,
            priority=priority,
            assigned_reviewer=None,
            requires_expert_review=content_category in [ContentCategory.YMYL, ContentCategory.MEDICAL],
            requires_fact_checking=ContentCategory.MEDICAL in [content_category],
            requires_legal_review=content_category == ContentCategory.LEGAL,
            created_at=datetime.now(timezone.utc),
            due_date=datetime.now(timezone.utc) + timedelta(hours=24 if priority == ReviewPriority.URGENT else 72),
            estimated_review_time=estimated_time,
            quality_score=quality_score.overall_score,
            spam_signals=quality_score.spam_signals,
            similarity_issues=similar_content,
            status="pending",
            reviewer_notes=None,
            resolution=None
        )
        
        self.review_queue.append(review_task)
        
        logger.info(f"Added content {content_id} to review queue with {priority.value} priority")
    
    def _estimate_review_time(self, 
                              quality_score: QualityScore,
                              content_category: ContentCategory) -> int:
        """Estimate review time in minutes."""
        base_time = 15  # Base review time
        
        # Add time for quality issues
        if quality_score.overall_score < 5.0:
            base_time += 10
        
        # Add time for spam signals
        base_time += len(quality_score.spam_signals) * 5
        
        # Add time for complex categories
        if content_category in [ContentCategory.YMYL, ContentCategory.MEDICAL, ContentCategory.LEGAL]:
            base_time += 20
        
        return base_time
    
    async def check_content_velocity(self, project_id: str) -> Dict[str, Union[bool, int, str]]:
        """Check if content velocity limits are exceeded."""
        
        today = datetime.now(timezone.utc).date()
        week_start = today - timedelta(days=today.weekday())
        
        # Track content for this project
        if project_id not in self.content_velocity_tracker:
            self.content_velocity_tracker[project_id] = {}
        
        project_tracker = self.content_velocity_tracker[project_id]
        
        # Count content published this week
        week_content = project_tracker.get(str(week_start), 0)
        daily_content = project_tracker.get(str(today), 0)
        
        # Check limits
        weekly_limit_exceeded = week_content >= self.governance_config.max_programmatic_per_week
        daily_limit_exceeded = daily_content >= self.governance_config.content_velocity_limit
        
        return {
            'weekly_limit_exceeded': weekly_limit_exceeded,
            'daily_limit_exceeded': daily_limit_exceeded,
            'weekly_count': week_content,
            'daily_count': daily_content,
            'weekly_limit': self.governance_config.max_programmatic_per_week,
            'daily_limit': self.governance_config.content_velocity_limit,
            'recommendation': self._get_velocity_recommendation(weekly_limit_exceeded, daily_limit_exceeded)
        }
    
    def _get_velocity_recommendation(self, weekly_exceeded: bool, daily_exceeded: bool) -> str:
        """Get recommendation based on velocity limits."""
        if weekly_exceeded and daily_exceeded:
            return "Both weekly and daily limits exceeded - pause content creation"
        elif weekly_exceeded:
            return "Weekly limit exceeded - reduce content velocity"
        elif daily_exceeded:
            return "Daily limit exceeded - pause content creation for today"
        else:
            return "Content velocity within acceptable limits"
    
    async def get_review_queue_status(self) -> Dict[str, Union[int, List[Dict]]]:
        """Get current review queue status."""
        
        # Count by priority
        priority_counts = {
            ReviewPriority.URGENT: 0,
            ReviewPriority.HIGH: 0,
            ReviewPriority.MEDIUM: 0,
            ReviewPriority.LOW: 0
        }
        
        # Count by status
        status_counts = {}
        
        # Overdue tasks
        overdue_tasks = []
        now = datetime.now(timezone.utc)
        
        for task in self.review_queue:
            priority_counts[task.priority] += 1
            status_counts[task.status] = status_counts.get(task.status, 0) + 1
            
            if task.due_date < now and task.status == 'pending':
                overdue_tasks.append({
                    'id': task.id,
                    'content_title': task.content_title,
                    'priority': task.priority.value,
                    'days_overdue': (now - task.due_date).days
                })
        
        return {
            'total_tasks': len(self.review_queue),
            'priority_breakdown': {p.value: count for p, count in priority_counts.items()},
            'status_breakdown': status_counts,
            'overdue_count': len(overdue_tasks),
            'overdue_tasks': overdue_tasks,
            'avg_wait_time_hours': self._calculate_avg_wait_time()
        }
    
    def _calculate_avg_wait_time(self) -> float:
        """Calculate average wait time for review tasks."""
        if not self.review_queue:
            return 0.0
        
        now = datetime.now(timezone.utc)
        total_wait_time = 0
        pending_count = 0
        
        for task in self.review_queue:
            if task.status == 'pending':
                wait_time = (now - task.created_at).total_seconds() / 3600  # hours
                total_wait_time += wait_time
                pending_count += 1
        
        return total_wait_time / pending_count if pending_count > 0 else 0.0
    
    async def export_quality_report(self, 
                                    project_id: str,
                                    output_path: Path) -> bool:
        """Export quality governance report."""
        try:
            # Get review queue status
            queue_status = await self.get_review_queue_status()
            
            # Get velocity status
            velocity_status = await self.check_content_velocity(project_id)
            
            report_data = {
                'project_id': project_id,
                'report_date': datetime.now(timezone.utc).isoformat(),
                'governance_config': {
                    'quality_score_minimum': self.governance_config.quality_score_minimum,
                    'similarity_threshold': self.governance_config.similarity_threshold,
                    'max_programmatic_per_week': self.governance_config.max_programmatic_per_week,
                    'content_velocity_limit': self.governance_config.content_velocity_limit
                },
                'review_queue_status': queue_status,
                'content_velocity_status': velocity_status,
                'recommendations': self._generate_governance_recommendations(queue_status, velocity_status)
            }
            
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                import json
                json.dump(report_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Quality governance report exported to {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export quality report: {e}")
            return False
    
    def _generate_governance_recommendations(self, 
                                             queue_status: Dict,
                                             velocity_status: Dict) -> List[str]:
        """Generate governance recommendations."""
        recommendations = []
        
        # Review queue recommendations
        if queue_status['overdue_count'] > 0:
            recommendations.append(f"Address {queue_status['overdue_count']} overdue review tasks")
        
        if queue_status['priority_breakdown']['urgent'] > 0:
            recommendations.append("Prioritize urgent review tasks immediately")
        
        if queue_status['avg_wait_time_hours'] > 48:
            recommendations.append("Review queue backlog is high - consider additional reviewers")
        
        # Velocity recommendations
        if velocity_status['weekly_limit_exceeded']:
            recommendations.append("Reduce content creation velocity to maintain quality")
        
        if velocity_status['daily_limit_exceeded']:
            recommendations.append("Daily content limit exceeded - implement content throttling")
        
        return recommendations


async def run_quality_audit(project_id: str,
                            content_id: str,
                            content: str,
                            settings: Settings,
                            governance_config: GovernanceConfig) -> QualityScore:
    """Run quality audit for content."""
    
    manager = QualityGovernanceManager(settings, governance_config)
    
    quality_score = await manager.assess_content_quality(
        content_id=content_id,
        content=content,
        content_category=ContentCategory.GENERAL
    )
    
    logger.info(f"Quality audit completed for {content_id}: {quality_score.overall_score:.1f}/10")
    
    return quality_score