"""Keyword prioritization module for SEO-Bot.

This module provides functionality for scoring and prioritizing keywords based on
traffic potential, difficulty, content gaps, and business value alignment.
"""

import logging
import math
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
from sqlalchemy.orm import Session

from ..models import Cluster, Keyword

logger = logging.getLogger(__name__)


class PrioritizationError(Exception):
    """Base exception for prioritization operations."""
    pass


class TrafficEstimator:
    """Estimates traffic potential for keywords."""
    
    def __init__(
        self,
        base_ctr: float = 0.25,
        position_decay: float = 0.5,
        branded_multiplier: float = 1.5
    ) -> None:
        """Initialize traffic estimator.
        
        Args:
            base_ctr: Base click-through rate for position 1
            position_decay: Decay rate for lower positions
            branded_multiplier: Multiplier for branded keywords
        """
        self.base_ctr = base_ctr
        self.position_decay = position_decay
        self.branded_multiplier = branded_multiplier
        
        # CTR by position (industry averages)
        self.position_ctr = {
            1: 0.316, 2: 0.158, 3: 0.110, 4: 0.080, 5: 0.061,
            6: 0.050, 7: 0.042, 8: 0.037, 9: 0.033, 10: 0.030
        }
    
    def _estimate_ctr_by_position(self, target_position: int) -> float:
        """Estimate CTR based on target ranking position.
        
        Args:
            target_position: Target ranking position (1-10+)
            
        Returns:
            Estimated click-through rate
        """
        if target_position in self.position_ctr:
            return self.position_ctr[target_position]
        elif target_position <= 10:
            # Interpolate for positions within top 10
            return max(0.02, self.base_ctr * (self.position_decay ** (target_position - 1)))
        else:
            # Very low CTR for positions beyond page 1
            return 0.01
    
    def _is_branded_keyword(self, keyword: str, brand_terms: List[str]) -> bool:
        """Check if keyword contains brand terms.
        
        Args:
            keyword: Keyword to check
            brand_terms: List of brand terms to look for
            
        Returns:
            True if keyword contains brand terms
        """
        if not brand_terms:
            return False
        
        keyword_lower = keyword.lower()
        return any(brand_term.lower() in keyword_lower for brand_term in brand_terms)
    
    def estimate_traffic_potential(
        self,
        keyword: str,
        search_volume: Optional[int] = None,
        difficulty: float = 0.5,
        current_position: Optional[int] = None,
        target_position: int = 3,
        brand_terms: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Estimate traffic potential for a keyword.
        
        Args:
            keyword: The keyword to analyze
            search_volume: Monthly search volume
            difficulty: Keyword difficulty (0-1 scale)
            current_position: Current ranking position
            target_position: Target ranking position
            brand_terms: Brand terms for branded keyword detection
            
        Returns:
            Dictionary with traffic estimates and metrics
        """
        brand_terms = brand_terms or []
        
        # Use default search volume if not provided
        if search_volume is None:
            # Estimate based on keyword characteristics
            if self._is_branded_keyword(keyword, brand_terms):
                search_volume = 500
            elif len(keyword.split()) >= 4:  # Long-tail
                search_volume = 100
            else:
                search_volume = 250
        
        # Calculate CTR for target position
        target_ctr = self._estimate_ctr_by_position(target_position)
        
        # Apply branded keyword multiplier
        if self._is_branded_keyword(keyword, brand_terms):
            target_ctr *= self.branded_multiplier
        
        # Estimate monthly traffic
        estimated_monthly_traffic = int(search_volume * target_ctr)
        
        # Calculate opportunity score (accounts for current position)
        if current_position and current_position <= 20:
            current_ctr = self._estimate_ctr_by_position(current_position)
            opportunity_traffic = max(0, int(search_volume * (target_ctr - current_ctr)))
        else:
            opportunity_traffic = estimated_monthly_traffic
        
        # Calculate confidence score (based on difficulty and data quality)
        confidence_factors = []
        
        # Difficulty factor (easier keywords have higher confidence)
        confidence_factors.append(1 - difficulty)
        
        # Volume factor (higher volume = higher confidence, but cap it)
        volume_confidence = min(1.0, search_volume / 1000)
        confidence_factors.append(volume_confidence)
        
        # Position factor (existing rankings increase confidence)
        if current_position and current_position <= 50:
            position_confidence = 1 - (current_position - 1) / 50
            confidence_factors.append(position_confidence)
        else:
            confidence_factors.append(0.3)  # Low confidence for unranked
        
        confidence_score = np.mean(confidence_factors)
        
        return {
            'estimated_monthly_traffic': estimated_monthly_traffic,
            'opportunity_traffic': opportunity_traffic,
            'target_ctr': target_ctr,
            'confidence_score': confidence_score,
            'is_branded': self._is_branded_keyword(keyword, brand_terms),
            'search_volume_source': 'estimated' if search_volume == 250 else 'provided'
        }


class ContentGapAnalyzer:
    """Analyzes content gaps and opportunities."""
    
    def __init__(self, gap_weight_multiplier: float = 1.2) -> None:
        """Initialize content gap analyzer.
        
        Args:
            gap_weight_multiplier: Multiplier for keywords with content gaps
        """
        self.gap_weight_multiplier = gap_weight_multiplier
    
    def _analyze_serp_features(self, serp_features: List[str]) -> Dict[str, Any]:
        """Analyze SERP features for content opportunities.
        
        Args:
            serp_features: List of SERP features present
            
        Returns:
            Analysis of content opportunities
        """
        high_opportunity_features = {
            'people_also_ask', 'featured_snippet', 'knowledge_panel',
            'how_to', 'faq', 'reviews', 'images'
        }
        
        medium_opportunity_features = {
            'local_pack', 'shopping', 'videos', 'news',
            'related_searches', 'site_links'
        }
        
        low_opportunity_features = {
            'ads', 'maps', 'flights', 'hotels'
        }
        
        present_features = set(serp_features)
        
        opportunity_score = 0.0
        content_suggestions = []
        
        # High opportunity features
        high_features = present_features & high_opportunity_features
        opportunity_score += len(high_features) * 0.3
        
        if 'people_also_ask' in high_features:
            content_suggestions.append("Include FAQ section addressing related questions")
        if 'featured_snippet' in high_features:
            content_suggestions.append("Structure content for featured snippet optimization")
        if 'how_to' in high_features:
            content_suggestions.append("Create step-by-step guides or tutorials")
        if 'images' in high_features:
            content_suggestions.append("Include relevant, optimized images")
        
        # Medium opportunity features
        medium_features = present_features & medium_opportunity_features
        opportunity_score += len(medium_features) * 0.15
        
        if 'videos' in medium_features:
            content_suggestions.append("Consider video content or embeds")
        if 'local_pack' in medium_features:
            content_suggestions.append("Include local SEO elements")
        
        # Penalty for high-competition features
        low_features = present_features & low_opportunity_features
        opportunity_score -= len(low_features) * 0.1
        
        return {
            'opportunity_score': max(0, min(1, opportunity_score)),
            'content_suggestions': content_suggestions,
            'high_opportunity_features': list(high_features),
            'competition_level': 'high' if len(low_features) > 2 else 'medium' if len(low_features) > 0 else 'low'
        }
    
    def analyze_content_gaps(
        self,
        keyword_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze content gaps for a keyword.
        
        Args:
            keyword_data: Dictionary containing keyword information
            
        Returns:
            Content gap analysis results
        """
        gaps = []
        gap_score = 0.0
        
        # Extract data
        serp_features = keyword_data.get('serp_features', [])
        gap_analysis = keyword_data.get('gap_analysis', {})
        content_requirements = keyword_data.get('content_requirements', [])
        
        # Analyze SERP features
        serp_analysis = self._analyze_serp_features(serp_features)
        gap_score += serp_analysis['opportunity_score'] * 0.4
        
        # Analyze existing gap analysis data
        if gap_analysis:
            missing_elements = gap_analysis.get('missing_elements', [])
            content_depth_score = gap_analysis.get('content_depth_score', 0)
            
            # Gap score based on missing elements
            if missing_elements:
                gap_score += min(0.3, len(missing_elements) * 0.05)
                gaps.extend([f"Missing: {element}" for element in missing_elements[:5]])
            
            # Content depth penalty
            if content_depth_score < 0.6:
                gap_score += 0.2
                gaps.append("Insufficient content depth compared to competitors")
        
        # Analyze content requirements
        if content_requirements:
            unmet_requirements = [req for req in content_requirements if not req.get('met', False)]
            if unmet_requirements:
                gap_score += min(0.3, len(unmet_requirements) * 0.1)
                gaps.extend([f"Unmet requirement: {req.get('type', 'Unknown')}" 
                           for req in unmet_requirements[:3]])
        
        # Calculate final gap weight
        gap_weight = 1.0 + (gap_score * (self.gap_weight_multiplier - 1.0))
        
        return {
            'gap_score': min(1.0, gap_score),
            'gap_weight': gap_weight,
            'identified_gaps': gaps,
            'serp_analysis': serp_analysis,
            'improvement_potential': 'high' if gap_score > 0.6 else 'medium' if gap_score > 0.3 else 'low'
        }


class BusinessValueCalculator:
    """Calculates business value alignment for keywords."""
    
    def __init__(
        self,
        intent_weights: Optional[Dict[str, float]] = None,
        business_multipliers: Optional[Dict[str, float]] = None
    ) -> None:
        """Initialize business value calculator.
        
        Args:
            intent_weights: Weights for different search intents
            business_multipliers: Multipliers for business-relevant terms
        """
        self.intent_weights = intent_weights or {
            'transactional': 1.0,
            'commercial': 0.8,
            'informational': 0.4,
            'navigational': 0.2
        }
        
        self.business_multipliers = business_multipliers or {
            'buy': 1.2, 'purchase': 1.2, 'price': 1.1, 'cost': 1.1,
            'best': 1.0, 'review': 0.9, 'compare': 0.9,
            'how': 0.6, 'what': 0.5, 'why': 0.4, 'when': 0.4
        }
    
    def _detect_commercial_intent(self, keyword: str) -> str:
        """Detect commercial intent from keyword text.
        
        Args:
            keyword: Keyword to analyze
            
        Returns:
            Detected intent category
        """
        keyword_lower = keyword.lower()
        
        # Transactional indicators
        transactional_terms = [
            'buy', 'purchase', 'order', 'shop', 'deal', 'sale', 'discount',
            'price', 'cost', 'cheap', 'affordable', 'free shipping'
        ]
        
        # Commercial investigation indicators
        commercial_terms = [
            'best', 'top', 'review', 'compare', 'comparison', 'vs', 'versus',
            'alternative', 'option', 'recommendation', 'guide'
        ]
        
        # Informational indicators
        informational_terms = [
            'how', 'what', 'why', 'when', 'where', 'tutorial', 'guide',
            'learn', 'understand', 'meaning', 'definition'
        ]
        
        # Navigational indicators
        navigational_terms = [
            'login', 'sign in', 'account', 'dashboard', 'portal',
            'official', 'website', 'homepage'
        ]
        
        # Check for patterns
        if any(term in keyword_lower for term in transactional_terms):
            return 'transactional'
        elif any(term in keyword_lower for term in commercial_terms):
            return 'commercial'
        elif any(term in keyword_lower for term in navigational_terms):
            return 'navigational'
        elif any(term in keyword_lower for term in informational_terms):
            return 'informational'
        else:
            # Default based on keyword length and structure
            if len(keyword.split()) >= 4:
                return 'informational'  # Long-tail often informational
            else:
                return 'commercial'  # Short keywords often commercial
    
    def calculate_business_value(
        self,
        keyword: str,
        intent: Optional[str] = None,
        cpc: Optional[float] = None,
        competition: Optional[float] = None
    ) -> Dict[str, Any]:
        """Calculate business value score for a keyword.
        
        Args:
            keyword: Keyword to analyze
            intent: Search intent (if known)
            cpc: Cost per click
            competition: Competition level (0-1)
            
        Returns:
            Business value analysis results
        """
        # Detect intent if not provided
        if intent is None:
            intent = self._detect_commercial_intent(keyword)
        
        # Base value from intent
        base_value = self.intent_weights.get(intent, 0.5)
        
        # Commercial value indicators
        commercial_multiplier = 1.0
        for term, multiplier in self.business_multipliers.items():
            if term in keyword.lower():
                commercial_multiplier = max(commercial_multiplier, multiplier)
        
        # CPC value (higher CPC often indicates higher commercial value)
        cpc_value = 0.0
        if cpc is not None and cpc > 0:
            # Normalize CPC to 0-1 scale (assuming $10 as high CPC)
            cpc_normalized = min(1.0, cpc / 10.0)
            cpc_value = cpc_normalized * 0.3  # 30% weight for CPC
        
        # Competition adjustment (moderate competition often better than very high or very low)
        competition_adjustment = 0.0
        if competition is not None:
            # Sweet spot around 0.3-0.7 competition
            if 0.3 <= competition <= 0.7:
                competition_adjustment = 0.1
            elif competition > 0.9:
                competition_adjustment = -0.2  # Very high competition penalty
            elif competition < 0.1:
                competition_adjustment = -0.1  # Very low competition might indicate low value
        
        # Calculate final business value
        business_value = (
            base_value * commercial_multiplier +
            cpc_value +
            competition_adjustment
        )
        
        # Ensure value is between 0 and 1
        business_value = max(0.0, min(1.0, business_value))
        
        return {
            'business_value_score': business_value,
            'detected_intent': intent,
            'commercial_multiplier': commercial_multiplier,
            'cpc_value_component': cpc_value,
            'competition_adjustment': competition_adjustment,
            'value_tier': 'high' if business_value > 0.7 else 'medium' if business_value > 0.4 else 'low'
        }


class KeywordPrioritizer:
    """Main class for keyword prioritization."""
    
    def __init__(
        self,
        traffic_weight: float = 0.4,
        difficulty_weight: float = 0.3,
        gap_weight: float = 0.2,
        business_value_weight: float = 0.1
    ) -> None:
        """Initialize keyword prioritizer.
        
        Args:
            traffic_weight: Weight for traffic potential (0-1)
            difficulty_weight: Weight for difficulty score (0-1)  
            gap_weight: Weight for content gaps (0-1)
            business_value_weight: Weight for business value (0-1)
        """
        # Normalize weights
        total_weight = traffic_weight + difficulty_weight + gap_weight + business_value_weight
        self.traffic_weight = traffic_weight / total_weight
        self.difficulty_weight = difficulty_weight / total_weight
        self.gap_weight = gap_weight / total_weight
        self.business_value_weight = business_value_weight / total_weight
        
        # Initialize analyzers
        self.traffic_estimator = TrafficEstimator()
        self.gap_analyzer = ContentGapAnalyzer()
        self.business_calculator = BusinessValueCalculator()
    
    def _normalize_difficulty(self, difficulty: float) -> float:
        """Normalize difficulty score (lower difficulty = higher score).
        
        Args:
            difficulty: Raw difficulty score (0-1, higher = more difficult)
            
        Returns:
            Normalized score (0-1, higher = better opportunity)
        """
        return 1.0 - difficulty
    
    def calculate_priority_score(
        self,
        keyword_data: Dict[str, Any],
        brand_terms: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Calculate comprehensive priority score for a keyword.
        
        Args:
            keyword_data: Dictionary containing keyword information
            brand_terms: Brand terms for branded keyword detection
            
        Returns:
            Priority analysis results
        """
        keyword = keyword_data.get('query', '')
        
        try:
            # Traffic potential analysis
            traffic_analysis = self.traffic_estimator.estimate_traffic_potential(
                keyword=keyword,
                search_volume=keyword_data.get('search_volume'),
                difficulty=keyword_data.get('difficulty_proxy', 0.5),
                current_position=keyword_data.get('current_position'),
                target_position=keyword_data.get('target_position', 3),
                brand_terms=brand_terms
            )
            
            # Content gap analysis
            gap_analysis = self.gap_analyzer.analyze_content_gaps(keyword_data)
            
            # Business value analysis
            business_analysis = self.business_calculator.calculate_business_value(
                keyword=keyword,
                intent=keyword_data.get('intent'),
                cpc=keyword_data.get('cpc'),
                competition=keyword_data.get('competition')
            )
            
            # Calculate component scores
            traffic_score = min(1.0, traffic_analysis['estimated_monthly_traffic'] / 1000)
            difficulty_score = self._normalize_difficulty(keyword_data.get('difficulty_proxy', 0.5))
            gap_score = gap_analysis['gap_score']
            business_score = business_analysis['business_value_score']
            
            # Calculate weighted priority score
            priority_score = (
                traffic_score * self.traffic_weight +
                difficulty_score * self.difficulty_weight +
                gap_score * self.gap_weight +
                business_score * self.business_value_weight
            )
            
            # Apply confidence adjustment
            confidence = traffic_analysis['confidence_score']
            adjusted_priority = priority_score * confidence
            
            return {
                'priority_score': adjusted_priority,
                'raw_priority_score': priority_score,
                'component_scores': {
                    'traffic_score': traffic_score,
                    'difficulty_score': difficulty_score,
                    'gap_score': gap_score,
                    'business_score': business_score
                },
                'weights_used': {
                    'traffic_weight': self.traffic_weight,
                    'difficulty_weight': self.difficulty_weight,
                    'gap_weight': self.gap_weight,
                    'business_value_weight': self.business_value_weight
                },
                'traffic_analysis': traffic_analysis,
                'gap_analysis': gap_analysis,
                'business_analysis': business_analysis,
                'confidence_score': confidence,
                'priority_tier': self._determine_priority_tier(adjusted_priority),
                'recommendations': self._generate_recommendations(
                    traffic_analysis, gap_analysis, business_analysis
                )
            }
            
        except Exception as e:
            logger.error(f"Priority calculation failed for keyword '{keyword}': {e}")
            return {
                'priority_score': 0.0,
                'error': str(e),
                'priority_tier': 'low'
            }
    
    def _determine_priority_tier(self, priority_score: float) -> str:
        """Determine priority tier based on score.
        
        Args:
            priority_score: Calculated priority score
            
        Returns:
            Priority tier string
        """
        if priority_score >= 0.8:
            return 'critical'
        elif priority_score >= 0.6:
            return 'high'
        elif priority_score >= 0.4:
            return 'medium'
        elif priority_score >= 0.2:
            return 'low'
        else:
            return 'minimal'
    
    def _generate_recommendations(
        self,
        traffic_analysis: Dict[str, Any],
        gap_analysis: Dict[str, Any],
        business_analysis: Dict[str, Any]
    ) -> List[str]:
        """Generate actionable recommendations.
        
        Args:
            traffic_analysis: Traffic analysis results
            gap_analysis: Gap analysis results
            business_analysis: Business value analysis
            
        Returns:
            List of recommendation strings
        """
        recommendations = []
        
        # Traffic-based recommendations
        if traffic_analysis['opportunity_traffic'] > 500:
            recommendations.append("High traffic opportunity - prioritize for content creation")
        
        if traffic_analysis['is_branded']:
            recommendations.append("Branded keyword - ensure brand presence and optimization")
        
        if traffic_analysis['confidence_score'] < 0.5:
            recommendations.append("Low confidence - validate traffic estimates with additional data")
        
        # Gap-based recommendations
        gap_recs = gap_analysis.get('serp_analysis', {}).get('content_suggestions', [])
        recommendations.extend(gap_recs[:2])  # Limit to top 2 suggestions
        
        if gap_analysis['improvement_potential'] == 'high':
            recommendations.append("High improvement potential - focus on content gaps")
        
        # Business value recommendations
        if business_analysis['value_tier'] == 'high':
            recommendations.append("High commercial value - prioritize for conversion optimization")
        
        intent = business_analysis['detected_intent']
        if intent == 'transactional':
            recommendations.append("Transactional intent - optimize for conversions and CTAs")
        elif intent == 'informational':
            recommendations.append("Informational intent - focus on comprehensive, helpful content")
        
        return recommendations[:5]  # Limit to top 5 recommendations
    
    def prioritize_keywords(
        self,
        keywords_data: List[Dict[str, Any]],
        brand_terms: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Prioritize a list of keywords.
        
        Args:
            keywords_data: List of keyword data dictionaries
            brand_terms: Brand terms for analysis
            
        Returns:
            List of keywords with priority analysis, sorted by priority
        """
        prioritized_keywords = []
        
        for keyword_data in keywords_data:
            priority_analysis = self.calculate_priority_score(keyword_data, brand_terms)
            
            # Add original data
            result = {**keyword_data, **priority_analysis}
            prioritized_keywords.append(result)
        
        # Sort by priority score (descending)
        prioritized_keywords.sort(
            key=lambda x: x.get('priority_score', 0),
            reverse=True
        )
        
        return prioritized_keywords
    
    def update_database_priorities(
        self,
        db: Session,
        prioritized_keywords: List[Dict[str, Any]]
    ) -> int:
        """Update database with priority scores.
        
        Args:
            db: Database session
            prioritized_keywords: Results from prioritize_keywords
            
        Returns:
            Number of keywords updated
        """
        updated_count = 0
        
        try:
            for keyword_data in prioritized_keywords:
                keyword_query = keyword_data.get('query')
                if not keyword_query:
                    continue
                
                # Find keyword in database
                keyword = db.query(Keyword).filter_by(query=keyword_query).first()
                if not keyword:
                    continue
                
                # Update priority-related fields
                traffic_analysis = keyword_data.get('traffic_analysis', {})
                
                # Update value score (using priority score as proxy)
                keyword.value_score = keyword_data.get('priority_score', 0.0)
                
                # Update content requirements with recommendations
                recommendations = keyword_data.get('recommendations', [])
                if recommendations:
                    existing_requirements = keyword.content_requirements or []
                    new_requirements = [
                        {'type': 'recommendation', 'description': rec, 'priority': 'high'}
                        for rec in recommendations[:3]
                    ]
                    keyword.content_requirements = existing_requirements + new_requirements
                
                updated_count += 1
            
            db.commit()
            logger.info(f"Updated priority scores for {updated_count} keywords")
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to update database priorities: {e}")
            raise PrioritizationError(f"Database update failed: {e}")
        
        return updated_count


def create_prioritizer(**kwargs) -> KeywordPrioritizer:
    """Create a keyword prioritizer with custom settings.
    
    Args:
        **kwargs: Configuration parameters for prioritization
        
    Returns:
        Configured KeywordPrioritizer instance
    """
    return KeywordPrioritizer(**kwargs)