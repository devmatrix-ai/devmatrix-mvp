"""
Security Monitoring Service

Detects security anomalies and creates security events for:
- Failed login clusters (5+ in 10 minutes)
- Geo-location changes (IP country change)
- Privilege escalation (role changed to admin/superadmin)
- Unusual access patterns (access at atypical hours)
- Multiple 403s (10+ in 5 minutes)
- Account lockout events
- 2FA disabled when enforced
- Multiple concurrent sessions from different countries

Runs in batch every 5 minutes via background job.

Part of Phase 2 - Task Group 13: Security Event Monitoring
"""

import uuid
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from collections import defaultdict

from src.models.security_event import SecurityEvent, SeverityLevel
from src.models.audit_log import AuditLog
from src.config.database import get_db_context
from src.config.settings import get_settings
from src.observability import get_logger

logger = get_logger("security_monitoring_service")
settings = get_settings()


class SecurityMonitoringService:
    """
    Security event monitoring service.

    Detects security anomalies by analyzing audit logs and creates
    security events with appropriate severity levels.

    Severity Levels:
    - critical: failed_login_cluster (>10 attempts), privilege_escalation (to superadmin),
                concurrent_sessions (from 3+ countries)
    - high: geo_changes, privilege_escalation (to admin), 2fa_disabled (when enforced)
    - medium: multiple_403s, unusual_access, account_lockout
    - low: other events
    """

    def __init__(self):
        """Initialize SecurityMonitoringService"""
        self.logger = logger

    def detect_failed_login_clusters(self) -> List[SecurityEvent]:
        """
        Detect clusters of failed login attempts (5+ in 10 minutes).

        Severity:
        - critical: 10+ failed attempts
        - high: 5-9 failed attempts

        Returns:
            List of SecurityEvent objects for detected clusters
        """
        try:
            with get_db_context() as db:
                # Look back 10 minutes
                cutoff_time = datetime.utcnow() - timedelta(minutes=10)

                # Query failed login attempts in last 10 minutes
                failed_logins = db.query(AuditLog).filter(
                    AuditLog.action == "auth.login_failed",
                    AuditLog.result == "denied",
                    AuditLog.timestamp >= cutoff_time
                ).all()

                # Group by user_id
                user_failures = defaultdict(list)
                for log in failed_logins:
                    if log.user_id:
                        user_failures[log.user_id].append(log)

                # Create security events for users with 5+ failures
                events = []
                for user_id, failures in user_failures.items():
                    if len(failures) >= 5:
                        # Determine severity
                        severity = SeverityLevel.CRITICAL if len(failures) >= 10 else SeverityLevel.HIGH

                        # Check if event already exists for this user in last 10 minutes
                        existing = db.query(SecurityEvent).filter(
                            SecurityEvent.event_type == "failed_login_cluster",
                            SecurityEvent.user_id == user_id,
                            SecurityEvent.detected_at >= cutoff_time,
                            SecurityEvent.resolved == False
                        ).first()

                        if existing:
                            # Update existing event data
                            existing.event_data = {
                                "failed_attempts": len(failures),
                                "ip_addresses": list(set([f.ip_address for f in failures if f.ip_address])),
                                "time_window": "10 minutes",
                                "first_attempt": min([f.timestamp for f in failures]).isoformat(),
                                "last_attempt": max([f.timestamp for f in failures]).isoformat()
                            }
                            existing.severity = severity.value
                            existing.detected_at = datetime.utcnow()
                            events.append(existing)
                        else:
                            # Create new event
                            event = SecurityEvent(
                                event_id=uuid.uuid4(),
                                event_type="failed_login_cluster",
                                severity=severity.value,
                                user_id=user_id,
                                event_data={
                                    "failed_attempts": len(failures),
                                    "ip_addresses": list(set([f.ip_address for f in failures if f.ip_address])),
                                    "time_window": "10 minutes",
                                    "first_attempt": min([f.timestamp for f in failures]).isoformat(),
                                    "last_attempt": max([f.timestamp for f in failures]).isoformat()
                                },
                                detected_at=datetime.utcnow(),
                                resolved=False
                            )
                            db.add(event)
                            events.append(event)

                        self.logger.info(
                            f"Detected failed login cluster: {len(failures)} attempts for user {user_id}",
                            extra={"user_id": str(user_id), "attempts": len(failures)}
                        )

                db.commit()
                return events

        except Exception as e:
            self.logger.error(f"Failed to detect failed login clusters: {str(e)}", exc_info=True)
            return []

    def detect_geo_changes(self) -> List[SecurityEvent]:
        """
        Detect geo-location changes (IP country change).

        Severity: high

        Returns:
            List of SecurityEvent objects for detected geo changes
        """
        try:
            with get_db_context() as db:
                # Look back 60 minutes for login events
                cutoff_time = datetime.utcnow() - timedelta(minutes=60)

                # Query successful logins with country metadata
                logins = db.query(AuditLog).filter(
                    AuditLog.action == "auth.login",
                    AuditLog.result == "success",
                    AuditLog.timestamp >= cutoff_time
                ).order_by(AuditLog.timestamp).all()

                # Group by user and track country changes
                user_logins = defaultdict(list)
                for log in logins:
                    if log.user_id and log.event_metadata and "country" in log.event_metadata:
                        user_logins[log.user_id].append(log)

                # Detect country changes
                events = []
                for user_id, user_login_list in user_logins.items():
                    if len(user_login_list) >= 2:
                        # Check consecutive logins for country changes
                        for i in range(1, len(user_login_list)):
                            prev_country = user_login_list[i-1].event_metadata.get("country")
                            curr_country = user_login_list[i].event_metadata.get("country")

                            if prev_country and curr_country and prev_country != curr_country:
                                # Time between logins
                                time_diff = user_login_list[i].timestamp - user_login_list[i-1].timestamp

                                # Check if event already exists
                                existing = db.query(SecurityEvent).filter(
                                    SecurityEvent.event_type == "geo_location_change",
                                    SecurityEvent.user_id == user_id,
                                    SecurityEvent.detected_at >= cutoff_time,
                                    SecurityEvent.resolved == False
                                ).first()

                                if not existing:
                                    event = SecurityEvent(
                                        event_id=uuid.uuid4(),
                                        event_type="geo_location_change",
                                        severity=SeverityLevel.HIGH.value,
                                        user_id=user_id,
                                        event_data={
                                            "previous_country": prev_country,
                                            "new_country": curr_country,
                                            "previous_ip": user_login_list[i-1].ip_address,
                                            "new_ip": user_login_list[i].ip_address,
                                            "time_between_logins": str(time_diff),
                                            "timestamp": user_login_list[i].timestamp.isoformat()
                                        },
                                        detected_at=datetime.utcnow(),
                                        resolved=False
                                    )
                                    db.add(event)
                                    events.append(event)

                                    self.logger.info(
                                        f"Detected geo-location change: {prev_country} -> {curr_country} for user {user_id}",
                                        extra={"user_id": str(user_id), "prev_country": prev_country, "new_country": curr_country}
                                    )

                db.commit()
                return events

        except Exception as e:
            self.logger.error(f"Failed to detect geo-location changes: {str(e)}", exc_info=True)
            return []

    def detect_privilege_escalations(self) -> List[SecurityEvent]:
        """
        Detect privilege escalation (role changed to admin/superadmin).

        Severity:
        - critical: escalation to superadmin
        - high: escalation to admin

        Returns:
            List of SecurityEvent objects for detected escalations
        """
        try:
            with get_db_context() as db:
                # Look back 60 minutes
                cutoff_time = datetime.utcnow() - timedelta(minutes=60)

                # Query role assignments
                role_assignments = db.query(AuditLog).filter(
                    AuditLog.action == "role.assigned",
                    AuditLog.result == "success",
                    AuditLog.timestamp >= cutoff_time
                ).all()

                # Detect escalations to admin/superadmin
                events = []
                for log in role_assignments:
                    if log.event_metadata and "role" in log.event_metadata:
                        role = log.event_metadata.get("role")

                        if role in ["admin", "superadmin"]:
                            # Determine severity
                            severity = SeverityLevel.CRITICAL if role == "superadmin" else SeverityLevel.HIGH

                            # Check if event already exists
                            existing = db.query(SecurityEvent).filter(
                                SecurityEvent.event_type == "privilege_escalation",
                                SecurityEvent.user_id == log.user_id,
                                SecurityEvent.detected_at >= cutoff_time,
                                SecurityEvent.resolved == False
                            ).first()

                            if not existing:
                                event = SecurityEvent(
                                    event_id=uuid.uuid4(),
                                    event_type="privilege_escalation",
                                    severity=severity.value,
                                    user_id=log.user_id,
                                    event_data={
                                        "role": role,
                                        "assigned_by": log.event_metadata.get("assigned_by"),
                                        "timestamp": log.timestamp.isoformat()
                                    },
                                    detected_at=datetime.utcnow(),
                                    resolved=False
                                )
                                db.add(event)
                                events.append(event)

                                self.logger.info(
                                    f"Detected privilege escalation: {role} for user {log.user_id}",
                                    extra={"user_id": str(log.user_id), "role": role}
                                )

                db.commit()
                return events

        except Exception as e:
            self.logger.error(f"Failed to detect privilege escalations: {str(e)}", exc_info=True)
            return []

    def detect_unusual_access_patterns(self) -> List[SecurityEvent]:
        """
        Detect unusual access patterns (access at atypical hours).

        Atypical hours: midnight (00:00) to 6 AM (06:00)

        Severity: medium

        Returns:
            List of SecurityEvent objects for detected unusual access
        """
        try:
            with get_db_context() as db:
                # Look back 60 minutes
                cutoff_time = datetime.utcnow() - timedelta(minutes=60)

                # Query all access events (read operations)
                access_logs = db.query(AuditLog).filter(
                    AuditLog.result == "success",
                    AuditLog.timestamp >= cutoff_time
                ).all()

                # Detect access during atypical hours (midnight to 6 AM)
                events = []
                user_unusual_access = defaultdict(list)

                for log in access_logs:
                    if log.user_id and log.timestamp:
                        hour = log.timestamp.hour

                        # Atypical hours: 0-5 (midnight to 6 AM)
                        if 0 <= hour < 6:
                            user_unusual_access[log.user_id].append(log)

                # Create events for users with unusual access
                for user_id, unusual_logs in user_unusual_access.items():
                    if len(unusual_logs) > 0:
                        # Check if event already exists
                        existing = db.query(SecurityEvent).filter(
                            SecurityEvent.event_type == "unusual_access",
                            SecurityEvent.user_id == user_id,
                            SecurityEvent.detected_at >= cutoff_time,
                            SecurityEvent.resolved == False
                        ).first()

                        if not existing:
                            event = SecurityEvent(
                                event_id=uuid.uuid4(),
                                event_type="unusual_access",
                                severity=SeverityLevel.MEDIUM.value,
                                user_id=user_id,
                                event_data={
                                    "hour": unusual_logs[0].timestamp.hour,
                                    "unusual_reason": "access_at_atypical_hours",
                                    "access_count": len(unusual_logs),
                                    "timestamp": unusual_logs[0].timestamp.isoformat()
                                },
                                detected_at=datetime.utcnow(),
                                resolved=False
                            )
                            db.add(event)
                            events.append(event)

                            self.logger.info(
                                f"Detected unusual access: {len(unusual_logs)} accesses at hour {unusual_logs[0].timestamp.hour} for user {user_id}",
                                extra={"user_id": str(user_id), "hour": unusual_logs[0].timestamp.hour}
                            )

                db.commit()
                return events

        except Exception as e:
            self.logger.error(f"Failed to detect unusual access patterns: {str(e)}", exc_info=True)
            return []

    def detect_multiple_403s(self) -> List[SecurityEvent]:
        """
        Detect multiple 403 errors (10+ denied access in 5 minutes).

        Severity: medium

        Returns:
            List of SecurityEvent objects for detected multiple 403s
        """
        try:
            with get_db_context() as db:
                # Look back 5 minutes
                cutoff_time = datetime.utcnow() - timedelta(minutes=5)

                # Query denied access attempts
                denied_logs = db.query(AuditLog).filter(
                    AuditLog.result == "denied",
                    AuditLog.timestamp >= cutoff_time
                ).all()

                # Group by user_id
                user_denials = defaultdict(list)
                for log in denied_logs:
                    if log.user_id:
                        user_denials[log.user_id].append(log)

                # Create events for users with 10+ denials
                events = []
                for user_id, denials in user_denials.items():
                    if len(denials) >= 10:
                        # Check if event already exists
                        existing = db.query(SecurityEvent).filter(
                            SecurityEvent.event_type == "multiple_403s",
                            SecurityEvent.user_id == user_id,
                            SecurityEvent.detected_at >= cutoff_time,
                            SecurityEvent.resolved == False
                        ).first()

                        if not existing:
                            event = SecurityEvent(
                                event_id=uuid.uuid4(),
                                event_type="multiple_403s",
                                severity=SeverityLevel.MEDIUM.value,
                                user_id=user_id,
                                event_data={
                                    "denied_count": len(denials),
                                    "time_window": "5 minutes",
                                    "resources": list(set([d.resource_type for d in denials if d.resource_type])),
                                    "first_denial": min([d.timestamp for d in denials]).isoformat(),
                                    "last_denial": max([d.timestamp for d in denials]).isoformat()
                                },
                                detected_at=datetime.utcnow(),
                                resolved=False
                            )
                            db.add(event)
                            events.append(event)

                            self.logger.info(
                                f"Detected multiple 403s: {len(denials)} denials for user {user_id}",
                                extra={"user_id": str(user_id), "denied_count": len(denials)}
                            )

                db.commit()
                return events

        except Exception as e:
            self.logger.error(f"Failed to detect multiple 403s: {str(e)}", exc_info=True)
            return []

    def detect_account_lockouts(self) -> List[SecurityEvent]:
        """
        Detect account lockout events.

        Severity: medium

        Returns:
            List of SecurityEvent objects for detected lockouts
        """
        try:
            with get_db_context() as db:
                # Look back 60 minutes
                cutoff_time = datetime.utcnow() - timedelta(minutes=60)

                # Query account lockout events
                lockout_logs = db.query(AuditLog).filter(
                    AuditLog.action == "account.locked",
                    AuditLog.result == "success",
                    AuditLog.timestamp >= cutoff_time
                ).all()

                # Create security events for lockouts
                events = []
                for log in lockout_logs:
                    if log.user_id:
                        # Check if event already exists
                        existing = db.query(SecurityEvent).filter(
                            SecurityEvent.event_type == "account_lockout",
                            SecurityEvent.user_id == log.user_id,
                            SecurityEvent.detected_at >= cutoff_time,
                            SecurityEvent.resolved == False
                        ).first()

                        if not existing:
                            event = SecurityEvent(
                                event_id=uuid.uuid4(),
                                event_type="account_lockout",
                                severity=SeverityLevel.MEDIUM.value,
                                user_id=log.user_id,
                                event_data={
                                    "reason": log.event_metadata.get("reason") if log.event_metadata else "unknown",
                                    "locked_until": log.event_metadata.get("locked_until") if log.event_metadata else None,
                                    "timestamp": log.timestamp.isoformat()
                                },
                                detected_at=datetime.utcnow(),
                                resolved=False
                            )
                            db.add(event)
                            events.append(event)

                            self.logger.info(
                                f"Detected account lockout for user {log.user_id}",
                                extra={"user_id": str(log.user_id)}
                            )

                db.commit()
                return events

        except Exception as e:
            self.logger.error(f"Failed to detect account lockouts: {str(e)}", exc_info=True)
            return []

    def detect_2fa_disabled(self) -> List[SecurityEvent]:
        """
        Detect 2FA disabled when enforcement is enabled.

        Severity: high

        Returns:
            List of SecurityEvent objects for detected 2FA disabled events
        """
        try:
            with get_db_context() as db:
                # Look back 60 minutes
                cutoff_time = datetime.utcnow() - timedelta(minutes=60)

                # Query 2FA disabled events
                disabled_logs = db.query(AuditLog).filter(
                    AuditLog.action == "2fa.disabled",
                    AuditLog.result == "success",
                    AuditLog.timestamp >= cutoff_time
                ).all()

                # Create security events for 2FA disabled when enforcement enabled
                events = []
                for log in disabled_logs:
                    if log.user_id:
                        # Check if enforcement was enabled
                        enforce_2fa = log.event_metadata.get("enforce_2fa") if log.event_metadata else False

                        if enforce_2fa:
                            # Check if event already exists
                            existing = db.query(SecurityEvent).filter(
                                SecurityEvent.event_type == "2fa_disabled",
                                SecurityEvent.user_id == log.user_id,
                                SecurityEvent.detected_at >= cutoff_time,
                                SecurityEvent.resolved == False
                            ).first()

                            if not existing:
                                event = SecurityEvent(
                                    event_id=uuid.uuid4(),
                                    event_type="2fa_disabled",
                                    severity=SeverityLevel.HIGH.value,
                                    user_id=log.user_id,
                                    event_data={
                                        "enforce_2fa": enforce_2fa,
                                        "timestamp": log.timestamp.isoformat()
                                    },
                                    detected_at=datetime.utcnow(),
                                    resolved=False
                                )
                                db.add(event)
                                events.append(event)

                                self.logger.info(
                                    f"Detected 2FA disabled (enforcement enabled) for user {log.user_id}",
                                    extra={"user_id": str(log.user_id)}
                                )

                db.commit()
                return events

        except Exception as e:
            self.logger.error(f"Failed to detect 2FA disabled events: {str(e)}", exc_info=True)
            return []

    def detect_concurrent_sessions(self) -> List[SecurityEvent]:
        """
        Detect multiple concurrent sessions from different countries.

        Severity:
        - critical: 3+ countries
        - high: 2 countries

        Returns:
            List of SecurityEvent objects for detected concurrent sessions
        """
        try:
            with get_db_context() as db:
                # Look back 10 minutes for concurrent logins
                cutoff_time = datetime.utcnow() - timedelta(minutes=10)

                # Query successful logins with country metadata
                logins = db.query(AuditLog).filter(
                    AuditLog.action == "auth.login",
                    AuditLog.result == "success",
                    AuditLog.timestamp >= cutoff_time
                ).all()

                # Group by user and track countries
                user_countries = defaultdict(set)
                for log in logins:
                    if log.user_id and log.event_metadata and "country" in log.event_metadata:
                        user_countries[log.user_id].add(log.event_metadata["country"])

                # Create events for users with sessions from multiple countries
                events = []
                for user_id, countries in user_countries.items():
                    if len(countries) >= 2:
                        # Determine severity
                        severity = SeverityLevel.CRITICAL if len(countries) >= 3 else SeverityLevel.HIGH

                        # Check if event already exists
                        existing = db.query(SecurityEvent).filter(
                            SecurityEvent.event_type == "concurrent_sessions",
                            SecurityEvent.user_id == user_id,
                            SecurityEvent.detected_at >= cutoff_time,
                            SecurityEvent.resolved == False
                        ).first()

                        if not existing:
                            event = SecurityEvent(
                                event_id=uuid.uuid4(),
                                event_type="concurrent_sessions",
                                severity=severity.value,
                                user_id=user_id,
                                event_data={
                                    "countries": sorted(list(countries)),
                                    "session_count": len(countries),
                                    "time_window": "10 minutes",
                                    "timestamp": datetime.utcnow().isoformat()
                                },
                                detected_at=datetime.utcnow(),
                                resolved=False
                            )
                            db.add(event)
                            events.append(event)

                            self.logger.info(
                                f"Detected concurrent sessions: {len(countries)} countries for user {user_id}",
                                extra={"user_id": str(user_id), "countries": list(countries)}
                            )

                db.commit()
                return events

        except Exception as e:
            self.logger.error(f"Failed to detect concurrent sessions: {str(e)}", exc_info=True)
            return []

    def run_all_detections(self) -> List[SecurityEvent]:
        """
        Run all security event detection methods in batch.

        This method is called by the background job every 5 minutes.

        Returns:
            List of all SecurityEvent objects detected across all methods
        """
        try:
            self.logger.info("Starting batch security event detection")

            all_events = []

            # Run all detection methods
            all_events.extend(self.detect_failed_login_clusters())
            all_events.extend(self.detect_geo_changes())
            all_events.extend(self.detect_privilege_escalations())
            all_events.extend(self.detect_unusual_access_patterns())
            all_events.extend(self.detect_multiple_403s())
            all_events.extend(self.detect_account_lockouts())
            all_events.extend(self.detect_2fa_disabled())
            all_events.extend(self.detect_concurrent_sessions())

            self.logger.info(
                f"Batch security event detection completed: {len(all_events)} events detected",
                extra={"event_count": len(all_events)}
            )

            return all_events

        except Exception as e:
            self.logger.error(f"Failed to run batch security event detection: {str(e)}", exc_info=True)
            return []
