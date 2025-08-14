"""Tests for keyword discovery and analysis modules."""

import pytest
from unittest.mock import Mock, patch
from src.seo_bot.keywords.discover import KeywordDiscoverer, KeywordSeed, DiscoveredKeyword
from src.seo_bot.keywords.score import KeywordScorer, SearchIntent
from src.seo_bot.keywords.serp_gap import SERPGapAnalyzer, SERPResult


class TestKeywordScorer:
    """Test keyword scoring functionality."""
    
    def test_intent_classification(self):
        """Test intent classification for various query types."""
        scorer = KeywordScorer()
        
        # Test informational queries
        result = scorer.score_keyword("how to bake bread")
        assert result.intent == SearchIntent.INFORMATIONAL
        assert result.intent_confidence > 0.5
        
        # Test transactional queries
        result = scorer.score_keyword("buy organic bread near me")
        assert result.intent == SearchIntent.TRANSACTIONAL
        
        # Test commercial queries
        result = scorer.score_keyword("best bread maker reviews")
        assert result.intent == SearchIntent.COMMERCIAL
    
    def test_value_scoring(self):
        """Test value scoring with different parameters."""
        scorer = KeywordScorer()
        
        # High-value transactional keyword
        result = scorer.score_keyword(
            query="hire plumber emergency",
            search_volume=1000,
            cpc=15.0,
            business_relevance=1.0
        )
        assert result.value_score > 5.0
        
        # Low-value informational keyword
        result = scorer.score_keyword(
            query="what is plumbing definition",
            search_volume=100,
            cpc=0.50,
            business_relevance=0.3
        )
        assert result.value_score < 5.0
    
    def test_difficulty_calculation(self):
        """Test difficulty proxy calculation."""
        scorer = KeywordScorer()
        
        # High competition keyword
        result = scorer.score_keyword(
            query="insurance",
            search_volume=50000,
            cpc=25.0,
            competition=0.9
        )
        assert result.difficulty_proxy > 0.6
        assert result.competition_level == "high"
        
        # Long-tail keyword (lower competition)
        result = scorer.score_keyword(
            query="how to fix leaky faucet in basement bathroom",
            search_volume=200,
            cpc=2.0
        )
        assert result.difficulty_proxy < 0.5
    
    def test_batch_scoring(self):
        """Test batch keyword scoring."""
        scorer = KeywordScorer()
        
        keywords_data = [
            {"query": "plumber near me", "search_volume": 1500, "cpc": 12.0},
            {"query": "how to fix sink", "search_volume": 800, "cpc": 3.0},
            {"query": "emergency plumbing service", "search_volume": 600, "cpc": 18.0},
        ]
        
        results = scorer.score_keywords_batch(keywords_data)
        assert len(results) == 3
        assert all(isinstance(result.final_score, float) for result in results)


class TestKeywordDiscoverer:
    """Test keyword discovery functionality."""
    
    def test_keyword_expansion(self):
        """Test seed keyword expansion."""
        discoverer = KeywordDiscoverer()
        
        seeds = [
            KeywordSeed(term="plumbing", priority=1.0),
            KeywordSeed(term="plumber", priority=0.8),
        ]
        
        keywords = discoverer.discover_keywords(
            project_id="test-project",
            seeds=seeds,
            use_gsc=False,
            use_serp_api=False
        )
        
        assert len(keywords) > 0
        # Should have variations like "how to plumbing", "plumbing near me", etc.
        keyword_queries = [kw.query for kw in keywords]
        assert any("how to" in query for query in keyword_queries)
        assert any("near me" in query for query in keyword_queries)
    
    @patch('src.seo_bot.keywords.discover.get_db_session')
    def test_keyword_filtering(self, mock_db):
        """Test keyword quality filtering."""
        discoverer = KeywordDiscoverer()
        
        # Mock database session
        mock_session = Mock()
        mock_project = Mock()
        mock_project.base_url = "https://example.com"
        mock_session.query().filter().first.return_value = mock_project
        mock_db.return_value.__enter__.return_value = mock_session
        
        # Test with mixed quality keywords
        test_keywords = [
            DiscoveredKeyword(query="good quality keyword", source="test"),
            DiscoveredKeyword(query="a", source="test"),  # Too short
            DiscoveredKeyword(query="keyword with special @#$ characters", source="test"),  # Bad chars
            DiscoveredKeyword(query="OVERLY BRANDED KEYWORD", source="test"),  # Too branded
            DiscoveredKeyword(query="another good quality keyword", source="test"),
        ]
        
        filtered = discoverer._filter_keywords(test_keywords)
        
        # Should filter out low quality keywords
        assert len(filtered) == 2
        assert all(len(kw.query.split()) >= 2 for kw in filtered)
    
    def test_csv_export(self, tmp_path):
        """Test CSV export functionality."""
        discoverer = KeywordDiscoverer()
        
        keywords = [
            DiscoveredKeyword(
                query="test keyword 1",
                source="test",
                search_volume=1000,
                cpc=5.0
            ),
            DiscoveredKeyword(
                query="test keyword 2", 
                source="test",
                search_volume=500,
                cpc=3.0
            ),
        ]
        
        output_file = tmp_path / "test_keywords.csv"
        discoverer.export_keywords_to_csv(keywords, output_file)
        
        assert output_file.exists()
        
        # Check CSV content
        import pandas as pd
        df = pd.read_csv(output_file)
        assert len(df) == 2
        assert "query" in df.columns
        assert "search_volume" in df.columns


class TestSERPGapAnalyzer:
    """Test SERP gap analysis functionality."""
    
    def test_serp_analysis_mock_data(self):
        """Test SERP analysis with mock data."""
        analyzer = SERPGapAnalyzer()
        
        # This will use fallback method with mock data
        analysis = analyzer.analyze_serp_gaps(
            query="test query",
            analyze_content=False  # Skip content analysis for speed
        )
        
        assert analysis.query == "test query"
        assert analysis.total_results >= 0
        assert isinstance(analysis.differentiation_opportunities, list)
    
    def test_entity_extraction(self):
        """Test entity extraction functionality."""
        analyzer = SERPGapAnalyzer()
        
        test_text = """
        John Smith from Apple Inc visited New York on January 15, 2024.
        The project cost $50,000 and achieved 95% success rate.
        """
        
        entities = analyzer.entity_extractor.extract_entities(test_text)
        
        assert len(entities) > 0
        # Should extract person, organization, location, date, money, percentage
        assert any("John Smith" in entity for entity in entities)
        assert any("Apple Inc" in entity for entity in entities)
    
    def test_content_gap_identification(self):
        """Test content gap identification."""
        analyzer = SERPGapAnalyzer()
        
        # Mock SERP results with varying word counts
        serp_results = [
            SERPResult(
                position=1,
                title="Complete Guide",
                url="https://example1.com",
                snippet="Comprehensive guide...",
                domain="example1.com",
                word_count=2000,
                headings=["Introduction", "Main Topics", "Conclusion"]
            ),
            SERPResult(
                position=2,
                title="Short Article",
                url="https://example2.com",
                snippet="Brief overview...",
                domain="example2.com", 
                word_count=500,
                headings=["Overview"]
            ),
        ]
        
        gaps = analyzer._identify_content_gaps(serp_results, "example2.com")
        
        assert len(gaps) > 0
        # Should identify depth gap for example2.com
        depth_gaps = [gap for gap in gaps if gap.gap_type == "insufficient_depth"]
        assert len(depth_gaps) > 0


class TestIntegration:
    """Test integration between modules."""
    
    @patch('src.seo_bot.keywords.discover.get_db_session')
    def test_full_pipeline(self, mock_db):
        """Test complete keyword discovery and analysis pipeline."""
        # Mock database
        mock_session = Mock()
        mock_project = Mock()
        mock_project.base_url = "https://example.com"
        mock_session.query().filter().first.return_value = mock_project
        mock_db.return_value.__enter__.return_value = mock_session
        
        # Initialize components
        discoverer = KeywordDiscoverer()
        scorer = KeywordScorer() 
        analyzer = SERPGapAnalyzer()
        
        # Step 1: Discover keywords
        seeds = [KeywordSeed(term="local business marketing")]
        
        keywords = discoverer.discover_keywords(
            project_id="test-project",
            seeds=seeds,
            use_gsc=False,
            use_serp_api=False
        )
        
        assert len(keywords) > 0
        
        # Step 2: Score keywords
        top_keyword = keywords[0]
        score_result = scorer.score_keyword(top_keyword.query)
        
        assert score_result.query == top_keyword.query
        assert isinstance(score_result.intent, SearchIntent)
        assert score_result.final_score >= 0
        
        # Step 3: Analyze SERP gaps for top keyword
        gap_analysis = analyzer.analyze_serp_gaps(
            query=top_keyword.query,
            analyze_content=False
        )
        
        assert gap_analysis.query == top_keyword.query
        assert isinstance(gap_analysis.differentiation_opportunities, list)
        
        # Integration check: all components work together
        assert len(gap_analysis.serp_results) >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])