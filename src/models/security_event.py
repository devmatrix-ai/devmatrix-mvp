"""
SecurityEvent Model for Security Monitoring

Stores security anomaly detection events with severity levels and resolution tracking.
Phase 2 - Task Group 11: Database Schema - Security Monitoring Tables
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Optional
from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Index, CheckConstraint, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from src.config.database import Base


class SeverityLevel(str, Enum):
    """Security event severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SecurityEvent(Base):
    """
    SecurityEvent model for security anomaly detection and monitoring.

    Fields:
        event_id: UUID primary key
        event_type: Type of security event (e.g., 'failed_login', 'privilege_escalation')
        severity: Severity level (low, medium, high, critical)
        user_id: Foreign key to users table (nullable to allow system-wide events)
        event_data: JSON data containing event details
        detected_at: Timestamp when event was detected
        resolved: Boolean flag indicating if event has been resolved
        resolved_at: Timestamp when event was resolved (nullable)
        resolved_by: User ID who resolved the event (foreign key to users)

    Monitored Event Types:
        - failed_login_cluster: 5+ failed logins in 10 minutes
        - geo_location_change: IP country change detected
        - privilege_escalation: Role changed to admin/superadmin
        - unusual_access: Access at atypical hours
        - multiple_403s: 10+ 403 errors in 5 minutes
        - account_lockout: Account locked due to failed attempts
        - 2fa_disabled: 2FA disabled when enforcement enabled
        - concurrent_sessions: Multiple sessions from different countries
    """

    __tablename__ = "security_events"

    event_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type = Column(String(50), nullable=False)
    severity = Column(String(20), nullable=False)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=True  # Allow system-wide events without specific user
    )
    event_data = Column(JSON, nullable=False)  # Use JSON for SQLite compatibility (becomes JSONB in PostgreSQL via migration)
    detected_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    resolved = Column(Boolean, default=False, nullable=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolved_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="SET NULL"),
        nullable=True
    )

    # Indexes for performance
    __table_args__ = (
        Index('idx_security_events_user_id', 'user_id'),
        Index('idx_security_events_detected_at', 'detected_at'),
        Index('idx_security_events_severity', 'severity'),
        Index('idx_security_events_resolved', 'resolved'),
        CheckConstraint(
            "severity IN ('low', 'medium', 'high', 'critical')",
            name='ck_security_events_severity'
        ),
    )

    # Relationships (optional, for convenience)
    # user = relationship("User", foreign_keys=[user_id], backref="security_events")
    # resolver = relationship("User", foreign_keys=[resolved_by])

    def __repr__(self) -> str:
        return (
            f"<SecurityEvent(event_id={self.event_id}, "
            f"event_type='{self.event_type}', "
            f"severity='{self.severity}', "
            f"user_id={self.user_id}, "
            f"resolved={self.resolved})>"
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "event_id": str(self.event_id),
            "event_type": self.event_type,
            "severity": self.severity,
            "user_id": str(self.user_id) if self.user_id else None,
            "event_data": self.event_data,
            "detected_at": self.detected_at.isoformat() if self.detected_at else None,
            "resolved": self.resolved,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "resolved_by": str(self.resolved_by) if self.resolved_by else None,
        }

    @staticmethod
    def validate_severity(severity: str) -> bool:
        """Validate severity level string."""
        try:
            SeverityLevel(severity)
            return True
        except ValueError:
            return False

    def is_resolved(self) -> bool:
        """Check if event has been resolved."""
        return self.resolved is True

    def is_critical(self) -> bool:
        """Check if event is critical severity."""
        return self.severity == SeverityLevel.CRITICAL.value

    def is_high_or_critical(self) -> bool:
        """Check if event is high or critical severity."""
        return self.severity in [SeverityLevel.HIGH.value, SeverityLevel.CRITICAL.value]
