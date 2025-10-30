"""
AlertHistory Model for Alert Delivery Tracking

Tracks alert delivery attempts for security events with status and error tracking.
Phase 2 - Task Group 11: Database Schema - Security Monitoring Tables
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Optional
from sqlalchemy import Column, String, DateTime, ForeignKey, Index, CheckConstraint, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from src.config.database import Base


class AlertStatus(str, Enum):
    """Alert delivery status values."""
    SENT = "sent"
    FAILED = "failed"
    THROTTLED = "throttled"


class AlertHistory(Base):
    """
    AlertHistory model for tracking alert delivery.

    Fields:
        alert_id: UUID primary key
        security_event_id: Foreign key to security_events table
        user_id: Foreign key to users table (recipient of the alert)
        alert_type: Type of alert (e.g., 'email', 'slack', 'pagerduty')
        sent_at: Timestamp when alert was sent/attempted
        status: Delivery status (sent, failed, throttled)
        error_message: Error message if delivery failed (nullable)

    Alert Types:
        - email: Email notification
        - slack: Slack webhook notification
        - pagerduty: PagerDuty alert for critical events

    Status Values:
        - sent: Alert successfully delivered
        - failed: Alert delivery failed (error_message contains details)
        - throttled: Alert was not sent due to throttling rules
    """

    __tablename__ = "alert_history"

    alert_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    security_event_id = Column(
        UUID(as_uuid=True),
        ForeignKey("security_events.event_id", ondelete="CASCADE"),
        nullable=False
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False
    )
    alert_type = Column(String(50), nullable=False)
    sent_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    status = Column(String(20), nullable=False)
    error_message = Column(Text, nullable=True)

    # Indexes for performance
    __table_args__ = (
        Index('idx_alert_history_user_id', 'user_id'),
        Index('idx_alert_history_sent_at', 'sent_at'),
        CheckConstraint(
            "status IN ('sent', 'failed', 'throttled')",
            name='ck_alert_history_status'
        ),
    )

    # Relationships (optional, for convenience)
    # security_event = relationship("SecurityEvent", backref="alerts")
    # user = relationship("User", backref="alert_history")

    def __repr__(self) -> str:
        return (
            f"<AlertHistory(alert_id={self.alert_id}, "
            f"alert_type='{self.alert_type}', "
            f"status='{self.status}', "
            f"user_id={self.user_id})>"
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "alert_id": str(self.alert_id),
            "security_event_id": str(self.security_event_id),
            "user_id": str(self.user_id),
            "alert_type": self.alert_type,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "status": self.status,
            "error_message": self.error_message,
        }

    @staticmethod
    def validate_status(status: str) -> bool:
        """Validate alert status string."""
        try:
            AlertStatus(status)
            return True
        except ValueError:
            return False

    def was_sent(self) -> bool:
        """Check if alert was successfully sent."""
        return self.status == AlertStatus.SENT.value

    def was_failed(self) -> bool:
        """Check if alert delivery failed."""
        return self.status == AlertStatus.FAILED.value

    def was_throttled(self) -> bool:
        """Check if alert was throttled."""
        return self.status == AlertStatus.THROTTLED.value
