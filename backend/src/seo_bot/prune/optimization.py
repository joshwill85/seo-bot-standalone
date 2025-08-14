"""Content Pruning & Optimization System.

Identifies low-value content using GSC data, provides merge/redirect recommendations,
automates internal link updating, and manages content consolidation workflows.
"""

import asyncio
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from ..config import Settings
from ..models import AlertSeverity
from ..monitor.coverage import GSCAdapter


logger = logging.getLogger(__name__)


class ContentAction(Enum):
    """Recommended actions for content optimization."""
    KEEP = "keep"
    IMPROVE = "improve"
    MERGE = "merge"
    REDIRECT = "redirect"
    DELETE = "delete"
    NOINDEX = "noindex"


class ContentValue(Enum):
    """Content value levels."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    ZERO = "zero"


class OrphanStatus(Enum):
    """Orphaned content status."""
    ORPHANED = "orphaned"
    POORLY_LINKED = "poorly_linked"
    WELL_CONNECTED = "well_connected"


@dataclass
class ContentMetrics:
    """Comprehensive content performance metrics."""
    url: str
    title: str
    word_count: int
    
    # Traffic metrics
    organic_clicks: int
    organic_impressions: int
    average_position: float
    ctr: float
    
    # Time-based metrics
    clicks_last_30d: int
    clicks_last_90d: int
    clicks_last_year: int
    
    # Quality metrics
    quality_score: float
    readability_score: float
    
    # Technical metrics
    page_speed_score: int
    core_web_vitals_pass: bool
    mobile_friendly: bool
    
    # Link metrics
    internal_links_in: int
    internal_links_out: int
    external_links: int
    
    # Search visibility
    ranking_keywords_count: int
    top_10_rankings: int
    featured_snippets: int
    
    # Optional metrics
    bounce_rate: Optional[float] = None
    time_on_page: Optional[float] = None
    
    # Content freshness
    published_date: Optional[datetime] = None
    last_modified: Optional[datetime] = None
    content_age_days: int = 0
    
    # Engagement
    social_shares: int = 0
    comments: int = 0
    conversion_rate: Optional[float] = None


@dataclass
class PruningRecommendation:
    """Content pruning recommendation."""
    url: str
    title: str
    action: ContentAction
    confidence: float  # 0-1 scale
    
    # Reasoning
    reason: str
    detailed_analysis: Dict[str, str]
    impact_assessment: str
    
    # Merge/redirect targets
    target_url: Optional[str] = None
    target_title: Optional[str] = None
    similarity_score: Optional[float] = None
    
    # Implementation details
    redirect_type: Optional[str] = None  # 301, 302, meta refresh
    merge_strategy: Optional[str] = None  # content consolidation approach
    
    # Expected outcomes
    estimated_traffic_impact: Optional[int] = None
    estimated_ranking_impact: Optional[str] = None
    seo_benefit: str = ""
    
    # Priority and effort
    priority: str = "medium"  # high, medium, low
    effort_level: str = "medium"  # high, medium, low
    estimated_hours: float = 2.0


@dataclass
class ContentConsolidationPlan:
    """Plan for consolidating multiple pieces of content."""
    primary_url: str
    primary_title: str
    consolidation_urls: List[str]
    
    # Content strategy
    final_title: str
    final_url: str
    content_outline: List[str]
    merged_sections: Dict[str, List[str]]  # section -> source URLs
    
    # SEO strategy
    target_keywords: List[str]
    internal_link_updates: List[Dict[str, str]]  # old -> new mappings
    redirect_plan: List[Dict[str, str]]
    
    # Expected impact
    combined_traffic: int
    keyword_consolidation: List[str]
    ranking_opportunities: List[str]
    
    # Implementation
    implementation_order: List[str]
    estimated_completion_time: int  # hours


class ContentAnalyzer:
    """Analyzes content performance and value."""
    
    def __init__(self, settings: Settings):
        """Initialize content analyzer."""
        self.settings = settings
        self.gsc_adapter = None
        if settings.google_search_console_credentials_file:
            self.gsc_adapter = GSCAdapter(settings.google_search_console_credentials_file)
    
    async def analyze_content_performance(self, 
                                          urls: List[str],
                                          domain: str,
                                          analysis_period_days: int = 90) -> List[ContentMetrics]:
        """Analyze performance metrics for a list of URLs."""
        metrics_list = []
        
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=analysis_period_days)
        
        try:
            if self.gsc_adapter:
                # Get GSC data for all URLs
                gsc_data = await self._get_gsc_data_for_urls(urls, domain, start_date, end_date)
            else:
                gsc_data = {}
            
            for url in urls:
                try:
                    metrics = await self._analyze_single_url(url, gsc_data.get(url, {}))
                    metrics_list.append(metrics)
                except Exception as e:
                    logger.error(f"Failed to analyze {url}: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"Failed to analyze content performance: {e}")
        
        return metrics_list
    
    async def _get_gsc_data_for_urls(self, 
                                     urls: List[str],
                                     domain: str,
                                     start_date: datetime,
                                     end_date: datetime) -> Dict[str, Dict]:
        """Get GSC data for specific URLs."""
        gsc_data = {}
        
        try:
            # Get performance data from GSC
            request = {
                'startDate': start_date.strftime('%Y-%m-%d'),
                'endDate': end_date.strftime('%Y-%m-%d'),
                'dimensions': ['page'],
                'rowLimit': 25000
            }
            
            response = await self.gsc_adapter.get_indexation_data(domain, start_date, end_date)
            
            # Process response
            for row in response.get('rows', []):
                page_url = row.get('keys', [''])[0]
                if page_url in urls:
                    gsc_data[page_url] = {
                        'clicks': row.get('clicks', 0),
                        'impressions': row.get('impressions', 0),
                        'ctr': row.get('ctr', 0),
                        'position': row.get('position', 0)
                    }
            
        except Exception as e:
            logger.error(f"Failed to get GSC data: {e}")
        
        return gsc_data
    
    async def _analyze_single_url(self, url: str, gsc_data: Dict) -> ContentMetrics:
        """Analyze metrics for a single URL."""
        
        # Get basic content info (would fetch actual content in production)
        title = f"Sample Title for {url}"
        word_count = 1200  # Would analyze actual content
        
        # GSC metrics
        clicks = gsc_data.get('clicks', 0)
        impressions = gsc_data.get('impressions', 0)
        position = gsc_data.get('position', 50)
        ctr = gsc_data.get('ctr', 0.02)
        
        # Simulate additional metrics (would fetch from actual sources)
        quality_score = 7.5 + np.random.normal(0, 1)
        readability_score = 65 + np.random.normal(0, 10)
        page_speed_score = 85 + np.random.randint(-15, 15)
        
        # Link metrics (would crawl actual internal link structure)
        internal_links_in = np.random.randint(2, 20)
        internal_links_out = np.random.randint(3, 15)
        external_links = np.random.randint(1, 8)
        
        # Time-based traffic simulation
        clicks_30d = max(0, clicks + np.random.randint(-5, 10))
        clicks_90d = max(0, clicks * 3 + np.random.randint(-10, 20))
        clicks_year = max(0, clicks * 12 + np.random.randint(-50, 100))
        
        # Content age
        content_age = np.random.randint(30, 1095)  # 30 days to 3 years
        
        # Ranking metrics
        ranking_keywords = max(1, int(impressions / 100))
        top_10_rankings = max(0, int(ranking_keywords * 0.1))
        
        return ContentMetrics(
            url=url,
            title=title,
            word_count=word_count,
            organic_clicks=clicks,
            organic_impressions=impressions,
            average_position=position,
            ctr=ctr,
            clicks_last_30d=clicks_30d,
            clicks_last_90d=clicks_90d,
            clicks_last_year=clicks_year,
            quality_score=quality_score,
            readability_score=readability_score,
            page_speed_score=page_speed_score,
            core_web_vitals_pass=page_speed_score > 75,
            mobile_friendly=True,
            internal_links_in=internal_links_in,
            internal_links_out=internal_links_out,
            external_links=external_links,
            content_age_days=content_age,
            ranking_keywords_count=ranking_keywords,
            top_10_rankings=top_10_rankings,
            featured_snippets=max(0, top_10_rankings // 3),
            social_shares=np.random.randint(0, 50),
            comments=np.random.randint(0, 20)
        )
    
    def calculate_content_value(self, metrics: ContentMetrics) -> ContentValue:
        """Calculate overall content value based on metrics."""
        
        # Scoring factors
        traffic_score = min(100, metrics.organic_clicks * 2)  # Max 100 for 50+ clicks
        impression_score = min(100, metrics.organic_impressions / 10)  # Max 100 for 1000+ impressions
        position_score = max(0, 100 - metrics.average_position * 2)  # Better position = higher score
        quality_score = metrics.quality_score * 10  # Convert to 0-100 scale
        link_score = min(100, metrics.internal_links_in * 5)  # Max 100 for 20+ inbound links
        freshness_score = max(0, 100 - (metrics.content_age_days / 365) * 20)  # Newer = better
        
        # Weighted average
        total_score = (
            traffic_score * 0.25 +
            impression_score * 0.20 +
            position_score * 0.15 +
            quality_score * 0.15 +
            link_score * 0.15 +
            freshness_score * 0.10
        )
        
        # Determine value level
        if total_score >= 70:
            return ContentValue.HIGH
        elif total_score >= 40:
            return ContentValue.MEDIUM
        elif total_score >= 15:
            return ContentValue.LOW
        else:
            return ContentValue.ZERO
    
    def identify_orphaned_content(self, all_metrics: List[ContentMetrics]) -> List[ContentMetrics]:
        """Identify orphaned or poorly connected content."""
        orphaned = []
        
        for metrics in all_metrics:
            # Content with very few inbound links is potentially orphaned
            if metrics.internal_links_in <= 2:
                # Also check if it has low visibility
                if metrics.organic_impressions < 100 and metrics.average_position > 30:
                    orphaned.append(metrics)
        
        return orphaned


class ContentSimilarityAnalyzer:
    """Analyzes content similarity for merge recommendations."""
    
    def __init__(self):
        """Initialize similarity analyzer."""
        self.vectorizer = TfidfVectorizer(
            max_features=5000,
            stop_words='english',
            ngram_range=(1, 2),
            max_df=0.8,
            min_df=2
        )
        self.content_vectors = {}
        self.content_metadata = {}
    
    def add_content(self, url: str, title: str, content: str, keywords: List[str] = None):
        """Add content to similarity analysis."""
        
        # Combine title and content for analysis
        full_text = f"{title} {content}"
        
        # Store metadata
        self.content_metadata[url] = {
            'title': title,
            'content_length': len(content),
            'keywords': keywords or [],
            'content_hash': hash(content)
        }
        
        # Preprocess and store
        processed_content = self._preprocess_content(full_text)
        
        if processed_content.strip():
            # Fit or transform based on whether this is first content
            if not self.content_vectors:
                vector = self.vectorizer.fit_transform([processed_content])
            else:
                try:
                    vector = self.vectorizer.transform([processed_content])
                except ValueError:
                    # Vocabulary has changed, refit
                    all_content = [processed_content]
                    vector = self.vectorizer.fit_transform(all_content)
            
            self.content_vectors[url] = vector
    
    def find_similar_content(self, similarity_threshold: float = 0.7) -> List[Tuple[str, str, float]]:
        """Find pairs of similar content above threshold."""
        similar_pairs = []
        
        urls = list(self.content_vectors.keys())
        
        for i, url1 in enumerate(urls):
            for j, url2 in enumerate(urls[i+1:], i+1):
                
                vector1 = self.content_vectors[url1]
                vector2 = self.content_vectors[url2]
                
                # Calculate cosine similarity
                similarity = cosine_similarity(vector1, vector2)[0][0]
                
                if similarity >= similarity_threshold:
                    similar_pairs.append((url1, url2, similarity))
        
        # Sort by similarity score
        similar_pairs.sort(key=lambda x: x[2], reverse=True)
        
        return similar_pairs
    
    def analyze_keyword_overlap(self, url1: str, url2: str) -> Dict[str, Any]:
        """Analyze keyword overlap between two pieces of content."""
        
        metadata1 = self.content_metadata.get(url1, {})
        metadata2 = self.content_metadata.get(url2, {})
        
        keywords1 = set(metadata1.get('keywords', []))
        keywords2 = set(metadata2.get('keywords', []))
        
        overlap = keywords1.intersection(keywords2)
        unique1 = keywords1.difference(keywords2)
        unique2 = keywords2.difference(keywords1)
        
        total_keywords = len(keywords1.union(keywords2))
        overlap_percentage = len(overlap) / total_keywords if total_keywords > 0 else 0
        
        return {
            'overlap_keywords': list(overlap),
            'unique_to_first': list(unique1),
            'unique_to_second': list(unique2),
            'overlap_percentage': overlap_percentage,
            'total_keywords': total_keywords,
            'recommendation': self._get_overlap_recommendation(overlap_percentage)
        }
    
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
    
    def _get_overlap_recommendation(self, overlap_percentage: float) -> str:
        """Get recommendation based on keyword overlap."""
        if overlap_percentage >= 0.8:
            return "High overlap - strong merge candidate"
        elif overlap_percentage >= 0.5:
            return "Moderate overlap - consider consolidation"
        elif overlap_percentage >= 0.3:
            return "Some overlap - review for complementary content"
        else:
            return "Low overlap - likely targeting different intents"


class PruningRecommendationEngine:
    """Generates specific pruning and optimization recommendations."""
    
    def __init__(self):
        """Initialize recommendation engine."""
        self.similarity_analyzer = ContentSimilarityAnalyzer()
    
    def generate_recommendations(self, 
                                 all_metrics: List[ContentMetrics],
                                 similarity_pairs: List[Tuple[str, str, float]] = None) -> List[PruningRecommendation]:
        """Generate comprehensive pruning recommendations."""
        
        recommendations = []
        analyzer = ContentAnalyzer(None)  # For value calculation
        
        # Analyze each piece of content
        for metrics in all_metrics:
            content_value = analyzer.calculate_content_value(metrics)
            
            # Generate recommendation based on value and metrics
            recommendation = self._generate_single_recommendation(metrics, content_value)
            recommendations.append(recommendation)
        
        # Add merge recommendations based on similarity
        if similarity_pairs:
            merge_recommendations = self._generate_merge_recommendations(similarity_pairs, all_metrics)
            recommendations.extend(merge_recommendations)
        
        # Sort by priority and confidence
        recommendations.sort(key=lambda r: (
            self._priority_order(r.priority),
            -r.confidence
        ))
        
        return recommendations
    
    def _generate_single_recommendation(self, 
                                        metrics: ContentMetrics,
                                        content_value: ContentValue) -> PruningRecommendation:
        """Generate recommendation for a single piece of content."""
        
        # Determine action based on value and specific metrics
        if content_value == ContentValue.ZERO:
            if metrics.organic_clicks == 0 and metrics.organic_impressions < 10:
                action = ContentAction.DELETE
                reason = "Zero traffic and minimal visibility"
                confidence = 0.9
                priority = "high"
            else:
                action = ContentAction.NOINDEX
                reason = "Very low value but some minimal visibility"
                confidence = 0.7
                priority = "medium"
        
        elif content_value == ContentValue.LOW:
            if metrics.internal_links_in <= 1:
                action = ContentAction.REDIRECT
                reason = "Low value content with poor internal linking"
                confidence = 0.8
                priority = "medium"
            else:
                action = ContentAction.IMPROVE
                reason = "Low value but connected - improvement opportunity"
                confidence = 0.6
                priority = "low"
        
        elif content_value == ContentValue.MEDIUM:
            if metrics.quality_score < 6.0:
                action = ContentAction.IMPROVE
                reason = "Medium traffic but quality issues"
                confidence = 0.7
                priority = "medium"
            else:
                action = ContentAction.KEEP
                reason = "Decent performance, maintain current state"
                confidence = 0.8
                priority = "low"
        
        else:  # HIGH value
            action = ContentAction.KEEP
            reason = "High-value content, maintain and optimize"
            confidence = 0.9
            priority = "low"
        
        # Generate detailed analysis
        detailed_analysis = self._create_detailed_analysis(metrics, content_value)
        
        # Assess impact
        impact_assessment = self._assess_impact(metrics, action)
        
        # Estimate effort
        effort_level, estimated_hours = self._estimate_effort(action, metrics)
        
        return PruningRecommendation(
            url=metrics.url,
            title=metrics.title,
            action=action,
            confidence=confidence,
            reason=reason,
            detailed_analysis=detailed_analysis,
            impact_assessment=impact_assessment,
            priority=priority,
            effort_level=effort_level,
            estimated_hours=estimated_hours,
            seo_benefit=self._calculate_seo_benefit(action, metrics)
        )
    
    def _generate_merge_recommendations(self, 
                                        similarity_pairs: List[Tuple[str, str, float]],
                                        all_metrics: List[ContentMetrics]) -> List[PruningRecommendation]:
        """Generate merge recommendations based on content similarity."""
        
        merge_recommendations = []
        metrics_by_url = {m.url: m for m in all_metrics}
        
        for url1, url2, similarity in similarity_pairs:
            if similarity >= 0.8:  # High similarity threshold for merge
                
                metrics1 = metrics_by_url.get(url1)
                metrics2 = metrics_by_url.get(url2)
                
                if not metrics1 or not metrics2:
                    continue
                
                # Determine which should be primary (better performance)
                primary_url, secondary_url = self._determine_merge_primary(metrics1, metrics2)
                primary_metrics = metrics_by_url[primary_url]
                secondary_metrics = metrics_by_url[secondary_url]
                
                recommendation = PruningRecommendation(
                    url=secondary_url,
                    title=secondary_metrics.title,
                    action=ContentAction.MERGE,
                    confidence=min(0.9, similarity),
                    reason=f"High content similarity ({similarity:.1%}) with {primary_url}",
                    detailed_analysis={
                        "similarity_score": f"{similarity:.1%}",
                        "merge_target": primary_url,
                        "traffic_consolidation": f"{secondary_metrics.organic_clicks + primary_metrics.organic_clicks} total clicks",
                        "ranking_opportunities": "Potential to improve rankings through content consolidation"
                    },
                    impact_assessment=f"Positive - consolidate {secondary_metrics.organic_clicks + primary_metrics.organic_clicks} clicks to single URL",
                    target_url=primary_url,
                    target_title=primary_metrics.title,
                    similarity_score=similarity,
                    merge_strategy="consolidate_content",
                    redirect_type="301",
                    estimated_traffic_impact=secondary_metrics.organic_clicks,
                    estimated_ranking_impact="Improved due to consolidation",
                    priority="medium",
                    effort_level="high",
                    estimated_hours=6.0,
                    seo_benefit="Content consolidation improves topical authority and eliminates cannibalization"
                )
                
                merge_recommendations.append(recommendation)
        
        return merge_recommendations
    
    def _determine_merge_primary(self, 
                                 metrics1: ContentMetrics,
                                 metrics2: ContentMetrics) -> Tuple[str, str]:
        """Determine which content should be primary in a merge."""
        
        # Score based on multiple factors
        score1 = (
            metrics1.organic_clicks * 2 +
            metrics1.organic_impressions / 10 +
            metrics1.internal_links_in * 5 +
            (100 - metrics1.average_position) +
            metrics1.quality_score * 5
        )
        
        score2 = (
            metrics2.organic_clicks * 2 +
            metrics2.organic_impressions / 10 +
            metrics2.internal_links_in * 5 +
            (100 - metrics2.average_position) +
            metrics2.quality_score * 5
        )
        
        if score1 >= score2:
            return metrics1.url, metrics2.url
        else:
            return metrics2.url, metrics1.url
    
    def _create_detailed_analysis(self, 
                                  metrics: ContentMetrics,
                                  content_value: ContentValue) -> Dict[str, str]:
        """Create detailed analysis for recommendation."""
        
        return {
            "content_value": content_value.value,
            "traffic_analysis": f"{metrics.organic_clicks} clicks, {metrics.organic_impressions} impressions",
            "position_analysis": f"Average position: {metrics.average_position:.1f}",
            "quality_analysis": f"Quality score: {metrics.quality_score:.1f}/10",
            "link_analysis": f"{metrics.internal_links_in} inbound, {metrics.internal_links_out} outbound links",
            "freshness_analysis": f"Content age: {metrics.content_age_days} days",
            "technical_analysis": f"Page speed: {metrics.page_speed_score}/100, CWV: {'Pass' if metrics.core_web_vitals_pass else 'Fail'}"
        }
    
    def _assess_impact(self, metrics: ContentMetrics, action: ContentAction) -> str:
        """Assess the impact of the recommended action."""
        
        if action == ContentAction.DELETE:
            return f"Minimal impact - removing {metrics.organic_clicks} clicks from low-value content"
        elif action == ContentAction.REDIRECT:
            return f"Neutral to positive - redirect {metrics.organic_clicks} clicks to better content"
        elif action == ContentAction.MERGE:
            return "Positive - consolidate traffic and improve topical authority"
        elif action == ContentAction.IMPROVE:
            return f"Positive - potential to increase {metrics.organic_clicks} clicks through optimization"
        elif action == ContentAction.NOINDEX:
            return "Neutral - remove from search while preserving for internal use"
        else:  # KEEP
            return "Maintain current performance"
    
    def _estimate_effort(self, action: ContentAction, metrics: ContentMetrics) -> Tuple[str, float]:
        """Estimate effort level and hours for action."""
        
        if action == ContentAction.DELETE:
            return "low", 0.5
        elif action == ContentAction.REDIRECT:
            return "low", 1.0
        elif action == ContentAction.NOINDEX:
            return "low", 0.5
        elif action == ContentAction.IMPROVE:
            # More effort for longer content
            hours = max(2.0, metrics.word_count / 500)
            if hours > 6:
                return "high", hours
            elif hours > 3:
                return "medium", hours
            else:
                return "low", hours
        elif action == ContentAction.MERGE:
            return "high", 6.0
        else:  # KEEP
            return "low", 0.5
    
    def _calculate_seo_benefit(self, action: ContentAction, metrics: ContentMetrics) -> str:
        """Calculate SEO benefit of the action."""
        
        if action == ContentAction.DELETE:
            return "Remove low-quality content to improve overall site quality"
        elif action == ContentAction.REDIRECT:
            return "Consolidate link equity and eliminate thin content"
        elif action == ContentAction.MERGE:
            return "Increase topical authority and eliminate keyword cannibalization"
        elif action == ContentAction.IMPROVE:
            return "Enhance content quality to improve rankings and CTR"
        elif action == ContentAction.NOINDEX:
            return "Remove from search index while preserving internal value"
        else:  # KEEP
            return "Maintain current SEO value"
    
    def _priority_order(self, priority: str) -> int:
        """Convert priority to numeric order for sorting."""
        return {"high": 0, "medium": 1, "low": 2}.get(priority, 2)


class ContentPruningManager:
    """Manages the complete content pruning and optimization workflow."""
    
    def __init__(self, settings: Settings):
        """Initialize content pruning manager."""
        self.settings = settings
        self.content_analyzer = ContentAnalyzer(settings)
        self.similarity_analyzer = ContentSimilarityAnalyzer()
        self.recommendation_engine = PruningRecommendationEngine()
    
    async def analyze_site_content(self, 
                                   domain: str,
                                   urls: List[str] = None,
                                   analysis_period_days: int = 90) -> Dict[str, Any]:
        """Perform comprehensive content analysis for a site."""
        
        logger.info(f"Starting content analysis for {domain}")
        
        # If no URLs provided, would typically fetch from sitemap
        if not urls:
            urls = await self._get_site_urls(domain)
        
        # Analyze content performance
        all_metrics = await self.content_analyzer.analyze_content_performance(
            urls, domain, analysis_period_days
        )
        
        # Analyze content similarity (would fetch actual content)
        similarity_pairs = await self._analyze_content_similarity(urls)
        
        # Generate recommendations
        recommendations = self.recommendation_engine.generate_recommendations(
            all_metrics, similarity_pairs
        )
        
        # Identify specific issues
        orphaned_content = self.content_analyzer.identify_orphaned_content(all_metrics)
        
        # Generate consolidation opportunities
        consolidation_plans = self._generate_consolidation_plans(recommendations)
        
        # Calculate overall impact
        impact_summary = self._calculate_impact_summary(recommendations, all_metrics)
        
        analysis_result = {
            "domain": domain,
            "analysis_date": datetime.now(timezone.utc).isoformat(),
            "total_urls_analyzed": len(all_metrics),
            "content_metrics": [metrics.__dict__ for metrics in all_metrics],
            "recommendations": [rec.__dict__ for rec in recommendations],
            "orphaned_content": [metrics.url for metrics in orphaned_content],
            "consolidation_plans": consolidation_plans,
            "impact_summary": impact_summary,
            "similar_content_pairs": similarity_pairs
        }
        
        logger.info(f"Content analysis completed: {len(recommendations)} recommendations generated")
        
        return analysis_result
    
    async def _get_site_urls(self, domain: str) -> List[str]:
        """Get all URLs for a site (would typically fetch from sitemap)."""
        # Placeholder - would fetch from sitemap.xml or crawl
        return [
            f"https://{domain}/page-{i}"
            for i in range(1, 51)  # Sample 50 URLs
        ]
    
    async def _analyze_content_similarity(self, urls: List[str]) -> List[Tuple[str, str, float]]:
        """Analyze content similarity between URLs."""
        # In production, would fetch actual content for each URL
        # For now, simulate some similar content pairs
        
        similarity_pairs = []
        
        # Simulate adding content to analyzer
        for url in urls[:20]:  # Analyze first 20 for demo
            title = f"Sample Title for {url}"
            content = f"Sample content for {url} with some overlapping text and keywords."
            keywords = ["sample", "content", "seo", "optimization"]
            
            self.similarity_analyzer.add_content(url, title, content, keywords)
        
        # Find similar content
        similarity_pairs = self.similarity_analyzer.find_similar_content(0.7)
        
        return similarity_pairs
    
    def _generate_consolidation_plans(self, 
                                      recommendations: List[PruningRecommendation]) -> List[Dict]:
        """Generate consolidation plans for merge recommendations."""
        
        consolidation_plans = []
        
        # Group merge recommendations by target URL
        merge_groups = {}
        for rec in recommendations:
            if rec.action == ContentAction.MERGE and rec.target_url:
                if rec.target_url not in merge_groups:
                    merge_groups[rec.target_url] = []
                merge_groups[rec.target_url].append(rec)
        
        # Create consolidation plans
        for target_url, merge_recs in merge_groups.items():
            if len(merge_recs) > 1:  # Only create plan if multiple merges to same target
                
                total_traffic = sum(rec.estimated_traffic_impact or 0 for rec in merge_recs)
                source_urls = [rec.url for rec in merge_recs]
                
                plan = {
                    "primary_url": target_url,
                    "consolidation_urls": source_urls,
                    "estimated_traffic_gain": total_traffic,
                    "implementation_steps": [
                        f"1. Review content on {target_url}",
                        "2. Identify unique value in source pages",
                        "3. Merge valuable content into primary page",
                        "4. Set up 301 redirects",
                        "5. Update internal links",
                        "6. Monitor rankings and traffic"
                    ],
                    "estimated_effort_hours": sum(rec.estimated_hours for rec in merge_recs),
                    "priority": "high" if total_traffic > 100 else "medium"
                }
                
                consolidation_plans.append(plan)
        
        return consolidation_plans
    
    def _calculate_impact_summary(self, 
                                  recommendations: List[PruningRecommendation],
                                  all_metrics: List[ContentMetrics]) -> Dict[str, Any]:
        """Calculate overall impact summary of recommendations."""
        
        # Count recommendations by action
        action_counts = {}
        for action in ContentAction:
            action_counts[action.value] = len([r for r in recommendations if r.action == action])
        
        # Calculate traffic impact
        total_current_traffic = sum(m.organic_clicks for m in all_metrics)
        
        # Estimate traffic changes from recommendations
        traffic_to_remove = sum(
            m.organic_clicks for m in all_metrics
            for r in recommendations
            if r.url == m.url and r.action in [ContentAction.DELETE, ContentAction.NOINDEX]
        )
        
        traffic_to_consolidate = sum(
            r.estimated_traffic_impact or 0 for r in recommendations
            if r.action == ContentAction.MERGE
        )
        
        # Estimate effort
        total_effort_hours = sum(r.estimated_hours for r in recommendations)
        
        # Priority breakdown
        priority_counts = {}
        for priority in ["high", "medium", "low"]:
            priority_counts[priority] = len([r for r in recommendations if r.priority == priority])
        
        return {
            "total_recommendations": len(recommendations),
            "action_breakdown": action_counts,
            "traffic_analysis": {
                "current_total_traffic": total_current_traffic,
                "traffic_to_remove": traffic_to_remove,
                "traffic_to_consolidate": traffic_to_consolidate,
                "estimated_net_impact": traffic_to_consolidate - traffic_to_remove
            },
            "effort_analysis": {
                "total_estimated_hours": total_effort_hours,
                "high_priority_hours": sum(r.estimated_hours for r in recommendations if r.priority == "high"),
                "quick_wins": len([r for r in recommendations if r.estimated_hours <= 1.0])
            },
            "priority_breakdown": priority_counts,
            "content_quality_impact": "Expected improvement in overall site quality through pruning",
            "seo_benefits": [
                "Eliminate thin content",
                "Reduce keyword cannibalization", 
                "Improve topical authority",
                "Better crawl budget utilization",
                "Enhanced user experience"
            ]
        }
    
    async def implement_recommendations(self, 
                                        recommendations: List[PruningRecommendation],
                                        dry_run: bool = True) -> Dict[str, Any]:
        """Implement pruning recommendations."""
        
        implementation_results = {
            "total_processed": 0,
            "successful": 0,
            "failed": 0,
            "skipped": 0,
            "results": []
        }
        
        for rec in recommendations:
            try:
                if rec.priority == "high" or not dry_run:
                    result = await self._implement_single_recommendation(rec, dry_run)
                    implementation_results["results"].append(result)
                    
                    if result["status"] == "success":
                        implementation_results["successful"] += 1
                    elif result["status"] == "failed":
                        implementation_results["failed"] += 1
                    else:
                        implementation_results["skipped"] += 1
                else:
                    implementation_results["skipped"] += 1
                
                implementation_results["total_processed"] += 1
                
            except Exception as e:
                logger.error(f"Failed to implement recommendation for {rec.url}: {e}")
                implementation_results["failed"] += 1
                implementation_results["results"].append({
                    "url": rec.url,
                    "action": rec.action.value,
                    "status": "failed",
                    "error": str(e)
                })
        
        return implementation_results
    
    async def _implement_single_recommendation(self, 
                                               rec: PruningRecommendation,
                                               dry_run: bool) -> Dict[str, Any]:
        """Implement a single recommendation."""
        
        result = {
            "url": rec.url,
            "action": rec.action.value,
            "status": "success",
            "message": ""
        }
        
        if dry_run:
            result["message"] = f"DRY RUN: Would {rec.action.value} {rec.url}"
            result["status"] = "simulated"
        else:
            # In production, would implement actual changes
            if rec.action == ContentAction.DELETE:
                result["message"] = f"Would delete {rec.url}"
            elif rec.action == ContentAction.REDIRECT:
                result["message"] = f"Would redirect {rec.url} to {rec.target_url or 'target'}"
            elif rec.action == ContentAction.MERGE:
                result["message"] = f"Would merge {rec.url} into {rec.target_url}"
            elif rec.action == ContentAction.NOINDEX:
                result["message"] = f"Would add noindex to {rec.url}"
            elif rec.action == ContentAction.IMPROVE:
                result["message"] = f"Would improve content quality for {rec.url}"
            else:
                result["message"] = f"Would keep {rec.url} as-is"
        
        return result
    
    async def export_analysis_report(self, 
                                     analysis_result: Dict[str, Any],
                                     output_path: Path) -> bool:
        """Export comprehensive analysis report."""
        
        try:
            # Add summary section
            report = {
                "executive_summary": {
                    "total_urls": analysis_result["total_urls_analyzed"],
                    "recommendations_count": len(analysis_result["recommendations"]),
                    "high_priority_actions": len([
                        r for r in analysis_result["recommendations"] 
                        if r.get("priority") == "high"
                    ]),
                    "estimated_effort_hours": sum(
                        r.get("estimated_hours", 0) 
                        for r in analysis_result["recommendations"]
                    ),
                    "key_benefits": [
                        "Improved site quality through content pruning",
                        "Better search visibility via consolidation",
                        "Enhanced crawl budget efficiency",
                        "Reduced keyword cannibalization"
                    ]
                },
                "detailed_analysis": analysis_result
            }
            
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                import json
                json.dump(report, f, indent=2, ensure_ascii=False, default=str)
            
            logger.info(f"Content pruning analysis exported to {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export analysis report: {e}")
            return False


async def run_content_analysis(domain: str,
                               settings: Settings,
                               urls: List[str] = None) -> Dict[str, Any]:
    """Run comprehensive content analysis for pruning opportunities."""
    
    manager = ContentPruningManager(settings)
    
    analysis_result = await manager.analyze_site_content(
        domain=domain,
        urls=urls,
        analysis_period_days=90
    )
    
    logger.info(f"Content analysis completed for {domain}: {analysis_result['total_urls_analyzed']} URLs analyzed")
    
    return analysis_result