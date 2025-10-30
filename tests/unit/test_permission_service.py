"""
Unit Tests for PermissionService

Tests granular permission checking with ownership-based access control.
Phase 2 - Task Group 8: Granular Permission System

Test Coverage:
- Ownership-based access (user can access own conversation)
- Shared resource access (user can access shared conversation)
- No access to other users' conversations
- Admin can access all conversations
- Superadmin can access all conversations
- Viewer can only read shared conversations
- Message ownership through conversation
- Permission level enforcement (view vs comment vs edit)
"""

import uuid
import pytest
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

from src.services.permission_service import PermissionService
from src.models.conversation import Conversation
from src.models.message import Message
from src.models.conversation_share import ConversationShare
from src.models.user import User


@pytest.fixture
def permission_service():
    """Create PermissionService instance."""
    return PermissionService()


@pytest.fixture
def user_ids():
    """Generate test user IDs."""
    return {
        'owner': uuid.uuid4(),
        'viewer': uuid.uuid4(),
        'admin': uuid.uuid4(),
        'superadmin': uuid.uuid4(),
        'other': uuid.uuid4()
    }


@pytest.fixture
def conversation_id():
    """Generate test conversation ID."""
    return uuid.uuid4()


@pytest.fixture
def message_id():
    """Generate test message ID."""
    return uuid.uuid4()


class TestOwnershipAccess:
    """Test ownership-based access control."""

    def test_user_can_access_own_conversation(
        self, permission_service, user_ids, conversation_id
    ):
        """User can access their own conversation."""
        with patch('src.services.permission_service.get_db_context') as mock_db:
            # Mock conversation owned by user
            mock_session = MagicMock()
            mock_conversation = Conversation(
                conversation_id=conversation_id,
                user_id=user_ids['owner']
            )
            mock_session.query.return_value.filter.return_value.first.return_value = mock_conversation
            mock_db.return_value.__enter__.return_value = mock_session

            result = permission_service.user_can_access_conversation(
                user_ids['owner'], conversation_id, 'read'
            )

            assert result is True

    def test_user_cannot_access_others_conversation(
        self, permission_service, user_ids, conversation_id
    ):
        """User cannot access another user's conversation."""
        with patch('src.services.permission_service.get_db_context') as mock_db:
            # Mock conversation owned by different user
            mock_session = MagicMock()
            mock_conversation = Conversation(
                conversation_id=conversation_id,
                user_id=user_ids['owner']
            )
            mock_session.query.return_value.filter.return_value.first.return_value = mock_conversation
            mock_db.return_value.__enter__.return_value = mock_session

            # Mock no share
            with patch.object(permission_service, 'is_conversation_shared_with', return_value=False):
                # Mock user is not admin
                with patch.object(permission_service.rbac_service, 'user_has_role', return_value=False):
                    result = permission_service.user_can_access_conversation(
                        user_ids['other'], conversation_id, 'read'
                    )

                    assert result is False

    def test_is_conversation_owner_returns_true_for_owner(
        self, permission_service, user_ids, conversation_id
    ):
        """is_conversation_owner returns True for actual owner."""
        with patch('src.services.permission_service.get_db_context') as mock_db:
            mock_session = MagicMock()
            mock_conversation = Conversation(
                conversation_id=conversation_id,
                user_id=user_ids['owner']
            )
            mock_session.query.return_value.filter.return_value.first.return_value = mock_conversation
            mock_db.return_value.__enter__.return_value = mock_session

            result = permission_service.is_conversation_owner(
                user_ids['owner'], conversation_id
            )

            assert result is True

    def test_is_conversation_owner_returns_false_for_non_owner(
        self, permission_service, user_ids, conversation_id
    ):
        """is_conversation_owner returns False for non-owner."""
        with patch('src.services.permission_service.get_db_context') as mock_db:
            mock_session = MagicMock()
            mock_conversation = Conversation(
                conversation_id=conversation_id,
                user_id=user_ids['owner']
            )
            mock_session.query.return_value.filter.return_value.first.return_value = mock_conversation
            mock_db.return_value.__enter__.return_value = mock_session

            result = permission_service.is_conversation_owner(
                user_ids['other'], conversation_id
            )

            assert result is False


class TestSharedAccess:
    """Test shared resource access control."""

    def test_user_can_access_shared_conversation(
        self, permission_service, user_ids, conversation_id
    ):
        """User can access conversation shared with them."""
        with patch('src.services.permission_service.get_db_context') as mock_db:
            mock_session = MagicMock()

            # Mock conversation owned by different user
            mock_conversation = Conversation(
                conversation_id=conversation_id,
                user_id=user_ids['owner']
            )

            # Mock share exists
            mock_share = ConversationShare(
                share_id=uuid.uuid4(),
                conversation_id=conversation_id,
                shared_with=user_ids['viewer'],
                permission_level='view'
            )

            # Set up query mocks for multiple calls
            mock_query = mock_session.query.return_value
            mock_query.filter.return_value.first.side_effect = [
                mock_conversation,  # First call for conversation ownership check
                mock_share,  # Second call for share check in is_conversation_shared_with
                mock_share   # Third call for get_user_conversation_permission
            ]

            mock_db.return_value.__enter__.return_value = mock_session

            # Mock rbac_service to return False (not admin)
            with patch.object(permission_service.rbac_service, 'user_has_role', return_value=False):
                result = permission_service.user_can_access_conversation(
                    user_ids['viewer'], conversation_id, 'read'
                )

                assert result is True

    def test_is_conversation_shared_with_returns_true(
        self, permission_service, user_ids, conversation_id
    ):
        """is_conversation_shared_with returns True when share exists."""
        with patch('src.services.permission_service.get_db_context') as mock_db:
            mock_session = MagicMock()
            mock_share = ConversationShare(
                share_id=uuid.uuid4(),
                conversation_id=conversation_id,
                shared_with=user_ids['viewer'],
                permission_level='view'
            )
            mock_session.query.return_value.filter.return_value.first.return_value = mock_share
            mock_db.return_value.__enter__.return_value = mock_session

            result = permission_service.is_conversation_shared_with(
                user_ids['viewer'], conversation_id
            )

            assert result is True

    def test_is_conversation_shared_with_returns_false(
        self, permission_service, user_ids, conversation_id
    ):
        """is_conversation_shared_with returns False when no share exists."""
        with patch('src.services.permission_service.get_db_context') as mock_db:
            mock_session = MagicMock()
            mock_session.query.return_value.filter.return_value.first.return_value = None
            mock_db.return_value.__enter__.return_value = mock_session

            result = permission_service.is_conversation_shared_with(
                user_ids['viewer'], conversation_id
            )

            assert result is False


class TestRoleBasedAccess:
    """Test role-based access (admin/superadmin bypass)."""

    def test_admin_can_access_all_conversations(
        self, permission_service, user_ids, conversation_id
    ):
        """Admin can access any conversation regardless of ownership."""
        with patch('src.services.permission_service.get_db_context') as mock_db:
            mock_session = MagicMock()
            mock_conversation = Conversation(
                conversation_id=conversation_id,
                user_id=user_ids['owner']
            )
            mock_session.query.return_value.filter.return_value.first.return_value = mock_conversation
            mock_db.return_value.__enter__.return_value = mock_session

            # Mock user has admin role
            with patch.object(permission_service.rbac_service, 'user_has_role') as mock_role:
                mock_role.side_effect = lambda user_id, role: role == 'admin'

                result = permission_service.user_can_access_conversation(
                    user_ids['admin'], conversation_id, 'read'
                )

                assert result is True

    def test_superadmin_can_access_all_conversations(
        self, permission_service, user_ids, conversation_id
    ):
        """Superadmin can access any conversation regardless of ownership."""
        with patch('src.services.permission_service.get_db_context') as mock_db:
            mock_session = MagicMock()
            mock_conversation = Conversation(
                conversation_id=conversation_id,
                user_id=user_ids['owner']
            )
            mock_session.query.return_value.filter.return_value.first.return_value = mock_session

            # Mock user has superadmin role
            with patch.object(permission_service.rbac_service, 'user_has_role') as mock_role:
                mock_role.side_effect = lambda user_id, role: role == 'superadmin'

                result = permission_service.user_can_access_conversation(
                    user_ids['superadmin'], conversation_id, 'read'
                )

                assert result is True


class TestPermissionLevelEnforcement:
    """Test permission level enforcement (view/comment/edit)."""

    def test_get_user_conversation_permission_returns_level(
        self, permission_service, user_ids, conversation_id
    ):
        """get_user_conversation_permission returns correct permission level."""
        with patch('src.services.permission_service.get_db_context') as mock_db:
            mock_session = MagicMock()
            mock_share = ConversationShare(
                share_id=uuid.uuid4(),
                conversation_id=conversation_id,
                shared_with=user_ids['viewer'],
                permission_level='comment'
            )
            mock_session.query.return_value.filter.return_value.first.return_value = mock_share
            mock_db.return_value.__enter__.return_value = mock_session

            result = permission_service.get_user_conversation_permission(
                user_ids['viewer'], conversation_id
            )

            assert result == 'comment'

    def test_view_permission_allows_read_only(
        self, permission_service, user_ids, conversation_id
    ):
        """View permission allows read but not write."""
        with patch('src.services.permission_service.get_db_context') as mock_db:
            mock_session = MagicMock()

            # Mock conversation and share
            mock_conversation = Conversation(
                conversation_id=conversation_id,
                user_id=user_ids['owner']
            )
            mock_share = ConversationShare(
                share_id=uuid.uuid4(),
                conversation_id=conversation_id,
                shared_with=user_ids['viewer'],
                permission_level='view'
            )

            # Set up mocks for multiple calls
            mock_query = mock_session.query.return_value
            mock_query.filter.return_value.first.side_effect = [
                mock_conversation,  # Conversation ownership check
                mock_share,  # is_conversation_shared_with
                mock_share   # get_user_conversation_permission
            ]

            mock_db.return_value.__enter__.return_value = mock_session

            # Mock rbac_service
            with patch.object(permission_service.rbac_service, 'user_has_role', return_value=False):
                # Read should be allowed
                read_result = permission_service.user_can_access_conversation(
                    user_ids['viewer'], conversation_id, 'read'
                )
                assert read_result is True

            # Reset mocks for write check
            mock_query.filter.return_value.first.side_effect = [
                mock_conversation,
                mock_share,
                mock_share
            ]

            # Mock rbac_service
            with patch.object(permission_service.rbac_service, 'user_has_role', return_value=False):
                # Write should not be allowed
                write_result = permission_service.user_can_access_conversation(
                    user_ids['viewer'], conversation_id, 'write'
                )
                assert write_result is False

    def test_comment_permission_allows_read_and_write(
        self, permission_service, user_ids, conversation_id
    ):
        """Comment permission allows read and write."""
        with patch('src.services.permission_service.get_db_context') as mock_db:
            mock_session = MagicMock()

            mock_conversation = Conversation(
                conversation_id=conversation_id,
                user_id=user_ids['owner']
            )
            mock_share = ConversationShare(
                share_id=uuid.uuid4(),
                conversation_id=conversation_id,
                shared_with=user_ids['viewer'],
                permission_level='comment'
            )

            mock_query = mock_session.query.return_value
            mock_query.filter.return_value.first.side_effect = [
                mock_conversation,
                mock_share,
                mock_share
            ]

            mock_db.return_value.__enter__.return_value = mock_session

            # Mock rbac_service
            with patch.object(permission_service.rbac_service, 'user_has_role', return_value=False):
                # Read should be allowed
                read_result = permission_service.user_can_access_conversation(
                    user_ids['viewer'], conversation_id, 'read'
                )
                assert read_result is True

            # Reset mocks
            mock_query.filter.return_value.first.side_effect = [
                mock_conversation,
                mock_share,
                mock_share
            ]

            # Mock rbac_service
            with patch.object(permission_service.rbac_service, 'user_has_role', return_value=False):
                # Write should be allowed
                write_result = permission_service.user_can_access_conversation(
                    user_ids['viewer'], conversation_id, 'write'
                )
                assert write_result is True

    def test_edit_permission_allows_all_except_delete(
        self, permission_service, user_ids, conversation_id
    ):
        """Edit permission allows read, write, but only owner can delete."""
        with patch('src.services.permission_service.get_db_context') as mock_db:
            mock_session = MagicMock()

            mock_conversation = Conversation(
                conversation_id=conversation_id,
                user_id=user_ids['owner']
            )
            mock_share = ConversationShare(
                share_id=uuid.uuid4(),
                conversation_id=conversation_id,
                shared_with=user_ids['viewer'],
                permission_level='edit'
            )

            mock_query = mock_session.query.return_value
            mock_query.filter.return_value.first.side_effect = [
                mock_conversation,
                mock_share,
                mock_share
            ]

            mock_db.return_value.__enter__.return_value = mock_session

            # Mock rbac_service
            with patch.object(permission_service.rbac_service, 'user_has_role', return_value=False):
                # Read should be allowed
                read_result = permission_service.user_can_access_conversation(
                    user_ids['viewer'], conversation_id, 'read'
                )
                assert read_result is True

            # Reset mocks
            mock_query.filter.return_value.first.side_effect = [
                mock_conversation,
                mock_share,
                mock_share
            ]

            # Mock rbac_service
            with patch.object(permission_service.rbac_service, 'user_has_role', return_value=False):
                # Write should be allowed
                write_result = permission_service.user_can_access_conversation(
                    user_ids['viewer'], conversation_id, 'write'
                )
                assert write_result is True

            # Reset mocks
            mock_query.filter.return_value.first.side_effect = [
                mock_conversation,
                mock_share,
                mock_share
            ]

            # Mock rbac_service
            with patch.object(permission_service.rbac_service, 'user_has_role', return_value=False):
                # Delete should not be allowed (only owner)
                delete_result = permission_service.user_can_access_conversation(
                    user_ids['viewer'], conversation_id, 'delete'
                )
                assert delete_result is False


class TestMessageAccess:
    """Test message access through conversation ownership."""

    def test_user_can_access_message_in_own_conversation(
        self, permission_service, user_ids, conversation_id, message_id
    ):
        """User can access messages in their own conversation."""
        with patch('src.services.permission_service.get_db_context') as mock_db:
            mock_session = MagicMock()

            mock_message = Message(
                message_id=message_id,
                conversation_id=conversation_id,
                role='user',
                content='Test message'
            )
            mock_conversation = Conversation(
                conversation_id=conversation_id,
                user_id=user_ids['owner']
            )

            # First query for message, second for conversation
            mock_query = mock_session.query.return_value
            mock_query.filter.return_value.first.side_effect = [
                mock_message,
                mock_conversation
            ]

            mock_db.return_value.__enter__.return_value = mock_session

            result = permission_service.user_can_access_message(
                user_ids['owner'], message_id, 'read'
            )

            assert result is True

    def test_user_cannot_access_message_in_others_conversation(
        self, permission_service, user_ids, conversation_id, message_id
    ):
        """User cannot access messages in another user's conversation."""
        with patch('src.services.permission_service.get_db_context') as mock_db:
            mock_session = MagicMock()

            mock_message = Message(
                message_id=message_id,
                conversation_id=conversation_id,
                role='user',
                content='Test message'
            )
            mock_conversation = Conversation(
                conversation_id=conversation_id,
                user_id=user_ids['owner']
            )

            mock_query = mock_session.query.return_value
            mock_query.filter.return_value.first.side_effect = [
                mock_message,
                mock_conversation,
                None  # No share
            ]

            mock_db.return_value.__enter__.return_value = mock_session

            # Mock user is not admin
            with patch.object(permission_service.rbac_service, 'user_has_role', return_value=False):
                result = permission_service.user_can_access_message(
                    user_ids['other'], message_id, 'read'
                )

                assert result is False
