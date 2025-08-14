"""Unit tests for notification utilities."""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch

from src.seo_bot.utils.notifications import (
    NotificationFormatter,
    MessageTemplate,
    NotificationContext,
    NotificationChannel,
    NotificationPriority,
    create_notification_context,
    format_metric_value
)


@pytest.fixture
def sample_notification_context():
    """Create sample notification context."""
    return NotificationContext(
        alert_title="High Error Rate Detected",
        alert_description="The error rate has exceeded the acceptable threshold",
        severity="high",
        metric_name="error_rate",
        metric_value=0.07,
        threshold_value=0.05,
        affected_url="https://example.com/api",
        project_name="SEO Bot",
        domain="example.com",
        timestamp=datetime(2023, 1, 15, 10, 30, 0, tzinfo=timezone.utc),
        dashboard_url="https://dashboard.example.com",
        additional_data={"region": "us-east-1", "service": "api"}
    )


@pytest.fixture
def sample_alert_data():
    """Create sample alert data."""
    return {
        "title": "Performance Degradation",
        "description": "Page load times have increased significantly",
        "severity": "medium",
        "metric_name": "page_load_time",
        "metric_value": 3500,
        "threshold_value": 2000,
        "affected_url": "https://example.com/page",
        "project_name": "Test Project",
        "domain": "example.com",
        "timestamp": datetime.now(timezone.utc),
        "dashboard_url": "https://dashboard.test.com"
    }


class TestNotificationContext:
    """Test notification context functionality."""
    
    def test_context_creation(self, sample_notification_context):
        """Test creating notification context."""
        context = sample_notification_context
        
        assert context.alert_title == "High Error Rate Detected"
        assert context.severity == "high"
        assert context.metric_value == 0.07
        assert context.domain == "example.com"
        assert context.additional_data["region"] == "us-east-1"
    
    def test_context_default_timestamp(self):
        """Test context with default timestamp."""
        context = NotificationContext(
            alert_title="Test Alert",
            alert_description="Test description",
            severity="low"
        )
        
        assert context.timestamp is not None
        assert isinstance(context.timestamp, datetime)
        assert context.additional_data == {}
    
    def test_context_post_init(self):
        """Test context post-initialization."""
        context = NotificationContext(
            alert_title="Test Alert",
            alert_description="Test description", 
            severity="medium",
            timestamp=None,
            additional_data=None
        )
        
        # Should set defaults
        assert context.timestamp is not None
        assert context.additional_data == {}


class TestMessageTemplate:
    """Test message template functionality."""
    
    def test_template_creation(self):
        """Test creating a message template."""
        template = MessageTemplate(
            template_id="test_template",
            channel=NotificationChannel.EMAIL,
            subject_template="Alert: {alert_title}",
            body_template="Description: {alert_description}",
            format_type="plain"
        )
        
        assert template.template_id == "test_template"
        assert template.channel == NotificationChannel.EMAIL
        assert template.format_type == "plain"
    
    def test_format_message_basic(self, sample_notification_context):
        """Test basic message formatting."""
        template = MessageTemplate(
            template_id="test_template",
            channel=NotificationChannel.EMAIL,
            subject_template="Alert: {alert_title}",
            body_template="Severity: {severity}\nDescription: {alert_description}",
            format_type="plain"
        )
        
        result = template.format_message(sample_notification_context)
        
        assert result["subject"] == "Alert: High Error Rate Detected"
        assert "Severity: HIGH" in result["body"]
        assert "The error rate has exceeded" in result["body"]
        assert result["format"] == "plain"
    
    def test_format_message_with_metrics(self, sample_notification_context):
        """Test message formatting with metric data."""
        template = MessageTemplate(
            template_id="metric_template",
            channel=NotificationChannel.SLACK,
            subject_template="Metric Alert",
            body_template="Metric: {metric_name}\nValue: {metric_value}\nThreshold: {threshold_value}",
            format_type="markdown"
        )
        
        result = template.format_message(sample_notification_context)
        
        assert "Metric: error_rate" in result["body"]
        assert "Value: 7.0%" in result["body"]  # Should format as percentage
        assert "Threshold: 5.0%" in result["body"]
    
    def test_format_message_missing_variable(self):
        """Test message formatting with missing template variable."""
        template = MessageTemplate(
            template_id="bad_template",
            channel=NotificationChannel.EMAIL,
            subject_template="Alert: {nonexistent_field}",
            body_template="Description: {alert_description}",
            format_type="plain"
        )
        
        context = NotificationContext(
            alert_title="Test Alert",
            alert_description="Test description",
            severity="low"
        )
        
        result = template.format_message(context)
        
        # Should fallback to basic formatting
        assert "Alert: Test Alert" in result["subject"]
        assert "Test Alert" in result["body"]
        assert "Test description" in result["body"]
    
    def test_extract_template_variables_percentage_format(self, sample_notification_context):
        """Test template variable extraction with percentage formatting."""
        template = MessageTemplate(
            template_id="test_template",
            channel=NotificationChannel.EMAIL,
            subject_template="Test",
            body_template="Test",
            format_type="plain"
        )
        
        # Set metric name with "rate" to trigger percentage formatting
        sample_notification_context.metric_name = "error_rate"
        sample_notification_context.threshold_value = 0.05
        
        variables = template._extract_template_variables(sample_notification_context)
        
        assert variables["metric_value"] == "7.0%"
        assert variables["threshold_value"] == "5.0%"
    
    def test_extract_template_variables_severity_emoji(self, sample_notification_context):
        """Test severity emoji mapping."""
        template = MessageTemplate(
            template_id="test_template",
            channel=NotificationChannel.SLACK,
            subject_template="Test",
            body_template="Test",
            format_type="markdown"
        )
        
        variables = template._extract_template_variables(sample_notification_context)
        
        assert variables["severity_emoji"] == "🚨"  # High severity
        assert variables["severity"] == "HIGH"
    
    def test_extract_template_variables_additional_data(self, sample_notification_context):
        """Test additional data extraction."""
        template = MessageTemplate(
            template_id="test_template",
            channel=NotificationChannel.EMAIL,
            subject_template="Test",
            body_template="Test",
            format_type="plain"
        )
        
        variables = template._extract_template_variables(sample_notification_context)
        
        assert variables["extra_region"] == "us-east-1"
        assert variables["extra_service"] == "api"


class TestNotificationFormatter:
    """Test notification formatter functionality."""
    
    def test_formatter_initialization(self):
        """Test formatter initialization."""
        formatter = NotificationFormatter()
        
        assert len(formatter.templates) > 0
        assert "email_alert" in formatter.templates
        assert "slack_alert" in formatter.templates
        assert "sms_alert" in formatter.templates
        assert "webhook_alert" in formatter.templates
    
    def test_format_alert_notification_email(self, sample_notification_context):
        """Test formatting email alert notification."""
        formatter = NotificationFormatter()
        
        result = formatter.format_alert_notification(
            sample_notification_context,
            NotificationChannel.EMAIL
        )
        
        assert "🚨 SEO Alert: High Error Rate Detected" in result["subject"]
        assert "<h2>🚨 SEO Monitoring Alert</h2>" in result["body"]
        assert "error_rate" in result["body"]
        assert "7.0%" in result["body"]
        assert result["format"] == "html"
    
    def test_format_alert_notification_slack(self, sample_notification_context):
        """Test formatting Slack alert notification."""
        formatter = NotificationFormatter()
        
        result = formatter.format_alert_notification(
            sample_notification_context,
            NotificationChannel.SLACK
        )
        
        assert "🚨 *SEO Alert: High Error Rate Detected*" in result["body"]
        assert "*Severity:* HIGH" in result["body"]
        assert "*Domain:* example.com" in result["body"]
        assert result["format"] == "markdown"
    
    def test_format_alert_notification_sms(self, sample_notification_context):
        """Test formatting SMS alert notification."""
        formatter = NotificationFormatter()
        
        result = formatter.format_alert_notification(
            sample_notification_context,
            NotificationChannel.SMS
        )
        
        assert "SEO Alert: High Error Rate Detected" in result["body"]
        assert "high severity" in result["body"]
        assert "example.com" in result["body"]
        assert result["format"] == "plain"
    
    def test_format_alert_notification_webhook(self, sample_notification_context):
        """Test formatting webhook alert notification."""
        formatter = NotificationFormatter()
        
        result = formatter.format_alert_notification(
            sample_notification_context,
            NotificationChannel.WEBHOOK
        )
        
        # Should be JSON format
        assert '"alert_type": "seo_monitoring"' in result["body"]
        assert '"title": "High Error Rate Detected"' in result["body"]
        assert '"severity": "HIGH"' in result["body"]
        assert result["format"] == "json"
    
    def test_format_alert_notification_custom_template(self, sample_notification_context):
        """Test formatting with custom template."""
        formatter = NotificationFormatter()
        
        custom_template = MessageTemplate(
            template_id="custom_alert",
            channel=NotificationChannel.EMAIL,
            subject_template="Custom: {alert_title}",
            body_template="Custom body: {alert_description}",
            format_type="plain"
        )
        
        formatter.add_custom_template(custom_template)
        
        result = formatter.format_alert_notification(
            sample_notification_context,
            NotificationChannel.EMAIL,
            template_id="custom_alert"
        )
        
        assert result["subject"] == "Custom: High Error Rate Detected"
        assert "Custom body:" in result["body"]
    
    def test_format_report_notification(self):
        """Test formatting report notification."""
        formatter = NotificationFormatter()
        
        report_data = {
            "project": "SEO Bot",
            "domain": "example.com",
            "total_pages": 1000,
            "issues_found": 5
        }
        
        result = formatter.format_report_notification(
            "coverage",
            report_data,
            NotificationChannel.EMAIL
        )
        
        assert "📊" in result["subject"]
        assert "Coverage Report Ready" in result["subject"]
        assert "SEO Bot" in result["body"]
        assert "example.com" in result["body"]
    
    def test_format_system_status_healthy(self):
        """Test formatting healthy system status."""
        formatter = NotificationFormatter()
        
        status = {
            "overall_status": "healthy",
            "errors": [],
            "warnings": []
        }
        
        result = formatter.format_system_status(status, NotificationChannel.SLACK)
        
        assert "All Systems Operational" in result["body"]
        assert "functioning normally" in result["body"]
    
    def test_format_system_status_warnings(self):
        """Test formatting system status with warnings."""
        formatter = NotificationFormatter()
        
        status = {
            "overall_status": "warning",
            "errors": [],
            "warnings": ["High memory usage", "Slow response times"]
        }
        
        result = formatter.format_system_status(status, NotificationChannel.EMAIL)
        
        assert "2 Warning(s) Detected" in result["body"]
        assert "require attention" in result["body"]
    
    def test_format_system_status_errors(self):
        """Test formatting system status with errors."""
        formatter = NotificationFormatter()
        
        status = {
            "overall_status": "critical",
            "errors": ["Database connection failed", "API endpoint down"],
            "warnings": ["High CPU usage"]
        }
        
        result = formatter.format_system_status(status, NotificationChannel.SLACK)
        
        assert "2 Error(s) Detected" in result["body"]
        assert "System issues detected" in result["body"]
    
    def test_format_performance_summary_excellent(self):
        """Test formatting excellent performance summary."""
        formatter = NotificationFormatter()
        
        metrics = {
            "overall_score": 95.5,
            "lcp_score": 98,
            "cls_score": 92,
            "inp_score": 94
        }
        
        result = formatter.format_performance_summary(metrics, NotificationChannel.EMAIL)
        
        assert "Performance Summary: Excellent" in result["body"]
        assert "95.5/100" in result["body"]
    
    def test_format_performance_summary_poor(self):
        """Test formatting poor performance summary."""
        formatter = NotificationFormatter()
        
        metrics = {
            "overall_score": 35.0,
            "lcp_score": 40,
            "cls_score": 30,
            "inp_score": 35
        }
        
        result = formatter.format_performance_summary(metrics, NotificationChannel.SLACK)
        
        assert "Performance Summary: Poor" in result["body"]
        assert "35.0/100" in result["body"]
    
    def test_add_custom_template(self):
        """Test adding custom template."""
        formatter = NotificationFormatter()
        
        custom_template = MessageTemplate(
            template_id="custom_test",
            channel=NotificationChannel.SMS,
            subject_template="Custom Subject",
            body_template="Custom Body",
            format_type="plain"
        )
        
        formatter.add_custom_template(custom_template)
        
        assert "custom_test" in formatter.templates
        assert formatter.get_template("custom_test") == custom_template
    
    def test_list_templates(self):
        """Test listing templates."""
        formatter = NotificationFormatter()
        
        all_templates = formatter.list_templates()
        email_templates = formatter.list_templates(NotificationChannel.EMAIL)
        
        assert len(all_templates) >= 4
        assert len(email_templates) >= 1
        assert "email_alert" in email_templates


class TestUtilityFunctions:
    """Test utility functions."""
    
    def test_create_notification_context(self, sample_alert_data):
        """Test creating notification context from alert data."""
        context = create_notification_context(sample_alert_data)
        
        assert context.alert_title == "Performance Degradation"
        assert context.severity == "medium"
        assert context.metric_value == 3500
        assert context.project_name == "Test Project"
    
    def test_create_notification_context_minimal(self):
        """Test creating notification context with minimal data."""
        minimal_data = {
            "title": "Test Alert"
        }
        
        context = create_notification_context(minimal_data)
        
        assert context.alert_title == "Test Alert"
        assert context.alert_description == "No description available"
        assert context.severity == "medium"
    
    def test_format_metric_value_number(self):
        """Test formatting numeric metric values."""
        assert format_metric_value(123.456, "number", 2) == "123.46"
        assert format_metric_value(123, "number", 0) == "123"
    
    def test_format_metric_value_percentage(self):
        """Test formatting percentage metric values."""
        assert format_metric_value(0.1234, "percentage", 1) == "12.3%"
        assert format_metric_value(0.5, "percentage", 0) == "50%"
    
    def test_format_metric_value_currency(self):
        """Test formatting currency metric values."""
        assert format_metric_value(123.45, "currency", 2) == "$123.45"
        assert format_metric_value(1000, "currency", 0) == "$1000"
    
    def test_format_metric_value_duration(self):
        """Test formatting duration metric values."""
        assert format_metric_value(1500, "duration_ms") == "1500ms"
        assert format_metric_value(2.5, "duration_s", 1) == "2.5s"
    
    def test_format_metric_value_bytes(self):
        """Test formatting bytes metric values."""
        assert format_metric_value(1024, "bytes", 1) == "1.0KB"
        assert format_metric_value(1048576, "bytes", 1) == "1.0MB"
        assert format_metric_value(1073741824, "bytes", 1) == "1.0GB"
        assert format_metric_value(512, "bytes", 0) == "512B"
    
    def test_format_metric_value_invalid(self):
        """Test formatting invalid metric values."""
        assert format_metric_value(None, "number") == "N/A"
        assert format_metric_value("invalid", "number") == "invalid"
        assert format_metric_value(123, "unknown_type") == "123"


class TestNotificationEnums:
    """Test notification enum classes."""
    
    def test_notification_channel_enum(self):
        """Test notification channel enum."""
        assert NotificationChannel.EMAIL.value == "email"
        assert NotificationChannel.SLACK.value == "slack"
        assert NotificationChannel.WEBHOOK.value == "webhook"
        assert NotificationChannel.SMS.value == "sms"
    
    def test_notification_priority_enum(self):
        """Test notification priority enum."""
        assert NotificationPriority.LOW.value == "low"
        assert NotificationPriority.MEDIUM.value == "medium"
        assert NotificationPriority.HIGH.value == "high"
        assert NotificationPriority.URGENT.value == "urgent"


if __name__ == "__main__":
    pytest.main([__file__])