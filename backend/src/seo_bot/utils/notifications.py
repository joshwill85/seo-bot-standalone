"""Notification formatting and template utilities."""

import logging
import re
from datetime import datetime
from typing import Dict, List, Optional, Union, Any
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class NotificationChannel(Enum):
    """Notification delivery channels."""
    EMAIL = "email"
    SLACK = "slack"
    WEBHOOK = "webhook"
    SMS = "sms"


class NotificationPriority(Enum):
    """Notification priority levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class NotificationContext:
    """Context data for notification formatting."""
    alert_title: str
    alert_description: str
    severity: str
    metric_name: Optional[str] = None
    metric_value: Optional[Union[str, float]] = None
    threshold_value: Optional[Union[str, float]] = None
    affected_url: Optional[str] = None
    project_name: Optional[str] = None
    domain: Optional[str] = None
    timestamp: Optional[datetime] = None
    dashboard_url: Optional[str] = None
    additional_data: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.additional_data is None:
            self.additional_data = {}


class MessageTemplate:
    """Template for formatting notification messages."""
    
    def __init__(self, 
                 template_id: str,
                 channel: NotificationChannel,
                 subject_template: str,
                 body_template: str,
                 format_type: str = "plain"):
        """Initialize message template.
        
        Args:
            template_id: Unique identifier for the template
            channel: Target notification channel
            subject_template: Template for subject/title
            body_template: Template for message body
            format_type: Format type (plain, html, markdown)
        """
        self.template_id = template_id
        self.channel = channel
        self.subject_template = subject_template
        self.body_template = body_template
        self.format_type = format_type
    
    def format_message(self, context: NotificationContext) -> Dict[str, str]:
        """Format message using the template and context."""
        
        # Prepare template variables
        template_vars = self._extract_template_variables(context)
        
        # Format subject and body
        try:
            formatted_subject = self.subject_template.format(**template_vars)
            formatted_body = self.body_template.format(**template_vars)
        except KeyError as e:
            logger.error(f"Template formatting error: Missing variable {e}")
            # Fallback to basic formatting
            formatted_subject = f"Alert: {context.alert_title}"
            formatted_body = f"{context.alert_title}\n\n{context.alert_description}"
        
        return {
            "subject": formatted_subject,
            "body": formatted_body,
            "format": self.format_type
        }
    
    def _extract_template_variables(self, context: NotificationContext) -> Dict[str, str]:
        """Extract and format template variables from context."""
        
        # Format timestamp
        timestamp_str = context.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC") if context.timestamp else "Unknown"
        
        # Format metric value
        metric_display = "N/A"
        if context.metric_value is not None:
            if isinstance(context.metric_value, float):
                if context.metric_name and "rate" in context.metric_name.lower():
                    metric_display = f"{context.metric_value:.1%}"
                else:
                    metric_display = f"{context.metric_value:.2f}"
            else:
                metric_display = str(context.metric_value)
        
        # Format threshold value
        threshold_display = "N/A"
        if context.threshold_value is not None:
            if isinstance(context.threshold_value, float):
                if context.metric_name and "rate" in context.metric_name.lower():
                    threshold_display = f"{context.threshold_value:.1%}"
                else:
                    threshold_display = f"{context.threshold_value:.2f}"
            else:
                threshold_display = str(context.threshold_value)
        
        # Severity emoji mapping
        severity_emojis = {
            "low": "ℹ️",
            "medium": "⚠️", 
            "high": "🚨",
            "critical": "🔥"
        }
        
        severity_emoji = severity_emojis.get(context.severity.lower(), "⚠️")
        
        template_vars = {
            "alert_title": context.alert_title,
            "alert_description": context.alert_description,
            "severity": context.severity.upper(),
            "severity_emoji": severity_emoji,
            "metric_name": context.metric_name or "N/A",
            "metric_value": metric_display,
            "threshold_value": threshold_display,
            "affected_url": context.affected_url or "N/A",
            "project_name": context.project_name or "Unknown Project",
            "domain": context.domain or "N/A",
            "timestamp": timestamp_str,
            "dashboard_url": context.dashboard_url or "#",
            "date": context.timestamp.strftime("%Y-%m-%d") if context.timestamp else "Unknown",
            "time": context.timestamp.strftime("%H:%M:%S") if context.timestamp else "Unknown"
        }
        
        # Add additional data
        if context.additional_data:
            for key, value in context.additional_data.items():
                template_vars[f"extra_{key}"] = str(value)
        
        return template_vars


class NotificationFormatter:
    """Formats notifications for different channels and priorities."""
    
    def __init__(self):
        """Initialize notification formatter with default templates."""
        self.templates = {}
        self._setup_default_templates()
    
    def _setup_default_templates(self):
        """Set up default notification templates."""
        
        # Email templates
        self.templates["email_alert"] = MessageTemplate(
            template_id="email_alert",
            channel=NotificationChannel.EMAIL,
            subject_template="{severity_emoji} SEO Alert: {alert_title}",
            body_template="""
<h2>{severity_emoji} SEO Monitoring Alert</h2>

<p><strong>Alert:</strong> {alert_title}</p>
<p><strong>Severity:</strong> {severity}</p>
<p><strong>Project:</strong> {project_name}</p>
<p><strong>Domain:</strong> {domain}</p>
<p><strong>Time:</strong> {timestamp}</p>

<h3>Details</h3>
<p>{alert_description}</p>

<p><strong>Metric:</strong> {metric_name}</p>
<p><strong>Current Value:</strong> {metric_value}</p>
<p><strong>Threshold:</strong> {threshold_value}</p>
<p><strong>Affected URL:</strong> {affected_url}</p>

<h3>Next Steps</h3>
<p>1. Review the issue in the <a href="{dashboard_url}">monitoring dashboard</a></p>
<p>2. Investigate the root cause</p>
<p>3. Take corrective action as needed</p>
<p>4. Monitor for resolution</p>

<p><em>This alert was generated automatically by SEO Bot monitoring system.</em></p>
            """,
            format_type="html"
        )
        
        # Slack templates
        self.templates["slack_alert"] = MessageTemplate(
            template_id="slack_alert",
            channel=NotificationChannel.SLACK,
            subject_template="SEO Alert",
            body_template="""{severity_emoji} *SEO Alert: {alert_title}*

*Severity:* {severity}
*Project:* {project_name}
*Domain:* {domain}
*Time:* {timestamp}

*Details:*
{alert_description}

*Metric:* {metric_name} = {metric_value} (threshold: {threshold_value})
*URL:* {affected_url}

<{dashboard_url}|View Dashboard> | <{dashboard_url}|Acknowledge Alert>""",
            format_type="markdown"
        )
        
        # SMS templates
        self.templates["sms_alert"] = MessageTemplate(
            template_id="sms_alert",
            channel=NotificationChannel.SMS,
            subject_template="SEO Alert",
            body_template="SEO Alert: {alert_title} - {severity} severity for {domain}. {metric_name}: {metric_value}. Check dashboard: {dashboard_url}",
            format_type="plain"
        )
        
        # Webhook templates
        self.templates["webhook_alert"] = MessageTemplate(
            template_id="webhook_alert",
            channel=NotificationChannel.WEBHOOK,
            subject_template="SEO Alert",
            body_template="""{{
    "alert_type": "seo_monitoring",
    "title": "{alert_title}",
    "description": "{alert_description}",
    "severity": "{severity}",
    "project": "{project_name}",
    "domain": "{domain}",
    "metric": {{
        "name": "{metric_name}",
        "value": "{metric_value}",
        "threshold": "{threshold_value}"
    }},
    "affected_url": "{affected_url}",
    "timestamp": "{timestamp}",
    "dashboard_url": "{dashboard_url}"
}}""",
            format_type="json"
        )
    
    def format_alert_notification(self, 
                                  context: NotificationContext,
                                  channel: NotificationChannel,
                                  template_id: Optional[str] = None) -> Dict[str, str]:
        """Format an alert notification for the specified channel."""
        
        # Determine template to use
        if template_id and template_id in self.templates:
            template = self.templates[template_id]
        else:
            # Use default template for channel
            default_templates = {
                NotificationChannel.EMAIL: "email_alert",
                NotificationChannel.SLACK: "slack_alert", 
                NotificationChannel.SMS: "sms_alert",
                NotificationChannel.WEBHOOK: "webhook_alert"
            }
            template_key = default_templates.get(channel, "email_alert")
            template = self.templates[template_key]
        
        return template.format_message(context)
    
    def format_report_notification(self,
                                   report_type: str,
                                   report_data: Dict[str, Any],
                                   channel: NotificationChannel) -> Dict[str, str]:
        """Format a report notification."""
        
        # Create context for report
        context = NotificationContext(
            alert_title=f"{report_type.title()} Report Available",
            alert_description=f"Your {report_type} report has been generated and is ready for review.",
            severity="medium",
            project_name=report_data.get("project", "Unknown"),
            domain=report_data.get("domain", "N/A"),
            additional_data=report_data
        )
        
        if channel == NotificationChannel.EMAIL:
            template = MessageTemplate(
                template_id="email_report",
                channel=NotificationChannel.EMAIL,
                subject_template="📊 {report_type} Report Ready - {project_name}",
                body_template="""
<h2>📊 {report_type} Report</h2>

<p>Your {report_type} report for <strong>{project_name}</strong> has been generated.</p>

<h3>Report Summary</h3>
<p><strong>Domain:</strong> {domain}</p>
<p><strong>Generated:</strong> {timestamp}</p>
<p><strong>Report Type:</strong> {report_type}</p>

<p>Please review the attached report or access it through the <a href="{dashboard_url}">monitoring dashboard</a>.</p>

<p><em>This report was generated automatically by SEO Bot.</em></p>
                """,
                format_type="html"
            )
        else:
            # Use default alert template for other channels
            template = self.templates.get(f"{channel.value}_alert", self.templates["email_alert"])
        
        # Update context with report-specific data
        context.alert_title = template.subject_template.format(
            report_type=report_type.title(),
            project_name=context.project_name
        )
        
        return template.format_message(context)
    
    def add_custom_template(self, template: MessageTemplate):
        """Add a custom notification template."""
        self.templates[template.template_id] = template
    
    def get_template(self, template_id: str) -> Optional[MessageTemplate]:
        """Get a template by ID."""
        return self.templates.get(template_id)
    
    def list_templates(self, channel: Optional[NotificationChannel] = None) -> List[str]:
        """List available templates, optionally filtered by channel."""
        if channel:
            return [
                template_id for template_id, template in self.templates.items()
                if template.channel == channel
            ]
        else:
            return list(self.templates.keys())
    
    def format_system_status(self,
                             status: Dict[str, Any],
                             channel: NotificationChannel) -> Dict[str, str]:
        """Format system status notification."""
        
        overall_status = status.get("overall_status", "unknown")
        error_count = len(status.get("errors", []))
        warning_count = len(status.get("warnings", []))
        
        if overall_status == "healthy":
            severity = "low"
            title = "System Status: All Systems Operational"
            description = "All monitoring systems are functioning normally."
        elif overall_status == "warning":
            severity = "medium"
            title = f"System Status: {warning_count} Warning(s) Detected"
            description = f"System is operational but {warning_count} warning(s) require attention."
        else:
            severity = "high"
            title = f"System Status: {error_count} Error(s) Detected"
            description = f"System issues detected: {error_count} error(s), {warning_count} warning(s)."
        
        context = NotificationContext(
            alert_title=title,
            alert_description=description,
            severity=severity,
            additional_data={
                "error_count": error_count,
                "warning_count": warning_count,
                "overall_status": overall_status
            }
        )
        
        return self.format_alert_notification(context, channel)
    
    def format_performance_summary(self,
                                   metrics: Dict[str, float],
                                   channel: NotificationChannel) -> Dict[str, str]:
        """Format performance summary notification."""
        
        # Determine overall performance status
        performance_score = metrics.get("overall_score", 0)
        
        if performance_score >= 90:
            status = "excellent"
            severity = "low"
        elif performance_score >= 75:
            status = "good"
            severity = "low"
        elif performance_score >= 50:
            status = "needs improvement"
            severity = "medium"
        else:
            status = "poor"
            severity = "high"
        
        context = NotificationContext(
            alert_title=f"Performance Summary: {status.title()}",
            alert_description=f"Overall performance score: {performance_score:.1f}/100",
            severity=severity,
            metric_name="performance_score",
            metric_value=performance_score,
            additional_data=metrics
        )
        
        return self.format_alert_notification(context, channel)


def create_notification_context(alert_data: Dict[str, Any]) -> NotificationContext:
    """Create notification context from alert data."""
    
    return NotificationContext(
        alert_title=alert_data.get("title", "Unknown Alert"),
        alert_description=alert_data.get("description", "No description available"),
        severity=alert_data.get("severity", "medium"),
        metric_name=alert_data.get("metric_name"),
        metric_value=alert_data.get("metric_value"),
        threshold_value=alert_data.get("threshold_value"),
        affected_url=alert_data.get("affected_url"),
        project_name=alert_data.get("project_name"),
        domain=alert_data.get("domain"),
        timestamp=alert_data.get("timestamp"),
        dashboard_url=alert_data.get("dashboard_url"),
        additional_data=alert_data.get("additional_data", {})
    )


def format_metric_value(value: Union[str, int, float], 
                        metric_type: str = "number",
                        precision: int = 2) -> str:
    """Format metric value for display."""
    
    if value is None:
        return "N/A"
    
    try:
        if metric_type == "percentage":
            return f"{float(value):.{precision}%}"
        elif metric_type == "currency":
            return f"${float(value):.{precision}f}"
        elif metric_type == "duration_ms":
            return f"{int(value)}ms"
        elif metric_type == "duration_s":
            return f"{float(value):.{precision}f}s"
        elif metric_type == "bytes":
            # Convert bytes to human readable format
            bytes_val = int(value)
            for unit in ['B', 'KB', 'MB', 'GB']:
                if bytes_val < 1024:
                    return f"{bytes_val:.{precision}f}{unit}"
                bytes_val /= 1024
            return f"{bytes_val:.{precision}f}TB"
        else:
            # Default number formatting
            if isinstance(value, float):
                return f"{value:.{precision}f}"
            else:
                return str(value)
    except (ValueError, TypeError):
        return str(value)