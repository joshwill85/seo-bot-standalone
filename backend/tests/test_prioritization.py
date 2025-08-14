"""Tests for keyword prioritization functionality."""

import numpy as np
import pytest
from unittest.mock import Mock, patch

from seo_bot.keywords.prioritize import (
    TrafficEstimator,
    ContentGapAnalyzer,
    BusinessValueCalculator,
    KeywordPrioritizer,
    PrioritizationError,
    create_prioritizer,
)


class TestTrafficEstimator:
    """Test traffic estimation functionality."""
    
    def test_init_default(self):
        """Test default initialization."""
        estimator = TrafficEstimator()
        assert estimator.base_ctr == 0.25
        assert estimator.position_decay == 0.5
        assert estimator.branded_multiplier == 1.5
        assert len(estimator.position_ctr) == 10
    
    def test_init_custom_params(self):
        """Test initialization with custom parameters."""
        estimator = TrafficEstimator(
            base_ctr=0.3,
            position_decay=0.6,
            branded_multiplier=2.0
        )
        assert estimator.base_ctr == 0.3
        assert estimator.position_decay == 0.6
        assert estimator.branded_multiplier == 2.0
    
    def test_estimate_ctr_by_position_known_positions(self):
        """Test CTR estimation for known positions."""
        estimator = TrafficEstimator()
        
        assert estimator._estimate_ctr_by_position(1) == 0.316
        assert estimator._estimate_ctr_by_position(5) == 0.061
        assert estimator._estimate_ctr_by_position(10) == 0.030
    
    def test_estimate_ctr_by_position_interpolated(self):
        """Test CTR estimation for positions within top 10."""
        estimator = TrafficEstimator()
        
        # Should use decay formula
        ctr = estimator._estimate_ctr_by_position(15)
        assert 0 < ctr < 0.25
        assert ctr == pytest.approx(0.02, rel=0.1)
    
    def test_estimate_ctr_by_position_beyond_page_one(self):
        """Test CTR estimation for positions beyond page 1."""
        estimator = TrafficEstimator()
        
        ctr = estimator._estimate_ctr_by_position(25)
        assert ctr == 0.01
    
    def test_is_branded_keyword_true(self):
        """Test branded keyword detection - positive cases."""
        estimator = TrafficEstimator()
        
        assert estimator._is_branded_keyword("Nike running shoes", ["Nike", "Adidas"])
        assert estimator._is_branded_keyword("best adidas sneakers", ["Nike", "Adidas"])
        assert estimator._is_branded_keyword("NIKE AIR MAX", ["nike"])  # Case insensitive
    
    def test_is_branded_keyword_false(self):
        """Test branded keyword detection - negative cases."""
        estimator = TrafficEstimator()
        
        assert not estimator._is_branded_keyword("running shoes", ["Nike", "Adidas"])
        assert not estimator._is_branded_keyword("best sneakers", ["Nike", "Adidas"])
        assert not estimator._is_branded_keyword("any keyword", [])  # No brand terms
    
    def test_estimate_traffic_potential_basic(self):
        """Test basic traffic estimation."""
        estimator = TrafficEstimator()
        
        result = estimator.estimate_traffic_potential(
            keyword="seo tools",
            search_volume=1000,
            difficulty=0.3,
            target_position=3
        )
        
        assert result['estimated_monthly_traffic'] == int(1000 * 0.110)  # CTR for position 3
        assert result['target_ctr'] == 0.110
        assert result['confidence_score'] > 0
        assert not result['is_branded']
    
    def test_estimate_traffic_potential_branded(self):
        """Test traffic estimation for branded keywords."""
        estimator = TrafficEstimator()
        
        result = estimator.estimate_traffic_potential(
            keyword="Nike running shoes",
            search_volume=500,
            difficulty=0.2,
            target_position=1,
            brand_terms=["Nike"]
        )
        
        expected_ctr = 0.316 * 1.5  # Base CTR * branded multiplier
        assert result['target_ctr'] == expected_ctr
        assert result['estimated_monthly_traffic'] == int(500 * expected_ctr)
        assert result['is_branded']
    
    def test_estimate_traffic_potential_with_current_position(self):
        """Test traffic estimation with current ranking position."""
        estimator = TrafficEstimator()
        
        result = estimator.estimate_traffic_potential(
            keyword="keyword research",
            search_volume=800,
            difficulty=0.4,
            current_position=10,
            target_position=3
        )
        
        current_ctr = estimator._estimate_ctr_by_position(10)  # 0.030
        target_ctr = estimator._estimate_ctr_by_position(3)    # 0.110
        expected_opportunity = max(0, int(800 * (target_ctr - current_ctr)))
        
        assert result['opportunity_traffic'] == expected_opportunity
        assert result['confidence_score'] > 0.5  # Should be higher with existing ranking
    
    def test_estimate_traffic_potential_no_search_volume(self):
        """Test traffic estimation without search volume data."""
        estimator = TrafficEstimator()
        
        # Test long-tail keyword
        result = estimator.estimate_traffic_potential(
            keyword="how to do seo for small business websites",
            difficulty=0.2,
            target_position=1
        )
        
        assert result['search_volume_source'] == 'estimated'
        # Long-tail should get 100 estimated volume
        assert result['estimated_monthly_traffic'] == int(100 * 0.316)
        
        # Test branded keyword
        result_branded = estimator.estimate_traffic_potential(
            keyword="Nike shoes",
            difficulty=0.2,
            target_position=1,
            brand_terms=["Nike"]
        )
        
        # Branded should get 500 estimated volume
        assert result_branded['estimated_monthly_traffic'] == int(500 * 0.316 * 1.5)
    
    def test_estimate_traffic_potential_confidence_factors(self):
        """Test confidence score calculation factors."""
        estimator = TrafficEstimator()
        
        # High confidence case
        result_high = estimator.estimate_traffic_potential(
            keyword="seo tools",
            search_volume=2000,  # High volume
            difficulty=0.1,      # Low difficulty
            current_position=5,  # Existing ranking
            target_position=1
        )
        
        # Low confidence case  
        result_low = estimator.estimate_traffic_potential(
            keyword="seo tools",
            search_volume=50,    # Low volume
            difficulty=0.9,      # High difficulty
            current_position=None,  # No existing ranking
            target_position=1
        )
        
        assert result_high['confidence_score'] > result_low['confidence_score']


class TestContentGapAnalyzer:
    """Test content gap analysis functionality."""
    
    def test_init_default(self):
        """Test default initialization."""
        analyzer = ContentGapAnalyzer()
        assert analyzer.gap_weight_multiplier == 1.2
    
    def test_init_custom_multiplier(self):
        """Test initialization with custom multiplier."""
        analyzer = ContentGapAnalyzer(gap_weight_multiplier=1.5)
        assert analyzer.gap_weight_multiplier == 1.5
    
    def test_analyze_serp_features_high_opportunity(self):
        """Test SERP feature analysis with high opportunity features."""
        analyzer = ContentGapAnalyzer()
        
        serp_features = ['people_also_ask', 'featured_snippet', 'how_to']
        result = analyzer._analyze_serp_features(serp_features)
        
        assert result['opportunity_score'] > 0.5  # High opportunity
        assert 'FAQ section' in str(result['content_suggestions'])
        assert 'featured snippet' in str(result['content_suggestions'])
        assert 'step-by-step' in str(result['content_suggestions'])
        assert len(result['high_opportunity_features']) == 3
    
    def test_analyze_serp_features_medium_opportunity(self):
        """Test SERP feature analysis with medium opportunity features."""
        analyzer = ContentGapAnalyzer()
        
        serp_features = ['videos', 'local_pack', 'related_searches']
        result = analyzer._analyze_serp_features(serp_features)
        
        assert 0.3 < result['opportunity_score'] < 0.7
        assert result['competition_level'] == 'low'  # No low-opportunity features
    
    def test_analyze_serp_features_high_competition(self):
        """Test SERP feature analysis with high competition features."""
        analyzer = ContentGapAnalyzer()
        
        serp_features = ['ads', 'shopping', 'flights', 'hotels']
        result = analyzer._analyze_serp_features(serp_features)
        
        assert result['competition_level'] == 'high'
        assert result['opportunity_score'] >= 0  # Should handle negative scores
    
    def test_analyze_content_gaps_comprehensive(self):
        """Test comprehensive content gap analysis."""
        analyzer = ContentGapAnalyzer()
        
        keyword_data = {
            'serp_features': ['people_also_ask', 'featured_snippet'],
            'gap_analysis': {
                'missing_elements': ['calculator', 'infographic', 'video'],
                'content_depth_score': 0.4  # Below threshold
            },
            'content_requirements': [
                {'type': 'FAQ', 'met': False},
                {'type': 'Examples', 'met': True},
                {'type': 'Tool', 'met': False}
            ]
        }
        
        result = analyzer.analyze_content_gaps(keyword_data)
        
        assert result['gap_score'] > 0.5
        assert result['gap_weight'] > 1.0  # Should be multiplied
        assert result['improvement_potential'] == 'high'
        assert len(result['identified_gaps']) > 0
    
    def test_analyze_content_gaps_minimal(self):
        """Test content gap analysis with minimal gaps."""
        analyzer = ContentGapAnalyzer()
        
        keyword_data = {
            'serp_features': [],
            'gap_analysis': {
                'missing_elements': [],
                'content_depth_score': 0.8  # Good score
            },
            'content_requirements': []
        }
        
        result = analyzer.analyze_content_gaps(keyword_data)
        
        assert result['gap_score'] < 0.3
        assert result['gap_weight'] == pytest.approx(1.0, rel=0.1)
        assert result['improvement_potential'] == 'low'
    
    def test_analyze_content_gaps_empty_data(self):
        """Test content gap analysis with empty data."""
        analyzer = ContentGapAnalyzer()
        
        keyword_data = {}
        result = analyzer.analyze_content_gaps(keyword_data)
        
        assert result['gap_score'] == 0.0
        assert result['gap_weight'] == 1.0
        assert result['improvement_potential'] == 'low'


class TestBusinessValueCalculator:
    """Test business value calculation functionality."""
    
    def test_init_default(self):
        """Test default initialization."""
        calculator = BusinessValueCalculator()
        
        assert calculator.intent_weights['transactional'] == 1.0
        assert calculator.intent_weights['informational'] == 0.4
        assert calculator.business_multipliers['buy'] == 1.2
    
    def test_init_custom_weights(self):
        """Test initialization with custom weights."""
        custom_intent_weights = {'transactional': 1.5, 'informational': 0.2}
        custom_business_multipliers = {'purchase': 1.5, 'guide': 0.3}
        
        calculator = BusinessValueCalculator(
            intent_weights=custom_intent_weights,
            business_multipliers=custom_business_multipliers
        )
        
        assert calculator.intent_weights == custom_intent_weights
        assert calculator.business_multipliers == custom_business_multipliers
    
    def test_detect_commercial_intent_transactional(self):
        """Test detection of transactional intent."""
        calculator = BusinessValueCalculator()
        
        assert calculator._detect_commercial_intent("buy seo software") == "transactional"
        assert calculator._detect_commercial_intent("purchase keyword tool") == "transactional"
        assert calculator._detect_commercial_intent("cheap seo tools") == "transactional"
        assert calculator._detect_commercial_intent("seo tools price") == "transactional"
    
    def test_detect_commercial_intent_commercial(self):
        """Test detection of commercial investigation intent."""
        calculator = BusinessValueCalculator()
        
        assert calculator._detect_commercial_intent("best seo tools") == "commercial"
        assert calculator._detect_commercial_intent("seo tools review") == "commercial"
        assert calculator._detect_commercial_intent("compare seo software") == "commercial"
        assert calculator._detect_commercial_intent("seo tools vs alternatives") == "commercial"
    
    def test_detect_commercial_intent_informational(self):
        """Test detection of informational intent."""
        calculator = BusinessValueCalculator()
        
        assert calculator._detect_commercial_intent("how to do seo") == "informational"
        assert calculator._detect_commercial_intent("what is keyword research") == "informational"
        assert calculator._detect_commercial_intent("seo tutorial guide") == "informational"
        assert calculator._detect_commercial_intent("learn seo techniques") == "informational"
    
    def test_detect_commercial_intent_navigational(self):
        """Test detection of navigational intent."""
        calculator = BusinessValueCalculator()
        
        assert calculator._detect_commercial_intent("semrush login") == "navigational"
        assert calculator._detect_commercial_intent("google analytics dashboard") == "navigational"
        assert calculator._detect_commercial_intent("ahrefs official website") == "navigational"
    
    def test_detect_commercial_intent_default_logic(self):
        """Test default intent detection logic."""
        calculator = BusinessValueCalculator()
        
        # Long-tail should default to informational
        long_tail = "advanced seo techniques for ecommerce websites"
        assert calculator._detect_commercial_intent(long_tail) == "informational"
        
        # Short keywords should default to commercial
        short_keyword = "seo tools"
        assert calculator._detect_commercial_intent(short_keyword) == "commercial"
    
    def test_calculate_business_value_high_commercial(self):
        """Test business value calculation for high commercial value."""
        calculator = BusinessValueCalculator()
        
        result = calculator.calculate_business_value(
            keyword="buy seo software online",
            intent="transactional",
            cpc=8.50,
            competition=0.6
        )
        
        assert result['business_value_score'] > 0.8
        assert result['detected_intent'] == "transactional"
        assert result['commercial_multiplier'] == 1.2  # 'buy' multiplier
        assert result['value_tier'] == 'high'
    
    def test_calculate_business_value_medium_commercial(self):
        """Test business value calculation for medium commercial value."""
        calculator = BusinessValueCalculator()
        
        result = calculator.calculate_business_value(
            keyword="best seo tools review",
            intent="commercial",
            cpc=3.50,
            competition=0.4
        )
        
        assert 0.4 < result['business_value_score'] < 0.8
        assert result['detected_intent'] == "commercial"
        assert result['value_tier'] == 'medium'
    
    def test_calculate_business_value_low_commercial(self):
        """Test business value calculation for low commercial value."""
        calculator = BusinessValueCalculator()
        
        result = calculator.calculate_business_value(
            keyword="what is seo meaning",
            intent="informational",
            cpc=0.50,
            competition=0.1
        )
        
        assert result['business_value_score'] < 0.5
        assert result['detected_intent'] == "informational"
        assert result['value_tier'] == 'low'
    
    def test_calculate_business_value_auto_detect_intent(self):
        """Test business value calculation with auto-detected intent."""
        calculator = BusinessValueCalculator()
        
        result = calculator.calculate_business_value(
            keyword="purchase keyword research tool",
            cpc=5.0,
            competition=0.5
        )
        
        # Should auto-detect as transactional due to 'purchase'
        assert result['detected_intent'] == "transactional"
        assert result['business_value_score'] > 0.7
    
    def test_calculate_business_value_competition_adjustments(self):
        """Test business value adjustments based on competition."""
        calculator = BusinessValueCalculator()
        
        # Sweet spot competition (0.3-0.7) should get bonus
        result_sweet = calculator.calculate_business_value(
            keyword="seo tools",
            competition=0.5
        )
        
        # Very high competition should get penalty
        result_high = calculator.calculate_business_value(
            keyword="seo tools",
            competition=0.95
        )
        
        # Very low competition should get small penalty
        result_low = calculator.calculate_business_value(
            keyword="seo tools",
            competition=0.05
        )
        
        assert result_sweet['competition_adjustment'] == 0.1
        assert result_high['competition_adjustment'] == -0.2
        assert result_low['competition_adjustment'] == -0.1
    
    def test_calculate_business_value_cpc_component(self):
        """Test CPC value component calculation."""
        calculator = BusinessValueCalculator()
        
        # High CPC should increase value
        result_high_cpc = calculator.calculate_business_value(
            keyword="seo tools",
            cpc=10.0  # At the normalization cap
        )
        
        # Low CPC should have minimal impact
        result_low_cpc = calculator.calculate_business_value(
            keyword="seo tools",
            cpc=1.0
        )
        
        assert result_high_cpc['cpc_value_component'] == 0.3  # 30% of normalized CPC
        assert result_low_cpc['cpc_value_component'] == 0.03  # 3% of normalized CPC
        
        # Very high CPC should be capped at normalization limit
        result_very_high_cpc = calculator.calculate_business_value(
            keyword="seo tools",
            cpc=50.0
        )
        
        assert result_very_high_cpc['cpc_value_component'] == 0.3  # Still capped at 30%


class TestKeywordPrioritizer:
    """Test main keyword prioritizer functionality."""
    
    def test_init_default(self):
        """Test default initialization."""
        prioritizer = KeywordPrioritizer()
        
        # Weights should sum to 1.0 after normalization
        total_weight = (
            prioritizer.traffic_weight + prioritizer.difficulty_weight +
            prioritizer.gap_weight + prioritizer.business_value_weight
        )
        assert total_weight == pytest.approx(1.0)
        
        assert isinstance(prioritizer.traffic_estimator, TrafficEstimator)
        assert isinstance(prioritizer.gap_analyzer, ContentGapAnalyzer)
        assert isinstance(prioritizer.business_calculator, BusinessValueCalculator)
    
    def test_init_custom_weights(self):
        """Test initialization with custom weights."""
        prioritizer = KeywordPrioritizer(
            traffic_weight=0.5,
            difficulty_weight=0.3,
            gap_weight=0.1,
            business_value_weight=0.1
        )
        
        # Should normalize to sum to 1.0
        total_weight = (
            prioritizer.traffic_weight + prioritizer.difficulty_weight +
            prioritizer.gap_weight + prioritizer.business_value_weight
        )
        assert total_weight == pytest.approx(1.0)
        
        # Should maintain relative proportions
        assert prioritizer.traffic_weight == 0.5
        assert prioritizer.difficulty_weight == 0.3
    
    def test_normalize_difficulty(self):
        """Test difficulty score normalization."""
        prioritizer = KeywordPrioritizer()
        
        # High difficulty should give low score (1 - 0.9 = 0.1)
        assert prioritizer._normalize_difficulty(0.9) == 0.1
        
        # Low difficulty should give high score (1 - 0.1 = 0.9)
        assert prioritizer._normalize_difficulty(0.1) == 0.9
        
        # Medium difficulty should give medium score
        assert prioritizer._normalize_difficulty(0.5) == 0.5
    
    def test_calculate_priority_score_high_priority(self):
        """Test priority calculation for high-priority keyword."""
        prioritizer = KeywordPrioritizer()
        
        keyword_data = {
            'query': 'buy seo software',
            'search_volume': 2000,
            'difficulty_proxy': 0.2,  # Low difficulty
            'intent': 'transactional',
            'cpc': 8.0,
            'competition': 0.5,
            'serp_features': ['people_also_ask', 'featured_snippet'],
            'gap_analysis': {
                'missing_elements': ['calculator', 'comparison'],
                'content_depth_score': 0.3
            },
            'content_requirements': [
                {'type': 'FAQ', 'met': False}
            ]
        }
        
        result = prioritizer.calculate_priority_score(keyword_data)
        
        assert result['priority_score'] > 0.6  # Should be high priority
        assert result['priority_tier'] in ['high', 'critical']
        assert 'traffic_analysis' in result
        assert 'gap_analysis' in result
        assert 'business_analysis' in result
        assert len(result['recommendations']) > 0
    
    def test_calculate_priority_score_low_priority(self):
        """Test priority calculation for low-priority keyword."""
        prioritizer = KeywordPrioritizer()
        
        keyword_data = {
            'query': 'what is seo definition',
            'search_volume': 50,
            'difficulty_proxy': 0.9,  # High difficulty
            'intent': 'informational',
            'cpc': 0.10,
            'competition': 0.05,
            'serp_features': [],
            'gap_analysis': {},
            'content_requirements': []
        }
        
        result = prioritizer.calculate_priority_score(keyword_data)
        
        assert result['priority_score'] < 0.4  # Should be low priority
        assert result['priority_tier'] in ['low', 'minimal']
    
    def test_calculate_priority_score_error_handling(self):
        """Test priority calculation error handling."""
        prioritizer = KeywordPrioritizer()
        
        # Mock an error in traffic estimation
        with patch.object(prioritizer.traffic_estimator, 'estimate_traffic_potential', 
                         side_effect=Exception("Traffic estimation failed")):
            
            keyword_data = {'query': 'test keyword'}
            result = prioritizer.calculate_priority_score(keyword_data)
            
            assert result['priority_score'] == 0.0
            assert 'error' in result
            assert result['priority_tier'] == 'low'
    
    def test_determine_priority_tier(self):
        """Test priority tier determination."""
        prioritizer = KeywordPrioritizer()
        
        assert prioritizer._determine_priority_tier(0.9) == 'critical'
        assert prioritizer._determine_priority_tier(0.7) == 'high'
        assert prioritizer._determine_priority_tier(0.5) == 'medium'
        assert prioritizer._determine_priority_tier(0.3) == 'low'
        assert prioritizer._determine_priority_tier(0.1) == 'minimal'
    
    def test_generate_recommendations_comprehensive(self):
        """Test comprehensive recommendation generation."""
        prioritizer = KeywordPrioritizer()
        
        traffic_analysis = {
            'opportunity_traffic': 1000,
            'is_branded': True,
            'confidence_score': 0.3  # Low confidence
        }
        
        gap_analysis = {
            'improvement_potential': 'high',
            'serp_analysis': {
                'content_suggestions': [
                    'Add FAQ section',
                    'Include infographics',
                    'Create video content'
                ]
            }
        }
        
        business_analysis = {
            'value_tier': 'high',
            'detected_intent': 'transactional'
        }
        
        recommendations = prioritizer._generate_recommendations(
            traffic_analysis, gap_analysis, business_analysis
        )
        
        assert len(recommendations) <= 5  # Should limit recommendations
        assert any('traffic' in rec.lower() for rec in recommendations)
        assert any('branded' in rec.lower() for rec in recommendations)
        assert any('confidence' in rec.lower() for rec in recommendations)
        assert any('high improvement' in rec.lower() for rec in recommendations)
        assert any('high commercial' in rec.lower() for rec in recommendations)
        assert any('transactional' in rec.lower() for rec in recommendations)
    
    def test_prioritize_keywords_sorting(self):
        """Test keyword prioritization and sorting."""
        prioritizer = KeywordPrioritizer()
        
        keywords_data = [
            {'query': 'low priority keyword', 'search_volume': 50, 'difficulty_proxy': 0.9},
            {'query': 'high priority keyword', 'search_volume': 2000, 'difficulty_proxy': 0.1},
            {'query': 'medium priority keyword', 'search_volume': 500, 'difficulty_proxy': 0.5}
        ]
        
        # Mock priority calculation to return predictable scores
        def mock_calculate_priority(keyword_data, brand_terms=None):
            if 'high priority' in keyword_data['query']:
                return {'priority_score': 0.9, 'priority_tier': 'critical'}
            elif 'medium priority' in keyword_data['query']:
                return {'priority_score': 0.5, 'priority_tier': 'medium'}
            else:
                return {'priority_score': 0.2, 'priority_tier': 'low'}
        
        with patch.object(prioritizer, 'calculate_priority_score', side_effect=mock_calculate_priority):
            result = prioritizer.prioritize_keywords(keywords_data)
            
            # Should be sorted by priority score (descending)
            assert result[0]['query'] == 'high priority keyword'
            assert result[1]['query'] == 'medium priority keyword'
            assert result[2]['query'] == 'low priority keyword'
            
            # Should include original data plus priority analysis
            for keyword_result in result:
                assert 'priority_score' in keyword_result
                assert 'priority_tier' in keyword_result
                assert 'query' in keyword_result
    
    def test_prioritize_keywords_brand_terms(self):
        """Test keyword prioritization with brand terms."""
        prioritizer = KeywordPrioritizer()
        brand_terms = ['MyBrand', 'CompanyName']
        
        keywords_data = [
            {'query': 'MyBrand seo tools', 'search_volume': 500},
            {'query': 'generic seo tools', 'search_volume': 500}
        ]
        
        with patch.object(prioritizer, 'calculate_priority_score') as mock_calc:
            mock_calc.return_value = {'priority_score': 0.5}
            
            prioritizer.prioritize_keywords(keywords_data, brand_terms)
            
            # Should pass brand terms to calculation
            assert mock_calc.call_count == 2
            for call in mock_calc.call_args_list:
                assert call[1]['brand_terms'] == brand_terms
    
    @patch('seo_bot.keywords.prioritize.logger')
    def test_update_database_priorities_success(self, mock_logger):
        """Test successful database priority update."""
        prioritizer = KeywordPrioritizer()
        
        # Mock database objects
        mock_db = Mock()
        mock_keyword = Mock()
        mock_keyword.content_requirements = []
        mock_db.query().filter_by().first.return_value = mock_keyword
        
        prioritized_keywords = [
            {
                'query': 'test keyword',
                'priority_score': 0.8,
                'traffic_analysis': {'estimated_monthly_traffic': 1000},
                'recommendations': ['Optimize for featured snippets', 'Add FAQ section']
            }
        ]
        
        result = prioritizer.update_database_priorities(mock_db, prioritized_keywords)
        
        assert result == 1  # One keyword updated
        assert mock_keyword.value_score == 0.8
        assert len(mock_keyword.content_requirements) == 2  # Two recommendations added
        mock_db.commit.assert_called_once()
    
    def test_update_database_priorities_keyword_not_found(self):
        """Test database update when keyword not found."""
        prioritizer = KeywordPrioritizer()
        
        mock_db = Mock()
        mock_db.query().filter_by().first.return_value = None  # Keyword not found
        
        prioritized_keywords = [{'query': 'nonexistent keyword', 'priority_score': 0.5}]
        
        result = prioritizer.update_database_priorities(mock_db, prioritized_keywords)
        
        assert result == 0  # No keywords updated
        mock_db.commit.assert_called_once()
    
    def test_update_database_priorities_error(self):
        """Test database update error handling."""
        prioritizer = KeywordPrioritizer()
        
        mock_db = Mock()
        mock_db.query.side_effect = Exception("Database error")
        
        prioritized_keywords = [{'query': 'test', 'priority_score': 0.5}]
        
        with pytest.raises(PrioritizationError):
            prioritizer.update_database_priorities(mock_db, prioritized_keywords)
        
        mock_db.rollback.assert_called_once()


class TestUtilityFunctions:
    """Test utility functions."""
    
    def test_create_prioritizer_default(self):
        """Test creating prioritizer with defaults."""
        prioritizer = create_prioritizer()
        assert isinstance(prioritizer, KeywordPrioritizer)
    
    def test_create_prioritizer_custom(self):
        """Test creating prioritizer with custom parameters."""
        prioritizer = create_prioritizer(
            traffic_weight=0.6,
            difficulty_weight=0.2,
            gap_weight=0.1,
            business_value_weight=0.1
        )
        
        assert prioritizer.traffic_weight == 0.6
        assert prioritizer.difficulty_weight == 0.2
        assert prioritizer.gap_weight == 0.1
        assert prioritizer.business_value_weight == 0.1


# Integration tests
class TestPrioritizationIntegration:
    """Test prioritization components working together."""
    
    def test_full_prioritization_pipeline(self):
        """Test complete prioritization pipeline."""
        prioritizer = KeywordPrioritizer()
        
        keywords_data = [
            {
                'query': 'buy premium seo tools online',
                'search_volume': 1500,
                'difficulty_proxy': 0.3,
                'intent': 'transactional',
                'cpc': 6.50,
                'competition': 0.6,
                'serp_features': ['people_also_ask', 'shopping'],
                'gap_analysis': {
                    'missing_elements': ['pricing_table', 'testimonials'],
                    'content_depth_score': 0.5
                },
                'content_requirements': [
                    {'type': 'comparison', 'met': False},
                    {'type': 'reviews', 'met': True}
                ]
            },
            {
                'query': 'how to learn seo basics',
                'search_volume': 800,
                'difficulty_proxy': 0.4,
                'intent': 'informational',
                'cpc': 1.20,
                'competition': 0.3,
                'serp_features': ['featured_snippet', 'videos'],
                'gap_analysis': {
                    'missing_elements': [],
                    'content_depth_score': 0.8
                },
                'content_requirements': []
            }
        ]
        
        results = prioritizer.prioritize_keywords(keywords_data, brand_terms=['SEOTool'])
        
        # Transactional keyword should rank higher than informational
        assert results[0]['query'] == 'buy premium seo tools online'
        assert results[1]['query'] == 'how to learn seo basics'
        
        # Each result should have comprehensive analysis
        for result in results:
            assert 'priority_score' in result
            assert 'priority_tier' in result
            assert 'traffic_analysis' in result
            assert 'gap_analysis' in result
            assert 'business_analysis' in result
            assert 'recommendations' in result
            assert 'component_scores' in result
    
    def test_edge_cases_handling(self):
        """Test handling of various edge cases."""
        prioritizer = KeywordPrioritizer()
        
        # Test with minimal data
        minimal_data = [{'query': 'test keyword'}]
        results = prioritizer.prioritize_keywords(minimal_data)
        
        assert len(results) == 1
        assert results[0]['priority_score'] >= 0
        
        # Test with empty search volume
        no_volume_data = [{'query': 'unknown volume keyword', 'search_volume': 0}]
        results = prioritizer.prioritize_keywords(no_volume_data)
        
        assert len(results) == 1
        assert results[0]['priority_score'] >= 0
        
        # Test with extreme values
        extreme_data = [{
            'query': 'extreme keyword',
            'search_volume': 1000000,  # Very high
            'difficulty_proxy': 0.0,   # Very easy
            'cpc': 100.0,              # Very expensive
            'competition': 1.0         # Maximum competition
        }]
        results = prioritizer.prioritize_keywords(extreme_data)
        
        assert len(results) == 1
        assert 0 <= results[0]['priority_score'] <= 1  # Should still be normalized
    
    def test_prioritizer_component_weights(self):
        """Test that component weights affect final scoring appropriately."""
        # Create prioritizer heavily weighted toward traffic
        traffic_prioritizer = KeywordPrioritizer(
            traffic_weight=0.8,
            difficulty_weight=0.1,
            gap_weight=0.05,
            business_value_weight=0.05
        )
        
        # Create prioritizer heavily weighted toward business value
        business_prioritizer = KeywordPrioritizer(
            traffic_weight=0.1,
            difficulty_weight=0.1,
            gap_weight=0.05,
            business_value_weight=0.75
        )
        
        keyword_data = {
            'query': 'test keyword',
            'search_volume': 10000,    # High traffic
            'difficulty_proxy': 0.8,   # High difficulty
            'intent': 'transactional', # High business value
            'cpc': 10.0,
            'competition': 0.5
        }
        
        traffic_result = traffic_prioritizer.calculate_priority_score(keyword_data)
        business_result = business_prioritizer.calculate_priority_score(keyword_data)
        
        # Traffic-weighted should score higher due to high volume despite high difficulty
        # Business-weighted should also score well due to transactional intent and high CPC
        # Both should be reasonable scores, but the weighting should be evident in components
        assert traffic_result['component_scores']['traffic_score'] > 0.5
        assert business_result['component_scores']['business_score'] > 0.5