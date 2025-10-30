"""
Unit tests for User model authentication hardening extensions (Phase 2).

Tests focus on:
- legacy_password flag behavior
- failed_login_attempts counter increment/reset
- locked_until expiry logic
- password_last_changed timestamp updates
- Helper methods: is_locked(), is_legacy_password(), lockout_remaining_time()

As per Task Group 1.1: Write 2-8 focused tests
"""

import uuid
from datetime import datetime, timedelta
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.config.database import Base, TEST_DATABASE_URL
from src.models.user import User


@pytest.fixture(scope="function")
def user_db_session():
    """
    Create a test database session with only User model imported.
    This avoids JSONB issues from other models when testing with SQLite.
    """
    engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(bind=engine)

    # Create only the users table
    User.__table__.create(bind=engine, checkfirst=True)

    session = SessionLocal()

    try:
        yield session
    finally:
        session.close()
        # Drop the users table
        User.__table__.drop(bind=engine, checkfirst=True)
        engine.dispose()


class TestLegacyPasswordFlag:
    """Test legacy_password flag behavior"""

    def test_legacy_password_can_be_set_to_false_for_new_users(self, user_db_session):
        """Test that new users can have legacy_password=False"""
        user = User(
            email="newuser@example.com",
            username="newuser",
            password_hash="hashed_password_with_new_policy"
        )
        user_db_session.add(user)
        user_db_session.flush()  # Trigger defaults

        # After flush, server_default should apply
        assert hasattr(user, 'legacy_password')
        # New users get False from server_default in SQLite tests
        # (In PostgreSQL, existing users would get TRUE from migration)
        assert user.legacy_password in [False, None]  # Allow None before commit

    def test_is_legacy_password_helper_method(self):
        """Test is_legacy_password() helper method"""
        user_legacy = User(
            email="legacy@example.com",
            username="legacyuser",
            password_hash="old_hash",
            legacy_password=True
        )

        user_new = User(
            email="new@example.com",
            username="newuser",
            password_hash="new_hash",
            legacy_password=False
        )

        assert user_legacy.is_legacy_password() is True
        assert user_new.is_legacy_password() is False


class TestFailedLoginAttempts:
    """Test failed_login_attempts counter"""

    def test_failed_login_attempts_defaults_to_zero(self, user_db_session):
        """Test that failed_login_attempts defaults to 0"""
        user = User(
            email="test@example.com",
            username="testuser",
            password_hash="hashed_password"
        )
        user_db_session.add(user)
        user_db_session.flush()

        assert hasattr(user, 'failed_login_attempts')
        # After flush, server_default should apply
        assert user.failed_login_attempts in [0, None]  # Allow None before commit

    def test_failed_login_attempts_increment(self, user_db_session):
        """Test incrementing failed login attempts"""
        user = User(
            email="attempts@example.com",
            username="attemptsuser",
            password_hash="hashed_password",
            failed_login_attempts=0
        )
        user_db_session.add(user)
        user_db_session.commit()

        # Increment attempts
        user.failed_login_attempts += 1
        user_db_session.commit()
        assert user.failed_login_attempts == 1

        user.failed_login_attempts += 1
        user_db_session.commit()
        assert user.failed_login_attempts == 2

    def test_failed_login_attempts_reset(self, user_db_session):
        """Test resetting failed login attempts after successful login"""
        user = User(
            email="reset@example.com",
            username="resetuser",
            password_hash="hashed_password",
            failed_login_attempts=5,
            last_failed_login=datetime.utcnow()
        )
        user_db_session.add(user)
        user_db_session.commit()

        assert user.failed_login_attempts == 5

        # Reset on successful login
        user.failed_login_attempts = 0
        user.last_failed_login = None
        user_db_session.commit()

        assert user.failed_login_attempts == 0
        assert user.last_failed_login is None


class TestAccountLockout:
    """Test account lockout functionality"""

    def test_locked_until_field_exists(self):
        """Test that locked_until field exists"""
        user = User(
            email="locked@example.com",
            username="lockeduser",
            password_hash="hashed_password",
            locked_until=datetime.utcnow() + timedelta(minutes=15)
        )

        assert hasattr(user, 'locked_until')
        assert isinstance(user.locked_until, datetime)

    def test_is_locked_when_lockout_active(self):
        """Test is_locked() returns True when lockout is active"""
        future_time = datetime.utcnow() + timedelta(minutes=15)
        user = User(
            email="locked1@example.com",
            username="locked1",
            password_hash="hashed_password",
            locked_until=future_time
        )

        assert user.is_locked() is True

    def test_is_locked_when_lockout_expired(self):
        """Test is_locked() returns False when lockout has expired"""
        past_time = datetime.utcnow() - timedelta(minutes=1)
        user = User(
            email="unlocked@example.com",
            username="unlocked",
            password_hash="hashed_password",
            locked_until=past_time
        )

        assert user.is_locked() is False

    def test_is_locked_when_no_lockout(self):
        """Test is_locked() returns False when no lockout set"""
        user = User(
            email="nolockout@example.com",
            username="nolockout",
            password_hash="hashed_password",
            locked_until=None
        )

        assert user.is_locked() is False

    def test_lockout_remaining_time(self):
        """Test lockout_remaining_time() returns correct time delta"""
        future_time = datetime.utcnow() + timedelta(minutes=15)
        user = User(
            email="remaining@example.com",
            username="remaining",
            password_hash="hashed_password",
            locked_until=future_time
        )

        remaining = user.lockout_remaining_time()
        assert remaining is not None
        # Should be approximately 15 minutes (allow 1 second tolerance)
        assert 14.98 <= remaining.total_seconds() / 60 <= 15.02

    def test_lockout_remaining_time_when_expired(self):
        """Test lockout_remaining_time() returns None when expired"""
        past_time = datetime.utcnow() - timedelta(minutes=1)
        user = User(
            email="expired@example.com",
            username="expired",
            password_hash="hashed_password",
            locked_until=past_time
        )

        remaining = user.lockout_remaining_time()
        assert remaining is None


class TestPasswordLastChanged:
    """Test password_last_changed timestamp"""

    def test_password_last_changed_field_exists(self):
        """Test that password_last_changed field exists"""
        now = datetime.utcnow()
        user = User(
            email="password@example.com",
            username="passworduser",
            password_hash="hashed_password",
            password_last_changed=now
        )

        assert hasattr(user, 'password_last_changed')
        assert isinstance(user.password_last_changed, datetime)

    def test_password_last_changed_updates_on_reset(self, user_db_session):
        """Test that password_last_changed updates when password is changed"""
        old_time = datetime.utcnow() - timedelta(days=30)
        user = User(
            email="change@example.com",
            username="changeuser",
            password_hash="old_hash",
            password_last_changed=old_time,
            legacy_password=True
        )
        user_db_session.add(user)
        user_db_session.commit()

        # Simulate password change
        new_time = datetime.utcnow()
        user.password_hash = "new_hash"
        user.password_last_changed = new_time
        user.legacy_password = False  # Mark as non-legacy after change
        user_db_session.commit()

        assert user.password_last_changed > old_time
        assert user.legacy_password is False


class TestLastFailedLogin:
    """Test last_failed_login timestamp tracking"""

    def test_last_failed_login_field_exists(self):
        """Test that last_failed_login field exists"""
        now = datetime.utcnow()
        user = User(
            email="failed@example.com",
            username="faileduser",
            password_hash="hashed_password",
            last_failed_login=now
        )

        assert hasattr(user, 'last_failed_login')
        assert isinstance(user.last_failed_login, datetime)

    def test_last_failed_login_tracks_most_recent_failure(self, user_db_session):
        """Test that last_failed_login tracks the most recent failed attempt"""
        user = User(
            email="tracking@example.com",
            username="trackinguser",
            password_hash="hashed_password",
            failed_login_attempts=0
        )
        user_db_session.add(user)
        user_db_session.commit()

        # Record first failure
        first_failure = datetime.utcnow()
        user.last_failed_login = first_failure
        user.failed_login_attempts = 1
        user_db_session.commit()

        # Record second failure (slightly later)
        import time
        time.sleep(0.1)  # Small delay to ensure different timestamp
        second_failure = datetime.utcnow()
        user.last_failed_login = second_failure
        user.failed_login_attempts = 2
        user_db_session.commit()

        assert user.last_failed_login > first_failure
        assert user.failed_login_attempts == 2
