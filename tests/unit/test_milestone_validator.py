"""
Unit Tests - MilestoneValidator (Level 3)

Tests milestone integration validation including interfaces, contracts,
API consistency, integration, and dependencies checks.

Author: DevMatrix Team
Date: 2025-10-23
"""

import pytest
import uuid
from unittest.mock import Mock

from src.validation.milestone_validator import MilestoneValidator, MilestoneValidationResult
from src.models import MasterPlanMilestone, MasterPlanTask


@pytest.fixture
def mock_db():
    """Create mock database session"""
    return Mock()


@pytest.fixture
def validator(mock_db):
    """Create MilestoneValidator instance"""
    return MilestoneValidator(mock_db)


@pytest.fixture
def valid_milestone():
    """Create a valid milestone for testing"""
    return MasterPlanMilestone(
        milestone_id=uuid.uuid4(),
        phase_id=uuid.uuid4(),
        milestone_name="Database Implementation",
        milestone_description="Implement database layer",
        milestone_order=1,
        status="planned"
    )


@pytest.fixture
def valid_tasks():
    """Create valid tasks for a milestone"""
    milestone_id = uuid.uuid4()
    return [
        MasterPlanTask(
            task_id=uuid.uuid4(),
            milestone_id=milestone_id,
            task_name="Schema Design",
            task_description="Design database schema",
            task_order=1,
            estimated_duration_hours=3.0,
            status="planned"
        ),
        MasterPlanTask(
            task_id=uuid.uuid4(),
            milestone_id=milestone_id,
            task_name="Connection Pool",
            task_description="Implement connection pooling",
            task_order=2,
            estimated_duration_hours=2.0,
            status="planned"
        )
    ]


# ============================================================================
# Interface Validation Tests
# ============================================================================

def test_validate_interfaces_valid_tasks(validator, valid_milestone, valid_tasks, mock_db):
    """Test interface validation with valid tasks"""
    mock_db.query().filter().first.return_value = valid_milestone
    mock_db.query().filter().all.return_value = valid_tasks

    result = validator.validate_milestone(valid_milestone.milestone_id)

    assert result.interfaces_valid == True


def test_validate_interfaces_missing_tasks(validator, valid_milestone, mock_db):
    """Test interface validation detects missing tasks"""
    mock_db.query().filter().first.return_value = valid_milestone
    mock_db.query().filter().all.return_value = []

    result = validator.validate_milestone(valid_milestone.milestone_id)

    assert result.interfaces_valid == False
    assert len(result.warnings) > 0


# ============================================================================
# Contracts Validation Tests
# ============================================================================

def test_validate_contracts_valid(validator, valid_milestone, valid_tasks, mock_db):
    """Test contract validation with valid milestone"""
    mock_db.query().filter().first.return_value = valid_milestone
    mock_db.query().filter().all.return_value = valid_tasks

    result = validator.validate_milestone(valid_milestone.milestone_id)

    assert result.contracts_valid == True


# ============================================================================
# API Consistency Tests
# ============================================================================

def test_validate_api_consistency(validator, valid_milestone, valid_tasks, mock_db):
    """Test API consistency validation"""
    mock_db.query().filter().first.return_value = valid_milestone
    mock_db.query().filter().all.return_value = valid_tasks

    result = validator.validate_milestone(valid_milestone.milestone_id)

    assert result.api_consistent == True


# ============================================================================
# Integration Validation Tests
# ============================================================================

def test_validate_integration_valid(validator, valid_milestone, valid_tasks, mock_db):
    """Test integration validation with valid tasks"""
    mock_db.query().filter().first.return_value = valid_milestone
    mock_db.query().filter().all.return_value = valid_tasks

    result = validator.validate_milestone(valid_milestone.milestone_id)

    assert result.integration_valid == True


# ============================================================================
# Dependencies Validation Tests
# ============================================================================

def test_validate_dependencies_no_cycles(validator, valid_milestone, valid_tasks, mock_db):
    """Test dependency validation detects no cycles"""
    mock_db.query().filter().first.return_value = valid_milestone
    mock_db.query().filter().all.return_value = valid_tasks

    result = validator.validate_milestone(valid_milestone.milestone_id)

    assert result.dependencies_valid == True


# ============================================================================
# Overall Validation Tests
# ============================================================================

def test_validate_milestone_not_found(validator, mock_db):
    """Test validation when milestone doesn't exist"""
    mock_db.query().filter().first.return_value = None

    result = validator.validate_milestone(uuid.uuid4())

    assert result.is_valid == False
    assert "not found" in result.errors[0].lower()


def test_validate_milestone_score_calculation(validator, valid_milestone, valid_tasks, mock_db):
    """Test validation score calculation"""
    mock_db.query().filter().first.return_value = valid_milestone
    mock_db.query().filter().all.return_value = valid_tasks

    result = validator.validate_milestone(valid_milestone.milestone_id)

    # Score should be based on 5 checks (20% each)
    assert 0.0 <= result.validation_score <= 1.0
    assert result.validation_score >= 0.7


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
