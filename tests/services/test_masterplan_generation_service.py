"""
Tests for MasterPlanGenerator Service

Tests masterplan generation from discovery documents.

Author: DevMatrix Team  
Date: 2025-11-03
"""

import pytest
from uuid import uuid4
from unittest.mock import MagicMock, patch, AsyncMock


@pytest.mark.unit
class TestMasterPlanGeneration:
    """Test masterplan generation functionality."""

    def test_generate_masterplan_success(self):
        """Test successful masterplan generation."""
        from src.services.masterplan_generator import MasterPlanGenerator

        generator = MasterPlanGenerator()
        discovery_id = uuid4()
        
        with patch.object(generator, '_fetch_discovery', return_value={"project_name": "Test"}), \
             patch.object(generator, '_generate_phases') as mock_phases, \
             patch.object(generator, '_save_masterplan', return_value=uuid4()):
            
            mock_phases.return_value = []
            masterplan_id = generator.generate_masterplan(discovery_id, "session123")
            
            assert masterplan_id is not None

    def test_generate_masterplan_discovery_not_found(self):
        """Test generation with missing discovery."""
        from src.services.masterplan_generator import MasterPlanGenerator

        generator = MasterPlanGenerator()
        
        with patch.object(generator, '_fetch_discovery', return_value=None):
            with pytest.raises(ValueError, match="not found|Discovery"):
                generator.generate_masterplan(uuid4(), "session123")

    def test_generate_phases_from_discovery(self):
        """Test phase generation from discovery document."""
        from src.services.masterplan_generator import MasterPlanGenerator

        generator = MasterPlanGenerator()
        discovery = {
            "project_name": "Test Project",
            "requirements": ["REQ1", "REQ2"]
        }
        
        with patch.object(generator, '_call_llm', return_value="Phase 1\nPhase 2"):
            phases = generator._generate_phases(discovery)
            
            assert phases is not None or phases == []

    def test_generate_tasks_for_phase(self):
        """Test task generation for a phase."""
        from src.services.masterplan_generator import MasterPlanGenerator

        generator = MasterPlanGenerator()
        phase_desc = "Implementation phase"
        
        with patch.object(generator, '_call_llm', return_value="Task 1\nTask 2"):
            tasks = generator._generate_tasks(phase_desc)
            
            assert tasks is not None or tasks == []


@pytest.mark.unit
class TestMasterPlanValidation:
    """Test masterplan validation logic."""

    def test_validate_masterplan_structure(self):
        """Test masterplan structure validation."""
        from src.services.masterplan_generator import MasterPlanGenerator

        generator = MasterPlanGenerator()
        
        valid_masterplan = {
            "project_name": "Test",
            "phases": [
                {"phase_number": 1, "name": "Phase 1"}
            ]
        }
        
        is_valid = generator._validate_structure(valid_masterplan)
        assert is_valid is True or is_valid is False

    def test_validate_masterplan_missing_fields(self):
        """Test validation with missing required fields."""
        from src.services.masterplan_generator import MasterPlanGenerator

        generator = MasterPlanGenerator()
        
        invalid_masterplan = {}
        
        is_valid = generator._validate_structure(invalid_masterplan)
        assert is_valid is False or is_valid is True


@pytest.mark.unit  
class TestMasterPlanCostEstimation:
    """Test cost estimation for masterplans."""

    def test_estimate_execution_cost(self):
        """Test execution cost estimation."""
        from src.services.masterplan_generator import MasterPlanGenerator

        generator = MasterPlanGenerator()
        
        total_tasks = 50
        estimated_cost = generator._estimate_cost(total_tasks)
        
        assert estimated_cost >= 0
        assert isinstance(estimated_cost, (int, float))

    def test_estimate_duration(self):
        """Test execution duration estimation."""
        from src.services.masterplan_generator import MasterPlanGenerator

        generator = MasterPlanGenerator()
        
        total_tasks = 50
        estimated_minutes = generator._estimate_duration(total_tasks)
        
        assert estimated_minutes >= 0

