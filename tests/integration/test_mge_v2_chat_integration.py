"""
End-to-End Integration Tests for MGE V2 Chat Service Integration

Tests the complete MGE V2 pipeline integration into ChatService including:
- Feature flag switching between V1 and V2
- MGE V2 orchestration service integration
- Event streaming
- Error handling

Author: DevMatrix Team
Date: 2025-11-10
"""

import pytest
import os
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from uuid import uuid4

from src.services.chat_service import ChatService, Conversation, MessageRole


@pytest.fixture
def mock_sqlalchemy_session():
    """Create mock SQLAlchemy database session."""
    session = Mock()
    session.query = Mock()
    session.add = Mock()
    session.commit = Mock()
    session.rollback = Mock()
    return session


@pytest.fixture
def chat_service_with_mge_v2(mock_sqlalchemy_session):
    """Create ChatService with MGE V2 enabled."""
    # Set MGE V2 environment variable
    os.environ["MGE_V2_ENABLED"] = "true"

    service = ChatService(
        api_key="test-api-key",
        sqlalchemy_session=mock_sqlalchemy_session
    )

    yield service

    # Cleanup
    os.environ["MGE_V2_ENABLED"] = "false"


@pytest.fixture
def chat_service_with_v1(mock_sqlalchemy_session):
    """Create ChatService with V1 (legacy) enabled."""
    os.environ["MGE_V2_ENABLED"] = "false"

    service = ChatService(
        api_key="test-api-key",
        sqlalchemy_session=mock_sqlalchemy_session
    )

    return service


@pytest.fixture
def sample_conversation():
    """Create sample conversation."""
    return Conversation(
        workspace_id="test_workspace",
        user_id="test_user"
    )


@pytest.mark.asyncio
class TestMGEV2ChatIntegration:
    """Test MGE V2 integration into ChatService."""

    async def test_feature_flag_routes_to_mge_v2(
        self,
        chat_service_with_mge_v2,
        sample_conversation
    ):
        """Test that MGE_V2_ENABLED=true routes to MGE V2 pipeline."""

        with patch.object(
            chat_service_with_mge_v2,
            '_execute_mge_v2',
            new=AsyncMock()
        ) as mock_mge_v2, \
        patch.object(
            chat_service_with_mge_v2,
            '_execute_legacy_orchestration',
            new=AsyncMock()
        ) as mock_legacy:

            # Mock MGE V2 to return some events
            mock_mge_v2.return_value = iter([
                {"type": "complete", "masterplan_id": str(uuid4())}
            ])

            # Execute orchestration
            events = []
            async for event in chat_service_with_mge_v2._execute_orchestration(
                sample_conversation,
                "Create a REST API"
            ):
                events.append(event)

            # Verify MGE V2 was called, not legacy
            mock_mge_v2.assert_called_once()
            mock_legacy.assert_not_called()

    async def test_feature_flag_routes_to_v1(
        self,
        chat_service_with_v1,
        sample_conversation
    ):
        """Test that MGE_V2_ENABLED=false routes to legacy V1 pipeline."""

        with patch.object(
            chat_service_with_v1,
            '_execute_mge_v2',
            new=AsyncMock()
        ) as mock_mge_v2, \
        patch.object(
            chat_service_with_v1,
            '_execute_legacy_orchestration',
            new=AsyncMock()
        ) as mock_legacy:

            # Mock legacy to return some events
            mock_legacy.return_value = iter([
                {"type": "complete", "workspace_id": "test"}
            ])

            # Execute orchestration
            events = []
            async for event in chat_service_with_v1._execute_orchestration(
                sample_conversation,
                "Create a REST API"
            ):
                events.append(event)

            # Verify legacy was called, not MGE V2
            mock_legacy.assert_called_once()
            mock_mge_v2.assert_not_called()

    async def test_mge_v2_requires_sqlalchemy_session(self):
        """Test that MGE V2 requires SQLAlchemy session."""
        os.environ["MGE_V2_ENABLED"] = "true"

        # Create service WITHOUT sqlalchemy_session
        service = ChatService(api_key="test-api-key")

        conversation = Conversation(workspace_id="test", user_id="test")

        # Execute orchestration
        events = []
        async for event in service._execute_orchestration(
            conversation,
            "Create a REST API"
        ):
            events.append(event)

        # Verify we got an error about missing session
        assert len(events) == 1
        assert events[0]["type"] == "error"
        assert "database session" in events[0]["content"].lower()

        # Cleanup
        os.environ["MGE_V2_ENABLED"] = "false"

    async def test_mge_v2_streams_progress_events(
        self,
        chat_service_with_mge_v2,
        sample_conversation,
        mock_sqlalchemy_session
    ):
        """Test that MGE V2 streams progress events correctly."""

        with patch('src.services.chat_service.MGE_V2_OrchestrationService') as MockService:
            # Mock MGE V2 service to return progress events
            mock_service_instance = MockService.return_value

            async def mock_orchestrate():
                yield {"type": "status", "message": "Starting..."}
                yield {"type": "progress", "phase": "masterplan_generation", "message": "Generating..."}
                yield {"type": "progress", "phase": "atomization", "message": "Atomizing..."}
                yield {"type": "progress", "phase": "execution", "message": "Executing..."}
                yield {
                    "type": "complete",
                    "masterplan_id": str(uuid4()),
                    "total_tasks": 120,
                    "total_atoms": 800,
                    "precision": 0.98,
                    "execution_time": 90.5
                }

            mock_service_instance.orchestrate_from_request = AsyncMock(
                side_effect=mock_orchestrate
            )

            # Execute orchestration
            events = []
            async for event in chat_service_with_mge_v2._execute_mge_v2(
                sample_conversation,
                "Create a REST API"
            ):
                events.append(event)

            # Verify we got all expected events
            assert len(events) >= 5  # status + 3 progress + complete

            # Check event types
            event_types = [e.get("type") for e in events]
            assert "status" in event_types
            assert "progress" in event_types
            assert "message" in event_types  # Final completion message

    async def test_mge_v2_handles_errors_gracefully(
        self,
        chat_service_with_mge_v2,
        sample_conversation
    ):
        """Test that MGE V2 handles errors gracefully."""

        with patch('src.services.chat_service.MGE_V2_OrchestrationService') as MockService:
            # Mock MGE V2 service to raise an error
            mock_service_instance = MockService.return_value
            mock_service_instance.orchestrate_from_request = AsyncMock(
                side_effect=Exception("Test error")
            )

            # Execute orchestration
            events = []
            async for event in chat_service_with_mge_v2._execute_mge_v2(
                sample_conversation,
                "Create a REST API"
            ):
                events.append(event)

            # Verify we got an error event
            error_events = [e for e in events if e.get("type") == "error"]
            assert len(error_events) > 0
            assert "Test error" in error_events[0].get("content", "")

    async def test_mge_v2_error_event_from_orchestrator(
        self,
        chat_service_with_mge_v2,
        sample_conversation
    ):
        """Test handling of error events from MGE V2 orchestrator."""

        with patch('src.services.chat_service.MGE_V2_OrchestrationService') as MockService:
            # Mock MGE V2 service to return an error event
            mock_service_instance = MockService.return_value

            async def mock_orchestrate_with_error():
                yield {"type": "status", "message": "Starting..."}
                yield {
                    "type": "error",
                    "message": "MasterPlan generation failed"
                }

            mock_service_instance.orchestrate_from_request = AsyncMock(
                side_effect=mock_orchestrate_with_error
            )

            # Execute orchestration
            events = []
            async for event in chat_service_with_mge_v2._execute_mge_v2(
                sample_conversation,
                "Create a REST API"
            ):
                events.append(event)

            # Verify we got the error event
            error_events = [e for e in events if e.get("type") == "error"]
            assert len(error_events) > 0
            assert "MasterPlan generation failed" in error_events[0].get("content", "")

    async def test_mge_v2_completion_message_formatting(
        self,
        chat_service_with_mge_v2
    ):
        """Test that MGE V2 completion messages are formatted correctly."""

        completion_event = {
            "masterplan_id": str(uuid4()),
            "total_tasks": 120,
            "total_atoms": 800,
            "precision": 0.98,
            "execution_time": 90.5
        }

        result = chat_service_with_mge_v2._format_mge_v2_completion(completion_event)

        # Verify formatting
        assert "MGE V2 Generation Complete" in result
        assert str(completion_event["masterplan_id"]) in result
        assert "120" in result  # total tasks
        assert "800" in result  # total atoms
        assert "98.0%" in result  # precision
        assert "90.5s" in result  # execution time

    async def test_mge_v2_saves_conversation_message(
        self,
        chat_service_with_mge_v2,
        sample_conversation,
        mock_sqlalchemy_session
    ):
        """Test that MGE V2 saves completion message to conversation."""

        with patch('src.services.chat_service.MGE_V2_OrchestrationService') as MockService:
            # Mock MGE V2 service
            mock_service_instance = MockService.return_value

            async def mock_orchestrate():
                yield {
                    "type": "complete",
                    "masterplan_id": str(uuid4()),
                    "total_tasks": 120,
                    "total_atoms": 800,
                    "precision": 0.98,
                    "execution_time": 90.5
                }

            mock_service_instance.orchestrate_from_request = AsyncMock(
                side_effect=mock_orchestrate
            )

            # Mock database save
            with patch.object(
                chat_service_with_mge_v2,
                '_save_message_to_db'
            ) as mock_save:

                # Execute orchestration
                events = []
                async for event in chat_service_with_mge_v2._execute_mge_v2(
                    sample_conversation,
                    "Create a REST API"
                ):
                    events.append(event)

                # Verify message was saved
                mock_save.assert_called_once()
                call_kwargs = mock_save.call_args[1]
                assert call_kwargs["role"] == MessageRole.ASSISTANT.value
                assert "mge_v2_result" in call_kwargs["metadata"]

    async def test_mge_v2_initialization_parameters(
        self,
        chat_service_with_mge_v2,
        sample_conversation
    ):
        """Test that MGE V2 service is initialized with correct parameters."""

        with patch('src.services.chat_service.MGE_V2_OrchestrationService') as MockService:
            # Mock MGE V2 service
            mock_service_instance = MockService.return_value
            mock_service_instance.orchestrate_from_request = AsyncMock(
                return_value=iter([
                    {"type": "error", "message": "test"}
                ])
            )

            # Execute orchestration
            events = []
            async for event in chat_service_with_mge_v2._execute_mge_v2(
                sample_conversation,
                "Create a REST API"
            ):
                events.append(event)

            # Verify service was initialized with correct parameters
            MockService.assert_called_once()
            call_kwargs = MockService.call_args[1]

            assert "db" in call_kwargs
            assert call_kwargs["db"] is not None
            assert "api_key" in call_kwargs
            assert call_kwargs["api_key"] == "test-api-key"
            assert "enable_caching" in call_kwargs
            assert "enable_rag" in call_kwargs


@pytest.mark.asyncio
class TestMGEV2ConfigurationFlags:
    """Test MGE V2 configuration flag behavior."""

    async def test_configuration_flags_passed_to_service(self):
        """Test that configuration flags are passed to MGE V2 service."""
        os.environ["MGE_V2_ENABLED"] = "true"
        os.environ["MGE_V2_ENABLE_CACHING"] = "false"
        os.environ["MGE_V2_ENABLE_RAG"] = "false"

        mock_session = Mock()
        service = ChatService(
            api_key="test-api-key",
            sqlalchemy_session=mock_session
        )

        conversation = Conversation(workspace_id="test", user_id="test")

        with patch('src.services.chat_service.MGE_V2_OrchestrationService') as MockService:
            mock_service_instance = MockService.return_value
            mock_service_instance.orchestrate_from_request = AsyncMock(
                return_value=iter([{"type": "error", "message": "test"}])
            )

            # Execute
            events = []
            async for event in service._execute_mge_v2(conversation, "test"):
                events.append(event)

            # Verify flags were passed
            call_kwargs = MockService.call_args[1]
            assert call_kwargs["enable_caching"] is False
            assert call_kwargs["enable_rag"] is False

        # Cleanup
        os.environ["MGE_V2_ENABLED"] = "false"
        os.environ["MGE_V2_ENABLE_CACHING"] = "true"
        os.environ["MGE_V2_ENABLE_RAG"] = "true"
