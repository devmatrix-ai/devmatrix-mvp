"""
Tests for Chat API Router

Tests conversation and message management endpoints.

Author: DevMatrix Team
Date: 2025-11-03
"""

import pytest
from uuid import uuid4
from unittest.mock import MagicMock, patch
from datetime import datetime

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.routers.chat import router
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
def client(mock_current_user):
    """Create test client with chat router."""
    test_app = FastAPI()
    test_app.include_router(router, prefix="/api/v1")

    # Override auth dependency
    def override_get_current_user():
        return mock_current_user

    from src.api.middleware.auth_middleware import get_current_user
    test_app.dependency_overrides[get_current_user] = override_get_current_user

    return TestClient(test_app)


@pytest.fixture
def sample_conversation_id():
    """Sample conversation ID."""
    return str(uuid4())


@pytest.fixture
def sample_message_id():
    """Sample message ID."""
    return str(uuid4())


@pytest.fixture
def mock_postgres_manager():
    """Create mock PostgresManager."""
    return MagicMock()


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
            'message_count': 0,
            'last_message': None
        }
    ]
    mock_postgres_manager._execute.return_value = mock_results

    with patch('src.api.routers.chat.PostgresManager', return_value=mock_postgres_manager):
        response = client.get("/api/v1/conversations")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]['message_count'] == 5


def test_list_conversations_with_workspace_filter(client, mock_postgres_manager):
    """Test conversation listing filtered by workspace."""
    mock_postgres_manager._execute.return_value = []

    with patch('src.api.routers.chat.PostgresManager', return_value=mock_postgres_manager):
        response = client.get("/api/v1/conversations?workspace_id=ws-123")

    assert response.status_code == 200


def test_list_conversations_with_limit(client, mock_postgres_manager):
    """Test conversation listing with custom limit."""
    mock_postgres_manager._execute.return_value = []

    with patch('src.api.routers.chat.PostgresManager', return_value=mock_postgres_manager):
        response = client.get("/api/v1/conversations?limit=25")

    assert response.status_code == 200


def test_list_conversations_empty(client, mock_postgres_manager):
    """Test conversation listing with no results."""
    mock_postgres_manager._execute.return_value = []

    with patch('src.api.routers.chat.PostgresManager', return_value=mock_postgres_manager):
        response = client.get("/api/v1/conversations")

    assert response.status_code == 200
    assert response.json() == []


def test_list_conversations_database_error(client, mock_postgres_manager):
    """Test conversation listing handles database errors."""
    mock_postgres_manager._execute.side_effect = Exception("Database error")

    with patch('src.api.routers.chat.PostgresManager', return_value=mock_postgres_manager):
        response = client.get("/api/v1/conversations")

    assert response.status_code == 500


# ============================================================================
# GET /api/v1/conversations/{conversation_id} Tests
# ============================================================================

def test_get_conversation_success(client, sample_conversation_id, mock_postgres_manager):
    """Test successful conversation retrieval."""
    mock_conv = {
        'id': sample_conversation_id,
        'created_at': datetime.now(),
        'updated_at': datetime.now(),
        'metadata': {'workspace_id': 'ws-1'}
    }
    mock_messages = [
        {
            'id': str(uuid4()),
            'role': 'user',
            'content': 'Hello',
            'created_at': datetime.now(),
            'metadata': {}
        },
        {
            'id': str(uuid4()),
            'role': 'assistant',
            'content': 'Hi there!',
            'created_at': datetime.now(),
            'metadata': {}
        }
    ]
    mock_postgres_manager.get_conversation.return_value = mock_conv
    mock_postgres_manager.get_conversation_messages.return_value = mock_messages

    with patch('src.api.routers.chat.PostgresManager', return_value=mock_postgres_manager), \
         patch('src.api.routers.chat.require_resource_ownership', lambda x: lambda f: f):
        response = client.get(f"/api/v1/conversations/{sample_conversation_id}")

    assert response.status_code == 200
    data = response.json()
    assert data['id'] == sample_conversation_id
    assert len(data['messages']) == 2


def test_get_conversation_not_found(client, mock_postgres_manager):
    """Test getting non-existent conversation."""
    conv_id = str(uuid4())
    mock_postgres_manager.get_conversation.return_value = None

    with patch('src.api.routers.chat.PostgresManager', return_value=mock_postgres_manager), \
         patch('src.api.routers.chat.require_resource_ownership', lambda x: lambda f: f):
        response = client.get(f"/api/v1/conversations/{conv_id}")

    assert response.status_code == 404


def test_get_conversation_with_many_messages(client, sample_conversation_id, mock_postgres_manager):
    """Test conversation with many messages."""
    mock_conv = {
        'id': sample_conversation_id,
        'created_at': datetime.now(),
        'updated_at': datetime.now(),
        'metadata': {}
    }
    mock_messages = [
        {
            'id': str(uuid4()),
            'role': 'user' if i % 2 == 0 else 'assistant',
            'content': f'Message {i}',
            'created_at': datetime.now(),
            'metadata': {}
        }
        for i in range(50)
    ]
    mock_postgres_manager.get_conversation.return_value = mock_conv
    mock_postgres_manager.get_conversation_messages.return_value = mock_messages

    with patch('src.api.routers.chat.PostgresManager', return_value=mock_postgres_manager), \
         patch('src.api.routers.chat.require_resource_ownership', lambda x: lambda f: f):
        response = client.get(f"/api/v1/conversations/{sample_conversation_id}")

    data = response.json()
    assert len(data['messages']) == 50


# ============================================================================
# PUT /api/v1/conversations/{conversation_id} Tests
# ============================================================================

def test_update_conversation_success(client, sample_conversation_id, mock_postgres_manager):
    """Test successful conversation update."""
    mock_postgres_manager.update_conversation.return_value = {
        'id': sample_conversation_id,
        'updated_at': datetime.now()
    }

    with patch('src.api.routers.chat.PostgresManager', return_value=mock_postgres_manager), \
         patch('src.api.routers.chat.require_resource_ownership', lambda x: lambda f: f):
        response = client.put(
            f"/api/v1/conversations/{sample_conversation_id}",
            json={"metadata": {"workspace_id": "ws-new"}}
        )

    assert response.status_code == 200


def test_update_conversation_not_found(client, mock_postgres_manager):
    """Test updating non-existent conversation."""
    conv_id = str(uuid4())
    mock_postgres_manager.update_conversation.side_effect = ValueError("Not found")

    with patch('src.api.routers.chat.PostgresManager', return_value=mock_postgres_manager), \
         patch('src.api.routers.chat.require_resource_ownership', lambda x: lambda f: f):
        response = client.put(
            f"/api/v1/conversations/{conv_id}",
            json={"metadata": {}}
        )

    assert response.status_code == 404


# ============================================================================
# DELETE /api/v1/conversations/{conversation_id} Tests
# ============================================================================

def test_delete_conversation_success(client, sample_conversation_id, mock_postgres_manager):
    """Test successful conversation deletion."""
    mock_postgres_manager.delete_conversation.return_value = True

    with patch('src.api.routers.chat.PostgresManager', return_value=mock_postgres_manager), \
         patch('src.api.routers.chat.require_resource_ownership', lambda x: lambda f: f):
        response = client.delete(f"/api/v1/conversations/{sample_conversation_id}")

    assert response.status_code == 204


def test_delete_conversation_not_found(client, mock_postgres_manager):
    """Test deleting non-existent conversation."""
    conv_id = str(uuid4())
    mock_postgres_manager.delete_conversation.side_effect = ValueError("Not found")

    with patch('src.api.routers.chat.PostgresManager', return_value=mock_postgres_manager), \
         patch('src.api.routers.chat.require_resource_ownership', lambda x: lambda f: f):
        response = client.delete(f"/api/v1/conversations/{conv_id}")

    assert response.status_code == 404


# ============================================================================
# GET /api/v1/conversations/{conversation_id}/messages Tests
# ============================================================================

def test_get_messages_success(client, sample_conversation_id, mock_postgres_manager):
    """Test successful message retrieval."""
    mock_messages = [
        {
            'id': str(uuid4()),
            'role': 'user',
            'content': 'Hello',
            'created_at': datetime.now()
        }
    ]
    mock_postgres_manager.get_conversation_messages.return_value = mock_messages

    with patch('src.api.routers.chat.PostgresManager', return_value=mock_postgres_manager), \
         patch('src.api.routers.chat.require_resource_ownership', lambda x: lambda f: f):
        response = client.get(f"/api/v1/conversations/{sample_conversation_id}/messages")

    assert response.status_code == 200
    assert len(response.json()) == 1


def test_get_messages_with_pagination(client, sample_conversation_id, mock_postgres_manager):
    """Test message retrieval with pagination."""
    mock_postgres_manager.get_conversation_messages.return_value = []

    with patch('src.api.routers.chat.PostgresManager', return_value=mock_postgres_manager), \
         patch('src.api.routers.chat.require_resource_ownership', lambda x: lambda f: f):
        response = client.get(
            f"/api/v1/conversations/{sample_conversation_id}/messages?limit=10&offset=5"
        )

    assert response.status_code == 200


def test_get_messages_empty(client, sample_conversation_id, mock_postgres_manager):
    """Test getting messages for conversation with no messages."""
    mock_postgres_manager.get_conversation_messages.return_value = []

    with patch('src.api.routers.chat.PostgresManager', return_value=mock_postgres_manager), \
         patch('src.api.routers.chat.require_resource_ownership', lambda x: lambda f: f):
        response = client.get(f"/api/v1/conversations/{sample_conversation_id}/messages")

    assert response.status_code == 200
    assert response.json() == []


# ============================================================================
# POST /api/v1/conversations/{conversation_id}/messages Tests
# ============================================================================

def test_create_message_success(client, sample_conversation_id, mock_postgres_manager):
    """Test successful message creation."""
    mock_message = {
        'id': str(uuid4()),
        'conversation_id': sample_conversation_id,
        'role': 'user',
        'content': 'Hello!',
        'created_at': datetime.now()
    }
    mock_postgres_manager.create_message.return_value = mock_message

    with patch('src.api.routers.chat.PostgresManager', return_value=mock_postgres_manager), \
         patch('src.api.routers.chat.require_resource_ownership', lambda x: lambda f: f):
        response = client.post(
            f"/api/v1/conversations/{sample_conversation_id}/messages",
            json={
                "role": "user",
                "content": "Hello!"
            }
        )

    assert response.status_code == 201
    data = response.json()
    assert data['role'] == 'user'
    assert data['content'] == 'Hello!'


def test_create_message_empty_content(client, sample_conversation_id):
    """Test creating message with empty content."""
    with patch('src.api.routers.chat.require_resource_ownership', lambda x: lambda f: f):
        response = client.post(
            f"/api/v1/conversations/{sample_conversation_id}/messages",
            json={
                "role": "user",
                "content": ""
            }
        )

    assert response.status_code == 422  # Validation error


def test_create_message_invalid_role(client, sample_conversation_id):
    """Test creating message with invalid role."""
    with patch('src.api.routers.chat.require_resource_ownership', lambda x: lambda f: f):
        response = client.post(
            f"/api/v1/conversations/{sample_conversation_id}/messages",
            json={
                "role": "invalid_role",
                "content": "Hello"
            }
        )

    assert response.status_code == 422


def test_create_message_with_metadata(client, sample_conversation_id, mock_postgres_manager):
    """Test creating message with metadata."""
    mock_message = {
        'id': str(uuid4()),
        'conversation_id': sample_conversation_id,
        'role': 'assistant',
        'content': 'Response',
        'created_at': datetime.now(),
        'metadata': {'model': 'claude-sonnet-4.5'}
    }
    mock_postgres_manager.create_message.return_value = mock_message

    with patch('src.api.routers.chat.PostgresManager', return_value=mock_postgres_manager), \
         patch('src.api.routers.chat.require_resource_ownership', lambda x: lambda f: f):
        response = client.post(
            f"/api/v1/conversations/{sample_conversation_id}/messages",
            json={
                "role": "assistant",
                "content": "Response",
                "metadata": {"model": "claude-sonnet-4.5"}
            }
        )

    assert response.status_code == 201


# ============================================================================
# PUT /api/v1/conversations/{conversation_id}/messages/{message_id} Tests
# ============================================================================

def test_update_message_success(client, sample_conversation_id, sample_message_id, mock_postgres_manager):
    """Test successful message update."""
    mock_postgres_manager.update_message.return_value = {
        'id': sample_message_id,
        'content': 'Updated content',
        'updated_at': datetime.now()
    }

    with patch('src.api.routers.chat.PostgresManager', return_value=mock_postgres_manager), \
         patch('src.api.routers.chat.require_resource_ownership', lambda x: lambda f: f):
        response = client.put(
            f"/api/v1/conversations/{sample_conversation_id}/messages/{sample_message_id}",
            json={"content": "Updated content"}
        )

    assert response.status_code == 200


def test_update_message_not_found(client, sample_conversation_id, mock_postgres_manager):
    """Test updating non-existent message."""
    msg_id = str(uuid4())
    mock_postgres_manager.update_message.side_effect = ValueError("Not found")

    with patch('src.api.routers.chat.PostgresManager', return_value=mock_postgres_manager), \
         patch('src.api.routers.chat.require_resource_ownership', lambda x: lambda f: f):
        response = client.put(
            f"/api/v1/conversations/{sample_conversation_id}/messages/{msg_id}",
            json={"content": "Updated"}
        )

    assert response.status_code == 404


# ============================================================================
# DELETE /api/v1/conversations/{conversation_id}/messages/{message_id} Tests
# ============================================================================

def test_delete_message_success(client, sample_conversation_id, sample_message_id, mock_postgres_manager):
    """Test successful message deletion."""
    mock_postgres_manager.delete_message.return_value = True

    with patch('src.api.routers.chat.PostgresManager', return_value=mock_postgres_manager), \
         patch('src.api.routers.chat.require_resource_ownership', lambda x: lambda f: f):
        response = client.delete(
            f"/api/v1/conversations/{sample_conversation_id}/messages/{sample_message_id}"
        )

    assert response.status_code == 204


def test_delete_message_not_found(client, sample_conversation_id, mock_postgres_manager):
    """Test deleting non-existent message."""
    msg_id = str(uuid4())
    mock_postgres_manager.delete_message.side_effect = ValueError("Not found")

    with patch('src.api.routers.chat.PostgresManager', return_value=mock_postgres_manager), \
         patch('src.api.routers.chat.require_resource_ownership', lambda x: lambda f: f):
        response = client.delete(
            f"/api/v1/conversations/{sample_conversation_id}/messages/{msg_id}"
        )

    assert response.status_code == 404


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================

def test_conversation_with_long_message_preview(client, mock_postgres_manager):
    """Test conversation listing with very long last message."""
    long_message = "A" * 200  # 200 character message
    mock_results = [{
        'id': str(uuid4()),
        'created_at': datetime.now(),
        'updated_at': datetime.now(),
        'metadata': None,
        'message_count': 1,
        'last_message': long_message
    }]
    mock_postgres_manager._execute.return_value = mock_results

    with patch('src.api.routers.chat.PostgresManager', return_value=mock_postgres_manager):
        response = client.get("/api/v1/conversations")

    data = response.json()
    # Should truncate to 100 chars + "..."
    assert len(data[0]['last_message_preview']) == 103


@pytest.mark.unit
class TestChatModels:
    """Unit tests for chat request/response models."""

    def test_conversation_summary_model(self):
        """Test ConversationSummary model."""
        from src.api.routers.chat import ConversationSummary

        summary = ConversationSummary(
            id=str(uuid4()),
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
            message_count=5,
            last_message_preview="Hello...",
            workspace_id="ws-1"
        )

        assert summary.message_count == 5
        assert summary.workspace_id == "ws-1"

    def test_conversation_detail_model(self):
        """Test ConversationDetail model."""
        from src.api.routers.chat import ConversationDetail

        detail = ConversationDetail(
            id=str(uuid4()),
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
            workspace_id="ws-1",
            messages=[
                {
                    'id': str(uuid4()),
                    'role': 'user',
                    'content': 'Hello',
                    'created_at': datetime.now().isoformat()
                }
            ],
            metadata={}
        )

        assert len(detail.messages) == 1
        assert detail.workspace_id == "ws-1"

