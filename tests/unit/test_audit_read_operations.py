"""
Unit Tests for Enhanced Audit Logging (Read Operations)

Task Group 12 - Phase 2: Enhanced Audit Logging
Tests read operation logging functionality.

Test Coverage:
- conversation.read logged
- message.read logged
- user.read logged
- Health checks NOT logged
- Keep-alive NOT logged
- Async logging (non-blocking)
- Log contains correct fields
- Exclusion paths work correctly
"""

import uuid
import pytest
from datetime import datetime
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from src.config.database import TEST_DATABASE_URL
from src.models.user import User
from src.models.audit_log import AuditLog
from src.observability.audit_logger import AuditLogger
from src.api.middleware.audit_middleware import (
    should_log_read_operation,
    map_endpoint_to_resource_type
)


@pytest.fixture(scope="function")
def audit_db_session():
    """
    Create a test database session with User and AuditLog models.
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

    # Create required tables
    User.__table__.create(bind=engine, checkfirst=True)
    AuditLog.__table__.create(bind=engine, checkfirst=True)

    session = SessionLocal()

    try:
        yield session
    finally:
        session.close()
        # Drop tables in reverse dependency order
        AuditLog.__table__.drop(bind=engine, checkfirst=True)
        User.__table__.drop(bind=engine, checkfirst=True)
        engine.dispose()


class TestReadOperationLogging:
    """Test suite for read operation audit logging."""

    @pytest.mark.asyncio
    async def test_log_read_operation_conversation_read(self, audit_db_session):
        """Test that conversation.read is logged correctly."""
        # Arrange
        user_id = uuid.uuid4()
        conversation_id = uuid.uuid4()
        ip_address = "192.168.1.100"
        user_agent = "Mozilla/5.0"

        # Act
        await AuditLogger.log_read_operation(
            user_id=user_id,
            resource_type="conversation",
            resource_id=conversation_id,
            ip_address=ip_address,
            user_agent=user_agent
        )

        # Assert
        log = audit_db_session.query(AuditLog).filter(
            AuditLog.user_id == user_id,
            AuditLog.action == "conversation.read"
        ).first()

        assert log is not None
        assert log.user_id == user_id
        assert log.action == "conversation.read"
        assert log.resource_type == "conversation"
        assert log.resource_id == conversation_id
        assert log.result == "success"
        assert log.ip_address == ip_address
        assert log.user_agent == user_agent

    @pytest.mark.asyncio
    async def test_log_read_operation_message_read(self, audit_db_session):
        """Test that message.read is logged correctly."""
        # Arrange
        user_id = uuid.uuid4()
        conversation_id = uuid.uuid4()
        ip_address = "10.0.0.5"

        # Act
        await AuditLogger.log_read_operation(
            user_id=user_id,
            resource_type="message",
            resource_id=conversation_id,
            ip_address=ip_address
        )

        # Assert
        log = audit_db_session.query(AuditLog).filter(
            AuditLog.user_id == user_id,
            AuditLog.action == "message.read"
        ).first()

        assert log is not None
        assert log.action == "message.read"
        assert log.resource_type == "message"
        assert log.result == "success"

    @pytest.mark.asyncio
    async def test_log_read_operation_user_read(self, audit_db_session):
        """Test that user.read is logged correctly."""
        # Arrange
        user_id = uuid.uuid4()
        target_user_id = uuid.uuid4()

        # Act
        await AuditLogger.log_read_operation(
            user_id=user_id,
            resource_type="user",
            resource_id=target_user_id,
            ip_address="203.0.113.10"
        )

        # Assert
        log = audit_db_session.query(AuditLog).filter(
            AuditLog.user_id == user_id,
            AuditLog.action == "user.read"
        ).first()

        assert log is not None
        assert log.action == "user.read"
        assert log.resource_type == "user"
        assert log.resource_id == target_user_id

    @pytest.mark.asyncio
    async def test_log_read_operation_contains_timestamp(self, audit_db_session):
        """Test that log entry contains a timestamp."""
        # Arrange
        user_id = uuid.uuid4()
        resource_id = uuid.uuid4()

        # Act
        await AuditLogger.log_read_operation(
            user_id=user_id,
            resource_type="conversation",
            resource_id=resource_id
        )

        # Assert
        log = audit_db_session.query(AuditLog).filter(
            AuditLog.user_id == user_id
        ).first()

        assert log is not None
        assert log.timestamp is not None
        assert isinstance(log.timestamp, datetime)

    @pytest.mark.asyncio
    async def test_log_read_operation_with_metadata(self, audit_db_session):
        """Test that metadata is stored correctly."""
        # Arrange
        user_id = uuid.uuid4()
        resource_id = uuid.uuid4()
        metadata = {
            "endpoint": "/api/v1/conversations/123",
            "query_params": {"include": "messages"}
        }

        # Act
        await AuditLogger.log_read_operation(
            user_id=user_id,
            resource_type="conversation",
            resource_id=resource_id,
            metadata=metadata
        )

        # Assert
        log = audit_db_session.query(AuditLog).filter(
            AuditLog.user_id == user_id
        ).first()

        assert log is not None
        assert log.event_metadata == metadata
        assert log.event_metadata["endpoint"] == "/api/v1/conversations/123"

    @pytest.mark.asyncio
    async def test_log_read_operation_async_non_blocking(self, audit_db_session):
        """Test that logging is async and non-blocking."""
        # This test verifies the log_read_operation method exists
        # and can be called asynchronously

        # Arrange
        user_id = uuid.uuid4()
        resource_id = uuid.uuid4()

        # Act - should not raise exception
        start_time = datetime.utcnow()

        await AuditLogger.log_read_operation(
            user_id=user_id,
            resource_type="conversation",
            resource_id=resource_id
        )

        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()

        # Assert - should complete quickly (under 1 second)
        assert duration < 1.0

    @pytest.mark.asyncio
    async def test_log_read_operation_handles_none_user_id(self, audit_db_session):
        """Test that logging works with None user_id (anonymous reads)."""
        # Arrange
        resource_id = uuid.uuid4()

        # Act
        await AuditLogger.log_read_operation(
            user_id=None,
            resource_type="conversation",
            resource_id=resource_id
        )

        # Assert
        log = audit_db_session.query(AuditLog).filter(
            AuditLog.action == "conversation.read",
            AuditLog.resource_id == resource_id
        ).first()

        assert log is not None
        assert log.user_id is None


class TestAuditMiddlewareExclusions:
    """Test suite for audit middleware path exclusions."""

    def test_health_check_not_logged(self):
        """Test that /health endpoint is NOT logged."""
        # Arrange
        path = "/api/v1/health"
        method = "GET"

        # Act
        result = should_log_read_operation(path, method)

        # Assert
        assert result is False

    def test_metrics_endpoint_not_logged(self):
        """Test that /metrics endpoint is NOT logged."""
        # Arrange
        path = "/api/v1/metrics"
        method = "GET"

        # Act
        result = should_log_read_operation(path, method)

        # Assert
        assert result is False

    def test_keep_alive_not_logged(self):
        """Test that /auth/session/keep-alive is NOT logged."""
        # Arrange
        path = "/api/v1/auth/session/keep-alive"
        method = "POST"

        # Act
        result = should_log_read_operation(path, method)

        # Assert
        assert result is False

    def test_static_assets_not_logged(self):
        """Test that static asset requests are NOT logged."""
        # Arrange
        paths = [
            "/static/css/main.css",
            "/assets/js/app.js",
            "/favicon.ico"
        ]

        # Act & Assert
        for path in paths:
            result = should_log_read_operation(path, "GET")
            assert result is False, f"Path {path} should not be logged"

    def test_conversation_get_is_logged(self):
        """Test that GET /conversations/{id} IS logged."""
        # Arrange
        path = "/api/v1/conversations/550e8400-e29b-41d4-a716-446655440000"
        method = "GET"

        # Act
        result = should_log_read_operation(path, method)

        # Assert
        assert result is True

    def test_messages_get_is_logged(self):
        """Test that GET /conversations/{id}/messages IS logged."""
        # Arrange
        path = "/api/v1/conversations/550e8400-e29b-41d4-a716-446655440000/messages"
        method = "GET"

        # Act
        result = should_log_read_operation(path, method)

        # Assert
        assert result is True

    def test_user_get_is_logged(self):
        """Test that GET /users/{id} IS logged."""
        # Arrange
        path = "/api/v1/users/550e8400-e29b-41d4-a716-446655440000"
        method = "GET"

        # Act
        result = should_log_read_operation(path, method)

        # Assert
        assert result is True

    def test_admin_users_list_is_logged(self):
        """Test that GET /admin/users IS logged."""
        # Arrange
        path = "/api/v1/admin/users"
        method = "GET"

        # Act
        result = should_log_read_operation(path, method)

        # Assert
        assert result is True

    def test_post_requests_not_logged_by_read_middleware(self):
        """Test that POST requests are NOT logged by read middleware."""
        # Arrange
        path = "/api/v1/conversations"
        method = "POST"

        # Act
        result = should_log_read_operation(path, method)

        # Assert
        # POST/PUT/DELETE are logged by existing write operation logging
        assert result is False


class TestResourceTypeMapping:
    """Test suite for endpoint to resource type mapping."""

    def test_map_endpoint_to_resource_type_conversation(self):
        """Test mapping conversation endpoint to resource type."""
        # Arrange
        paths = [
            "/api/v1/conversations/550e8400-e29b-41d4-a716-446655440000",
            "/conversations/550e8400-e29b-41d4-a716-446655440000"
        ]

        # Act & Assert
        for path in paths:
            resource_type, resource_id = map_endpoint_to_resource_type(path)
            assert resource_type == "conversation"
            assert resource_id == "550e8400-e29b-41d4-a716-446655440000"

    def test_map_endpoint_to_resource_type_message(self):
        """Test mapping message endpoint to resource type."""
        # Arrange
        path = "/api/v1/conversations/550e8400-e29b-41d4-a716-446655440000/messages"

        # Act
        resource_type, resource_id = map_endpoint_to_resource_type(path)

        # Assert
        assert resource_type == "message"
        assert resource_id == "550e8400-e29b-41d4-a716-446655440000"

    def test_map_endpoint_to_resource_type_user(self):
        """Test mapping user endpoint to resource type."""
        # Arrange
        paths = [
            "/api/v1/users/550e8400-e29b-41d4-a716-446655440000",
            "/api/v1/admin/users"
        ]

        # Act & Assert
        for path in paths:
            resource_type, resource_id = map_endpoint_to_resource_type(path)
            assert resource_type == "user"

    def test_map_endpoint_to_resource_type_unknown(self):
        """Test mapping unknown endpoint returns None."""
        # Arrange
        path = "/api/v1/unknown/endpoint"

        # Act
        resource_type, resource_id = map_endpoint_to_resource_type(path)

        # Assert
        assert resource_type is None
        assert resource_id is None
