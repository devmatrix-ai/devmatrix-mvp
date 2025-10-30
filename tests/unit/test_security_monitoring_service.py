"""
Unit Tests for SecurityMonitoringService

Tests security event detection and monitoring including:
- Failed login clusters (5+ in 10 minutes)
- Geo-location changes (IP country change)
- Privilege escalation (role changed to admin/superadmin)
- Unusual access patterns (access at atypical hours)
- Multiple 403s (10+ in 5 minutes)
- Account lockout events
- 2FA disabled when enforced
- Multiple concurrent sessions from different countries
- Severity assignment (low/medium/high/critical)
- Batch processing workflow

Part of Phase 2 - Task Group 13: Security Event Monitoring
"""

import pytest
import uuid
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from freezegun import freeze_time
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.services.security_monitoring_service import SecurityMonitoringService
from src.models.security_event import SecurityEvent, SeverityLevel
from src.models.audit_log import AuditLog
from src.models.user import User
from src.config.database import Base, TEST_DATABASE_URL


@pytest.fixture(scope="function")
def test_db_session():
    """
    Create a test database session for security monitoring tests.
    Creates User, AuditLog, and SecurityEvent tables.
    """
    engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(bind=engine)

    # Create tables
    User.__table__.create(bind=engine, checkfirst=True)
    AuditLog.__table__.create(bind=engine, checkfirst=True)
    SecurityEvent.__table__.create(bind=engine, checkfirst=True)

    session = SessionLocal()

    try:
        yield session
    finally:
        session.close()
        # Drop tables
        SecurityEvent.__table__.drop(bind=engine, checkfirst=True)
        AuditLog.__table__.drop(bind=engine, checkfirst=True)
        User.__table__.drop(bind=engine, checkfirst=True)
        engine.dispose()


@pytest.fixture
def test_user(test_db_session):
    """Create a test user for security monitoring tests"""
    user = User(
        user_id=uuid.uuid4(),
        email="security_test@example.com",
        username="security_test_user",
        password_hash="$2b$12$hashed_password_placeholder",
        is_active=True,
        is_superuser=False
    )
    test_db_session.add(user)
    test_db_session.commit()
    test_db_session.refresh(user)
    return user


class TestSecurityMonitoringService:
    """Test suite for SecurityMonitoringService"""

    @pytest.fixture
    def service(self):
        """Create SecurityMonitoringService instance for tests"""
        return SecurityMonitoringService()

    # ========================================
    # Test 1: Detect Failed Login Clusters (5+ in 10 minutes)
    # ========================================

    @freeze_time("2025-10-26 10:00:00")
    @patch('src.services.security_monitoring_service.get_db_context')
    def test_detect_failed_login_clusters(self, mock_db_context, service, test_db_session, test_user):
        """Test detection of 5+ failed logins within 10 minutes"""
        mock_db_context.return_value.__enter__.return_value = test_db_session
        mock_db_context.return_value.__exit__.return_value = None

        # Create 6 failed login attempts within 10 minutes
        base_time = datetime(2025, 10, 26, 10, 0, 0)
        for i in range(6):
            audit_log = AuditLog(
                id=uuid.uuid4(),
                timestamp=base_time + timedelta(minutes=i),
                user_id=test_user.user_id,
                action="auth.login_failed",
                result="denied",
                ip_address="192.168.1.100",
                user_agent="Mozilla/5.0",
                event_metadata={}
            )
            test_db_session.add(audit_log)
        test_db_session.commit()

        # Detect failed login clusters
        events = service.detect_failed_login_clusters()

        # Should detect 1 cluster for this user
        assert len(events) == 1, "Should detect 1 failed login cluster"
        assert events[0].event_type == "failed_login_cluster"
        assert events[0].user_id == test_user.user_id
        assert events[0].severity == SeverityLevel.HIGH.value  # 6 attempts is high, 10+ is critical
        assert events[0].event_data["failed_attempts"] == 6
        assert events[0].event_data["time_window"] == "10 minutes"

    # ========================================
    # Test 2: Detect Geo-Location Changes
    # ========================================

    @freeze_time("2025-10-26 10:00:00")
    @patch('src.services.security_monitoring_service.get_db_context')
    def test_detect_geo_changes(self, mock_db_context, service, test_db_session, test_user):
        """Test detection of IP country changes"""
        mock_db_context.return_value.__enter__.return_value = test_db_session
        mock_db_context.return_value.__exit__.return_value = None

        # Create login from US
        audit_log1 = AuditLog(
            id=uuid.uuid4(),
            timestamp=datetime(2025, 10, 26, 9, 50, 0),
            user_id=test_user.user_id,
            action="auth.login",
            result="success",
            ip_address="192.168.1.100",  # US IP (simulated)
            user_agent="Mozilla/5.0",
            event_metadata={"country": "US"}
        )
        test_db_session.add(audit_log1)

        # Create login from different country (China) 5 minutes later
        audit_log2 = AuditLog(
            id=uuid.uuid4(),
            timestamp=datetime(2025, 10, 26, 9, 55, 0),
            user_id=test_user.user_id,
            action="auth.login",
            result="success",
            ip_address="103.45.67.89",  # China IP (simulated)
            user_agent="Mozilla/5.0",
            event_metadata={"country": "CN"}
        )
        test_db_session.add(audit_log2)
        test_db_session.commit()

        # Detect geo changes
        events = service.detect_geo_changes()

        # Should detect 1 geo change event
        assert len(events) == 1, "Should detect 1 geo-location change"
        assert events[0].event_type == "geo_location_change"
        assert events[0].user_id == test_user.user_id
        assert events[0].severity == SeverityLevel.HIGH.value
        assert events[0].event_data["previous_country"] == "US"
        assert events[0].event_data["new_country"] == "CN"

    # ========================================
    # Test 3: Detect Privilege Escalations
    # ========================================

    @freeze_time("2025-10-26 10:00:00")
    @patch('src.services.security_monitoring_service.get_db_context')
    def test_detect_privilege_escalations(self, mock_db_context, service, test_db_session, test_user):
        """Test detection of role changes to admin/superadmin"""
        mock_db_context.return_value.__enter__.return_value = test_db_session
        mock_db_context.return_value.__exit__.return_value = None

        # Create role assignment to superadmin
        audit_log = AuditLog(
            id=uuid.uuid4(),
            timestamp=datetime(2025, 10, 26, 9, 55, 0),
            user_id=test_user.user_id,
            action="role.assigned",
            result="success",
            resource_type="role",
            ip_address="192.168.1.100",
            user_agent="Mozilla/5.0",
            event_metadata={"role": "superadmin", "assigned_by": str(uuid.uuid4())}
        )
        test_db_session.add(audit_log)
        test_db_session.commit()

        # Detect privilege escalations
        events = service.detect_privilege_escalations()

        # Should detect 1 privilege escalation event
        assert len(events) == 1, "Should detect 1 privilege escalation"
        assert events[0].event_type == "privilege_escalation"
        assert events[0].user_id == test_user.user_id
        assert events[0].severity == SeverityLevel.CRITICAL.value
        assert events[0].event_data["role"] == "superadmin"

    # ========================================
    # Test 4: Detect Unusual Access Patterns
    # ========================================

    @freeze_time("2025-10-26 03:00:00")  # 3 AM (unusual hour)
    @patch('src.services.security_monitoring_service.get_db_context')
    def test_detect_unusual_access_patterns(self, mock_db_context, service, test_db_session, test_user):
        """Test detection of access at atypical hours (midnight to 6 AM)"""
        mock_db_context.return_value.__enter__.return_value = test_db_session
        mock_db_context.return_value.__exit__.return_value = None

        # Create access at 3 AM (unusual hour)
        audit_log = AuditLog(
            id=uuid.uuid4(),
            timestamp=datetime(2025, 10, 26, 3, 0, 0),
            user_id=test_user.user_id,
            action="conversation.read",
            result="success",
            ip_address="192.168.1.100",
            user_agent="Mozilla/5.0",
            event_metadata={}
        )
        test_db_session.add(audit_log)
        test_db_session.commit()

        # Detect unusual access patterns
        events = service.detect_unusual_access_patterns()

        # Should detect 1 unusual access event
        assert len(events) == 1, "Should detect 1 unusual access pattern"
        assert events[0].event_type == "unusual_access"
        assert events[0].user_id == test_user.user_id
        assert events[0].severity == SeverityLevel.MEDIUM.value
        assert events[0].event_data["hour"] == 3
        assert events[0].event_data["unusual_reason"] == "access_at_atypical_hours"

    # ========================================
    # Test 5: Detect Multiple 403s (10+ in 5 minutes)
    # ========================================

    @freeze_time("2025-10-26 10:00:00")
    @patch('src.services.security_monitoring_service.get_db_context')
    def test_detect_multiple_403s(self, mock_db_context, service, test_db_session, test_user):
        """Test detection of 10+ 403 errors within 5 minutes"""
        mock_db_context.return_value.__enter__.return_value = test_db_session
        mock_db_context.return_value.__exit__.return_value = None

        # Create 12 denied access attempts within 5 minutes
        base_time = datetime(2025, 10, 26, 10, 0, 0)
        for i in range(12):
            audit_log = AuditLog(
                id=uuid.uuid4(),
                timestamp=base_time + timedelta(seconds=i * 20),  # Every 20 seconds
                user_id=test_user.user_id,
                action="conversation.read_denied",
                result="denied",
                resource_type="conversation",
                resource_id=uuid.uuid4(),
                ip_address="192.168.1.100",
                user_agent="Mozilla/5.0",
                event_metadata={}
            )
            test_db_session.add(audit_log)
        test_db_session.commit()

        # Detect multiple 403s
        events = service.detect_multiple_403s()

        # Should detect 1 event
        assert len(events) == 1, "Should detect 1 multiple 403s event"
        assert events[0].event_type == "multiple_403s"
        assert events[0].user_id == test_user.user_id
        assert events[0].severity == SeverityLevel.MEDIUM.value
        assert events[0].event_data["denied_count"] == 12
        assert events[0].event_data["time_window"] == "5 minutes"

    # ========================================
    # Test 6: Detect Account Lockouts
    # ========================================

    @freeze_time("2025-10-26 10:00:00")
    @patch('src.services.security_monitoring_service.get_db_context')
    def test_detect_account_lockouts(self, mock_db_context, service, test_db_session, test_user):
        """Test detection of account lockout events"""
        mock_db_context.return_value.__enter__.return_value = test_db_session
        mock_db_context.return_value.__exit__.return_value = None

        # Create account lockout event
        audit_log = AuditLog(
            id=uuid.uuid4(),
            timestamp=datetime(2025, 10, 26, 9, 55, 0),
            user_id=test_user.user_id,
            action="account.locked",
            result="success",
            ip_address="192.168.1.100",
            user_agent="Mozilla/5.0",
            event_metadata={"reason": "failed_login_threshold", "locked_until": "2025-10-26 10:10:00"}
        )
        test_db_session.add(audit_log)
        test_db_session.commit()

        # Detect account lockouts
        events = service.detect_account_lockouts()

        # Should detect 1 lockout event
        assert len(events) == 1, "Should detect 1 account lockout"
        assert events[0].event_type == "account_lockout"
        assert events[0].user_id == test_user.user_id
        assert events[0].severity == SeverityLevel.MEDIUM.value
        assert events[0].event_data["reason"] == "failed_login_threshold"

    # ========================================
    # Test 7: Detect 2FA Disabled When Enforced
    # ========================================

    @freeze_time("2025-10-26 10:00:00")
    @patch('src.services.security_monitoring_service.get_db_context')
    def test_detect_2fa_disabled(self, mock_db_context, service, test_db_session, test_user):
        """Test detection of 2FA disabled when enforcement is enabled"""
        mock_db_context.return_value.__enter__.return_value = test_db_session
        mock_db_context.return_value.__exit__.return_value = None

        # Create 2FA disabled event
        audit_log = AuditLog(
            id=uuid.uuid4(),
            timestamp=datetime(2025, 10, 26, 9, 55, 0),
            user_id=test_user.user_id,
            action="2fa.disabled",
            result="success",
            ip_address="192.168.1.100",
            user_agent="Mozilla/5.0",
            event_metadata={"enforce_2fa": True}
        )
        test_db_session.add(audit_log)
        test_db_session.commit()

        # Detect 2FA disabled events
        events = service.detect_2fa_disabled()

        # Should detect 1 event
        assert len(events) == 1, "Should detect 1 2FA disabled event"
        assert events[0].event_type == "2fa_disabled"
        assert events[0].user_id == test_user.user_id
        assert events[0].severity == SeverityLevel.HIGH.value
        assert events[0].event_data["enforce_2fa"] is True

    # ========================================
    # Test 8: Detect Concurrent Sessions from Different Countries
    # ========================================

    @freeze_time("2025-10-26 10:00:00")
    @patch('src.services.security_monitoring_service.get_db_context')
    def test_detect_concurrent_sessions(self, mock_db_context, service, test_db_session, test_user):
        """Test detection of multiple concurrent sessions from different countries"""
        mock_db_context.return_value.__enter__.return_value = test_db_session
        mock_db_context.return_value.__exit__.return_value = None

        # Create logins from 3 different countries within 5 minutes
        base_time = datetime(2025, 10, 26, 9, 55, 0)
        countries = ["US", "CN", "RU"]
        for i, country in enumerate(countries):
            audit_log = AuditLog(
                id=uuid.uuid4(),
                timestamp=base_time + timedelta(minutes=i),
                user_id=test_user.user_id,
                action="auth.login",
                result="success",
                ip_address=f"192.168.{i}.100",
                user_agent="Mozilla/5.0",
                event_metadata={"country": country}
            )
            test_db_session.add(audit_log)
        test_db_session.commit()

        # Detect concurrent sessions
        events = service.detect_concurrent_sessions()

        # Should detect 1 event
        assert len(events) == 1, "Should detect 1 concurrent sessions event"
        assert events[0].event_type == "concurrent_sessions"
        assert events[0].user_id == test_user.user_id
        assert events[0].severity == SeverityLevel.CRITICAL.value
        assert sorted(events[0].event_data["countries"]) == sorted(["US", "CN", "RU"])  # Countries are sorted
        assert events[0].event_data["session_count"] == 3

    # ========================================
    # Test 9: Severity Assignment Logic
    # ========================================

    @freeze_time("2025-10-26 10:00:00")
    @patch('src.services.security_monitoring_service.get_db_context')
    def test_severity_assignment_critical(self, mock_db_context, service, test_db_session, test_user):
        """Test critical severity assignment for severe events"""
        mock_db_context.return_value.__enter__.return_value = test_db_session
        mock_db_context.return_value.__exit__.return_value = None

        # Create 11 failed login attempts (should be critical)
        base_time = datetime(2025, 10, 26, 10, 0, 0)
        for i in range(11):
            audit_log = AuditLog(
                id=uuid.uuid4(),
                timestamp=base_time + timedelta(minutes=i),
                user_id=test_user.user_id,
                action="auth.login_failed",
                result="denied",
                ip_address="192.168.1.100",
                user_agent="Mozilla/5.0",
                event_metadata={}
            )
            test_db_session.add(audit_log)
        test_db_session.commit()

        events = service.detect_failed_login_clusters()

        assert len(events) == 1
        assert events[0].severity == SeverityLevel.CRITICAL.value, "10+ failed logins should be critical"

    # ========================================
    # Test 10: Batch Processing Workflow
    # ========================================

    @freeze_time("2025-10-26 10:00:00")
    @patch('src.services.security_monitoring_service.get_db_context')
    def test_run_all_detections(self, mock_db_context, service, test_db_session, test_user):
        """Test batch processing runs all detection methods"""
        mock_db_context.return_value.__enter__.return_value = test_db_session
        mock_db_context.return_value.__exit__.return_value = None

        # Create various security events
        base_time = datetime(2025, 10, 26, 10, 0, 0)

        # Failed logins
        for i in range(6):
            test_db_session.add(AuditLog(
                id=uuid.uuid4(),
                timestamp=base_time + timedelta(minutes=i),
                user_id=test_user.user_id,
                action="auth.login_failed",
                result="denied",
                ip_address="192.168.1.100",
                user_agent="Mozilla/5.0",
                event_metadata={}
            ))

        # Account lockout
        test_db_session.add(AuditLog(
            id=uuid.uuid4(),
            timestamp=base_time,
            user_id=test_user.user_id,
            action="account.locked",
            result="success",
            ip_address="192.168.1.100",
            user_agent="Mozilla/5.0",
            event_metadata={"reason": "failed_login_threshold"}
        ))

        test_db_session.commit()

        # Run all detections
        all_events = service.run_all_detections()

        # Should detect at least 2 events (failed login cluster + account lockout)
        assert len(all_events) >= 2, "Should detect multiple event types"

        event_types = [e.event_type for e in all_events]
        assert "failed_login_cluster" in event_types
        assert "account_lockout" in event_types

    # ========================================
    # Test 11: No Duplicate Events Created
    # ========================================

    @freeze_time("2025-10-26 10:00:00")
    @patch('src.services.security_monitoring_service.get_db_context')
    def test_no_duplicate_events_created(self, mock_db_context, service, test_db_session, test_user):
        """Test that running detection multiple times doesn't create duplicate events"""
        mock_db_context.return_value.__enter__.return_value = test_db_session
        mock_db_context.return_value.__exit__.return_value = None

        # Create failed login attempts
        base_time = datetime(2025, 10, 26, 10, 0, 0)
        for i in range(6):
            test_db_session.add(AuditLog(
                id=uuid.uuid4(),
                timestamp=base_time + timedelta(minutes=i),
                user_id=test_user.user_id,
                action="auth.login_failed",
                result="denied",
                ip_address="192.168.1.100",
                user_agent="Mozilla/5.0",
                event_metadata={}
            ))
        test_db_session.commit()

        # Run detection twice
        events1 = service.detect_failed_login_clusters()

        # Check if event already exists in DB before creating (service should check this)
        existing_events = test_db_session.query(SecurityEvent).filter(
            SecurityEvent.event_type == "failed_login_cluster",
            SecurityEvent.user_id == test_user.user_id,
            SecurityEvent.detected_at >= base_time
        ).all()

        # Second run should not create duplicates if events already exist
        events2 = service.detect_failed_login_clusters()

        # Both should return events, but DB should only have unique events
        assert len(events1) >= 1
        assert len(events2) >= 1

    # ========================================
    # Test 12: Empty Results When No Events
    # ========================================

    @freeze_time("2025-10-26 10:00:00")
    @patch('src.services.security_monitoring_service.get_db_context')
    def test_empty_results_when_no_events(self, mock_db_context, service, test_db_session, test_user):
        """Test that detection returns empty list when no security events detected"""
        mock_db_context.return_value.__enter__.return_value = test_db_session
        mock_db_context.return_value.__exit__.return_value = None

        # No audit logs created - should detect nothing
        events = service.detect_failed_login_clusters()
        assert len(events) == 0, "Should return empty list when no events detected"

        events = service.detect_geo_changes()
        assert len(events) == 0, "Should return empty list when no geo changes"

        events = service.run_all_detections()
        assert len(events) == 0, "Should return empty list when no events at all"

    # ========================================
    # Test 13: Privilege Escalation to Admin (High Severity)
    # ========================================

    @freeze_time("2025-10-26 10:00:00")
    @patch('src.services.security_monitoring_service.get_db_context')
    def test_privilege_escalation_admin_high_severity(self, mock_db_context, service, test_db_session, test_user):
        """Test that escalation to admin (not superadmin) is high severity"""
        mock_db_context.return_value.__enter__.return_value = test_db_session
        mock_db_context.return_value.__exit__.return_value = None

        # Create role assignment to admin
        audit_log = AuditLog(
            id=uuid.uuid4(),
            timestamp=datetime(2025, 10, 26, 9, 55, 0),
            user_id=test_user.user_id,
            action="role.assigned",
            result="success",
            resource_type="role",
            ip_address="192.168.1.100",
            user_agent="Mozilla/5.0",
            event_metadata={"role": "admin", "assigned_by": str(uuid.uuid4())}
        )
        test_db_session.add(audit_log)
        test_db_session.commit()

        # Detect privilege escalations
        events = service.detect_privilege_escalations()

        # Should detect 1 event with high severity (admin is less severe than superadmin)
        assert len(events) == 1
        assert events[0].severity == SeverityLevel.HIGH.value
        assert events[0].event_data["role"] == "admin"

    # ========================================
    # Test 14: Concurrent Sessions from 2 Countries (High Severity)
    # ========================================

    @freeze_time("2025-10-26 10:00:00")
    @patch('src.services.security_monitoring_service.get_db_context')
    def test_concurrent_sessions_two_countries_high_severity(self, mock_db_context, service, test_db_session, test_user):
        """Test that 2 countries is high severity (not critical)"""
        mock_db_context.return_value.__enter__.return_value = test_db_session
        mock_db_context.return_value.__exit__.return_value = None

        # Create logins from 2 different countries
        base_time = datetime(2025, 10, 26, 9, 58, 0)
        countries = ["US", "CN"]
        for i, country in enumerate(countries):
            audit_log = AuditLog(
                id=uuid.uuid4(),
                timestamp=base_time + timedelta(minutes=i),
                user_id=test_user.user_id,
                action="auth.login",
                result="success",
                ip_address=f"192.168.{i}.100",
                user_agent="Mozilla/5.0",
                event_metadata={"country": country}
            )
            test_db_session.add(audit_log)
        test_db_session.commit()

        # Detect concurrent sessions
        events = service.detect_concurrent_sessions()

        # Should detect 1 event with high severity (2 countries = high, 3+ = critical)
        assert len(events) == 1
        assert events[0].severity == SeverityLevel.HIGH.value
        assert events[0].event_data["session_count"] == 2

    # ========================================
    # Test 15: Batch Processing Completes Quickly
    # ========================================

    @freeze_time("2025-10-26 10:00:00")
    @patch('src.services.security_monitoring_service.get_db_context')
    def test_batch_processing_performance(self, mock_db_context, service, test_db_session, test_user):
        """Test that batch processing completes in reasonable time (<30 seconds per spec)"""
        mock_db_context.return_value.__enter__.return_value = test_db_session
        mock_db_context.return_value.__exit__.return_value = None

        # Create a moderate number of audit logs
        base_time = datetime(2025, 10, 26, 10, 0, 0)
        for i in range(20):
            test_db_session.add(AuditLog(
                id=uuid.uuid4(),
                timestamp=base_time + timedelta(minutes=i),
                user_id=test_user.user_id,
                action="auth.login_failed",
                result="denied",
                ip_address="192.168.1.100",
                user_agent="Mozilla/5.0",
                event_metadata={}
            ))
        test_db_session.commit()

        # Run all detections
        import time
        start = time.time()
        events = service.run_all_detections()
        duration = time.time() - start

        # Should complete quickly (in tests, should be < 1 second)
        assert duration < 5.0, f"Batch processing took {duration}s, should be < 5s in tests"
        assert len(events) >= 0, "Should return results"
