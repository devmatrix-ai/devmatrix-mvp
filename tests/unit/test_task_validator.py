"""
Unit Tests - TaskValidator (Level 2)

Tests task coherence validation including consistency, integration,
imports, naming, and contracts checks.

Author: DevMatrix Team
Date: 2025-10-23
"""

import pytest
import uuid
from datetime import datetime
from unittest.mock import Mock, MagicMock

from src.validation.task_validator import TaskValidator, TaskValidationResult
from src.models import MasterPlanTask, AtomicUnit


@pytest.fixture
def mock_db():
    """Create mock database session"""
    return Mock()


@pytest.fixture
def validator(mock_db):
    """Create TaskValidator instance"""
    return TaskValidator(mock_db)


@pytest.fixture
def valid_task():
    """Create a valid task for testing"""
    return MasterPlanTask(
        task_id=uuid.uuid4(),
        milestone_id=uuid.uuid4(),
        task_name="Database Setup",
        task_description="Setup database schema and connections",
        task_order=1,
        estimated_duration_hours=3.0,
        status="planned"
    )


@pytest.fixture
def valid_atoms():
    """Create valid atoms for a task"""
    task_id = uuid.uuid4()
    return [
        AtomicUnit(
            atom_id=uuid.uuid4(),
            masterplan_id=uuid.uuid4(),
            task_id=task_id,
            atom_number=1,
            description="Import statements",
            code_to_generate="from typing import Dict\nimport json",
            file_path="src/database.py",
            language="python",
            complexity=1.0,
            status="pending",
            dependencies=[],
            context_completeness=0.95
        ),
        AtomicUnit(
            atom_id=uuid.uuid4(),
            masterplan_id=uuid.uuid4(),
            task_id=task_id,
            atom_number=2,
            description="Database connection",
            code_to_generate="def connect_db() -> Dict:\n    return {'status': 'connected'}",
            file_path="src/database.py",
            language="python",
            complexity=1.5,
            status="pending",
            dependencies=[],
            context_completeness=0.95
        )
    ]


# ============================================================================
# Consistency Validation Tests
# ============================================================================

def test_validate_consistency_same_language(validator, valid_task, valid_atoms, mock_db):
    """Test consistency validation with same language"""
    mock_db.query().filter().first.return_value = valid_task
    mock_db.query().filter().all.return_value = valid_atoms

    result = validator.validate_task(valid_task.task_id)

    assert result.consistency_valid == True


def test_validate_consistency_mixed_languages(validator, valid_task, mock_db):
    """Test consistency validation detects mixed languages"""
    mixed_atoms = [
        AtomicUnit(
            atom_id=uuid.uuid4(),
            masterplan_id=uuid.uuid4(),
            task_id=valid_task.task_id,
            atom_number=1,
            description="Python code",
            code_to_generate="def func(): pass",
            file_path="src/test.py",
            language="python",
            complexity=1.0,
            status="pending",
            dependencies=[],
            context_completeness=0.9
        ),
        AtomicUnit(
            atom_id=uuid.uuid4(),
            masterplan_id=uuid.uuid4(),
            task_id=valid_task.task_id,
            atom_number=2,
            description="JavaScript code",
            code_to_generate="function func() {}",
            file_path="src/test.js",
            language="javascript",
            complexity=1.0,
            status="pending",
            dependencies=[],
            context_completeness=0.9
        )
    ]

    mock_db.query().filter().first.return_value = valid_task
    mock_db.query().filter().all.return_value = mixed_atoms

    result = validator.validate_task(valid_task.task_id)

    assert result.consistency_valid == False
    assert len(result.warnings) > 0


# ============================================================================
# Integration Validation Tests
# ============================================================================

def test_validate_integration_symbol_resolution(validator, valid_task, mock_db):
    """Test integration validation with proper symbol usage"""
    integrated_atoms = [
        AtomicUnit(
            atom_id=uuid.uuid4(),
            masterplan_id=uuid.uuid4(),
            task_id=valid_task.task_id,
            atom_number=1,
            description="Define function",
            code_to_generate="def helper_function(x):\n    return x * 2",
            file_path="src/helpers.py",
            language="python",
            complexity=1.0,
            status="pending",
            dependencies=[],
            context_completeness=0.95
        ),
        AtomicUnit(
            atom_id=uuid.uuid4(),
            masterplan_id=uuid.uuid4(),
            task_id=valid_task.task_id,
            atom_number=2,
            description="Use function",
            code_to_generate="def main():\n    result = helper_function(5)\n    return result",
            file_path="src/main.py",
            language="python",
            complexity=1.0,
            status="pending",
            dependencies=[],
            context_completeness=0.95
        )
    ]

    mock_db.query().filter().first.return_value = valid_task
    mock_db.query().filter().all.return_value = integrated_atoms

    result = validator.validate_task(valid_task.task_id)

    assert result.integration_valid == True


# ============================================================================
# Imports Validation Tests
# ============================================================================

def test_validate_imports_duplicate_detection(validator, valid_task, mock_db):
    """Test import validation detects duplicates"""
    atoms_with_duplicates = [
        AtomicUnit(
            atom_id=uuid.uuid4(),
            masterplan_id=uuid.uuid4(),
            task_id=valid_task.task_id,
            atom_number=1,
            description="First import",
            code_to_generate="import json\nimport typing",
            file_path="src/file1.py",
            language="python",
            complexity=1.0,
            status="pending",
            dependencies=[],
            context_completeness=0.9
        ),
        AtomicUnit(
            atom_id=uuid.uuid4(),
            masterplan_id=uuid.uuid4(),
            task_id=valid_task.task_id,
            atom_number=2,
            description="Duplicate import",
            code_to_generate="import json\nimport os",
            file_path="src/file2.py",
            language="python",
            complexity=1.0,
            status="pending",
            dependencies=[],
            context_completeness=0.9
        )
    ]

    mock_db.query().filter().first.return_value = valid_task
    mock_db.query().filter().all.return_value = atoms_with_duplicates

    result = validator.validate_task(valid_task.task_id)

    # Duplicate imports should generate warnings
    assert len(result.warnings) > 0


# ============================================================================
# Naming Validation Tests
# ============================================================================

def test_validate_naming_consistent_style(validator, valid_task, valid_atoms, mock_db):
    """Test naming validation with consistent style"""
    mock_db.query().filter().first.return_value = valid_task
    mock_db.query().filter().all.return_value = valid_atoms

    result = validator.validate_task(valid_task.task_id)

    assert result.naming_valid == True


def test_validate_naming_inconsistent_style(validator, valid_task, mock_db):
    """Test naming validation detects inconsistent style"""
    inconsistent_atoms = [
        AtomicUnit(
            atom_id=uuid.uuid4(),
            masterplan_id=uuid.uuid4(),
            task_id=valid_task.task_id,
            atom_number=1,
            description="Snake case",
            code_to_generate="def my_function(): pass",
            file_path="src/test.py",
            language="python",
            complexity=1.0,
            status="pending",
            dependencies=[],
            context_completeness=0.9
        ),
        AtomicUnit(
            atom_id=uuid.uuid4(),
            masterplan_id=uuid.uuid4(),
            task_id=valid_task.task_id,
            atom_number=2,
            description="Camel case",
            code_to_generate="def myFunction(): pass",
            file_path="src/test.py",
            language="python",
            complexity=1.0,
            status="pending",
            dependencies=[],
            context_completeness=0.9
        )
    ]

    mock_db.query().filter().first.return_value = valid_task
    mock_db.query().filter().all.return_value = inconsistent_atoms

    result = validator.validate_task(valid_task.task_id)

    assert result.naming_valid == False


# ============================================================================
# Contracts Validation Tests
# ============================================================================

def test_validate_contracts_public_api(validator, valid_task, valid_atoms, mock_db):
    """Test contract validation checks public API consistency"""
    mock_db.query().filter().first.return_value = valid_task
    mock_db.query().filter().all.return_value = valid_atoms

    result = validator.validate_task(valid_task.task_id)

    assert result.contracts_valid == True


# ============================================================================
# Overall Validation Tests
# ============================================================================

def test_validate_task_not_found(validator, mock_db):
    """Test validation when task doesn't exist"""
    mock_db.query().filter().first.return_value = None

    result = validator.validate_task(uuid.uuid4())

    assert result.is_valid == False
    assert "not found" in result.errors[0].lower()


def test_validate_task_no_atoms(validator, valid_task, mock_db):
    """Test validation when task has no atoms"""
    mock_db.query().filter().first.return_value = valid_task
    mock_db.query().filter().all.return_value = []

    result = validator.validate_task(valid_task.task_id)

    assert result.is_valid == False
    assert len(result.errors) > 0


def test_validate_task_score_calculation(validator, valid_task, valid_atoms, mock_db):
    """Test validation score calculation"""
    mock_db.query().filter().first.return_value = valid_task
    mock_db.query().filter().all.return_value = valid_atoms

    result = validator.validate_task(valid_task.task_id)

    # Score should be based on 5 checks (20% each)
    assert 0.0 <= result.validation_score <= 1.0
    assert result.validation_score >= 0.7


def test_validate_task_multiple_issues(validator, valid_task, mock_db):
    """Test validation with multiple issues"""
    problematic_atoms = [
        AtomicUnit(
            atom_id=uuid.uuid4(),
            masterplan_id=uuid.uuid4(),
            task_id=valid_task.task_id,
            atom_number=1,
            description="Python code",
            code_to_generate="def myFunction(): pass",  # Wrong naming for Python
            file_path="src/test.py",
            language="python",
            complexity=1.0,
            status="pending",
            dependencies=[],
            context_completeness=0.6  # Low context
        ),
        AtomicUnit(
            atom_id=uuid.uuid4(),
            masterplan_id=uuid.uuid4(),
            task_id=valid_task.task_id,
            atom_number=2,
            description="JavaScript code",  # Mixed language
            code_to_generate="function test() {}",
            file_path="src/test.js",
            language="javascript",
            complexity=1.0,
            status="pending",
            dependencies=[],
            context_completeness=0.6
        )
    ]

    mock_db.query().filter().first.return_value = valid_task
    mock_db.query().filter().all.return_value = problematic_atoms

    result = validator.validate_task(valid_task.task_id)

    # Should have multiple issues
    assert len(result.issues) > 1
    assert result.validation_score < 0.7


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
