"""Unit tests for monitoring dashboard system."""

import pytest
import asyncio
import json
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, AsyncMock

from src.seo_bot.monitor.dashboard import (
    DashboardServer,
    MetricsCollector,
    DashboardDataProcessor,
    DashboardWidget,
    WidgetType,
    KPIMetric,
    ChartData,
    SystemStatus
)
from src.seo_bot.config import DashboardConfig, Settings


@pytest.fixture
def dashboard_config():
    """Create test dashboard configuration."""
    return DashboardConfig(
        host="localhost",
        port=8080,
        auto_refresh_seconds=30,
        max_data_points=1000,
        enable_auth=False
    )


@pytest.fixture
def settings():
    """Create test settings."""
    return Settings()


@pytest.fixture
def sample_metrics_data():
    """Create sample metrics data."""
    base_time = datetime.now(timezone.utc)
    return [
        {
            "timestamp": base_time - timedelta(minutes=i),
            "metric_name": "error_rate",
            "value": 0.02 + (i % 3) * 0.005,
            "dimensions": {"source": "api"}
        }
        for i in range(60)  # 1 hour of data
    ]


@pytest.fixture
def sample_kpi_data():
    """Create sample KPI data."""
    return {
        "indexation_rate": 0.85,
        "avg_position": 12.5,
        "total_clicks": 1500,
        "total_impressions": 25000,
        "ctr": 0.06,
        "coverage_violations": 3
    }


class TestDashboardServer:
    """Test dashboard server functionality."""
    
    def test_server_initialization(self, settings, dashboard_config):
        """Test server initialization."""
        server = DashboardServer(settings, dashboard_config)
        
        assert server.settings == settings
        assert server.dashboard_config == dashboard_config
        assert isinstance(server.metrics_collector, MetricsCollector)
        assert isinstance(server.data_processor, DashboardDataProcessor)
    
    @pytest.mark.asyncio
    async def test_get_dashboard_data(self, settings, dashboard_config, sample_kpi_data):
        """Test getting dashboard data."""
        server = DashboardServer(settings, dashboard_config)
        
        # Mock data collection
        with patch.object(server.metrics_collector, 'get_current_kpis', new_callable=AsyncMock) as mock_kpis:
            mock_kpis.return_value = sample_kpi_data
            
            with patch.object(server.data_processor, 'get_chart_data', new_callable=AsyncMock) as mock_charts:
                mock_charts.return_value = {
                    "error_rate": ChartData(
                        labels=["10:00", "10:15", "10:30"],
                        datasets=[{"label": "Error Rate", "data": [0.02, 0.025, 0.03]}]
                    )
                }
                
                with patch.object(server, '_get_system_status', new_callable=AsyncMock) as mock_status:
                    mock_status.return_value = SystemStatus(
                        overall_health="healthy",
                        services_up=5,
                        services_down=0,
                        last_updated=datetime.now(timezone.utc)
                    )
                    
                    data = await server.get_dashboard_data()
                    
                    assert "kpis" in data
                    assert "charts" in data
                    assert "system_status" in data
                    assert data["kpis"]["indexation_rate"] == 0.85
    
    @pytest.mark.asyncio
    async def test_websocket_connection(self, settings, dashboard_config):
        """Test WebSocket connection handling."""
        server = DashboardServer(settings, dashboard_config)
        
        # Mock WebSocket
        mock_websocket = AsyncMock()
        mock_websocket.send_text = AsyncMock()
        
        # Mock dashboard data
        with patch.object(server, 'get_dashboard_data', new_callable=AsyncMock) as mock_data:
            mock_data.return_value = {"test": "data"}
            
            # Simulate connection
            server.active_connections.add(mock_websocket)
            
            await server.broadcast_update()
            
            mock_websocket.send_text.assert_called_once()
            call_args = mock_websocket.send_text.call_args[0][0]
            sent_data = json.loads(call_args)
            assert sent_data["type"] == "dashboard_update"
    
    def test_create_widgets(self, settings, dashboard_config):
        """Test widget creation."""
        server = DashboardServer(settings, dashboard_config)
        
        widgets = server._create_widgets()
        
        assert len(widgets) > 0
        assert any(w.widget_type == WidgetType.KPI for w in widgets)
        assert any(w.widget_type == WidgetType.CHART for w in widgets)
        assert any(w.widget_type == WidgetType.TABLE for w in widgets)
    
    def test_validate_widget_config(self, settings, dashboard_config):
        """Test widget configuration validation."""
        server = DashboardServer(settings, dashboard_config)
        
        valid_widget = DashboardWidget(
            id="test_widget",
            title="Test Widget",
            widget_type=WidgetType.KPI,
            config={"metric": "error_rate", "format": "percentage"}
        )
        
        invalid_widget = DashboardWidget(
            id="invalid_widget",
            title="Invalid Widget",
            widget_type=WidgetType.KPI,
            config={}  # Missing required config
        )
        
        assert server._validate_widget_config(valid_widget)
        assert not server._validate_widget_config(invalid_widget)


class TestMetricsCollector:
    """Test metrics collection functionality."""
    
    def test_collector_initialization(self, settings):
        """Test metrics collector initialization."""
        collector = MetricsCollector(settings)
        
        assert collector.settings == settings
    
    @pytest.mark.asyncio
    async def test_get_current_kpis(self, settings):
        """Test getting current KPIs."""
        collector = MetricsCollector(settings)
        
        # Mock various data sources
        with patch.object(collector, '_get_indexation_metrics', new_callable=AsyncMock) as mock_indexation:
            mock_indexation.return_value = {"indexation_rate": 0.85, "total_pages": 1000}
            
            with patch.object(collector, '_get_performance_metrics', new_callable=AsyncMock) as mock_performance:
                mock_performance.return_value = {"avg_lcp": 2500, "avg_cls": 0.1}
                
                with patch.object(collector, '_get_traffic_metrics', new_callable=AsyncMock) as mock_traffic:
                    mock_traffic.return_value = {"total_clicks": 1500, "total_impressions": 25000}
                    
                    kpis = await collector.get_current_kpis()
                    
                    assert "indexation_rate" in kpis
                    assert "total_clicks" in kpis
                    assert "avg_lcp" in kpis
    
    @pytest.mark.asyncio
    async def test_get_time_series_data(self, settings, sample_metrics_data):
        """Test getting time series data."""
        collector = MetricsCollector(settings)
        
        # Mock database query
        with patch.object(collector, '_query_metrics_database', new_callable=AsyncMock) as mock_query:
            mock_query.return_value = sample_metrics_data
            
            data = await collector.get_time_series_data(
                "error_rate",
                start_time=datetime.now(timezone.utc) - timedelta(hours=1),
                end_time=datetime.now(timezone.utc)
            )
            
            assert len(data) == 60
            assert all("timestamp" in point for point in data)
            assert all("value" in point for point in data)
    
    @pytest.mark.asyncio
    async def test_get_alert_summary(self, settings):
        """Test getting alert summary."""
        collector = MetricsCollector(settings)
        
        # Mock alert data
        with patch.object(collector, '_get_recent_alerts', new_callable=AsyncMock) as mock_alerts:
            mock_alerts.return_value = [
                {"severity": "high", "status": "active"},
                {"severity": "medium", "status": "resolved"},
                {"severity": "low", "status": "active"}
            ]
            
            summary = await collector.get_alert_summary()
            
            assert "total_alerts" in summary
            assert "active_alerts" in summary
            assert "by_severity" in summary
            assert summary["active_alerts"] == 2
    
    def test_calculate_derived_metrics(self, settings):
        """Test derived metrics calculation."""
        collector = MetricsCollector(settings)
        
        base_metrics = {
            "total_clicks": 1500,
            "total_impressions": 25000,
            "indexed_pages": 850,
            "total_pages": 1000
        }
        
        derived = collector._calculate_derived_metrics(base_metrics)
        
        assert "ctr" in derived
        assert "indexation_rate" in derived
        assert abs(derived["ctr"] - 0.06) < 0.001  # 1500/25000
        assert abs(derived["indexation_rate"] - 0.85) < 0.001  # 850/1000


class TestDashboardDataProcessor:
    """Test dashboard data processing functionality."""
    
    def test_processor_initialization(self):
        """Test data processor initialization."""
        processor = DashboardDataProcessor()
        
        assert processor.max_data_points == 1000
    
    @pytest.mark.asyncio
    async def test_get_chart_data(self, sample_metrics_data):
        """Test getting chart data."""
        processor = DashboardDataProcessor()
        
        # Mock time series data
        with patch.object(processor, '_get_time_series', new_callable=AsyncMock) as mock_series:
            mock_series.return_value = sample_metrics_data
            
            chart_data = await processor.get_chart_data("error_rate")
            
            assert isinstance(chart_data, ChartData)
            assert len(chart_data.labels) > 0
            assert len(chart_data.datasets) > 0
            assert chart_data.datasets[0]["label"] == "Error Rate"
    
    def test_process_kpi_metrics(self, sample_kpi_data):
        """Test KPI metrics processing."""
        processor = DashboardDataProcessor()
        
        kpis = processor.process_kpi_metrics(sample_kpi_data)
        
        assert len(kpis) > 0
        assert all(isinstance(kpi, KPIMetric) for kpi in kpis)
        
        # Check specific KPI processing
        indexation_kpi = next((k for k in kpis if k.name == "Indexation Rate"), None)
        assert indexation_kpi is not None
        assert indexation_kpi.value == "85.0%"
        assert indexation_kpi.trend_direction in ["up", "down", "stable"]
    
    def test_aggregate_time_series(self, sample_metrics_data):
        """Test time series aggregation."""
        processor = DashboardDataProcessor()
        
        # Test hourly aggregation
        aggregated = processor._aggregate_time_series(
            sample_metrics_data, 
            interval="hourly"
        )
        
        assert len(aggregated) <= len(sample_metrics_data)
        assert all("timestamp" in point for point in aggregated)
        assert all("value" in point for point in aggregated)
    
    def test_calculate_trends(self):
        """Test trend calculation."""
        processor = DashboardDataProcessor()
        
        # Increasing trend
        increasing_values = [1, 2, 3, 4, 5]
        trend_up = processor._calculate_trend(increasing_values)
        assert trend_up["direction"] == "up"
        assert trend_up["percentage"] > 0
        
        # Decreasing trend
        decreasing_values = [5, 4, 3, 2, 1]
        trend_down = processor._calculate_trend(decreasing_values)
        assert trend_down["direction"] == "down"
        assert trend_down["percentage"] < 0
        
        # Stable trend
        stable_values = [3, 3, 3, 3, 3]
        trend_stable = processor._calculate_trend(stable_values)
        assert trend_stable["direction"] == "stable"
        assert abs(trend_stable["percentage"]) < 1


class TestDashboardWidget:
    """Test dashboard widget functionality."""
    
    def test_widget_creation(self):
        """Test creating a dashboard widget."""
        widget = DashboardWidget(
            id="test_widget",
            title="Test KPI Widget",
            widget_type=WidgetType.KPI,
            config={
                "metric": "error_rate",
                "format": "percentage",
                "threshold": 0.05
            }
        )
        
        assert widget.id == "test_widget"
        assert widget.widget_type == WidgetType.KPI
        assert widget.config["metric"] == "error_rate"
    
    def test_widget_validation(self):
        """Test widget configuration validation."""
        # Valid KPI widget
        kpi_widget = DashboardWidget(
            id="kpi_widget",
            title="KPI Widget",
            widget_type=WidgetType.KPI,
            config={"metric": "test_metric"}
        )
        assert kpi_widget.is_valid()
        
        # Valid chart widget
        chart_widget = DashboardWidget(
            id="chart_widget",
            title="Chart Widget",
            widget_type=WidgetType.CHART,
            config={"metrics": ["metric1", "metric2"], "chart_type": "line"}
        )
        assert chart_widget.is_valid()
        
        # Invalid widget (missing required config)
        invalid_widget = DashboardWidget(
            id="invalid_widget",
            title="Invalid Widget",
            widget_type=WidgetType.KPI,
            config={}
        )
        assert not invalid_widget.is_valid()


class TestKPIMetric:
    """Test KPI metric functionality."""
    
    def test_kpi_metric_creation(self):
        """Test creating a KPI metric."""
        kpi = KPIMetric(
            name="Error Rate",
            value="2.5%",
            trend_direction="down",
            trend_percentage=-15.5,
            status="good"
        )
        
        assert kpi.name == "Error Rate"
        assert kpi.value == "2.5%"
        assert kpi.trend_direction == "down"
        assert kpi.trend_percentage == -15.5
        assert kpi.status == "good"
    
    def test_kpi_status_determination(self):
        """Test KPI status determination."""
        # Good status (low error rate, decreasing)
        good_kpi = KPIMetric(
            name="Error Rate",
            value="1.0%",
            trend_direction="down",
            trend_percentage=-10.0
        )
        good_kpi.determine_status(threshold=0.05, lower_is_better=True)
        assert good_kpi.status == "good"
        
        # Warning status (approaching threshold)
        warning_kpi = KPIMetric(
            name="Error Rate", 
            value="4.5%",
            trend_direction="up",
            trend_percentage=20.0
        )
        warning_kpi.determine_status(threshold=0.05, lower_is_better=True)
        assert warning_kpi.status == "warning"
        
        # Critical status (above threshold)
        critical_kpi = KPIMetric(
            name="Error Rate",
            value="8.0%", 
            trend_direction="up",
            trend_percentage=50.0
        )
        critical_kpi.determine_status(threshold=0.05, lower_is_better=True)
        assert critical_kpi.status == "critical"


class TestChartData:
    """Test chart data functionality."""
    
    def test_chart_data_creation(self):
        """Test creating chart data."""
        chart = ChartData(
            labels=["Jan", "Feb", "Mar"],
            datasets=[
                {
                    "label": "Clicks",
                    "data": [100, 150, 200],
                    "borderColor": "blue"
                }
            ]
        )
        
        assert len(chart.labels) == 3
        assert len(chart.datasets) == 1
        assert chart.datasets[0]["label"] == "Clicks"
    
    def test_chart_data_validation(self):
        """Test chart data validation."""
        # Valid chart data
        valid_chart = ChartData(
            labels=["A", "B", "C"],
            datasets=[{"label": "Test", "data": [1, 2, 3]}]
        )
        assert valid_chart.is_valid()
        
        # Invalid chart data (mismatched lengths)
        invalid_chart = ChartData(
            labels=["A", "B"],  # 2 labels
            datasets=[{"label": "Test", "data": [1, 2, 3]}]  # 3 data points
        )
        assert not invalid_chart.is_valid()


class TestSystemStatus:
    """Test system status functionality."""
    
    def test_system_status_creation(self):
        """Test creating system status."""
        status = SystemStatus(
            overall_health="healthy",
            services_up=5,
            services_down=0,
            last_updated=datetime.now(timezone.utc)
        )
        
        assert status.overall_health == "healthy"
        assert status.services_up == 5
        assert status.services_down == 0
        assert status.is_healthy()
    
    def test_system_status_health_check(self):
        """Test system health determination."""
        # Healthy system
        healthy_status = SystemStatus(
            overall_health="healthy",
            services_up=10,
            services_down=0
        )
        assert healthy_status.is_healthy()
        assert healthy_status.get_health_percentage() == 100.0
        
        # Degraded system
        degraded_status = SystemStatus(
            overall_health="degraded",
            services_up=8,
            services_down=2
        )
        assert not degraded_status.is_healthy()
        assert degraded_status.get_health_percentage() == 80.0
        
        # Critical system
        critical_status = SystemStatus(
            overall_health="critical",
            services_up=3,
            services_down=7
        )
        assert not critical_status.is_healthy()
        assert critical_status.get_health_percentage() == 30.0


if __name__ == "__main__":
    pytest.main([__file__])