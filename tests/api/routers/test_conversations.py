"""
Tests for Conversations API Router

Tests conversation sharing and collaboration endpoints.

Author: DevMatrix Team
Date: 2025-11-03
"""

import pytest
from uuid import uuid4, UUID
from unittest.mock import MagicMock, patch, Mock
from datetime import datetime

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.routers.conversations import router
from src.models.user import User


@pytest.fixture
def mock_current_user():
    """Create mock authenticated user."""
    user = MagicMock(spec=User)
    user.user_id = uuid4()
    user.username = "testuser"
    user.email = "test@example.com"
    return user


@pytest.fixture
def mock_sharing_service():
    """Create mock SharingService."""
    return MagicMock()


@pytest.fixture
def mock_postgres_manager():
    """Create mock PostgresManager."""
    return MagicMock()


@pytest.fixture
def client(mock_current_user):
    """Create test client with conversations router."""
    test_app = FastAPI()
    test_app.include_router(router, prefix="/api/v1/conversations")

    # Override auth dependency
    def override_get_current_user():
        return mock_current_user

    from src.api.middleware.auth_middleware import get_current_user
    test_app.dependency_overrides[get_current_user] = override_get_current_user

    return TestClient(test_app)


@pytest.fixture
def sample_conversation_id():
    """Sample conversation UUID."""
    return uuid4()


@pytest.fixture
def sample_share_id():
    """Sample share UUID."""
    return uuid4()


# ============================================================================
# GET /api/v1/conversations Tests
# ============================================================================

def test_list_conversations_success(client, mock_current_user, mock_postgres_manager):
    """Test successful conversation listing."""
    mock_results = [
        {
            'id': str(uuid4()),
            'created_at': datetime.now(),
            'updated_at': datetime.now(),
            'metadata': {'workspace_id': 'ws-1'},
            'message_count': 5,
            'last_message': 'Hello, how are you?'
        },
        {
            'id': str(uuid4()),
            'created_at': datetime.now(),
            'updated_at': datetime.now(),
            'metadata': None,
            'message_count': 2,
            'last_message': 'This is a test message that is very long and should be truncated to only show the first 100 characters as a preview'
        }
    ]

    mock_postgres_manager._execute.return_value = mock_results

    with patch('src.api.routers.conversations.PostgresManager', return_value=mock_postgres_manager):
        response = client.get("/api/v1/conversations/")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]['message_count'] == 5
    assert data[1]['last_message_preview'] is not None
    assert len(data[1]['last_message_preview']) <= 103  # 100 chars + "..."


def test_list_conversations_with_workspace_filter(client, mock_current_user, mock_postgres_manager):
    """Test conversation listing filtered by workspace."""
    mock_postgres_manager._execute.return_value = []

    with patch('src.api.routers.conversations.PostgresManager', return_value=mock_postgres_manager):
        response = client.get("/api/v1/conversations/?workspace_id=ws-123")

    assert response.status_code == 200
    # Verify workspace_id was passed in query
    mock_postgres_manager._execute.assert_called_once()
    call_args = mock_postgres_manager._execute.call_args
    assert 'ws-123' in call_args[0][1]  # Check params tuple


def test_list_conversations_with_limit(client, mock_current_user, mock_postgres_manager):
    """Test conversation listing with custom limit."""
    mock_postgres_manager._execute.return_value = []

    with patch('src.api.routers.conversations.PostgresManager', return_value=mock_postgres_manager):
        response = client.get("/api/v1/conversations/?limit=25")

    assert response.status_code == 200
    # Verify limit was passed in query
    call_args = mock_postgres_manager._execute.call_args
    assert 25 in call_args[0][1]  # Check params tuple


def test_list_conversations_empty_result(client, mock_current_user, mock_postgres_manager):
    """Test conversation listing with no results."""
    mock_postgres_manager._execute.return_value = []

    with patch('src.api.routers.conversations.PostgresManager', return_value=mock_postgres_manager):
        response = client.get("/api/v1/conversations/")

    assert response.status_code == 200
    data = response.json()
    assert data == []


def test_list_conversations_database_error(client, mock_current_user, mock_postgres_manager):
    """Test conversation listing handles database errors."""
    mock_postgres_manager._execute.side_effect = Exception("Database connection failed")

    with patch('src.api.routers.conversations.PostgresManager', return_value=mock_postgres_manager):
        response = client.get("/api/v1/conversations/")

    assert response.status_code == 500
    assert "Database connection failed" in response.json()['detail']


# ============================================================================
# POST /api/v1/conversations/{conversation_id}/share Tests
# ============================================================================

def test_share_conversation_success(client, sample_conversation_id, mock_current_user, mock_sharing_service):
    """Test successful conversation sharing."""
    mock_share = MagicMock()
    mock_share.share_id = uuid4()
    mock_share.conversation_id = sample_conversation_id
    mock_share.shared_with = uuid4()
    mock_share.permission_level = "view"
    mock_share.shared_at = datetime.now()

    mock_sharing_service.share_conversation.return_value = mock_share

    mock_recipient = MagicMock()
    mock_recipient.email = "recipient@example.com"

    with patch('src.api.routers.conversations.SharingService', return_value=mock_sharing_service), \
         patch('src.api.routers.conversations.get_db_context') as mock_db_context:

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_recipient
        mock_db_context.return_value.__enter__.return_value = mock_db

        response = client.post(
            f"/api/v1/conversations/{sample_conversation_id}/share",
            json={
                "user_email": "recipient@example.com",
                "permission_level": "view"
            }
        )

    assert response.status_code == 201
    data = response.json()
    assert data['conversation_id'] == str(sample_conversation_id)
    assert data['permission_level'] == "view"
    assert data['shared_with_email'] == "recipient@example.com"


def test_share_conversation_invalid_permission_level(client, sample_conversation_id, mock_sharing_service):
    """Test sharing with invalid permission level."""
    mock_sharing_service.share_conversation.side_effect = ValueError("Invalid permission level")

    with patch('src.api.routers.conversations.SharingService', return_value=mock_sharing_service):
        response = client.post(
            f"/api/v1/conversations/{sample_conversation_id}/share",
            json={
                "user_email": "recipient@example.com",
                "permission_level": "invalid"
            }
        )

    assert response.status_code == 400
    assert "Invalid permission level" in response.json()['detail']


def test_share_conversation_not_owner(client, sample_conversation_id, mock_sharing_service):
    """Test sharing conversation when not the owner."""
    mock_sharing_service.share_conversation.side_effect = PermissionError(
        "Only the conversation owner can share"
    )

    with patch('src.api.routers.conversations.SharingService', return_value=mock_sharing_service):
        response = client.post(
            f"/api/v1/conversations/{sample_conversation_id}/share",
            json={
                "user_email": "recipient@example.com",
                "permission_level": "view"
            }
        )

    assert response.status_code == 403
    assert "Only the conversation owner can share" in response.json()['detail']


def test_share_conversation_already_shared(client, sample_conversation_id, mock_sharing_service):
    """Test sharing conversation that's already shared with user."""
    mock_sharing_service.share_conversation.side_effect = ValueError(
        "Conversation already shared with this user"
    )

    with patch('src.api.routers.conversations.SharingService', return_value=mock_sharing_service):
        response = client.post(
            f"/api/v1/conversations/{sample_conversation_id}/share",
            json={
                "user_email": "recipient@example.com",
                "permission_level": "view"
            }
        )

    assert response.status_code == 400


def test_share_conversation_recipient_not_found(client, sample_conversation_id, mock_sharing_service):
    """Test sharing with non-existent recipient."""
    mock_sharing_service.share_conversation.side_effect = ValueError(
        "Recipient user not found"
    )

    with patch('src.api.routers.conversations.SharingService', return_value=mock_sharing_service):
        response = client.post(
            f"/api/v1/conversations/{sample_conversation_id}/share",
            json={
                "user_email": "nonexistent@example.com",
                "permission_level": "view"
            }
        )

    assert response.status_code == 400


# ============================================================================
# GET /api/v1/conversations/{conversation_id}/shares Tests
# ============================================================================

def test_list_conversation_shares_success(client, sample_conversation_id, mock_sharing_service):
    """Test successful listing of conversation shares."""
    mock_shares = [
        MagicMock(
            share_id=uuid4(),
            shared_with=uuid4(),
            permission_level="view",
            shared_at=datetime.now()
        ),
        MagicMock(
            share_id=uuid4(),
            shared_with=uuid4(),
            permission_level="edit",
            shared_at=datetime.now()
        )
    ]

    mock_sharing_service.list_conversation_shares.return_value = mock_shares

    mock_users = [
        MagicMock(email="user1@example.com", username="user1"),
        MagicMock(email="user2@example.com", username="user2")
    ]

    with patch('src.api.routers.conversations.SharingService', return_value=mock_sharing_service), \
         patch('src.api.routers.conversations.get_db_context') as mock_db_context:

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.side_effect = mock_users
        mock_db_context.return_value.__enter__.return_value = mock_db

        response = client.get(f"/api/v1/conversations/{sample_conversation_id}/shares")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]['permission_level'] == "view"
    assert data[1]['permission_level'] == "edit"


def test_list_conversation_shares_empty(client, sample_conversation_id, mock_sharing_service):
    """Test listing shares when none exist."""
    mock_sharing_service.list_conversation_shares.return_value = []

    with patch('src.api.routers.conversations.SharingService', return_value=mock_sharing_service), \
         patch('src.api.routers.conversations.get_db_context'):
        response = client.get(f"/api/v1/conversations/{sample_conversation_id}/shares")

    assert response.status_code == 200
    assert response.json() == []


def test_list_conversation_shares_not_owner(client, sample_conversation_id, mock_sharing_service):
    """Test listing shares when not the owner."""
    mock_sharing_service.list_conversation_shares.side_effect = PermissionError(
        "Only the conversation owner can list shares"
    )

    with patch('src.api.routers.conversations.SharingService', return_value=mock_sharing_service):
        response = client.get(f"/api/v1/conversations/{sample_conversation_id}/shares")

    assert response.status_code == 403


# ============================================================================
# PATCH /api/v1/conversations/{conversation_id}/shares/{share_id} Tests
# ============================================================================

def test_update_share_permission_success(client, sample_conversation_id, sample_share_id, mock_sharing_service):
    """Test successful share permission update."""
    mock_updated_share = MagicMock()
    mock_updated_share.share_id = sample_share_id
    mock_updated_share.conversation_id = sample_conversation_id
    mock_updated_share.shared_with = uuid4()
    mock_updated_share.permission_level = "edit"
    mock_updated_share.shared_at = datetime.now()

    mock_sharing_service.update_share_permission.return_value = mock_updated_share

    mock_recipient = MagicMock(email="recipient@example.com")

    with patch('src.api.routers.conversations.SharingService', return_value=mock_sharing_service), \
         patch('src.api.routers.conversations.get_db_context') as mock_db_context:

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_recipient
        mock_db_context.return_value.__enter__.return_value = mock_db

        response = client.patch(
            f"/api/v1/conversations/{sample_conversation_id}/shares/{sample_share_id}",
            json={"permission_level": "edit"}
        )

    assert response.status_code == 200
    data = response.json()
    assert data['permission_level'] == "edit"
    assert data['share_id'] == str(sample_share_id)


def test_update_share_permission_invalid_level(client, sample_conversation_id, sample_share_id, mock_sharing_service):
    """Test updating to invalid permission level."""
    mock_sharing_service.update_share_permission.side_effect = ValueError(
        "Invalid permission level"
    )

    with patch('src.api.routers.conversations.SharingService', return_value=mock_sharing_service):
        response = client.patch(
            f"/api/v1/conversations/{sample_conversation_id}/shares/{sample_share_id}",
            json={"permission_level": "invalid"}
        )

    assert response.status_code == 400


def test_update_share_permission_not_owner(client, sample_conversation_id, sample_share_id, mock_sharing_service):
    """Test updating share permission when not owner."""
    mock_sharing_service.update_share_permission.side_effect = PermissionError(
        "Only the conversation owner can update permissions"
    )

    with patch('src.api.routers.conversations.SharingService', return_value=mock_sharing_service):
        response = client.patch(
            f"/api/v1/conversations/{sample_conversation_id}/shares/{sample_share_id}",
            json={"permission_level": "edit"}
        )

    assert response.status_code == 403


# ============================================================================
# DELETE /api/v1/conversations/{conversation_id}/shares/{share_id} Tests
# ============================================================================

def test_revoke_share_success(client, sample_conversation_id, sample_share_id, mock_sharing_service):
    """Test successful share revocation."""
    mock_sharing_service.revoke_share.return_value = None

    with patch('src.api.routers.conversations.SharingService', return_value=mock_sharing_service):
        response = client.delete(
            f"/api/v1/conversations/{sample_conversation_id}/shares/{sample_share_id}"
        )

    assert response.status_code == 204


def test_revoke_share_not_found(client, sample_conversation_id, sample_share_id, mock_sharing_service):
    """Test revoking non-existent share."""
    mock_sharing_service.revoke_share.side_effect = ValueError("Share not found")

    with patch('src.api.routers.conversations.SharingService', return_value=mock_sharing_service):
        response = client.delete(
            f"/api/v1/conversations/{sample_conversation_id}/shares/{sample_share_id}"
        )

    assert response.status_code == 404


def test_revoke_share_not_owner(client, sample_conversation_id, sample_share_id, mock_sharing_service):
    """Test revoking share when not the owner."""
    mock_sharing_service.revoke_share.side_effect = PermissionError(
        "Only the conversation owner can revoke shares"
    )

    with patch('src.api.routers.conversations.SharingService', return_value=mock_sharing_service):
        response = client.delete(
            f"/api/v1/conversations/{sample_conversation_id}/shares/{sample_share_id}"
        )

    assert response.status_code == 403


# ============================================================================
# GET /api/v1/conversations/shared-with-me Tests
# ============================================================================

def test_list_shared_with_me_success(client, mock_current_user, mock_sharing_service):
    """Test successful listing of conversations shared with user."""
    mock_conversations = [
        {
            "conversation": MagicMock(
                conversation_id=uuid4(),
                user_id=uuid4(),
                title="Shared Conversation 1"
            ),
            "permission_level": "view",
            "shared_at": datetime.now(),
            "shared_by": uuid4()
        },
        {
            "conversation": MagicMock(
                conversation_id=uuid4(),
                user_id=uuid4(),
                title=None  # Test untitled conversation
            ),
            "permission_level": "edit",
            "shared_at": datetime.now(),
            "shared_by": uuid4()
        }
    ]

    mock_sharing_service.list_shared_with_user.return_value = mock_conversations

    mock_owners = [
        MagicMock(username="owner1"),
        MagicMock(username="owner2")
    ]

    with patch('src.api.routers.conversations.SharingService', return_value=mock_sharing_service), \
         patch('src.api.routers.conversations.get_db_context') as mock_db_context:

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.side_effect = mock_owners
        mock_db_context.return_value.__enter__.return_value = mock_db

        response = client.get("/api/v1/conversations/shared-with-me")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]['permission_level'] == "view"
    assert data[0]['title'] == "Shared Conversation 1"
    assert data[1]['title'] == "Untitled Conversation"  # Default title


def test_list_shared_with_me_empty(client, mock_current_user, mock_sharing_service):
    """Test listing shared conversations when none exist."""
    mock_sharing_service.list_shared_with_user.return_value = []

    with patch('src.api.routers.conversations.SharingService', return_value=mock_sharing_service), \
         patch('src.api.routers.conversations.get_db_context'):
        response = client.get("/api/v1/conversations/shared-with-me")

    assert response.status_code == 200
    assert response.json() == []


def test_list_shared_with_me_database_error(client, mock_sharing_service):
    """Test shared conversations listing handles database errors."""
    mock_sharing_service.list_shared_with_user.side_effect = Exception("Database error")

    with patch('src.api.routers.conversations.SharingService', return_value=mock_sharing_service):
        response = client.get("/api/v1/conversations/shared-with-me")

    assert response.status_code == 500


# ============================================================================
# Unit Tests for Request Models
# ============================================================================

@pytest.mark.unit
class TestConversationsRequestModels:
    """Unit tests for request/response models."""

    def test_share_conversation_request_model(self):
        """Test ShareConversationRequest model validation."""
        from src.api.routers.conversations import ShareConversationRequest

        # Valid request
        request = ShareConversationRequest(
            user_email="test@example.com",
            permission_level="view"
        )
        assert request.user_email == "test@example.com"
        assert request.permission_level == "view"

    def test_update_share_permission_request_model(self):
        """Test UpdateSharePermissionRequest model validation."""
        from src.api.routers.conversations import UpdateSharePermissionRequest

        request = UpdateSharePermissionRequest(permission_level="edit")
        assert request.permission_level == "edit"

    def test_conversation_summary_model(self):
        """Test ConversationSummary model."""
        from src.api.routers.conversations import ConversationSummary

        summary = ConversationSummary(
            id=str(uuid4()),
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
            message_count=5,
            last_message_preview="Test message",
            workspace_id="ws-123"
        )
        assert summary.message_count == 5
        assert summary.workspace_id == "ws-123"

