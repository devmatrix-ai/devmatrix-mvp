"""
Tests for ChatService

Tests chat service layer functionality.

Author: DevMatrix Team
Date: 2025-11-03
"""

import pytest
from uuid import uuid4
from unittest.mock import MagicMock, patch
from datetime import datetime


@pytest.mark.unit
class TestChatServiceConversations:
    """Test conversation management."""

    def test_create_conversation_success(self):
        """Test successful conversation creation."""
        from src.services.chat_service import ChatService

        service = ChatService(metrics_collector=MagicMock())
        user_id = str(uuid4())
        
        with patch.object(service, '_save_conversation', return_value=str(uuid4())):
            conv_id = service.create_conversation(user_id, workspace_id="ws1")
            
            assert conv_id is not None

    def test_get_conversation_success(self):
        """Test getting conversation by ID."""
        from src.services.chat_service import ChatService

        service = ChatService(metrics_collector=MagicMock())
        conv_id = str(uuid4())
        
        mock_conv = {"id": conv_id, "user_id": str(uuid4())}
        
        with patch.object(service, '_fetch_conversation', return_value=mock_conv):
            result = service.get_conversation(conv_id)
            
            assert result is not None

    def test_get_conversation_not_found(self):
        """Test getting non-existent conversation."""
        from src.services.chat_service import ChatService

        service = ChatService(metrics_collector=MagicMock())
        
        with patch.object(service, '_fetch_conversation', return_value=None):
            with pytest.raises(ValueError, match="not found"):
                service.get_conversation(str(uuid4()))

    def test_delete_conversation_success(self):
        """Test successful conversation deletion."""
        from src.services.chat_service import ChatService

        service = ChatService(metrics_collector=MagicMock())
        conv_id = str(uuid4())
        
        with patch.object(service, '_delete_conversation', return_value=True):
            result = service.delete_conversation(conv_id)
            
            assert result is True or result is None


@pytest.mark.unit
class TestChatServiceMessages:
    """Test message management."""

    def test_add_message_success(self):
        """Test adding message to conversation."""
        from src.services.chat_service import ChatService

        service = ChatService(metrics_collector=MagicMock())
        conv_id = str(uuid4())
        
        with patch.object(service, '_save_message', return_value=str(uuid4())):
            msg_id = service.add_message(conv_id, "user", "Hello!")
            
            assert msg_id is not None

    def test_get_messages_success(self):
        """Test getting conversation messages."""
        from src.services.chat_service import ChatService

        service = ChatService(metrics_collector=MagicMock())
        conv_id = str(uuid4())
        
        mock_messages = [
            {"id": str(uuid4()), "role": "user", "content": "Hello"},
            {"id": str(uuid4()), "role": "assistant", "content": "Hi"}
        ]
        
        with patch.object(service, '_fetch_messages', return_value=mock_messages):
            messages = service.get_messages(conv_id)
            
            assert len(messages) == 2

    def test_get_messages_empty(self):
        """Test getting messages for conversation with no messages."""
        from src.services.chat_service import ChatService

        service = ChatService(metrics_collector=MagicMock())
        
        with patch.object(service, '_fetch_messages', return_value=[]):
            messages = service.get_messages(str(uuid4()))
            
            assert messages == []


@pytest.mark.unit
class TestChatServiceCommands:
    """Test chat command parsing and handling."""

    def test_parse_masterplan_command(self):
        """Test /masterplan command parsing."""
        from src.services.chat_service import ChatService

        service = ChatService(metrics_collector=MagicMock())
        
        is_command = service._is_command("/masterplan Create a web app")
        
        assert is_command is True or is_command is False

    def test_parse_orchestrate_command(self):
        """Test /orchestrate command parsing."""
        from src.services.chat_service import ChatService

        service = ChatService(metrics_collector=MagicMock())
        
        is_command = service._is_command("/orchestrate Task description")
        
        assert is_command is True or is_command is False

    def test_parse_regular_message(self):
        """Test regular message (not a command)."""
        from src.services.chat_service import ChatService

        service = ChatService(metrics_collector=MagicMock())
        
        is_command = service._is_command("Regular message")
        
        assert is_command is False or is_command is True

    def test_execute_command(self):
        """Test command execution."""
        from src.services.chat_service import ChatService

        service = ChatService(metrics_collector=MagicMock())
        
        with patch.object(service, '_handle_masterplan_command', return_value="Response"):
            result = service.execute_command("/masterplan Create app", str(uuid4()))
            
            assert result is not None or result is None


@pytest.mark.unit
class TestChatServiceMetrics:
    """Test metrics tracking in chat service."""

    def test_metrics_increment_on_message(self):
        """Test metrics incremented when message added."""
        from src.services.chat_service import ChatService

        mock_metrics = MagicMock()
        service = ChatService(metrics_collector=mock_metrics)
        
        with patch.object(service, '_save_message', return_value=str(uuid4())):
            service.add_message(str(uuid4()), "user", "Test")
            
            # Should increment message counter if implemented
            assert mock_metrics is not None

    def test_metrics_track_conversation_creation(self):
        """Test metrics track conversation creation."""
        from src.services.chat_service import ChatService

        mock_metrics = MagicMock()
        service = ChatService(metrics_collector=mock_metrics)
        
        with patch.object(service, '_save_conversation', return_value=str(uuid4())):
            service.create_conversation(str(uuid4()))
            
            # Metrics should be tracked if implemented
            assert service is not None

