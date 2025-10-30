"""
Session Service

Manages session metadata in Redis for session timeout tracking.
Implements idle timeout (30 minutes) and absolute timeout (12 hours) enforcement.

Part of Phase 2 - Task Group 4: Session Timeout Management
"""

import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from uuid import UUID

from src.state.redis_manager import RedisManager
from src.config.settings import get_settings
from src.observability import get_logger

logger = get_logger("session_service")
settings = get_settings()


class SessionService:
    """
    Service for managing user session metadata in Redis.

    Session metadata format:
    {
        "user_id": str,
        "token_jti": str,
        "last_activity": ISO timestamp,
        "issued_at": ISO timestamp
    }

    Redis key format: session:{user_id}:{token_jti}
    TTL: SESSION_IDLE_TIMEOUT_MINUTES (30 minutes)
    """

    def __init__(self, redis_manager: Optional[RedisManager] = None):
        """
        Initialize session service.

        Args:
            redis_manager: Optional RedisManager instance (defaults to new instance)
        """
        self.redis_manager = redis_manager or RedisManager(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=0,
            enable_fallback=True
        )
        self.idle_timeout_seconds = settings.SESSION_IDLE_TIMEOUT_MINUTES * 60
        self.absolute_timeout_seconds = settings.SESSION_ABSOLUTE_TIMEOUT_HOURS * 3600

    def create_session(
        self,
        user_id: UUID,
        token_jti: str,
        issued_at: datetime
    ) -> bool:
        """
        Create session metadata in Redis.

        Args:
            user_id: User UUID
            token_jti: JWT ID (jti claim)
            issued_at: Token issued at timestamp

        Returns:
            True if session created successfully, False otherwise
        """
        try:
            session_key = f"session:{user_id}:{token_jti}"

            session_metadata = {
                "user_id": str(user_id),
                "token_jti": token_jti,
                "last_activity": datetime.utcnow().isoformat(),
                "issued_at": issued_at.isoformat()
            }

            # Store in Redis with idle timeout TTL
            if self.redis_manager.connected:
                self.redis_manager.client.setex(
                    session_key,
                    self.idle_timeout_seconds,
                    json.dumps(session_metadata)
                )
                logger.debug(
                    f"Session created: {session_key} (TTL: {self.idle_timeout_seconds}s)"
                )
                return True
            else:
                logger.warning(
                    f"Redis unavailable - session not created for user {user_id}"
                )
                return False

        except Exception as e:
            logger.error(
                f"Failed to create session for user {user_id}: {str(e)}",
                exc_info=True
            )
            return False

    def get_session(
        self,
        user_id: UUID,
        token_jti: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get session metadata from Redis.

        Args:
            user_id: User UUID
            token_jti: JWT ID (jti claim)

        Returns:
            Session metadata dict if found, None if expired or not found
        """
        try:
            session_key = f"session:{user_id}:{token_jti}"

            if self.redis_manager.connected:
                session_data = self.redis_manager.client.get(session_key)

                if session_data:
                    return json.loads(session_data)
                else:
                    logger.debug(f"Session not found or expired: {session_key}")
                    return None
            else:
                logger.warning(
                    f"Redis unavailable - cannot check session for user {user_id}"
                )
                return None

        except Exception as e:
            logger.error(
                f"Failed to get session for user {user_id}: {str(e)}",
                exc_info=True
            )
            return None

    def update_activity(
        self,
        user_id: UUID,
        token_jti: str
    ) -> bool:
        """
        Update last activity timestamp and reset idle timeout.

        Called on every authenticated request to track activity.

        Args:
            user_id: User UUID
            token_jti: JWT ID (jti claim)

        Returns:
            True if activity updated successfully, False otherwise
        """
        try:
            session_key = f"session:{user_id}:{token_jti}"

            if not self.redis_manager.connected:
                logger.warning(
                    f"Redis unavailable - cannot update activity for user {user_id}"
                )
                return False

            # Get current session
            session_data = self.redis_manager.client.get(session_key)

            if not session_data:
                logger.debug(f"Session not found for activity update: {session_key}")
                return False

            # Update last_activity timestamp
            session_metadata = json.loads(session_data)
            session_metadata["last_activity"] = datetime.utcnow().isoformat()

            # Update session and reset TTL to idle timeout
            self.redis_manager.client.setex(
                session_key,
                self.idle_timeout_seconds,
                json.dumps(session_metadata)
            )

            logger.debug(f"Session activity updated: {session_key}")
            return True

        except Exception as e:
            logger.error(
                f"Failed to update activity for user {user_id}: {str(e)}",
                exc_info=True
            )
            return False

    def extend_session(
        self,
        user_id: UUID,
        token_jti: str
    ) -> Optional[datetime]:
        """
        Extend session idle timeout (keep-alive).

        Resets the Redis TTL to SESSION_IDLE_TIMEOUT_MINUTES.

        Args:
            user_id: User UUID
            token_jti: JWT ID (jti claim)

        Returns:
            Extended until timestamp if successful, None otherwise
        """
        try:
            session_key = f"session:{user_id}:{token_jti}"

            if not self.redis_manager.connected:
                logger.warning(
                    f"Redis unavailable - cannot extend session for user {user_id}"
                )
                return None

            # Check session exists
            session_data = self.redis_manager.client.get(session_key)

            if not session_data:
                logger.debug(f"Session not found for extension: {session_key}")
                return None

            # Reset TTL to idle timeout
            self.redis_manager.client.expire(session_key, self.idle_timeout_seconds)

            # Calculate extended until timestamp
            extended_until = datetime.utcnow() + timedelta(seconds=self.idle_timeout_seconds)

            logger.info(f"Session extended: {session_key} until {extended_until}")
            return extended_until

        except Exception as e:
            logger.error(
                f"Failed to extend session for user {user_id}: {str(e)}",
                exc_info=True
            )
            return None

    def delete_session(
        self,
        user_id: UUID,
        token_jti: str
    ) -> bool:
        """
        Delete session metadata from Redis.

        Called on logout to clean up session.

        Args:
            user_id: User UUID
            token_jti: JWT ID (jti claim)

        Returns:
            True if session deleted successfully, False otherwise
        """
        try:
            session_key = f"session:{user_id}:{token_jti}"

            if self.redis_manager.connected:
                deleted = self.redis_manager.client.delete(session_key)

                if deleted > 0:
                    logger.info(f"Session deleted: {session_key}")
                    return True
                else:
                    logger.debug(f"Session not found for deletion: {session_key}")
                    return False
            else:
                logger.warning(
                    f"Redis unavailable - cannot delete session for user {user_id}"
                )
                return False

        except Exception as e:
            logger.error(
                f"Failed to delete session for user {user_id}: {str(e)}",
                exc_info=True
            )
            return False

    def check_absolute_timeout(
        self,
        issued_at: datetime
    ) -> bool:
        """
        Check if session has exceeded absolute timeout (12 hours).

        Args:
            issued_at: Token issued at timestamp

        Returns:
            True if session is expired (exceeded 12 hours), False otherwise
        """
        try:
            current_time = datetime.utcnow()
            time_since_issuance = (current_time - issued_at).total_seconds()

            if time_since_issuance > self.absolute_timeout_seconds:
                logger.debug(
                    f"Session exceeded absolute timeout: {time_since_issuance}s > {self.absolute_timeout_seconds}s"
                )
                return True

            return False

        except Exception as e:
            logger.error(
                f"Failed to check absolute timeout: {str(e)}",
                exc_info=True
            )
            # Fail safe: allow session if check fails
            return False
