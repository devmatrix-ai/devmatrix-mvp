"""
PostgreSQL E2E Tests - Validation System

Tests the complete 4-level hierarchical validation system using PostgreSQL.
Avoids SQLite limitations with ARRAY types.

Author: DevMatrix Team
Date: 2025-10-23
"""

import pytest
import uuid
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.models import (
    Base, MasterPlan, MasterPlanPhase, MasterPlanMilestone,
    MasterPlanTask, AtomicUnit, DependencyGraph, ExecutionWave
)
from src.validation import (
    AtomicValidator, TaskValidator, MilestoneValidator, MasterPlanValidator
)
from src.services.validation_service import ValidationService


# PostgreSQL connection string
POSTGRES_URL = "postgresql://devmatrix:devmatrix@localhost:5432/devmatrix_test"


@pytest.fixture(scope="module")
def postgres_engine():
    """Create PostgreSQL engine for testing"""
    engine = create_engine(POSTGRES_URL)

    # Create all tables
    Base.metadata.create_all(engine)

    yield engine

    # Cleanup: Drop all tables after tests
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def db_session(postgres_engine):
    """Create a fresh database session for each test"""
    Session = sessionmaker(bind=postgres_engine)
    session = Session()

    yield session

    # Rollback any uncommitted changes
    session.rollback()
    session.close()


@pytest.fixture
def sample_masterplan(db_session):
    """Create a sample MasterPlan with complete hierarchy"""
    # Create MasterPlan
    masterplan = MasterPlan(
        masterplan_id=uuid.uuid4(),
        project_name="Test Validation Project",
        total_tasks=3,
        estimated_duration_hours=10.0,
        status="planned",
        created_at=datetime.utcnow()
    )
    db_session.add(masterplan)
    db_session.flush()

    # Create Phase
    phase = MasterPlanPhase(
        phase_id=uuid.uuid4(),
        masterplan_id=masterplan.masterplan_id,
        phase_name="Setup Phase",
        phase_description="Initial setup and configuration",
        phase_order=1,
        status="planned"
    )
    db_session.add(phase)
    db_session.flush()

    # Create Milestone
    milestone = MasterPlanMilestone(
        milestone_id=uuid.uuid4(),
        phase_id=phase.phase_id,
        milestone_name="Database Setup",
        milestone_description="Set up database schema and connections",
        milestone_order=1,
        status="planned"
    )
    db_session.add(milestone)
    db_session.flush()

    # Create 3 Tasks
    tasks = []
    for i in range(3):
        task = MasterPlanTask(
            task_id=uuid.uuid4(),
            milestone_id=milestone.milestone_id,
            task_name=f"Task {i+1}",
            task_description=f"Implementation of task {i+1}",
            task_order=i+1,
            estimated_duration_hours=3.0,
            status="planned"
        )
        db_session.add(task)
        tasks.append(task)

    db_session.flush()

    # Create Atoms for each task
    all_atoms = []
    for task_idx, task in enumerate(tasks):
        for atom_idx in range(2):  # 2 atoms per task
            atom = AtomicUnit(
                atom_id=uuid.uuid4(),
                masterplan_id=masterplan.masterplan_id,
                task_id=task.task_id,
                atom_number=task_idx * 2 + atom_idx + 1,
                description=f"Atom {atom_idx+1} for {task.task_name}",
                code_to_generate=f"""
def function_{task_idx}_{atom_idx}():
    \"\"\"Sample function for testing\"\"\"
    x = 10
    y = 20
    return x + y
""",
                file_path=f"src/module_{task_idx}.py",
                language="python",
                complexity=1.5,
                status="pending",
                dependencies=[],
                context_completeness=0.95,
                imports=["typing"],
                type_schema={},
                preconditions=[],
                postconditions=[],
                test_cases=[],
                created_at=datetime.utcnow()
            )
            db_session.add(atom)
            all_atoms.append(atom)

    db_session.commit()

    return {
        'masterplan': masterplan,
        'phase': phase,
        'milestone': milestone,
        'tasks': tasks,
        'atoms': all_atoms
    }


# ============================================================================
# Level 1: Atomic Validation Tests
# ============================================================================

def test_atomic_validator_valid_atom(db_session, sample_masterplan):
    """Test Level 1: Validate a valid atom"""
    validator = AtomicValidator(db_session)
    atom = sample_masterplan['atoms'][0]

    result = validator.validate_atom(atom.atom_id)

    assert result is not None
    assert result.atom_id == atom.atom_id
    assert result.is_valid == True
    assert result.validation_score >= 0.8
    assert result.syntax_valid == True
    assert len(result.errors) == 0


def test_atomic_validator_invalid_syntax(db_session, sample_masterplan):
    """Test Level 1: Detect syntax errors"""
    # Create atom with invalid syntax
    atom = AtomicUnit(
        atom_id=uuid.uuid4(),
        masterplan_id=sample_masterplan['masterplan'].masterplan_id,
        task_id=sample_masterplan['tasks'][0].task_id,
        atom_number=100,
        description="Invalid syntax atom",
        code_to_generate="def invalid_function(\n    # Missing closing parenthesis",
        file_path="src/invalid.py",
        language="python",
        complexity=1.0,
        status="pending",
        dependencies=[],
        context_completeness=0.5
    )
    db_session.add(atom)
    db_session.commit()

    validator = AtomicValidator(db_session)
    result = validator.validate_atom(atom.atom_id)

    assert result.syntax_valid == False
    assert result.is_valid == False
    assert len(result.errors) > 0


def test_atomic_validator_high_complexity(db_session, sample_masterplan):
    """Test Level 1: Detect high complexity"""
    # Create atom with high complexity
    complex_code = """
def complex_function(x):
    if x > 10:
        if x > 20:
            if x > 30:
                if x > 40:
                    return 1
                return 2
            return 3
        return 4
    return 5
"""

    atom = AtomicUnit(
        atom_id=uuid.uuid4(),
        masterplan_id=sample_masterplan['masterplan'].masterplan_id,
        task_id=sample_masterplan['tasks'][0].task_id,
        atom_number=101,
        description="High complexity atom",
        code_to_generate=complex_code,
        file_path="src/complex.py",
        language="python",
        complexity=6.0,
        status="pending",
        dependencies=[],
        context_completeness=0.9
    )
    db_session.add(atom)
    db_session.commit()

    validator = AtomicValidator(db_session)
    result = validator.validate_atom(atom.atom_id)

    assert result.atomicity_valid == False
    assert len(result.warnings) > 0


# ============================================================================
# Level 2: Task Validation Tests
# ============================================================================

def test_task_validator_valid_task(db_session, sample_masterplan):
    """Test Level 2: Validate a valid task"""
    validator = TaskValidator(db_session)
    task = sample_masterplan['tasks'][0]

    result = validator.validate_task(task.task_id)

    assert result is not None
    assert result.task_id == task.task_id
    assert result.is_valid == True
    assert result.validation_score >= 0.7
    assert result.consistency_valid == True


def test_task_validator_empty_task(db_session, sample_masterplan):
    """Test Level 2: Detect empty task (no atoms)"""
    # Create task with no atoms
    empty_task = MasterPlanTask(
        task_id=uuid.uuid4(),
        milestone_id=sample_masterplan['milestone'].milestone_id,
        task_name="Empty Task",
        task_description="Task with no atoms",
        task_order=10,
        estimated_duration_hours=1.0,
        status="planned"
    )
    db_session.add(empty_task)
    db_session.commit()

    validator = TaskValidator(db_session)
    result = validator.validate_task(empty_task.task_id)

    assert result.is_valid == False
    assert len(result.errors) > 0


def test_task_validator_consistency(db_session, sample_masterplan):
    """Test Level 2: Check consistency between atoms in task"""
    validator = TaskValidator(db_session)
    task = sample_masterplan['tasks'][0]

    result = validator.validate_task(task.task_id)

    # Should have consistent language (all Python)
    assert result.consistency_valid == True
    assert result.validation_score > 0.0


# ============================================================================
# Level 3: Milestone Validation Tests
# ============================================================================

def test_milestone_validator_valid_milestone(db_session, sample_masterplan):
    """Test Level 3: Validate a valid milestone"""
    validator = MilestoneValidator(db_session)
    milestone = sample_masterplan['milestone']

    result = validator.validate_milestone(milestone.milestone_id)

    assert result is not None
    assert result.milestone_id == milestone.milestone_id
    assert result.is_valid == True
    assert result.validation_score >= 0.7


def test_milestone_validator_empty_milestone(db_session, sample_masterplan):
    """Test Level 3: Detect empty milestone (no tasks)"""
    # Create milestone with no tasks
    empty_milestone = MasterPlanMilestone(
        milestone_id=uuid.uuid4(),
        phase_id=sample_masterplan['phase'].phase_id,
        milestone_name="Empty Milestone",
        milestone_description="Milestone with no tasks",
        milestone_order=10,
        status="planned"
    )
    db_session.add(empty_milestone)
    db_session.commit()

    validator = MilestoneValidator(db_session)
    result = validator.validate_milestone(empty_milestone.milestone_id)

    assert result.is_valid == False
    assert len(result.warnings) > 0


def test_milestone_validator_integration(db_session, sample_masterplan):
    """Test Level 3: Check task integration within milestone"""
    validator = MilestoneValidator(db_session)
    milestone = sample_masterplan['milestone']

    result = validator.validate_milestone(milestone.milestone_id)

    assert result.integration_valid == True


# ============================================================================
# Level 4: MasterPlan Validation Tests
# ============================================================================

def test_masterplan_validator_valid_masterplan(db_session, sample_masterplan):
    """Test Level 4: Validate a valid masterplan"""
    validator = MasterPlanValidator(db_session)
    masterplan = sample_masterplan['masterplan']

    result = validator.validate_system(masterplan.masterplan_id)

    assert result is not None
    assert result.masterplan_id == masterplan.masterplan_id
    assert result.is_valid == True
    assert result.validation_score >= 0.7
    assert result.architecture_valid == True


def test_masterplan_validator_empty_masterplan(db_session):
    """Test Level 4: Detect empty masterplan"""
    # Create masterplan with no content
    empty_masterplan = MasterPlan(
        masterplan_id=uuid.uuid4(),
        project_name="Empty Project",
        total_tasks=0,
        estimated_duration_hours=0.0,
        status="planned",
        created_at=datetime.utcnow()
    )
    db_session.add(empty_masterplan)
    db_session.commit()

    validator = MasterPlanValidator(db_session)
    result = validator.validate_system(empty_masterplan.masterplan_id)

    # Empty masterplan should be valid (planning phase)
    assert result.is_valid == True
    assert len(result.warnings) > 0


def test_masterplan_validator_statistics(db_session, sample_masterplan):
    """Test Level 4: Verify statistics collection"""
    validator = MasterPlanValidator(db_session)
    masterplan = sample_masterplan['masterplan']

    result = validator.validate_system(masterplan.masterplan_id)

    assert result.total_atoms == 6  # 3 tasks * 2 atoms
    assert result.total_tasks == 3
    assert result.total_milestones == 1


# ============================================================================
# Hierarchical Validation Tests
# ============================================================================

def test_validation_service_hierarchical(db_session, sample_masterplan):
    """Test complete hierarchical validation"""
    service = ValidationService(db_session)
    masterplan = sample_masterplan['masterplan']

    result = service.validate_hierarchical(masterplan.masterplan_id)

    assert result['masterplan_id'] == str(masterplan.masterplan_id)
    assert result['overall_valid'] == True
    assert result['overall_score'] >= 0.7

    # Check all levels were validated
    assert 'atomic' in result['results']
    assert 'task' in result['results']
    assert 'milestone' in result['results']
    assert 'masterplan' in result['results']

    # Check atomic level
    assert result['results']['atomic']['total_atoms'] == 6

    # Check task level
    assert result['results']['task']['total_tasks'] == 3

    # Check milestone level
    assert result['results']['milestone']['total_milestones'] == 1


def test_validation_service_selective_levels(db_session, sample_masterplan):
    """Test hierarchical validation with selected levels"""
    service = ValidationService(db_session)
    masterplan = sample_masterplan['masterplan']

    # Only validate atomic and task levels
    result = service.validate_hierarchical(
        masterplan.masterplan_id,
        levels=['atomic', 'task']
    )

    assert 'atomic' in result['results']
    assert 'task' in result['results']
    assert 'milestone' not in result['results']
    assert 'masterplan' not in result['results']


def test_validation_service_batch_atoms(db_session, sample_masterplan):
    """Test batch atom validation"""
    service = ValidationService(db_session)
    atoms = sample_masterplan['atoms']

    # Batch validate first 3 atoms
    atom_ids = [atom.atom_id for atom in atoms[:3]]
    result = service.batch_validate_atoms(atom_ids)

    assert result['total_atoms'] == 3
    assert result['valid_atoms'] >= 0
    assert 'avg_score' in result
    assert len(result['atoms']) == 3


# ============================================================================
# Performance Tests
# ============================================================================

def test_validation_performance_large_masterplan(db_session):
    """Test validation performance with larger dataset"""
    # Create masterplan with more atoms
    masterplan = MasterPlan(
        masterplan_id=uuid.uuid4(),
        project_name="Large Test Project",
        total_tasks=10,
        estimated_duration_hours=50.0,
        status="planned",
        created_at=datetime.utcnow()
    )
    db_session.add(masterplan)
    db_session.flush()

    phase = MasterPlanPhase(
        phase_id=uuid.uuid4(),
        masterplan_id=masterplan.masterplan_id,
        phase_name="Core Phase",
        phase_description="Core implementation",
        phase_order=1,
        status="planned"
    )
    db_session.add(phase)
    db_session.flush()

    milestone = MasterPlanMilestone(
        milestone_id=uuid.uuid4(),
        phase_id=phase.phase_id,
        milestone_name="Implementation",
        milestone_description="Core implementation milestone",
        milestone_order=1,
        status="planned"
    )
    db_session.add(milestone)
    db_session.flush()

    # Create 10 tasks with 5 atoms each = 50 atoms total
    for task_idx in range(10):
        task = MasterPlanTask(
            task_id=uuid.uuid4(),
            milestone_id=milestone.milestone_id,
            task_name=f"Task {task_idx+1}",
            task_description=f"Implementation task {task_idx+1}",
            task_order=task_idx+1,
            estimated_duration_hours=5.0,
            status="planned"
        )
        db_session.add(task)
        db_session.flush()

        for atom_idx in range(5):
            atom = AtomicUnit(
                atom_id=uuid.uuid4(),
                masterplan_id=masterplan.masterplan_id,
                task_id=task.task_id,
                atom_number=task_idx * 5 + atom_idx + 1,
                description=f"Atom {atom_idx+1}",
                code_to_generate=f"def func_{task_idx}_{atom_idx}(): return {atom_idx}",
                file_path=f"src/module_{task_idx}.py",
                language="python",
                complexity=1.5,
                status="pending",
                dependencies=[],
                context_completeness=0.9
            )
            db_session.add(atom)

    db_session.commit()

    # Validate hierarchically - should complete without timeout
    service = ValidationService(db_session)
    result = service.validate_hierarchical(masterplan.masterplan_id)

    assert result['overall_valid'] == True
    assert result['results']['atomic']['total_atoms'] == 50
    assert result['results']['task']['total_tasks'] == 10


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
