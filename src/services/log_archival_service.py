"""
Log Archival Service

Handles archival, restoration, and purging of audit logs, security events, and alert history.

Features:
- Archive logs to S3 in compressed JSON format
- Generate manifest files with checksums
- Restore logs from S3 to temporary tables
- Purge old logs from database
- Auto-purge temporary tables

Phase 2 - Task Group 15: Log Retention & Management
"""

import json
import gzip
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional
from uuid import UUID

from src.config.database import get_db_context
from src.config.settings import get_settings
from src.models.audit_log import AuditLog
from src.models.security_event import SecurityEvent
from src.models.alert_history import AlertHistory
from src.observability import get_logger

logger = get_logger("log_archival_service")
settings = get_settings()


class LogArchivalService:
    """
    Service for log archival, restoration, and retention management.

    Handles:
    - Archival of audit logs, security events, and alert history to S3
    - Compressed JSON (gzip) format
    - Manifest file generation with checksums
    - Restoration from S3 to temporary tables
    - Purging old logs and temporary tables

    Retention Policy:
    - Audit logs: 90 days PostgreSQL (hot), 7 years S3 (cold)
    - Security events: 90 days PostgreSQL (hot), 7 years S3 (cold)
    - Alert history: 1 year PostgreSQL (purge after 1 year)

    S3 Structure:
    - s3://bucket/audit-logs/YYYY/MM/audit_logs_YYYY_MM.json.gz
    - s3://bucket/security-events/YYYY/MM/security_events_YYYY_MM.json.gz
    - s3://bucket/alert-history/YYYY/MM/alert_history_YYYY_MM.json.gz

    Usage:
        service = LogArchivalService()

        # Archive October 2025 audit logs
        manifest = service.archive_audit_logs(2025, 10)

        # Purge logs older than 90 days
        rows_deleted = service.purge_old_logs("audit_logs", 90)

        # Restore logs from S3
        temp_table = service.restore_logs("audit-logs/2025/10/audit_logs_2025_10.json.gz")
    """

    def __init__(self):
        """Initialize log archival service."""
        self.s3_bucket = getattr(settings, 'AWS_S3_BUCKET', None)
        self.aws_access_key_id = getattr(settings, 'AWS_ACCESS_KEY_ID', None)
        self.aws_secret_access_key = getattr(settings, 'AWS_SECRET_ACCESS_KEY', None)
        self.audit_log_retention_days = getattr(settings, 'AUDIT_LOG_RETENTION_DAYS', 90)
        self.security_event_retention_days = getattr(settings, 'SECURITY_EVENT_RETENTION_DAYS', 90)
        self.alert_history_retention_days = getattr(settings, 'ALERT_HISTORY_RETENTION_DAYS', 365)

        # Log configuration
        if self.s3_bucket:
            logger.info(f"Log archival service initialized: S3 bucket={self.s3_bucket}")
        else:
            logger.warning("Log archival service initialized: S3 not configured (archival will fail)")

    def archive_audit_logs(self, year: int, month: int) -> Dict[str, Any]:
        """
        Archive audit logs for a specific month to S3.

        Args:
            year: Year to archive (e.g., 2025)
            month: Month to archive (1-12)

        Returns:
            Manifest dictionary with metadata:
            {
                "table_name": "audit_logs",
                "year": 2025,
                "month": 10,
                "row_count": 1234,
                "file_size": 45678,
                "checksum": "sha256_hex",
                "archived_at": "2025-11-01T02:00:00Z"
            }
        """
        logger.info(f"Starting archival of audit_logs for {year}-{month:02d}")

        try:
            # Query logs for the specified month
            with get_db_context() as db:
                start_date = datetime(year, month, 1)
                if month == 12:
                    end_date = datetime(year + 1, 1, 1)
                else:
                    end_date = datetime(year, month + 1, 1)

                logs = db.query(AuditLog).filter(
                    AuditLog.timestamp >= start_date,
                    AuditLog.timestamp < end_date
                ).all()

                # Convert to dictionaries
                data = [log.to_dict() for log in logs]

            logger.info(f"Found {len(data)} audit logs for {year}-{month:02d}")

            if len(data) == 0:
                logger.warning(f"No audit logs found for {year}-{month:02d}, skipping archival")
                return {
                    "table_name": "audit_logs",
                    "year": year,
                    "month": month,
                    "row_count": 0,
                    "file_size": 0,
                    "checksum": "",
                    "archived_at": datetime.utcnow().isoformat()
                }

            # Create compressed JSON file
            file_path = self._create_archive_file(data, "audit_logs", year, month)

            # Upload to S3
            s3_key = f"audit-logs/{year}/{month:02d}/audit_logs_{year}_{month:02d}.json.gz"
            upload_success = self.upload_to_s3(file_path, s3_key)

            if not upload_success:
                logger.error(f"Failed to upload audit logs to S3: {s3_key}")

            # Generate manifest
            manifest = self.generate_manifest(data, "audit_logs", year, month, file_path)

            # Cleanup local file
            Path(file_path).unlink(missing_ok=True)

            logger.info(f"Successfully archived {len(data)} audit logs to {s3_key}")

            return manifest

        except Exception as e:
            logger.error(f"Failed to archive audit logs for {year}-{month:02d}: {str(e)}", exc_info=True)
            raise

    def archive_security_events(self, year: int, month: int) -> Dict[str, Any]:
        """
        Archive security events for a specific month to S3.

        Args:
            year: Year to archive (e.g., 2025)
            month: Month to archive (1-12)

        Returns:
            Manifest dictionary with metadata
        """
        logger.info(f"Starting archival of security_events for {year}-{month:02d}")

        try:
            # Query events for the specified month
            with get_db_context() as db:
                start_date = datetime(year, month, 1)
                if month == 12:
                    end_date = datetime(year + 1, 1, 1)
                else:
                    end_date = datetime(year, month + 1, 1)

                events = db.query(SecurityEvent).filter(
                    SecurityEvent.detected_at >= start_date,
                    SecurityEvent.detected_at < end_date
                ).all()

                # Convert to dictionaries
                data = [event.to_dict() for event in events]

            logger.info(f"Found {len(data)} security events for {year}-{month:02d}")

            if len(data) == 0:
                logger.warning(f"No security events found for {year}-{month:02d}, skipping archival")
                return {
                    "table_name": "security_events",
                    "year": year,
                    "month": month,
                    "row_count": 0,
                    "file_size": 0,
                    "checksum": "",
                    "archived_at": datetime.utcnow().isoformat()
                }

            # Create compressed JSON file
            file_path = self._create_archive_file(data, "security_events", year, month)

            # Upload to S3
            s3_key = f"security-events/{year}/{month:02d}/security_events_{year}_{month:02d}.json.gz"
            upload_success = self.upload_to_s3(file_path, s3_key)

            if not upload_success:
                logger.error(f"Failed to upload security events to S3: {s3_key}")

            # Generate manifest
            manifest = self.generate_manifest(data, "security_events", year, month, file_path)

            # Cleanup local file
            Path(file_path).unlink(missing_ok=True)

            logger.info(f"Successfully archived {len(data)} security events to {s3_key}")

            return manifest

        except Exception as e:
            logger.error(f"Failed to archive security events for {year}-{month:02d}: {str(e)}", exc_info=True)
            raise

    def purge_old_logs(self, table_name: str, days_retention: int) -> int:
        """
        Purge logs older than retention period from database.

        Args:
            table_name: Table to purge ("audit_logs", "security_events", "alert_history")
            days_retention: Number of days to retain (e.g., 90)

        Returns:
            Number of rows deleted

        Raises:
            ValueError: If table_name is invalid
        """
        logger.info(f"Starting purge of {table_name} older than {days_retention} days")

        # Validate table name
        valid_tables = ["audit_logs", "security_events", "alert_history"]
        if table_name not in valid_tables:
            raise ValueError(f"Invalid table_name: {table_name}. Must be one of {valid_tables}")

        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_retention)

            with get_db_context() as db:
                if table_name == "audit_logs":
                    rows = db.query(AuditLog).filter(AuditLog.timestamp < cutoff_date).all()
                    count = len(rows)
                    for row in rows:
                        db.delete(row)

                elif table_name == "security_events":
                    rows = db.query(SecurityEvent).filter(SecurityEvent.detected_at < cutoff_date).all()
                    count = len(rows)
                    for row in rows:
                        db.delete(row)

                elif table_name == "alert_history":
                    rows = db.query(AlertHistory).filter(AlertHistory.sent_at < cutoff_date).all()
                    count = len(rows)
                    for row in rows:
                        db.delete(row)

                db.commit()

            logger.info(f"Purged {count} rows from {table_name} (older than {days_retention} days)")

            return count

        except Exception as e:
            logger.error(f"Failed to purge {table_name}: {str(e)}", exc_info=True)
            raise

    def restore_logs(self, s3_key: str) -> str:
        """
        Restore logs from S3 to a temporary table.

        Creates a temporary table with name: {table_name}_restored_{timestamp}
        Table auto-purges after 7 days.

        Args:
            s3_key: S3 key of archive file (e.g., "audit-logs/2025/10/audit_logs_2025_10.json.gz")

        Returns:
            Temporary table name

        Raises:
            Exception: If download or restoration fails
        """
        logger.info(f"Starting restoration from S3: {s3_key}")

        try:
            # Download from S3
            local_file = f"/tmp/{Path(s3_key).name}"
            self.download_from_s3(s3_key, local_file)

            # Decompress and parse JSON
            with gzip.open(local_file, 'rt') as f:
                data = json.load(f)

            logger.info(f"Downloaded and decompressed {len(data)} records from {s3_key}")

            # Extract table name from S3 key
            table_name = Path(s3_key).stem.split('_')[0]  # e.g., "audit" from "audit_logs_2025_10"
            if "audit" in table_name:
                table_name = "audit_logs"
            elif "security" in table_name:
                table_name = "security_events"
            elif "alert" in table_name:
                table_name = "alert_history"

            # Create temporary table name
            temp_table_name = f"{table_name}_restored_{int(datetime.utcnow().timestamp())}"

            # Create temporary table and insert data
            with get_db_context() as db:
                # Create table structure (simplified for temp table)
                if table_name == "audit_logs":
                    db.execute(f"""
                        CREATE TABLE {temp_table_name} (
                            id TEXT PRIMARY KEY,
                            timestamp TEXT,
                            user_id TEXT,
                            action TEXT,
                            resource_type TEXT,
                            resource_id TEXT,
                            result TEXT,
                            ip_address TEXT,
                            user_agent TEXT,
                            metadata TEXT
                        )
                    """)
                elif table_name == "security_events":
                    db.execute(f"""
                        CREATE TABLE {temp_table_name} (
                            event_id TEXT PRIMARY KEY,
                            event_type TEXT,
                            severity TEXT,
                            user_id TEXT,
                            event_data TEXT,
                            detected_at TEXT,
                            resolved INTEGER,
                            resolved_at TEXT,
                            resolved_by TEXT
                        )
                    """)

                # Insert data
                for record in data:
                    if table_name == "audit_logs":
                        db.execute(f"""
                            INSERT INTO {temp_table_name}
                            (id, timestamp, user_id, action, resource_type, resource_id, result, ip_address, user_agent, metadata)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            record.get("id"),
                            record.get("timestamp"),
                            record.get("user_id"),
                            record.get("action"),
                            record.get("resource_type"),
                            record.get("resource_id"),
                            record.get("result"),
                            record.get("ip_address"),
                            record.get("user_agent"),
                            json.dumps(record.get("metadata", {}))
                        ))
                    elif table_name == "security_events":
                        db.execute(f"""
                            INSERT INTO {temp_table_name}
                            (event_id, event_type, severity, user_id, event_data, detected_at, resolved, resolved_at, resolved_by)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            record.get("event_id"),
                            record.get("event_type"),
                            record.get("severity"),
                            record.get("user_id"),
                            json.dumps(record.get("event_data", {})),
                            record.get("detected_at"),
                            1 if record.get("resolved") else 0,
                            record.get("resolved_at"),
                            record.get("resolved_by")
                        ))

                db.commit()

            # Cleanup local file
            Path(local_file).unlink(missing_ok=True)

            logger.info(f"Successfully restored {len(data)} records to temporary table: {temp_table_name}")

            return temp_table_name

        except Exception as e:
            logger.error(f"Failed to restore logs from {s3_key}: {str(e)}", exc_info=True)
            raise

    def purge_temp_tables(self) -> int:
        """
        Purge temporary tables older than 7 days.

        Temporary tables have format: {table_name}_restored_{timestamp}

        Returns:
            Number of tables purged
        """
        logger.info("Starting purge of temporary tables older than 7 days")

        try:
            cutoff_timestamp = int((datetime.utcnow() - timedelta(days=7)).timestamp())
            tables_purged = 0

            with get_db_context() as db:
                # Get all table names
                result = db.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [row[0] for row in result.fetchall()]

                # Find and drop old temporary tables
                for table in tables:
                    if "_restored_" in table:
                        # Extract timestamp from table name
                        try:
                            timestamp_str = table.split("_restored_")[1]
                            timestamp = int(timestamp_str)

                            if timestamp < cutoff_timestamp:
                                # Drop table
                                db.execute(f"DROP TABLE {table}")
                                tables_purged += 1
                                logger.info(f"Purged temporary table: {table}")

                        except (ValueError, IndexError):
                            logger.warning(f"Could not parse timestamp from table name: {table}")
                            continue

                db.commit()

            logger.info(f"Purged {tables_purged} temporary tables")

            return tables_purged

        except Exception as e:
            logger.error(f"Failed to purge temporary tables: {str(e)}", exc_info=True)
            return 0

    def upload_to_s3(self, file_path: str, s3_key: str) -> bool:
        """
        Upload file to S3.

        Args:
            file_path: Local file path
            s3_key: S3 key (path within bucket)

        Returns:
            True if upload successful, False otherwise
        """
        if not self.s3_bucket:
            logger.error("S3 bucket not configured, cannot upload")
            return False

        try:
            import boto3
            from botocore.exceptions import ClientError

            # Create S3 client
            if self.aws_access_key_id and self.aws_secret_access_key:
                s3_client = boto3.client(
                    's3',
                    aws_access_key_id=self.aws_access_key_id,
                    aws_secret_access_key=self.aws_secret_access_key
                )
            else:
                # Use IAM role credentials
                s3_client = boto3.client('s3')

            # Upload file
            s3_client.upload_file(file_path, self.s3_bucket, s3_key)

            logger.info(f"Successfully uploaded to S3: s3://{self.s3_bucket}/{s3_key}")

            return True

        except ClientError as e:
            logger.error(f"S3 upload failed: {str(e)}", exc_info=True)
            return False
        except Exception as e:
            logger.error(f"S3 upload failed: {str(e)}", exc_info=True)
            return False

    def download_from_s3(self, s3_key: str, local_path: str) -> bool:
        """
        Download file from S3.

        Args:
            s3_key: S3 key (path within bucket)
            local_path: Local file path to save to

        Returns:
            True if download successful, False otherwise
        """
        if not self.s3_bucket:
            logger.error("S3 bucket not configured, cannot download")
            return False

        try:
            import boto3
            from botocore.exceptions import ClientError

            # Create S3 client
            if self.aws_access_key_id and self.aws_secret_access_key:
                s3_client = boto3.client(
                    's3',
                    aws_access_key_id=self.aws_access_key_id,
                    aws_secret_access_key=self.aws_secret_access_key
                )
            else:
                # Use IAM role credentials
                s3_client = boto3.client('s3')

            # Download file
            s3_client.download_file(self.s3_bucket, s3_key, local_path)

            logger.info(f"Successfully downloaded from S3: s3://{self.s3_bucket}/{s3_key}")

            return True

        except ClientError as e:
            logger.error(f"S3 download failed: {str(e)}", exc_info=True)
            return False
        except Exception as e:
            logger.error(f"S3 download failed: {str(e)}", exc_info=True)
            return False

    def generate_manifest(
        self,
        data: List[Dict[str, Any]],
        table_name: str,
        year: int,
        month: int,
        file_path: str
    ) -> Dict[str, Any]:
        """
        Generate manifest file with metadata and checksum.

        Args:
            data: Data that was archived
            table_name: Table name
            year: Year
            month: Month
            file_path: Path to archive file

        Returns:
            Manifest dictionary
        """
        # Calculate file size
        file_size = Path(file_path).stat().st_size if Path(file_path).exists() else 0

        # Calculate checksum
        checksum = self._calculate_checksum(data)

        manifest = {
            "table_name": table_name,
            "year": year,
            "month": month,
            "row_count": len(data),
            "file_size": file_size,
            "checksum": checksum,
            "archived_at": datetime.utcnow().isoformat()
        }

        return manifest

    def _create_archive_file(
        self,
        data: List[Dict[str, Any]],
        table_name: str,
        year: int,
        month: int
    ) -> str:
        """
        Create compressed JSON archive file.

        Args:
            data: Data to archive
            table_name: Table name
            year: Year
            month: Month

        Returns:
            File path
        """
        # Create filename
        filename = f"{table_name}_{year}_{month:02d}.json.gz"
        file_path = f"/tmp/{filename}"

        # Write compressed JSON
        with gzip.open(file_path, 'wt', encoding='utf-8') as f:
            json.dump(data, f, indent=2, default=str)

        logger.debug(f"Created archive file: {file_path} ({len(data)} records)")

        return file_path

    def _calculate_checksum(self, data: List[Dict[str, Any]]) -> str:
        """
        Calculate SHA256 checksum of data.

        Args:
            data: Data to checksum

        Returns:
            SHA256 hex string
        """
        # Convert to JSON string (sorted keys for consistency)
        json_str = json.dumps(data, sort_keys=True, default=str)

        # Calculate SHA256
        checksum = hashlib.sha256(json_str.encode('utf-8')).hexdigest()

        return checksum
