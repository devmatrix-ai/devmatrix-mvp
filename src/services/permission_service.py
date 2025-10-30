"""
Permission Service

Implements granular permission checking with ownership-based access control.
Phase 2 - Task Group 8: Granular Permission System

Features:
- Ownership-based access (users can access their own resources)
- Shared resource access (users can access shared conversations)
- Role-based bypass (admin/superadmin can access all resources)
- Permission level enforcement (view/comment/edit)
- Message access through conversation ownership

Permission Levels:
- view: Read-only access
- comment: Read + write messages
- edit: Full access except delete/re-share

Usage:
    permission_service = PermissionService()

    # Check conversation access
    if permission_service.user_can_access_conversation(user_id, conversation_id, 'read'):
        # Allow read operation

    # Check message access
    if permission_service.user_can_access_message(user_id, message_id, 'write'):
        # Allow write operation

    # Get permission level
    level = permission_service.get_user_conversation_permission(user_id, conversation_id)
    # Returns: 'view', 'comment', 'edit', or None
"""

import uuid
from typing import Optional
from src.models.conversation import Conversation
from src.models.message import Message
from src.models.conversation_share import ConversationShare
from src.services.rbac_service import RBACService
from src.config.database import get_db_context
from src.observability import get_logger

logger = get_logger("permission_service")


class PermissionService:
    """
    Service for granular permission checking.

    Implements three-tier access control:
    1. Ownership: Users can access their own resources
    2. Sharing: Users can access resources shared with them (based on permission level)
    3. Role-based: Admin/superadmin can access all resources

    Permission hierarchy (most to least permissive):
    - Owner: Full control (read/write/delete/share)
    - Edit: Read + write (no delete/share)
    - Comment: Read + write messages only
    - View: Read-only
    """

    def __init__(self):
        """Initialize PermissionService with RBACService."""
        self.rbac_service = RBACService()

    def user_can_access_conversation(
        self,
        user_id: uuid.UUID,
        conversation_id: uuid.UUID,
        action: str
    ) -> bool:
        """
        Check if user can perform action on conversation.

        Access is granted if:
        1. User owns the conversation (all actions)
        2. User has admin/superadmin role (all actions)
        3. Conversation is shared with user (based on permission level)

        Args:
            user_id: UUID of user
            conversation_id: UUID of conversation
            action: Action to perform ('read', 'write', 'delete', 'share')

        Returns:
            True if user can perform action, False otherwise
        """
        try:
            # Check if user owns conversation
            if self.is_conversation_owner(user_id, conversation_id):
                logger.debug(
                    f"User {user_id} owns conversation {conversation_id}, "
                    f"allowing {action}"
                )
                return True

            # Check if user has admin/superadmin role (bypass)
            if self.rbac_service.user_has_role(user_id, "superadmin") or \
               self.rbac_service.user_has_role(user_id, "admin"):
                logger.debug(
                    f"User {user_id} has admin role, "
                    f"allowing {action} on conversation {conversation_id}"
                )
                return True

            # Check if conversation is shared with user
            if self.is_conversation_shared_with(user_id, conversation_id):
                permission_level = self.get_user_conversation_permission(
                    user_id, conversation_id
                )

                # Check permission level allows action
                allowed = self._permission_level_allows_action(
                    permission_level, action
                )

                if allowed:
                    logger.debug(
                        f"User {user_id} has '{permission_level}' permission "
                        f"on conversation {conversation_id}, allowing {action}"
                    )
                else:
                    logger.debug(
                        f"User {user_id} has '{permission_level}' permission "
                        f"on conversation {conversation_id}, denying {action}"
                    )

                return allowed

            # No access
            logger.debug(
                f"User {user_id} has no access to conversation {conversation_id}"
            )
            return False

        except Exception as e:
            logger.error(
                f"Error checking conversation access: {str(e)}",
                exc_info=True
            )
            return False

    def user_can_access_message(
        self,
        user_id: uuid.UUID,
        message_id: uuid.UUID,
        action: str
    ) -> bool:
        """
        Check if user can perform action on message.

        Message access is determined by conversation access.
        User must have access to the conversation containing the message.

        Args:
            user_id: UUID of user
            message_id: UUID of message
            action: Action to perform ('read', 'write', 'delete')

        Returns:
            True if user can perform action, False otherwise
        """
        try:
            # Get message's conversation
            with get_db_context() as db:
                message = db.query(Message).filter(
                    Message.message_id == message_id
                ).first()

                if not message:
                    logger.warning(f"Message {message_id} not found")
                    return False

                # Check conversation access
                return self.user_can_access_conversation(
                    user_id, message.conversation_id, action
                )

        except Exception as e:
            logger.error(
                f"Error checking message access: {str(e)}",
                exc_info=True
            )
            return False

    def get_user_conversation_permission(
        self,
        user_id: uuid.UUID,
        conversation_id: uuid.UUID
    ) -> Optional[str]:
        """
        Get user's permission level for conversation.

        Returns:
            Permission level string ('view', 'comment', 'edit') or None
        """
        try:
            with get_db_context() as db:
                share = db.query(ConversationShare).filter(
                    ConversationShare.conversation_id == conversation_id,
                    ConversationShare.shared_with == user_id
                ).first()

                if share:
                    return share.permission_level

                return None

        except Exception as e:
            logger.error(
                f"Error getting conversation permission: {str(e)}",
                exc_info=True
            )
            return None

    def is_conversation_owner(
        self,
        user_id: uuid.UUID,
        conversation_id: uuid.UUID
    ) -> bool:
        """
        Check if user owns conversation.

        Args:
            user_id: UUID of user
            conversation_id: UUID of conversation

        Returns:
            True if user owns conversation, False otherwise
        """
        try:
            with get_db_context() as db:
                conversation = db.query(Conversation).filter(
                    Conversation.conversation_id == conversation_id
                ).first()

                if not conversation:
                    logger.warning(f"Conversation {conversation_id} not found")
                    return False

                return conversation.user_id == user_id

        except Exception as e:
            logger.error(
                f"Error checking conversation ownership: {str(e)}",
                exc_info=True
            )
            return False

    def is_conversation_shared_with(
        self,
        user_id: uuid.UUID,
        conversation_id: uuid.UUID
    ) -> bool:
        """
        Check if conversation is shared with user.

        Args:
            user_id: UUID of user
            conversation_id: UUID of conversation

        Returns:
            True if conversation is shared with user, False otherwise
        """
        try:
            with get_db_context() as db:
                share = db.query(ConversationShare).filter(
                    ConversationShare.conversation_id == conversation_id,
                    ConversationShare.shared_with == user_id
                ).first()

                return share is not None

        except Exception as e:
            logger.error(
                f"Error checking conversation share: {str(e)}",
                exc_info=True
            )
            return False

    def _permission_level_allows_action(
        self,
        permission_level: Optional[str],
        action: str
    ) -> bool:
        """
        Check if permission level allows action.

        Permission Matrix:
        - view: read only
        - comment: read + write (messages only)
        - edit: read + write (all resources except delete)
        - owner: all actions (read/write/delete/share)

        Args:
            permission_level: Permission level string
            action: Action to perform

        Returns:
            True if permission level allows action, False otherwise
        """
        if not permission_level:
            return False

        # View permission: read only
        if permission_level == "view":
            return action == "read"

        # Comment permission: read + write
        if permission_level == "comment":
            return action in ["read", "write"]

        # Edit permission: read + write (no delete/share)
        if permission_level == "edit":
            return action in ["read", "write"]

        # Unknown permission level
        logger.warning(f"Unknown permission level: {permission_level}")
        return False
