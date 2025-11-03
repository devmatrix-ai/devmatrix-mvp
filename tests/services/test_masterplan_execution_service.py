"""
Tests for MasterplanExecutionService

Tests masterplan execution orchestration.

Author: DevMatrix Team
Date: 2025-11-03
"""

import pytest
from uuid import uuid4
from unittest.mock import MagicMock, patch


@pytest.mark.unit
class TestMasterplanExecutionStart:
    """Test execution initialization."""

    def test_start_execution_success(self):
        """Test successful execution start."""
        from src.services.masterplan_execution_service import MasterplanExecutionService

        service = MasterplanExecutionService()
        masterplan_id = uuid4()
        
        with patch.object(service, '_validate_masterplan', return_value=True), \
             patch.object(service, '_create_workspace', return_value="/path/to/workspace"), \
             patch.object(service, '_initialize_execution', return_value=uuid4()):
            
            result = service.start_execution(masterplan_id)
            
            assert result is not None

    def test_start_execution_not_approved(self):
        """Test execution start for unapproved masterplan."""
        from src.services.masterplan_execution_service import MasterplanExecutionService

        service = MasterplanExecutionService()
        
        with patch.object(service, '_validate_masterplan', side_effect=ValueError("Not approved")):
            with pytest.raises(ValueError, match="approved"):
                service.start_execution(uuid4())

    def test_start_execution_already_running(self):
        """Test execution start when already running."""
        from src.services.masterplan_execution_service import MasterplanExecutionService

        service = MasterplanExecutionService()
        
        with patch.object(service, '_check_status', return_value="running"):
            with pytest.raises(ValueError, match="already|running"):
                service.start_execution(uuid4())


@pytest.mark.unit
class TestMasterplanExecutionProgress:
    """Test execution progress tracking."""

    def test_get_execution_progress(self):
        """Test getting execution progress."""
        from src.services.masterplan_execution_service import MasterplanExecutionService

        service = MasterplanExecutionService()
        
        mock_progress = {
            "total_tasks": 50,
            "completed": 25,
            "failed": 2,
            "pending": 23,
            "progress_percent": 50.0
        }
        
        with patch.object(service, '_calculate_progress', return_value=mock_progress):
            progress = service.get_progress(uuid4())
            
            assert progress is not None
            assert progress.get("progress_percent", 0) == 50.0

    def test_update_task_status(self):
        """Test updating task status."""
        from src.services.masterplan_execution_service import MasterplanExecutionService

        service = MasterplanExecutionService()
        
        with patch.object(service, '_save_task_status', return_value=True):
            result = service.update_task_status(
                task_id=uuid4(),
                status="completed"
            )
            
            assert result is True or result is None


@pytest.mark.unit
class TestMasterplanExecutionControl:
    """Test execution control (pause, resume, cancel)."""

    def test_pause_execution_success(self):
        """Test successful execution pause."""
        from src.services.masterplan_execution_service import MasterplanExecutionService

        service = MasterplanExecutionService()
        
        with patch.object(service, '_get_status', return_value="running"), \
             patch.object(service, '_set_status', return_value=True):
            
            result = service.pause_execution(uuid4())
            
            assert result is True or result is None

    def test_resume_execution_success(self):
        """Test successful execution resume."""
        from src.services.masterplan_execution_service import MasterplanExecutionService

        service = MasterplanExecutionService()
        
        with patch.object(service, '_get_status', return_value="paused"), \
             patch.object(service, '_set_status', return_value=True):
            
            result = service.resume_execution(uuid4())
            
            assert result is True or result is None

    def test_cancel_execution_success(self):
        """Test successful execution cancellation."""
        from src.services.masterplan_execution_service import MasterplanExecutionService

        service = MasterplanExecutionService()
        
        with patch.object(service, '_cleanup_workspace', return_value=True), \
             patch.object(service, '_set_status', return_value=True):
            
            result = service.cancel_execution(uuid4())
            
            assert result is True or result is None


@pytest.mark.unit
class TestMasterplanExecutionWorkspace:
    """Test workspace management."""

    def test_create_workspace_for_execution(self):
        """Test workspace creation."""
        from src.services.masterplan_execution_service import MasterplanExecutionService

        service = MasterplanExecutionService()
        
        with patch.object(service, '_init_workspace', return_value="/tmp/workspace"):
            workspace_path = service._create_workspace(uuid4())
            
            assert workspace_path is not None

    def test_cleanup_workspace_on_completion(self):
        """Test workspace cleanup."""
        from src.services.masterplan_execution_service import MasterplanExecutionService

        service = MasterplanExecutionService()
        
        with patch.object(service, '_remove_workspace', return_value=True):
            result = service._cleanup_workspace("/tmp/workspace")
            
            assert result is True or result is None

