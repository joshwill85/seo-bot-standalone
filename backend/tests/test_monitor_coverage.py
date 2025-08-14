"""Unit tests for coverage monitoring system."""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, AsyncMock

from src.seo_bot.monitor.coverage import (
    CoverageFreshnessMonitor,
    CoverageViolation,
    CoverageIssueType,
    GSCAdapter
)
from src.seo_bot.config import CoverageSLAConfig, Settings
from src.seo_bot.models import AlertSeverity


@pytest.fixture
def settings():
    """Create test settings."""
    return Settings(
        google_search_console_credentials_file="test_credentials.json"
    )


@pytest.fixture
def sla_config():
    """Create test SLA configuration."""
    return CoverageSLAConfig(
        indexation_target=0.80,
        indexation_timeframe_days=14,
        freshness_review_days=90,
        min_internal_links=8,
        max_orphan_pages=0
    )


@pytest.fixture
def mock_gsc_data():
    """Create mock GSC data."""
    return {
        'rows': [
            {
                'keys': ['https://example.com/page1'],
                'clicks': 100,
                'impressions': 1000,
                'ctr': 0.1,
                'position': 5.5
            },
            {
                'keys': ['https://example.com/page2'],
                'clicks': 0,
                'impressions': 0,
                'ctr': 0.0,
                'position': 50.0
            },
            {
                'keys': ['https://example.com/page3'],
                'clicks': 50,
                'impressions': 500,
                'ctr': 0.1,
                'position': 10.0
            }
        ]
    }


@pytest.fixture
def mock_coverage_data():
    """Create mock coverage data."""
    return {
        'site_info': {
            'siteUrl': 'https://example.com',
            'permissionLevel': 'siteOwner'
        },
        'inspection': {
            'indexStatusResult': {
                'verdict': 'PASS'
            }
        }
    }


class TestGSCAdapter:
    """Test GSC adapter functionality."""
    
    def test_gsc_adapter_initialization(self, settings):
        """Test GSC adapter initialization."""
        with patch('src.seo_bot.monitor.coverage.Credentials.from_service_account_file') as mock_creds:
            with patch('src.seo_bot.monitor.coverage.build') as mock_build:
                mock_creds.return_value = Mock()
                mock_build.return_value = Mock()
                
                adapter = GSCAdapter(settings.google_search_console_credentials_file)
                
                assert adapter.credentials_file == settings.google_search_console_credentials_file
                assert adapter.service is not None
                mock_creds.assert_called_once()
                mock_build.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_indexation_data(self, settings, mock_gsc_data):
        """Test getting indexation data from GSC."""
        with patch('src.seo_bot.monitor.coverage.Credentials.from_service_account_file'):
            with patch('src.seo_bot.monitor.coverage.build') as mock_build:
                # Setup mock service
                mock_service = Mock()
                mock_search_analytics = Mock()
                mock_query = Mock()
                mock_query.execute.return_value = mock_gsc_data
                mock_search_analytics.query.return_value = mock_query
                mock_service.searchanalytics.return_value = mock_search_analytics
                mock_build.return_value = mock_service
                
                adapter = GSCAdapter(settings.google_search_console_credentials_file)
                
                end_date = datetime.now(timezone.utc)
                start_date = end_date - timedelta(days=30)
                
                result = await adapter.get_indexation_data("example.com", start_date, end_date)
                
                assert result == mock_gsc_data
                assert len(result['rows']) == 3
                mock_search_analytics.query.assert_called_once()


class TestCoverageFreshnessMonitor:
    """Test coverage and freshness monitoring."""
    
    def test_monitor_initialization(self, settings, sla_config):
        """Test monitor initialization."""
        monitor = CoverageFreshnessMonitor(settings, sla_config, "example.com")
        
        assert monitor.settings == settings
        assert monitor.sla_config == sla_config
        assert monitor.domain == "example.com"
        assert monitor.gsc_adapter is not None
    
    @pytest.mark.asyncio
    async def test_check_indexation_sla_success(self, settings, sla_config, mock_gsc_data, mock_coverage_data):
        """Test successful SLA check."""
        monitor = CoverageFreshnessMonitor(settings, sla_config, "example.com")
        
        # Mock the GSC adapter methods
        with patch.object(monitor.gsc_adapter, 'get_indexation_data', new_callable=AsyncMock) as mock_indexation:
            with patch.object(monitor.gsc_adapter, 'get_coverage_data', new_callable=AsyncMock) as mock_coverage:
                with patch.object(monitor.gsc_adapter, 'get_mobile_usability', new_callable=AsyncMock) as mock_mobile:
                    mock_indexation.return_value = mock_gsc_data
                    mock_coverage.return_value = mock_coverage_data
                    mock_mobile.return_value = {'rows': []}
                    
                    report = await monitor.check_indexation_sla()
                    
                    assert report.domain == "example.com"
                    assert report.total_pages == 3
                    assert report.indexed_pages == 2  # Pages with impressions > 0
                    assert report.indexation_rate == 2/3  # 66.7%
                    assert not report.sla_compliance  # Below 80% target
    
    @pytest.mark.asyncio
    async def test_identify_coverage_violations(self, settings, sla_config, mock_gsc_data):
        """Test identification of coverage violations."""
        monitor = CoverageFreshnessMonitor(settings, sla_config, "example.com")
        
        violations = await monitor._identify_coverage_violations(mock_gsc_data['rows'])
        
        # Should find one violation (page2 with 0 impressions)
        assert len(violations) == 1
        assert violations[0].url == 'https://example.com/page2'
        assert violations[0].issue_type == CoverageIssueType.SUBMITTED_NOT_INDEXED
        assert violations[0].severity == AlertSeverity.HIGH
    
    @pytest.mark.asyncio
    async def test_auto_resolve_coverage_issues(self, settings, sla_config):
        """Test automatic resolution of coverage issues."""
        monitor = CoverageFreshnessMonitor(settings, sla_config, "example.com")
        
        # Create test violations
        violations = [
            CoverageViolation(
                url="https://example.com/page1",
                issue_type=CoverageIssueType.SUBMITTED_NOT_INDEXED,
                severity=AlertSeverity.HIGH,
                detected_at=datetime.now(timezone.utc),
                description="Test violation",
                suggested_actions=["Request indexing"]
            )
        ]
        
        with patch.object(monitor, '_request_indexing', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = True
            
            results = await monitor.auto_resolve_coverage_issues(violations)
            
            assert results['resolved'] == 1
            assert results['failed'] == 0
            mock_request.assert_called_once_with("https://example.com/page1")
    
    def test_calculate_mobile_usability_score(self, settings, sla_config):
        """Test mobile usability score calculation."""
        monitor = CoverageFreshnessMonitor(settings, sla_config, "example.com")
        
        mobile_data = {
            'rows': [
                {'keys': ['mobile'], 'clicks': 800},
                {'keys': ['desktop'], 'clicks': 200}
            ]
        }
        
        score = monitor._calculate_mobile_usability_score(mobile_data)
        
        assert score == 80.0  # 800/(800+200) * 100


class TestCoverageViolation:
    """Test coverage violation functionality."""
    
    def test_coverage_violation_creation(self):
        """Test creating a coverage violation."""
        violation = CoverageViolation(
            url="https://example.com/test",
            issue_type=CoverageIssueType.CRAWL_ERROR,
            severity=AlertSeverity.MEDIUM,
            detected_at=datetime.now(timezone.utc),
            description="Test crawl error",
            suggested_actions=["Check server logs", "Fix server issues"]
        )
        
        assert violation.url == "https://example.com/test"
        assert violation.issue_type == CoverageIssueType.CRAWL_ERROR
        assert violation.severity == AlertSeverity.MEDIUM
        assert len(violation.suggested_actions) == 2


class TestCoverageMetrics:
    """Test coverage metrics calculations."""
    
    def test_calculate_avg_indexation_time(self, settings, sla_config):
        """Test average indexation time calculation."""
        monitor = CoverageFreshnessMonitor(settings, sla_config, "example.com")
        
        # Mock data
        rows = [
            {'keys': ['page1'], 'clicks': 10, 'impressions': 100},
            {'keys': ['page2'], 'clicks': 5, 'impressions': 50}
        ]
        
        avg_time = monitor._calculate_avg_indexation_time(rows)
        
        # Should return half of the timeframe as estimate
        expected_time = sla_config.indexation_timeframe_days / 2
        assert avg_time == expected_time
    
    def test_extract_crawl_errors(self, settings, sla_config):
        """Test crawl error extraction."""
        monitor = CoverageFreshnessMonitor(settings, sla_config, "example.com")
        
        coverage_data = {
            'site_info': {'errors': []},
            'inspection': {'indexStatusResult': {'verdict': 'PASS'}}
        }
        
        errors = monitor._extract_crawl_errors(coverage_data)
        
        assert isinstance(errors, dict)
        assert 'server_errors' in errors
        assert 'not_found' in errors
        assert 'access_denied' in errors
        assert 'redirect_errors' in errors


class TestCoverageReporting:
    """Test coverage reporting functionality."""
    
    @pytest.mark.asyncio
    async def test_export_coverage_report(self, settings, sla_config, tmp_path):
        """Test exporting coverage report."""
        monitor = CoverageFreshnessMonitor(settings, sla_config, "example.com")
        
        # Create test report
        from src.seo_bot.monitor.coverage import CoverageSLAReport
        
        report = CoverageSLAReport(
            domain="example.com",
            report_date=datetime.now(timezone.utc),
            indexation_rate=0.85,
            sla_compliance=True,
            total_pages=100,
            indexed_pages=85,
            submitted_pages=100,
            coverage_violations=[],
            freshness_violations=[],
            mobile_usability_score=92.5,
            crawl_errors={'server_errors': 0},
            avg_indexation_time_days=7.5,
            trend_data={'indexation_rate_7d': 0.83},
            next_review_date=datetime.now(timezone.utc) + timedelta(days=90)
        )
        
        output_path = tmp_path / "coverage_report.json"
        
        success = await monitor.export_coverage_report(report, output_path)
        
        assert success
        assert output_path.exists()
        
        # Verify report content
        import json
        with open(output_path, 'r') as f:
            report_data = json.load(f)
        
        assert report_data['domain'] == "example.com"
        assert report_data['indexation_rate'] == 0.85
        assert report_data['sla_compliance'] is True


if __name__ == "__main__":
    pytest.main([__file__])