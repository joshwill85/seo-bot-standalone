"""Unit tests for content pruning and optimization system."""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, AsyncMock

from src.seo_bot.prune.optimization import (
    ContentPruningManager,
    ContentAnalyzer,
    PruningRecommendationEngine,
    ContentPerformanceData,
    PruningRecommendation,
    PruningAction,
    ContentCluster
)
from src.seo_bot.config import PruningConfig, Settings


@pytest.fixture
def pruning_config():
    """Create test pruning configuration."""
    return PruningConfig(
        min_performance_threshold=0.3,
        min_content_age_days=90,
        similarity_threshold=0.85,
        min_traffic_threshold=10,
        consolidation_threshold=0.80
    )


@pytest.fixture
def settings():
    """Create test settings."""
    return Settings()


@pytest.fixture
def sample_content_data():
    """Create sample content performance data."""
    base_time = datetime.now(timezone.utc)
    return [
        ContentPerformanceData(
            url="https://example.com/article1",
            title="How to Improve SEO Rankings",
            content="Comprehensive guide to SEO optimization...",
            word_count=1500,
            published_at=base_time - timedelta(days=180),
            last_updated=base_time - timedelta(days=30),
            monthly_clicks=500,
            monthly_impressions=10000,
            avg_position=8.5,
            ctr=0.05,
            bounce_rate=0.65,
            time_on_page=180,
            backlinks=25,
            internal_links=8,
            quality_score=7.5
        ),
        ContentPerformanceData(
            url="https://example.com/article2",
            title="SEO Best Practices Guide",
            content="Another guide to SEO optimization with similar content...",
            word_count=1200,
            published_at=base_time - timedelta(days=200),
            last_updated=base_time - timedelta(days=60),
            monthly_clicks=50,
            monthly_impressions=2000,
            avg_position=25.0,
            ctr=0.025,
            bounce_rate=0.85,
            time_on_page=45,
            backlinks=3,
            internal_links=2,
            quality_score=4.0
        ),
        ContentPerformanceData(
            url="https://example.com/article3",
            title="Advanced SEO Techniques",
            content="Deep dive into advanced SEO strategies...",
            word_count=2000,
            published_at=base_time - timedelta(days=60),
            last_updated=base_time - timedelta(days=10),
            monthly_clicks=800,
            monthly_impressions=15000,
            avg_position=5.2,
            ctr=0.053,
            bounce_rate=0.45,
            time_on_page=240,
            backlinks=40,
            internal_links=12,
            quality_score=9.0
        )
    ]


@pytest.fixture
def underperforming_content():
    """Create underperforming content data."""
    base_time = datetime.now(timezone.utc)
    return ContentPerformanceData(
        url="https://example.com/poor-article",
        title="Outdated SEO Tips",
        content="Old SEO advice that's no longer relevant...",
        word_count=300,
        published_at=base_time - timedelta(days=365),
        last_updated=base_time - timedelta(days=300),
        monthly_clicks=5,
        monthly_impressions=100,
        avg_position=50.0,
        ctr=0.05,
        bounce_rate=0.95,
        time_on_page=15,
        backlinks=0,
        internal_links=1,
        quality_score=2.0
    )


class TestContentPruningManager:
    """Test content pruning manager functionality."""
    
    def test_manager_initialization(self, settings, pruning_config):
        """Test manager initialization."""
        manager = ContentPruningManager(settings, pruning_config)
        
        assert manager.settings == settings
        assert manager.pruning_config == pruning_config
        assert isinstance(manager.content_analyzer, ContentAnalyzer)
        assert isinstance(manager.recommendation_engine, PruningRecommendationEngine)
    
    @pytest.mark.asyncio
    async def test_analyze_content_portfolio(self, settings, pruning_config, sample_content_data):
        """Test content portfolio analysis."""
        manager = ContentPruningManager(settings, pruning_config)
        
        # Mock content analysis
        with patch.object(manager.content_analyzer, 'analyze_content_performance', new_callable=AsyncMock) as mock_analyze:
            mock_analyze.return_value = sample_content_data
            
            with patch.object(manager.content_analyzer, 'find_content_clusters', new_callable=AsyncMock) as mock_clusters:
                mock_clusters.return_value = [
                    ContentCluster(
                        id="cluster_1",
                        urls=["https://example.com/article1", "https://example.com/article2"],
                        topic="SEO optimization",
                        similarity_score=0.87
                    )
                ]
                
                report = await manager.analyze_content_portfolio("example.com")
                
                assert report.total_content == 3
                assert report.underperforming_count > 0
                assert len(report.content_clusters) == 1
                assert report.potential_savings > 0
    
    @pytest.mark.asyncio
    async def test_generate_pruning_recommendations(self, settings, pruning_config, sample_content_data):
        """Test pruning recommendation generation."""
        manager = ContentPruningManager(settings, pruning_config)
        
        recommendations = await manager.generate_pruning_recommendations(sample_content_data)
        
        assert len(recommendations) > 0
        
        # Should recommend action for underperforming content
        poor_content = sample_content_data[1]  # article2 with low performance
        poor_rec = next((r for r in recommendations if r.url == poor_content.url), None)
        assert poor_rec is not None
        assert poor_rec.action in [PruningAction.DELETE, PruningAction.MERGE, PruningAction.IMPROVE]
    
    @pytest.mark.asyncio
    async def test_execute_pruning_actions(self, settings, pruning_config):
        """Test executing pruning actions."""
        manager = ContentPruningManager(settings, pruning_config)
        
        recommendations = [
            PruningRecommendation(
                url="https://example.com/test1",
                action=PruningAction.DELETE,
                reason="Low performance and no traffic",
                confidence=0.95,
                estimated_impact="Minimal impact on traffic",
                alternative_url=None
            ),
            PruningRecommendation(
                url="https://example.com/test2",
                action=PruningAction.MERGE,
                reason="Similar content exists",
                confidence=0.85,
                estimated_impact="Consolidate authority",
                alternative_url="https://example.com/test3"
            )
        ]
        
        with patch.object(manager, '_execute_delete_action', new_callable=AsyncMock) as mock_delete:
            mock_delete.return_value = True
            
            with patch.object(manager, '_execute_merge_action', new_callable=AsyncMock) as mock_merge:
                mock_merge.return_value = True
                
                results = await manager.execute_pruning_actions(recommendations)
                
                assert results['total_actions'] == 2
                assert results['successful_actions'] == 2
                assert results['failed_actions'] == 0
    
    def test_calculate_content_value_score(self, settings, pruning_config):
        """Test content value score calculation."""
        manager = ContentPruningManager(settings, pruning_config)
        
        high_value_content = ContentPerformanceData(
            url="https://example.com/high-value",
            monthly_clicks=1000,
            monthly_impressions=20000,
            avg_position=3.0,
            ctr=0.05,
            backlinks=50,
            quality_score=9.0,
            published_at=datetime.now(timezone.utc) - timedelta(days=30)
        )
        
        low_value_content = ContentPerformanceData(
            url="https://example.com/low-value",
            monthly_clicks=5,
            monthly_impressions=200,
            avg_position=45.0,
            ctr=0.025,
            backlinks=1,
            quality_score=3.0,
            published_at=datetime.now(timezone.utc) - timedelta(days=365)
        )
        
        high_score = manager._calculate_content_value_score(high_value_content)
        low_score = manager._calculate_content_value_score(low_value_content)
        
        assert high_score > low_score
        assert high_score > 0.7  # Should be high value
        assert low_score < 0.3   # Should be low value


class TestContentAnalyzer:
    """Test content analyzer functionality."""
    
    def test_analyzer_initialization(self, pruning_config):
        """Test analyzer initialization."""
        analyzer = ContentAnalyzer(pruning_config)
        
        assert analyzer.pruning_config == pruning_config
    
    @pytest.mark.asyncio
    async def test_analyze_content_performance(self, pruning_config, sample_content_data):
        """Test content performance analysis."""
        analyzer = ContentAnalyzer(pruning_config)
        
        # Mock data retrieval
        with patch.object(analyzer, '_get_content_metrics', new_callable=AsyncMock) as mock_metrics:
            mock_metrics.return_value = sample_content_data
            
            performance_data = await analyzer.analyze_content_performance("example.com")
            
            assert len(performance_data) == 3
            assert all(isinstance(item, ContentPerformanceData) for item in performance_data)
    
    @pytest.mark.asyncio
    async def test_find_content_clusters(self, pruning_config, sample_content_data):
        """Test content clustering."""
        analyzer = ContentAnalyzer(pruning_config)
        
        clusters = await analyzer.find_content_clusters(sample_content_data)
        
        # Should find similar content (article1 and article2 about SEO)
        assert len(clusters) > 0
        
        seo_cluster = clusters[0]
        assert len(seo_cluster.urls) >= 2
        assert seo_cluster.similarity_score > pruning_config.similarity_threshold
    
    def test_calculate_content_similarity(self, pruning_config):
        """Test content similarity calculation."""
        analyzer = ContentAnalyzer(pruning_config)
        
        content1 = "SEO optimization is crucial for website success"
        content2 = "Search engine optimization is essential for site success"
        content3 = "Cooking recipes for delicious meals"
        
        similarity_high = analyzer._calculate_content_similarity(content1, content2)
        similarity_low = analyzer._calculate_content_similarity(content1, content3)
        
        assert similarity_high > similarity_low
        assert similarity_high > 0.5  # Should detect semantic similarity
        assert similarity_low < 0.3   # Should detect low similarity
    
    def test_identify_underperforming_content(self, pruning_config, sample_content_data, underperforming_content):
        """Test underperforming content identification."""
        analyzer = ContentAnalyzer(pruning_config)
        
        content_list = sample_content_data + [underperforming_content]
        underperforming = analyzer._identify_underperforming_content(content_list)
        
        # Should identify the poor-performing content
        assert len(underperforming) > 0
        assert underperforming_content.url in [item.url for item in underperforming]
    
    def test_analyze_content_overlap(self, pruning_config, sample_content_data):
        """Test content overlap analysis."""
        analyzer = ContentAnalyzer(pruning_config)
        
        overlaps = analyzer._analyze_content_overlap(sample_content_data)
        
        # Should find overlap between similar SEO articles
        assert len(overlaps) > 0
        overlap_pair = overlaps[0]
        assert overlap_pair["similarity"] > pruning_config.similarity_threshold


class TestPruningRecommendationEngine:
    """Test pruning recommendation engine functionality."""
    
    def test_engine_initialization(self, pruning_config):
        """Test recommendation engine initialization."""
        engine = PruningRecommendationEngine(pruning_config)
        
        assert engine.pruning_config == pruning_config
    
    @pytest.mark.asyncio
    async def test_generate_recommendations(self, pruning_config, sample_content_data, underperforming_content):
        """Test recommendation generation."""
        engine = PruningRecommendationEngine(pruning_config)
        
        content_list = sample_content_data + [underperforming_content]
        recommendations = await engine.generate_recommendations(content_list)
        
        assert len(recommendations) > 0
        
        # Should recommend deletion for very poor content
        delete_recs = [r for r in recommendations if r.action == PruningAction.DELETE]
        assert len(delete_recs) > 0
        
        # Should have high confidence for clear decisions
        high_confidence_recs = [r for r in recommendations if r.confidence > 0.8]
        assert len(high_confidence_recs) > 0
    
    def test_recommend_delete_action(self, pruning_config, underperforming_content):
        """Test delete action recommendation."""
        engine = PruningRecommendationEngine(pruning_config)
        
        recommendation = engine._recommend_delete_action(underperforming_content)
        
        assert recommendation.action == PruningAction.DELETE
        assert recommendation.confidence > 0.7  # Should be confident about deletion
        assert "low performance" in recommendation.reason.lower()
    
    def test_recommend_merge_action(self, pruning_config, sample_content_data):
        """Test merge action recommendation."""
        engine = PruningRecommendationEngine(pruning_config)
        
        # Simulate similar content for merging
        source_content = sample_content_data[1]  # Lower performing
        target_content = sample_content_data[0]  # Higher performing
        
        recommendation = engine._recommend_merge_action(source_content, target_content)
        
        assert recommendation.action == PruningAction.MERGE
        assert recommendation.alternative_url == target_content.url
        assert "similar content" in recommendation.reason.lower()
    
    def test_recommend_improve_action(self, pruning_config, sample_content_data):
        """Test improve action recommendation."""
        engine = PruningRecommendationEngine(pruning_config)
        
        # Content with potential but needs improvement
        improvable_content = sample_content_data[1]  # Medium performance
        
        recommendation = engine._recommend_improve_action(improvable_content)
        
        assert recommendation.action == PruningAction.IMPROVE
        assert len(recommendation.improvement_suggestions) > 0
    
    def test_calculate_consolidation_impact(self, pruning_config, sample_content_data):
        """Test consolidation impact calculation."""
        engine = PruningRecommendationEngine(pruning_config)
        
        source_content = sample_content_data[1]
        target_content = sample_content_data[0]
        
        impact = engine._calculate_consolidation_impact(source_content, target_content)
        
        assert "clicks" in impact
        assert "position" in impact
        assert "authority" in impact
        assert impact["estimated_improvement"] >= 0


class TestContentPerformanceData:
    """Test content performance data functionality."""
    
    def test_performance_data_creation(self, sample_content_data):
        """Test creating content performance data."""
        content = sample_content_data[0]
        
        assert content.url == "https://example.com/article1"
        assert content.monthly_clicks == 500
        assert content.quality_score == 7.5
    
    def test_performance_metrics_calculation(self, sample_content_data):
        """Test performance metrics calculation."""
        content = sample_content_data[0]
        
        # Test CTR calculation
        expected_ctr = content.monthly_clicks / content.monthly_impressions
        assert abs(content.ctr - expected_ctr) < 0.001
        
        # Test age calculation
        age_days = (datetime.now(timezone.utc) - content.published_at).days
        assert content.get_age_days() == age_days
    
    def test_is_underperforming(self, sample_content_data, underperforming_content):
        """Test underperforming content detection."""
        good_content = sample_content_data[0]  # High performing
        poor_content = underperforming_content
        
        assert not good_content.is_underperforming(threshold=0.3)
        assert poor_content.is_underperforming(threshold=0.3)


class TestPruningRecommendation:
    """Test pruning recommendation functionality."""
    
    def test_recommendation_creation(self):
        """Test creating a pruning recommendation."""
        recommendation = PruningRecommendation(
            url="https://example.com/test",
            action=PruningAction.DELETE,
            reason="Low performance and no traffic",
            confidence=0.95,
            estimated_impact="Minimal impact on traffic",
            alternative_url=None
        )
        
        assert recommendation.url == "https://example.com/test"
        assert recommendation.action == PruningAction.DELETE
        assert recommendation.confidence == 0.95
    
    def test_recommendation_serialization(self):
        """Test recommendation serialization."""
        recommendation = PruningRecommendation(
            url="https://example.com/test",
            action=PruningAction.MERGE,
            reason="Similar content exists",
            confidence=0.85,
            estimated_impact="Consolidate authority",
            alternative_url="https://example.com/target"
        )
        
        rec_dict = recommendation.to_dict()
        
        assert rec_dict["url"] == "https://example.com/test"
        assert rec_dict["action"] == "merge"
        assert rec_dict["confidence"] == 0.85
        assert rec_dict["alternative_url"] == "https://example.com/target"


class TestContentCluster:
    """Test content cluster functionality."""
    
    def test_cluster_creation(self):
        """Test creating a content cluster."""
        cluster = ContentCluster(
            id="cluster_1",
            urls=["https://example.com/a", "https://example.com/b"],
            topic="SEO optimization",
            similarity_score=0.87
        )
        
        assert cluster.id == "cluster_1"
        assert len(cluster.urls) == 2
        assert cluster.similarity_score == 0.87
    
    def test_cluster_primary_content(self):
        """Test identifying primary content in cluster."""
        cluster = ContentCluster(
            id="cluster_1",
            urls=["https://example.com/a", "https://example.com/b"],
            topic="SEO optimization",
            similarity_score=0.87
        )
        
        # Mock performance data for primary selection
        content_data = [
            ContentPerformanceData(
                url="https://example.com/a",
                monthly_clicks=100,
                quality_score=6.0
            ),
            ContentPerformanceData(
                url="https://example.com/b", 
                monthly_clicks=500,
                quality_score=8.0
            )
        ]
        
        primary = cluster.get_primary_content(content_data)
        
        # Should select the higher-performing content
        assert primary.url == "https://example.com/b"
        assert primary.monthly_clicks == 500


if __name__ == "__main__":
    pytest.main([__file__])