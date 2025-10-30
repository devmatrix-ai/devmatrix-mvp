"""
Unit Tests for LogArchivalService

Tests log archival, restoration, and purging functionality.
Phase 2 - Task Group 15: Log Retention & Management
"""

import json
import gzip
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call
from uuid import uuid4

import pytest
from freezegun import freeze_time
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.services.log_archival_service import LogArchivalService
from src.models.audit_log import AuditLog
from src.models.security_event import SecurityEvent
from src.models.alert_history import AlertHistory
from src.config.database import get_db_context, DatabaseConfig, Base


# ========================================
# Fixtures
# ========================================

@pytest.fixture(scope="function")
def db_setup():
    """Setup in-memory SQLite database for testing."""
    # Use in-memory SQLite
    DatabaseConfig._engine = None
    DatabaseConfig._session_factory = None

    engine = create_engine("sqlite:///:memory:", echo=False)
    DatabaseConfig._engine = engine

    # Create sessionmaker
    Session = sessionmaker(bind=engine)
    DatabaseConfig._session_factory = Session

    # Create ONLY the tables we need for these tests
    AuditLog.__table__.create(bind=engine, checkfirst=True)
    SecurityEvent.__table__.create(bind=engine, checkfirst=True)
    AlertHistory.__table__.create(bind=engine, checkfirst=True)

    yield

    # Cleanup
    AuditLog.__table__.drop(bind=engine, checkfirst=True)
    SecurityEvent.__table__.drop(bind=engine, checkfirst=True)
    AlertHistory.__table__.drop(bind=engine, checkfirst=True)

    DatabaseConfig._engine = None
    DatabaseConfig._session_factory = None


@pytest.fixture
def log_archival_service():
    """Create LogArchivalService instance."""
    return LogArchivalService()


@pytest.fixture
def sample_audit_logs(db_setup):
    """Create sample audit logs for testing."""
    with get_db_context() as db:
        # Create logs from 17 days ago (mid-October, for October archival test)
        old_date = datetime.utcnow() - timedelta(days=17)  # Mid-October

        logs = []
        for i in range(5):
            log = AuditLog(
                timestamp=old_date,
                user_id=uuid4(),
                action="conversation.read",
                resource_type="conversation",
                resource_id=uuid4(),
                result="success",
                ip_address="192.168.1.1",
                user_agent="Mozilla/5.0",
                event_metadata={"test": f"data_{i}"}
            )
            db.add(log)
            logs.append(log)

        db.commit()

        # Refresh to get IDs
        for log in logs:
            db.refresh(log)

        return [log.to_dict() for log in logs]


@pytest.fixture
def sample_security_events(db_setup):
    """Create sample security events for testing."""
    with get_db_context() as db:
        # Create events from 95 days ago (should be archived)
        old_date = datetime.utcnow() - timedelta(days=17)  # Mid-October

        events = []
        for i in range(3):
            event = SecurityEvent(
                event_type="failed_login_cluster",
                severity="high",
                user_id=uuid4(),
                event_data={"attempts": 5 + i},
                detected_at=old_date,
                resolved=False
            )
            db.add(event)
            events.append(event)

        db.commit()

        # Refresh to get IDs
        for event in events:
            db.refresh(event)

        return [event.to_dict() for event in events]




@pytest.fixture
def old_audit_logs_for_purge(db_setup):
    """Create audit logs 95 days old for purge testing."""
    with get_db_context() as db:
        # Create logs from 95 days ago (should be purged)
        old_date = datetime.utcnow() - timedelta(days=95)

        logs = []
        for i in range(5):
            log = AuditLog(
                timestamp=old_date,
                user_id=uuid4(),
                action="conversation.read",
                resource_type="conversation",
                resource_id=uuid4(),
                result="success",
                ip_address="192.168.1.1",
                user_agent="Mozilla/5.0",
                event_metadata={"test": f"data_{i}"}
            )
            db.add(log)
            logs.append(log)

        db.commit()

        for log in logs:
            db.refresh(log)

        return [log.to_dict() for log in logs]


@pytest.fixture
def old_security_events_for_purge(db_setup):
    """Create security events 95 days old for purge testing."""
    with get_db_context() as db:
        # Create events from 95 days ago (should be purged)
        old_date = datetime.utcnow() - timedelta(days=95)

        events = []
        for i in range(3):
            event = SecurityEvent(
                event_type="failed_login_cluster",
                severity="high",
                user_id=uuid4(),
                event_data={"attempts": 5 + i},
                detected_at=old_date,
                resolved=False
            )
            db.add(event)
            events.append(event)

        db.commit()

        for event in events:
            db.refresh(event)

        return [event.to_dict() for event in events]


# ========================================
# Test: Archive Audit Logs
# ========================================

@freeze_time("2025-11-01")
def test_archive_audit_logs_creates_gzipped_json(log_archival_service, sample_audit_logs):
    """Test that archive_audit_logs creates gzipped JSON file."""
    with patch.object(log_archival_service, 'upload_to_s3', return_value=True) as mock_upload:
        # Archive October 2025 logs
        manifest = log_archival_service.archive_audit_logs(2025, 10)

        # Verify manifest
        assert manifest is not None
        assert manifest["table_name"] == "audit_logs"
        assert manifest["year"] == 2025
        assert manifest["month"] == 10
        assert manifest["row_count"] == 5
        assert manifest["file_size"] > 0
        assert "checksum" in manifest
        assert len(manifest["checksum"]) == 64  # SHA256 hex length

        # Verify S3 upload was called
        mock_upload.assert_called_once()

        # Verify file was created
        args = mock_upload.call_args[0]
        file_path = args[0]
        assert Path(file_path).exists()
        assert file_path.endswith(".json.gz")

        # Verify file can be decompressed and parsed
        with gzip.open(file_path, 'rt') as f:
            data = json.load(f)
            assert len(data) == 5
            assert data[0]["action"] == "conversation.read"

        # Cleanup
        Path(file_path).unlink(missing_ok=True)


@freeze_time("2025-11-01")
def test_archive_security_events_creates_gzipped_json(log_archival_service, sample_security_events):
    """Test that archive_security_events creates gzipped JSON file."""
    with patch.object(log_archival_service, 'upload_to_s3', return_value=True) as mock_upload:
        # Archive October 2025 events
        manifest = log_archival_service.archive_security_events(2025, 10)

        # Verify manifest
        assert manifest is not None
        assert manifest["table_name"] == "security_events"
        assert manifest["year"] == 2025
        assert manifest["month"] == 10
        assert manifest["row_count"] == 3
        assert manifest["file_size"] > 0
        assert "checksum" in manifest

        # Verify S3 upload was called
        mock_upload.assert_called_once()

        # Verify file was created
        args = mock_upload.call_args[0]
        file_path = args[0]
        assert Path(file_path).exists()

        # Verify file can be decompressed and parsed
        with gzip.open(file_path, 'rt') as f:
            data = json.load(f)
            assert len(data) == 3
            assert data[0]["event_type"] == "failed_login_cluster"

        # Cleanup
        Path(file_path).unlink(missing_ok=True)


# ========================================
# Test: Manifest File Creation
# ========================================

def test_generate_manifest_with_checksum(log_archival_service):
    """Test that generate_manifest creates manifest with checksum."""
    data = [
        {"id": "123", "action": "test"},
        {"id": "456", "action": "test2"}
    ]

    manifest = log_archival_service.generate_manifest(
        data=data,
        table_name="audit_logs",
        year=2025,
        month=10,
        file_path="/tmp/test.json.gz"
    )

    assert manifest["table_name"] == "audit_logs"
    assert manifest["year"] == 2025
    assert manifest["month"] == 10
    assert manifest["row_count"] == 2
    assert manifest["file_size"] == 0  # File doesn't exist
    assert "checksum" in manifest
    assert len(manifest["checksum"]) == 64  # SHA256


# ========================================
# Test: S3 Upload (Mocked)
# ========================================

@patch('boto3.client')
def test_upload_to_s3_success(mock_boto_client, log_archival_service):
    """Test S3 upload with mocked boto3."""
    # Mock S3 client
    mock_s3 = MagicMock()
    mock_boto_client.return_value = mock_s3

    # Create temporary file
    temp_file = Path("/tmp/test_upload.json.gz")
    temp_file.write_text("test data")

    try:
        # Upload
        success = log_archival_service.upload_to_s3(
            str(temp_file),
            "audit-logs/2025/10/audit_logs_2025_10.json.gz"
        )

        # Verify upload was called
        assert success is True
        mock_s3.upload_file.assert_called_once()

    finally:
        # Cleanup
        temp_file.unlink(missing_ok=True)


@patch('boto3.client')
def test_upload_to_s3_failure(mock_boto_client, log_archival_service):
    """Test S3 upload failure handling."""
    # Mock S3 client to raise exception
    mock_s3 = MagicMock()
    mock_s3.upload_file.side_effect = Exception("S3 upload failed")
    mock_boto_client.return_value = mock_s3

    # Create temporary file
    temp_file = Path("/tmp/test_upload.json.gz")
    temp_file.write_text("test data")

    try:
        # Upload should fail gracefully
        success = log_archival_service.upload_to_s3(
            str(temp_file),
            "audit-logs/2025/10/audit_logs_2025_10.json.gz"
        )

        assert success is False

    finally:
        # Cleanup
        temp_file.unlink(missing_ok=True)


# ========================================
# Test: Purge Old Logs
# ========================================

@freeze_time("2025-11-01")
def test_purge_old_logs_deletes_records_DISABLED():  # Disabled - needs different fixture
    """Test that purge_old_logs deletes records older than retention period."""
    # Purge logs older than 90 days
    rows_deleted = log_archival_service.purge_old_logs("audit_logs", 90)

    # Verify 5 rows were deleted (all sample logs are 95 days old)
    assert rows_deleted == 5

    # Verify logs are gone
    with get_db_context() as db:
        remaining = db.query(AuditLog).count()
        assert remaining == 0


@freeze_time("2025-11-01")
def test_purge_old_security_events_DISABLED():  # Disabled - needs different fixture
    """Test purging old security events."""
    # Purge events older than 90 days
    rows_deleted = log_archival_service.purge_old_logs("security_events", 90)

    # Verify 3 rows were deleted
    assert rows_deleted == 3

    # Verify events are gone
    with get_db_context() as db:
        remaining = db.query(SecurityEvent).count()
        assert remaining == 0


@freeze_time("2025-11-01")
def test_purge_respects_retention_period(log_archival_service, db_setup):
    """Test that purge respects retention period."""
    with get_db_context() as db:
        # Create logs at different ages
        db.add(AuditLog(
            timestamp=datetime.utcnow() - timedelta(days=95),  # Should be deleted
            action="old", result="success"
        ))
        db.add(AuditLog(
            timestamp=datetime.utcnow() - timedelta(days=85),  # Should be kept
            action="recent", result="success"
        ))
        db.commit()

    # Purge logs older than 90 days
    rows_deleted = log_archival_service.purge_old_logs("audit_logs", 90)

    # Only 1 row should be deleted
    assert rows_deleted == 1

    # Verify recent log still exists
    with get_db_context() as db:
        remaining = db.query(AuditLog).filter(AuditLog.action == "recent").first()
        assert remaining is not None


# ========================================
# Test: Restore Logs
# ========================================

@patch('boto3.client')
def test_restore_logs_creates_temporary_table(mock_boto_client, log_archival_service, db_setup):
    """Test that restore_logs creates temporary table."""
    # Mock S3 download
    mock_s3 = MagicMock()

    def mock_download(bucket, s3_key, file_path):
        # Create mock gzipped JSON file
        data = [
            {"id": str(uuid4()), "action": "restored_log_1", "result": "success"},
            {"id": str(uuid4()), "action": "restored_log_2", "result": "success"}
        ]
        with gzip.open(file_path, 'wt') as f:
            json.dump(data, f)

    mock_s3.download_file = mock_download
    mock_boto_client.return_value = mock_s3

    # Restore logs
    temp_table = log_archival_service.restore_logs(
        "audit-logs/2025/10/audit_logs_2025_10.json.gz"
    )

    # Verify temporary table name
    assert temp_table.startswith("audit_logs_restored_")

    # Verify data was restored (using raw SQL since it's a temp table)
    with get_db_context() as db:
        result = db.execute(f"SELECT COUNT(*) FROM {temp_table}").scalar()
        assert result == 2


# ========================================
# Test: Auto-purge Temporary Tables
# ========================================

def test_purge_temp_tables_deletes_old_tables(log_archival_service, db_setup):
    """Test that purge_temp_tables deletes tables older than 7 days."""
    with get_db_context() as db:
        # Create temporary table (simulated with regular table for testing)
        old_table_name = f"audit_logs_restored_{int((datetime.utcnow() - timedelta(days=8)).timestamp())}"

        # Create table with timestamp in name indicating it's 8 days old
        db.execute(f"""
            CREATE TABLE {old_table_name} (
                id TEXT PRIMARY KEY,
                action TEXT,
                result TEXT
            )
        """)
        db.commit()

    # Purge old temp tables (>7 days)
    tables_purged = log_archival_service.purge_temp_tables()

    # Verify table was purged
    assert tables_purged == 1


# ========================================
# Test: Admin Permissions
# ========================================

def test_archive_requires_no_special_permissions(log_archival_service):
    """Test that archival can be triggered by admin (no permission check in service)."""
    # Archive should work without errors (permission checks are in API layer)
    with patch.object(log_archival_service, 'upload_to_s3', return_value=True):
        # This should not raise any exceptions
        manifest = log_archival_service.archive_audit_logs(2025, 10)
        assert manifest is not None


def test_restore_requires_no_special_permissions(log_archival_service):
    """Test that restoration can be triggered by admin (no permission check in service)."""
    with patch('boto3.client') as mock_boto:
        mock_s3 = MagicMock()

        def mock_download(bucket, key, path):
            # Create mock gzipped JSON file
            data = [{"id": str(uuid4()), "action": "test", "result": "success"}]
            with gzip.open(path, 'wt') as f:
                json.dump(data, f)

        mock_s3.download_file = mock_download
        mock_boto.return_value = mock_s3

        # This should not raise any exceptions
        temp_table = log_archival_service.restore_logs(
            "audit-logs/2025/10/audit_logs_2025_10.json.gz"
        )
        assert temp_table is not None


# ========================================
# Test: Graceful Degradation
# ========================================

@patch('boto3.client')
def test_graceful_degradation_when_s3_not_configured(mock_boto_client, db_setup):
    """Test graceful degradation when S3 is not configured."""
    # Mock boto3 to raise exception (S3 not configured)
    mock_boto_client.side_effect = Exception("AWS credentials not configured")

    # Create service
    service = LogArchivalService()

    # Archive should fail gracefully
    with patch.object(service, 'upload_to_s3', return_value=False):
        manifest = service.archive_audit_logs(2025, 10)
        # Should still return manifest even if upload fails
        assert manifest is not None
        assert manifest["row_count"] == 0  # No data to archive


def test_archive_with_no_data_returns_empty_manifest(log_archival_service, db_setup):
    """Test archival when there's no data to archive."""
    with patch.object(log_archival_service, 'upload_to_s3', return_value=True):
        # Archive month with no data
        manifest = log_archival_service.archive_audit_logs(2025, 10)

        # Should return manifest with 0 rows
        assert manifest is not None
        assert manifest["row_count"] == 0

@freeze_time("2025-11-01")
def test_purge_old_logs_deletes_records_new(log_archival_service, old_audit_logs_for_purge):
    """Test that purge_old_logs deletes records older than retention period."""
    # Purge logs older than 90 days
    rows_deleted = log_archival_service.purge_old_logs("audit_logs", 90)

    # Verify 5 rows were deleted (all sample logs are 95 days old)
    assert rows_deleted == 5

    # Verify logs are gone
    with get_db_context() as db:
        remaining = db.query(AuditLog).count()
        assert remaining == 0


@freeze_time("2025-11-01")
def test_purge_old_security_events_new(log_archival_service, old_security_events_for_purge):
    """Test purging old security events."""
    # Purge events older than 90 days
    rows_deleted = log_archival_service.purge_old_logs("security_events", 90)

    # Verify 3 rows were deleted
    assert rows_deleted == 3

    # Verify events are gone
    with get_db_context() as db:
        remaining = db.query(SecurityEvent).count()
        assert remaining == 0

