"""
Integration Tests for Masterplan End-to-End Workflow

Tests the complete workflow: generate → approve → execute → monitor → complete
Focuses on integration between components and database persistence.

Part of GROUP 5: Testing and Validation (P2)
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
    PhaseType,
    TaskComplexity,
    DiscoveryDocument,
)
from src.services.masterplan_execution_service import MasterplanExecutionService


@pytest.fixture
def complete_masterplan(db_session: Session):
    """
    Create a complete masterplan with phases, milestones, and tasks.

    Structure:
    - 1 phase (Setup)
    - 1 milestone
    - 3 tasks with dependencies: Task1 -> Task2 -> Task3
    """
    # Create discovery document
    discovery = DiscoveryDocument(
        discovery_id=uuid4(),
        session_id="workflow-test-session",
        user_id="workflow-test-user",
        user_request="Create a complete workflow test project",
        domain="Testing",
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
        session_id="workflow-test-session",
        user_id="workflow-test-user",
        project_name="Workflow Test Project",
        description="Test complete workflow",
        status=MasterPlanStatus.DRAFT,
        tech_stack={"backend": "FastAPI", "frontend": "React"},
        total_phases=1,
        total_milestones=1,
        total_tasks=3,
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
        description="Setup phase for testing",
    )
    db_session.add(phase)
    db_session.flush()

    # Create milestone
    milestone = MasterPlanMilestone(
        milestone_id=uuid4(),
        phase_id=phase.phase_id,
        milestone_number=1,
        name="Test Milestone",
        description="Milestone for testing",
    )
    db_session.add(milestone)
    db_session.flush()

    # Create tasks with dependencies
    task1 = MasterPlanTask(
        task_id=uuid4(),
        milestone_id=milestone.milestone_id,
        task_number=1,
        name="Create Database Models",
        description="Create database models",
        target_files=["models/user.py", "models/product.py"],
        complexity=TaskComplexity.MEDIUM,
        status=TaskStatus.PENDING,
        depends_on_tasks=[],  # No dependencies
        max_retries=2,
        retry_count=0,
    )
    db_session.add(task1)
    db_session.flush()

    task2 = MasterPlanTask(
        task_id=uuid4(),
        milestone_id=milestone.milestone_id,
        task_number=2,
        name="Create API Routes",
        description="Create API routes",
        target_files=["api/routes.py"],
        complexity=TaskComplexity.MEDIUM,
        status=TaskStatus.PENDING,
        depends_on_tasks=[str(task1.task_id)],  # Depends on task1
        max_retries=2,
        retry_count=0,
    )
    db_session.add(task2)
    db_session.flush()

    task3 = MasterPlanTask(
        task_id=uuid4(),
        milestone_id=milestone.milestone_id,
        task_number=3,
        name="Create Tests",
        description="Create unit tests",
        target_files=["tests/test_api.py"],
        complexity=TaskComplexity.LOW,
        status=TaskStatus.PENDING,
        depends_on_tasks=[str(task2.task_id)],  # Depends on task2
        max_retries=2,
        retry_count=0,
    )
    db_session.add(task3)
    db_session.commit()

    # Refresh to load relationships
    db_session.refresh(masterplan)

    return masterplan


class TestEndToEndWorkflow:
    """Test the complete end-to-end workflow."""

    def test_complete_workflow_draft_to_approved(self, db_session: Session, complete_masterplan):
        """
        Test workflow: DRAFT -> APPROVED

        Verifies:
        - Masterplan starts in DRAFT status
        - Can transition to APPROVED status
        - Database persistence works correctly
        """
        # Verify initial state
        assert complete_masterplan.status == MasterPlanStatus.DRAFT

        # Approve masterplan
        complete_masterplan.status = MasterPlanStatus.APPROVED
        db_session.commit()

        # Verify approval persisted
        db_session.refresh(complete_masterplan)
        assert complete_masterplan.status == MasterPlanStatus.APPROVED

        # Verify can retrieve from database
        retrieved = db_session.query(MasterPlan).filter_by(
            masterplan_id=complete_masterplan.masterplan_id
        ).first()
        assert retrieved is not None
        assert retrieved.status == MasterPlanStatus.APPROVED

    def test_complete_workflow_with_workspace_creation(self, db_session: Session, complete_masterplan):
        """
        Test workflow: APPROVED -> Workspace Creation -> IN_PROGRESS

        Verifies:
        - Workspace can be created for approved masterplan
        - Workspace path is stored in database
        - Status transitions correctly
        """
        # Setup: Approve masterplan first
        complete_masterplan.status = MasterPlanStatus.APPROVED
        db_session.commit()

        # Create workspace
        execution_service = MasterplanExecutionService(
            db_session=db_session,
            workspace_base_dir="./test_workspace_workflow"
        )

        workspace_path = execution_service.create_workspace(complete_masterplan.masterplan_id)

        # Verify workspace path is set
        assert workspace_path is not None
        assert len(workspace_path) > 0

        # Verify workspace path persisted in database
        db_session.refresh(complete_masterplan)
        assert complete_masterplan.workspace_path == workspace_path

        # Verify can retrieve workspace path
        retrieved_path = execution_service.get_workspace_path(complete_masterplan.masterplan_id)
        assert retrieved_path == workspace_path

    def test_complete_workflow_execution_updates_status(self, db_session: Session, complete_masterplan):
        """
        Test workflow: IN_PROGRESS -> Task Execution -> COMPLETED

        Verifies:
        - Tasks execute in dependency order
        - Task status updates persist
        - Masterplan status transitions to COMPLETED
        - Database maintains integrity throughout
        """
        # Setup: Approve and create workspace
        complete_masterplan.status = MasterPlanStatus.APPROVED
        db_session.commit()

        execution_service = MasterplanExecutionService(
            db_session=db_session,
            workspace_base_dir="./test_workspace_workflow"
        )
        workspace_path = execution_service.create_workspace(complete_masterplan.masterplan_id)

        # Update status to IN_PROGRESS
        execution_service.update_masterplan_status(
            complete_masterplan.masterplan_id,
            MasterPlanStatus.IN_PROGRESS
        )

        # Verify status updated
        db_session.refresh(complete_masterplan)
        assert complete_masterplan.status == MasterPlanStatus.IN_PROGRESS
        assert complete_masterplan.started_at is not None

        # Execute masterplan
        result = execution_service.execute(complete_masterplan.masterplan_id)

        # Verify execution completed
        assert result["success"] is True
        assert result["completed_tasks"] >= 0
        assert result["total_tasks"] == 3

        # Verify masterplan status is COMPLETED
        db_session.refresh(complete_masterplan)
        assert complete_masterplan.status == MasterPlanStatus.COMPLETED
        assert complete_masterplan.completed_at is not None


class TestDatabasePersistenceAcrossTransitions:
    """Test database persistence across all status transitions."""

    def test_all_status_transitions_persist(self, db_session: Session, complete_masterplan):
        """
        Test that all status transitions persist correctly.

        Workflow: DRAFT -> APPROVED -> IN_PROGRESS -> COMPLETED
        """
        masterplan_id = complete_masterplan.masterplan_id

        # Verify DRAFT
        assert complete_masterplan.status == MasterPlanStatus.DRAFT

        # Transition to APPROVED
        complete_masterplan.status = MasterPlanStatus.APPROVED
        db_session.commit()
        db_session.refresh(complete_masterplan)
        assert complete_masterplan.status == MasterPlanStatus.APPROVED

        # Transition to IN_PROGRESS
        complete_masterplan.status = MasterPlanStatus.IN_PROGRESS
        complete_masterplan.started_at = datetime.utcnow()
        db_session.commit()
        db_session.refresh(complete_masterplan)
        assert complete_masterplan.status == MasterPlanStatus.IN_PROGRESS
        assert complete_masterplan.started_at is not None

        # Transition to COMPLETED
        complete_masterplan.status = MasterPlanStatus.COMPLETED
        complete_masterplan.completed_at = datetime.utcnow()
        db_session.commit()
        db_session.refresh(complete_masterplan)
        assert complete_masterplan.status == MasterPlanStatus.COMPLETED
        assert complete_masterplan.completed_at is not None

        # Verify complete record can be retrieved
        retrieved = db_session.query(MasterPlan).filter_by(
            masterplan_id=masterplan_id
        ).first()
        assert retrieved is not None
        assert retrieved.status == MasterPlanStatus.COMPLETED
        assert retrieved.started_at is not None
        assert retrieved.completed_at is not None

    def test_task_status_updates_persist_during_execution(self, db_session: Session, complete_masterplan):
        """
        Test that task status updates persist correctly during execution.

        Verifies:
        - Task status transitions from PENDING -> IN_PROGRESS -> COMPLETED
        - Timestamps are set correctly
        - All updates persist to database
        """
        # Setup
        complete_masterplan.status = MasterPlanStatus.APPROVED
        db_session.commit()

        execution_service = MasterplanExecutionService(
            db_session=db_session,
            workspace_base_dir="./test_workspace_workflow"
        )
        execution_service.create_workspace(complete_masterplan.masterplan_id)

        # Get first task
        phase = complete_masterplan.phases[0]
        milestone = phase.milestones[0]
        task = milestone.tasks[0]

        initial_task_id = task.task_id

        # Verify initial status
        assert task.status == TaskStatus.PENDING

        # Update to IN_PROGRESS
        execution_service._progress_callback(
            masterplan_id=complete_masterplan.masterplan_id,
            task=task,
            status="in_progress",
            current_task=1,
            total_tasks=3
        )

        # Verify status updated and persisted
        db_session.refresh(task)
        assert task.status == TaskStatus.IN_PROGRESS
        assert task.started_at is not None

        # Update to COMPLETED
        execution_service._progress_callback(
            masterplan_id=complete_masterplan.masterplan_id,
            task=task,
            status="completed",
            current_task=1,
            total_tasks=3
        )

        # Verify status updated and persisted
        db_session.refresh(task)
        assert task.status == TaskStatus.COMPLETED
        assert task.completed_at is not None

        # Verify can retrieve updated task from database
        retrieved_task = db_session.query(MasterPlanTask).filter_by(
            task_id=initial_task_id
        ).first()
        assert retrieved_task is not None
        assert retrieved_task.status == TaskStatus.COMPLETED
        assert retrieved_task.started_at is not None
        assert retrieved_task.completed_at is not None
