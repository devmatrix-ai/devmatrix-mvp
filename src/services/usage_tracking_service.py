"""
Usage Tracking Service

Tracks user resource consumption and enforces quotas.
Task Group 5.1-5.4 - Phase 6: Authentication & Multi-tenancy

Features:
- LLM token usage tracking
- Cost calculation and tracking
- Quota enforcement
- Monthly usage aggregation
- Storage tracking
- API call tracking

Design:
- Tracks usage per user per month
- Auto-creates usage records as needed
- Calculates costs based on token usage
- Enforces quota limits before operations
- Provides usage analytics
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional, Dict, Any
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from src.models.user_usage import UserUsage
from src.models.user_quota import UserQuota
from src.config.database import get_db_context
from src.config.constants import (
    COST_PER_1M_INPUT_TOKENS_USD,
    COST_PER_1M_OUTPUT_TOKENS_USD,
    USD_TO_EUR_RATE,
)
from src.observability import get_logger

logger = get_logger("usage_tracking_service")


class QuotaExceededException(Exception):
    """Raised when user exceeds their quota"""
    pass


class UsageTrackingService:
    """
    Service for tracking user resource usage and enforcing quotas.

    Usage:
        tracker = UsageTrackingService(user_id)

        # Record LLM usage
        tracker.record_llm_usage(
            input_tokens=1000,
            output_tokens=500,
            cached_tokens=200
        )

        # Check quota before operation
        if not tracker.can_use_llm_tokens(5000):
            raise QuotaExceededException("Monthly token limit exceeded")

        # Get current usage
        usage = tracker.get_current_usage()
        print(f"Tokens used: {usage['llm_tokens_used']}")
    """

    def __init__(self, user_id: UUID):
        """
        Initialize usage tracking service for a user.

        Args:
            user_id: UUID of the user
        """
        self.user_id = user_id

    # ========================================================================
    # Current Month Management
    # ========================================================================

    def get_current_month_date(self) -> date:
        """
        Get first day of current month.

        Returns:
            Date object for first day of current month (e.g., 2025-10-01)
        """
        today = date.today()
        return date(today.year, today.month, 1)

    def get_or_create_usage_record(self, month: Optional[date] = None) -> UserUsage:
        """
        Get or create usage record for user and month.

        Creates new record with zeros if doesn't exist.

        Args:
            month: Month date (first day). If None, uses current month.

        Returns:
            UserUsage record
        """
        if month is None:
            month = self.get_current_month_date()

        with get_db_context() as db:
            # Try to get existing record
            usage = db.query(UserUsage).filter(
                UserUsage.user_id == self.user_id,
                UserUsage.month == month
            ).first()

            if usage:
                return usage

            # Create new record
            usage = UserUsage(
                user_id=self.user_id,
                month=month,
                llm_tokens_used=0,
                llm_cost_usd=Decimal("0.0"),
                masterplans_created=0,
                storage_bytes=0,
                api_calls=0
            )

            try:
                db.add(usage)
                db.commit()
                db.refresh(usage)
                logger.info(f"Created new usage record for user {self.user_id}, month {month}")
                return usage
            except IntegrityError:
                # Race condition: record was created by another request
                db.rollback()
                usage = db.query(UserUsage).filter(
                    UserUsage.user_id == self.user_id,
                    UserUsage.month == month
                ).first()
                return usage

    # ========================================================================
    # LLM Usage Tracking
    # ========================================================================

    def calculate_llm_cost(
        self,
        input_tokens: int,
        output_tokens: int,
        cached_tokens: int = 0
    ) -> Decimal:
        """
        Calculate LLM cost based on token usage.

        Uses pricing from config/constants.py:
        - Input tokens: $3.00 per 1M tokens
        - Output tokens: $15.00 per 1M tokens
        - Cached tokens: 10% of input token cost (90% discount)

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            cached_tokens: Number of cached tokens (prompt caching)

        Returns:
            Cost in USD as Decimal
        """
        # Regular input tokens (non-cached)
        regular_input_tokens = input_tokens - cached_tokens

        # Calculate costs
        input_cost = (regular_input_tokens / 1_000_000) * COST_PER_1M_INPUT_TOKENS_USD
        output_cost = (output_tokens / 1_000_000) * COST_PER_1M_OUTPUT_TOKENS_USD

        # Cached tokens cost 10% of regular input token cost
        cached_cost = (cached_tokens / 1_000_000) * COST_PER_1M_INPUT_TOKENS_USD * 0.1

        total_cost = input_cost + output_cost + cached_cost

        return Decimal(str(round(total_cost, 4)))

    def record_llm_usage(
        self,
        input_tokens: int,
        output_tokens: int,
        cached_tokens: int = 0,
        month: Optional[date] = None
    ) -> Dict[str, Any]:
        """
        Record LLM usage for user.

        Updates usage record with token count and calculated cost.

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            cached_tokens: Number of cached tokens (prompt caching)
            month: Optional month (defaults to current month)

        Returns:
            Dictionary with updated usage stats
        """
        # Calculate cost
        cost_usd = self.calculate_llm_cost(input_tokens, output_tokens, cached_tokens)
        total_tokens = input_tokens + output_tokens

        # Get or create usage record
        usage = self.get_or_create_usage_record(month)

        # Update usage
        with get_db_context() as db:
            db_usage = db.query(UserUsage).filter(
                UserUsage.usage_id == usage.usage_id
            ).first()

            db_usage.llm_tokens_used += total_tokens
            db_usage.llm_cost_usd += cost_usd

            db.commit()
            db.refresh(db_usage)

            logger.info(
                f"Recorded LLM usage for user {self.user_id}: "
                f"+{total_tokens} tokens, +${cost_usd:.4f} "
                f"(total: {db_usage.llm_tokens_used} tokens, ${db_usage.llm_cost_usd:.4f})"
            )

            return {
                "tokens_added": total_tokens,
                "cost_added_usd": float(cost_usd),
                "total_tokens": db_usage.llm_tokens_used,
                "total_cost_usd": float(db_usage.llm_cost_usd),
                "month": str(db_usage.month)
            }

    def record_masterplan_creation(self, month: Optional[date] = None) -> Dict[str, Any]:
        """
        Record masterplan creation for user.

        Args:
            month: Optional month (defaults to current month)

        Returns:
            Dictionary with updated masterplan count
        """
        usage = self.get_or_create_usage_record(month)

        with get_db_context() as db:
            db_usage = db.query(UserUsage).filter(
                UserUsage.usage_id == usage.usage_id
            ).first()

            db_usage.masterplans_created += 1

            db.commit()
            db.refresh(db_usage)

            logger.info(
                f"Recorded masterplan creation for user {self.user_id}: "
                f"total={db_usage.masterplans_created}"
            )

            return {
                "masterplans_created": db_usage.masterplans_created,
                "month": str(db_usage.month)
            }

    def record_api_call(self, count: int = 1, month: Optional[date] = None) -> Dict[str, Any]:
        """
        Record API call(s) for user.

        Args:
            count: Number of API calls to record (default 1)
            month: Optional month (defaults to current month)

        Returns:
            Dictionary with updated API call count
        """
        usage = self.get_or_create_usage_record(month)

        with get_db_context() as db:
            db_usage = db.query(UserUsage).filter(
                UserUsage.usage_id == usage.usage_id
            ).first()

            db_usage.api_calls += count

            db.commit()
            db.refresh(db_usage)

            logger.debug(
                f"Recorded {count} API call(s) for user {self.user_id}: "
                f"total={db_usage.api_calls}"
            )

            return {
                "api_calls": db_usage.api_calls,
                "month": str(db_usage.month)
            }

    def update_storage_usage(self, storage_bytes: int, month: Optional[date] = None) -> Dict[str, Any]:
        """
        Update storage usage for user.

        This is an absolute value, not incremental.

        Args:
            storage_bytes: Current total storage in bytes
            month: Optional month (defaults to current month)

        Returns:
            Dictionary with updated storage info
        """
        usage = self.get_or_create_usage_record(month)

        with get_db_context() as db:
            db_usage = db.query(UserUsage).filter(
                UserUsage.usage_id == usage.usage_id
            ).first()

            db_usage.storage_bytes = storage_bytes

            db.commit()
            db.refresh(db_usage)

            logger.info(
                f"Updated storage usage for user {self.user_id}: "
                f"{storage_bytes} bytes ({storage_bytes / 1024 / 1024:.2f} MB)"
            )

            return {
                "storage_bytes": storage_bytes,
                "storage_mb": storage_bytes / 1024 / 1024,
                "month": str(db_usage.month)
            }

    # ========================================================================
    # Quota Management
    # ========================================================================

    def get_user_quota(self) -> Optional[UserQuota]:
        """
        Get user's quota limits.

        Returns:
            UserQuota object if exists, None otherwise
        """
        with get_db_context() as db:
            quota = db.query(UserQuota).filter(
                UserQuota.user_id == self.user_id
            ).first()
            return quota

    def can_use_llm_tokens(self, additional_tokens: int) -> bool:
        """
        Check if user can use additional LLM tokens without exceeding quota.

        Args:
            additional_tokens: Number of tokens user wants to use

        Returns:
            True if within quota, False if would exceed
        """
        quota = self.get_user_quota()

        # No quota = unlimited
        if not quota or quota.llm_tokens_monthly_limit is None:
            return True

        # Get current usage
        usage = self.get_or_create_usage_record()
        current_tokens = usage.llm_tokens_used

        # Check if adding would exceed limit
        would_exceed = (current_tokens + additional_tokens) > quota.llm_tokens_monthly_limit

        if would_exceed:
            logger.warning(
                f"User {self.user_id} would exceed token quota: "
                f"{current_tokens} + {additional_tokens} > {quota.llm_tokens_monthly_limit}"
            )

        return not would_exceed

    def can_create_masterplan(self) -> bool:
        """
        Check if user can create another masterplan.

        Returns:
            True if within quota, False if would exceed
        """
        quota = self.get_user_quota()

        # No quota = unlimited
        if not quota or quota.masterplans_limit is None:
            return True

        # Get current usage across all months
        with get_db_context() as db:
            total_masterplans = db.query(func.sum(UserUsage.masterplans_created)).filter(
                UserUsage.user_id == self.user_id
            ).scalar() or 0

            would_exceed = total_masterplans >= quota.masterplans_limit

            if would_exceed:
                logger.warning(
                    f"User {self.user_id} would exceed masterplan quota: "
                    f"{total_masterplans} >= {quota.masterplans_limit}"
                )

            return not would_exceed

    def can_use_storage(self, storage_bytes: int) -> bool:
        """
        Check if user can use given amount of storage.

        Args:
            storage_bytes: Total storage in bytes

        Returns:
            True if within quota, False if would exceed
        """
        quota = self.get_user_quota()

        # No quota = unlimited
        if not quota or quota.storage_bytes_limit is None:
            return True

        would_exceed = storage_bytes > quota.storage_bytes_limit

        if would_exceed:
            logger.warning(
                f"User {self.user_id} would exceed storage quota: "
                f"{storage_bytes} > {quota.storage_bytes_limit}"
            )

        return not would_exceed

    def enforce_llm_quota(self, estimated_tokens: int):
        """
        Enforce LLM quota before operation.

        Raises QuotaExceededException if quota would be exceeded.

        Args:
            estimated_tokens: Estimated tokens for operation

        Raises:
            QuotaExceededException: If quota would be exceeded
        """
        if not self.can_use_llm_tokens(estimated_tokens):
            quota = self.get_user_quota()
            usage = self.get_or_create_usage_record()

            raise QuotaExceededException(
                f"Monthly LLM token quota exceeded. "
                f"Used: {usage.llm_tokens_used}, "
                f"Limit: {quota.llm_tokens_monthly_limit}, "
                f"Requested: {estimated_tokens}"
            )

    def enforce_masterplan_quota(self):
        """
        Enforce masterplan quota before creation.

        Raises QuotaExceededException if quota would be exceeded.

        Raises:
            QuotaExceededException: If quota would be exceeded
        """
        if not self.can_create_masterplan():
            quota = self.get_user_quota()

            raise QuotaExceededException(
                f"MasterPlan creation quota exceeded. "
                f"Limit: {quota.masterplans_limit}"
            )

    # ========================================================================
    # Usage Analytics
    # ========================================================================

    def get_current_usage(self) -> Dict[str, Any]:
        """
        Get current month's usage statistics.

        Returns:
            Dictionary with usage stats
        """
        usage = self.get_or_create_usage_record()

        return {
            "user_id": str(self.user_id),
            "month": str(usage.month),
            "llm_tokens_used": usage.llm_tokens_used,
            "llm_cost_usd": float(usage.llm_cost_usd),
            "llm_cost_eur": float(usage.llm_cost_usd) * USD_TO_EUR_RATE,
            "masterplans_created": usage.masterplans_created,
            "storage_bytes": usage.storage_bytes,
            "storage_mb": usage.storage_bytes / 1024 / 1024 if usage.storage_bytes else 0,
            "api_calls": usage.api_calls,
        }

    def get_quota_status(self) -> Dict[str, Any]:
        """
        Get quota status with usage percentages.

        Returns:
            Dictionary with quota and usage info
        """
        quota = self.get_user_quota()
        usage = self.get_or_create_usage_record()

        # Calculate percentages
        token_percent = None
        storage_percent = None

        if quota and quota.llm_tokens_monthly_limit:
            token_percent = (usage.llm_tokens_used / quota.llm_tokens_monthly_limit) * 100

        if quota and quota.storage_bytes_limit and usage.storage_bytes:
            storage_percent = (usage.storage_bytes / quota.storage_bytes_limit) * 100

        return {
            "quota": quota.to_dict() if quota else None,
            "usage": self.get_current_usage(),
            "percentages": {
                "tokens": round(token_percent, 2) if token_percent is not None else None,
                "storage": round(storage_percent, 2) if storage_percent is not None else None,
            },
            "warnings": {
                "tokens_near_limit": token_percent >= 90 if token_percent else False,
                "storage_near_limit": storage_percent >= 90 if storage_percent else False,
            }
        }


def get_usage_tracker(user_id: UUID) -> UsageTrackingService:
    """
    Factory function to create UsageTrackingService instance.

    Args:
        user_id: UUID of user

    Returns:
        UsageTrackingService instance
    """
    return UsageTrackingService(user_id)
