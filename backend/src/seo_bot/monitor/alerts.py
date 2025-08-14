"""Automated Alerting & Reporting System.

Provides multi-channel alerting with intelligent routing, escalation rules,
anomaly detection, and automated reporting capabilities.
"""

import asyncio
import logging
import json
import smtplib
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Set, Tuple, Union, Any
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import httpx
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import IsolationForest

from ..config import MonitoringConfig, Settings
from ..models import AlertSeverity


logger = logging.getLogger(__name__)


class AlertType(Enum):
    """Types of alerts."""
    PERFORMANCE_DEGRADATION = "performance_degradation"
    INDEXATION_ISSUE = "indexation_issue"
    TRAFFIC_ANOMALY = "traffic_anomaly"
    QUALITY_VIOLATION = "quality_violation"
    SYSTEM_ERROR = "system_error"
    SECURITY_ALERT = "security_alert"
    BUDGET_EXCEEDED = "budget_exceeded"
    SLA_BREACH = "sla_breach"


class AlertStatus(Enum):
    """Alert status values."""
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"


class AlertChannel(Enum):
    """Alert delivery channels."""
    EMAIL = "email"
    SLACK = "slack"
    WEBHOOK = "webhook"
    SMS = "sms"
    DASHBOARD = "dashboard"


@dataclass
class Alert:
    """Alert data structure."""
    id: str
    title: str
    description: str
    alert_type: AlertType
    severity: AlertSeverity
    status: AlertStatus
    
    # Context
    project_id: str
    source: str  # Which system generated the alert
    created_at: datetime
    last_updated: datetime
    
    # Optional context
    affected_url: Optional[str] = None
    metric_name: Optional[str] = None
    metric_value: Optional[float] = None
    threshold_value: Optional[float] = None
    
    # Timing
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    
    # Escalation
    escalation_level: int = 0
    escalated_at: Optional[datetime] = None
    assigned_to: Optional[str] = None
    
    # Context data
    context: Dict[str, Any] = None
    tags: List[str] = None
    
    def to_dict(self) -> Dict:
        """Convert alert to dictionary for serialization."""
        data = asdict(self)
        data['alert_type'] = self.alert_type.value
        data['severity'] = self.severity.value
        data['status'] = self.status.value
        data['created_at'] = self.created_at.isoformat()
        data['last_updated'] = self.last_updated.isoformat()
        if self.acknowledged_at:
            data['acknowledged_at'] = self.acknowledged_at.isoformat()
        if self.resolved_at:
            data['resolved_at'] = self.resolved_at.isoformat()
        if self.escalated_at:
            data['escalated_at'] = self.escalated_at.isoformat()
        return data


@dataclass
class AlertRule:
    """Alert rule configuration."""
    id: str
    name: str
    description: str
    alert_type: AlertType
    severity: AlertSeverity
    
    # Conditions
    metric_name: str
    condition: str  # gt, lt, eq, anomaly
    threshold_value: Optional[float] = None
    duration_minutes: int = 5  # How long condition must persist
    
    # Targeting
    project_ids: List[str] = None  # None = all projects
    tags: List[str] = None
    
    # Delivery
    channels: List[AlertChannel] = None
    suppress_during_maintenance: bool = True
    cooldown_minutes: int = 60  # Minimum time between same alerts
    
    # Escalation
    escalation_chain: List[str] = None  # List of email addresses
    escalation_delay_minutes: int = 30
    
    # Status
    enabled: bool = True
    last_triggered: Optional[datetime] = None


@dataclass
class NotificationTemplate:
    """Template for alert notifications."""
    template_id: str
    alert_type: AlertType
    channel: AlertChannel
    subject_template: str
    body_template: str
    
    # Channel-specific formatting
    slack_color: Optional[str] = None
    include_graphs: bool = False
    include_logs: bool = False


class AnomalyDetector:
    """Machine learning-based anomaly detection."""
    
    def __init__(self, sensitivity: float = 0.1):
        """Initialize anomaly detector.
        
        Args:
            sensitivity: Detection sensitivity (0.0-1.0, lower = more sensitive)
        """
        self.sensitivity = sensitivity
        self.models = {}
        self.scalers = {}
        self.historical_data = {}
        
    def train_model(self, metric_name: str, historical_values: List[float]):
        """Train anomaly detection model for a metric."""
        if len(historical_values) < 20:
            logger.warning(f"Insufficient data to train anomaly model for {metric_name}")
            return
        
        # Prepare data
        values = np.array(historical_values).reshape(-1, 1)
        
        # Scale data
        scaler = StandardScaler()
        scaled_values = scaler.fit_transform(values)
        
        # Train isolation forest
        model = IsolationForest(
            contamination=self.sensitivity,
            random_state=42,
            n_estimators=100
        )
        model.fit(scaled_values)
        
        # Store model and scaler
        self.models[metric_name] = model
        self.scalers[metric_name] = scaler
        self.historical_data[metric_name] = values.flatten()
        
        logger.info(f"Trained anomaly detection model for {metric_name}")
    
    def detect_anomaly(self, metric_name: str, value: float) -> Tuple[bool, float]:
        """Detect if a value is anomalous.
        
        Returns:
            Tuple of (is_anomaly, anomaly_score)
        """
        if metric_name not in self.models:
            return False, 0.0
        
        model = self.models[metric_name]
        scaler = self.scalers[metric_name]
        
        # Scale the value
        scaled_value = scaler.transform([[value]])
        
        # Get anomaly score
        anomaly_score = model.decision_function(scaled_value)[0]
        is_anomaly = model.predict(scaled_value)[0] == -1
        
        # Additional statistical checks
        if metric_name in self.historical_data:
            historical = self.historical_data[metric_name]
            mean = np.mean(historical)
            std = np.std(historical)
            
            # Z-score check (3 sigma rule)
            z_score = abs(value - mean) / std if std > 0 else 0
            if z_score > 3:
                is_anomaly = True
                anomaly_score = min(anomaly_score, -0.5)
        
        return is_anomaly, anomaly_score
    
    def update_historical_data(self, metric_name: str, value: float):
        """Update historical data with new value."""
        if metric_name in self.historical_data:
            # Keep last 1000 values
            data = list(self.historical_data[metric_name])
            data.append(value)
            if len(data) > 1000:
                data = data[-1000:]
            self.historical_data[metric_name] = np.array(data)


class NotificationDelivery:
    """Handles delivery of notifications across different channels."""
    
    def __init__(self, settings: Settings):
        """Initialize notification delivery."""
        self.settings = settings
    
    async def send_email(self, 
                         to_emails: List[str],
                         subject: str,
                         body: str,
                         is_html: bool = False) -> bool:
        """Send email notification."""
        try:
            if not self.settings.smtp_host or not self.settings.smtp_username:
                logger.warning("SMTP not configured - skipping email notification")
                return False
            
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.settings.smtp_username
            msg['To'] = ', '.join(to_emails)
            
            # Add body
            mime_type = 'html' if is_html else 'plain'
            msg.attach(MIMEText(body, mime_type))
            
            # Send email
            with smtplib.SMTP(self.settings.smtp_host, self.settings.smtp_port) as server:
                server.starttls()
                server.login(self.settings.smtp_username, self.settings.smtp_password)
                server.send_message(msg)
            
            logger.info(f"Email sent to {len(to_emails)} recipients")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False
    
    async def send_slack(self, 
                         webhook_url: str,
                         message: str,
                         color: str = "warning",
                         attachments: List[Dict] = None) -> bool:
        """Send Slack notification."""
        try:
            payload = {
                "text": message,
                "color": color,
                "username": "SEO Bot Monitor",
                "icon_emoji": ":warning:"
            }
            
            if attachments:
                payload["attachments"] = attachments
            
            async with httpx.AsyncClient() as client:
                response = await client.post(webhook_url, json=payload)
                response.raise_for_status()
            
            logger.info("Slack notification sent")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send Slack notification: {e}")
            return False
    
    async def send_webhook(self, 
                           webhook_url: str,
                           payload: Dict) -> bool:
        """Send webhook notification."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(webhook_url, json=payload, timeout=10.0)
                response.raise_for_status()
            
            logger.info(f"Webhook sent to {webhook_url}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send webhook: {e}")
            return False
    
    async def send_sms(self, 
                       phone_numbers: List[str],
                       message: str) -> bool:
        """Send SMS notification (placeholder - would integrate with SMS service)."""
        try:
            # Would integrate with Twilio, AWS SNS, etc.
            logger.info(f"SMS would be sent to {len(phone_numbers)} numbers: {message[:50]}...")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send SMS: {e}")
            return False


class AlertManager:
    """Manages alert lifecycle, routing, and delivery."""
    
    def __init__(self, 
                 settings: Settings,
                 monitoring_config: MonitoringConfig):
        """Initialize alert manager."""
        self.settings = settings
        self.monitoring_config = monitoring_config
        self.notification_delivery = NotificationDelivery(settings)
        self.anomaly_detector = AnomalyDetector()
        
        # Alert storage (would use database in production)
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_rules: Dict[str, AlertRule] = {}
        self.notification_templates: Dict[str, NotificationTemplate] = {}
        self.suppression_windows: List[Tuple[datetime, datetime]] = []
        
        # Metrics for rule evaluation
        self.metric_history: Dict[str, List[Tuple[datetime, float]]] = {}
        
        # Initialize default rules and templates
        self._setup_default_rules()
        self._setup_default_templates()
    
    def _setup_default_rules(self):
        """Set up default alert rules."""
        default_rules = [
            AlertRule(
                id="high_lcp",
                name="High LCP Alert",
                description="Largest Contentful Paint exceeds 2.5s",
                alert_type=AlertType.PERFORMANCE_DEGRADATION,
                severity=AlertSeverity.HIGH,
                metric_name="lcp",
                condition="gt",
                threshold_value=2500,
                duration_minutes=5,
                channels=[AlertChannel.EMAIL, AlertChannel.SLACK],
                escalation_delay_minutes=30
            ),
            AlertRule(
                id="low_indexation",
                name="Low Indexation Rate",
                description="Indexation rate below 80%",
                alert_type=AlertType.INDEXATION_ISSUE,
                severity=AlertSeverity.HIGH,
                metric_name="indexation_rate",
                condition="lt",
                threshold_value=0.8,
                duration_minutes=10,
                channels=[AlertChannel.EMAIL, AlertChannel.WEBHOOK]
            ),
            AlertRule(
                id="traffic_anomaly",
                name="Traffic Anomaly",
                description="Unusual traffic pattern detected",
                alert_type=AlertType.TRAFFIC_ANOMALY,
                severity=AlertSeverity.MEDIUM,
                metric_name="organic_traffic",
                condition="anomaly",
                channels=[AlertChannel.SLACK, AlertChannel.DASHBOARD]
            ),
            AlertRule(
                id="quality_violation",
                name="Content Quality Violation",
                description="Content quality below minimum threshold",
                alert_type=AlertType.QUALITY_VIOLATION,
                severity=AlertSeverity.MEDIUM,
                metric_name="avg_content_quality",
                condition="lt",
                threshold_value=7.0,
                channels=[AlertChannel.EMAIL]
            )
        ]
        
        for rule in default_rules:
            self.alert_rules[rule.id] = rule
    
    def _setup_default_templates(self):
        """Set up default notification templates."""
        templates = [
            NotificationTemplate(
                template_id="performance_email",
                alert_type=AlertType.PERFORMANCE_DEGRADATION,
                channel=AlertChannel.EMAIL,
                subject_template="⚠️ Performance Alert: {alert_title}",
                body_template="""
                <h2>Performance Alert</h2>
                <p><strong>Alert:</strong> {alert_title}</p>
                <p><strong>Description:</strong> {description}</p>
                <p><strong>Metric:</strong> {metric_name} = {metric_value}</p>
                <p><strong>Threshold:</strong> {threshold_value}</p>
                <p><strong>Affected URL:</strong> {affected_url}</p>
                <p><strong>Time:</strong> {created_at}</p>
                
                <h3>Recommended Actions:</h3>
                <ul>
                    <li>Check PageSpeed Insights for the affected URL</li>
                    <li>Review recent changes to the page</li>
                    <li>Check server response times</li>
                    <li>Verify CDN and caching configuration</li>
                </ul>
                
                <p>View the monitoring dashboard for more details.</p>
                """
            ),
            NotificationTemplate(
                template_id="performance_slack",
                alert_type=AlertType.PERFORMANCE_DEGRADATION,
                channel=AlertChannel.SLACK,
                subject_template="Performance Alert",
                body_template="""
                🚨 *Performance Alert*
                
                *Alert:* {alert_title}
                *Metric:* {metric_name} = {metric_value}
                *Threshold:* {threshold_value}
                *URL:* {affected_url}
                
                <{dashboard_url}|View Dashboard>
                """,
                slack_color="danger"
            ),
            NotificationTemplate(
                template_id="indexation_email",
                alert_type=AlertType.INDEXATION_ISSUE,
                channel=AlertChannel.EMAIL,
                subject_template="🔍 Indexation Alert: {alert_title}",
                body_template="""
                <h2>Indexation Alert</h2>
                <p><strong>Alert:</strong> {alert_title}</p>
                <p><strong>Description:</strong> {description}</p>
                <p><strong>Current Rate:</strong> {metric_value:.1%}</p>
                <p><strong>Target Rate:</strong> {threshold_value:.1%}</p>
                
                <h3>Recommended Actions:</h3>
                <ul>
                    <li>Check Google Search Console for coverage issues</li>
                    <li>Review sitemap submission status</li>
                    <li>Check robots.txt for blocking issues</li>
                    <li>Request indexing for important pages</li>
                </ul>
                """
            )
        ]
        
        for template in templates:
            key = f"{template.alert_type.value}_{template.channel.value}"
            self.notification_templates[key] = template
    
    async def evaluate_metric(self, 
                              metric_name: str,
                              value: float,
                              project_id: str,
                              url: str = None,
                              timestamp: datetime = None) -> List[Alert]:
        """Evaluate a metric value against alert rules."""
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)
        
        # Store metric value
        if metric_name not in self.metric_history:
            self.metric_history[metric_name] = []
        
        self.metric_history[metric_name].append((timestamp, value))
        
        # Keep only last 1000 values
        if len(self.metric_history[metric_name]) > 1000:
            self.metric_history[metric_name] = self.metric_history[metric_name][-1000:]
        
        # Update anomaly detector
        self.anomaly_detector.update_historical_data(metric_name, value)
        
        # Evaluate against rules
        triggered_alerts = []
        
        for rule in self.alert_rules.values():
            if not rule.enabled:
                continue
            
            if rule.metric_name != metric_name:
                continue
            
            # Check project targeting
            if rule.project_ids and project_id not in rule.project_ids:
                continue
            
            # Check if we're in suppression window
            if self._is_suppressed(rule, timestamp):
                continue
            
            # Check cooldown
            if self._is_in_cooldown(rule, timestamp):
                continue
            
            # Evaluate condition
            should_alert = await self._evaluate_rule_condition(rule, value, metric_name)
            
            if should_alert:
                alert = await self._create_alert(rule, value, project_id, url, timestamp)
                triggered_alerts.append(alert)
                
                # Update rule last triggered
                rule.last_triggered = timestamp
        
        return triggered_alerts
    
    async def _evaluate_rule_condition(self, 
                                       rule: AlertRule,
                                       value: float,
                                       metric_name: str) -> bool:
        """Evaluate if a rule condition is met."""
        
        if rule.condition == "gt":
            return value > rule.threshold_value
        elif rule.condition == "lt":
            return value < rule.threshold_value
        elif rule.condition == "eq":
            return abs(value - rule.threshold_value) < 0.001
        elif rule.condition == "anomaly":
            is_anomaly, _ = self.anomaly_detector.detect_anomaly(metric_name, value)
            return is_anomaly
        
        return False
    
    async def _create_alert(self, 
                            rule: AlertRule,
                            metric_value: float,
                            project_id: str,
                            url: str,
                            timestamp: datetime) -> Alert:
        """Create an alert from a triggered rule."""
        
        alert_id = self._generate_alert_id(rule, project_id, timestamp)
        
        alert = Alert(
            id=alert_id,
            title=rule.name,
            description=rule.description,
            alert_type=rule.alert_type,
            severity=rule.severity,
            status=AlertStatus.OPEN,
            project_id=project_id,
            source="alert_manager",
            affected_url=url,
            metric_name=rule.metric_name,
            metric_value=metric_value,
            threshold_value=rule.threshold_value,
            created_at=timestamp,
            last_updated=timestamp,
            context={
                "rule_id": rule.id,
                "evaluation_timestamp": timestamp.isoformat()
            },
            tags=rule.tags or []
        )
        
        # Store alert
        self.active_alerts[alert_id] = alert
        
        # Send notifications
        await self._send_alert_notifications(alert, rule)
        
        logger.info(f"Created alert {alert_id}: {alert.title}")
        
        return alert
    
    def _generate_alert_id(self, 
                           rule: AlertRule,
                           project_id: str,
                           timestamp: datetime) -> str:
        """Generate unique alert ID."""
        content = f"{rule.id}_{project_id}_{timestamp.date()}"
        return hashlib.md5(content.encode()).hexdigest()[:12]
    
    def _is_suppressed(self, rule: AlertRule, timestamp: datetime) -> bool:
        """Check if alerts are suppressed for this rule."""
        if not rule.suppress_during_maintenance:
            return False
        
        # Check maintenance windows
        for start, end in self.suppression_windows:
            if start <= timestamp <= end:
                return True
        
        return False
    
    def _is_in_cooldown(self, rule: AlertRule, timestamp: datetime) -> bool:
        """Check if rule is in cooldown period."""
        if not rule.last_triggered:
            return False
        
        cooldown_delta = timedelta(minutes=rule.cooldown_minutes)
        return timestamp < rule.last_triggered + cooldown_delta
    
    async def _send_alert_notifications(self, alert: Alert, rule: AlertRule):
        """Send alert notifications through configured channels."""
        
        for channel in rule.channels or []:
            try:
                if channel == AlertChannel.EMAIL:
                    await self._send_email_alert(alert, rule)
                elif channel == AlertChannel.SLACK:
                    await self._send_slack_alert(alert, rule)
                elif channel == AlertChannel.WEBHOOK:
                    await self._send_webhook_alert(alert, rule)
                elif channel == AlertChannel.SMS:
                    await self._send_sms_alert(alert, rule)
                elif channel == AlertChannel.DASHBOARD:
                    # Dashboard alerts are handled by storing in active_alerts
                    pass
                    
            except Exception as e:
                logger.error(f"Failed to send {channel.value} notification for alert {alert.id}: {e}")
    
    async def _send_email_alert(self, alert: Alert, rule: AlertRule):
        """Send email alert notification."""
        template_key = f"{alert.alert_type.value}_email"
        template = self.notification_templates.get(template_key)
        
        if not template:
            # Use generic template
            subject = f"Alert: {alert.title}"
            body = f"""
            Alert: {alert.title}
            Description: {alert.description}
            Metric: {alert.metric_name} = {alert.metric_value}
            Threshold: {alert.threshold_value}
            Time: {alert.created_at}
            """
        else:
            subject = self._format_template(template.subject_template, alert)
            body = self._format_template(template.body_template, alert)
        
        # Get email recipients
        recipients = rule.escalation_chain or ["admin@example.com"]
        
        await self.notification_delivery.send_email(recipients, subject, body, is_html=True)
    
    async def _send_slack_alert(self, alert: Alert, rule: AlertRule):
        """Send Slack alert notification."""
        if not self.settings.slack_webhook_url:
            logger.warning("Slack webhook URL not configured")
            return
        
        template_key = f"{alert.alert_type.value}_slack"
        template = self.notification_templates.get(template_key)
        
        if template:
            message = self._format_template(template.body_template, alert)
            color = template.slack_color or "warning"
        else:
            message = f"🚨 Alert: {alert.title}\n{alert.description}"
            color = "danger" if alert.severity == AlertSeverity.CRITICAL else "warning"
        
        await self.notification_delivery.send_slack(
            self.settings.slack_webhook_url,
            message,
            color
        )
    
    async def _send_webhook_alert(self, alert: Alert, rule: AlertRule):
        """Send webhook alert notification."""
        # Use a generic webhook URL or from settings
        webhook_url = "https://your-webhook-endpoint.com/alerts"  # Would be configurable
        
        payload = {
            "alert": alert.to_dict(),
            "rule": {
                "id": rule.id,
                "name": rule.name
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        await self.notification_delivery.send_webhook(webhook_url, payload)
    
    async def _send_sms_alert(self, alert: Alert, rule: AlertRule):
        """Send SMS alert notification."""
        # Only send SMS for critical alerts
        if alert.severity != AlertSeverity.CRITICAL:
            return
        
        phone_numbers = ["+1234567890"]  # Would be configurable
        message = f"CRITICAL SEO Alert: {alert.title} - {alert.description[:100]}"
        
        await self.notification_delivery.send_sms(phone_numbers, message)
    
    def _format_template(self, template: str, alert: Alert) -> str:
        """Format notification template with alert data."""
        context = {
            "alert_title": alert.title,
            "description": alert.description,
            "metric_name": alert.metric_name or "N/A",
            "metric_value": alert.metric_value or 0,
            "threshold_value": alert.threshold_value or 0,
            "affected_url": alert.affected_url or "N/A",
            "created_at": alert.created_at.strftime("%Y-%m-%d %H:%M:%S UTC"),
            "severity": alert.severity.value.upper(),
            "dashboard_url": "http://localhost:8000"  # Would be configurable
        }
        
        return template.format(**context)
    
    async def acknowledge_alert(self, alert_id: str, acknowledged_by: str) -> bool:
        """Acknowledge an alert."""
        if alert_id not in self.active_alerts:
            return False
        
        alert = self.active_alerts[alert_id]
        alert.status = AlertStatus.ACKNOWLEDGED
        alert.acknowledged_at = datetime.now(timezone.utc)
        alert.last_updated = datetime.now(timezone.utc)
        alert.assigned_to = acknowledged_by
        
        logger.info(f"Alert {alert_id} acknowledged by {acknowledged_by}")
        return True
    
    async def resolve_alert(self, alert_id: str, resolved_by: str, resolution: str = None) -> bool:
        """Resolve an alert."""
        if alert_id not in self.active_alerts:
            return False
        
        alert = self.active_alerts[alert_id]
        alert.status = AlertStatus.RESOLVED
        alert.resolved_at = datetime.now(timezone.utc)
        alert.last_updated = datetime.now(timezone.utc)
        alert.assigned_to = resolved_by
        
        if resolution:
            if not alert.context:
                alert.context = {}
            alert.context["resolution"] = resolution
        
        logger.info(f"Alert {alert_id} resolved by {resolved_by}")
        return True
    
    async def escalate_alerts(self):
        """Check for alerts that need escalation."""
        now = datetime.now(timezone.utc)
        
        for alert in self.active_alerts.values():
            if alert.status != AlertStatus.OPEN:
                continue
            
            # Find the rule for this alert
            rule_id = alert.context.get("rule_id") if alert.context else None
            if not rule_id or rule_id not in self.alert_rules:
                continue
            
            rule = self.alert_rules[rule_id]
            
            # Check if escalation time has passed
            escalation_delta = timedelta(minutes=rule.escalation_delay_minutes)
            if now >= alert.created_at + escalation_delta:
                await self._escalate_alert(alert, rule)
    
    async def _escalate_alert(self, alert: Alert, rule: AlertRule):
        """Escalate an alert to the next level."""
        alert.escalation_level += 1
        alert.escalated_at = datetime.now(timezone.utc)
        alert.last_updated = datetime.now(timezone.utc)
        
        # Send escalation notification
        if rule.escalation_chain and alert.escalation_level <= len(rule.escalation_chain):
            escalation_email = rule.escalation_chain[alert.escalation_level - 1]
            
            subject = f"ESCALATED: {alert.title}"
            body = f"""
            This alert has been escalated due to lack of response.
            
            Alert: {alert.title}
            Description: {alert.description}
            Created: {alert.created_at}
            Escalation Level: {alert.escalation_level}
            
            Please take immediate action.
            """
            
            await self.notification_delivery.send_email([escalation_email], subject, body)
            
            logger.warning(f"Alert {alert.id} escalated to level {alert.escalation_level}")
    
    def add_suppression_window(self, start: datetime, end: datetime):
        """Add a maintenance/suppression window."""
        self.suppression_windows.append((start, end))
        logger.info(f"Added suppression window: {start} to {end}")
    
    def get_active_alerts(self, 
                          project_id: str = None,
                          severity: AlertSeverity = None) -> List[Alert]:
        """Get active alerts with optional filtering."""
        alerts = list(self.active_alerts.values())
        
        # Filter by project
        if project_id:
            alerts = [a for a in alerts if a.project_id == project_id]
        
        # Filter by severity
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        
        # Filter only open and acknowledged alerts
        alerts = [a for a in alerts if a.status in [AlertStatus.OPEN, AlertStatus.ACKNOWLEDGED]]
        
        # Sort by severity and creation time
        severity_order = {
            AlertSeverity.CRITICAL: 0,
            AlertSeverity.HIGH: 1,
            AlertSeverity.MEDIUM: 2,
            AlertSeverity.LOW: 3
        }
        
        alerts.sort(key=lambda a: (severity_order[a.severity], a.created_at))
        
        return alerts
    
    async def generate_alert_report(self, 
                                    project_id: str,
                                    start_date: datetime,
                                    end_date: datetime) -> Dict[str, Any]:
        """Generate alert summary report."""
        
        # Get alerts in date range
        alerts_in_range = [
            alert for alert in self.active_alerts.values()
            if start_date <= alert.created_at <= end_date
            and (not project_id or alert.project_id == project_id)
        ]
        
        # Calculate statistics
        total_alerts = len(alerts_in_range)
        
        # Group by severity
        by_severity = {}
        for severity in AlertSeverity:
            by_severity[severity.value] = len([a for a in alerts_in_range if a.severity == severity])
        
        # Group by type
        by_type = {}
        for alert_type in AlertType:
            by_type[alert_type.value] = len([a for a in alerts_in_range if a.alert_type == alert_type])
        
        # Group by status
        by_status = {}
        for status in AlertStatus:
            by_status[status.value] = len([a for a in alerts_in_range if a.status == status])
        
        # Calculate resolution times
        resolved_alerts = [a for a in alerts_in_range if a.resolved_at]
        avg_resolution_time = 0
        if resolved_alerts:
            resolution_times = [
                (a.resolved_at - a.created_at).total_seconds() / 3600  # hours
                for a in resolved_alerts
            ]
            avg_resolution_time = sum(resolution_times) / len(resolution_times)
        
        # Top issues
        top_metrics = {}
        for alert in alerts_in_range:
            if alert.metric_name:
                top_metrics[alert.metric_name] = top_metrics.get(alert.metric_name, 0) + 1
        
        top_metrics = sorted(top_metrics.items(), key=lambda x: x[1], reverse=True)[:5]
        
        return {
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            },
            "summary": {
                "total_alerts": total_alerts,
                "avg_resolution_time_hours": avg_resolution_time,
                "escalated_alerts": len([a for a in alerts_in_range if a.escalation_level > 0])
            },
            "breakdown": {
                "by_severity": by_severity,
                "by_type": by_type,
                "by_status": by_status
            },
            "top_issues": dict(top_metrics),
            "recommendations": self._generate_alert_recommendations(alerts_in_range)
        }
    
    def _generate_alert_recommendations(self, alerts: List[Alert]) -> List[str]:
        """Generate recommendations based on alert patterns."""
        recommendations = []
        
        # Check for frequent performance alerts
        perf_alerts = [a for a in alerts if a.alert_type == AlertType.PERFORMANCE_DEGRADATION]
        if len(perf_alerts) > 5:
            recommendations.append("Consider implementing performance monitoring and optimization")
        
        # Check for indexation issues
        index_alerts = [a for a in alerts if a.alert_type == AlertType.INDEXATION_ISSUE]
        if len(index_alerts) > 2:
            recommendations.append("Review Google Search Console for systematic indexation issues")
        
        # Check for quality violations
        quality_alerts = [a for a in alerts if a.alert_type == AlertType.QUALITY_VIOLATION]
        if len(quality_alerts) > 3:
            recommendations.append("Implement stricter content quality controls")
        
        # Check resolution times
        unresolved = [a for a in alerts if a.status == AlertStatus.OPEN]
        if len(unresolved) > len(alerts) * 0.3:
            recommendations.append("Improve alert response procedures and staffing")
        
        return recommendations
    
    async def export_alert_data(self, output_path: Path) -> bool:
        """Export alert data to file."""
        try:
            export_data = {
                "export_timestamp": datetime.now(timezone.utc).isoformat(),
                "active_alerts": [alert.to_dict() for alert in self.active_alerts.values()],
                "alert_rules": [asdict(rule) for rule in self.alert_rules.values()],
                "suppression_windows": [
                    {"start": start.isoformat(), "end": end.isoformat()}
                    for start, end in self.suppression_windows
                ]
            }
            
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False, default=str)
            
            logger.info(f"Alert data exported to {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export alert data: {e}")
            return False


async def run_alert_monitoring(project_id: str,
                               settings: Settings,
                               monitoring_config: MonitoringConfig) -> AlertManager:
    """Initialize and run alert monitoring."""
    
    alert_manager = AlertManager(settings, monitoring_config)
    
    # Start background tasks
    async def escalation_loop():
        while True:
            try:
                await alert_manager.escalate_alerts()
                await asyncio.sleep(300)  # Check every 5 minutes
            except Exception as e:
                logger.error(f"Error in escalation loop: {e}")
                await asyncio.sleep(60)
    
    # Start escalation monitoring
    asyncio.create_task(escalation_loop())
    
    logger.info("Alert monitoring started")
    return alert_manager