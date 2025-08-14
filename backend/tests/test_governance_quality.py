"""Unit tests for governance and quality management system."""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, AsyncMock

from src.seo_bot.governance.quality import (
    QualityGovernanceManager,
    SpamDetector,
    ContentSimilarityDetector,
    QualityScore,
    GovernanceViolation,
    SpamSignalType,
    ContentFlags
)
from src.seo_bot.config import GovernanceConfig, Settings
from src.seo_bot.models import AlertSeverity


@pytest.fixture
def governance_config():
    """Create test governance configuration."""
    return GovernanceConfig(
        max_programmatic_per_week=100,
        similarity_threshold=0.85,
        quality_score_minimum=6.0,
        content_velocity_limit=50,
        human_review_required=['ymyl', 'medical']
    )


@pytest.fixture
def settings():
    """Create test settings."""
    return Settings()


@pytest.fixture
def sample_content():
    """Create sample content for testing."""
    return {
        "title": "How to Improve Your SEO Rankings",
        "content": """
        Search engine optimization (SEO) is crucial for online success. 
        This comprehensive guide will help you understand the fundamentals 
        of SEO and provide actionable strategies to improve your rankings.
        
        Key factors include keyword research, content quality, technical SEO,
        and building authority through backlinks. Each element plays a vital
        role in determining how search engines rank your content.
        """,
        "url": "https://example.com/seo-guide",
        "word_count": 85,
        "category": "marketing"
    }


@pytest.fixture
def duplicate_content():
    """Create duplicate content for similarity testing."""
    return {
        "title": "How to Boost Your SEO Rankings",
        "content": """
        Search engine optimization (SEO) is essential for digital success.
        This complete guide will help you learn the basics of SEO and 
        provide practical strategies to boost your rankings.
        
        Important factors include keyword research, content quality, technical SEO,
        and building authority through backlinks. Each component plays a crucial
        role in determining how search engines rank your content.
        """,
        "url": "https://example.com/seo-boost",
        "word_count": 83,
        "category": "marketing"
    }


class TestQualityGovernanceManager:
    """Test quality governance manager functionality."""
    
    def test_manager_initialization(self, settings, governance_config):
        """Test manager initialization."""
        manager = QualityGovernanceManager(settings, governance_config)
        
        assert manager.settings == settings
        assert manager.governance_config == governance_config
        assert isinstance(manager.spam_detector, SpamDetector)
        assert isinstance(manager.similarity_detector, ContentSimilarityDetector)
    
    @pytest.mark.asyncio
    async def test_content_quality_audit_high_quality(self, settings, governance_config, sample_content):
        """Test content quality audit with high-quality content."""
        manager = QualityGovernanceManager(settings, governance_config)
        
        # Mock content analysis
        with patch.object(manager, '_analyze_content_quality', new_callable=AsyncMock) as mock_analyze:
            mock_analyze.return_value = QualityScore(
                overall_score=8.5,
                readability_score=85,
                uniqueness_score=90,
                authority_score=80,
                technical_score=85,
                user_engagement_score=88
            )
            
            with patch.object(manager, '_check_spam_signals', new_callable=AsyncMock) as mock_spam:
                mock_spam.return_value = []
                
                with patch.object(manager, '_check_content_similarity', new_callable=AsyncMock) as mock_similarity:
                    mock_similarity.return_value = []
                    
                    report = await manager.content_quality_audit([sample_content])
                    
                    assert report.total_content == 1
                    assert report.high_quality_count == 1
                    assert report.low_quality_count == 0
                    assert report.spam_detected == 0
                    assert len(report.violations) == 0
    
    @pytest.mark.asyncio
    async def test_content_quality_audit_with_violations(self, settings, governance_config):
        """Test content quality audit with violations."""
        manager = QualityGovernanceManager(settings, governance_config)
        
        low_quality_content = {
            "title": "Bad",
            "content": "Short bad content",
            "url": "https://example.com/bad",
            "word_count": 3,
            "category": "general"
        }
        
        # Mock poor quality analysis
        with patch.object(manager, '_analyze_content_quality', new_callable=AsyncMock) as mock_analyze:
            mock_analyze.return_value = QualityScore(
                overall_score=3.0,  # Below minimum
                readability_score=30,
                uniqueness_score=40,
                authority_score=20,
                technical_score=35,
                user_engagement_score=25
            )
            
            with patch.object(manager, '_check_spam_signals', new_callable=AsyncMock) as mock_spam:
                mock_spam.return_value = [
                    GovernanceViolation(
                        content_url="https://example.com/bad",
                        violation_type="quality_threshold",
                        severity=AlertSeverity.HIGH,
                        description="Content quality below minimum threshold",
                        detected_at=datetime.now(timezone.utc),
                        auto_resolvable=False
                    )
                ]
                
                with patch.object(manager, '_check_content_similarity', new_callable=AsyncMock) as mock_similarity:
                    mock_similarity.return_value = []
                    
                    report = await manager.content_quality_audit([low_quality_content])
                    
                    assert report.total_content == 1
                    assert report.high_quality_count == 0
                    assert report.low_quality_count == 1
                    assert len(report.violations) == 1
    
    @pytest.mark.asyncio
    async def test_detect_content_spam(self, settings, governance_config):
        """Test spam detection functionality."""
        manager = QualityGovernanceManager(settings, governance_config)
        
        spam_content = {
            "title": "URGENT!!! BUY NOW!!! CLICK HERE!!!",
            "content": "Click here now! Buy buy buy! Urgent offer expires soon! Act now!",
            "url": "https://example.com/spam",
            "word_count": 15,
            "category": "promotional"
        }
        
        spam_signals = await manager._check_spam_signals(spam_content)
        
        assert len(spam_signals) > 0
        assert any("excessive_capitalization" in signal.violation_type for signal in spam_signals)
    
    @pytest.mark.asyncio
    async def test_auto_resolve_violations(self, settings, governance_config):
        """Test automatic violation resolution."""
        manager = QualityGovernanceManager(settings, governance_config)
        
        violations = [
            GovernanceViolation(
                content_url="https://example.com/test1",
                violation_type="minor_quality_issue",
                severity=AlertSeverity.LOW,
                description="Minor formatting issue",
                detected_at=datetime.now(timezone.utc),
                auto_resolvable=True
            ),
            GovernanceViolation(
                content_url="https://example.com/test2",
                violation_type="major_quality_issue",
                severity=AlertSeverity.HIGH,
                description="Major content issue",
                detected_at=datetime.now(timezone.utc),
                auto_resolvable=False
            )
        ]
        
        with patch.object(manager, '_auto_fix_violation', new_callable=AsyncMock) as mock_fix:
            mock_fix.return_value = True
            
            results = await manager.auto_resolve_violations(violations)
            
            assert results['total_violations'] == 2
            assert results['auto_resolvable'] == 1
            assert results['resolved'] == 1
            assert results['failed'] == 0
    
    def test_calculate_content_velocity(self, settings, governance_config):
        """Test content velocity calculation."""
        manager = QualityGovernanceManager(settings, governance_config)
        
        # Mock content with timestamps
        base_time = datetime.now(timezone.utc)
        content_items = []
        
        # Create 10 items over 7 days
        for i in range(10):
            content_items.append({
                "published_at": base_time - timedelta(days=i),
                "url": f"https://example.com/post{i}"
            })
        
        velocity = manager._calculate_content_velocity(content_items, days=7)
        
        assert velocity == 10  # 10 items in 7 days
    
    def test_requires_human_review(self, settings, governance_config):
        """Test human review requirement detection."""
        manager = QualityGovernanceManager(settings, governance_config)
        
        # YMYL content should require review
        ymyl_content = {
            "category": "medical",
            "tags": ["health", "medical advice"]
        }
        
        # General content should not require review
        general_content = {
            "category": "technology",
            "tags": ["programming", "tutorials"]
        }
        
        assert manager._requires_human_review(ymyl_content)
        assert not manager._requires_human_review(general_content)


class TestSpamDetector:
    """Test spam detection functionality."""
    
    def test_spam_detector_initialization(self):
        """Test spam detector initialization."""
        detector = SpamDetector()
        
        assert detector.spam_keywords is not None
        assert detector.suspicious_patterns is not None
    
    def test_detect_keyword_stuffing(self):
        """Test keyword stuffing detection."""
        detector = SpamDetector()
        
        # Content with keyword stuffing
        stuffed_content = "SEO SEO SEO best SEO tips for SEO optimization and SEO ranking SEO"
        stuffed_tokens = stuffed_content.lower().split()
        
        signals = detector._detect_keyword_stuffing(stuffed_tokens)
        
        assert len(signals) > 0
        assert signals[0].signal_type == SpamSignalType.KEYWORD_STUFFING
    
    def test_detect_excessive_capitalization(self):
        """Test excessive capitalization detection."""
        detector = SpamDetector()
        
        caps_content = "THIS IS URGENT!!! BUY NOW OR MISS OUT FOREVER!!!"
        
        signals = detector._detect_excessive_capitalization(caps_content)
        
        assert len(signals) > 0
        assert signals[0].signal_type == SpamSignalType.EXCESSIVE_CAPS
    
    def test_detect_suspicious_patterns(self):
        """Test suspicious pattern detection."""
        detector = SpamDetector()
        
        suspicious_content = "Click here now! Limited time offer! Act fast!"
        
        signals = detector._detect_suspicious_patterns(suspicious_content)
        
        assert len(signals) > 0
        assert signals[0].signal_type == SpamSignalType.SUSPICIOUS_PATTERNS
    
    def test_detect_link_schemes(self):
        """Test link scheme detection."""
        detector = SpamDetector()
        
        # Content with excessive links
        links = ["https://spam1.com", "https://spam2.com", "https://spam3.com"] * 10
        
        signals = detector._detect_link_schemes(links)
        
        assert len(signals) > 0
        assert signals[0].signal_type == SpamSignalType.EXCESSIVE_LINKS


class TestContentSimilarityDetector:
    """Test content similarity detection."""
    
    def test_similarity_detector_initialization(self):
        """Test similarity detector initialization."""
        detector = ContentSimilarityDetector(threshold=0.8)
        
        assert detector.similarity_threshold == 0.8
    
    def test_calculate_similarity_high(self, sample_content, duplicate_content):
        """Test similarity calculation with high similarity."""
        detector = ContentSimilarityDetector()
        
        similarity = detector._calculate_text_similarity(
            sample_content["content"],
            duplicate_content["content"]
        )
        
        # Should detect high similarity
        assert similarity > 0.7
    
    def test_calculate_similarity_low(self, sample_content):
        """Test similarity calculation with low similarity."""
        detector = ContentSimilarityDetector()
        
        different_content = "This is completely different content about cooking recipes."
        
        similarity = detector._calculate_text_similarity(
            sample_content["content"],
            different_content
        )
        
        # Should detect low similarity
        assert similarity < 0.3
    
    @pytest.mark.asyncio
    async def test_check_against_existing_content(self, sample_content, duplicate_content):
        """Test checking content against existing content."""
        detector = ContentSimilarityDetector(threshold=0.8)
        
        existing_content = [sample_content]
        
        violations = await detector.check_against_existing_content(
            duplicate_content,
            existing_content
        )
        
        # Should detect similarity violation
        assert len(violations) > 0
        assert "similarity" in violations[0].violation_type


class TestQualityScore:
    """Test quality score functionality."""
    
    def test_quality_score_creation(self):
        """Test creating a quality score."""
        score = QualityScore(
            overall_score=8.5,
            readability_score=85,
            uniqueness_score=90,
            authority_score=80,
            technical_score=85,
            user_engagement_score=88
        )
        
        assert score.overall_score == 8.5
        assert score.readability_score == 85
        assert score.meets_threshold(6.0)
        assert not score.meets_threshold(9.0)
    
    def test_quality_score_calculation(self):
        """Test quality score calculation logic."""
        score = QualityScore(
            overall_score=0,  # Will be calculated
            readability_score=80,
            uniqueness_score=90,
            authority_score=70,
            technical_score=85,
            user_engagement_score=75
        )
        
        # Test weighted average calculation
        expected_score = (80 + 90 + 70 + 85 + 75) / 5  # 80
        calculated_score = score._calculate_overall_score()
        
        assert abs(calculated_score - expected_score) < 0.1


class TestGovernanceViolation:
    """Test governance violation functionality."""
    
    def test_violation_creation(self):
        """Test creating a governance violation."""
        violation = GovernanceViolation(
            content_url="https://example.com/test",
            violation_type="quality_threshold",
            severity=AlertSeverity.MEDIUM,
            description="Content quality below threshold",
            detected_at=datetime.now(timezone.utc),
            auto_resolvable=True
        )
        
        assert violation.content_url == "https://example.com/test"
        assert violation.severity == AlertSeverity.MEDIUM
        assert violation.auto_resolvable is True
    
    def test_violation_serialization(self):
        """Test violation serialization to dict."""
        violation = GovernanceViolation(
            content_url="https://example.com/test",
            violation_type="spam_detected",
            severity=AlertSeverity.HIGH,
            description="Spam content detected",
            detected_at=datetime.now(timezone.utc),
            auto_resolvable=False
        )
        
        violation_dict = violation.to_dict()
        
        assert violation_dict["content_url"] == "https://example.com/test"
        assert violation_dict["violation_type"] == "spam_detected"
        assert violation_dict["severity"] == "high"


class TestContentFlags:
    """Test content flags functionality."""
    
    def test_content_flags_creation(self):
        """Test creating content flags."""
        flags = ContentFlags(
            requires_human_review=True,
            spam_risk_level="high",
            similarity_matches=2,
            quality_issues=["low_readability", "thin_content"]
        )
        
        assert flags.requires_human_review is True
        assert flags.spam_risk_level == "high"
        assert flags.similarity_matches == 2
        assert len(flags.quality_issues) == 2
    
    def test_content_flags_evaluation(self):
        """Test content flags evaluation."""
        flags = ContentFlags(
            requires_human_review=False,
            spam_risk_level="low",
            similarity_matches=0,
            quality_issues=[]
        )
        
        assert flags.is_safe_to_publish()
        
        # Create flags that should block publishing
        unsafe_flags = ContentFlags(
            requires_human_review=True,
            spam_risk_level="high",
            similarity_matches=3,
            quality_issues=["spam_detected"]
        )
        
        assert not unsafe_flags.is_safe_to_publish()


if __name__ == "__main__":
    pytest.main([__file__])