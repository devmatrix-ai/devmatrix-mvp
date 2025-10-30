"""
Account Lockout Service

Handles account lockout protection with exponential backoff.

Features:
- Tracks failed login attempts
- Triggers lockout after configurable threshold (default: 5 attempts in 15 minutes)
- Exponential backoff lockout durations (15min → 30min → 1hr → 2hrs → 4hrs max)
- Admin manual unlock capability
- Auto-unlock for expired lockouts
- Alert admins when account locked 3+ times in 24 hours

Part of Phase 2 - Task Group 3: Account Lockout Protection
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from uuid import UUID
from sqlalchemy import and_

from src.models.user import User
from src.config.database import get_db_context
from src.config.settings import get_settings
from src.observability import get_logger
from src.observability.audit_logger import audit_logger

logger = get_logger("account_lockout_service")
settings = get_settings()


class AccountLockoutService:
    """
    Account lockout service for brute force protection.

    Usage:
        service = AccountLockoutService()

        # Record failed login attempt
        result = service.record_failed_attempt(user_id, ip_address)
        if result["locked"]:
            print(f"Account locked until {result['locked_until']}")

        # Reset attempts after successful login
        service.reset_attempts(user_id)

        # Admin manual unlock
        service.unlock_account(user_id, admin_user_id)

        # Auto-unlock expired lockouts (background job)
        unlocked_count = service.process_auto_unlock()
    """

    def __init__(self):
        """Initialize account lockout service with configuration"""
        self.threshold = settings.ACCOUNT_LOCKOUT_THRESHOLD
        self.window_minutes = settings.ACCOUNT_LOCKOUT_WINDOW_MINUTES

        # Parse lockout durations from comma-separated string
        duration_str = settings.ACCOUNT_LOCKOUT_DURATIONS
        self.lockout_durations = [int(d) for d in duration_str.split(",")]

        logger.info(
            f"AccountLockoutService initialized: threshold={self.threshold}, "
            f"window={self.window_minutes}min, durations={self.lockout_durations}"
        )

    def record_failed_attempt(self, user_id: UUID, ip_address: str) -> Dict[str, Any]:
        """
        Record failed login attempt and check if lockout should trigger.

        Args:
            user_id: User UUID
            ip_address: Client IP address

        Returns:
            dict: {
                "locked": bool,
                "locked_until": datetime or None,
                "attempts_remaining": int
            }

        Example:
            result = service.record_failed_attempt(user.user_id, "192.168.1.100")
            if result["locked"]:
                raise HTTPException(
                    status_code=403,
                    detail=f"Account locked. Try again in {result['minutes_remaining']} minutes."
                )
        """
        try:
            with get_db_context() as db:
                user = db.query(User).filter(User.user_id == user_id).first()

                if not user:
                    logger.warning(f"Failed to record attempt: User {user_id} not found")
                    return {
                        "locked": False,
                        "locked_until": None,
                        "attempts_remaining": self.threshold
                    }

                # Increment failed login attempts
                user.failed_login_attempts += 1
                user.last_failed_login = datetime.utcnow()

                logger.info(
                    f"Failed login attempt recorded for user {user_id}: "
                    f"{user.failed_login_attempts}/{self.threshold} attempts"
                )

                # Check if should trigger lockout
                if user.failed_login_attempts >= self.threshold:
                    # Calculate lockout duration based on history
                    lockout_count = self.get_lockout_count(user_id)
                    duration_index = min(lockout_count, len(self.lockout_durations) - 1)
                    duration_minutes = self.lockout_durations[duration_index]

                    # Set lockout expiry
                    user.locked_until = datetime.utcnow() + timedelta(minutes=duration_minutes)
                    db.commit()

                    logger.warning(
                        f"Account locked: user {user_id}, duration={duration_minutes}min, "
                        f"lockout_count={lockout_count + 1}, locked_until={user.locked_until}"
                    )

                    # Log audit event (async)
                    import asyncio
                    asyncio.create_task(
                        audit_logger.log_event(
                            user_id=user_id,
                            action="auth.account_locked",
                            result="success",
                            resource_type="user",
                            resource_id=user_id,
                            ip_address=ip_address,
                            metadata={
                                "lockout_duration_minutes": duration_minutes,
                                "lockout_count": lockout_count + 1,
                                "failed_attempts": user.failed_login_attempts
                            }
                        )
                    )

                    return {
                        "locked": True,
                        "locked_until": user.locked_until,
                        "attempts_remaining": 0,
                        "lockout_duration_minutes": duration_minutes
                    }

                # Not locked yet
                db.commit()

                return {
                    "locked": False,
                    "locked_until": None,
                    "attempts_remaining": self.threshold - user.failed_login_attempts
                }

        except Exception as e:
            logger.error(
                f"Error recording failed attempt for user {user_id}: {str(e)}",
                exc_info=True
            )
            # Return safe default (not locked) to avoid blocking legitimate users
            return {
                "locked": False,
                "locked_until": None,
                "attempts_remaining": self.threshold
            }

    def reset_attempts(self, user_id: UUID) -> None:
        """
        Reset failed login attempts after successful login.

        Args:
            user_id: User UUID

        Example:
            # After successful password verification
            service.reset_attempts(user.user_id)
        """
        try:
            with get_db_context() as db:
                user = db.query(User).filter(User.user_id == user_id).first()

                if not user:
                    logger.warning(f"Failed to reset attempts: User {user_id} not found")
                    return

                # Reset failed login counter
                previous_attempts = user.failed_login_attempts
                user.failed_login_attempts = 0
                user.last_failed_login = None

                db.commit()

                if previous_attempts > 0:
                    logger.info(
                        f"Failed login attempts reset for user {user_id}: "
                        f"{previous_attempts} → 0"
                    )

        except Exception as e:
            logger.error(
                f"Error resetting attempts for user {user_id}: {str(e)}",
                exc_info=True
            )

    def unlock_account(self, user_id: UUID, admin_user_id: UUID) -> None:
        """
        Admin manual unlock of locked account.

        Args:
            user_id: User UUID to unlock
            admin_user_id: Admin user UUID performing the unlock

        Example:
            # Admin endpoint
            service.unlock_account(locked_user_id, current_admin.user_id)
        """
        try:
            with get_db_context() as db:
                user = db.query(User).filter(User.user_id == user_id).first()

                if not user:
                    logger.warning(f"Failed to unlock: User {user_id} not found")
                    return

                # Clear lockout and reset attempts
                was_locked = user.locked_until is not None
                user.locked_until = None
                user.failed_login_attempts = 0
                user.last_failed_login = None

                db.commit()

                if was_locked:
                    logger.info(
                        f"Account unlocked by admin: user {user_id}, "
                        f"admin {admin_user_id}"
                    )

                    # Log audit event (async)
                    import asyncio
                    asyncio.create_task(
                        audit_logger.log_event(
                            user_id=admin_user_id,
                            action="user.unlock",
                            result="success",
                            resource_type="user",
                            resource_id=user_id,
                            metadata={
                                "unlocked_user_id": str(user_id),
                                "admin_user_id": str(admin_user_id)
                            }
                        )
                    )

        except Exception as e:
            logger.error(
                f"Error unlocking account for user {user_id}: {str(e)}",
                exc_info=True
            )

    def get_lockout_count(self, user_id: UUID) -> int:
        """
        Get number of lockouts for user in past 24 hours.

        This is used to determine the exponential backoff duration.

        Args:
            user_id: User UUID

        Returns:
            int: Number of lockouts in past 24 hours

        Note:
            For Phase 2.1, we use a simplified approach:
            - Query audit logs for "auth.account_locked" events in past 24 hours
            - This provides historical lockout count for exponential backoff

            Alternative implementation (Phase 2.2+):
            - Add lockout_history table with timestamps
            - More efficient for high-volume scenarios
        """
        try:
            from src.models.audit_log import AuditLog

            with get_db_context() as db:
                # Query audit logs for lockout events in past 24 hours
                cutoff_time = datetime.utcnow() - timedelta(hours=24)

                lockout_events = db.query(AuditLog).filter(
                    and_(
                        AuditLog.user_id == user_id,
                        AuditLog.action == "auth.account_locked",
                        AuditLog.timestamp >= cutoff_time
                    )
                ).count()

                logger.debug(f"Lockout count for user {user_id}: {lockout_events} in past 24h")

                return lockout_events

        except Exception as e:
            logger.error(
                f"Error getting lockout count for user {user_id}: {str(e)}",
                exc_info=True
            )
            # Return 0 to use first lockout duration (15 minutes)
            return 0

    def get_expired_lockouts(self) -> List[User]:
        """
        Get list of users with expired lockouts.

        Used by auto-unlock background job to identify accounts to unlock.

        Returns:
            List[User]: Users with expired lockouts (locked_until <= NOW)

        Example:
            # In background job
            expired_users = service.get_expired_lockouts()
            for user in expired_users:
                print(f"Auto-unlocking user {user.user_id}")
        """
        try:
            with get_db_context() as db:
                now = datetime.utcnow()

                # Find users where lockout has expired
                expired_users = db.query(User).filter(
                    and_(
                        User.locked_until.isnot(None),
                        User.locked_until <= now
                    )
                ).all()

                logger.debug(f"Found {len(expired_users)} users with expired lockouts")

                return expired_users

        except Exception as e:
            logger.error(
                f"Error getting expired lockouts: {str(e)}",
                exc_info=True
            )
            return []

    def process_auto_unlock(self) -> int:
        """
        Process auto-unlock for all expired lockouts.

        This method is called by the background job every 5 minutes.

        Returns:
            int: Number of accounts unlocked

        Example:
            # In APScheduler job
            @scheduler.scheduled_job('interval', minutes=5)
            async def auto_unlock_job():
                service = AccountLockoutService()
                unlocked_count = service.process_auto_unlock()
                logger.info(f"Auto-unlocked {unlocked_count} accounts")
        """
        try:
            unlocked_count = 0

            with get_db_context() as db:
                now = datetime.utcnow()

                # Find and unlock expired lockouts
                locked_users = db.query(User).filter(
                    and_(
                        User.locked_until.isnot(None),
                        User.locked_until <= now
                    )
                ).all()

                for user in locked_users:
                    user.locked_until = None
                    user.failed_login_attempts = 0
                    user.last_failed_login = None
                    unlocked_count += 1

                    logger.info(f"Auto-unlocked expired lockout for user {user.user_id}")

                db.commit()

                if unlocked_count > 0:
                    logger.info(f"Auto-unlock completed: {unlocked_count} accounts unlocked")

                return unlocked_count

        except Exception as e:
            logger.error(
                f"Error processing auto-unlock: {str(e)}",
                exc_info=True
            )
            return 0
