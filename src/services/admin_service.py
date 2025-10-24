"""
Admin Service

Provides administrative functions for user and quota management.
Task Group 6.1-6.3 - Phase 6: Authentication & Multi-tenancy

Features:
- User management (list, view, activate/deactivate, delete)
- Quota management (create, update, delete)
- System statistics
- Usage monitoring across all users
"""

from datetime import date, datetime
from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy import func, desc

from src.models.user import User
from src.models.user_quota import UserQuota
from src.models.user_usage import UserUsage
from src.models.conversation import Conversation
from src.models.masterplan import MasterPlan
from src.config.database import get_db_context
from src.observability import get_logger

logger = get_logger("admin_service")


class AdminService:
    """
    Service for administrative operations.

    IMPORTANT: All methods in this service should only be called after
    verifying that the current user is a superuser. Use the
    get_current_superuser dependency in API endpoints.

    Usage:
        admin = AdminService()

        # List all users
        users = admin.list_users()

        # Set user quota
        admin.set_user_quota(
            user_id=user_id,
            llm_tokens_monthly_limit=1_000_000,
            masterplans_limit=10
        )

        # Get system stats
        stats = admin.get_system_stats()
    """

    # ========================================================================
    # User Management
    # ========================================================================

    def list_users(
        self,
        limit: int = 100,
        offset: int = 0,
        is_active: Optional[bool] = None,
        is_verified: Optional[bool] = None,
        search: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        List all users with optional filtering.

        Args:
            limit: Maximum number of users to return
            offset: Number of users to skip
            is_active: Filter by active status (None = all)
            is_verified: Filter by verified status (None = all)
            search: Search by email or username (partial match)

        Returns:
            Dictionary with users list and total count
        """
        with get_db_context() as db:
            query = db.query(User)

            # Apply filters
            if is_active is not None:
                query = query.filter(User.is_active == is_active)

            if is_verified is not None:
                query = query.filter(User.is_verified == is_verified)

            if search:
                search_pattern = f"%{search}%"
                query = query.filter(
                    (User.email.ilike(search_pattern)) |
                    (User.username.ilike(search_pattern))
                )

            # Get total count before pagination
            total = query.count()

            # Apply pagination
            users = query.order_by(desc(User.created_at)).limit(limit).offset(offset).all()

            logger.info(f"Admin listed {len(users)} users (total: {total})")

            return {
                "users": [user.to_dict() for user in users],
                "total": total,
                "limit": limit,
                "offset": offset
            }

    def get_user_details(self, user_id: UUID) -> Dict[str, Any]:
        """
        Get detailed user information including quota and usage.

        Args:
            user_id: User UUID

        Returns:
            Dictionary with user details, quota, and current usage

        Raises:
            ValueError: If user not found
        """
        with get_db_context() as db:
            user = db.query(User).filter(User.user_id == user_id).first()

            if not user:
                raise ValueError(f"User not found: {user_id}")

            # Get quota
            quota = db.query(UserQuota).filter(UserQuota.user_id == user_id).first()

            # Get current month usage
            today = date.today()
            current_month = date(today.year, today.month, 1)
            usage = db.query(UserUsage).filter(
                UserUsage.user_id == user_id,
                UserUsage.month == current_month
            ).first()

            # Get resource counts
            conversations_count = db.query(func.count()).select_from(Conversation).filter(
                Conversation.user_id == user_id
            ).scalar()

            masterplans_count = db.query(func.count(MasterPlan.masterplan_id)).filter(
                MasterPlan.user_id == user_id
            ).scalar()

            logger.info(f"Admin retrieved details for user {user_id}")

            return {
                "user": user.to_dict(),
                "quota": quota.to_dict() if quota else None,
                "current_usage": usage.to_dict() if usage else None,
                "resource_counts": {
                    "conversations": conversations_count,
                    "masterplans": masterplans_count
                }
            }

    def update_user_status(
        self,
        user_id: UUID,
        is_active: Optional[bool] = None,
        is_verified: Optional[bool] = None,
        is_superuser: Optional[bool] = None
    ) -> User:
        """
        Update user status flags.

        Args:
            user_id: User UUID
            is_active: Set active status
            is_verified: Set verified status
            is_superuser: Set superuser status

        Returns:
            Updated User object

        Raises:
            ValueError: If user not found
        """
        with get_db_context() as db:
            user = db.query(User).filter(User.user_id == user_id).first()

            if not user:
                raise ValueError(f"User not found: {user_id}")

            # Update fields
            if is_active is not None:
                user.is_active = is_active

            if is_verified is not None:
                user.is_verified = is_verified

            if is_superuser is not None:
                user.is_superuser = is_superuser

            db.commit()
            db.refresh(user)

            logger.info(
                f"Admin updated user {user_id} status: "
                f"active={is_active}, verified={is_verified}, superuser={is_superuser}"
            )

            return user

    def delete_user(self, user_id: UUID) -> bool:
        """
        Delete user and all associated data.

        Due to CASCADE delete constraints, this will also delete:
        - User quota
        - User usage records
        - Conversations and messages
        - MasterPlans and all related data

        Args:
            user_id: User UUID

        Returns:
            True if deleted, False if not found

        Raises:
            ValueError: If trying to delete the last superuser
        """
        with get_db_context() as db:
            user = db.query(User).filter(User.user_id == user_id).first()

            if not user:
                return False

            # Prevent deleting last superuser
            if user.is_superuser:
                superuser_count = db.query(func.count(User.user_id)).filter(
                    User.is_superuser == True
                ).scalar()

                if superuser_count <= 1:
                    raise ValueError("Cannot delete the last superuser")

            db.delete(user)
            db.commit()

            logger.warning(f"Admin deleted user {user_id} ({user.email})")

            return True

    # ========================================================================
    # Quota Management
    # ========================================================================

    def set_user_quota(
        self,
        user_id: UUID,
        llm_tokens_monthly_limit: Optional[int] = None,
        masterplans_limit: Optional[int] = None,
        storage_bytes_limit: Optional[int] = None,
        api_calls_per_minute: int = 30
    ) -> UserQuota:
        """
        Create or update user quota.

        Args:
            user_id: User UUID
            llm_tokens_monthly_limit: Monthly LLM token limit (None = unlimited)
            masterplans_limit: Max masterplans (None = unlimited)
            storage_bytes_limit: Max storage in bytes (None = unlimited)
            api_calls_per_minute: API rate limit per minute

        Returns:
            UserQuota object

        Raises:
            ValueError: If user not found
        """
        with get_db_context() as db:
            # Verify user exists
            user = db.query(User).filter(User.user_id == user_id).first()
            if not user:
                raise ValueError(f"User not found: {user_id}")

            # Get or create quota
            quota = db.query(UserQuota).filter(UserQuota.user_id == user_id).first()

            if quota:
                # Update existing quota
                quota.llm_tokens_monthly_limit = llm_tokens_monthly_limit
                quota.masterplans_limit = masterplans_limit
                quota.storage_bytes_limit = storage_bytes_limit
                quota.api_calls_per_minute = api_calls_per_minute

                logger.info(f"Admin updated quota for user {user_id}")
            else:
                # Create new quota
                quota = UserQuota(
                    user_id=user_id,
                    llm_tokens_monthly_limit=llm_tokens_monthly_limit,
                    masterplans_limit=masterplans_limit,
                    storage_bytes_limit=storage_bytes_limit,
                    api_calls_per_minute=api_calls_per_minute
                )
                db.add(quota)

                logger.info(f"Admin created quota for user {user_id}")

            db.commit()
            db.refresh(quota)

            return quota

    def delete_user_quota(self, user_id: UUID) -> bool:
        """
        Delete user quota (resets to unlimited).

        Args:
            user_id: User UUID

        Returns:
            True if deleted, False if no quota existed
        """
        with get_db_context() as db:
            quota = db.query(UserQuota).filter(UserQuota.user_id == user_id).first()

            if not quota:
                return False

            db.delete(quota)
            db.commit()

            logger.info(f"Admin deleted quota for user {user_id} (now unlimited)")

            return True

    # ========================================================================
    # System Statistics
    # ========================================================================

    def get_system_stats(self) -> Dict[str, Any]:
        """
        Get system-wide statistics.

        Returns:
            Dictionary with system statistics
        """
        with get_db_context() as db:
            # User statistics
            total_users = db.query(func.count(User.user_id)).scalar()
            active_users = db.query(func.count(User.user_id)).filter(
                User.is_active == True
            ).scalar()
            verified_users = db.query(func.count(User.user_id)).filter(
                User.is_verified == True
            ).scalar()
            superusers = db.query(func.count(User.user_id)).filter(
                User.is_superuser == True
            ).scalar()

            # Resource statistics
            total_conversations = db.query(func.count()).select_from(Conversation).scalar()
            total_masterplans = db.query(func.count(MasterPlan.masterplan_id)).scalar()

            # Usage statistics (current month)
            today = date.today()
            current_month = date(today.year, today.month, 1)

            current_month_usage = db.query(
                func.sum(UserUsage.llm_tokens_used).label('total_tokens'),
                func.sum(UserUsage.llm_cost_usd).label('total_cost'),
                func.sum(UserUsage.api_calls).label('total_api_calls')
            ).filter(
                UserUsage.month == current_month
            ).first()

            logger.info("Admin retrieved system statistics")

            return {
                "users": {
                    "total": total_users,
                    "active": active_users,
                    "verified": verified_users,
                    "superusers": superusers,
                },
                "resources": {
                    "conversations": total_conversations,
                    "masterplans": total_masterplans,
                },
                "current_month_usage": {
                    "month": str(current_month),
                    "total_llm_tokens": int(current_month_usage.total_tokens or 0),
                    "total_cost_usd": float(current_month_usage.total_cost or 0.0),
                    "total_api_calls": int(current_month_usage.total_api_calls or 0),
                }
            }

    def get_top_users_by_usage(self, limit: int = 10, month: Optional[date] = None) -> List[Dict[str, Any]]:
        """
        Get top users by LLM token usage.

        Args:
            limit: Number of top users to return
            month: Specific month (None = current month)

        Returns:
            List of users with their usage, sorted by tokens descending
        """
        if month is None:
            today = date.today()
            month = date(today.year, today.month, 1)

        with get_db_context() as db:
            results = db.query(
                User.user_id,
                User.email,
                User.username,
                UserUsage.llm_tokens_used,
                UserUsage.llm_cost_usd,
                UserUsage.api_calls
            ).join(
                UserUsage, User.user_id == UserUsage.user_id
            ).filter(
                UserUsage.month == month
            ).order_by(
                desc(UserUsage.llm_tokens_used)
            ).limit(limit).all()

            top_users = [
                {
                    "user_id": str(result.user_id),
                    "email": result.email,
                    "username": result.username,
                    "llm_tokens_used": result.llm_tokens_used,
                    "llm_cost_usd": float(result.llm_cost_usd),
                    "api_calls": result.api_calls,
                }
                for result in results
            ]

            logger.info(f"Admin retrieved top {limit} users by usage for month {month}")

            return top_users


def get_admin_service() -> AdminService:
    """
    Factory function to create AdminService instance.

    Returns:
        AdminService instance
    """
    return AdminService()
