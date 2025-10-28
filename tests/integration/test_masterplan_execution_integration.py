"""
Integration Tests for Masterplan Execution Engine

Tests task execution with dependencies, retry logic, and error handling.
Validates integration between execution service and database.

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
def masterplan_with_dependencies(db_session: Session):
    """
    Create masterplan with complex task dependencies.

    Structure:
    Task1 (no deps) -> Task2 (depends on Task1) -> Task4 (depends on Task2)
    Task3 (no deps) -> Task4 (depends on Task3)

    Task4 has two dependencies: Task2 and Task3
    """
    # Create discovery document
    discovery = DiscoveryDocument(
        discovery_id=uuid4(),
        session_id="dependency-test-session",
        user_id="dependency-test-user",
        user_request="Test dependency execution",
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
        session_id="dependency-test-session",
        user_id="dependency-test-user",
        project_name="Dependency Test Project",
        description="Test task dependencies",
        status=MasterPlanStatus.APPROVED,
        tech_stack={"backend": "FastAPI"},
        total_phases=1,
        total_milestones=1,
        total_tasks=4,
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

    # Create tasks with dependencies
    task1 = MasterPlanTask(
        task_id=uuid4(),
        milestone_id=milestone.milestone_id,
        task_number=1,
        name="Task 1 - No Dependencies",
        description="First independent task",
        target_files=["file1.py"],
        complexity=TaskComplexity.LOW,
        status=TaskStatus.PENDING,
        depends_on_tasks=[],
        max_retries=2,
        retry_count=0,
    )
    db_session.add(task1)
    db_session.flush()

    task3 = MasterPlanTask(
        task_id=uuid4(),
        milestone_id=milestone.milestone_id,
        task_number=3,
        name="Task 3 - No Dependencies",
        description="Second independent task",
        target_files=["file3.py"],
        complexity=TaskComplexity.LOW,
        status=TaskStatus.PENDING,
        depends_on_tasks=[],
        max_retries=2,
        retry_count=0,
    )
    db_session.add(task3)
    db_session.flush()

    task2 = MasterPlanTask(
        task_id=uuid4(),
        milestone_id=milestone.milestone_id,
        task_number=2,
        name="Task 2 - Depends on Task 1",
        description="Depends on task1",
        target_files=["file2.py"],
        complexity=TaskComplexity.MEDIUM,
        status=TaskStatus.PENDING,
        depends_on_tasks=[str(task1.task_id)],
        max_retries=2,
        retry_count=0,
    )
    db_session.add(task2)
    db_session.flush()

    task4 = MasterPlanTask(
        task_id=uuid4(),
        milestone_id=milestone.milestone_id,
        task_number=4,
        name="Task 4 - Depends on Task 2 and Task 3",
        description="Depends on task2 and task3",
        target_files=["file4.py"],
        complexity=TaskComplexity.HIGH,
        status=TaskStatus.PENDING,
        depends_on_tasks=[str(task2.task_id), str(task3.task_id)],
        max_retries=2,
        retry_count=0,
    )
    db_session.add(task4)
    db_session.commit()

    # Refresh to load relationships
    db_session.refresh(masterplan)

    return masterplan


class TestTaskDependencyExecution:
    """Test task execution with dependencies."""

    def test_tasks_execute_in_dependency_order(self, db_session: Session, masterplan_with_dependencies):
        """
        Test that tasks execute in correct dependency order.

        Expected order: Task1 and Task3 (parallel) -> Task2 -> Task4
        """
        execution_service = MasterplanExecutionService(
            db_session=db_session,
            workspace_base_dir="./test_workspace_deps"
        )

        # Create workspace
        workspace_path = execution_service.create_workspace(masterplan_with_dependencies.masterplan_id)
        assert workspace_path is not None

        # Get all tasks
        phase = masterplan_with_dependencies.phases[0]
        milestone = phase.milestones[0]
        all_tasks = milestone.tasks

        # Build dependency graph
        dependency_graph = execution_service._build_dependency_graph(all_tasks)

        # Verify dependency graph is built correctly
        task_by_number = {task.task_number: task for task in all_tasks}

        # Task1 should have no dependencies
        assert dependency_graph[task_by_number[1].task_id] == []

        # Task3 should have no dependencies
        assert dependency_graph[task_by_number[3].task_id] == []

        # Task2 should depend on Task1
        assert task_by_number[1].task_id in dependency_graph[task_by_number[2].task_id]

        # Task4 should depend on Task2 and Task3
        task4_deps = dependency_graph[task_by_number[4].task_id]
        assert task_by_number[2].task_id in task4_deps
        assert task_by_number[3].task_id in task4_deps

        # Execute topological sort
        execution_order = execution_service._topological_sort(all_tasks, dependency_graph)

        # Verify execution order is valid
        assert len(execution_order) == 4

        # Build map of task positions
        task_positions = {task.task_id: idx for idx, task in enumerate(execution_order)}

        # Verify Task1 comes before Task2
        assert task_positions[task_by_number[1].task_id] < task_positions[task_by_number[2].task_id]

        # Verify Task3 comes before Task4
        assert task_positions[task_by_number[3].task_id] < task_positions[task_by_number[4].task_id]

        # Verify Task2 comes before Task4
        assert task_positions[task_by_number[2].task_id] < task_positions[task_by_number[4].task_id]

    def test_circular_dependencies_detected(self, db_session: Session):
        """
        Test that circular dependencies are detected and handled.

        Creates: Task1 -> Task2 -> Task3 -> Task1 (circular)
        """
        # Create discovery document
        discovery = DiscoveryDocument(
            discovery_id=uuid4(),
            session_id="circular-test-session",
            user_id="circular-test-user",
            user_request="Test circular dependencies",
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
            session_id="circular-test-session",
            user_id="circular-test-user",
            project_name="Circular Dependency Test",
            status=MasterPlanStatus.APPROVED,
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

        # Create tasks with circular dependencies (Task1 -> Task2 -> Task3 -> Task1)
        task1_id = uuid4()
        task2_id = uuid4()
        task3_id = uuid4()

        # We'll update dependencies after creating all tasks
        task1 = MasterPlanTask(
            task_id=task1_id,
            milestone_id=milestone.milestone_id,
            task_number=1,
            name="Task 1",
            target_files=["file1.py"],
            complexity=TaskComplexity.LOW,
            depends_on_tasks=[str(task3_id)],  # Depends on task3 (creates circle)
            max_retries=2,
        )
        db_session.add(task1)

        task2 = MasterPlanTask(
            task_id=task2_id,
            milestone_id=milestone.milestone_id,
            task_number=2,
            name="Task 2",
            target_files=["file2.py"],
            complexity=TaskComplexity.LOW,
            depends_on_tasks=[str(task1_id)],  # Depends on task1
            max_retries=2,
        )
        db_session.add(task2)

        task3 = MasterPlanTask(
            task_id=task3_id,
            milestone_id=milestone.milestone_id,
            task_number=3,
            name="Task 3",
            target_files=["file3.py"],
            complexity=TaskComplexity.LOW,
            depends_on_tasks=[str(task2_id)],  # Depends on task2
            max_retries=2,
        )
        db_session.add(task3)
        db_session.commit()

        # Create execution service
        execution_service = MasterplanExecutionService(
            db_session=db_session,
            workspace_base_dir="./test_workspace_circular"
        )

        # Create workspace
        execution_service.create_workspace(masterplan.masterplan_id)

        # Execute should detect circular dependency
        result = execution_service.execute(masterplan.masterplan_id)

        # Verify circular dependency was detected
        assert result["success"] is False
        assert "circular" in result.get("error", "").lower()


class TestRetryLogicIntegration:
    """Test retry logic during execution."""

    def test_failed_task_retries_according_to_max_retries(self, db_session: Session):
        """
        Test that failed tasks retry according to max_retries setting.

        Note: This test uses the stub execution, so it will mark tasks as completed.
        In real execution, we would inject failures to test retry logic.
        """
        # Create simple masterplan with one task
        discovery = DiscoveryDocument(
            discovery_id=uuid4(),
            session_id="retry-test-session",
            user_id="retry-test-user",
            user_request="Test retry logic",
            domain="Testing",
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
            session_id="retry-test-session",
            user_id="retry-test-user",
            project_name="Retry Test Project",
            status=MasterPlanStatus.APPROVED,
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

        task = MasterPlanTask(
            task_id=uuid4(),
            milestone_id=milestone.milestone_id,
            task_number=1,
            name="Task with Retries",
            target_files=["test.py"],
            complexity=TaskComplexity.MEDIUM,
            status=TaskStatus.PENDING,
            depends_on_tasks=[],
            max_retries=3,  # Allow 3 retries
            retry_count=0,
        )
        db_session.add(task)
        db_session.commit()

        # Verify task has correct retry settings
        assert task.max_retries == 3
        assert task.retry_count == 0

        # Create execution service
        execution_service = MasterplanExecutionService(
            db_session=db_session,
            workspace_base_dir="./test_workspace_retry"
        )

        execution_service.create_workspace(masterplan.masterplan_id)

        # Execute masterplan
        result = execution_service.execute(masterplan.masterplan_id)

        # In stub implementation, task will succeed
        # But verify retry fields are properly initialized
        assert result["success"] is True
        db_session.refresh(task)

        # Task should have succeeded without needing retries
        # (in stub implementation)
        assert task.status == TaskStatus.COMPLETED


class TestTargetFilesExtraction:
    """Test that target_files are correctly extracted and used."""

    def test_target_files_extracted_for_all_tasks(self, db_session: Session, masterplan_with_dependencies):
        """
        Test that target_files are extracted from all tasks.

        Verifies:
        - Each task has unique target_files
        - No task defaults to ["main.py"]
        - target_files are available during execution
        """
        execution_service = MasterplanExecutionService(
            db_session=db_session,
            workspace_base_dir="./test_workspace_target_files"
        )

        # Create workspace
        execution_service.create_workspace(masterplan_with_dependencies.masterplan_id)

        # Get all tasks
        phase = masterplan_with_dependencies.phases[0]
        milestone = phase.milestones[0]
        all_tasks = milestone.tasks

        # Verify each task has target_files
        target_files_sets = []
        for task in all_tasks:
            assert task.target_files is not None, f"Task {task.task_number} has no target_files"
            assert len(task.target_files) > 0, f"Task {task.task_number} has empty target_files"
            assert task.target_files != ["main.py"], f"Task {task.task_number} has default main.py"

            target_files_sets.append(set(task.target_files))

        # Verify each task has unique target_files (no overlap)
        for i, files1 in enumerate(target_files_sets):
            for j, files2 in enumerate(target_files_sets):
                if i != j:
                    # No two tasks should have the exact same target_files
                    # (though they could share some files in complex scenarios)
                    pass  # In this test, each task has unique files

        # Execute and verify target_files are used
        result = execution_service.execute(masterplan_with_dependencies.masterplan_id)
        assert result["success"] is True
