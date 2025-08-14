"""SERP gap analysis and content differentiation strategies."""

import json
import re
import statistics
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Set, Tuple
from urllib.parse import urljoin, urlparse

import httpx
import numpy as np

from ..config import settings
from ..logging import get_logger, LoggerMixin


@dataclass
class SERPResult:
    """Individual SERP result data."""
    position: int
    title: str
    url: str
    snippet: str
    domain: str
    word_count: Optional[int] = None
    content: Optional[str] = None
    headings: Optional[List[str]] = None
    entities: Optional[List[str]] = None
    topics: Optional[List[str]] = None


@dataclass
class ContentGap:
    """Content gap analysis result."""
    gap_type: str  # "missing_topic", "insufficient_depth", "missing_entity", "format_gap", "statistical_opportunity"
    description: str
    priority: float  # 0-1 priority score
    competitors_covering: List[str]  # Domains that cover this gap
    suggested_action: str
    evidence: Dict  # Supporting data
    statistical_significance: Optional[float] = None  # p-value for statistical gaps
    confidence_interval: Optional[Tuple[float, float]] = None  # 95% CI for metrics
    information_gain_potential: Optional[float] = None  # Expected unique value score


@dataclass
class SERPAnalysis:
    """Complete SERP analysis results."""
    query: str
    total_results: int
    serp_results: List[SERPResult]
    top_domains: List[str]
    common_entities: List[Tuple[str, int]]  # (entity, frequency)
    common_topics: List[Tuple[str, float]]  # (topic, relevance_score)
    content_gaps: List[ContentGap]
    serp_features: List[str]
    avg_word_count: float
    content_clusters: List[Dict]
    differentiation_opportunities: List[str]


class SERPFetcher:
    """Fetches SERP results from various sources."""
    
    def __init__(self, api_key: Optional[str] = None, provider: str = "serpapi"):
        """Initialize SERP fetcher."""
        self.api_key = api_key or settings.serp_api_key
        self.provider = provider
        self.logger = get_logger(self.__class__.__name__)
        
        if provider == "serpapi":
            self.base_url = "https://serpapi.com/search"
        elif provider == "dataforseo":
            self.base_url = "https://api.dataforseo.com/v3/serp/google/organic/live/regular"
        else:
            self.logger.warning(f"Provider {provider} not fully supported, will use fallback methods")
    
    def fetch_serp_results(
        self,
        query: str,
        location: str = "United States",
        language: str = "en",
        num_results: int = 10
    ) -> List[SERPResult]:
        """
        Fetch SERP results for a query.
        
        Args:
            query: Search query
            location: Geographic location
            language: Search language
            num_results: Number of results to fetch
            
        Returns:
            List of SERP results
        """
        if self.api_key and self.provider == "serpapi":
            return self._fetch_from_serpapi(query, location, language, num_results)
        else:
            # Fallback to scraping (with caution and respect for robots.txt)
            return self._fetch_fallback(query, num_results)
    
    def _fetch_from_serpapi(
        self,
        query: str,
        location: str,
        language: str,
        num_results: int
    ) -> List[SERPResult]:
        """Fetch results using SerpAPI."""
        try:
            params = {
                'engine': 'google',
                'q': query,
                'location': location,
                'hl': language,
                'gl': 'us',
                'num': num_results,
                'api_key': self.api_key
            }
            
            response = httpx.get(self.base_url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            results = []
            
            for i, result in enumerate(data.get('organic_results', [])[:num_results]):
                domain = urlparse(result.get('link', '')).netloc
                
                serp_result = SERPResult(
                    position=i + 1,
                    title=result.get('title', ''),
                    url=result.get('link', ''),
                    snippet=result.get('snippet', ''),
                    domain=domain
                )
                results.append(serp_result)
            
            # Extract SERP features
            serp_features = []
            if data.get('answer_box'):
                serp_features.append('answer_box')
            if data.get('knowledge_graph'):
                serp_features.append('knowledge_graph')
            if data.get('related_questions'):
                serp_features.append('people_also_ask')
            
            self.logger.info(
                f"Fetched {len(results)} SERP results for '{query}'",
                serp_features=serp_features
            )
            
            return results
        
        except Exception as e:
            self.logger.error(f"Failed to fetch SERP results from API: {e}")
            return self._fetch_fallback(query, num_results)
    
    def _fetch_fallback(self, query: str, num_results: int) -> List[SERPResult]:
        """
        Fallback method that returns mock data for testing.
        In production, this could implement basic web scraping with proper rate limiting.
        """
        self.logger.warning(f"Using fallback method for query '{query}' - returning mock data")
        
        # Return mock data for testing purposes
        mock_results = []
        for i in range(min(num_results, 3)):  # Just a few mock results
            mock_results.append(SERPResult(
                position=i + 1,
                title=f"Mock Result {i + 1} for {query}",
                url=f"https://example{i + 1}.com/page",
                snippet=f"This is a mock snippet for result {i + 1} about {query}",
                domain=f"example{i + 1}.com"
            ))
        
        return mock_results


class ContentAnalyzer:
    """Analyzes content from SERP results."""
    
    def __init__(self):
        """Initialize content analyzer."""
        self.logger = get_logger(self.__class__.__name__)
        self.session = httpx.Client(
            timeout=30,
            headers={
                'User-Agent': 'SEO-Bot Content Analyzer 1.0'
            }
        )
    
    def analyze_content(self, serp_result: SERPResult) -> SERPResult:
        """
        Analyze content from a SERP result URL.
        
        Args:
            serp_result: SERP result to analyze
            
        Returns:
            Updated SERP result with content analysis
        """
        try:
            # Import BeautifulSoup when needed
            try:
                from bs4 import BeautifulSoup
            except ImportError:
                self.logger.warning("BeautifulSoup not available, skipping content analysis")
                return serp_result
            
            # Fetch page content
            response = self.session.get(serp_result.url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract text content
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Get main content (try common content selectors)
            content_selectors = [
                'main', 'article', '[role="main"]',
                '.content', '.post-content', '.entry-content',
                '#content', '#main-content'
            ]
            
            content_element = None
            for selector in content_selectors:
                content_element = soup.select_one(selector)
                if content_element:
                    break
            
            if not content_element:
                content_element = soup.body or soup
            
            # Extract text
            content_text = content_element.get_text(separator=' ', strip=True)
            word_count = len(content_text.split())
            
            # Extract headings
            headings = []
            for h_level in range(1, 7):
                for heading in soup.find_all(f'h{h_level}'):
                    if heading.get_text(strip=True):
                        headings.append(heading.get_text(strip=True))
            
            # Update SERP result
            serp_result.content = content_text[:5000]  # Limit content length
            serp_result.word_count = word_count
            serp_result.headings = headings
            
            self.logger.debug(
                f"Analyzed content for {serp_result.domain}",
                word_count=word_count,
                headings_count=len(headings)
            )
            
        except Exception as e:
            self.logger.warning(f"Failed to analyze content for {serp_result.url}: {e}")
        
        return serp_result
    
    def analyze_all_results(self, serp_results: List[SERPResult]) -> List[SERPResult]:
        """Analyze content for all SERP results."""
        analyzed_results = []
        
        for result in serp_results:
            analyzed_result = self.analyze_content(result)
            analyzed_results.append(analyzed_result)
        
        return analyzed_results


class EntityExtractor:
    """Extracts entities and topics from content using advanced NLP."""
    
    # Fallback entity patterns for when spaCy is not available
    ENTITY_PATTERNS = {
        'person': re.compile(r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b'),
        'organization': re.compile(r'\b[A-Z][a-z]+\s+(?:Inc|LLC|Corp|Company|Ltd)\b'),
        'location': re.compile(r'\b(?:New York|California|London|Tokyo|Paris)\b'),
        'date': re.compile(r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b'),
        'money': re.compile(r'\$\d+(?:,\d{3})*(?:\.\d{2})?'),
        'percentage': re.compile(r'\d+(?:\.\d+)?%'),
    }
    
    def __init__(self):
        """Initialize entity extractor."""
        self.logger = get_logger(self.__class__.__name__)
        self.nlp = None
        self._setup_nlp()
    
    def _setup_nlp(self):
        """Setup spaCy NLP pipeline."""
        try:
            import spacy
            # Try to load a pre-trained model
            try:
                self.nlp = spacy.load("en_core_web_sm")
                self.logger.info("Loaded spaCy en_core_web_sm model for entity extraction")
            except OSError:
                try:
                    self.nlp = spacy.load("en_core_web_md")
                    self.logger.info("Loaded spaCy en_core_web_md model for entity extraction")
                except OSError:
                    self.logger.warning("No spaCy models found, falling back to pattern-based extraction")
                    self.nlp = None
        except ImportError:
            self.logger.warning("spaCy not available, using pattern-based entity extraction")
            self.nlp = None
    
    def extract_entities(self, text: str) -> List[str]:
        """
        Extract named entities from text using spaCy NER or fallback patterns.
        
        Args:
            text: Text to analyze
            
        Returns:
            List of extracted entities
        """
        if self.nlp:
            return self._extract_entities_spacy(text)
        else:
            return self._extract_entities_patterns(text)
    
    def _extract_entities_spacy(self, text: str) -> List[str]:
        """Extract entities using spaCy NER."""
        if len(text) > 1000000:  # Limit text size to prevent memory issues
            text = text[:1000000]
        
        doc = self.nlp(text)
        entities = []
        
        # Extract named entities
        for ent in doc.ents:
            if ent.label_ in ['PERSON', 'ORG', 'GPE', 'PRODUCT', 'EVENT', 'WORK_OF_ART', 'LAW']:
                entity_text = ent.text.strip()
                if len(entity_text) > 2 and len(entity_text) < 100:  # Filter reasonable entity lengths
                    entities.append(entity_text)
        
        # Extract noun phrases that might be important concepts
        for chunk in doc.noun_chunks:
            if len(chunk.text) > 3 and len(chunk.text) < 50:
                # Filter for meaningful noun phrases
                if any(token.pos_ in ['NOUN', 'PROPN'] for token in chunk):
                    entities.append(chunk.text.strip())
        
        # Remove duplicates while preserving order
        seen = set()
        unique_entities = []
        for entity in entities:
            entity_lower = entity.lower()
            if entity_lower not in seen and len(entity) > 2:
                seen.add(entity_lower)
                unique_entities.append(entity)
        
        return unique_entities[:30]  # Limit to top 30 entities
    
    def _extract_entities_patterns(self, text: str) -> List[str]:
        """Fallback pattern-based entity extraction."""
        entities = []
        
        for entity_type, pattern in self.ENTITY_PATTERNS.items():
            matches = pattern.findall(text)
            for match in matches:
                entities.append(match.strip())
        
        # Remove duplicates while preserving order
        seen = set()
        unique_entities = []
        for entity in entities:
            if entity not in seen and len(entity) > 2:
                seen.add(entity)
                unique_entities.append(entity)
        
        return unique_entities[:20]  # Limit to top 20 entities
    
    def extract_topics(self, texts: List[str], max_topics: int = 10) -> List[Tuple[str, float]]:
        """
        Extract main topics from a collection of texts using TF-IDF.
        
        Args:
            texts: List of text documents
            max_topics: Maximum number of topics to return
            
        Returns:
            List of (topic, relevance_score) tuples
        """
        if not texts:
            return []
        
        try:
            # Import sklearn when needed
            try:
                from sklearn.feature_extraction.text import TfidfVectorizer
            except ImportError:
                self.logger.warning("sklearn not available, using fallback topic extraction")
                return self._extract_topics_fallback(texts, max_topics)
            
            # Clean texts
            clean_texts = []
            for text in texts:
                if text and len(text.strip()) > 50:
                    clean_texts.append(text.strip())
            
            if len(clean_texts) < 2:
                return []
            
            # Use TF-IDF to find important terms
            vectorizer = TfidfVectorizer(
                max_features=1000,
                ngram_range=(1, 3),
                stop_words='english',
                min_df=2,  # Term must appear in at least 2 documents
                max_df=0.8  # Term must appear in less than 80% of documents
            )
            
            tfidf_matrix = vectorizer.fit_transform(clean_texts)
            feature_names = vectorizer.get_feature_names_out()
            
            # Calculate average TF-IDF scores
            avg_scores = tfidf_matrix.mean(axis=0).A1
            topic_scores = list(zip(feature_names, avg_scores))
            
            # Sort by relevance and filter
            topic_scores.sort(key=lambda x: x[1], reverse=True)
            
            # Filter out very short terms and common words
            filtered_topics = []
            for topic, score in topic_scores:
                if len(topic) > 3 and score > 0.01:
                    filtered_topics.append((topic, float(score)))
                
                if len(filtered_topics) >= max_topics:
                    break
            
            return filtered_topics
        
        except Exception as e:
            self.logger.error(f"Failed to extract topics: {e}")
            return []
    
    def _extract_topics_fallback(self, texts: List[str], max_topics: int) -> List[Tuple[str, float]]:
        """Fallback topic extraction using simple word frequency."""
        word_counts = {}
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with',
            'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'this', 'that',
            'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her',
            'us', 'them', 'my', 'your', 'his', 'her', 'its', 'our', 'their'
        }
        
        for text in texts:
            if text:
                words = re.findall(r'\b\w+\b', text.lower())
                for word in words:
                    if len(word) > 3 and word not in stop_words:
                        word_counts[word] = word_counts.get(word, 0) + 1
        
        # Convert to topics with scores
        total_words = sum(word_counts.values())
        if total_words == 0:
            return []
        
        topics = [(word, count / total_words) for word, count in word_counts.items()]
        topics.sort(key=lambda x: x[1], reverse=True)
        
        return topics[:max_topics]


class StatisticalAnalyzer:
    """Performs statistical analysis on SERP data for gap identification."""
    
    def __init__(self):
        """Initialize statistical analyzer."""
        self.logger = get_logger(self.__class__.__name__)
    
    def calculate_confidence_interval(self, data: List[float], confidence_level: float = 0.95) -> Tuple[float, float]:
        """Calculate confidence interval for a dataset."""
        if len(data) < 2:
            return (0.0, 0.0)
        
        try:
            import scipy.stats as stats
            mean = np.mean(data)
            std_err = stats.sem(data)
            interval = stats.t.interval(confidence_level, len(data) - 1, loc=mean, scale=std_err)
            return interval
        except ImportError:
            # Fallback using manual calculation
            mean = statistics.mean(data)
            std_dev = statistics.stdev(data) if len(data) > 1 else 0
            margin = 1.96 * (std_dev / (len(data) ** 0.5))  # Approximate 95% CI
            return (mean - margin, mean + margin)
    
    def test_statistical_significance(self, sample1: List[float], sample2: List[float]) -> Tuple[float, bool]:
        """Perform t-test to check for statistical significance between two samples."""
        if len(sample1) < 2 or len(sample2) < 2:
            return 1.0, False
        
        try:
            import scipy.stats as stats
            t_stat, p_value = stats.ttest_ind(sample1, sample2)
            is_significant = p_value < 0.05
            return p_value, is_significant
        except ImportError:
            # Fallback using manual calculation
            mean1, mean2 = statistics.mean(sample1), statistics.mean(sample2)
            var1, var2 = statistics.variance(sample1), statistics.variance(sample2)
            n1, n2 = len(sample1), len(sample2)
            
            # Pooled standard error
            pooled_se = ((var1/n1) + (var2/n2)) ** 0.5
            if pooled_se == 0:
                return 1.0, False
            
            t_stat = abs(mean1 - mean2) / pooled_se
            # Rough approximation for p-value
            p_value = max(0.001, 2 * (1 - min(0.999, t_stat / 3)))
            return p_value, p_value < 0.05
    
    def identify_statistical_opportunities(self, serp_results: List[SERPResult]) -> List[Dict]:
        """Identify statistical opportunities in SERP results."""
        opportunities = []
        
        # Analyze word count distribution
        word_counts = [r.word_count for r in serp_results if r.word_count and r.word_count > 0]
        if len(word_counts) >= 3:
            ci = self.calculate_confidence_interval(word_counts)
            mean_words = statistics.mean(word_counts)
            
            opportunities.append({
                'type': 'word_count_analysis',
                'mean_word_count': mean_words,
                'confidence_interval': ci,
                'recommendation': f"Target word count between {int(ci[0])} and {int(ci[1])} words",
                'statistical_confidence': 0.95
            })
        
        # Analyze heading count patterns
        heading_counts = [len(r.headings) for r in serp_results if r.headings]
        if len(heading_counts) >= 3:
            ci = self.calculate_confidence_interval(heading_counts)
            mean_headings = statistics.mean(heading_counts)
            
            opportunities.append({
                'type': 'heading_structure_analysis',
                'mean_heading_count': mean_headings,
                'confidence_interval': ci,
                'recommendation': f"Use {int(ci[0])}-{int(ci[1])} headings for optimal structure",
                'statistical_confidence': 0.95
            })
        
        return opportunities
    
    def calculate_information_gain_potential(self, serp_results: List[SERPResult], target_entities: List[str]) -> float:
        """Calculate potential information gain score for new content."""
        if not serp_results:
            return 0.0
        
        # Count entity coverage across competitors
        entity_coverage = {}
        for result in serp_results:
            if result.entities:
                for entity in result.entities:
                    entity_coverage[entity] = entity_coverage.get(entity, 0) + 1
        
        # Calculate uniqueness potential
        total_competitors = len(serp_results)
        unique_value_score = 0.0
        
        for entity in target_entities:
            coverage_ratio = entity_coverage.get(entity, 0) / total_competitors
            # Higher score for entities covered by fewer competitors
            uniqueness = 1.0 - coverage_ratio
            unique_value_score += uniqueness
        
        # Normalize by number of target entities
        if target_entities:
            unique_value_score /= len(target_entities)
        
        return min(1.0, unique_value_score)


class SERPGapAnalyzer(LoggerMixin):
    """Main SERP gap analysis service."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize SERP gap analyzer."""
        self.serp_fetcher = SERPFetcher(api_key)
        self.content_analyzer = ContentAnalyzer()
        self.entity_extractor = EntityExtractor()
        self.statistical_analyzer = StatisticalAnalyzer()
    
    def analyze_serp_gaps(
        self,
        query: str,
        target_domain: Optional[str] = None,
        num_results: int = 10,
        analyze_content: bool = True
    ) -> SERPAnalysis:
        """
        Perform comprehensive SERP gap analysis.
        
        Args:
            query: Search query to analyze
            target_domain: Your domain to compare against
            num_results: Number of SERP results to analyze
            analyze_content: Whether to fetch and analyze page content
            
        Returns:
            Complete SERP analysis
        """
        self.logger.info(f"Starting SERP gap analysis for query: {query}")
        
        # Fetch SERP results
        serp_results = self.serp_fetcher.fetch_serp_results(query, num_results=num_results)
        
        if not serp_results:
            self.logger.warning(f"No SERP results found for query: {query}")
            return SERPAnalysis(
                query=query,
                total_results=0,
                serp_results=[],
                top_domains=[],
                common_entities=[],
                common_topics=[],
                content_gaps=[],
                serp_features=[],
                avg_word_count=0.0,
                content_clusters=[],
                differentiation_opportunities=[]
            )
        
        # Analyze content if requested
        if analyze_content:
            self.logger.info(f"Analyzing content for {len(serp_results)} SERP results")
            serp_results = self.content_analyzer.analyze_all_results(serp_results)
        
        # Extract entities and topics
        all_content = []
        all_snippets = []
        
        for result in serp_results:
            if result.content:
                all_content.append(result.content)
            if result.snippet:
                all_snippets.append(result.snippet)
        
        # Entity extraction
        common_entities = self._find_common_entities(serp_results)
        
        # Topic extraction
        content_for_topics = all_content if all_content else all_snippets
        common_topics = self.entity_extractor.extract_topics(content_for_topics)
        
        # Analyze gaps (including statistical analysis)
        content_gaps = self._identify_content_gaps(serp_results, target_domain)
        
        # Add statistical gap analysis
        statistical_opportunities = self.statistical_analyzer.identify_statistical_opportunities(serp_results)
        for opportunity in statistical_opportunities:
            content_gaps.append(ContentGap(
                gap_type="statistical_opportunity",
                description=opportunity.get('recommendation', ''),
                priority=0.8,
                competitors_covering=[r.domain for r in serp_results[:5]],
                suggested_action=f"Optimize based on statistical analysis: {opportunity.get('type', '')}",
                evidence=opportunity,
                statistical_significance=0.05,
                confidence_interval=opportunity.get('confidence_interval'),
                information_gain_potential=0.7
            ))
        
        # Calculate metrics
        word_counts = [r.word_count for r in serp_results if r.word_count]
        avg_word_count = sum(word_counts) / len(word_counts) if word_counts else 0
        
        top_domains = list(set([r.domain for r in serp_results[:5]]))
        
        # Content clustering
        content_clusters = self._cluster_content(serp_results)
        
        # Differentiation opportunities
        differentiation_opportunities = self._identify_differentiation_opportunities(
            serp_results, common_topics, content_gaps
        )
        
        analysis = SERPAnalysis(
            query=query,
            total_results=len(serp_results),
            serp_results=serp_results,
            top_domains=top_domains,
            common_entities=common_entities,
            common_topics=common_topics,
            content_gaps=content_gaps,
            serp_features=[],  # Would be populated from SERP API
            avg_word_count=avg_word_count,
            content_clusters=content_clusters,
            differentiation_opportunities=differentiation_opportunities
        )
        
        self.logger.info(
            f"SERP gap analysis completed",
            query=query,
            results_analyzed=len(serp_results),
            gaps_found=len(content_gaps),
            opportunities=len(differentiation_opportunities)
        )
        
        return analysis
    
    def _find_common_entities(self, serp_results: List[SERPResult]) -> List[Tuple[str, int]]:
        """Find entities that appear across multiple SERP results."""
        entity_counts = {}
        
        for result in serp_results:
            # Extract entities from snippet and content
            text_sources = [result.snippet]
            if result.content:
                text_sources.append(result.content[:1000])  # First 1000 chars
            
            for text in text_sources:
                if text:
                    entities = self.entity_extractor.extract_entities(text)
                    for entity in entities:
                        entity_counts[entity] = entity_counts.get(entity, 0) + 1
        
        # Sort by frequency and return top entities
        common_entities = [(entity, count) for entity, count in entity_counts.items() if count >= 2]
        common_entities.sort(key=lambda x: x[1], reverse=True)
        
        return common_entities[:15]
    
    def _identify_content_gaps(
        self,
        serp_results: List[SERPResult],
        target_domain: Optional[str]
    ) -> List[ContentGap]:
        """Identify content gaps in SERP results."""
        gaps = []
        
        # Analyze content depth
        if serp_results and any(r.word_count for r in serp_results):
            word_counts = [r.word_count for r in serp_results if r.word_count]
            avg_words = sum(word_counts) / len(word_counts)
            max_words = max(word_counts)
            
            # Check if target domain is under-performing on length
            target_result = None
            if target_domain:
                target_result = next((r for r in serp_results if target_domain in r.domain), None)
            
            if target_result and target_result.word_count and target_result.word_count < avg_words * 0.7:
                # Calculate statistical significance
                target_words = [target_result.word_count]
                competitor_words = [r.word_count for r in serp_results if r.word_count and r.domain != target_domain]
                p_value, is_significant = self.statistical_analyzer.test_statistical_significance(target_words, competitor_words)
                
                gaps.append(ContentGap(
                    gap_type="insufficient_depth",
                    description=f"Content length below average ({target_result.word_count} vs {int(avg_words)} words)",
                    priority=0.9 if is_significant else 0.7,
                    competitors_covering=[r.domain for r in serp_results if r.word_count and r.word_count > avg_words],
                    suggested_action="Expand content depth and detail",
                    evidence={"current_words": target_result.word_count, "avg_words": avg_words},
                    statistical_significance=p_value,
                    confidence_interval=self.statistical_analyzer.calculate_confidence_interval(competitor_words),
                    information_gain_potential=0.8
                ))
        
        # Analyze heading structure
        all_headings = []
        for result in serp_results:
            if result.headings:
                all_headings.extend(result.headings)
        
        if all_headings:
            # Find common heading patterns
            heading_keywords = {}
            for heading in all_headings:
                words = heading.lower().split()
                for word in words:
                    if len(word) > 3:
                        heading_keywords[word] = heading_keywords.get(word, 0) + 1
            
            # Identify missing topics in headings
            common_heading_topics = [word for word, count in heading_keywords.items() if count >= 2]
            
            if len(common_heading_topics) > 3:
                # Calculate information gain potential for missing topics
                info_gain = self.statistical_analyzer.calculate_information_gain_potential(serp_results, common_heading_topics)
                
                gaps.append(ContentGap(
                    gap_type="missing_topic",
                    description=f"Common topics not covered: {', '.join(common_heading_topics[:3])}",
                    priority=0.7 + (info_gain * 0.2),  # Boost priority based on information gain
                    competitors_covering=[r.domain for r in serp_results if r.headings],
                    suggested_action="Add sections covering common topics",
                    evidence={"missing_topics": common_heading_topics[:5]},
                    information_gain_potential=info_gain
                ))
        
        # Check for format diversity
        content_types = set()
        for result in serp_results:
            # Simple heuristics for content type detection
            if result.headings:
                if any("how to" in h.lower() for h in result.headings):
                    content_types.add("how_to_guide")
                if any("vs" in h.lower() or "versus" in h.lower() for h in result.headings):
                    content_types.add("comparison")
                if any("best" in h.lower() or "top" in h.lower() for h in result.headings):
                    content_types.add("list_article")
        
        if len(content_types) > 1:
            gaps.append(ContentGap(
                gap_type="format_gap",
                description=f"Multiple content formats in SERP: {', '.join(content_types)}",
                priority=0.6,
                competitors_covering=[r.domain for r in serp_results[:5]],
                suggested_action="Consider creating content in different formats",
                evidence={"formats_found": list(content_types)}
            ))
        
        # Entity coverage analysis
        entity_gaps = self._analyze_entity_gaps(serp_results, target_domain)
        gaps.extend(entity_gaps)
        
        return gaps
    
    def _analyze_entity_gaps(self, serp_results: List[SERPResult], target_domain: Optional[str]) -> List[ContentGap]:
        """Analyze entity coverage gaps in SERP results."""
        gaps = []
        
        # Count entity frequency across all results
        entity_counts = {}
        total_results = len(serp_results)
        
        for result in serp_results:
            if result.entities:
                for entity in result.entities:
                    entity_counts[entity] = entity_counts.get(entity, 0) + 1
        
        # Find entities that appear in most competitors but are missing from target
        target_result = None
        target_entities = set()
        
        if target_domain:
            target_result = next((r for r in serp_results if target_domain in r.domain), None)
            if target_result and target_result.entities:
                target_entities = set(target_result.entities)
        
        # Identify high-frequency entities missing from target
        missing_entities = []
        for entity, count in entity_counts.items():
            coverage_ratio = count / total_results
            if coverage_ratio >= 0.5 and entity not in target_entities:  # Entity in 50%+ of results
                missing_entities.append((entity, coverage_ratio))
        
        if missing_entities:
            # Sort by coverage ratio
            missing_entities.sort(key=lambda x: x[1], reverse=True)
            top_missing = missing_entities[:5]
            
            # Calculate information gain potential
            missing_entity_names = [entity for entity, _ in top_missing]
            info_gain = self.statistical_analyzer.calculate_information_gain_potential(serp_results, missing_entity_names)
            
            gaps.append(ContentGap(
                gap_type="missing_entity",
                description=f"High-frequency entities missing: {', '.join([e[0] for e in top_missing[:3]])}",
                priority=0.8,
                competitors_covering=[r.domain for r in serp_results if r.entities and any(e[0] in r.entities for e in top_missing)],
                suggested_action="Include coverage of these important entities",
                evidence={"missing_entities": top_missing},
                information_gain_potential=info_gain
            ))
        
        return gaps
    
    def _cluster_content(self, serp_results: List[SERPResult]) -> List[Dict]:
        """Cluster SERP results by content similarity."""
        if len(serp_results) < 3:
            return []
        
        try:
            # Import sklearn when needed
            try:
                from sklearn.feature_extraction.text import TfidfVectorizer
                from sklearn.metrics.pairwise import cosine_similarity
            except ImportError:
                self.logger.warning("sklearn not available, using fallback clustering")
                return self._cluster_content_fallback(serp_results)
            
            # Prepare texts for clustering
            texts = []
            for result in serp_results:
                text = result.snippet
                if result.content:
                    text += " " + result.content[:500]  # Add some content
                texts.append(text)
            
            # Use TF-IDF for similarity
            vectorizer = TfidfVectorizer(
                max_features=500,
                ngram_range=(1, 2),
                stop_words='english'
            )
            
            tfidf_matrix = vectorizer.fit_transform(texts)
            similarity_matrix = cosine_similarity(tfidf_matrix)
            
            # Simple clustering based on similarity threshold
            clusters = []
            used_indices = set()
            
            for i in range(len(serp_results)):
                if i in used_indices:
                    continue
                
                cluster = [i]
                used_indices.add(i)
                
                for j in range(i + 1, len(serp_results)):
                    if j not in used_indices and similarity_matrix[i][j] > 0.3:
                        cluster.append(j)
                        used_indices.add(j)
                
                if len(cluster) > 1:
                    cluster_info = {
                        'size': len(cluster),
                        'domains': [serp_results[idx].domain for idx in cluster],
                        'positions': [serp_results[idx].position for idx in cluster],
                        'theme': 'similar_content'
                    }
                    clusters.append(cluster_info)
            
            return clusters
        
        except Exception as e:
            self.logger.error(f"Failed to cluster content: {e}")
            return []
    
    def _cluster_content_fallback(self, serp_results: List[SERPResult]) -> List[Dict]:
        """Fallback content clustering using simple keyword matching."""
        clusters = []
        
        # Group by common keywords in titles
        title_keywords = {}
        for i, result in enumerate(serp_results):
            title_words = set(word.lower() for word in re.findall(r'\b\w+\b', result.title) if len(word) > 3)
            title_keywords[i] = title_words
        
        # Find clusters based on shared keywords
        used_indices = set()
        for i in range(len(serp_results)):
            if i in used_indices:
                continue
            
            cluster = [i]
            used_indices.add(i)
            
            for j in range(i + 1, len(serp_results)):
                if j not in used_indices:
                    # Check if they share at least 2 keywords
                    shared = title_keywords[i].intersection(title_keywords[j])
                    if len(shared) >= 2:
                        cluster.append(j)
                        used_indices.add(j)
            
            if len(cluster) > 1:
                cluster_info = {
                    'size': len(cluster),
                    'domains': [serp_results[idx].domain for idx in cluster],
                    'positions': [serp_results[idx].position for idx in cluster],
                    'theme': 'similar_titles'
                }
                clusters.append(cluster_info)
        
        return clusters
    
    def _identify_differentiation_opportunities(
        self,
        serp_results: List[SERPResult],
        common_topics: List[Tuple[str, float]],
        content_gaps: List[ContentGap]
    ) -> List[str]:
        """Identify opportunities for content differentiation."""
        opportunities = []
        
        # Analyze content diversity
        unique_domains = len(set(r.domain for r in serp_results))
        if unique_domains < len(serp_results) * 0.8:
            opportunities.append("Domain concentration - opportunity for new perspective")
        
        # Check for topic saturation
        if len(common_topics) > 5:
            top_topics = [topic for topic, _ in common_topics[:3]]
            opportunities.append(f"Consider unique angles on saturated topics: {', '.join(top_topics)}")
        
        # Analyze gaps
        high_priority_gaps = [gap for gap in content_gaps if gap.priority > 0.7]
        if high_priority_gaps:
            opportunities.append(f"Address high-priority gaps: {high_priority_gaps[0].suggested_action}")
        
        # Content format opportunities
        has_video_indicators = any(
            "video" in result.title.lower() or "watch" in result.title.lower()
            for result in serp_results
        )
        
        if not has_video_indicators:
            opportunities.append("Consider video content - no video results in top 10")
        
        # Check for tool/calculator opportunities
        has_tools = any(
            "calculator" in result.title.lower() or "tool" in result.title.lower()
            for result in serp_results
        )
        
        if not has_tools:
            opportunities.append("Consider interactive tools or calculators")
        
        return opportunities[:5]  # Return top 5 opportunities
    
    def export_analysis(self, analysis: SERPAnalysis, output_path: str) -> None:
        """Export SERP analysis to JSON file."""
        try:
            # Convert to serializable format
            analysis_dict = asdict(analysis)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(analysis_dict, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"SERP analysis exported to {output_path}")
        
        except Exception as e:
            self.logger.error(f"Failed to export analysis: {e}")