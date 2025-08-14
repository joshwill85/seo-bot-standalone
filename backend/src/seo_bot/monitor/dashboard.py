"""Real-Time Monitoring Dashboard.

Provides live performance metrics visualization, SEO KPI tracking,
system health monitoring, and historical trend analysis.
"""

import asyncio
import logging
import json
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple, Union, Any
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path

import numpy as np
import pandas as pd
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

from ..config import Settings, MonitoringConfig
from ..models import AlertSeverity
from .coverage import CoverageFreshnessMonitor, CoverageSLAReport
from .alerts import AlertManager, Alert


logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Types of metrics tracked."""
    TRAFFIC = "traffic"
    RANKINGS = "rankings"
    CONVERSIONS = "conversions"
    TECHNICAL = "technical"
    CONTENT = "content"
    ALERTS = "alerts"


class TimeRange(Enum):
    """Time ranges for metrics."""
    LAST_HOUR = "1h"
    LAST_DAY = "24h"
    LAST_WEEK = "7d"
    LAST_MONTH = "30d"
    LAST_QUARTER = "90d"


@dataclass
class MetricData:
    """Individual metric data point."""
    timestamp: datetime
    value: float
    metric_name: str
    metric_type: MetricType
    dimensions: Dict[str, str] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        data['metric_type'] = self.metric_type.value
        return data


@dataclass
class KPIWidget:
    """Dashboard KPI widget configuration."""
    id: str
    title: str
    metric_type: MetricType
    current_value: float
    previous_value: float
    change_percentage: float
    trend_direction: str  # up, down, stable
    format_type: str  # number, percentage, currency, duration
    threshold_warning: Optional[float] = None
    threshold_critical: Optional[float] = None


@dataclass
class ChartData:
    """Chart data for dashboard visualization."""
    chart_id: str
    chart_type: str  # line, bar, pie, gauge
    title: str
    data_points: List[MetricData]
    time_range: TimeRange
    update_frequency: int  # seconds


@dataclass
class DashboardState:
    """Current dashboard state."""
    project_id: str
    domain: str
    last_updated: datetime
    kpi_widgets: List[KPIWidget]
    charts: List[ChartData]
    active_alerts: List[Alert]
    system_health: Dict[str, Any]
    uptime_percentage: float


class MetricsCollector:
    """Collects metrics from various sources."""
    
    def __init__(self, settings: Settings):
        """Initialize metrics collector."""
        self.settings = settings
        self.metrics_buffer = []
        self.max_buffer_size = 10000
        
    async def collect_traffic_metrics(self, project_id: str) -> List[MetricData]:
        """Collect traffic metrics from GSC."""
        metrics = []
        now = datetime.now(timezone.utc)
        
        try:
            # Simulate GSC data collection
            # In real implementation, would use GSC API
            base_traffic = 1000
            hourly_variation = np.random.normal(0, 0.1)
            
            current_traffic = base_traffic * (1 + hourly_variation)
            
            metrics.append(MetricData(
                timestamp=now,
                value=current_traffic,
                metric_name="organic_traffic",
                metric_type=MetricType.TRAFFIC,
                dimensions={"source": "gsc", "device": "all"}
            ))
            
            # CTR metric
            ctr = 0.05 + np.random.normal(0, 0.005)
            metrics.append(MetricData(
                timestamp=now,
                value=ctr,
                metric_name="organic_ctr",
                metric_type=MetricType.TRAFFIC,
                dimensions={"source": "gsc"}
            ))
            
            # Average position
            avg_position = 15 + np.random.normal(0, 2)
            metrics.append(MetricData(
                timestamp=now,
                value=avg_position,
                metric_name="average_position",
                metric_type=MetricType.RANKINGS,
                dimensions={"source": "gsc"}
            ))
            
        except Exception as e:
            logger.error(f"Failed to collect traffic metrics: {e}")
        
        return metrics
    
    async def collect_technical_metrics(self, domain: str) -> List[MetricData]:
        """Collect technical performance metrics."""
        metrics = []
        now = datetime.now(timezone.utc)
        
        try:
            # Simulate PageSpeed Insights data
            # In real implementation, would use PSI API
            
            # Core Web Vitals
            lcp = 2000 + np.random.normal(0, 200)  # LCP in ms
            inp = 150 + np.random.normal(0, 50)    # INP in ms
            cls = 0.1 + np.random.normal(0, 0.02)  # CLS
            
            metrics.extend([
                MetricData(now, lcp, "lcp", MetricType.TECHNICAL, {"device": "mobile"}),
                MetricData(now, inp, "inp", MetricType.TECHNICAL, {"device": "mobile"}),
                MetricData(now, cls, "cls", MetricType.TECHNICAL, {"device": "mobile"})
            ])
            
            # Performance score
            performance_score = 85 + np.random.normal(0, 5)
            metrics.append(MetricData(
                now, performance_score, "performance_score", 
                MetricType.TECHNICAL, {"device": "mobile"}
            ))
            
        except Exception as e:
            logger.error(f"Failed to collect technical metrics: {e}")
        
        return metrics
    
    async def collect_content_metrics(self, project_id: str) -> List[MetricData]:
        """Collect content-related metrics."""
        metrics = []
        now = datetime.now(timezone.utc)
        
        try:
            # Content velocity
            daily_content = 5 + np.random.poisson(2)
            metrics.append(MetricData(
                now, daily_content, "content_published_daily",
                MetricType.CONTENT, {"type": "all"}
            ))
            
            # Quality score average
            avg_quality = 7.5 + np.random.normal(0, 0.5)
            metrics.append(MetricData(
                now, avg_quality, "avg_content_quality",
                MetricType.CONTENT, {"period": "daily"}
            ))
            
            # Indexation rate
            indexation_rate = 0.85 + np.random.normal(0, 0.05)
            metrics.append(MetricData(
                now, indexation_rate, "indexation_rate",
                MetricType.CONTENT, {"source": "gsc"}
            ))
            
        except Exception as e:
            logger.error(f"Failed to collect content metrics: {e}")
        
        return metrics
    
    async def collect_all_metrics(self, project_id: str, domain: str) -> List[MetricData]:
        """Collect all metrics for a project."""
        all_metrics = []
        
        # Collect from all sources
        traffic_metrics = await self.collect_traffic_metrics(project_id)
        technical_metrics = await self.collect_technical_metrics(domain)
        content_metrics = await self.collect_content_metrics(project_id)
        
        all_metrics.extend(traffic_metrics)
        all_metrics.extend(technical_metrics)
        all_metrics.extend(content_metrics)
        
        # Buffer metrics
        self.metrics_buffer.extend(all_metrics)
        
        # Trim buffer if too large
        if len(self.metrics_buffer) > self.max_buffer_size:
            self.metrics_buffer = self.metrics_buffer[-self.max_buffer_size:]
        
        return all_metrics


class DashboardDataProcessor:
    """Processes metrics data for dashboard display."""
    
    def __init__(self):
        """Initialize data processor."""
        self.historical_data = {}
    
    def create_kpi_widgets(self, 
                           current_metrics: List[MetricData],
                           historical_metrics: List[MetricData]) -> List[KPIWidget]:
        """Create KPI widgets from metrics data."""
        widgets = []
        
        # Group current metrics by name
        current_by_name = {m.metric_name: m for m in current_metrics}
        
        # Group historical metrics (24h ago) by name
        historical_by_name = {}
        if historical_metrics:
            # Find metrics from 24h ago
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=24)
            historical_24h = [m for m in historical_metrics 
                            if abs((m.timestamp - cutoff_time).total_seconds()) < 3600]
            historical_by_name = {m.metric_name: m for m in historical_24h}
        
        # Create widgets for key metrics
        widget_configs = [
            ("organic_traffic", "Organic Traffic", "number"),
            ("organic_ctr", "Organic CTR", "percentage"),
            ("average_position", "Avg Position", "number"),
            ("performance_score", "Performance Score", "number"),
            ("avg_content_quality", "Content Quality", "number"),
            ("indexation_rate", "Indexation Rate", "percentage")
        ]
        
        for metric_name, title, format_type in widget_configs:
            current_metric = current_by_name.get(metric_name)
            historical_metric = historical_by_name.get(metric_name)
            
            if current_metric:
                current_value = current_metric.value
                previous_value = historical_metric.value if historical_metric else current_value
                
                # Calculate change percentage
                if previous_value != 0:
                    change_pct = ((current_value - previous_value) / previous_value) * 100
                else:
                    change_pct = 0
                
                # Determine trend direction
                if abs(change_pct) < 1:
                    trend = "stable"
                elif change_pct > 0:
                    trend = "up"
                else:
                    trend = "down"
                
                widgets.append(KPIWidget(
                    id=f"kpi_{metric_name}",
                    title=title,
                    metric_type=current_metric.metric_type,
                    current_value=current_value,
                    previous_value=previous_value,
                    change_percentage=change_pct,
                    trend_direction=trend,
                    format_type=format_type
                ))
        
        return widgets
    
    def create_chart_data(self, 
                          metrics: List[MetricData],
                          time_range: TimeRange) -> List[ChartData]:
        """Create chart data from metrics."""
        charts = []
        
        # Filter metrics by time range
        now = datetime.now(timezone.utc)
        if time_range == TimeRange.LAST_HOUR:
            cutoff = now - timedelta(hours=1)
        elif time_range == TimeRange.LAST_DAY:
            cutoff = now - timedelta(days=1)
        elif time_range == TimeRange.LAST_WEEK:
            cutoff = now - timedelta(days=7)
        elif time_range == TimeRange.LAST_MONTH:
            cutoff = now - timedelta(days=30)
        else:
            cutoff = now - timedelta(days=90)
        
        filtered_metrics = [m for m in metrics if m.timestamp >= cutoff]
        
        # Group by metric type
        by_type = {}
        for metric in filtered_metrics:
            metric_type = metric.metric_type
            if metric_type not in by_type:
                by_type[metric_type] = []
            by_type[metric_type].append(metric)
        
        # Create charts for each type
        chart_configs = [
            (MetricType.TRAFFIC, "Traffic Metrics", "line"),
            (MetricType.RANKINGS, "Rankings Metrics", "line"),
            (MetricType.TECHNICAL, "Technical Metrics", "line"),
            (MetricType.CONTENT, "Content Metrics", "bar")
        ]
        
        for metric_type, title, chart_type in chart_configs:
            if metric_type in by_type:
                charts.append(ChartData(
                    chart_id=f"chart_{metric_type.value}",
                    chart_type=chart_type,
                    title=title,
                    data_points=by_type[metric_type],
                    time_range=time_range,
                    update_frequency=30  # 30 seconds
                ))
        
        return charts
    
    def calculate_system_health(self, 
                                current_metrics: List[MetricData],
                                alerts: List[Alert]) -> Dict[str, Any]:
        """Calculate overall system health."""
        health = {
            "overall_score": 100,
            "status": "healthy",
            "issues": [],
            "components": {}
        }
        
        # Check technical performance
        technical_metrics = [m for m in current_metrics if m.metric_type == MetricType.TECHNICAL]
        tech_health = self._assess_technical_health(technical_metrics)
        health["components"]["technical"] = tech_health
        
        # Check content health
        content_metrics = [m for m in current_metrics if m.metric_type == MetricType.CONTENT]
        content_health = self._assess_content_health(content_metrics)
        health["components"]["content"] = content_health
        
        # Check traffic health
        traffic_metrics = [m for m in current_metrics if m.metric_type == MetricType.TRAFFIC]
        traffic_health = self._assess_traffic_health(traffic_metrics)
        health["components"]["traffic"] = traffic_health
        
        # Factor in active alerts
        alert_penalty = len([a for a in alerts if a.severity in [AlertSeverity.HIGH, AlertSeverity.CRITICAL]]) * 10
        
        # Calculate overall score
        component_scores = [health["components"][comp]["score"] for comp in health["components"]]
        avg_score = np.mean(component_scores) if component_scores else 100
        health["overall_score"] = max(0, avg_score - alert_penalty)
        
        # Determine status
        if health["overall_score"] >= 90:
            health["status"] = "healthy"
        elif health["overall_score"] >= 70:
            health["status"] = "warning"
        else:
            health["status"] = "critical"
        
        return health
    
    def _assess_technical_health(self, metrics: List[MetricData]) -> Dict[str, Any]:
        """Assess technical health from metrics."""
        health = {"score": 100, "issues": []}
        
        for metric in metrics:
            if metric.metric_name == "lcp" and metric.value > 2500:
                health["score"] -= 20
                health["issues"].append("LCP exceeds 2.5s threshold")
            elif metric.metric_name == "inp" and metric.value > 200:
                health["score"] -= 15
                health["issues"].append("INP exceeds 200ms threshold")
            elif metric.metric_name == "cls" and metric.value > 0.1:
                health["score"] -= 15
                health["issues"].append("CLS exceeds 0.1 threshold")
            elif metric.metric_name == "performance_score" and metric.value < 75:
                health["score"] -= 25
                health["issues"].append("Performance score below 75")
        
        return health
    
    def _assess_content_health(self, metrics: List[MetricData]) -> Dict[str, Any]:
        """Assess content health from metrics."""
        health = {"score": 100, "issues": []}
        
        for metric in metrics:
            if metric.metric_name == "avg_content_quality" and metric.value < 7.0:
                health["score"] -= 20
                health["issues"].append("Average content quality below 7.0")
            elif metric.metric_name == "indexation_rate" and metric.value < 0.8:
                health["score"] -= 25
                health["issues"].append("Indexation rate below 80%")
        
        return health
    
    def _assess_traffic_health(self, metrics: List[MetricData]) -> Dict[str, Any]:
        """Assess traffic health from metrics."""
        health = {"score": 100, "issues": []}
        
        for metric in metrics:
            if metric.metric_name == "organic_ctr" and metric.value < 0.02:
                health["score"] -= 15
                health["issues"].append("Organic CTR below 2%")
            elif metric.metric_name == "average_position" and metric.value > 20:
                health["score"] -= 20
                health["issues"].append("Average position worse than 20")
        
        return health


class DashboardWebSocketManager:
    """Manages WebSocket connections for real-time updates."""
    
    def __init__(self):
        """Initialize WebSocket manager."""
        self.active_connections: List[WebSocket] = []
        self.connection_metadata: Dict[WebSocket, Dict] = {}
    
    async def connect(self, websocket: WebSocket, project_id: str):
        """Accept a WebSocket connection."""
        await websocket.accept()
        self.active_connections.append(websocket)
        self.connection_metadata[websocket] = {
            "project_id": project_id,
            "connected_at": datetime.now(timezone.utc)
        }
        logger.info(f"WebSocket connected for project {project_id}")
    
    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            self.connection_metadata.pop(websocket, None)
            logger.info("WebSocket disconnected")
    
    async def broadcast_update(self, data: Dict, project_id: str = None):
        """Broadcast update to connected clients."""
        disconnected = []
        
        for connection in self.active_connections:
            try:
                # Filter by project if specified
                if project_id:
                    conn_project = self.connection_metadata.get(connection, {}).get("project_id")
                    if conn_project != project_id:
                        continue
                
                await connection.send_text(json.dumps(data, default=str))
            except WebSocketDisconnect:
                disconnected.append(connection)
            except Exception as e:
                logger.error(f"Error broadcasting to WebSocket: {e}")
                disconnected.append(connection)
        
        # Clean up disconnected clients
        for conn in disconnected:
            self.disconnect(conn)


class DashboardServer:
    """FastAPI server for the monitoring dashboard."""
    
    def __init__(self, 
                 settings: Settings,
                 monitoring_config: MonitoringConfig):
        """Initialize dashboard server."""
        self.settings = settings
        self.monitoring_config = monitoring_config
        self.app = FastAPI(title="SEO Bot Monitoring Dashboard")
        self.websocket_manager = DashboardWebSocketManager()
        self.metrics_collector = MetricsCollector(settings)
        self.data_processor = DashboardDataProcessor()
        
        # In-memory storage for demo (would use Redis/database in production)
        self.metrics_storage = []
        self.dashboard_cache = {}
        
        self._setup_routes()
        self._setup_static_files()
        
        # Background task for metrics collection
        self.update_task = None
    
    def _setup_routes(self):
        """Set up API routes."""
        
        @self.app.get("/")
        async def get_dashboard():
            """Serve the main dashboard HTML."""
            return HTMLResponse(self._get_dashboard_html())
        
        @self.app.get("/api/dashboard/{project_id}")
        async def get_dashboard_data(project_id: str, time_range: str = "24h"):
            """Get dashboard data for a project."""
            try:
                dashboard_state = await self._get_dashboard_state(project_id, TimeRange(time_range))
                return JSONResponse(dashboard_state)
            except Exception as e:
                logger.error(f"Error getting dashboard data: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/metrics/{project_id}")
        async def get_metrics(project_id: str, 
                              time_range: str = "24h",
                              metric_type: str = None):
            """Get metrics data for a project."""
            try:
                # Filter metrics
                filtered_metrics = [m for m in self.metrics_storage 
                                  if m.timestamp >= self._get_time_cutoff(TimeRange(time_range))]
                
                if metric_type:
                    filtered_metrics = [m for m in filtered_metrics 
                                      if m.metric_type == MetricType(metric_type)]
                
                return JSONResponse([m.to_dict() for m in filtered_metrics])
            except Exception as e:
                logger.error(f"Error getting metrics: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.websocket("/ws/{project_id}")
        async def websocket_endpoint(websocket: WebSocket, project_id: str):
            """WebSocket endpoint for real-time updates."""
            await self.websocket_manager.connect(websocket, project_id)
            try:
                while True:
                    # Keep connection alive
                    await websocket.receive_text()
            except WebSocketDisconnect:
                self.websocket_manager.disconnect(websocket)
    
    def _setup_static_files(self):
        """Set up static file serving."""
        # In a real implementation, would serve CSS/JS assets
        pass
    
    async def _get_dashboard_state(self, project_id: str, time_range: TimeRange) -> Dict:
        """Get current dashboard state."""
        # Get current metrics
        current_metrics = await self.metrics_collector.collect_all_metrics(project_id, "example.com")
        
        # Get historical metrics
        cutoff_time = self._get_time_cutoff(time_range)
        historical_metrics = [m for m in self.metrics_storage if m.timestamp >= cutoff_time]
        
        # Create KPI widgets
        kpi_widgets = self.data_processor.create_kpi_widgets(current_metrics, historical_metrics)
        
        # Create charts
        charts = self.data_processor.create_chart_data(historical_metrics, time_range)
        
        # Get active alerts (placeholder)
        active_alerts = []
        
        # Calculate system health
        system_health = self.data_processor.calculate_system_health(current_metrics, active_alerts)
        
        # Calculate uptime
        uptime_percentage = 99.9  # Would calculate from actual data
        
        dashboard_state = DashboardState(
            project_id=project_id,
            domain="example.com",
            last_updated=datetime.now(timezone.utc),
            kpi_widgets=kpi_widgets,
            charts=charts,
            active_alerts=active_alerts,
            system_health=system_health,
            uptime_percentage=uptime_percentage
        )
        
        return asdict(dashboard_state)
    
    def _get_time_cutoff(self, time_range: TimeRange) -> datetime:
        """Get time cutoff for the given range."""
        now = datetime.now(timezone.utc)
        if time_range == TimeRange.LAST_HOUR:
            return now - timedelta(hours=1)
        elif time_range == TimeRange.LAST_DAY:
            return now - timedelta(days=1)
        elif time_range == TimeRange.LAST_WEEK:
            return now - timedelta(days=7)
        elif time_range == TimeRange.LAST_MONTH:
            return now - timedelta(days=30)
        else:
            return now - timedelta(days=90)
    
    async def start_background_updates(self, project_id: str, domain: str):
        """Start background task for metrics collection and updates."""
        async def update_loop():
            while True:
                try:
                    # Collect new metrics
                    new_metrics = await self.metrics_collector.collect_all_metrics(project_id, domain)
                    self.metrics_storage.extend(new_metrics)
                    
                    # Trim old metrics (keep last 30 days)
                    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
                    self.metrics_storage = [m for m in self.metrics_storage if m.timestamp >= cutoff]
                    
                    # Get updated dashboard state
                    dashboard_state = await self._get_dashboard_state(project_id, TimeRange.LAST_DAY)
                    
                    # Broadcast update to connected clients
                    await self.websocket_manager.broadcast_update({
                        "type": "dashboard_update",
                        "data": dashboard_state
                    }, project_id)
                    
                    # Wait before next update
                    await asyncio.sleep(30)  # Update every 30 seconds
                    
                except Exception as e:
                    logger.error(f"Error in background update loop: {e}")
                    await asyncio.sleep(60)  # Wait longer if error
        
        self.update_task = asyncio.create_task(update_loop())
    
    def _get_dashboard_html(self) -> str:
        """Get the dashboard HTML template."""
        return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SEO Bot Monitoring Dashboard</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .dashboard {
            max-width: 1400px;
            margin: 0 auto;
        }
        .header {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        .kpi-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .kpi-widget {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .kpi-title {
            font-size: 14px;
            color: #666;
            margin-bottom: 10px;
        }
        .kpi-value {
            font-size: 32px;
            font-weight: bold;
            margin-bottom: 5px;
        }
        .kpi-change {
            font-size: 14px;
            display: flex;
            align-items: center;
        }
        .trend-up { color: #28a745; }
        .trend-down { color: #dc3545; }
        .trend-stable { color: #6c757d; }
        .charts-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .chart-widget {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            min-height: 300px;
        }
        .status-indicator {
            display: inline-block;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-right: 8px;
        }
        .status-healthy { background-color: #28a745; }
        .status-warning { background-color: #ffc107; }
        .status-critical { background-color: #dc3545; }
        .last-updated {
            color: #666;
            font-size: 14px;
            text-align: right;
        }
    </style>
</head>
<body>
    <div class="dashboard">
        <div class="header">
            <h1>SEO Bot Monitoring Dashboard</h1>
            <div class="last-updated" id="lastUpdated">Last updated: Loading...</div>
        </div>
        
        <div class="kpi-grid" id="kpiGrid">
            <!-- KPI widgets will be populated here -->
        </div>
        
        <div class="charts-grid" id="chartsGrid">
            <!-- Charts will be populated here -->
        </div>
        
        <div class="system-health" id="systemHealth">
            <!-- System health will be populated here -->
        </div>
    </div>

    <script>
        // WebSocket connection for real-time updates
        const projectId = 'demo-project';
        const ws = new WebSocket(`ws://localhost:8000/ws/${projectId}`);
        
        ws.onmessage = function(event) {
            const data = JSON.parse(event.data);
            if (data.type === 'dashboard_update') {
                updateDashboard(data.data);
            }
        };
        
        // Load initial dashboard data
        async function loadDashboard() {
            try {
                const response = await fetch(`/api/dashboard/${projectId}`);
                const data = await response.json();
                updateDashboard(data);
            } catch (error) {
                console.error('Error loading dashboard:', error);
            }
        }
        
        function updateDashboard(dashboardState) {
            updateKPIs(dashboardState.kpi_widgets);
            updateCharts(dashboardState.charts);
            updateSystemHealth(dashboardState.system_health);
            document.getElementById('lastUpdated').textContent = 
                `Last updated: ${new Date(dashboardState.last_updated).toLocaleString()}`;
        }
        
        function updateKPIs(kpiWidgets) {
            const grid = document.getElementById('kpiGrid');
            grid.innerHTML = '';
            
            kpiWidgets.forEach(widget => {
                const div = document.createElement('div');
                div.className = 'kpi-widget';
                
                const trendClass = `trend-${widget.trend_direction}`;
                const trendSymbol = widget.trend_direction === 'up' ? '↗' : 
                                   widget.trend_direction === 'down' ? '↘' : '→';
                
                div.innerHTML = `
                    <div class="kpi-title">${widget.title}</div>
                    <div class="kpi-value">${formatValue(widget.current_value, widget.format_type)}</div>
                    <div class="kpi-change ${trendClass}">
                        ${trendSymbol} ${widget.change_percentage.toFixed(1)}%
                    </div>
                `;
                
                grid.appendChild(div);
            });
        }
        
        function updateCharts(charts) {
            const grid = document.getElementById('chartsGrid');
            grid.innerHTML = '';
            
            charts.forEach(chart => {
                const div = document.createElement('div');
                div.className = 'chart-widget';
                div.innerHTML = `
                    <h3>${chart.title}</h3>
                    <div>Chart visualization would go here (${chart.data_points.length} data points)</div>
                `;
                grid.appendChild(div);
            });
        }
        
        function updateSystemHealth(health) {
            const div = document.getElementById('systemHealth');
            const statusClass = `status-${health.status}`;
            
            div.innerHTML = `
                <div class="chart-widget">
                    <h3>System Health</h3>
                    <div>
                        <span class="status-indicator ${statusClass}"></span>
                        ${health.status.toUpperCase()} (${health.overall_score.toFixed(1)}/100)
                    </div>
                    ${health.issues.length > 0 ? `
                        <ul>
                            ${health.issues.map(issue => `<li>${issue}</li>`).join('')}
                        </ul>
                    ` : ''}
                </div>
            `;
        }
        
        function formatValue(value, formatType) {
            switch (formatType) {
                case 'percentage':
                    return `${(value * 100).toFixed(1)}%`;
                case 'currency':
                    return `$${value.toFixed(2)}`;
                case 'duration':
                    return `${value.toFixed(0)}ms`;
                default:
                    return value.toFixed(1);
            }
        }
        
        // Load dashboard on page load
        loadDashboard();
        
        // Refresh every 30 seconds as fallback
        setInterval(loadDashboard, 30000);
    </script>
</body>
</html>
        """


async def launch_dashboard(project_id: str,
                           domain: str,
                           settings: Settings,
                           monitoring_config: MonitoringConfig,
                           port: int = 8000,
                           host: str = "127.0.0.1") -> DashboardServer:
    """Launch the monitoring dashboard server."""
    
    dashboard = DashboardServer(settings, monitoring_config)
    
    # Start background metrics collection
    await dashboard.start_background_updates(project_id, domain)
    
    logger.info(f"Starting dashboard server on http://{host}:{port}")
    
    # Run the server
    config = uvicorn.Config(
        app=dashboard.app,
        host=host,
        port=port,
        log_level="info"
    )
    server = uvicorn.Server(config)
    
    # Start server in background task
    asyncio.create_task(server.serve())
    
    return dashboard


def export_dashboard_config(output_path: Path) -> bool:
    """Export dashboard configuration template."""
    try:
        config = {
            "dashboard": {
                "title": "SEO Bot Monitoring Dashboard",
                "refresh_interval": 30,
                "widgets": [
                    {
                        "id": "organic_traffic",
                        "type": "kpi",
                        "title": "Organic Traffic",
                        "metric": "organic_traffic",
                        "format": "number"
                    },
                    {
                        "id": "traffic_chart",
                        "type": "line_chart",
                        "title": "Traffic Trends",
                        "metrics": ["organic_traffic", "organic_ctr"],
                        "time_range": "7d"
                    }
                ],
                "alerts": {
                    "enabled": True,
                    "sound_notifications": False,
                    "desktop_notifications": True
                }
            }
        }
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)
        
        logger.info(f"Dashboard configuration exported to {output_path}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to export dashboard configuration: {e}")
        return False