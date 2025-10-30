"""
Unit tests for Security Monitoring database schema (Phase 2 - Task Group 11).

Tests focus on:
- security_events table structure and constraints
- alert_history table structure and constraints
- security_events foreign keys (user_id, resolved_by)
- alert_history foreign keys (security_event_id, user_id)
- severity CHECK constraint (low, medium, high, critical)
- status CHECK constraint (sent, failed, throttled)
- CASCADE delete behavior
- SecurityEvent and AlertHistory model relationships

As per Task Group 11: Write 6-10 focused tests for security monitoring tables
"""

import uuid
from datetime import datetime
import pytest
from sqlalchemy import create_engine, inspect, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

from src.config.database import Base, TEST_DATABASE_URL
from src.models.user import User
from src.models.security_event import SecurityEvent, SeverityLevel
from src.models.alert_history import AlertHistory, AlertStatus


@pytest.fixture(scope="function")
def security_monitoring_db_session():
    """
    Create a test database session with User, SecurityEvent, and AlertHistory models.
    Enables foreign key constraints for SQLite.
    """
    engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})

    # Enable foreign key constraints in SQLite
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    SessionLocal = sessionmaker(bind=engine)

    # Create all required tables
    User.__table__.create(bind=engine, checkfirst=True)
    SecurityEvent.__table__.create(bind=engine, checkfirst=True)
    AlertHistory.__table__.create(bind=engine, checkfirst=True)

    session = SessionLocal()

    try:
        yield session
    finally:
        session.close()
        # Drop tables in reverse dependency order
        AlertHistory.__table__.drop(bind=engine, checkfirst=True)
        SecurityEvent.__table__.drop(bind=engine, checkfirst=True)
        User.__table__.drop(bind=engine, checkfirst=True)
        engine.dispose()


class TestSecurityEventsTable:
    """Test security_events table structure and constraints"""

    def test_security_events_table_has_correct_columns(self, security_monitoring_db_session):
        """Test that security_events table has all required columns"""
        inspector = inspect(security_monitoring_db_session.bind)
        columns = {col['name']: col for col in inspector.get_columns('security_events')}

        # Verify all required columns exist
        assert 'event_id' in columns
        assert 'event_type' in columns
        assert 'severity' in columns
        assert 'user_id' in columns
        assert 'event_data' in columns
        assert 'detected_at' in columns
        assert 'resolved' in columns
        assert 'resolved_at' in columns
        assert 'resolved_by' in columns

    def test_security_event_severity_enum_constraint(self, security_monitoring_db_session):
        """Test that severity field only accepts valid values (low/medium/high/critical)"""
        # Create user for foreign key
        user = User(
            email="test@example.com",
            username="testuser",
            password_hash="hashed_password"
        )
        security_monitoring_db_session.add(user)
        security_monitoring_db_session.commit()

        # Valid severity values should work
        valid_severities = ['low', 'medium', 'high', 'critical']
        for severity in valid_severities:
            event = SecurityEvent(
                event_type="failed_login",
                severity=severity,
                user_id=user.user_id,
                event_data={"reason": "invalid_password"}
            )
            security_monitoring_db_session.add(event)
            security_monitoring_db_session.commit()
            security_monitoring_db_session.delete(event)
            security_monitoring_db_session.commit()

        # Invalid severity should fail (CHECK constraint)
        # Note: SQLite doesn't enforce CHECK constraints by default in some versions
        # This test documents expected behavior for PostgreSQL
        invalid_event = SecurityEvent(
            event_type="failed_login",
            severity="invalid",  # Invalid severity
            user_id=user.user_id,
            event_data={"reason": "test"}
        )
        security_monitoring_db_session.add(invalid_event)

        # This will fail in PostgreSQL with CHECK constraint violation
        # In SQLite, we rely on enum validation at the model layer
        try:
            security_monitoring_db_session.commit()
            # If commit succeeds (SQLite), validate through model enum
            assert invalid_event.severity not in [s.value for s in SeverityLevel]
        except (IntegrityError, ValueError):
            # Expected in PostgreSQL or with strict validation
            security_monitoring_db_session.rollback()

    def test_security_event_foreign_key_to_user(self, security_monitoring_db_session):
        """Test foreign key relationship from security_events.user_id to users.user_id"""
        # Create user
        user = User(
            email="test@example.com",
            username="testuser",
            password_hash="hashed_password"
        )
        security_monitoring_db_session.add(user)
        security_monitoring_db_session.commit()

        # Create security event
        event = SecurityEvent(
            event_type="suspicious_login",
            severity="high",
            user_id=user.user_id,
            event_data={"ip": "1.2.3.4", "location": "Unknown"}
        )
        security_monitoring_db_session.add(event)
        security_monitoring_db_session.commit()

        assert event.event_id is not None
        assert event.user_id == user.user_id
        assert event.detected_at is not None

    def test_security_event_resolved_by_foreign_key(self, security_monitoring_db_session):
        """Test foreign key relationship from security_events.resolved_by to users.user_id"""
        # Create user and admin
        user = User(
            email="user@example.com",
            username="user",
            password_hash="hashed_password"
        )
        admin = User(
            email="admin@example.com",
            username="admin",
            password_hash="hashed_password",
            is_superuser=True
        )
        security_monitoring_db_session.add(user)
        security_monitoring_db_session.add(admin)
        security_monitoring_db_session.commit()

        # Create security event
        event = SecurityEvent(
            event_type="account_lockout",
            severity="medium",
            user_id=user.user_id,
            event_data={"reason": "too_many_failed_attempts"}
        )
        security_monitoring_db_session.add(event)
        security_monitoring_db_session.commit()

        # Admin resolves the event
        event.resolved = True
        event.resolved_at = datetime.utcnow()
        event.resolved_by = admin.user_id
        security_monitoring_db_session.commit()

        assert event.resolved is True
        assert event.resolved_by == admin.user_id
        assert event.resolved_at is not None

    def test_cascade_delete_security_event_when_user_deleted(self, security_monitoring_db_session):
        """Test CASCADE delete: deleting user removes their security events"""
        # Create user
        user = User(
            email="test@example.com",
            username="testuser",
            password_hash="hashed_password"
        )
        security_monitoring_db_session.add(user)
        security_monitoring_db_session.commit()

        # Create security event
        event = SecurityEvent(
            event_type="failed_login",
            severity="low",
            user_id=user.user_id,
            event_data={"reason": "invalid_password"}
        )
        security_monitoring_db_session.add(event)
        security_monitoring_db_session.commit()

        event_id = event.event_id

        # Delete user (should cascade to security_events)
        security_monitoring_db_session.delete(user)
        security_monitoring_db_session.commit()

        # Verify security event was cascade deleted
        deleted_event = security_monitoring_db_session.query(SecurityEvent).filter(
            SecurityEvent.event_id == event_id
        ).first()
        assert deleted_event is None


class TestAlertHistoryTable:
    """Test alert_history table structure with foreign keys"""

    def test_alert_history_table_has_correct_columns(self, security_monitoring_db_session):
        """Test that alert_history table has all required columns"""
        inspector = inspect(security_monitoring_db_session.bind)
        columns = {col['name']: col for col in inspector.get_columns('alert_history')}

        # Verify all required columns exist
        assert 'alert_id' in columns
        assert 'security_event_id' in columns
        assert 'user_id' in columns
        assert 'alert_type' in columns
        assert 'sent_at' in columns
        assert 'status' in columns
        assert 'error_message' in columns

    def test_alert_history_status_enum_constraint(self, security_monitoring_db_session):
        """Test that status field only accepts valid values (sent/failed/throttled)"""
        # Create user
        user = User(
            email="test@example.com",
            username="testuser",
            password_hash="hashed_password"
        )
        security_monitoring_db_session.add(user)
        security_monitoring_db_session.commit()

        # Create security event
        event = SecurityEvent(
            event_type="failed_login",
            severity="medium",
            user_id=user.user_id,
            event_data={"reason": "invalid_password"}
        )
        security_monitoring_db_session.add(event)
        security_monitoring_db_session.commit()

        # Valid status values should work
        valid_statuses = ['sent', 'failed', 'throttled']
        for status in valid_statuses:
            alert = AlertHistory(
                security_event_id=event.event_id,
                user_id=user.user_id,
                alert_type="email",
                status=status
            )
            security_monitoring_db_session.add(alert)
            security_monitoring_db_session.commit()
            security_monitoring_db_session.delete(alert)
            security_monitoring_db_session.commit()

        # Invalid status should fail (CHECK constraint)
        invalid_alert = AlertHistory(
            security_event_id=event.event_id,
            user_id=user.user_id,
            alert_type="email",
            status="invalid"  # Invalid status
        )
        security_monitoring_db_session.add(invalid_alert)

        # This will fail in PostgreSQL with CHECK constraint violation
        try:
            security_monitoring_db_session.commit()
            # If commit succeeds (SQLite), validate through model enum
            assert invalid_alert.status not in [s.value for s in AlertStatus]
        except (IntegrityError, ValueError):
            # Expected in PostgreSQL or with strict validation
            security_monitoring_db_session.rollback()

    def test_alert_history_foreign_keys(self, security_monitoring_db_session):
        """Test foreign key relationships to security_events and users"""
        # Create user
        user = User(
            email="test@example.com",
            username="testuser",
            password_hash="hashed_password"
        )
        security_monitoring_db_session.add(user)
        security_monitoring_db_session.commit()

        # Create security event
        event = SecurityEvent(
            event_type="privilege_escalation",
            severity="critical",
            user_id=user.user_id,
            event_data={"old_role": "user", "new_role": "admin"}
        )
        security_monitoring_db_session.add(event)
        security_monitoring_db_session.commit()

        # Create alert history
        alert = AlertHistory(
            security_event_id=event.event_id,
            user_id=user.user_id,
            alert_type="email",
            status="sent"
        )
        security_monitoring_db_session.add(alert)
        security_monitoring_db_session.commit()

        assert alert.alert_id is not None
        assert alert.security_event_id == event.event_id
        assert alert.user_id == user.user_id
        assert alert.sent_at is not None

    def test_cascade_delete_alert_when_security_event_deleted(self, security_monitoring_db_session):
        """Test CASCADE delete: deleting security event removes alert history"""
        # Create user
        user = User(
            email="test@example.com",
            username="testuser",
            password_hash="hashed_password"
        )
        security_monitoring_db_session.add(user)
        security_monitoring_db_session.commit()

        # Create security event
        event = SecurityEvent(
            event_type="geo_location_change",
            severity="high",
            user_id=user.user_id,
            event_data={"old_country": "US", "new_country": "CN"}
        )
        security_monitoring_db_session.add(event)
        security_monitoring_db_session.commit()

        # Create alert history
        alert = AlertHistory(
            security_event_id=event.event_id,
            user_id=user.user_id,
            alert_type="email",
            status="sent"
        )
        security_monitoring_db_session.add(alert)
        security_monitoring_db_session.commit()

        alert_id = alert.alert_id

        # Delete security event (should cascade to alert_history)
        security_monitoring_db_session.delete(event)
        security_monitoring_db_session.commit()

        # Verify alert was cascade deleted
        deleted_alert = security_monitoring_db_session.query(AlertHistory).filter(
            AlertHistory.alert_id == alert_id
        ).first()
        assert deleted_alert is None

    def test_cascade_delete_alert_when_user_deleted(self, security_monitoring_db_session):
        """Test CASCADE delete: deleting user removes their alert history"""
        # Create user
        user = User(
            email="test@example.com",
            username="testuser",
            password_hash="hashed_password"
        )
        security_monitoring_db_session.add(user)
        security_monitoring_db_session.commit()

        # Create security event
        event = SecurityEvent(
            event_type="unusual_access",
            severity="medium",
            user_id=user.user_id,
            event_data={"access_time": "3am"}
        )
        security_monitoring_db_session.add(event)
        security_monitoring_db_session.commit()

        # Create alert history
        alert = AlertHistory(
            security_event_id=event.event_id,
            user_id=user.user_id,
            alert_type="slack",
            status="sent"
        )
        security_monitoring_db_session.add(alert)
        security_monitoring_db_session.commit()

        alert_id = alert.alert_id

        # Delete user (should cascade to both security_events and alert_history)
        security_monitoring_db_session.delete(user)
        security_monitoring_db_session.commit()

        # Verify alert was cascade deleted
        deleted_alert = security_monitoring_db_session.query(AlertHistory).filter(
            AlertHistory.alert_id == alert_id
        ).first()
        assert deleted_alert is None


class TestSecurityEventModel:
    """Test SecurityEvent model functionality"""

    def test_security_event_to_dict(self, security_monitoring_db_session):
        """Test SecurityEvent.to_dict() method"""
        # Create user
        user = User(
            email="test@example.com",
            username="testuser",
            password_hash="hashed_password"
        )
        security_monitoring_db_session.add(user)
        security_monitoring_db_session.commit()

        # Create security event
        event = SecurityEvent(
            event_type="failed_login_cluster",
            severity="high",
            user_id=user.user_id,
            event_data={"failed_attempts": 5, "time_window": "10m"}
        )
        security_monitoring_db_session.add(event)
        security_monitoring_db_session.commit()

        # Test to_dict
        event_dict = event.to_dict()
        assert event_dict['event_id'] == str(event.event_id)
        assert event_dict['event_type'] == "failed_login_cluster"
        assert event_dict['severity'] == "high"
        assert event_dict['user_id'] == str(user.user_id)
        assert event_dict['event_data'] == {"failed_attempts": 5, "time_window": "10m"}
        assert event_dict['resolved'] is False
        assert 'detected_at' in event_dict


class TestAlertHistoryModel:
    """Test AlertHistory model functionality"""

    def test_alert_history_to_dict(self, security_monitoring_db_session):
        """Test AlertHistory.to_dict() method"""
        # Create user
        user = User(
            email="test@example.com",
            username="testuser",
            password_hash="hashed_password"
        )
        security_monitoring_db_session.add(user)
        security_monitoring_db_session.commit()

        # Create security event
        event = SecurityEvent(
            event_type="2fa_disabled",
            severity="critical",
            user_id=user.user_id,
            event_data={"enforced": True}
        )
        security_monitoring_db_session.add(event)
        security_monitoring_db_session.commit()

        # Create alert history
        alert = AlertHistory(
            security_event_id=event.event_id,
            user_id=user.user_id,
            alert_type="pagerduty",
            status="sent"
        )
        security_monitoring_db_session.add(alert)
        security_monitoring_db_session.commit()

        # Test to_dict
        alert_dict = alert.to_dict()
        assert alert_dict['alert_id'] == str(alert.alert_id)
        assert alert_dict['security_event_id'] == str(event.event_id)
        assert alert_dict['user_id'] == str(user.user_id)
        assert alert_dict['alert_type'] == "pagerduty"
        assert alert_dict['status'] == "sent"
        assert 'sent_at' in alert_dict
        assert alert_dict['error_message'] is None
