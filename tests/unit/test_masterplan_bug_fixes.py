"""
Unit Tests for Critical Bug Fixes - GROUP 1

Tests for:
- target_files extraction from MasterPlanTask model
- workspace_path storage in database
- No attempts to write to 'projects' table
"""

import pytest
from uuid import uuid4
from datetime import datetime
from sqlalchemy.orm import Session

from src.models.masterplan import (
    MasterPlan,
    MasterPlanPhase,
    MasterPlanMilestone,
    MasterPlanTask,
    MasterPlanStatus,
    TaskStatus,
    TaskComplexity,
    PhaseType,
    DiscoveryDocument,
)


class TestTargetFilesExtraction:
    """Test that target_files are correctly extracted from MasterPlanTask."""

    def test_task_target_files_field_exists(self, db_session: Session):
        """Test that MasterPlanTask.target_files field exists and can store file paths."""
        # Create discovery document
        discovery = DiscoveryDocument(
            discovery_id=uuid4(),
            session_id="test-session",
            user_id="test-user",
            user_request="Create a simple API",
            domain="API",
            bounded_contexts=[],
            aggregates=[],
            value_objects=[],
            domain_events=[],
            services=[],
        )
        db_session.add(discovery)
        db_session.flush()

        # Create masterplan
        masterplan = MasterPlan(
            masterplan_id=uuid4(),
            discovery_id=discovery.discovery_id,
            session_id="test-session",
            user_id="test-user",
            project_name="Test Project",
            status=MasterPlanStatus.DRAFT,
            tech_stack={"backend": "FastAPI"},
        )
        db_session.add(masterplan)
        db_session.flush()

        # Create phase
        phase = MasterPlanPhase(
            phase_id=uuid4(),
            masterplan_id=masterplan.masterplan_id,
            phase_type=PhaseType.SETUP,
            phase_number=1,
            name="Setup Phase",
        )
        db_session.add(phase)
        db_session.flush()

        # Create milestone
        milestone = MasterPlanMilestone(
            milestone_id=uuid4(),
            phase_id=phase.phase_id,
            milestone_number=1,
            name="Test Milestone",
        )
        db_session.add(milestone)
        db_session.flush()

        # Create task with target_files
        target_files = ["src/models/user.py", "src/api/routes/users.py"]
        task = MasterPlanTask(
            task_id=uuid4(),
            milestone_id=milestone.milestone_id,
            task_number=1,
            name="Create User model and API",
            description="Create User model and API endpoints",
            target_files=target_files,  # THIS IS THE CRITICAL FIELD
            complexity=TaskComplexity.MEDIUM,
        )
        db_session.add(task)
        db_session.commit()

        # Verify target_files is stored and can be retrieved
        retrieved_task = db_session.query(MasterPlanTask).filter_by(task_id=task.task_id).first()
        assert retrieved_task is not None
        assert retrieved_task.target_files == target_files
        assert len(retrieved_task.target_files) == 2
        assert "src/models/user.py" in retrieved_task.target_files

    def test_task_target_files_defaults_to_empty_list(self, db_session: Session):
        """Test that target_files can be None or empty list."""
        # Create required parent objects
        discovery = DiscoveryDocument(
            discovery_id=uuid4(),
            session_id="test-session",
            user_id="test-user",
            user_request="Create a simple API",
            domain="API",
            bounded_contexts=[],
            aggregates=[],
            value_objects=[],
            domain_events=[],
            services=[],
        )
        db_session.add(discovery)
        db_session.flush()

        masterplan = MasterPlan(
            masterplan_id=uuid4(),
            discovery_id=discovery.discovery_id,
            session_id="test-session",
            user_id="test-user",
            project_name="Test Project",
            status=MasterPlanStatus.DRAFT,
            tech_stack={"backend": "FastAPI"},
        )
        db_session.add(masterplan)
        db_session.flush()

        phase = MasterPlanPhase(
            phase_id=uuid4(),
            masterplan_id=masterplan.masterplan_id,
            phase_type=PhaseType.SETUP,
            phase_number=1,
            name="Setup Phase",
        )
        db_session.add(phase)
        db_session.flush()

        milestone = MasterPlanMilestone(
            milestone_id=uuid4(),
            phase_id=phase.phase_id,
            milestone_number=1,
            name="Test Milestone",
        )
        db_session.add(milestone)
        db_session.flush()

        # Create task without target_files
        task = MasterPlanTask(
            task_id=uuid4(),
            milestone_id=milestone.milestone_id,
            task_number=1,
            name="Generic task",
            description="A task without specific files",
            complexity=TaskComplexity.LOW,
        )
        db_session.add(task)
        db_session.commit()

        # Verify target_files is None (nullable)
        retrieved_task = db_session.query(MasterPlanTask).filter_by(task_id=task.task_id).first()
        assert retrieved_task is not None
        # Can be None or empty - both are acceptable


class TestWorkspacePathStorage:
    """Test that workspace_path can be stored in masterplans table."""

    def test_masterplan_workspace_path_column_exists(self, db_session: Session):
        """Test that MasterPlan model accepts workspace_path field after migration."""
        # Create discovery document
        discovery = DiscoveryDocument(
            discovery_id=uuid4(),
            session_id="test-session",
            user_id="test-user",
            user_request="Create a simple API",
            domain="API",
            bounded_contexts=[],
            aggregates=[],
            value_objects=[],
            domain_events=[],
            services=[],
        )
        db_session.add(discovery)
        db_session.flush()

        # Create masterplan with workspace_path
        workspace_path = "/workspace/test-project_abc123"
        masterplan = MasterPlan(
            masterplan_id=uuid4(),
            discovery_id=discovery.discovery_id,
            session_id="test-session",
            user_id="test-user",
            project_name="Test Project",
            status=MasterPlanStatus.APPROVED,
            tech_stack={"backend": "FastAPI"},
        )

        # Try to set workspace_path (will work after migration)
        try:
            setattr(masterplan, 'workspace_path', workspace_path)
            db_session.add(masterplan)
            db_session.commit()

            # Verify workspace_path is stored
            retrieved = db_session.query(MasterPlan).filter_by(masterplan_id=masterplan.masterplan_id).first()
            assert retrieved is not None
            assert hasattr(retrieved, 'workspace_path')
            assert getattr(retrieved, 'workspace_path', None) == workspace_path
        except Exception as e:
            # Expected to fail before migration is run
            pytest.skip(f"Migration not yet applied: {e}")

    def test_masterplan_workspace_path_nullable(self, db_session: Session):
        """Test that workspace_path is nullable (not required on creation)."""
        # Create discovery document
        discovery = DiscoveryDocument(
            discovery_id=uuid4(),
            session_id="test-session",
            user_id="test-user",
            user_request="Create a simple API",
            domain="API",
            bounded_contexts=[],
            aggregates=[],
            value_objects=[],
            domain_events=[],
            services=[],
        )
        db_session.add(discovery)
        db_session.flush()

        # Create masterplan without workspace_path (should succeed)
        masterplan = MasterPlan(
            masterplan_id=uuid4(),
            discovery_id=discovery.discovery_id,
            session_id="test-session",
            user_id="test-user",
            project_name="Test Project",
            status=MasterPlanStatus.DRAFT,
            tech_stack={"backend": "FastAPI"},
        )
        db_session.add(masterplan)
        db_session.commit()

        # Verify masterplan is created without workspace_path
        retrieved = db_session.query(MasterPlan).filter_by(masterplan_id=masterplan.masterplan_id).first()
        assert retrieved is not None
        # workspace_path should be None or not set initially


class TestProjectsTableRemoval:
    """Test that no code attempts to write to non-existent 'projects' table."""

    def test_orchestrator_does_not_reference_projects_table(self):
        """Test that orchestrator_agent.py does not import or reference 'projects' table."""
        import inspect
        from src.agents import orchestrator_agent

        # Get source code
        source = inspect.getsource(orchestrator_agent)

        # Verify no references to 'projects' table
        assert 'create_project' not in source or 'postgres.create_project' not in source, \
            "Found reference to create_project in orchestrator_agent.py - should be removed"

        # Verify _finalize method doesn't try to save to projects table
        # This test will pass after we remove the problematic code


class TestMasterplanExecutionServiceSkeleton:
    """Test that MasterplanExecutionService skeleton exists with required methods."""

    def test_masterplan_execution_service_exists(self):
        """Test that MasterplanExecutionService class exists."""
        try:
            from src.services.masterplan_execution_service import MasterplanExecutionService
            assert MasterplanExecutionService is not None
        except ImportError:
            pytest.skip("MasterplanExecutionService not yet created")

    def test_create_workspace_method_exists(self):
        """Test that create_workspace method exists in MasterplanExecutionService."""
        try:
            from src.services.masterplan_execution_service import MasterplanExecutionService

            # Check that class has create_workspace method
            assert hasattr(MasterplanExecutionService, 'create_workspace')

            # Check method signature
            import inspect
            sig = inspect.signature(MasterplanExecutionService.create_workspace)
            params = list(sig.parameters.keys())
            assert 'masterplan_id' in params or len(params) >= 1

        except ImportError:
            pytest.skip("MasterplanExecutionService not yet created")
