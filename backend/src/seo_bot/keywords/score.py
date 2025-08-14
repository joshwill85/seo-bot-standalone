"""Keyword scoring, intent classification, and difficulty analysis."""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple

# Optional sklearn imports - will be imported when needed

from ..config import KeywordsConfig
from ..logging import get_logger, LoggerMixin

logger = get_logger(__name__)


class SearchIntent(Enum):
    """Search intent classification."""
    INFORMATIONAL = "informational"
    NAVIGATIONAL = "navigational"
    TRANSACTIONAL = "transactional"
    COMMERCIAL = "commercial"


@dataclass
class KeywordScore:
    """Comprehensive keyword scoring results."""
    query: str
    intent: SearchIntent
    intent_confidence: float
    value_score: float
    difficulty_proxy: float
    competition_level: str
    final_score: float
    reasoning: Dict[str, str]


class IntentClassifier:
    """Classifies search intent based on keyword patterns and features."""
    
    INTENT_PATTERNS = {
        SearchIntent.INFORMATIONAL: [
            r'\b(what|how|why|when|where|who|which)\b',
            r'\b(guide|tutorial|tips|learn|definition|meaning)\b',
            r'\b(vs|versus|difference|compare|comparison)\b',
            r'\b(best|top|review|rating)\b',
            r'\b(example|case study|research)\b',
        ],
        SearchIntent.NAVIGATIONAL: [
            r'\b(login|sign in|official|website|homepage)\b',
            r'\b(contact|phone|address|location)\b',
            r'\b(download|app|software)\b',
            r'^[a-zA-Z0-9\s]+ (inc|llc|corp|company)$',
        ],
        SearchIntent.TRANSACTIONAL: [
            r'\b(buy|purchase|order|shop|sale|deal)\b',
            r'\b(price|cost|cheap|discount|coupon)\b',
            r'\b(hire|book|reserve|schedule)\b',
            r'\b(for sale|on sale|special offer)\b',
            r'\b(near me|local|nearby)\b',
        ],
        SearchIntent.COMMERCIAL: [
            r'\b(service|services|provider|company)\b',
            r'\b(consultant|expert|professional)\b',
            r'\b(quote|estimate|pricing)\b',
            r'\b(repair|fix|maintenance)\b',
            r'\b(install|installation|setup)\b',
        ]
    }
    
    def __init__(self):
        """Initialize the intent classifier."""
        self.logger = get_logger(self.__class__.__name__)
        self._compiled_patterns = {}
        for intent, patterns in self.INTENT_PATTERNS.items():
            self._compiled_patterns[intent] = [re.compile(p, re.IGNORECASE) for p in patterns]
    
    def classify_intent(self, query: str) -> Tuple[SearchIntent, float]:
        """
        Classify search intent for a query.
        
        Args:
            query: Search query to classify
            
        Returns:
            Tuple of (intent, confidence_score)
        """
        query = query.lower().strip()
        intent_scores = {}
        
        # Score each intent based on pattern matches
        for intent, patterns in self._compiled_patterns.items():
            score = 0
            matches = []
            
            for pattern in patterns:
                if pattern.search(query):
                    score += 1
                    matches.append(pattern.pattern)
            
            # Normalize score by number of patterns
            normalized_score = score / len(patterns) if patterns else 0
            intent_scores[intent] = normalized_score
            
            if matches:
                self.logger.debug(
                    f"Intent {intent.value} matched patterns for '{query}'",
                    patterns_matched=matches,
                    score=normalized_score
                )
        
        # Handle special cases and modifiers
        intent_scores = self._apply_intent_modifiers(query, intent_scores)
        
        # Find highest scoring intent
        if not intent_scores or all(score == 0 for score in intent_scores.values()):
            # Default to informational for ambiguous queries
            return SearchIntent.INFORMATIONAL, 0.1
        
        best_intent = max(intent_scores, key=intent_scores.get)
        confidence = intent_scores[best_intent]
        
        # Boost confidence for strong signals
        if confidence >= 0.5:
            confidence = min(0.95, confidence * 1.2)
        
        self.logger.debug(
            f"Classified intent for '{query}'",
            intent=best_intent.value,
            confidence=confidence,
            all_scores=intent_scores
        )
        
        return best_intent, confidence
    
    def _apply_intent_modifiers(self, query: str, scores: Dict[SearchIntent, float]) -> Dict[SearchIntent, float]:
        """Apply additional scoring modifiers based on query characteristics."""
        
        # Long-tail informational queries
        if len(query.split()) >= 5 and any(word in query for word in ['how', 'what', 'why']):
            scores[SearchIntent.INFORMATIONAL] = scores.get(SearchIntent.INFORMATIONAL, 0) + 0.3
        
        # Question words strongly indicate informational
        question_words = ['how', 'what', 'why', 'when', 'where', 'who', 'which']
        if any(query.startswith(word) for word in question_words):
            scores[SearchIntent.INFORMATIONAL] = scores.get(SearchIntent.INFORMATIONAL, 0) + 0.4
        
        # Brand + product combinations
        if re.search(r'\b(amazon|google|apple|microsoft|facebook)\s+\w+', query, re.IGNORECASE):
            scores[SearchIntent.NAVIGATIONAL] = scores.get(SearchIntent.NAVIGATIONAL, 0) + 0.3
        
        # Local intent indicators
        if any(term in query for term in ['near me', 'nearby', 'local', 'in my area']):
            scores[SearchIntent.TRANSACTIONAL] = scores.get(SearchIntent.TRANSACTIONAL, 0) + 0.3
        
        # Commercial modifiers
        commercial_modifiers = ['best', 'top', 'review', 'comparison', 'vs']
        if any(mod in query for mod in commercial_modifiers):
            scores[SearchIntent.COMMERCIAL] = scores.get(SearchIntent.COMMERCIAL, 0) + 0.2
        
        return scores


class DifficultyCalculator:
    """Calculates keyword difficulty proxy metrics."""
    
    COMPETITIVE_TERMS = {
        'insurance', 'loan', 'mortgage', 'attorney', 'lawyer', 'credit',
        'hosting', 'casino', 'bitcoin', 'forex', 'software', 'saas'
    }
    
    def __init__(self):
        """Initialize the difficulty calculator."""
        self.logger = get_logger(self.__class__.__name__)
    
    def calculate_difficulty_proxy(
        self,
        query: str,
        search_volume: Optional[int] = None,
        cpc: Optional[float] = None,
        competition: Optional[float] = None
    ) -> Tuple[float, str]:
        """
        Calculate keyword difficulty proxy score.
        
        Args:
            query: Search query
            search_volume: Monthly search volume
            cpc: Cost per click
            competition: Competition score (0-1)
            
        Returns:
            Tuple of (difficulty_score, competition_level)
        """
        factors = []
        reasoning = []
        
        # Query length factor (shorter = harder)
        word_count = len(query.split())
        if word_count <= 2:
            length_factor = 0.8
            reasoning.append("Short query (high competition)")
        elif word_count <= 3:
            length_factor = 0.5
            reasoning.append("Medium-length query")
        else:
            length_factor = 0.2
            reasoning.append("Long-tail query (lower competition)")
        
        factors.append(length_factor)
        
        # Commercial terms factor
        commercial_factor = 0.0
        for term in self.COMPETITIVE_TERMS:
            if term in query.lower():
                commercial_factor = 0.9
                reasoning.append(f"High-competition term: {term}")
                break
        
        factors.append(commercial_factor)
        
        # Search volume factor
        if search_volume is not None:
            if search_volume >= 10000:
                volume_factor = 0.8
                reasoning.append("High search volume")
            elif search_volume >= 1000:
                volume_factor = 0.5
                reasoning.append("Medium search volume")
            else:
                volume_factor = 0.2
                reasoning.append("Low search volume")
            
            factors.append(volume_factor)
        
        # CPC factor
        if cpc is not None:
            if cpc >= 5.0:
                cpc_factor = 0.9
                reasoning.append("High CPC indicates competition")
            elif cpc >= 1.0:
                cpc_factor = 0.6
                reasoning.append("Medium CPC")
            else:
                cpc_factor = 0.3
                reasoning.append("Low CPC")
            
            factors.append(cpc_factor)
        
        # Direct competition score
        if competition is not None:
            factors.append(competition)
            reasoning.append(f"Direct competition score: {competition:.2f}")
        
        # Calculate weighted difficulty
        if len(factors) > 0:
            difficulty = sum(factors) / len(factors)
        else:
            difficulty = 0.5  # Default moderate difficulty
        
        # Determine competition level
        if difficulty >= 0.7:
            level = "high"
        elif difficulty >= 0.4:
            level = "medium"
        else:
            level = "low"
        
        self.logger.debug(
            f"Calculated difficulty for '{query}'",
            difficulty_score=difficulty,
            competition_level=level,
            factors=factors,
            reasoning=reasoning
        )
        
        return difficulty, level


class ValueScorer:
    """Scores keyword value based on business relevance and potential."""
    
    HIGH_VALUE_TERMS = {
        'buy', 'purchase', 'hire', 'service', 'consultation', 'quote',
        'near me', 'local', 'emergency', 'repair', 'installation'
    }
    
    MEDIUM_VALUE_TERMS = {
        'best', 'top', 'review', 'comparison', 'vs', 'how to choose',
        'cost', 'price', 'estimate'
    }
    
    def __init__(self, config: Optional[KeywordsConfig] = None):
        """Initialize the value scorer."""
        self.config = config or KeywordsConfig()
        self.logger = get_logger(self.__class__.__name__)
    
    def calculate_value_score(
        self,
        query: str,
        intent: SearchIntent,
        search_volume: Optional[int] = None,
        cpc: Optional[float] = None,
        business_relevance: float = 1.0
    ) -> float:
        """
        Calculate keyword value score.
        
        Args:
            query: Search query
            intent: Search intent
            search_volume: Monthly search volume
            cpc: Cost per click
            business_relevance: Business relevance score (0-1)
            
        Returns:
            Value score (0-10)
        """
        factors = []
        reasoning = []
        
        # Intent-based scoring
        intent_scores = {
            SearchIntent.TRANSACTIONAL: 4.0,
            SearchIntent.COMMERCIAL: 3.0,
            SearchIntent.INFORMATIONAL: 1.5,
            SearchIntent.NAVIGATIONAL: 1.0,
        }
        
        intent_score = intent_scores.get(intent, 1.0)
        factors.append(intent_score)
        reasoning.append(f"Intent score: {intent_score} ({intent.value})")
        
        # Value terms boost
        query_lower = query.lower()
        value_boost = 0.0
        
        for term in self.HIGH_VALUE_TERMS:
            if term in query_lower:
                value_boost += 2.0
                reasoning.append(f"High-value term: {term}")
                break
        
        if value_boost == 0:
            for term in self.MEDIUM_VALUE_TERMS:
                if term in query_lower:
                    value_boost += 1.0
                    reasoning.append(f"Medium-value term: {term}")
                    break
        
        factors.append(value_boost)
        
        # Search volume factor
        if search_volume is not None:
            if search_volume >= 1000:
                volume_score = 2.0
                reasoning.append("Good search volume")
            elif search_volume >= 100:
                volume_score = 1.0
                reasoning.append("Decent search volume")
            else:
                volume_score = 0.5
                reasoning.append("Low search volume")
            
            factors.append(volume_score)
        
        # CPC factor (higher CPC = more valuable)
        if cpc is not None:
            if cpc >= 5.0:
                cpc_score = 2.0
                reasoning.append("High commercial value (CPC)")
            elif cpc >= 1.0:
                cpc_score = 1.0
                reasoning.append("Medium commercial value")
            else:
                cpc_score = 0.5
                reasoning.append("Low commercial value")
            
            factors.append(cpc_score)
        
        # Business relevance
        relevance_score = business_relevance * 2.0
        factors.append(relevance_score)
        reasoning.append(f"Business relevance: {business_relevance:.2f}")
        
        # Calculate final score
        base_score = sum(factors)
        final_score = min(10.0, base_score)
        
        self.logger.debug(
            f"Calculated value score for '{query}'",
            value_score=final_score,
            factors=factors,
            reasoning=reasoning
        )
        
        return final_score


class KeywordScorer(LoggerMixin):
    """Main keyword scoring service combining all scoring components."""
    
    def __init__(self, config: Optional[KeywordsConfig] = None):
        """Initialize the keyword scorer."""
        self.config = config or KeywordsConfig()
        self.intent_classifier = IntentClassifier()
        self.difficulty_calculator = DifficultyCalculator()
        self.value_scorer = ValueScorer(config)
    
    def score_keyword(
        self,
        query: str,
        search_volume: Optional[int] = None,
        cpc: Optional[float] = None,
        competition: Optional[float] = None,
        business_relevance: float = 1.0,
        serp_features: Optional[List[str]] = None
    ) -> KeywordScore:
        """
        Comprehensively score a keyword.
        
        Args:
            query: Search query
            search_volume: Monthly search volume
            cpc: Cost per click
            competition: Competition score (0-1)
            business_relevance: Business relevance score (0-1)
            serp_features: SERP features present
            
        Returns:
            KeywordScore object with all scoring results
        """
        self.logger.info(f"Scoring keyword: {query}")
        
        # Classify intent
        intent, intent_confidence = self.intent_classifier.classify_intent(query)
        
        # Calculate difficulty
        difficulty_proxy, competition_level = self.difficulty_calculator.calculate_difficulty_proxy(
            query, search_volume, cpc, competition
        )
        
        # Calculate value score
        value_score = self.value_scorer.calculate_value_score(
            query, intent, search_volume, cpc, business_relevance
        )
        
        # Calculate final composite score
        final_score = self._calculate_final_score(
            value_score, difficulty_proxy, intent_confidence
        )
        
        # Build reasoning
        reasoning = {
            "intent": f"{intent.value} with {intent_confidence:.1%} confidence",
            "value": f"Value score of {value_score:.1f}/10",
            "difficulty": f"{competition_level} difficulty ({difficulty_proxy:.2f})",
            "final": f"Final score: {final_score:.2f}"
        }
        
        result = KeywordScore(
            query=query,
            intent=intent,
            intent_confidence=intent_confidence,
            value_score=value_score,
            difficulty_proxy=difficulty_proxy,
            competition_level=competition_level,
            final_score=final_score,
            reasoning=reasoning
        )
        
        self.logger.info(
            f"Scored keyword '{query}'",
            intent=intent.value,
            value_score=value_score,
            difficulty_proxy=difficulty_proxy,
            final_score=final_score
        )
        
        return result
    
    def _calculate_final_score(
        self, value_score: float, difficulty_proxy: float, intent_confidence: float
    ) -> float:
        """Calculate final composite score balancing value and difficulty."""
        
        # Penalize high difficulty
        difficulty_penalty = difficulty_proxy * 3.0
        
        # Boost for high confidence intent classification
        confidence_boost = (intent_confidence - 0.5) * 2.0 if intent_confidence > 0.5 else 0
        
        # Final score: value - difficulty + confidence boost
        final = max(0, value_score - difficulty_penalty + confidence_boost)
        
        return min(10.0, final)
    
    def score_keywords_batch(
        self, 
        keywords_data: List[Dict]
    ) -> List[KeywordScore]:
        """
        Score multiple keywords in batch.
        
        Args:
            keywords_data: List of keyword data dictionaries
            
        Returns:
            List of KeywordScore objects
        """
        results = []
        
        for keyword_data in keywords_data:
            try:
                score = self.score_keyword(**keyword_data)
                results.append(score)
            except Exception as e:
                self.logger.error(
                    f"Failed to score keyword",
                    query=keyword_data.get('query', 'unknown'),
                    error=str(e)
                )
                continue
        
        self.logger.info(f"Scored {len(results)}/{len(keywords_data)} keywords successfully")
        return results