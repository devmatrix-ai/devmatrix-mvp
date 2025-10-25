"""
Unit Tests for Authorization and Access Control (Group 4)

Tests for:
- Ownership validation on conversation endpoints
- Superuser bypass functionality
- 403 for unauthorized access
- 404 for non-existent resources
- Ownership validation on message endpoints
"""

import os
import sys
import uuid
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from fastapi import HTTPException, Request

# Set up test environment variables before importing
os.environ['JWT_SECRET'] = 'test-jwt-secret-key-minimum-32-characters-long'
os.environ['DATABASE_URL'] = 'postgresql://test:test@localhost:5432/test_db'

from src.models.user import User
from src.models.conversation import Conversation


class TestOwnershipValidation:
    """Test ownership validation middleware"""

    def test_user_can_access_own_conversation(self):
        """Test that a user can access their own conversation"""
        # Import directly to avoid src.api module issues
        sys.path.insert(0, '/Users/arieleduardoghysels/code/devmatrix/devmatrix-mvp')

        # Arrange
        user_id = uuid.uuid4()
        conversation_id = uuid.uuid4()

        user = Mock(spec=User)
        user.user_id = user_id
        user.is_superuser = False

        conversation = Mock(spec=Conversation)
        conversation.conversation_id = conversation_id
        conversation.user_id = user_id

        # Mock database query before importing middleware
        with patch('src.config.database.get_db_context') as mock_db:
            mock_session = MagicMock()
            mock_db.return_value.__enter__.return_value = mock_session
            mock_session.query.return_value.filter.return_value.first.return_value = conversation

            # Import decorator after mocking
            from src.api.middleware.ownership_middleware import require_resource_ownership

            # Create decorated function
            @require_resource_ownership("conversation")
            async def test_endpoint(conversation_id: str, current_user: User):
                return {"status": "success"}

            # Act
            import asyncio
            result = asyncio.run(test_endpoint(
                conversation_id=str(conversation_id),
                current_user=user
            ))

            # Assert
            assert result["status"] == "success"

    def test_user_cannot_access_other_conversation(self):
        """Test that a user cannot access another user's conversation (403)"""
        # Arrange
        user_id = uuid.uuid4()
        other_user_id = uuid.uuid4()
        conversation_id = uuid.uuid4()

        user = Mock(spec=User)
        user.user_id = user_id
        user.is_superuser = False

        conversation = Mock(spec=Conversation)
        conversation.conversation_id = conversation_id
        conversation.user_id = other_user_id  # Different user

        # Mock database query before importing middleware
        with patch('src.config.database.get_db_context') as mock_db:
            mock_session = MagicMock()
            mock_db.return_value.__enter__.return_value = mock_session
            mock_session.query.return_value.filter.return_value.first.return_value = conversation

            # Import decorator
            from src.api.middleware.ownership_middleware import require_resource_ownership

            # Create decorated function
            @require_resource_ownership("conversation")
            async def test_endpoint(conversation_id: str, current_user: User):
                return {"status": "success"}

            # Act & Assert
            import asyncio
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(test_endpoint(
                    conversation_id=str(conversation_id),
                    current_user=user
                ))

            assert exc_info.value.status_code == 403
            assert "Access denied" in exc_info.value.detail

    def test_superuser_can_access_any_conversation(self):
        """Test that a superuser can access any conversation"""
        # Arrange
        superuser_id = uuid.uuid4()
        other_user_id = uuid.uuid4()
        conversation_id = uuid.uuid4()

        superuser = Mock(spec=User)
        superuser.user_id = superuser_id
        superuser.is_superuser = True  # Superuser flag

        conversation = Mock(spec=Conversation)
        conversation.conversation_id = conversation_id
        conversation.user_id = other_user_id  # Different user

        # Mock database query before importing middleware
        with patch('src.config.database.get_db_context') as mock_db:
            mock_session = MagicMock()
            mock_db.return_value.__enter__.return_value = mock_session
            mock_session.query.return_value.filter.return_value.first.return_value = conversation

            # Import decorator
            from src.api.middleware.ownership_middleware import require_resource_ownership

            # Create decorated function
            @require_resource_ownership("conversation")
            async def test_endpoint(conversation_id: str, current_user: User):
                return {"status": "success"}

            # Act
            import asyncio
            result = asyncio.run(test_endpoint(
                conversation_id=str(conversation_id),
                current_user=superuser
            ))

            # Assert
            assert result["status"] == "success"

    def test_404_for_nonexistent_conversation(self):
        """Test that accessing a non-existent conversation returns 404"""
        # Arrange
        user_id = uuid.uuid4()
        conversation_id = uuid.uuid4()

        user = Mock(spec=User)
        user.user_id = user_id
        user.is_superuser = False

        # Mock database query - returns None (not found)
        with patch('src.config.database.get_db_context') as mock_db:
            mock_session = MagicMock()
            mock_db.return_value.__enter__.return_value = mock_session
            mock_session.query.return_value.filter.return_value.first.return_value = None

            # Import decorator
            from src.api.middleware.ownership_middleware import require_resource_ownership

            # Create decorated function
            @require_resource_ownership("conversation")
            async def test_endpoint(conversation_id: str, current_user: User):
                return {"status": "success"}

            # Act & Assert
            import asyncio
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(test_endpoint(
                    conversation_id=str(conversation_id),
                    current_user=user
                ))

            # Should return 404 (not 403) for security - don't reveal existence
            assert exc_info.value.status_code == 404
            assert "not found" in exc_info.value.detail.lower()

    def test_user_cannot_update_other_conversation(self):
        """Test that a user cannot update another user's conversation (403)"""
        # Arrange
        user_id = uuid.uuid4()
        other_user_id = uuid.uuid4()
        conversation_id = uuid.uuid4()

        user = Mock(spec=User)
        user.user_id = user_id
        user.is_superuser = False

        conversation = Mock(spec=Conversation)
        conversation.conversation_id = conversation_id
        conversation.user_id = other_user_id

        # Mock database query
        with patch('src.config.database.get_db_context') as mock_db:
            mock_session = MagicMock()
            mock_db.return_value.__enter__.return_value = mock_session
            mock_session.query.return_value.filter.return_value.first.return_value = conversation

            # Import decorator
            from src.api.middleware.ownership_middleware import require_resource_ownership

            # Create decorated function (simulating PUT endpoint)
            @require_resource_ownership("conversation")
            async def update_endpoint(conversation_id: str, current_user: User):
                return {"status": "updated"}

            # Act & Assert
            import asyncio
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(update_endpoint(
                    conversation_id=str(conversation_id),
                    current_user=user
                ))

            assert exc_info.value.status_code == 403

    def test_user_cannot_delete_other_conversation(self):
        """Test that a user cannot delete another user's conversation (403)"""
        # Arrange
        user_id = uuid.uuid4()
        other_user_id = uuid.uuid4()
        conversation_id = uuid.uuid4()

        user = Mock(spec=User)
        user.user_id = user_id
        user.is_superuser = False

        conversation = Mock(spec=Conversation)
        conversation.conversation_id = conversation_id
        conversation.user_id = other_user_id

        # Mock database query
        with patch('src.config.database.get_db_context') as mock_db:
            mock_session = MagicMock()
            mock_db.return_value.__enter__.return_value = mock_session
            mock_session.query.return_value.filter.return_value.first.return_value = conversation

            # Import decorator
            from src.api.middleware.ownership_middleware import require_resource_ownership

            # Create decorated function (simulating DELETE endpoint)
            @require_resource_ownership("conversation")
            async def delete_endpoint(conversation_id: str, current_user: User):
                return {"status": "deleted"}

            # Act & Assert
            import asyncio
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(delete_endpoint(
                    conversation_id=str(conversation_id),
                    current_user=user
                ))

            assert exc_info.value.status_code == 403

    def test_ownership_validation_on_message_endpoints(self):
        """Test that message endpoints inherit conversation ownership validation"""
        # Arrange - user tries to add message to someone else's conversation
        user_id = uuid.uuid4()
        other_user_id = uuid.uuid4()
        conversation_id = uuid.uuid4()
        message_id = uuid.uuid4()

        user = Mock(spec=User)
        user.user_id = user_id
        user.is_superuser = False

        conversation = Mock(spec=Conversation)
        conversation.conversation_id = conversation_id
        conversation.user_id = other_user_id  # Different user

        # Mock database query
        with patch('src.config.database.get_db_context') as mock_db:
            mock_session = MagicMock()
            mock_db.return_value.__enter__.return_value = mock_session
            mock_session.query.return_value.filter.return_value.first.return_value = conversation

            # Import decorator
            from src.api.middleware.ownership_middleware import require_resource_ownership

            # Create decorated function (simulating POST message endpoint)
            @require_resource_ownership("conversation")
            async def create_message_endpoint(
                conversation_id: str,
                message_id: str,
                current_user: User
            ):
                return {"status": "message_created"}

            # Act & Assert
            import asyncio
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(create_message_endpoint(
                    conversation_id=str(conversation_id),
                    message_id=str(message_id),
                    current_user=user
                ))

            # Should be denied with 403
            assert exc_info.value.status_code == 403
            assert "Access denied" in exc_info.value.detail
