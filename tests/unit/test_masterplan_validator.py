"""
Unit Tests - MasterPlanValidator (Level 4)

Tests masterplan system-wide validation including architecture, dependencies,
contracts, performance, and security checks.

Author: DevMatrix Team
Date: 2025-10-23
"""

import pytest
import uuid
from datetime import datetime
from unittest.mock import Mock, MagicMock

from src.validation.masterplan_validator import (
    MasterPlanValidator, MasterPlanValidationResult
)
from src.models import (
    MasterPlan, MasterPlanPhase, MasterPlanMilestone,
    MasterPlanTask, AtomicUnit, DependencyGraph
)


@pytest.fixture
def mock_db():
    """Create mock database session"""
    db = Mock()
    # Setup query chain mocking
    db.query.return_value = db
    db.filter.return_value = db
    db.join.return_value = db
    return db


@pytest.fixture
def validator(mock_db):
    """Create MasterPlanValidator instance"""
    return MasterPlanValidator(mock_db)


@pytest.fixture
def valid_masterplan():
    """Create a valid masterplan for testing"""
    return MasterPlan(
        masterplan_id=uuid.uuid4(),
        project_name="Test Project",
        total_tasks=3,
        estimated_duration_hours=10.0,
        status="planned",
        created_at=datetime.utcnow()
    )


@pytest.fixture
def complete_hierarchy(valid_masterplan):
    """Create complete MasterPlan hierarchy"""
    phase = MasterPlanPhase(
        phase_id=uuid.uuid4(),
        masterplan_id=valid_masterplan.masterplan_id,
        phase_name="Setup",
        phase_description="Setup phase",
        phase_order=1,
        status="planned"
    )

    milestone = MasterPlanMilestone(
        milestone_id=uuid.uuid4(),
        phase_id=phase.phase_id,
        milestone_name="Database",
        milestone_description="Database milestone",
        milestone_order=1,
        status="planned"
    )

    task = MasterPlanTask(
        task_id=uuid.uuid4(),
        milestone_id=milestone.milestone_id,
        task_name="Schema",
        task_description="Database schema",
        task_order=1,
        estimated_duration_hours=3.0,
        status="planned"
    )

    atom = AtomicUnit(
        atom_id=uuid.uuid4(),
        masterplan_id=valid_masterplan.masterplan_id,
        task_id=task.task_id,
        atom_number=1,
        description="Create table",
        code_to_generate="def create_table(): pass",
        file_path="src/db.py",
        language="python",
        complexity=1.5,
        status="pending",
        dependencies=[],
        context_completeness=0.95
    )

    return {
        'masterplan': valid_masterplan,
        'phases': [phase],
        'milestones': [milestone],
        'tasks': [task],
        'atoms': [atom]
    }


# ============================================================================
# Architecture Validation Tests
# ============================================================================

def test_validate_architecture_valid(validator, complete_hierarchy, mock_db):
    """Test architecture validation with valid structure"""
    hierarchy = complete_hierarchy

    # Setup mock returns
    mock_db.first.return_value = hierarchy['masterplan']

    # Mock phases query
    phases_query = Mock()
    phases_query.all.return_value = hierarchy['phases']

    # Mock milestones query
    milestones_query = Mock()
    milestones_query.all.return_value = hierarchy['milestones']

    # Mock tasks query
    tasks_query = Mock()
    tasks_query.all.return_value = hierarchy['tasks']

    # Mock atoms query
    atoms_query = Mock()
    atoms_query.all.return_value = hierarchy['atoms']

    # Setup query chain
    mock_db.query.side_effect = [
        mock_db,  # MasterPlan query
        phases_query,  # MasterPlanPhase query
        milestones_query,  # MasterPlanMilestone query
        tasks_query,  # MasterPlanTask query
        atoms_query,  # AtomicUnit query
    ]

    result = validator.validate_system(hierarchy['masterplan'].masterplan_id)

    assert result.architecture_valid == True


def test_validate_architecture_no_phases(validator, valid_masterplan, mock_db):
    """Test architecture validation detects missing phases"""
    mock_db.first.return_value = valid_masterplan

    # Return empty lists for all hierarchy queries
    empty_query = Mock()
    empty_query.all.return_value = []
    mock_db.query.side_effect = [
        mock_db,  # MasterPlan query
        empty_query,  # Phases
        empty_query,  # Milestones
        empty_query,  # Tasks
        empty_query,  # Atoms
    ]

    result = validator.validate_system(valid_masterplan.masterplan_id)

    # Empty masterplan is valid (planning phase)
    assert result.is_valid == True
    assert len(result.warnings) > 0


# ============================================================================
# Dependencies Validation Tests
# ============================================================================

def test_validate_dependencies_no_cycles(validator, complete_hierarchy, mock_db):
    """Test dependency validation with no cycles"""
    hierarchy = complete_hierarchy

    # Create valid dependency graph
    dep_graph = DependencyGraph(
        graph_id=uuid.uuid4(),
        masterplan_id=hierarchy['masterplan'].masterplan_id,
        total_atoms=1,
        total_dependencies=0,
        has_cycles=False,
        max_parallelism=1,
        created_at=datetime.utcnow()
    )

    # Setup mock chain
    mock_db.first.side_effect = [
        hierarchy['masterplan'],  # MasterPlan query
        dep_graph  # DependencyGraph query
    ]

    phases_query = Mock()
    phases_query.all.return_value = hierarchy['phases']

    milestones_query = Mock()
    milestones_query.all.return_value = hierarchy['milestones']

    tasks_query = Mock()
    tasks_query.all.return_value = hierarchy['tasks']

    atoms_query = Mock()
    atoms_query.all.return_value = hierarchy['atoms']

    mock_db.query.side_effect = [
        mock_db,  # MasterPlan
        phases_query,  # Phases
        milestones_query,  # Milestones
        tasks_query,  # Tasks
        atoms_query,  # Atoms
        mock_db,  # DependencyGraph
    ]

    result = validator.validate_system(hierarchy['masterplan'].masterplan_id)

    assert result.dependencies_valid == True


def test_validate_dependencies_with_cycles(validator, complete_hierarchy, mock_db):
    """Test dependency validation detects cycles"""
    hierarchy = complete_hierarchy

    # Create dependency graph with cycles
    dep_graph = DependencyGraph(
        graph_id=uuid.uuid4(),
        masterplan_id=hierarchy['masterplan'].masterplan_id,
        total_atoms=2,
        total_dependencies=2,
        has_cycles=True,
        max_parallelism=1,
        created_at=datetime.utcnow()
    )

    mock_db.first.side_effect = [
        hierarchy['masterplan'],
        dep_graph
    ]

    phases_query = Mock()
    phases_query.all.return_value = hierarchy['phases']

    milestones_query = Mock()
    milestones_query.all.return_value = hierarchy['milestones']

    tasks_query = Mock()
    tasks_query.all.return_value = hierarchy['tasks']

    atoms_query = Mock()
    atoms_query.all.return_value = hierarchy['atoms']

    mock_db.query.side_effect = [
        mock_db,
        phases_query,
        milestones_query,
        tasks_query,
        atoms_query,
        mock_db,
    ]

    result = validator.validate_system(hierarchy['masterplan'].masterplan_id)

    assert result.dependencies_valid == False
    assert len(result.errors) > 0


# ============================================================================
# Performance Validation Tests
# ============================================================================

def test_validate_performance_acceptable(validator, complete_hierarchy, mock_db):
    """Test performance validation with acceptable metrics"""
    hierarchy = complete_hierarchy

    mock_db.first.return_value = hierarchy['masterplan']

    phases_query = Mock()
    phases_query.all.return_value = hierarchy['phases']

    milestones_query = Mock()
    milestones_query.all.return_value = hierarchy['milestones']

    tasks_query = Mock()
    tasks_query.all.return_value = hierarchy['tasks']

    atoms_query = Mock()
    atoms_query.all.return_value = hierarchy['atoms']

    mock_db.query.side_effect = [
        mock_db,
        phases_query,
        milestones_query,
        tasks_query,
        atoms_query,
    ]

    result = validator.validate_system(hierarchy['masterplan'].masterplan_id)

    assert result.performance_acceptable == True


# ============================================================================
# Security Validation Tests
# ============================================================================

def test_validate_security_safe_code(validator, complete_hierarchy, mock_db):
    """Test security validation with safe code"""
    hierarchy = complete_hierarchy

    mock_db.first.return_value = hierarchy['masterplan']

    phases_query = Mock()
    phases_query.all.return_value = hierarchy['phases']

    milestones_query = Mock()
    milestones_query.all.return_value = hierarchy['milestones']

    tasks_query = Mock()
    tasks_query.all.return_value = hierarchy['tasks']

    atoms_query = Mock()
    atoms_query.all.return_value = hierarchy['atoms']

    mock_db.query.side_effect = [
        mock_db,
        phases_query,
        milestones_query,
        tasks_query,
        atoms_query,
    ]

    result = validator.validate_system(hierarchy['masterplan'].masterplan_id)

    assert result.security_acceptable == True


def test_validate_security_dangerous_patterns(validator, complete_hierarchy, mock_db):
    """Test security validation detects dangerous patterns"""
    hierarchy = complete_hierarchy

    # Create atom with dangerous code
    dangerous_atom = AtomicUnit(
        atom_id=uuid.uuid4(),
        masterplan_id=hierarchy['masterplan'].masterplan_id,
        task_id=hierarchy['tasks'][0].task_id,
        atom_number=2,
        description="Dangerous code",
        code_to_generate='def dangerous(): eval("print(1)")',
        file_path="src/dangerous.py",
        language="python",
        complexity=1.0,
        status="pending",
        dependencies=[],
        context_completeness=0.9
    )

    mock_db.first.return_value = hierarchy['masterplan']

    phases_query = Mock()
    phases_query.all.return_value = hierarchy['phases']

    milestones_query = Mock()
    milestones_query.all.return_value = hierarchy['milestones']

    tasks_query = Mock()
    tasks_query.all.return_value = hierarchy['tasks']

    atoms_query = Mock()
    atoms_query.all.return_value = [dangerous_atom]

    mock_db.query.side_effect = [
        mock_db,
        phases_query,
        milestones_query,
        tasks_query,
        atoms_query,
    ]

    result = validator.validate_system(hierarchy['masterplan'].masterplan_id)

    assert result.security_acceptable == False
    assert len(result.warnings) > 0


# ============================================================================
# Overall Validation Tests
# ============================================================================

def test_validate_masterplan_not_found(validator, mock_db):
    """Test validation when masterplan doesn't exist"""
    mock_db.first.return_value = None

    result = validator.validate_system(uuid.uuid4())

    assert result.is_valid == False
    assert "not found" in result.errors[0].lower()


def test_validate_masterplan_score_calculation(validator, complete_hierarchy, mock_db):
    """Test validation score calculation"""
    hierarchy = complete_hierarchy

    mock_db.first.return_value = hierarchy['masterplan']

    phases_query = Mock()
    phases_query.all.return_value = hierarchy['phases']

    milestones_query = Mock()
    milestones_query.all.return_value = hierarchy['milestones']

    tasks_query = Mock()
    tasks_query.all.return_value = hierarchy['tasks']

    atoms_query = Mock()
    atoms_query.all.return_value = hierarchy['atoms']

    mock_db.query.side_effect = [
        mock_db,
        phases_query,
        milestones_query,
        tasks_query,
        atoms_query,
    ]

    result = validator.validate_system(hierarchy['masterplan'].masterplan_id)

    # Score should be based on 5 checks
    assert 0.0 <= result.validation_score <= 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
