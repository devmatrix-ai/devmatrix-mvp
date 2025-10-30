"""
Unit Tests for AlertService

Tests alert delivery via email, Slack, and PagerDuty based on severity.
Tests throttling, recipient selection, and alert history tracking.

Phase 2 - Task Group 14: Alert System Implementation
"""

import uuid
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.services.alert_service import AlertService
from src.models.security_event import SecurityEvent, SeverityLevel
from src.models.alert_history import AlertHistory, AlertStatus
from src.models.user import User
from src.config.database import Base, TEST_DATABASE_URL, get_db_context


@pytest.fixture(scope="function")
def test_db_session():
    """
    Create a test database session for alert service tests.
    Creates User, SecurityEvent, and AlertHistory tables.
    """
    engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(bind=engine)

    # Create tables
    User.__table__.create(bind=engine, checkfirst=True)
    SecurityEvent.__table__.create(bind=engine, checkfirst=True)
    AlertHistory.__table__.create(bind=engine, checkfirst=True)

    session = SessionLocal()

    try:
        yield session
    finally:
        session.close()
        # Drop tables
        AlertHistory.__table__.drop(bind=engine, checkfirst=True)
        SecurityEvent.__table__.drop(bind=engine, checkfirst=True)
        User.__table__.drop(bind=engine, checkfirst=True)
        engine.dispose()


@pytest.fixture
def test_user(test_db_session):
    """Create a test user for alert service tests"""
    user = User(
        user_id=uuid.uuid4(),
        email="testuser@example.com",
        username="testuser",
        password_hash="$2b$12$hashed_password_placeholder",
        is_active=True,
        is_superuser=False
    )
    test_db_session.add(user)
    test_db_session.commit()
    test_db_session.refresh(user)
    return user


@pytest.fixture
def test_admin_user(test_db_session):
    """Create a test admin user for alert service tests"""
    admin = User(
        user_id=uuid.uuid4(),
        email="admin@example.com",
        username="admin",
        password_hash="$2b$12$hashed_password_placeholder",
        is_active=True,
        is_superuser=True
    )
    test_db_session.add(admin)
    test_db_session.commit()
    test_db_session.refresh(admin)
    return admin


class TestAlertService:
    """Test suite for AlertService."""

    @pytest.fixture
    def alert_service(self):
        """Create AlertService instance."""
        return AlertService()

    @pytest.fixture
    def critical_event(self, test_db_session, test_user):
        """Create critical security event."""
        event = SecurityEvent(
            event_id=uuid.uuid4(),
            event_type="failed_login_cluster",
            severity=SeverityLevel.CRITICAL.value,
            user_id=test_user.user_id,
            event_data={
                "failed_attempts": 10,
                "ip_addresses": ["192.168.1.100"],
                "time_window": "10 minutes"
            },
            detected_at=datetime.utcnow(),
            resolved=False
        )
        test_db_session.add(event)
        test_db_session.commit()
        test_db_session.refresh(event)
        return event

    @pytest.fixture
    def high_event(self, test_db_session, test_user):
        """Create high severity security event."""
        event = SecurityEvent(
            event_id=uuid.uuid4(),
            event_type="geo_location_change",
            severity=SeverityLevel.HIGH.value,
            user_id=test_user.user_id,
            event_data={
                "previous_country": "US",
                "new_country": "RU",
                "previous_ip": "1.2.3.4",
                "new_ip": "5.6.7.8"
            },
            detected_at=datetime.utcnow(),
            resolved=False
        )
        test_db_session.add(event)
        test_db_session.commit()
        test_db_session.refresh(event)
        return event

    @pytest.fixture
    def medium_event(self, test_db_session, test_user):
        """Create medium severity security event."""
        event = SecurityEvent(
            event_id=uuid.uuid4(),
            event_type="unusual_access",
            severity=SeverityLevel.MEDIUM.value,
            user_id=test_user.user_id,
            event_data={
                "hour": 3,
                "unusual_reason": "access_at_atypical_hours"
            },
            detected_at=datetime.utcnow(),
            resolved=False
        )
        test_db_session.add(event)
        test_db_session.commit()
        test_db_session.refresh(event)
        return event

    @pytest.fixture
    def low_event(self, test_db_session, test_user):
        """Create low severity security event."""
        event = SecurityEvent(
            event_id=uuid.uuid4(),
            event_type="low_priority_event",
            severity=SeverityLevel.LOW.value,
            user_id=test_user.user_id,
            event_data={
                "message": "Low priority event"
            },
            detected_at=datetime.utcnow(),
            resolved=False
        )
        test_db_session.add(event)
        test_db_session.commit()
        test_db_session.refresh(event)
        return event

    @patch('src.services.alert_service.get_db_context')
    def test_send_alert_critical_sends_all_channels(
        self, mock_get_db_context, alert_service, critical_event, test_db_session
    ):
        """Test critical alert sends via email, Slack, and PagerDuty."""
        mock_get_db_context.return_value.__enter__.return_value = test_db_session

        with patch.object(alert_service, 'send_email_alert', return_value=True) as mock_email, \
             patch.object(alert_service, 'send_slack_alert', return_value=True) as mock_slack, \
             patch.object(alert_service, 'send_pagerduty_alert', return_value=True) as mock_pagerduty:

            alert_history = alert_service.send_alert(critical_event)

            # Verify all three channels were called
            assert mock_email.called
            assert mock_slack.called
            assert mock_pagerduty.called

            # Verify alert_history created
            assert alert_history is not None
            assert len(alert_history) == 3  # email + slack + pagerduty

    @patch('src.services.alert_service.get_db_context')
    def test_send_alert_high_sends_email_and_slack(
        self, mock_get_db_context, alert_service, high_event, test_db_session
    ):
        """Test high alert sends via email and Slack (no PagerDuty)."""
        mock_get_db_context.return_value.__enter__.return_value = test_db_session

        with patch.object(alert_service, 'send_email_alert', return_value=True) as mock_email, \
             patch.object(alert_service, 'send_slack_alert', return_value=True) as mock_slack, \
             patch.object(alert_service, 'send_pagerduty_alert', return_value=True) as mock_pagerduty:

            alert_history = alert_service.send_alert(high_event)

            # Verify email and Slack called, but NOT PagerDuty
            assert mock_email.called
            assert mock_slack.called
            assert not mock_pagerduty.called

            # Verify alert_history created
            assert alert_history is not None
            assert len(alert_history) == 2  # email + slack

    @patch('src.services.alert_service.get_db_context')
    def test_send_alert_medium_sends_email_only(
        self, mock_get_db_context, alert_service, medium_event, test_db_session
    ):
        """Test medium alert sends via email only."""
        mock_get_db_context.return_value.__enter__.return_value = test_db_session

        with patch.object(alert_service, 'send_email_alert', return_value=True) as mock_email, \
             patch.object(alert_service, 'send_slack_alert', return_value=True) as mock_slack, \
             patch.object(alert_service, 'send_pagerduty_alert', return_value=True) as mock_pagerduty:

            alert_history = alert_service.send_alert(medium_event)

            # Verify only email called
            assert mock_email.called
            assert not mock_slack.called
            assert not mock_pagerduty.called

            # Verify alert_history created
            assert alert_history is not None
            assert len(alert_history) == 1  # email only

    @patch('src.services.alert_service.get_db_context')
    def test_send_alert_low_no_realtime_alerts(
        self, mock_get_db_context, alert_service, low_event, test_db_session
    ):
        """Test low alert does not send real-time alerts (dashboard only)."""
        mock_get_db_context.return_value.__enter__.return_value = test_db_session

        with patch.object(alert_service, 'send_email_alert', return_value=True) as mock_email, \
             patch.object(alert_service, 'send_slack_alert', return_value=True) as mock_slack, \
             patch.object(alert_service, 'send_pagerduty_alert', return_value=True) as mock_pagerduty:

            alert_history = alert_service.send_alert(low_event)

            # Verify no channels called
            assert not mock_email.called
            assert not mock_slack.called
            assert not mock_pagerduty.called

            # Verify no alert_history created
            assert alert_history is not None
            assert len(alert_history) == 0  # no alerts sent

    @patch('src.services.alert_service.get_db_context')
    def test_throttling_prevents_duplicate_alerts(
        self, mock_get_db_context, alert_service, critical_event, test_db_session
    ):
        """Test throttling prevents duplicate alerts (max 1 per event type per user per hour)."""
        mock_get_db_context.return_value.__enter__.return_value = test_db_session

        with patch.object(alert_service, 'send_email_alert', return_value=True), \
             patch.object(alert_service, 'send_slack_alert', return_value=True), \
             patch.object(alert_service, 'send_pagerduty_alert', return_value=True):

            # Send first alert
            alert_history_1 = alert_service.send_alert(critical_event)
            assert alert_history_1 is not None
            assert len(alert_history_1) == 3

            # Try sending same alert again immediately
            alert_history_2 = alert_service.send_alert(critical_event)

            # Should be throttled
            assert alert_history_2 is not None
            # Verify alerts were throttled (status = throttled)
            throttled_alerts = test_db_session.query(AlertHistory).filter(
                AlertHistory.security_event_id == critical_event.event_id,
                AlertHistory.status == AlertStatus.THROTTLED.value
            ).all()
            assert len(throttled_alerts) > 0

    @patch('src.services.alert_service.get_db_context')
    def test_alert_history_created_for_each_channel(
        self, mock_get_db_context, alert_service, critical_event, test_db_session
    ):
        """Test alert_history record created for each channel."""
        mock_get_db_context.return_value.__enter__.return_value = test_db_session

        with patch.object(alert_service, 'send_email_alert', return_value=True), \
             patch.object(alert_service, 'send_slack_alert', return_value=True), \
             patch.object(alert_service, 'send_pagerduty_alert', return_value=True):

            alert_service.send_alert(critical_event)

            # Verify alert_history records created
            alert_history = test_db_session.query(AlertHistory).filter(
                AlertHistory.security_event_id == critical_event.event_id
            ).all()

            assert len(alert_history) == 3

            # Check alert types
            alert_types = {ah.alert_type for ah in alert_history}
            assert "email" in alert_types
            assert "slack" in alert_types
            assert "pagerduty" in alert_types

            # Check status
            for ah in alert_history:
                assert ah.status == AlertStatus.SENT.value

    @patch('src.services.alert_service.get_db_context')
    def test_failed_alert_logged_with_error_message(
        self, mock_get_db_context, alert_service, critical_event, test_db_session
    ):
        """Test failed alerts logged with error message."""
        mock_get_db_context.return_value.__enter__.return_value = test_db_session

        with patch.object(alert_service, 'send_email_alert', side_effect=Exception("SMTP error")), \
             patch.object(alert_service, 'send_slack_alert', return_value=True), \
             patch.object(alert_service, 'send_pagerduty_alert', return_value=True):

            alert_service.send_alert(critical_event)

            # Verify alert_history has failed email
            failed_alerts = test_db_session.query(AlertHistory).filter(
                AlertHistory.security_event_id == critical_event.event_id,
                AlertHistory.alert_type == "email",
                AlertHistory.status == AlertStatus.FAILED.value
            ).all()

            assert len(failed_alerts) == 1
            assert "SMTP error" in failed_alerts[0].error_message

    @patch('src.services.alert_service.get_db_context')
    def test_get_alert_recipients_includes_admins(
        self, mock_get_db_context, alert_service, critical_event, test_db_session, test_admin_user
    ):
        """Test alert recipients include admins."""
        mock_get_db_context.return_value.__enter__.return_value = test_db_session

        recipients = alert_service.get_alert_recipients(critical_event)

        # Should include at least one admin
        assert len(recipients) > 0

        # Verify recipients are valid email addresses
        for recipient in recipients:
            assert "@" in recipient

        # Verify admin is included
        assert test_admin_user.email in recipients

    @patch('src.services.alert_service.get_db_context')
    def test_get_alert_recipients_includes_affected_user(
        self, mock_get_db_context, alert_service, critical_event, test_db_session, test_user, test_admin_user
    ):
        """Test alert recipients include affected user."""
        mock_get_db_context.return_value.__enter__.return_value = test_db_session

        recipients = alert_service.get_alert_recipients(critical_event)

        # Should include affected user
        assert test_user.email in recipients

    @patch('src.services.alert_service.get_db_context')
    def test_send_email_alert_uses_template(
        self, mock_get_db_context, alert_service, critical_event, test_db_session
    ):
        """Test email alert uses Jinja2 template."""
        mock_get_db_context.return_value.__enter__.return_value = test_db_session

        from src.services.email_service import EmailService

        with patch.object(EmailService, 'send_email', return_value=True) as mock_send:
            recipients = ["admin@example.com"]
            result = alert_service.send_email_alert(critical_event, recipients)

            assert result is True
            assert mock_send.called

            # Verify template content - check for keyword arguments
            call_args = mock_send.call_args
            # Get html_body from kwargs (keyword arguments)
            html_body = call_args.kwargs.get('html_body') or call_args[0][2]

            assert "Security Alert" in html_body
            assert critical_event.event_type in html_body
            assert critical_event.severity in html_body

    def test_send_slack_alert_uses_block_formatting(
        self, alert_service, critical_event
    ):
        """Test Slack alert uses Block Kit formatting."""
        import requests

        with patch.object(requests, 'post', return_value=Mock(status_code=200)) as mock_post:
            # Enable Slack by mocking webhook URL
            alert_service.slack_webhook_url = "https://hooks.slack.com/services/test/webhook/url"

            result = alert_service.send_slack_alert(critical_event)

            assert result is True
            assert mock_post.called

            # Verify Block Kit format
            call_args = mock_post.call_args
            payload = call_args[1]['json']

            assert "attachments" in payload
            assert "blocks" in payload["attachments"][0]

    def test_send_pagerduty_alert_uses_events_api_v2(
        self, alert_service, critical_event
    ):
        """Test PagerDuty alert uses Events API v2."""
        import requests

        with patch.object(requests, 'post', return_value=Mock(status_code=202)) as mock_post:
            # Enable PagerDuty by mocking API key
            alert_service.pagerduty_api_key = "test_pagerduty_api_key"

            result = alert_service.send_pagerduty_alert(critical_event)

            assert result is True
            assert mock_post.called

            # Verify Events API v2 format
            call_args = mock_post.call_args
            payload = call_args[1]['json']

            assert "event_action" in payload
            assert "payload" in payload
            assert payload["event_action"] == "trigger"

    @patch('src.services.alert_service.get_db_context')
    def test_alert_service_async_sending(
        self, mock_get_db_context, alert_service, critical_event, test_db_session
    ):
        """Test alert sending is async (non-blocking)."""
        mock_get_db_context.return_value.__enter__.return_value = test_db_session

        import time

        with patch.object(alert_service, 'send_email_alert', return_value=True), \
             patch.object(alert_service, 'send_slack_alert', return_value=True), \
             patch.object(alert_service, 'send_pagerduty_alert', return_value=True):

            start_time = time.time()
            alert_service.send_alert(critical_event)
            end_time = time.time()

            # Should complete quickly (async)
            elapsed = end_time - start_time
            assert elapsed < 2.0  # Less than 2 seconds

    @patch('src.services.alert_service.get_db_context')
    def test_check_throttle_returns_true_when_recent_alert_exists(
        self, mock_get_db_context, alert_service, test_db_session, test_user
    ):
        """Test check_throttle returns True when recent alert exists."""
        mock_get_db_context.return_value.__enter__.return_value = test_db_session

        event_type = "failed_login_cluster"

        # Create recent alert
        event = SecurityEvent(
            event_id=uuid.uuid4(),
            event_type=event_type,
            severity=SeverityLevel.CRITICAL.value,
            user_id=test_user.user_id,
            event_data={},
            detected_at=datetime.utcnow(),
            resolved=False
        )
        test_db_session.add(event)
        test_db_session.commit()

        alert = AlertHistory(
            alert_id=uuid.uuid4(),
            security_event_id=event.event_id,
            user_id=test_user.user_id,
            alert_type="email",
            sent_at=datetime.utcnow(),
            status=AlertStatus.SENT.value
        )
        test_db_session.add(alert)
        test_db_session.commit()

        # Check throttle
        is_throttled = alert_service.check_throttle(test_user.user_id, event_type)
        assert is_throttled is True

    @patch('src.services.alert_service.get_db_context')
    def test_check_throttle_returns_false_when_no_recent_alert(
        self, mock_get_db_context, alert_service, test_db_session, test_user
    ):
        """Test check_throttle returns False when no recent alert exists."""
        mock_get_db_context.return_value.__enter__.return_value = test_db_session

        event_type = "failed_login_cluster"

        # No recent alerts
        is_throttled = alert_service.check_throttle(test_user.user_id, event_type)
        assert is_throttled is False

    @patch('src.services.alert_service.get_db_context')
    def test_check_throttle_returns_false_after_throttle_window(
        self, mock_get_db_context, alert_service, test_db_session, test_user
    ):
        """Test check_throttle returns False after throttle window expires."""
        mock_get_db_context.return_value.__enter__.return_value = test_db_session

        event_type = "failed_login_cluster"

        # Create old alert (2 hours ago, outside 1-hour throttle window)
        event = SecurityEvent(
            event_id=uuid.uuid4(),
            event_type=event_type,
            severity=SeverityLevel.CRITICAL.value,
            user_id=test_user.user_id,
            event_data={},
            detected_at=datetime.utcnow() - timedelta(hours=2),
            resolved=False
        )
        test_db_session.add(event)
        test_db_session.commit()

        alert = AlertHistory(
            alert_id=uuid.uuid4(),
            security_event_id=event.event_id,
            user_id=test_user.user_id,
            alert_type="email",
            sent_at=datetime.utcnow() - timedelta(hours=2),
            status=AlertStatus.SENT.value
        )
        test_db_session.add(alert)
        test_db_session.commit()

        # Check throttle
        is_throttled = alert_service.check_throttle(test_user.user_id, event_type)
        assert is_throttled is False
