"""Unit tests for monitoring alerts system."""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, AsyncMock

from src.seo_bot.monitor.alerts import (
    AlertManager,
    NotificationDelivery,
    AnomalyDetector,
    Alert,
    AlertRule,
    AlertChannel,
    AlertStatus,
    AnomalyResult
)
from src.seo_bot.config import AlertingConfig, Settings
from src.seo_bot.models import AlertSeverity


@pytest.fixture
def alerting_config():
    """Create test alerting configuration."""
    return AlertingConfig(
        default_channels=['email', 'slack'],
        escalation_timeout_minutes=60,
        max_alerts_per_hour=10,
        anomaly_detection_enabled=True,
        anomaly_sensitivity=0.95
    )


@pytest.fixture
def settings():
    """Create test settings."""
    return Settings(
        smtp_host="smtp.example.com",
        smtp_port=587,
        smtp_user="test@example.com",
        smtp_password="password",
        slack_webhook_url="https://hooks.slack.com/test"
    )


@pytest.fixture
def sample_alert():
    """Create sample alert for testing."""
    return Alert(
        id="alert_123",
        title="High Error Rate Detected",
        description="Error rate has exceeded 5% threshold",
        severity=AlertSeverity.HIGH,
        metric_name="error_rate",
        metric_value=0.07,
        threshold_value=0.05,
        affected_url="https://example.com/page",
        triggered_at=datetime.now(timezone.utc),
        status=AlertStatus.ACTIVE,
        rule_id="rule_error_rate"
    )


@pytest.fixture
def sample_alert_rule():
    """Create sample alert rule for testing."""
    return AlertRule(
        id="rule_error_rate",
        name="Error Rate Monitor",
        metric_name="error_rate",
        condition="greater_than",
        threshold=0.05,
        window_minutes=15,
        severity=AlertSeverity.HIGH,
        channels=[AlertChannel.EMAIL, AlertChannel.SLACK],
        enabled=True
    )


@pytest.fixture
def sample_metrics_data():
    """Create sample metrics data for testing."""
    base_time = datetime.now(timezone.utc)
    data = []
    
    # Normal data points
    for i in range(20):
        timestamp = base_time - timedelta(minutes=i)
        value = 0.02 + (i % 3) * 0.005  # Normal range 0.02-0.03
        data.append((timestamp, value))
    
    # Add anomalous point
    data.append((base_time - timedelta(minutes=21), 0.15))  # Anomaly
    
    return sorted(data, key=lambda x: x[0])


class TestAlertManager:
    """Test alert manager functionality."""
    
    def test_manager_initialization(self, settings, alerting_config):
        """Test manager initialization."""
        manager = AlertManager(settings, alerting_config)
        
        assert manager.settings == settings
        assert manager.alerting_config == alerting_config
        assert isinstance(manager.notification_delivery, NotificationDelivery)
        assert isinstance(manager.anomaly_detector, AnomalyDetector)
    
    @pytest.mark.asyncio
    async def test_evaluate_alert_rules_trigger(self, settings, alerting_config, sample_alert_rule):
        """Test alert rule evaluation that triggers an alert."""
        manager = AlertManager(settings, alerting_config)
        
        # Mock metrics that exceed threshold
        with patch.object(manager, '_get_metric_value', new_callable=AsyncMock) as mock_metric:
            mock_metric.return_value = 0.07  # Above 0.05 threshold
            
            with patch.object(manager, '_send_alert', new_callable=AsyncMock) as mock_send:
                mock_send.return_value = True
                
                alerts = await manager.evaluate_alert_rules([sample_alert_rule])
                
                assert len(alerts) == 1
                assert alerts[0].severity == AlertSeverity.HIGH
                assert alerts[0].metric_value == 0.07
                mock_send.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_evaluate_alert_rules_no_trigger(self, settings, alerting_config, sample_alert_rule):
        """Test alert rule evaluation that doesn't trigger."""
        manager = AlertManager(settings, alerting_config)
        
        # Mock metrics below threshold
        with patch.object(manager, '_get_metric_value', new_callable=AsyncMock) as mock_metric:
            mock_metric.return_value = 0.03  # Below 0.05 threshold
            
            alerts = await manager.evaluate_alert_rules([sample_alert_rule])
            
            assert len(alerts) == 0
    
    @pytest.mark.asyncio
    async def test_process_anomaly_detection(self, settings, alerting_config, sample_metrics_data):
        """Test anomaly detection processing."""
        manager = AlertManager(settings, alerting_config)
        
        # Mock anomaly detection
        with patch.object(manager.anomaly_detector, 'detect_anomalies', new_callable=AsyncMock) as mock_detect:
            mock_detect.return_value = [
                AnomalyResult(
                    timestamp=sample_metrics_data[-1][0],
                    value=sample_metrics_data[-1][1],
                    expected_range=(0.02, 0.03),
                    anomaly_score=0.98,
                    severity=AlertSeverity.HIGH
                )
            ]
            
            with patch.object(manager, '_send_alert', new_callable=AsyncMock) as mock_send:
                mock_send.return_value = True
                
                anomalies = await manager.process_anomaly_detection(
                    "error_rate", sample_metrics_data
                )
                
                assert len(anomalies) == 1
                assert anomalies[0].anomaly_score == 0.98
                mock_send.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_acknowledge_alert(self, settings, alerting_config, sample_alert):
        """Test alert acknowledgment."""
        manager = AlertManager(settings, alerting_config)
        
        # Mock alert storage
        manager.active_alerts = {sample_alert.id: sample_alert}
        
        success = await manager.acknowledge_alert(sample_alert.id, "test_user")
        
        assert success
        assert manager.active_alerts[sample_alert.id].status == AlertStatus.ACKNOWLEDGED
        assert manager.active_alerts[sample_alert.id].acknowledged_by == "test_user"
    
    @pytest.mark.asyncio
    async def test_resolve_alert(self, settings, alerting_config, sample_alert):
        """Test alert resolution."""
        manager = AlertManager(settings, alerting_config)
        
        # Mock alert storage
        manager.active_alerts = {sample_alert.id: sample_alert}
        
        success = await manager.resolve_alert(sample_alert.id, "Manually resolved")
        
        assert success
        assert manager.active_alerts[sample_alert.id].status == AlertStatus.RESOLVED
        assert "Manually resolved" in manager.active_alerts[sample_alert.id].resolution_notes
    
    def test_check_rate_limits(self, settings, alerting_config):
        """Test alert rate limiting."""
        manager = AlertManager(settings, alerting_config)
        
        # Simulate reaching rate limit
        current_time = datetime.now(timezone.utc)
        for i in range(alerting_config.max_alerts_per_hour):
            manager.alert_timestamps.append(current_time - timedelta(minutes=i))
        
        # Should be rate limited
        assert not manager._check_rate_limits()
        
        # Clear old timestamps (simulate time passing)
        manager.alert_timestamps = [current_time - timedelta(minutes=120)]
        
        # Should not be rate limited
        assert manager._check_rate_limits()
    
    @pytest.mark.asyncio
    async def test_escalate_unacknowledged_alerts(self, settings, alerting_config, sample_alert):
        """Test escalation of unacknowledged alerts."""
        manager = AlertManager(settings, alerting_config)
        
        # Create old unacknowledged alert
        old_alert = sample_alert
        old_alert.triggered_at = datetime.now(timezone.utc) - timedelta(hours=2)
        old_alert.status = AlertStatus.ACTIVE
        
        manager.active_alerts = {old_alert.id: old_alert}
        
        with patch.object(manager, '_send_escalation_alert', new_callable=AsyncMock) as mock_escalate:
            mock_escalate.return_value = True
            
            escalated = await manager.escalate_unacknowledged_alerts()
            
            assert escalated == 1
            mock_escalate.assert_called_once()


class TestNotificationDelivery:
    """Test notification delivery functionality."""
    
    def test_delivery_initialization(self, settings):
        """Test notification delivery initialization."""
        delivery = NotificationDelivery(settings)
        
        assert delivery.settings == settings
    
    @pytest.mark.asyncio
    async def test_send_email_notification(self, settings, sample_alert):
        """Test email notification sending."""
        delivery = NotificationDelivery(settings)
        
        # Mock SMTP
        with patch('src.seo_bot.monitor.alerts.smtplib.SMTP') as mock_smtp:
            mock_server = Mock()
            mock_smtp.return_value.__enter__.return_value = mock_server
            
            success = await delivery.send_email_notification(
                "test@example.com", sample_alert
            )
            
            assert success
            mock_server.send_message.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_slack_notification(self, settings, sample_alert):
        """Test Slack notification sending."""
        delivery = NotificationDelivery(settings)
        
        # Mock HTTP request
        with patch('src.seo_bot.monitor.alerts.httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"ok": True}
            
            mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
            
            success = await delivery.send_slack_notification(sample_alert)
            
            assert success
    
    @pytest.mark.asyncio
    async def test_send_webhook_notification(self, settings, sample_alert):
        """Test webhook notification sending."""
        delivery = NotificationDelivery(settings)
        
        webhook_url = "https://example.com/webhook"
        
        # Mock HTTP request
        with patch('src.seo_bot.monitor.alerts.httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            
            mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
            
            success = await delivery.send_webhook_notification(webhook_url, sample_alert)
            
            assert success
    
    def test_format_alert_message(self, settings, sample_alert):
        """Test alert message formatting."""
        delivery = NotificationDelivery(settings)
        
        message = delivery._format_alert_message(sample_alert, "email")
        
        assert sample_alert.title in message["subject"]
        assert sample_alert.description in message["body"]
        assert str(sample_alert.metric_value) in message["body"]


class TestAnomalyDetector:
    """Test anomaly detection functionality."""
    
    def test_detector_initialization(self):
        """Test anomaly detector initialization."""
        detector = AnomalyDetector(sensitivity=0.95)
        
        assert detector.sensitivity == 0.95
    
    @pytest.mark.asyncio
    async def test_detect_anomalies_statistical(self, sample_metrics_data):
        """Test statistical anomaly detection."""
        detector = AnomalyDetector()
        
        anomalies = await detector.detect_anomalies(sample_metrics_data, method="statistical")
        
        # Should detect the anomalous point (0.15)
        assert len(anomalies) > 0
        assert any(abs(a.value - 0.15) < 0.01 for a in anomalies)
    
    @pytest.mark.asyncio
    async def test_detect_anomalies_iqr(self, sample_metrics_data):
        """Test IQR-based anomaly detection."""
        detector = AnomalyDetector()
        
        anomalies = await detector.detect_anomalies(sample_metrics_data, method="iqr")
        
        # Should detect outliers
        assert len(anomalies) > 0
    
    def test_calculate_z_score(self):
        """Test Z-score calculation."""
        detector = AnomalyDetector()
        
        values = [1, 2, 3, 4, 5, 100]  # 100 is an outlier
        z_scores = detector._calculate_z_scores(values)
        
        # Last value should have high Z-score
        assert abs(z_scores[-1]) > 2
    
    def test_calculate_iqr_bounds(self):
        """Test IQR bounds calculation."""
        detector = AnomalyDetector()
        
        values = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        lower, upper = detector._calculate_iqr_bounds(values)
        
        assert lower < upper
        assert lower < min(values)
        assert upper > max(values)
    
    def test_seasonal_decomposition(self):
        """Test seasonal pattern detection."""
        detector = AnomalyDetector()
        
        # Create data with seasonal pattern
        timestamps = [datetime.now(timezone.utc) - timedelta(hours=i) for i in range(24)]
        values = [10 + 5 * (i % 24 / 12) for i in range(24)]  # Daily pattern
        
        trend, seasonal, residual = detector._seasonal_decomposition(
            list(zip(timestamps, values))
        )
        
        assert len(trend) == len(values)
        assert len(seasonal) == len(values)
        assert len(residual) == len(values)


class TestAlert:
    """Test alert functionality."""
    
    def test_alert_creation(self, sample_alert):
        """Test creating an alert."""
        assert sample_alert.title == "High Error Rate Detected"
        assert sample_alert.severity == AlertSeverity.HIGH
        assert sample_alert.status == AlertStatus.ACTIVE
    
    def test_alert_serialization(self, sample_alert):
        """Test alert serialization."""
        alert_dict = sample_alert.to_dict()
        
        assert alert_dict["id"] == sample_alert.id
        assert alert_dict["title"] == sample_alert.title
        assert alert_dict["severity"] == "high"
        assert alert_dict["status"] == "active"
    
    def test_alert_acknowledgment(self, sample_alert):
        """Test alert acknowledgment."""
        sample_alert.acknowledge("test_user")
        
        assert sample_alert.status == AlertStatus.ACKNOWLEDGED
        assert sample_alert.acknowledged_by == "test_user"
        assert sample_alert.acknowledged_at is not None
    
    def test_alert_resolution(self, sample_alert):
        """Test alert resolution."""
        sample_alert.resolve("Issue fixed manually")
        
        assert sample_alert.status == AlertStatus.RESOLVED
        assert sample_alert.resolved_at is not None
        assert "Issue fixed manually" in sample_alert.resolution_notes


class TestAlertRule:
    """Test alert rule functionality."""
    
    def test_rule_creation(self, sample_alert_rule):
        """Test creating an alert rule."""
        assert sample_alert_rule.metric_name == "error_rate"
        assert sample_alert_rule.condition == "greater_than"
        assert sample_alert_rule.threshold == 0.05
        assert sample_alert_rule.enabled is True
    
    def test_rule_evaluation_trigger(self, sample_alert_rule):
        """Test rule evaluation that triggers."""
        # Value above threshold should trigger
        assert sample_alert_rule.evaluate(0.07)
        
        # Value at threshold should not trigger (greater_than)
        assert not sample_alert_rule.evaluate(0.05)
        
        # Value below threshold should not trigger
        assert not sample_alert_rule.evaluate(0.03)
    
    def test_rule_evaluation_conditions(self):
        """Test different rule conditions."""
        # Test less_than condition
        rule_lt = AlertRule(
            id="rule_lt",
            name="Less Than Test",
            metric_name="test_metric",
            condition="less_than",
            threshold=0.5,
            severity=AlertSeverity.MEDIUM
        )
        
        assert rule_lt.evaluate(0.3)  # Below threshold
        assert not rule_lt.evaluate(0.7)  # Above threshold
        
        # Test equals condition
        rule_eq = AlertRule(
            id="rule_eq",
            name="Equals Test",
            metric_name="test_metric",
            condition="equals",
            threshold=1.0,
            severity=AlertSeverity.LOW
        )
        
        assert rule_eq.evaluate(1.0)  # Equal to threshold
        assert not rule_eq.evaluate(1.1)  # Not equal


class TestAnomalyResult:
    """Test anomaly result functionality."""
    
    def test_anomaly_result_creation(self):
        """Test creating an anomaly result."""
        result = AnomalyResult(
            timestamp=datetime.now(timezone.utc),
            value=0.15,
            expected_range=(0.02, 0.03),
            anomaly_score=0.95,
            severity=AlertSeverity.HIGH
        )
        
        assert result.value == 0.15
        assert result.expected_range == (0.02, 0.03)
        assert result.anomaly_score == 0.95
        assert result.severity == AlertSeverity.HIGH
    
    def test_anomaly_result_deviation(self):
        """Test anomaly deviation calculation."""
        result = AnomalyResult(
            timestamp=datetime.now(timezone.utc),
            value=0.15,
            expected_range=(0.02, 0.03),
            anomaly_score=0.95,
            severity=AlertSeverity.HIGH
        )
        
        # Value is way above expected range
        deviation = result.calculate_deviation()
        assert deviation > 0.12  # 0.15 - 0.03


if __name__ == "__main__":
    pytest.main([__file__])