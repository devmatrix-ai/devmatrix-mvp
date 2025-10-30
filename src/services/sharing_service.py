"""
Sharing Service

Implements conversation sharing functionality for user-to-user collaboration.
Phase 2 - Task Group 10: Resource Sharing & Collaboration

Features:
- Share conversations with specific users
- 3 permission levels: view (read-only), comment (read + write messages), edit (full access except delete/re-share)
- Owner retains full control (delete, revoke shares)
- Email notifications when conversation shared
- No expiration dates (manual revoke only)
- Cannot share same conversation to same user twice (DB constraint enforced)

Permission Levels:
- view: Read-only access
- comment: Read + write messages
- edit: Full access except delete/re-share

Usage:
    sharing_service = SharingService()

    # Share conversation
    share = sharing_service.share_conversation(
        conversation_id=conversation_id,
        shared_with_email="user@example.com",
        permission_level="view",
        shared_by_user_id=owner_user_id
    )

    # List shares
    shares = sharing_service.list_conversation_shares(conversation_id, owner_user_id)

    # Update permission
    share = sharing_service.update_share_permission(share_id, "edit", owner_user_id)

    # Revoke share
    sharing_service.revoke_share(share_id, owner_user_id)

    # List shared with me
    shared = sharing_service.list_shared_with_user(user_id)
"""

import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime

from src.models.conversation import Conversation
from src.models.conversation_share import ConversationShare
from src.models.user import User
from src.services.email_service import EmailService
from src.observability.audit_logger import AuditLogger
from src.config.database import get_db_context
from src.observability import get_logger

logger = get_logger("sharing_service")


class SharingService:
    """
    Service for conversation sharing and collaboration.

    Implements secure conversation sharing with:
    - Ownership verification
    - Permission level enforcement
    - Email notifications
    - Audit logging
    - Duplicate share prevention
    """

    # Valid permission levels
    VALID_PERMISSIONS = ["view", "comment", "edit"]

    def __init__(self):
        """Initialize SharingService with dependencies."""
        self.email_service = EmailService()

    def share_conversation(
        self,
        conversation_id: uuid.UUID,
        shared_with_email: str,
        permission_level: str,
        shared_by_user_id: uuid.UUID
    ) -> ConversationShare:
        """
        Share conversation with another user.

        Args:
            conversation_id: UUID of conversation to share
            shared_with_email: Email of user to share with
            permission_level: Permission level (view/comment/edit)
            shared_by_user_id: UUID of user sharing the conversation

        Returns:
            ConversationShare: Created share record

        Raises:
            ValueError: If invalid permission level, user not found, or already shared
            PermissionError: If user is not conversation owner
        """
        try:
            # Validate permission level
            if permission_level not in self.VALID_PERMISSIONS:
                raise ValueError(
                    f"Invalid permission level: {permission_level}. "
                    f"Must be one of: {', '.join(self.VALID_PERMISSIONS)}"
                )

            with get_db_context() as db:
                # Verify conversation exists
                conversation = db.query(Conversation).filter(
                    Conversation.conversation_id == conversation_id
                ).first()

                if not conversation:
                    raise ValueError(f"Conversation {conversation_id} not found")

                # Verify user is owner
                if conversation.user_id != shared_by_user_id:
                    raise PermissionError(
                        "Only conversation owner can share conversations"
                    )

                # Find recipient user by email
                recipient_user = db.query(User).filter(
                    User.email == shared_with_email
                ).first()

                if not recipient_user:
                    raise ValueError(f"User with email {shared_with_email} not found")

                # Cannot share with yourself
                if recipient_user.user_id == shared_by_user_id:
                    raise ValueError("Cannot share conversation with yourself")

                # Check if already shared (prevent duplicate)
                existing_share = db.query(ConversationShare).filter(
                    ConversationShare.conversation_id == conversation_id,
                    ConversationShare.shared_with == recipient_user.user_id
                ).first()

                if existing_share:
                    raise ValueError(
                        f"Conversation already shared with this user. "
                        f"Use update_share_permission to change permission level."
                    )

                # Create share record
                share = ConversationShare(
                    share_id=uuid.uuid4(),
                    conversation_id=conversation_id,
                    shared_by=shared_by_user_id,
                    shared_with=recipient_user.user_id,
                    permission_level=permission_level,
                    shared_at=datetime.utcnow()
                )

                db.add(share)
                db.commit()
                db.refresh(share)

                # Get sharer username for email
                sharer = db.query(User).filter(
                    User.user_id == shared_by_user_id
                ).first()

                logger.info(
                    f"Conversation {conversation_id} shared with {recipient_user.email} "
                    f"by {shared_by_user_id} with permission {permission_level}"
                )

                # Send email notification
                try:
                    self.email_service.send_conversation_share_email(
                        to_email=recipient_user.email,
                        recipient_username=recipient_user.username,
                        sharer_username=sharer.username if sharer else "A user",
                        conversation_title=conversation.title or "Untitled Conversation",
                        permission_level=permission_level,
                        conversation_id=conversation_id
                    )
                except Exception as e:
                    logger.error(
                        f"Failed to send share notification email: {str(e)}",
                        exc_info=True
                    )
                    # Don't fail the share if email fails

                # Audit log
                try:
                    AuditLogger.log_event(
                        user_id=shared_by_user_id,
                        action="conversation.shared",
                        result="success",
                        resource_type="conversation",
                        resource_id=conversation_id,
                        metadata={
                            "shared_with_user_id": str(recipient_user.user_id),
                            "shared_with_email": shared_with_email,
                            "permission_level": permission_level
                        }
                    )
                except Exception as e:
                    logger.error(f"Failed to log share audit event: {str(e)}")

                return share

        except (ValueError, PermissionError):
            raise
        except Exception as e:
            logger.error(f"Error sharing conversation: {str(e)}", exc_info=True)
            raise

    def list_conversation_shares(
        self,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> List[ConversationShare]:
        """
        List all shares for a conversation.

        Only conversation owner can list shares.

        Args:
            conversation_id: UUID of conversation
            user_id: UUID of user requesting list (must be owner)

        Returns:
            List of ConversationShare records

        Raises:
            PermissionError: If user is not conversation owner
        """
        try:
            with get_db_context() as db:
                # Verify conversation exists and user is owner
                conversation = db.query(Conversation).filter(
                    Conversation.conversation_id == conversation_id
                ).first()

                if not conversation:
                    raise ValueError(f"Conversation {conversation_id} not found")

                if conversation.user_id != user_id:
                    raise PermissionError(
                        "Only conversation owner can list shares"
                    )

                # Get all shares for conversation
                shares = db.query(ConversationShare).filter(
                    ConversationShare.conversation_id == conversation_id
                ).all()

                logger.info(
                    f"Listed {len(shares)} shares for conversation {conversation_id}"
                )

                return shares

        except (ValueError, PermissionError):
            raise
        except Exception as e:
            logger.error(f"Error listing conversation shares: {str(e)}", exc_info=True)
            raise

    def update_share_permission(
        self,
        share_id: uuid.UUID,
        new_permission_level: str,
        user_id: uuid.UUID
    ) -> ConversationShare:
        """
        Update permission level for existing share.

        Only conversation owner can update permissions.

        Args:
            share_id: UUID of share to update
            new_permission_level: New permission level (view/comment/edit)
            user_id: UUID of user making update (must be owner)

        Returns:
            Updated ConversationShare

        Raises:
            ValueError: If invalid permission level or share not found
            PermissionError: If user is not conversation owner
        """
        try:
            # Validate permission level
            if new_permission_level not in self.VALID_PERMISSIONS:
                raise ValueError(
                    f"Invalid permission level: {new_permission_level}. "
                    f"Must be one of: {', '.join(self.VALID_PERMISSIONS)}"
                )

            with get_db_context() as db:
                # Get share
                share = db.query(ConversationShare).filter(
                    ConversationShare.share_id == share_id
                ).first()

                if not share:
                    raise ValueError(f"Share {share_id} not found")

                # Verify user is conversation owner
                conversation = db.query(Conversation).filter(
                    Conversation.conversation_id == share.conversation_id
                ).first()

                if not conversation or conversation.user_id != user_id:
                    raise PermissionError(
                        "Only conversation owner can update share permissions"
                    )

                # Update permission level
                old_permission = share.permission_level
                share.permission_level = new_permission_level
                db.commit()
                db.refresh(share)

                logger.info(
                    f"Updated share {share_id} permission from {old_permission} "
                    f"to {new_permission_level}"
                )

                # Audit log
                try:
                    AuditLogger.log_event(
                        user_id=user_id,
                        action="conversation.share_permission_updated",
                        result="success",
                        resource_type="conversation",
                        resource_id=share.conversation_id,
                        metadata={
                            "share_id": str(share_id),
                            "old_permission": old_permission,
                            "new_permission": new_permission_level,
                            "shared_with_user_id": str(share.shared_with)
                        }
                    )
                except Exception as e:
                    logger.error(f"Failed to log permission update audit event: {str(e)}")

                return share

        except (ValueError, PermissionError):
            raise
        except Exception as e:
            logger.error(f"Error updating share permission: {str(e)}", exc_info=True)
            raise

    def revoke_share(
        self,
        share_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> bool:
        """
        Revoke conversation share.

        Only conversation owner can revoke shares.

        Args:
            share_id: UUID of share to revoke
            user_id: UUID of user revoking (must be owner)

        Returns:
            True if revoked successfully

        Raises:
            ValueError: If share not found
            PermissionError: If user is not conversation owner
        """
        try:
            with get_db_context() as db:
                # Get share
                share = db.query(ConversationShare).filter(
                    ConversationShare.share_id == share_id
                ).first()

                if not share:
                    raise ValueError(f"Share {share_id} not found")

                # Verify user is conversation owner
                conversation = db.query(Conversation).filter(
                    Conversation.conversation_id == share.conversation_id
                ).first()

                if not conversation or conversation.user_id != user_id:
                    raise PermissionError(
                        "Only conversation owner can revoke shares"
                    )

                # Store info for logging before deletion
                conversation_id = share.conversation_id
                shared_with = share.shared_with

                # Delete share
                db.delete(share)
                db.commit()

                logger.info(f"Revoked share {share_id} for conversation {conversation_id}")

                # Audit log
                try:
                    AuditLogger.log_event(
                        user_id=user_id,
                        action="conversation.share_revoked",
                        result="success",
                        resource_type="conversation",
                        resource_id=conversation_id,
                        metadata={
                            "share_id": str(share_id),
                            "shared_with_user_id": str(shared_with)
                        }
                    )
                except Exception as e:
                    logger.error(f"Failed to log share revoke audit event: {str(e)}")

                return True

        except (ValueError, PermissionError):
            raise
        except Exception as e:
            logger.error(f"Error revoking share: {str(e)}", exc_info=True)
            raise

    def list_shared_with_user(
        self,
        user_id: uuid.UUID
    ) -> List[Dict[str, Any]]:
        """
        List all conversations shared with user.

        Args:
            user_id: UUID of user

        Returns:
            List of dicts with conversation, permission_level, and shared_at
        """
        try:
            with get_db_context() as db:
                # Query conversations shared with user
                results = db.query(Conversation, ConversationShare).join(
                    ConversationShare,
                    Conversation.conversation_id == ConversationShare.conversation_id
                ).filter(
                    ConversationShare.shared_with == user_id
                ).all()

                shared_conversations = [
                    {
                        "conversation": conversation,
                        "permission_level": share.permission_level,
                        "shared_at": share.shared_at,
                        "shared_by": share.shared_by
                    }
                    for conversation, share in results
                ]

                logger.info(
                    f"Listed {len(shared_conversations)} conversations shared with user {user_id}"
                )

                return shared_conversations

        except Exception as e:
            logger.error(
                f"Error listing shared conversations for user {user_id}: {str(e)}",
                exc_info=True
            )
            raise
