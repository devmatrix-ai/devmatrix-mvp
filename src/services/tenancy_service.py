"""
Tenancy Service

Provides utilities for multi-tenant data isolation and scoped queries.
Task Group 4.1-4.2 - Phase 6: Authentication & Multi-tenancy

Features:
- User-scoped database queries
- Automatic tenant filtering
- Data isolation helpers
- Authorization checks

Design:
- All queries are scoped to the current user (tenant)
- No user can access another user's data
- Enforces foreign key relationships
- Provides helper methods for common patterns
"""

from typing import Optional, Type, TypeVar, List
from uuid import UUID
from sqlalchemy.orm import Session, Query
from sqlalchemy import and_

from src.models.user import User
from src.models.conversation import Conversation
from src.models.message import Message
from src.models.user_quota import UserQuota
from src.models.user_usage import UserUsage
from src.models.masterplan import MasterPlan, DiscoveryDocument
from src.config.database import get_db_context
from src.observability import get_logger

logger = get_logger("tenancy_service")

# Type variable for model classes
T = TypeVar('T')


class TenancyService:
    """
    Service for multi-tenant data isolation.

    Ensures all database queries are properly scoped to the current user (tenant).
    Prevents unauthorized access to other users' data.

    Usage:
        # Initialize with user context
        tenancy = TenancyService(current_user_id)

        # Get user's conversations (automatically scoped)
        conversations = tenancy.get_user_conversations()

        # Get user's masterplans (automatically scoped)
        masterplans = tenancy.get_user_masterplans()

        # Verify ownership before accessing
        if tenancy.user_owns_conversation(conversation_id):
            # Access allowed
            pass

        # Get scoped query for custom filtering
        with get_db_context() as db:
            query = tenancy.scope_conversation_query(db)
            recent = query.order_by(Conversation.created_at.desc()).limit(10).all()
    """

    def __init__(self, user_id: UUID):
        """
        Initialize tenancy service for a specific user.

        Args:
            user_id: UUID of the current user (tenant)
        """
        self.user_id = user_id
        logger.debug(f"TenancyService initialized for user {user_id}")

    # ========================================================================
    # Conversation Scoping
    # ========================================================================

    def scope_conversation_query(self, db: Session) -> Query:
        """
        Get scoped query for conversations.

        Returns query that only includes conversations owned by current user.

        Args:
            db: Database session

        Returns:
            Scoped SQLAlchemy query
        """
        return db.query(Conversation).filter(Conversation.user_id == self.user_id)

    def get_user_conversations(self, limit: Optional[int] = None) -> List[Conversation]:
        """
        Get all conversations for current user.

        Args:
            limit: Optional limit on number of results

        Returns:
            List of user's conversations
        """
        with get_db_context() as db:
            query = self.scope_conversation_query(db).order_by(Conversation.created_at.desc())
            if limit:
                query = query.limit(limit)
            conversations = query.all()
            logger.debug(f"Retrieved {len(conversations)} conversations for user {self.user_id}")
            return conversations

    def user_owns_conversation(self, conversation_id: UUID) -> bool:
        """
        Check if current user owns a conversation.

        Args:
            conversation_id: Conversation UUID

        Returns:
            True if user owns conversation, False otherwise
        """
        with get_db_context() as db:
            conversation = self.scope_conversation_query(db).filter(
                Conversation.conversation_id == conversation_id
            ).first()
            return conversation is not None

    def get_user_conversation(self, conversation_id: UUID) -> Optional[Conversation]:
        """
        Get a specific conversation if user owns it.

        Args:
            conversation_id: Conversation UUID

        Returns:
            Conversation object if owned by user, None otherwise
        """
        with get_db_context() as db:
            conversation = self.scope_conversation_query(db).filter(
                Conversation.conversation_id == conversation_id
            ).first()
            if conversation:
                logger.debug(f"User {self.user_id} accessed conversation {conversation_id}")
            else:
                logger.warning(
                    f"User {self.user_id} attempted to access unauthorized conversation {conversation_id}"
                )
            return conversation

    # ========================================================================
    # MasterPlan Scoping
    # ========================================================================

    def scope_masterplan_query(self, db: Session) -> Query:
        """
        Get scoped query for masterplans.

        Returns query that only includes masterplans owned by current user.

        Args:
            db: Database session

        Returns:
            Scoped SQLAlchemy query
        """
        return db.query(MasterPlan).filter(MasterPlan.user_id == self.user_id)

    def get_user_masterplans(self, limit: Optional[int] = None) -> List[MasterPlan]:
        """
        Get all masterplans for current user.

        Args:
            limit: Optional limit on number of results

        Returns:
            List of user's masterplans
        """
        with get_db_context() as db:
            query = self.scope_masterplan_query(db).order_by(MasterPlan.created_at.desc())
            if limit:
                query = query.limit(limit)
            masterplans = query.all()
            logger.debug(f"Retrieved {len(masterplans)} masterplans for user {self.user_id}")
            return masterplans

    def user_owns_masterplan(self, masterplan_id: UUID) -> bool:
        """
        Check if current user owns a masterplan.

        Args:
            masterplan_id: MasterPlan UUID

        Returns:
            True if user owns masterplan, False otherwise
        """
        with get_db_context() as db:
            masterplan = self.scope_masterplan_query(db).filter(
                MasterPlan.masterplan_id == masterplan_id
            ).first()
            return masterplan is not None

    def get_user_masterplan(self, masterplan_id: UUID) -> Optional[MasterPlan]:
        """
        Get a specific masterplan if user owns it.

        Args:
            masterplan_id: MasterPlan UUID

        Returns:
            MasterPlan object if owned by user, None otherwise
        """
        with get_db_context() as db:
            masterplan = self.scope_masterplan_query(db).filter(
                MasterPlan.masterplan_id == masterplan_id
            ).first()
            if masterplan:
                logger.debug(f"User {self.user_id} accessed masterplan {masterplan_id}")
            else:
                logger.warning(
                    f"User {self.user_id} attempted to access unauthorized masterplan {masterplan_id}"
                )
            return masterplan

    # ========================================================================
    # Discovery Document Scoping
    # ========================================================================

    def scope_discovery_query(self, db: Session) -> Query:
        """
        Get scoped query for discovery documents.

        Returns query that only includes documents owned by current user.

        Args:
            db: Database session

        Returns:
            Scoped SQLAlchemy query
        """
        return db.query(DiscoveryDocument).filter(DiscoveryDocument.user_id == self.user_id)

    def user_owns_discovery(self, discovery_id: UUID) -> bool:
        """
        Check if current user owns a discovery document.

        Args:
            discovery_id: DiscoveryDocument UUID

        Returns:
            True if user owns document, False otherwise
        """
        with get_db_context() as db:
            document = self.scope_discovery_query(db).filter(
                DiscoveryDocument.discovery_id == discovery_id
            ).first()
            return document is not None

    # ========================================================================
    # User Quota & Usage Scoping
    # ========================================================================

    def get_user_quota(self) -> Optional[UserQuota]:
        """
        Get quota for current user.

        Returns:
            UserQuota object if exists, None otherwise
        """
        with get_db_context() as db:
            quota = db.query(UserQuota).filter(UserQuota.user_id == self.user_id).first()
            return quota

    def get_user_usage(self, month: Optional[str] = None) -> Optional[UserUsage]:
        """
        Get usage for current user for a specific month.

        Args:
            month: Optional month (YYYY-MM-DD format, e.g., "2025-10-01")
                   If not provided, returns current month

        Returns:
            UserUsage object if exists, None otherwise
        """
        from datetime import date

        with get_db_context() as db:
            query = db.query(UserUsage).filter(UserUsage.user_id == self.user_id)

            if month:
                query = query.filter(UserUsage.month == month)
            else:
                # Get current month
                today = date.today()
                current_month = date(today.year, today.month, 1)
                query = query.filter(UserUsage.month == current_month)

            usage = query.first()
            return usage

    # ========================================================================
    # Authorization Helpers
    # ========================================================================

    def authorize_conversation_access(self, conversation_id: UUID) -> Conversation:
        """
        Authorize and return conversation or raise error.

        Args:
            conversation_id: Conversation UUID

        Returns:
            Conversation object

        Raises:
            ValueError: If user doesn't own conversation
        """
        conversation = self.get_user_conversation(conversation_id)
        if not conversation:
            logger.error(
                f"Authorization failed: User {self.user_id} does not own conversation {conversation_id}"
            )
            raise ValueError("Conversation not found or access denied")
        return conversation

    def authorize_masterplan_access(self, masterplan_id: UUID) -> MasterPlan:
        """
        Authorize and return masterplan or raise error.

        Args:
            masterplan_id: MasterPlan UUID

        Returns:
            MasterPlan object

        Raises:
            ValueError: If user doesn't own masterplan
        """
        masterplan = self.get_user_masterplan(masterplan_id)
        if not masterplan:
            logger.error(
                f"Authorization failed: User {self.user_id} does not own masterplan {masterplan_id}"
            )
            raise ValueError("MasterPlan not found or access denied")
        return masterplan


def get_tenancy_service(user_id: UUID) -> TenancyService:
    """
    Factory function to create TenancyService instance.

    Args:
        user_id: UUID of current user

    Returns:
        TenancyService instance
    """
    return TenancyService(user_id)
