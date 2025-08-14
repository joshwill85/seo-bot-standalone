"""Unit tests for metrics utilities."""

import pytest
import numpy as np
from datetime import datetime, timezone, timedelta

from src.seo_bot.utils.metrics import (
    MetricsAggregator,
    PerformanceCalculator,
    MetricPoint,
    AggregationMethod
)


@pytest.fixture
def sample_metrics():
    """Create sample metric data points."""
    base_time = datetime.now(timezone.utc)
    points = []
    
    for i in range(10):
        timestamp = base_time + timedelta(hours=i)
        value = 100 + np.random.normal(0, 10)  # Mean 100, std 10
        dimensions = {"device": "mobile" if i % 2 == 0 else "desktop"}
        points.append(MetricPoint(timestamp, value, dimensions))
    
    return points


@pytest.fixture
def time_series_data():
    """Create time series data for testing."""
    base_time = datetime.now(timezone.utc) - timedelta(days=30)
    points = []
    
    # Create daily data points for 30 days
    for i in range(30):
        timestamp = base_time + timedelta(days=i)
        # Create trending data
        value = 50 + i * 2 + np.random.normal(0, 5)
        points.append(MetricPoint(timestamp, value))
    
    return points


class TestMetricPoint:
    """Test MetricPoint functionality."""
    
    def test_metric_point_creation(self):
        """Test creating a metric point."""
        timestamp = datetime.now(timezone.utc)
        point = MetricPoint(timestamp, 100.5, {"source": "test"})
        
        assert point.timestamp == timestamp
        assert point.value == 100.5
        assert point.dimensions == {"source": "test"}
    
    def test_metric_point_default_dimensions(self):
        """Test metric point with default dimensions."""
        timestamp = datetime.now(timezone.utc)
        point = MetricPoint(timestamp, 50.0)
        
        assert point.dimensions == {}


class TestMetricsAggregator:
    """Test MetricsAggregator functionality."""
    
    def test_aggregator_initialization(self):
        """Test aggregator initialization."""
        aggregator = MetricsAggregator()
        
        assert aggregator.data_points == []
    
    def test_add_data_point(self):
        """Test adding a data point."""
        aggregator = MetricsAggregator()
        timestamp = datetime.now(timezone.utc)
        
        aggregator.add_data_point(timestamp, 100.0, {"device": "mobile"})
        
        assert len(aggregator.data_points) == 1
        assert aggregator.data_points[0].value == 100.0
        assert aggregator.data_points[0].dimensions == {"device": "mobile"}
    
    def test_add_data_points(self, sample_metrics):
        """Test adding multiple data points."""
        aggregator = MetricsAggregator()
        
        aggregator.add_data_points(sample_metrics)
        
        assert len(aggregator.data_points) == 10
    
    def test_aggregate_by_time_hourly(self, sample_metrics):
        """Test time-based aggregation by hour."""
        aggregator = MetricsAggregator()
        aggregator.add_data_points(sample_metrics)
        
        # Aggregate by 2-hour windows
        result = aggregator.aggregate_by_time(
            time_window=timedelta(hours=2),
            method=AggregationMethod.MEAN
        )
        
        assert len(result) <= 5  # 10 hours / 2-hour windows
        assert all(isinstance(timestamp, datetime) for timestamp, _ in result)
        assert all(isinstance(value, float) for _, value in result)
    
    def test_aggregate_by_dimension(self, sample_metrics):
        """Test dimension-based aggregation."""
        aggregator = MetricsAggregator()
        aggregator.add_data_points(sample_metrics)
        
        result = aggregator.aggregate_by_dimension("device", AggregationMethod.MEAN)
        
        assert "mobile" in result
        assert "desktop" in result
        assert isinstance(result["mobile"], float)
        assert isinstance(result["desktop"], float)
    
    def test_aggregation_methods(self):
        """Test different aggregation methods."""
        aggregator = MetricsAggregator()
        
        # Add known values
        base_time = datetime.now(timezone.utc)
        values = [10, 20, 30, 40, 50]
        for i, value in enumerate(values):
            aggregator.add_data_point(base_time + timedelta(minutes=i), value)
        
        result_mean = aggregator.aggregate_by_time(timedelta(hours=1), AggregationMethod.MEAN)
        result_sum = aggregator.aggregate_by_time(timedelta(hours=1), AggregationMethod.SUM)
        result_min = aggregator.aggregate_by_time(timedelta(hours=1), AggregationMethod.MIN)
        result_max = aggregator.aggregate_by_time(timedelta(hours=1), AggregationMethod.MAX)
        
        # All should be in single window
        assert len(result_mean) == 1
        assert result_mean[0][1] == 30.0  # Mean of [10,20,30,40,50]
        assert result_sum[0][1] == 150.0  # Sum
        assert result_min[0][1] == 10.0   # Min
        assert result_max[0][1] == 50.0   # Max
    
    def test_calculate_trend_linear(self, time_series_data):
        """Test linear trend calculation."""
        aggregator = MetricsAggregator()
        aggregator.add_data_points(time_series_data)
        
        trend = aggregator.calculate_trend(window_days=30, method="linear")
        
        assert "trend" in trend
        assert "correlation" in trend
        assert "confidence" in trend
        
        # Should detect positive trend (data increases over time)
        assert trend["trend"] > 0
        assert trend["confidence"] > 0
    
    def test_calculate_trend_percentage(self, time_series_data):
        """Test percentage trend calculation."""
        aggregator = MetricsAggregator()
        aggregator.add_data_points(time_series_data)
        
        trend = aggregator.calculate_trend(window_days=30, method="percentage")
        
        assert "trend" in trend
        assert "confidence" in trend
        
        # Should detect positive trend
        assert trend["trend"] > 0
    
    def test_detect_anomalies(self):
        """Test anomaly detection."""
        aggregator = MetricsAggregator()
        base_time = datetime.now(timezone.utc)
        
        # Add normal data points
        for i in range(20):
            value = 100 + np.random.normal(0, 5)  # Normal distribution
            aggregator.add_data_point(base_time + timedelta(minutes=i), value)
        
        # Add anomalous point
        aggregator.add_data_point(base_time + timedelta(minutes=20), 200)  # Clear outlier
        
        anomalies = aggregator.detect_anomalies(sensitivity=2.0, window_size=10)
        
        # Should detect the outlier
        assert len(anomalies) >= 1
        assert any(abs(a.value - 200) < 1 for a in anomalies)
    
    def test_calculate_percentiles(self, sample_metrics):
        """Test percentile calculation."""
        aggregator = MetricsAggregator()
        aggregator.add_data_points(sample_metrics)
        
        percentiles = aggregator.calculate_percentiles([50, 90, 95, 99])
        
        assert "p50" in percentiles
        assert "p90" in percentiles
        assert "p95" in percentiles
        assert "p99" in percentiles
        
        # Percentiles should be in order
        assert percentiles["p50"] <= percentiles["p90"]
        assert percentiles["p90"] <= percentiles["p95"]
        assert percentiles["p95"] <= percentiles["p99"]
    
    def test_get_summary_stats(self, sample_metrics):
        """Test summary statistics calculation."""
        aggregator = MetricsAggregator()
        aggregator.add_data_points(sample_metrics)
        
        stats = aggregator.get_summary_stats()
        
        required_fields = ["count", "mean", "median", "std", "min", "max"]
        for field in required_fields:
            assert field in stats
            assert isinstance(stats[field], (int, float))
        
        assert stats["count"] == 10
        assert stats["min"] <= stats["mean"] <= stats["max"]
        assert stats["min"] <= stats["median"] <= stats["max"]
    
    def test_empty_aggregator(self):
        """Test aggregator behavior with no data."""
        aggregator = MetricsAggregator()
        
        # Should handle empty data gracefully
        time_agg = aggregator.aggregate_by_time(timedelta(hours=1))
        dim_agg = aggregator.aggregate_by_dimension("device")
        stats = aggregator.get_summary_stats()
        
        assert time_agg == []
        assert dim_agg == {}
        assert stats["count"] == 0


class TestPerformanceCalculator:
    """Test PerformanceCalculator functionality."""
    
    def test_core_web_vitals_good(self):
        """Test Core Web Vitals calculation with good scores."""
        result = PerformanceCalculator.calculate_core_web_vitals_score(
            lcp=2000,  # Good
            inp=150,   # Good
            cls=0.05   # Good
        )
        
        assert result["overall_rating"] == "good"
        assert result["passes_cwv"] is True
        assert result["lcp_rating"] == "good"
        assert result["inp_rating"] == "good"
        assert result["cls_rating"] == "good"
        assert result["overall_score"] > 80
    
    def test_core_web_vitals_poor(self):
        """Test Core Web Vitals calculation with poor scores."""
        result = PerformanceCalculator.calculate_core_web_vitals_score(
            lcp=5000,  # Poor
            inp=800,   # Poor
            cls=0.5    # Poor
        )
        
        assert result["overall_rating"] == "needs-improvement"
        assert result["passes_cwv"] is False
        assert result["lcp_rating"] == "poor"
        assert result["inp_rating"] == "poor"
        assert result["cls_rating"] == "poor"
        assert result["overall_score"] < 50
    
    def test_core_web_vitals_mixed(self):
        """Test Core Web Vitals calculation with mixed scores."""
        result = PerformanceCalculator.calculate_core_web_vitals_score(
            lcp=2000,  # Good
            inp=300,   # Needs improvement
            cls=0.3    # Poor
        )
        
        # Overall should be needs-improvement (not all good)
        assert result["overall_rating"] == "needs-improvement"
        assert result["passes_cwv"] is False
        assert result["lcp_rating"] == "good"
        assert result["inp_rating"] == "needs-improvement"
        assert result["cls_rating"] == "poor"
    
    def test_seo_visibility_score(self):
        """Test SEO visibility score calculation."""
        rankings = {
            "keyword1": 3.0,
            "keyword2": 8.0,
            "keyword3": 15.0,
            "keyword4": 25.0
        }
        
        result = PerformanceCalculator.calculate_seo_visibility_score(
            rankings=rankings,
            impressions=10000,
            clicks=500
        )
        
        assert "overall_score" in result
        assert "position_score" in result
        assert "impressions_score" in result
        assert "ctr_score" in result
        assert "rankings_score" in result
        assert "average_position" in result
        assert "ctr" in result
        assert "top_10_rankings" in result
        
        assert 0 <= result["overall_score"] <= 100
        assert result["ctr"] == 0.05  # 500/10000
        assert result["top_10_rankings"] == 2  # Keywords 1 and 2
        assert result["average_position"] == 12.75  # (3+8+15+25)/4
    
    def test_seo_visibility_no_rankings(self):
        """Test SEO visibility with no rankings."""
        result = PerformanceCalculator.calculate_seo_visibility_score(
            rankings={},
            impressions=1000,
            clicks=50
        )
        
        assert result["overall_score"] >= 0
        assert result["average_position"] == 0
        assert result["top_10_rankings"] == 0
        assert result["rankings_score"] == 0
    
    def test_content_freshness_score(self):
        """Test content freshness score calculation."""
        # Mix of fresh and stale content (ages in days)
        content_ages = [30, 60, 90, 200, 400, 500]  # 3 fresh, 3 stale (target 365)
        
        result = PerformanceCalculator.calculate_content_freshness_score(
            content_ages=content_ages,
            target_max_age=365
        )
        
        assert "score" in result
        assert "fresh_content" in result
        assert "stale_content" in result
        assert "avg_age" in result
        assert "freshness_ratio" in result
        
        assert 0 <= result["score"] <= 100
        assert result["fresh_content"] == 3  # Ages <= 365
        assert result["stale_content"] == 3  # Ages > 365
        assert result["freshness_ratio"] == 0.5  # 3/6
    
    def test_content_freshness_all_fresh(self):
        """Test content freshness with all fresh content."""
        content_ages = [10, 30, 60, 100, 200]  # All under 365
        
        result = PerformanceCalculator.calculate_content_freshness_score(
            content_ages=content_ages,
            target_max_age=365
        )
        
        assert result["fresh_content"] == 5
        assert result["stale_content"] == 0
        assert result["freshness_ratio"] == 1.0
        assert result["score"] > 80  # Should be high score
    
    def test_quality_trend(self):
        """Test quality trend calculation."""
        base_time = datetime.now(timezone.utc)
        
        # Create trending quality scores
        quality_scores = []
        for i in range(60):  # 60 days of data
            date = base_time - timedelta(days=60-i)
            score = 6.0 + (i / 60) * 2.0  # Trend from 6.0 to 8.0
            quality_scores.append((date, score))
        
        result = PerformanceCalculator.calculate_quality_trend(
            quality_scores=quality_scores,
            days=30
        )
        
        assert "trend" in result
        assert "current_avg" in result
        assert "previous_avg" in result
        assert "data_points" in result
        
        # Should detect positive trend
        assert result["trend"] > 0
        assert result["current_avg"] > result["previous_avg"]
        assert result["data_points"] == 60
    
    def test_quality_trend_no_change(self):
        """Test quality trend with no change."""
        base_time = datetime.now(timezone.utc)
        
        # Flat quality scores
        quality_scores = []
        for i in range(60):
            date = base_time - timedelta(days=60-i)
            score = 7.0  # Constant
            quality_scores.append((date, score))
        
        result = PerformanceCalculator.calculate_quality_trend(
            quality_scores=quality_scores,
            days=30
        )
        
        assert abs(result["trend"]) < 1.0  # Very small trend
        assert abs(result["current_avg"] - result["previous_avg"]) < 0.1
    
    def test_indexation_health_excellent(self):
        """Test indexation health with excellent metrics."""
        result = PerformanceCalculator.calculate_indexation_health(
            submitted=100,
            indexed=95,
            excluded=3,
            errors=2
        )
        
        assert result["rating"] == "excellent"
        assert result["score"] >= 80
        assert result["indexation_rate"] == 0.95
        assert result["error_rate"] == 0.02
        assert result["exclusion_rate"] == 0.03
    
    def test_indexation_health_poor(self):
        """Test indexation health with poor metrics."""
        result = PerformanceCalculator.calculate_indexation_health(
            submitted=100,
            indexed=30,
            excluded=20,
            errors=50
        )
        
        assert result["rating"] == "poor"
        assert result["score"] < 40
        assert result["indexation_rate"] == 0.3
        assert result["error_rate"] == 0.5
        assert result["exclusion_rate"] == 0.2
    
    def test_indexation_health_no_data(self):
        """Test indexation health with no data."""
        result = PerformanceCalculator.calculate_indexation_health(
            submitted=0,
            indexed=0,
            excluded=0,
            errors=0
        )
        
        assert result["rating"] == "no-data"
        assert result["score"] == 0
        assert result["indexation_rate"] == 0


if __name__ == "__main__":
    pytest.main([__file__])