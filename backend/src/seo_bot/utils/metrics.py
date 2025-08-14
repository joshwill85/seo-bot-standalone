"""Metrics aggregation and calculation utilities."""

import logging
import statistics
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass
from enum import Enum

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class AggregationMethod(Enum):
    """Methods for aggregating metrics."""
    MEAN = "mean"
    MEDIAN = "median"
    SUM = "sum"
    MIN = "min"
    MAX = "max"
    P95 = "p95"
    P99 = "p99"


@dataclass
class MetricPoint:
    """Individual metric data point."""
    timestamp: datetime
    value: float
    dimensions: Dict[str, str] = None
    
    def __post_init__(self):
        if self.dimensions is None:
            self.dimensions = {}


class MetricsAggregator:
    """Aggregates and analyzes time-series metrics data."""
    
    def __init__(self):
        """Initialize metrics aggregator."""
        self.data_points: List[MetricPoint] = []
    
    def add_data_point(self, timestamp: datetime, value: float, dimensions: Dict[str, str] = None):
        """Add a metric data point."""
        point = MetricPoint(timestamp, value, dimensions or {})
        self.data_points.append(point)
    
    def add_data_points(self, points: List[MetricPoint]):
        """Add multiple metric data points."""
        self.data_points.extend(points)
    
    def aggregate_by_time(self, 
                          time_window: timedelta,
                          method: AggregationMethod = AggregationMethod.MEAN,
                          start_time: Optional[datetime] = None,
                          end_time: Optional[datetime] = None) -> List[Tuple[datetime, float]]:
        """Aggregate data points by time windows."""
        
        if not self.data_points:
            return []
        
        # Filter by time range if specified
        filtered_points = self.data_points
        if start_time or end_time:
            filtered_points = [
                p for p in self.data_points
                if (start_time is None or p.timestamp >= start_time) and
                   (end_time is None or p.timestamp <= end_time)
            ]
        
        if not filtered_points:
            return []
        
        # Sort by timestamp
        filtered_points.sort(key=lambda p: p.timestamp)
        
        # Group by time windows
        aggregated = []
        current_window_start = filtered_points[0].timestamp
        current_window_points = []
        
        for point in filtered_points:
            # Check if point belongs to current window
            if point.timestamp < current_window_start + time_window:
                current_window_points.append(point.value)
            else:
                # Process current window
                if current_window_points:
                    agg_value = self._apply_aggregation_method(current_window_points, method)
                    aggregated.append((current_window_start, agg_value))
                
                # Start new window
                current_window_start = point.timestamp
                current_window_points = [point.value]
        
        # Process final window
        if current_window_points:
            agg_value = self._apply_aggregation_method(current_window_points, method)
            aggregated.append((current_window_start, agg_value))
        
        return aggregated
    
    def aggregate_by_dimension(self, 
                               dimension_key: str,
                               method: AggregationMethod = AggregationMethod.MEAN) -> Dict[str, float]:
        """Aggregate data points by dimension values."""
        
        if not self.data_points:
            return {}
        
        # Group by dimension value
        dimension_groups = {}
        for point in self.data_points:
            dim_value = point.dimensions.get(dimension_key, "unknown")
            if dim_value not in dimension_groups:
                dimension_groups[dim_value] = []
            dimension_groups[dim_value].append(point.value)
        
        # Aggregate each group
        aggregated = {}
        for dim_value, values in dimension_groups.items():
            aggregated[dim_value] = self._apply_aggregation_method(values, method)
        
        return aggregated
    
    def calculate_trend(self, 
                        window_days: int = 7,
                        method: str = "linear") -> Dict[str, float]:
        """Calculate trend statistics for the metric."""
        
        if len(self.data_points) < 2:
            return {"trend": 0.0, "confidence": 0.0}
        
        # Get data for trend calculation
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=window_days)
        
        trend_points = [
            p for p in self.data_points
            if start_time <= p.timestamp <= end_time
        ]
        
        if len(trend_points) < 2:
            return {"trend": 0.0, "confidence": 0.0}
        
        # Sort by timestamp
        trend_points.sort(key=lambda p: p.timestamp)
        
        # Convert to numerical arrays
        timestamps = [(p.timestamp - trend_points[0].timestamp).total_seconds() for p in trend_points]
        values = [p.value for p in trend_points]
        
        if method == "linear":
            # Linear regression
            correlation = np.corrcoef(timestamps, values)[0, 1] if len(timestamps) > 1 else 0
            slope = np.polyfit(timestamps, values, 1)[0] if len(timestamps) > 1 else 0
            
            return {
                "trend": slope,
                "correlation": correlation,
                "confidence": abs(correlation)
            }
        else:
            # Simple percentage change
            if len(values) >= 2:
                start_value = values[0]
                end_value = values[-1]
                
                if start_value != 0:
                    trend = ((end_value - start_value) / start_value) * 100
                else:
                    trend = 0.0
                
                return {
                    "trend": trend,
                    "confidence": min(1.0, len(values) / 10.0)  # More data = higher confidence
                }
            else:
                return {"trend": 0.0, "confidence": 0.0}
    
    def detect_anomalies(self, 
                         sensitivity: float = 2.0,
                         window_size: int = 10) -> List[MetricPoint]:
        """Detect anomalous data points using statistical methods."""
        
        if len(self.data_points) < window_size:
            return []
        
        anomalies = []
        
        # Sort by timestamp
        sorted_points = sorted(self.data_points, key=lambda p: p.timestamp)
        
        for i in range(window_size, len(sorted_points)):
            # Get window of previous points
            window = sorted_points[i-window_size:i]
            window_values = [p.value for p in window]
            
            # Calculate statistics
            mean_val = statistics.mean(window_values)
            std_val = statistics.stdev(window_values) if len(window_values) > 1 else 0
            
            # Check if current point is anomalous
            current_point = sorted_points[i]
            if std_val > 0:
                z_score = abs(current_point.value - mean_val) / std_val
                if z_score > sensitivity:
                    anomalies.append(current_point)
        
        return anomalies
    
    def calculate_percentiles(self, percentiles: List[float] = None) -> Dict[str, float]:
        """Calculate percentile values for the metric."""
        
        if percentiles is None:
            percentiles = [50, 90, 95, 99]
        
        if not self.data_points:
            return {f"p{p}": 0.0 for p in percentiles}
        
        values = [p.value for p in self.data_points]
        
        result = {}
        for p in percentiles:
            result[f"p{p}"] = np.percentile(values, p)
        
        return result
    
    def get_summary_stats(self) -> Dict[str, float]:
        """Get comprehensive summary statistics."""
        
        if not self.data_points:
            return {
                "count": 0,
                "mean": 0.0,
                "median": 0.0,
                "std": 0.0,
                "min": 0.0,
                "max": 0.0
            }
        
        values = [p.value for p in self.data_points]
        
        return {
            "count": len(values),
            "mean": statistics.mean(values),
            "median": statistics.median(values),
            "std": statistics.stdev(values) if len(values) > 1 else 0.0,
            "min": min(values),
            "max": max(values)
        }
    
    def _apply_aggregation_method(self, values: List[float], method: AggregationMethod) -> float:
        """Apply aggregation method to a list of values."""
        
        if not values:
            return 0.0
        
        if method == AggregationMethod.MEAN:
            return statistics.mean(values)
        elif method == AggregationMethod.MEDIAN:
            return statistics.median(values)
        elif method == AggregationMethod.SUM:
            return sum(values)
        elif method == AggregationMethod.MIN:
            return min(values)
        elif method == AggregationMethod.MAX:
            return max(values)
        elif method == AggregationMethod.P95:
            return np.percentile(values, 95)
        elif method == AggregationMethod.P99:
            return np.percentile(values, 99)
        else:
            return statistics.mean(values)


class PerformanceCalculator:
    """Calculates performance metrics and KPIs."""
    
    @staticmethod
    def calculate_core_web_vitals_score(lcp: float, inp: float, cls: float) -> Dict[str, Union[float, str]]:
        """Calculate Core Web Vitals score and rating."""
        
        # LCP thresholds (milliseconds)
        lcp_good = 2500
        lcp_needs_improvement = 4000
        
        # INP thresholds (milliseconds)  
        inp_good = 200
        inp_needs_improvement = 500
        
        # CLS thresholds
        cls_good = 0.1
        cls_needs_improvement = 0.25
        
        # Rate individual metrics
        lcp_rating = "good" if lcp <= lcp_good else "needs-improvement" if lcp <= lcp_needs_improvement else "poor"
        inp_rating = "good" if inp <= inp_good else "needs-improvement" if inp <= inp_needs_improvement else "poor"
        cls_rating = "good" if cls <= cls_good else "needs-improvement" if cls <= cls_needs_improvement else "poor"
        
        # Calculate numeric scores (0-100)
        lcp_score = max(0, 100 - (lcp / lcp_good) * 50) if lcp <= lcp_needs_improvement else max(0, 50 - ((lcp - lcp_needs_improvement) / lcp_needs_improvement) * 50)
        inp_score = max(0, 100 - (inp / inp_good) * 50) if inp <= inp_needs_improvement else max(0, 50 - ((inp - inp_needs_improvement) / inp_needs_improvement) * 50)
        cls_score = max(0, 100 - (cls / cls_good) * 50) if cls <= cls_needs_improvement else max(0, 50 - ((cls - cls_needs_improvement) / cls_needs_improvement) * 50)
        
        # Overall CWV score (all must be good for overall good rating)
        overall_rating = "good" if all(r == "good" for r in [lcp_rating, inp_rating, cls_rating]) else "needs-improvement"
        overall_score = (lcp_score + inp_score + cls_score) / 3
        
        return {
            "overall_score": overall_score,
            "overall_rating": overall_rating,
            "lcp_score": lcp_score,
            "lcp_rating": lcp_rating,
            "inp_score": inp_score,
            "inp_rating": inp_rating,
            "cls_score": cls_score,
            "cls_rating": cls_rating,
            "passes_cwv": overall_rating == "good"
        }
    
    @staticmethod
    def calculate_seo_visibility_score(rankings: Dict[str, float], 
                                       impressions: int,
                                       clicks: int) -> Dict[str, float]:
        """Calculate SEO visibility and performance score."""
        
        # Average position score (lower position = higher score)
        if rankings:
            avg_position = sum(rankings.values()) / len(rankings)
            position_score = max(0, 100 - (avg_position - 1) * 5)  # Score decreases by 5 per position
        else:
            position_score = 0
        
        # Impressions score (logarithmic scale)
        impressions_score = min(100, (np.log10(max(1, impressions)) / 6) * 100)  # Max at 1M impressions
        
        # CTR score
        ctr = clicks / impressions if impressions > 0 else 0
        ctr_score = min(100, ctr * 2000)  # 5% CTR = 100 points
        
        # Rankings distribution score
        if rankings:
            top_10_count = sum(1 for pos in rankings.values() if pos <= 10)
            rankings_score = (top_10_count / len(rankings)) * 100
        else:
            rankings_score = 0
        
        # Overall visibility score (weighted average)
        overall_score = (
            position_score * 0.3 +
            impressions_score * 0.25 +
            ctr_score * 0.25 +
            rankings_score * 0.2
        )
        
        return {
            "overall_score": overall_score,
            "position_score": position_score,
            "impressions_score": impressions_score,
            "ctr_score": ctr_score,
            "rankings_score": rankings_score,
            "average_position": avg_position if rankings else 0,
            "ctr": ctr,
            "top_10_rankings": top_10_count if rankings else 0
        }
    
    @staticmethod
    def calculate_content_freshness_score(content_ages: List[int],
                                          target_max_age: int = 365) -> Dict[str, Union[float, int]]:
        """Calculate content freshness score."""
        
        if not content_ages:
            return {"score": 0, "fresh_content": 0, "stale_content": 0, "avg_age": 0}
        
        # Count fresh vs stale content
        fresh_content = sum(1 for age in content_ages if age <= target_max_age)
        stale_content = len(content_ages) - fresh_content
        
        # Calculate freshness score
        freshness_ratio = fresh_content / len(content_ages)
        
        # Apply age penalty to score
        avg_age = sum(content_ages) / len(content_ages)
        age_penalty = min(50, (avg_age / target_max_age) * 25)  # Max 50 point penalty
        
        score = max(0, (freshness_ratio * 100) - age_penalty)
        
        return {
            "score": score,
            "fresh_content": fresh_content,
            "stale_content": stale_content,
            "avg_age": avg_age,
            "freshness_ratio": freshness_ratio
        }
    
    @staticmethod
    def calculate_quality_trend(quality_scores: List[Tuple[datetime, float]],
                                days: int = 30) -> Dict[str, float]:
        """Calculate quality trend over time."""
        
        if len(quality_scores) < 2:
            return {"trend": 0.0, "current_avg": 0.0, "previous_avg": 0.0}
        
        # Sort by date
        sorted_scores = sorted(quality_scores, key=lambda x: x[0])
        
        # Split into current and previous periods
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        current_scores = [score for date, score in sorted_scores if date >= cutoff_date]
        previous_scores = [score for date, score in sorted_scores if date < cutoff_date]
        
        current_avg = sum(current_scores) / len(current_scores) if current_scores else 0
        previous_avg = sum(previous_scores) / len(previous_scores) if previous_scores else current_avg
        
        # Calculate trend
        if previous_avg > 0:
            trend = ((current_avg - previous_avg) / previous_avg) * 100
        else:
            trend = 0.0
        
        return {
            "trend": trend,
            "current_avg": current_avg,
            "previous_avg": previous_avg,
            "data_points": len(sorted_scores)
        }
    
    @staticmethod
    def calculate_indexation_health(submitted: int,
                                    indexed: int,
                                    excluded: int,
                                    errors: int) -> Dict[str, Union[float, str]]:
        """Calculate indexation health score."""
        
        total = submitted + excluded + errors
        if total == 0:
            return {"score": 0, "rating": "no-data", "indexation_rate": 0}
        
        # Indexation rate
        indexation_rate = indexed / total if total > 0 else 0
        
        # Error rate
        error_rate = errors / total if total > 0 else 0
        
        # Exclusion rate
        exclusion_rate = excluded / total if total > 0 else 0
        
        # Calculate score
        base_score = indexation_rate * 100
        error_penalty = error_rate * 50  # Errors are worse than exclusions
        exclusion_penalty = exclusion_rate * 25
        
        score = max(0, base_score - error_penalty - exclusion_penalty)
        
        # Determine rating
        if score >= 80:
            rating = "excellent"
        elif score >= 60:
            rating = "good"
        elif score >= 40:
            rating = "needs-improvement"
        else:
            rating = "poor"
        
        return {
            "score": score,
            "rating": rating,
            "indexation_rate": indexation_rate,
            "error_rate": error_rate,
            "exclusion_rate": exclusion_rate
        }