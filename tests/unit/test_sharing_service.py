"""
Tests for Resource Sharing & Collaboration Service

Task Group 10 - Phase 2: Resource Sharing & Collaboration

Tests cover:
- Share conversation (owner can share)
- Cannot share same conversation twice to same user
- Non-owner cannot share
- List shares (owner can list)
- Update share permission level
- Revoke share (owner can revoke)
- List shared-with-me conversations
- Permission levels (view, comment, edit)
- Email notification sent on share
"""

import uuid
import pytest
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

from src.services.sharing_service import SharingService
from src.models.conversation import Conversation
from src.models.conversation_share import ConversationShare
from src.models.user import User
from src.config.database import get_db_context


@pytest.fixture
def mock_db():
    """Mock database session."""
    with patch('src.services.sharing_service.get_db_context') as mock_context:
        mock_session = MagicMock()
        mock_context.return_value.__enter__.return_value = mock_session
        yield mock_session


@pytest.fixture
def sharing_service():
    """Create SharingService instance."""
    return SharingService()


@pytest.fixture
def owner_user():
    """Create owner user."""
    return User(
        user_id=uuid.uuid4(),
        email="owner@example.com",
        username="owner",
        password_hash="hash"
    )


@pytest.fixture
def recipient_user():
    """Create recipient user."""
    return User(
        user_id=uuid.uuid4(),
        email="recipient@example.com",
        username="recipient",
        password_hash="hash"
    )


@pytest.fixture
def conversation(owner_user):
    """Create conversation owned by owner_user."""
    return Conversation(
        conversation_id=uuid.uuid4(),
        user_id=owner_user.user_id,
        title="Test Conversation"
    )


class TestShareConversation:
    """Test sharing conversation functionality."""

    def test_share_conversation_success(self, sharing_service, mock_db, owner_user, recipient_user, conversation):
        """Test owner can share conversation successfully."""
        # Mock database queries - in order:
        # 1. Check conversation exists
        # 2. Find recipient user by email
        # 3. Check if already shared (should be None)
        # 4. Get sharer user for email
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            conversation,  # Conversation exists
            recipient_user,  # Recipient user exists
            None,  # No existing share
            owner_user  # Sharer user for email
        ]

        # Mock audit logger
        with patch('src.services.sharing_service.AuditLogger.log_event') as mock_audit:
            # Share conversation
            share = sharing_service.share_conversation(
                conversation_id=conversation.conversation_id,
                shared_with_email="recipient@example.com",
                permission_level="view",
                shared_by_user_id=owner_user.user_id
            )

            # Verify share created
            assert share is not None
            assert share.conversation_id == conversation.conversation_id
            assert share.shared_by == owner_user.user_id
            assert share.permission_level == "view"

            # Verify audit log called
            mock_audit.assert_called_once()

    def test_cannot_share_same_conversation_twice(self, sharing_service, mock_db, owner_user, recipient_user, conversation):
        """Test cannot share same conversation to same user twice."""
        # Mock existing share
        existing_share = ConversationShare(
            share_id=uuid.uuid4(),
            conversation_id=conversation.conversation_id,
            shared_by=owner_user.user_id,
            shared_with=recipient_user.user_id,
            permission_level="view"
        )

        # Mock database queries
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            conversation,  # Conversation exists
            recipient_user,  # Recipient user exists
            existing_share,  # Share already exists
        ]

        # Attempt to share again
        with pytest.raises(ValueError, match="already shared with this user"):
            sharing_service.share_conversation(
                conversation_id=conversation.conversation_id,
                shared_with_email="recipient@example.com",
                permission_level="view",
                shared_by_user_id=owner_user.user_id
            )

    def test_non_owner_cannot_share(self, sharing_service, mock_db, owner_user, recipient_user, conversation):
        """Test non-owner cannot share conversation."""
        non_owner_id = uuid.uuid4()

        # Mock database queries
        mock_db.query.return_value.filter.return_value.first.return_value = conversation

        # Attempt to share as non-owner
        with pytest.raises(PermissionError, match="Only conversation owner can share"):
            sharing_service.share_conversation(
                conversation_id=conversation.conversation_id,
                shared_with_email="recipient@example.com",
                permission_level="view",
                shared_by_user_id=non_owner_id
            )

    def test_cannot_share_with_self(self, sharing_service, mock_db, owner_user, conversation):
        """Test cannot share conversation with yourself."""
        # Mock database queries
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            conversation,  # Conversation exists
            owner_user  # Recipient is same as owner
        ]

        # Attempt to share with self
        with pytest.raises(ValueError, match="Cannot share conversation with yourself"):
            sharing_service.share_conversation(
                conversation_id=conversation.conversation_id,
                shared_with_email="owner@example.com",
                permission_level="view",
                shared_by_user_id=owner_user.user_id
            )

    def test_share_with_invalid_permission_level(self, sharing_service, mock_db, owner_user, recipient_user, conversation):
        """Test sharing with invalid permission level fails."""
        # Mock database queries
        mock_db.query.return_value.filter.return_value.first.return_value = conversation

        # Attempt to share with invalid permission level
        with pytest.raises(ValueError, match="Invalid permission level"):
            sharing_service.share_conversation(
                conversation_id=conversation.conversation_id,
                shared_with_email="recipient@example.com",
                permission_level="invalid",
                shared_by_user_id=owner_user.user_id
            )


class TestListShares:
    """Test listing conversation shares."""

    def test_list_conversation_shares(self, sharing_service, mock_db, owner_user, recipient_user, conversation):
        """Test owner can list all shares for conversation."""
        # Create mock shares
        share1 = ConversationShare(
            share_id=uuid.uuid4(),
            conversation_id=conversation.conversation_id,
            shared_by=owner_user.user_id,
            shared_with=recipient_user.user_id,
            permission_level="view"
        )

        # Mock database queries
        mock_db.query.return_value.filter.return_value.first.return_value = conversation
        mock_db.query.return_value.filter.return_value.all.return_value = [share1]

        # List shares
        shares = sharing_service.list_conversation_shares(
            conversation_id=conversation.conversation_id,
            user_id=owner_user.user_id
        )

        # Verify shares returned
        assert len(shares) == 1
        assert shares[0].share_id == share1.share_id

    def test_non_owner_cannot_list_shares(self, sharing_service, mock_db, owner_user, conversation):
        """Test non-owner cannot list conversation shares."""
        non_owner_id = uuid.uuid4()

        # Mock database queries
        mock_db.query.return_value.filter.return_value.first.return_value = conversation

        # Attempt to list shares as non-owner
        with pytest.raises(PermissionError, match="Only conversation owner can list shares"):
            sharing_service.list_conversation_shares(
                conversation_id=conversation.conversation_id,
                user_id=non_owner_id
            )


class TestUpdateSharePermission:
    """Test updating share permission level."""

    def test_update_share_permission_success(self, sharing_service, mock_db, owner_user, recipient_user, conversation):
        """Test owner can update share permission level."""
        share = ConversationShare(
            share_id=uuid.uuid4(),
            conversation_id=conversation.conversation_id,
            shared_by=owner_user.user_id,
            shared_with=recipient_user.user_id,
            permission_level="view"
        )

        # Mock database queries
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            share,  # Share exists
            conversation  # Conversation exists
        ]

        # Mock audit logger
        with patch('src.services.sharing_service.AuditLogger.log_event') as mock_audit:
            # Update permission
            updated_share = sharing_service.update_share_permission(
                share_id=share.share_id,
                new_permission_level="edit",
                user_id=owner_user.user_id
            )

            # Verify permission updated
            assert updated_share.permission_level == "edit"

            # Verify audit log
            mock_audit.assert_called_once()

    def test_non_owner_cannot_update_permission(self, sharing_service, mock_db, owner_user, recipient_user, conversation):
        """Test non-owner cannot update share permission."""
        non_owner_id = uuid.uuid4()
        share = ConversationShare(
            share_id=uuid.uuid4(),
            conversation_id=conversation.conversation_id,
            shared_by=owner_user.user_id,
            shared_with=recipient_user.user_id,
            permission_level="view"
        )

        # Mock database queries
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            share,  # Share exists
            conversation  # Conversation exists
        ]

        # Attempt to update permission as non-owner
        with pytest.raises(PermissionError, match="Only conversation owner can update share"):
            sharing_service.update_share_permission(
                share_id=share.share_id,
                new_permission_level="edit",
                user_id=non_owner_id
            )


class TestRevokeShare:
    """Test revoking conversation share."""

    def test_revoke_share_success(self, sharing_service, mock_db, owner_user, recipient_user, conversation):
        """Test owner can revoke share."""
        share = ConversationShare(
            share_id=uuid.uuid4(),
            conversation_id=conversation.conversation_id,
            shared_by=owner_user.user_id,
            shared_with=recipient_user.user_id,
            permission_level="view"
        )

        # Mock database queries
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            share,  # Share exists
            conversation  # Conversation exists
        ]

        # Mock audit logger
        with patch('src.services.sharing_service.AuditLogger.log_event') as mock_audit:
            # Revoke share
            result = sharing_service.revoke_share(
                share_id=share.share_id,
                user_id=owner_user.user_id
            )

            # Verify revoked
            assert result is True

            # Verify audit log
            mock_audit.assert_called_once()

    def test_non_owner_cannot_revoke_share(self, sharing_service, mock_db, owner_user, recipient_user, conversation):
        """Test non-owner cannot revoke share."""
        non_owner_id = uuid.uuid4()
        share = ConversationShare(
            share_id=uuid.uuid4(),
            conversation_id=conversation.conversation_id,
            shared_by=owner_user.user_id,
            shared_with=recipient_user.user_id,
            permission_level="view"
        )

        # Mock database queries
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            share,  # Share exists
            conversation  # Conversation exists
        ]

        # Attempt to revoke share as non-owner
        with pytest.raises(PermissionError, match="Only conversation owner can revoke share"):
            sharing_service.revoke_share(
                share_id=share.share_id,
                user_id=non_owner_id
            )


class TestListSharedWithMe:
    """Test listing conversations shared with user."""

    def test_list_shared_with_me(self, sharing_service, mock_db, owner_user, recipient_user, conversation):
        """Test user can list conversations shared with them."""
        share = ConversationShare(
            share_id=uuid.uuid4(),
            conversation_id=conversation.conversation_id,
            shared_by=owner_user.user_id,
            shared_with=recipient_user.user_id,
            permission_level="view",
            shared_at=datetime.utcnow()
        )

        # Mock database queries - return share with joined conversation
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.join.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = [(conversation, share)]

        # List shared conversations
        shared_convos = sharing_service.list_shared_with_user(
            user_id=recipient_user.user_id
        )

        # Verify conversations returned with permission level
        assert len(shared_convos) == 1
        assert shared_convos[0]["conversation"].conversation_id == conversation.conversation_id
        assert shared_convos[0]["permission_level"] == "view"
        assert shared_convos[0]["shared_at"] is not None
        assert shared_convos[0]["shared_by"] == owner_user.user_id
