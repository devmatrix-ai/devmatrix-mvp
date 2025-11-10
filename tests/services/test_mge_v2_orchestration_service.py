"""
Tests for MGE V2 Orchestration Service

Tests the complete end-to-end MGE V2 pipeline integration.

Author: DevMatrix Team
Date: 2025-11-10
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from uuid import uuid4

from src.services.mge_v2_orchestration_service import MGE_V2_OrchestrationService


@pytest.fixture
def mock_db_session():
    """Create mock database session."""
    db = Mock()
    db.query = Mock()
    db.add = Mock()
    db.commit = Mock()
    db.rollback = Mock()
    return db


@pytest.fixture
def mock_llm_client():
    """Create mock LLM client."""
    client = Mock()
    client.generate = AsyncMock()
    return client


@pytest.fixture
def mock_masterplan_generator():
    """Create mock masterplan generator."""
    generator = Mock()
    generator.generate_masterplan = AsyncMock(return_value=uuid4())
    return generator


@pytest.fixture
def mock_atom_service():
    """Create mock atom service."""
    service = Mock()
    service.decompose_task = Mock(return_value={
        "atoms": [
            {"atom_id": str(uuid4()), "name": "atom_1", "loc": 10},
            {"atom_id": str(uuid4()), "name": "atom_2", "loc": 10},
        ]
    })
    return service


@pytest.fixture
def mock_execution_service():
    """Create mock execution service."""
    service = Mock()
    service.start_execution = AsyncMock(return_value={
        "total_waves": 3,
        "precision": 0.98,
        "execution_time": 90.5
    })
    return service


class TestMGEV2OrchestrationServiceInit:
    """Test initialization of MGE V2 Orchestration Service."""

    def test_initialization_with_defaults(self, mock_db_session):
        """Test service initializes with default parameters."""
        with patch('src.services.mge_v2_orchestration_service.EnhancedAnthropicClient'), \
             patch('src.services.mge_v2_orchestration_service.MasterPlanGenerator'), \
             patch('src.services.mge_v2_orchestration_service.AtomService'), \
             patch('src.services.mge_v2_orchestration_service.ExecutionServiceV2'):

            service = MGE_V2_OrchestrationService(db=mock_db_session)

            assert service.db == mock_db_session
            assert service.llm_client is not None
            assert service.masterplan_generator is not None
            assert service.atom_service is not None
            assert service.execution_service is not None

    def test_initialization_with_custom_api_key(self, mock_db_session):
        """Test service initializes with custom API key."""
        custom_key = "sk-ant-custom-key"

        with patch('src.services.mge_v2_orchestration_service.EnhancedAnthropicClient') as MockClient, \
             patch('src.services.mge_v2_orchestration_service.MasterPlanGenerator'), \
             patch('src.services.mge_v2_orchestration_service.AtomService'), \
             patch('src.services.mge_v2_orchestration_service.ExecutionServiceV2'):

            service = MGE_V2_OrchestrationService(
                db=mock_db_session,
                api_key=custom_key
            )

            # Verify LLM client was created with custom key
            MockClient.assert_called_once()
            call_kwargs = MockClient.call_args[1]
            assert call_kwargs['api_key'] == custom_key
            assert call_kwargs['cost_optimization'] is True
            assert call_kwargs['enable_v2_caching'] is True

    def test_initialization_with_caching_disabled(self, mock_db_session):
        """Test service initializes with caching disabled."""
        with patch('src.services.mge_v2_orchestration_service.EnhancedAnthropicClient') as MockClient, \
             patch('src.services.mge_v2_orchestration_service.MasterPlanGenerator'), \
             patch('src.services.mge_v2_orchestration_service.AtomService'), \
             patch('src.services.mge_v2_orchestration_service.ExecutionServiceV2'):

            service = MGE_V2_OrchestrationService(
                db=mock_db_session,
                enable_caching=False
            )

            # Verify caching was disabled
            call_kwargs = MockClient.call_args[1]
            assert call_kwargs['enable_v2_caching'] is False


@pytest.mark.asyncio
class TestMGEV2OrchestrationServiceFromDiscovery:
    """Test orchestration from Discovery Document."""

    async def test_orchestrate_from_discovery_success(self, mock_db_session):
        """Test successful orchestration from discovery document."""
        discovery_id = uuid4()
        session_id = "test_session"
        user_id = "test_user"

        with patch('src.services.mge_v2_orchestration_service.EnhancedAnthropicClient'), \
             patch('src.services.mge_v2_orchestration_service.MasterPlanGenerator') as MockMPG, \
             patch('src.services.mge_v2_orchestration_service.AtomService') as MockAtomService, \
             patch('src.services.mge_v2_orchestration_service.ExecutionServiceV2') as MockExecService:

            # Setup mocks
            mock_masterplan_id = uuid4()
            mock_mp_gen = MockMPG.return_value
            mock_mp_gen.generate_masterplan = AsyncMock(return_value=mock_masterplan_id)

            # Mock database query for masterplan
            mock_masterplan = Mock()
            mock_masterplan.masterplan_id = mock_masterplan_id
            mock_db_session.query.return_value.filter.return_value.first.return_value = mock_masterplan

            # Mock database query for tasks
            mock_tasks = [
                Mock(task_id=uuid4(), task_number=1, title="Task 1"),
                Mock(task_id=uuid4(), task_number=2, title="Task 2"),
            ]
            mock_db_session.query.return_value.filter.return_value.all.return_value = mock_tasks

            # Mock atom service
            mock_atom_svc = MockAtomService.return_value
            mock_atom_svc.decompose_task.return_value = {
                "atoms": [
                    {"atom_id": str(uuid4()), "name": "atom_1"},
                    {"atom_id": str(uuid4()), "name": "atom_2"},
                ]
            }

            # Mock execution service
            mock_exec_svc = MockExecService.return_value
            mock_exec_svc.start_execution = AsyncMock(return_value={
                "total_waves": 2,
                "precision": 0.98,
                "execution_time": 45.0
            })

            # Create service
            service = MGE_V2_OrchestrationService(db=mock_db_session)

            # Execute orchestration
            events = []
            async for event in service.orchestrate_from_discovery(
                discovery_id=discovery_id,
                session_id=session_id,
                user_id=user_id
            ):
                events.append(event)

            # Verify event sequence
            assert len(events) > 0

            # Check for key phases
            phases = [e.get("phase") for e in events if "phase" in e]
            assert "masterplan_generation" in phases
            assert "atomization" in phases
            assert "execution" in phases

            # Check for completion event
            completion_events = [e for e in events if e.get("type") == "complete"]
            assert len(completion_events) == 1

            completion = completion_events[0]
            assert str(completion.get("masterplan_id")) == str(mock_masterplan_id)
            assert completion.get("total_tasks") == 2
            assert completion.get("total_atoms") == 4  # 2 tasks * 2 atoms

    async def test_orchestrate_from_discovery_masterplan_not_found(self, mock_db_session):
        """Test orchestration fails when masterplan not found after generation."""
        discovery_id = uuid4()

        with patch('src.services.mge_v2_orchestration_service.EnhancedAnthropicClient'), \
             patch('src.services.mge_v2_orchestration_service.MasterPlanGenerator') as MockMPG, \
             patch('src.services.mge_v2_orchestration_service.AtomService'), \
             patch('src.services.mge_v2_orchestration_service.ExecutionServiceV2'):

            # Setup mocks
            mock_mp_gen = MockMPG.return_value
            mock_mp_gen.generate_masterplan = AsyncMock(return_value=uuid4())

            # Mock database query to return None (masterplan not found)
            mock_db_session.query.return_value.filter.return_value.first.return_value = None

            # Create service
            service = MGE_V2_OrchestrationService(db=mock_db_session)

            # Execute orchestration
            events = []
            async for event in service.orchestrate_from_discovery(
                discovery_id=discovery_id,
                session_id="test_session",
                user_id="test_user"
            ):
                events.append(event)

            # Verify error event
            error_events = [e for e in events if e.get("type") == "error"]
            assert len(error_events) > 0
            assert "not found after generation" in error_events[0].get("message", "")

    async def test_orchestrate_from_discovery_handles_exceptions(self, mock_db_session):
        """Test orchestration handles exceptions gracefully."""
        discovery_id = uuid4()

        with patch('src.services.mge_v2_orchestration_service.EnhancedAnthropicClient'), \
             patch('src.services.mge_v2_orchestration_service.MasterPlanGenerator') as MockMPG, \
             patch('src.services.mge_v2_orchestration_service.AtomService'), \
             patch('src.services.mge_v2_orchestration_service.ExecutionServiceV2'):

            # Setup mock to raise exception
            mock_mp_gen = MockMPG.return_value
            mock_mp_gen.generate_masterplan = AsyncMock(side_effect=Exception("Test error"))

            # Create service
            service = MGE_V2_OrchestrationService(db=mock_db_session)

            # Execute orchestration
            events = []
            async for event in service.orchestrate_from_discovery(
                discovery_id=discovery_id,
                session_id="test_session",
                user_id="test_user"
            ):
                events.append(event)

            # Verify error event
            error_events = [e for e in events if e.get("type") == "error"]
            assert len(error_events) > 0
            assert "Test error" in error_events[0].get("message", "")


@pytest.mark.asyncio
class TestMGEV2OrchestrationServiceFromRequest:
    """Test orchestration from user request."""

    async def test_orchestrate_from_request_not_implemented(self, mock_db_session):
        """Test that orchestrate_from_request returns not implemented error."""
        with patch('src.services.mge_v2_orchestration_service.EnhancedAnthropicClient'), \
             patch('src.services.mge_v2_orchestration_service.MasterPlanGenerator'), \
             patch('src.services.mge_v2_orchestration_service.AtomService'), \
             patch('src.services.mge_v2_orchestration_service.ExecutionServiceV2'):

            service = MGE_V2_OrchestrationService(db=mock_db_session)

            events = []
            async for event in service.orchestrate_from_request(
                user_request="Create a REST API",
                workspace_id="test_workspace"
            ):
                events.append(event)

            # Verify we get discovery phase start and error
            assert len(events) == 2
            assert events[0].get("phase") == "discovery"
            assert events[1].get("type") == "error"
            assert "not yet implemented" in events[1].get("message", "").lower()
