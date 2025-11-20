"""
Alert Service

Multi-channel alert delivery for security events:
- Email (primary) - all severity levels
- Slack webhook (optional) - high/critical only
- PagerDuty Events API v2 (optional) - critical only

Features:
- Severity-based routing
- Throttling (max 1 alert per event type per user per hour)
- Alert history tracking
- Async sending (non-blocking)
- HTML email templates
- Slack Block Kit formatting
- PagerDuty Events API v2 integration

Part of Phase 2 - Task Group 14: Alert System Implementation
"""

import uuid
import requests
from datetime import datetime, timedelta
from typing import List, Optional

from src.models.security_event import SecurityEvent, SeverityLevel
from src.models.alert_history import AlertHistory, AlertStatus
from src.models.user import User
from src.config.database import get_db_context
from src.config.settings import get_settings
from src.services.email_service import EmailService
from src.observability import get_logger

logger = get_logger("alert_service")
settings = get_settings()


class AlertService:
    """
    Service for sending multi-channel alerts for security events.

    Alert channels based on severity:
    - Critical: Email + Slack + PagerDuty
    - High: Email + Slack
    - Medium: Email only
    - Low: No real-time alert (dashboard only)

    Features:
    - Throttling: Max 1 alert per event type per user per hour
    - Alert recipients: Admins for all alerts, affected users for own events
    - Alert history tracking
    - Async sending (non-blocking)
    """

    def __init__(self):
        """Initialize AlertService."""
        self.logger = logger
        self.email_service = EmailService()
        self.slack_webhook_url = getattr(settings, 'SLACK_WEBHOOK_URL', None)
        self.pagerduty_api_key = getattr(settings, 'PAGERDUTY_API_KEY', None)
        self.alert_throttle_hours = getattr(settings, 'ALERT_THROTTLE_HOURS', 1)

        self.logger.info(
            f"AlertService initialized: "
            f"Slack={'enabled' if self.slack_webhook_url else 'disabled'}, "
            f"PagerDuty={'enabled' if self.pagerduty_api_key else 'disabled'}, "
            f"Throttle={self.alert_throttle_hours}h"
        )

    def send_alert(self, security_event: SecurityEvent) -> List[AlertHistory]:
        """
        Send alert for security event via appropriate channels based on severity.

        Severity routing:
        - critical: Email + Slack + PagerDuty
        - high: Email + Slack
        - medium: Email only
        - low: No real-time alert (dashboard only)

        Args:
            security_event: SecurityEvent to alert on

        Returns:
            List of AlertHistory records created
        """
        try:
            alert_history_list = []

            # Low severity: no real-time alerts (dashboard only)
            if security_event.severity == SeverityLevel.LOW.value:
                self.logger.info(
                    f"Skipping alert for low severity event: {security_event.event_type}",
                    extra={"event_id": str(security_event.event_id)}
                )
                return alert_history_list

            # Check throttling
            if self.check_throttle(security_event.user_id, security_event.event_type):
                self.logger.info(
                    f"Alert throttled for event: {security_event.event_type} (user: {security_event.user_id})",
                    extra={
                        "event_id": str(security_event.event_id),
                        "user_id": str(security_event.user_id)
                    }
                )
                # Record throttled alerts
                alert_history_list.extend(self._record_throttled_alerts(security_event))
                return alert_history_list

            # Get alert recipients
            recipients = self.get_alert_recipients(security_event)

            if not recipients:
                self.logger.warning(
                    f"No alert recipients found for event: {security_event.event_type}",
                    extra={"event_id": str(security_event.event_id)}
                )
                return alert_history_list

            # Send email for all severity levels (medium, high, critical)
            email_alert = self._send_and_record_alert(
                security_event=security_event,
                alert_type="email",
                send_func=lambda: self.send_email_alert(security_event, recipients)
            )
            if email_alert:
                alert_history_list.append(email_alert)

            # Send Slack for high and critical
            if security_event.severity in [SeverityLevel.HIGH.value, SeverityLevel.CRITICAL.value]:
                slack_alert = self._send_and_record_alert(
                    security_event=security_event,
                    alert_type="slack",
                    send_func=lambda: self.send_slack_alert(security_event)
                )
                if slack_alert:
                    alert_history_list.append(slack_alert)

            # Send PagerDuty for critical only
            if security_event.severity == SeverityLevel.CRITICAL.value:
                pagerduty_alert = self._send_and_record_alert(
                    security_event=security_event,
                    alert_type="pagerduty",
                    send_func=lambda: self.send_pagerduty_alert(security_event)
                )
                if pagerduty_alert:
                    alert_history_list.append(pagerduty_alert)

            self.logger.info(
                f"Alerts sent for event: {security_event.event_type} "
                f"(severity: {security_event.severity}, channels: {len(alert_history_list)})",
                extra={
                    "event_id": str(security_event.event_id),
                    "severity": security_event.severity,
                    "channels": len(alert_history_list)
                }
            )

            return alert_history_list

        except Exception as e:
            self.logger.error(
                f"Failed to send alert for event: {security_event.event_type}: {str(e)}",
                exc_info=True,
                extra={"event_id": str(security_event.event_id)}
            )
            return []

    def _send_and_record_alert(
        self,
        security_event: SecurityEvent,
        alert_type: str,
        send_func
    ) -> Optional[AlertHistory]:
        """
        Send alert and record result in alert_history.

        Args:
            security_event: SecurityEvent to alert on
            alert_type: Type of alert (email, slack, pagerduty)
            send_func: Function to call to send alert

        Returns:
            AlertHistory record created, or None if failed
        """
        try:
            # Send alert
            success = send_func()

            # Record in alert_history
            with get_db_context() as db:
                alert_history = AlertHistory(
                    alert_id=uuid.uuid4(),
                    security_event_id=security_event.event_id,
                    user_id=security_event.user_id,
                    alert_type=alert_type,
                    sent_at=datetime.utcnow(),
                    status=AlertStatus.SENT.value if success else AlertStatus.FAILED.value,
                    error_message=None if success else f"Failed to send {alert_type} alert"
                )
                db.add(alert_history)
                db.commit()
                db.refresh(alert_history)
                return alert_history

        except Exception as e:
            # Record failed alert
            self.logger.error(
                f"Failed to send {alert_type} alert: {str(e)}",
                exc_info=True,
                extra={
                    "event_id": str(security_event.event_id),
                    "alert_type": alert_type
                }
            )

            with get_db_context() as db:
                alert_history = AlertHistory(
                    alert_id=uuid.uuid4(),
                    security_event_id=security_event.event_id,
                    user_id=security_event.user_id,
                    alert_type=alert_type,
                    sent_at=datetime.utcnow(),
                    status=AlertStatus.FAILED.value,
                    error_message=str(e)
                )
                db.add(alert_history)
                db.commit()
                db.refresh(alert_history)
                return alert_history

    def _record_throttled_alerts(self, security_event: SecurityEvent) -> List[AlertHistory]:
        """
        Record throttled alerts in alert_history.

        Args:
            security_event: SecurityEvent that was throttled

        Returns:
            List of AlertHistory records for throttled alerts
        """
        alert_history_list = []

        # Determine which channels would have been used
        channels = ["email"]
        if security_event.severity in [SeverityLevel.HIGH.value, SeverityLevel.CRITICAL.value]:
            channels.append("slack")
        if security_event.severity == SeverityLevel.CRITICAL.value:
            channels.append("pagerduty")

        with get_db_context() as db:
            for channel in channels:
                alert_history = AlertHistory(
                    alert_id=uuid.uuid4(),
                    security_event_id=security_event.event_id,
                    user_id=security_event.user_id,
                    alert_type=channel,
                    sent_at=datetime.utcnow(),
                    status=AlertStatus.THROTTLED.value,
                    error_message="Alert throttled (max 1 per event type per user per hour)"
                )
                db.add(alert_history)
                alert_history_list.append(alert_history)

            db.commit()

        return alert_history_list

    def send_email_alert(self, security_event: SecurityEvent, recipients: List[str]) -> bool:
        """
        Send email alert for security events.

        Args:
            security_event: SecurityEvent to alert on
            recipients: List of email addresses to send to

        Returns:
            True if sent successfully, False otherwise
        """
        try:
            # Build email body
            html_body = self._build_email_alert_body(security_event)

            # Send to each recipient
            for recipient in recipients:
                success = self.email_service.send_email(
                    to_email=recipient,
                    subject=f"[{security_event.severity.upper()}] Security Alert: {security_event.event_type}",
                    html_body=html_body
                )
                if not success:
                    self.logger.error(
                        f"Failed to send email alert to {recipient}",
                        extra={
                            "event_id": str(security_event.event_id),
                            "recipient": recipient
                        }
                    )

            return True

        except Exception as e:
            self.logger.error(
                f"Failed to send email alert: {str(e)}",
                exc_info=True,
                extra={"event_id": str(security_event.event_id)}
            )
            return False

    def _build_email_alert_body(self, security_event: SecurityEvent) -> str:
        """
        Build email alert body for security events.

        Args:
            security_event: SecurityEvent to alert on

        Returns:
            HTML email body string
        """
        # Determine severity color
        severity_color_map = {
            'critical': '#dc2626',
            'high': '#ea580c',
            'medium': '#ca8a04',
            'low': '#059669'
        }
        severity = security_event.severity.lower() if security_event.severity else 'low'
        severity_color = severity_color_map.get(severity, '#059669')

        return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Security Alert</title>
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="background: {severity_color}; padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
        <h1 style="color: white; margin: 0; font-size: 28px;">Security Alert</h1>
        <p style="color: white; margin: 10px 0 0 0; font-size: 16px; opacity: 0.9;">{security_event.severity.upper()} severity event detected</p>
    </div>

    <div style="background: #ffffff; padding: 40px; border: 1px solid #e0e0e0; border-top: none; border-radius: 0 0 10px 10px;">
        <h2 style="color: #333; margin-top: 0;">Event Details</h2>

        <div style="background: #f5f5f5; padding: 20px; border-radius: 8px; margin: 20px 0;">
            <p style="margin: 0 0 10px 0;"><strong>Event Type:</strong></p>
            <p style="font-size: 16px; color: #667eea; margin: 0 0 15px 0;">{security_event.event_type}</p>

            <p style="margin: 0 0 10px 0;"><strong>Severity:</strong></p>
            <p style="margin: 0 0 15px 0; color: {severity_color}; font-weight: bold; text-transform: uppercase;">{severity.upper()}</p>

            <p style="margin: 0 0 10px 0;"><strong>Detected At:</strong></p>
            <p style="margin: 0 0 15px 0; color: #666;">{security_event.detected_at.strftime('%Y-%m-%d %H:%M:%S UTC') if security_event.detected_at else 'N/A'}</p>

            {f'<p style="margin: 0 0 10px 0;"><strong>Affected User:</strong></p><p style="margin: 0; color: #666; font-family: monospace;">{security_event.user_id}</p>' if security_event.user_id else ''}
        </div>

        <h3 style="color: #333; margin-top: 30px;">Event Data</h3>
        <div style="background: #f9fafb; padding: 15px; border-radius: 8px; margin: 10px 0;">
            <pre style="margin: 0; white-space: pre-wrap; word-wrap: break-word; font-size: 13px; color: #374151;">{security_event.event_data}</pre>
        </div>

        <h3 style="color: #333; margin-top: 30px;">Action Items</h3>
        <ul style="color: #666; font-size: 14px; margin: 10px 0; padding-left: 20px;">
            <li>Review the security event in the admin dashboard</li>
            <li>Investigate the affected user's recent activity</li>
            <li>Take appropriate action to mitigate the threat</li>
            <li>Mark the event as resolved once addressed</li>
        </ul>

        <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #e0e0e0;">
            <p style="color: #999; font-size: 13px; margin: 0;">
                <strong>Event ID:</strong> {security_event.event_id}
            </p>
        </div>
    </div>

    <div style="text-align: center; margin-top: 20px; color: #999; font-size: 12px;">
        <p>This is an automated security alert from DevMatrix.</p>
        <p>© 2024 DevMatrix. All rights reserved.</p>
    </div>
</body>
</html>
        """.strip()

    def send_slack_alert(self, security_event: SecurityEvent) -> bool:
        """
        Send Slack alert using Block Kit formatting.

        Args:
            security_event: SecurityEvent to alert on

        Returns:
            True if sent successfully, False otherwise
        """
        if not self.slack_webhook_url:
            self.logger.info("Slack webhook not configured, skipping Slack alert")
            return False

        try:
            # Color based on severity
            color_map = {
                SeverityLevel.CRITICAL.value: "#dc2626",  # red
                SeverityLevel.HIGH.value: "#ea580c",      # orange
                SeverityLevel.MEDIUM.value: "#ca8a04",    # yellow
                SeverityLevel.LOW.value: "#059669",       # green
            }
            color = color_map.get(security_event.severity, "#6b7280")

            # Build Slack blocks
            payload = {
                "attachments": [
                    {
                        "color": color,
                        "blocks": [
                            {
                                "type": "header",
                                "text": {
                                    "type": "plain_text",
                                    "text": f"🚨 Security Alert: {security_event.event_type}",
                                    "emoji": True
                                }
                            },
                            {
                                "type": "section",
                                "fields": [
                                    {
                                        "type": "mrkdwn",
                                        "text": f"*Severity:*\n{security_event.severity.upper()}"
                                    },
                                    {
                                        "type": "mrkdwn",
                                        "text": f"*Event Type:*\n{security_event.event_type}"
                                    }
                                ]
                            },
                            {
                                "type": "section",
                                "fields": [
                                    {
                                        "type": "mrkdwn",
                                        "text": f"*Detected At:*\n{security_event.detected_at.strftime('%Y-%m-%d %H:%M:%S UTC') if security_event.detected_at else 'N/A'}"
                                    },
                                    {
                                        "type": "mrkdwn",
                                        "text": f"*User ID:*\n{security_event.user_id or 'N/A'}"
                                    }
                                ]
                            },
                            {
                                "type": "section",
                                "text": {
                                    "type": "mrkdwn",
                                    "text": f"*Event Data:*\n```{str(security_event.event_data)}```"
                                }
                            },
                            {
                                "type": "context",
                                "elements": [
                                    {
                                        "type": "mrkdwn",
                                        "text": f"Event ID: {security_event.event_id}"
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }

            # Send to Slack
            response = requests.post(
                self.slack_webhook_url,
                json=payload,
                timeout=10
            )

            if response.status_code == 200:
                self.logger.info(
                    "Slack alert sent successfully",
                    extra={"event_id": str(security_event.event_id)}
                )
                return True
            else:
                self.logger.error(
                    f"Failed to send Slack alert: {response.status_code} {response.text}",
                    extra={"event_id": str(security_event.event_id)}
                )
                return False

        except Exception as e:
            self.logger.error(
                f"Failed to send Slack alert: {str(e)}",
                exc_info=True,
                extra={"event_id": str(security_event.event_id)}
            )
            return False

    def send_pagerduty_alert(self, security_event: SecurityEvent) -> bool:
        """
        Send PagerDuty alert using Events API v2.

        Args:
            security_event: SecurityEvent to alert on

        Returns:
            True if sent successfully, False otherwise
        """
        if not self.pagerduty_api_key:
            self.logger.info("PagerDuty API key not configured, skipping PagerDuty alert")
            return False

        try:
            # Build PagerDuty Events API v2 payload
            payload = {
                "routing_key": self.pagerduty_api_key,
                "event_action": "trigger",
                "payload": {
                    "summary": f"Security Alert: {security_event.event_type}",
                    "severity": security_event.severity,
                    "source": "DevMatrix Security Monitoring",
                    "timestamp": security_event.detected_at.isoformat() if security_event.detected_at else datetime.utcnow().isoformat(),
                    "custom_details": {
                        "event_type": security_event.event_type,
                        "user_id": str(security_event.user_id) if security_event.user_id else None,
                        "event_data": security_event.event_data,
                        "event_id": str(security_event.event_id)
                    }
                }
            }

            # Send to PagerDuty Events API v2
            response = requests.post(
                "https://events.pagerduty.com/v2/enqueue",
                json=payload,
                timeout=10
            )

            if response.status_code == 202:
                self.logger.info(
                    "PagerDuty alert sent successfully",
                    extra={"event_id": str(security_event.event_id)}
                )
                return True
            else:
                self.logger.error(
                    f"Failed to send PagerDuty alert: {response.status_code} {response.text}",
                    extra={"event_id": str(security_event.event_id)}
                )
                return False

        except Exception as e:
            self.logger.error(
                f"Failed to send PagerDuty alert: {str(e)}",
                exc_info=True,
                extra={"event_id": str(security_event.event_id)}
            )
            return False

    def check_throttle(self, user_id: uuid.UUID, event_type: str) -> bool:
        """
        Check if alert should be throttled (max 1 per event type per user per hour).

        Args:
            user_id: User ID to check
            event_type: Event type to check

        Returns:
            True if alert should be throttled, False otherwise
        """
        try:
            with get_db_context() as db:
                # Look back throttle window
                cutoff_time = datetime.utcnow() - timedelta(hours=self.alert_throttle_hours)

                # Query for recent alerts of same type for same user
                recent_alerts = db.query(AlertHistory).join(
                    SecurityEvent,
                    AlertHistory.security_event_id == SecurityEvent.event_id
                ).filter(
                    SecurityEvent.event_type == event_type,
                    AlertHistory.user_id == user_id,
                    AlertHistory.sent_at >= cutoff_time,
                    AlertHistory.status.in_([AlertStatus.SENT.value, AlertStatus.THROTTLED.value])
                ).first()

                return recent_alerts is not None

        except Exception as e:
            self.logger.error(
                f"Failed to check throttle: {str(e)}",
                exc_info=True,
                extra={"user_id": str(user_id), "event_type": event_type}
            )
            # Fail open (don't throttle on error)
            return False

    def get_alert_recipients(self, security_event: SecurityEvent) -> List[str]:
        """
        Get list of alert recipients for security event.

        Recipients:
        - All admins (is_superuser=True)
        - Affected user (if event has user_id)

        Args:
            security_event: SecurityEvent to get recipients for

        Returns:
            List of email addresses
        """
        try:
            recipients = []

            with get_db_context() as db:
                # Get all admin users
                admins = db.query(User).filter(User.is_superuser == True).all()
                recipients.extend([admin.email for admin in admins])

                # Get affected user if exists
                if security_event.user_id:
                    affected_user = db.query(User).filter(
                        User.user_id == security_event.user_id
                    ).first()

                    if affected_user and affected_user.email not in recipients:
                        recipients.append(affected_user.email)

            # Remove duplicates
            recipients = list(set(recipients))

            return recipients

        except Exception as e:
            self.logger.error(
                f"Failed to get alert recipients: {str(e)}",
                exc_info=True,
                extra={"event_id": str(security_event.event_id)}
            )
            return []
