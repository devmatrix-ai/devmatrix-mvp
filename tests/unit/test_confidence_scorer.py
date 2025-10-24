"""
Unit Tests - ConfidenceScorer

Tests confidence scoring calculation for atoms.

Author: DevMatrix Team
Date: 2025-10-24
"""

import pytest
import uuid
from datetime import datetime
from sqlalchemy.orm import Session

from src.review.confidence_scorer import ConfidenceScorer, ConfidenceScore
from src.models import AtomicUnit, ValidationResult, AtomRetryHistory


@pytest.fixture
def scorer(db_session: Session):
    """Create ConfidenceScorer instance"""
    return ConfidenceScorer(db_session)


@pytest.fixture
def sample_atom(db_session: Session):
    """Create sample atom for testing"""
    atom = AtomicUnit(
        atom_id=uuid.uuid4(),
        masterplan_id=uuid.uuid4(),
        task_id=uuid.uuid4(),
        atom_number=1,
        description="Sample atom",
        code_to_generate="def sample(): return 1",
        file_path="sample.py",
        language="python",
        complexity=2.0,
        status="completed",
        dependencies=[],
        context_completeness=0.95
    )
    db_session.add(atom)
    db_session.commit()
    return atom


# ============================================================================
# Overall Confidence Calculation Tests
# ============================================================================

def test_calculate_confidence_high_quality(scorer, sample_atom, db_session):
    """Test confidence calculation for high-quality atom"""
    # Add perfect validation result
    validation = ValidationResult(
        validation_id=uuid.uuid4(),
        atom_id=sample_atom.atom_id,
        validation_level="atomic",
        passed=True,
        validation_data={
            "syntax": {"passed": True},
            "semantics": {"passed": True},
            "atomicity": {"passed": True},
            "type_safety": {"passed": True},
            "runtime_safety": {"passed": True}
        },
        created_at=datetime.utcnow()
    )
    db_session.add(validation)
    db_session.commit()

    # No retries needed (first try success)
    # Low complexity (2.0 < 3.0)

    score = scorer.calculate_confidence(sample_atom.atom_id)

    assert score.overall_score >= 0.85  # High confidence
    assert score.confidence_level == "high"
    assert score.needs_review is False
    assert len(score.issues) == 0


def test_calculate_confidence_low_quality(scorer, sample_atom, db_session):
    """Test confidence calculation for low-quality atom"""
    # Add failing validation result
    validation = ValidationResult(
        validation_id=uuid.uuid4(),
        atom_id=sample_atom.atom_id,
        validation_level="atomic",
        passed=False,
        validation_data={
            "syntax": {"passed": False},
            "semantics": {"passed": False},
            "atomicity": {"passed": False},
            "type_safety": {"passed": False},
            "runtime_safety": {"passed": False}
        },
        created_at=datetime.utcnow()
    )
    db_session.add(validation)

    # Add multiple retries
    for i in range(5):
        retry = AtomRetryHistory(
            retry_id=uuid.uuid4(),
            atom_id=sample_atom.atom_id,
            attempt_number=i + 1,
            error_category="syntax",
            error_message="Syntax error",
            temperature_used=0.7 - (i * 0.1),
            retry_prompt="Fix syntax",
            outcome="failed",
            created_at=datetime.utcnow()
        )
        db_session.add(retry)

    # High complexity
    sample_atom.complexity = 12.0
    sample_atom.status = "failed"

    db_session.commit()

    score = scorer.calculate_confidence(sample_atom.atom_id)

    assert score.overall_score < 0.50  # Critical confidence
    assert score.confidence_level == "critical"
    assert score.needs_review is True
    assert len(score.issues) > 0


# ============================================================================
# Validation Score Tests
# ============================================================================

def test_score_validation_all_passed(scorer, sample_atom, db_session):
    """Test validation scoring when all checks pass"""
    validation = ValidationResult(
        validation_id=uuid.uuid4(),
        atom_id=sample_atom.atom_id,
        validation_level="atomic",
        passed=True,
        validation_data={
            "syntax": {"passed": True},
            "semantics": {"passed": True},
            "atomicity": {"passed": True},
            "type_safety": {"passed": True},
            "runtime_safety": {"passed": True}
        },
        created_at=datetime.utcnow()
    )
    db_session.add(validation)
    db_session.commit()

    score = scorer.score_validation_results(sample_atom)

    assert score == 1.0  # Perfect validation


def test_score_validation_all_failed(scorer, sample_atom, db_session):
    """Test validation scoring when all checks fail"""
    validation = ValidationResult(
        validation_id=uuid.uuid4(),
        atom_id=sample_atom.atom_id,
        validation_level="atomic",
        passed=False,
        validation_data={
            "syntax": {"passed": False},
            "semantics": {"passed": False},
            "atomicity": {"passed": False},
            "type_safety": {"passed": False},
            "runtime_safety": {"passed": False}
        },
        created_at=datetime.utcnow()
    )
    db_session.add(validation)
    db_session.commit()

    score = scorer.score_validation_results(sample_atom)

    assert score == 0.0  # Complete validation failure


def test_score_validation_no_validation(scorer, sample_atom):
    """Test validation scoring when no validation exists"""
    score = scorer.score_validation_results(sample_atom)

    assert score == 0.3  # Low score for missing validation


def test_score_validation_partial_pass(scorer, sample_atom, db_session):
    """Test validation scoring with partial pass"""
    validation = ValidationResult(
        validation_id=uuid.uuid4(),
        atom_id=sample_atom.atom_id,
        validation_level="atomic",
        passed=False,
        validation_data={
            "syntax": {"passed": True},  # Critical - passed
            "semantics": {"passed": True},  # Critical - passed
            "atomicity": {"passed": False},
            "type_safety": {"passed": False},
            "runtime_safety": {"passed": True}
        },
        created_at=datetime.utcnow()
    )
    db_session.add(validation)
    db_session.commit()

    score = scorer.score_validation_results(sample_atom)

    # 4 passed (syntax=2, semantics=2, runtime=1) / 7 total
    assert score == pytest.approx(5/7, rel=0.01)


# ============================================================================
# Attempts Score Tests
# ============================================================================

def test_score_attempts_first_try(scorer, sample_atom):
    """Test attempts scoring for first-try success"""
    score = scorer.score_attempts(sample_atom)

    assert score == 1.0  # Perfect - no retries


def test_score_attempts_one_retry(scorer, sample_atom, db_session):
    """Test attempts scoring with one retry"""
    retry = AtomRetryHistory(
        retry_id=uuid.uuid4(),
        atom_id=sample_atom.atom_id,
        attempt_number=1,
        error_category="syntax",
        error_message="Error",
        temperature_used=0.7,
        retry_prompt="Fix",
        outcome="success",
        created_at=datetime.utcnow()
    )
    db_session.add(retry)
    db_session.commit()

    score = scorer.score_attempts(sample_atom)

    assert score == 0.8  # 1 - (1/5)


def test_score_attempts_max_retries(scorer, sample_atom, db_session):
    """Test attempts scoring at max retries"""
    for i in range(5):
        retry = AtomRetryHistory(
            retry_id=uuid.uuid4(),
            atom_id=sample_atom.atom_id,
            attempt_number=i + 1,
            error_category="syntax",
            error_message="Error",
            temperature_used=0.7,
            retry_prompt="Fix",
            outcome="failed",
            created_at=datetime.utcnow()
        )
        db_session.add(retry)
    db_session.commit()

    score = scorer.score_attempts(sample_atom)

    assert score == 0.0  # Max retries = 0 score


def test_score_attempts_beyond_max(scorer, sample_atom, db_session):
    """Test attempts scoring beyond max retries"""
    for i in range(10):  # Way beyond max
        retry = AtomRetryHistory(
            retry_id=uuid.uuid4(),
            atom_id=sample_atom.atom_id,
            attempt_number=i + 1,
            error_category="syntax",
            error_message="Error",
            temperature_used=0.7,
            retry_prompt="Fix",
            outcome="failed",
            created_at=datetime.utcnow()
        )
        db_session.add(retry)
    db_session.commit()

    score = scorer.score_attempts(sample_atom)

    assert score == 0.0  # Still 0


# ============================================================================
# Complexity Score Tests
# ============================================================================

def test_score_complexity_below_target(scorer):
    """Test complexity scoring below target (<3.0)"""
    score = scorer.score_complexity(2.0)

    assert score == 1.0  # Perfect


def test_score_complexity_at_target(scorer):
    """Test complexity scoring at target (3.0)"""
    score = scorer.score_complexity(3.0)

    # Just at target, should be very high
    assert score >= 0.99


def test_score_complexity_above_max(scorer):
    """Test complexity scoring above max (>10.0)"""
    score = scorer.score_complexity(15.0)

    assert score == 0.0  # Beyond max


def test_score_complexity_mid_range(scorer):
    """Test complexity scoring in mid-range"""
    score = scorer.score_complexity(6.5)

    # Linear decay from 3.0 to 10.0
    # 6.5 is exactly halfway
    assert score == 0.5


# ============================================================================
# Confidence Level Tests
# ============================================================================

def test_confidence_level_high(scorer, sample_atom, db_session):
    """Test high confidence level determination"""
    # Perfect validation
    validation = ValidationResult(
        validation_id=uuid.uuid4(),
        atom_id=sample_atom.atom_id,
        validation_level="atomic",
        passed=True,
        validation_data={
            "syntax": {"passed": True},
            "semantics": {"passed": True},
            "atomicity": {"passed": True},
            "type_safety": {"passed": True},
            "runtime_safety": {"passed": True}
        },
        created_at=datetime.utcnow()
    )
    db_session.add(validation)
    db_session.commit()

    score = scorer.calculate_confidence(sample_atom.atom_id)

    assert score.confidence_level == "high"
    assert score.overall_score >= 0.85


def test_confidence_level_medium(scorer, sample_atom, db_session):
    """Test medium confidence level determination"""
    # Partial validation
    validation = ValidationResult(
        validation_id=uuid.uuid4(),
        atom_id=sample_atom.atom_id,
        validation_level="atomic",
        passed=True,
        validation_data={
            "syntax": {"passed": True},
            "semantics": {"passed": True},
            "atomicity": {"passed": False},
            "type_safety": {"passed": True},
            "runtime_safety": {"passed": False}
        },
        created_at=datetime.utcnow()
    )
    db_session.add(validation)

    # One retry
    retry = AtomRetryHistory(
        retry_id=uuid.uuid4(),
        atom_id=sample_atom.atom_id,
        attempt_number=1,
        error_category="syntax",
        error_message="Error",
        temperature_used=0.7,
        retry_prompt="Fix",
        outcome="success",
        created_at=datetime.utcnow()
    )
    db_session.add(retry)
    db_session.commit()

    score = scorer.calculate_confidence(sample_atom.atom_id)

    # Should be in medium range
    assert 0.70 <= score.overall_score < 0.85
    assert score.confidence_level == "medium"


def test_confidence_level_low(scorer, sample_atom, db_session):
    """Test low confidence level determination"""
    # Weak validation
    validation = ValidationResult(
        validation_id=uuid.uuid4(),
        atom_id=sample_atom.atom_id,
        validation_level="atomic",
        passed=False,
        validation_data={
            "syntax": {"passed": True},
            "semantics": {"passed": False},
            "atomicity": {"passed": False},
            "type_safety": {"passed": False},
            "runtime_safety": {"passed": False}
        },
        created_at=datetime.utcnow()
    )
    db_session.add(validation)

    # Multiple retries
    for i in range(3):
        retry = AtomRetryHistory(
            retry_id=uuid.uuid4(),
            atom_id=sample_atom.atom_id,
            attempt_number=i + 1,
            error_category="syntax",
            error_message="Error",
            temperature_used=0.7,
            retry_prompt="Fix",
            outcome="failed",
            created_at=datetime.utcnow()
        )
        db_session.add(retry)
    db_session.commit()

    score = scorer.calculate_confidence(sample_atom.atom_id)

    # Should be in low range
    assert 0.50 <= score.overall_score < 0.70
    assert score.confidence_level == "low"
    assert score.needs_review is True


def test_confidence_level_critical(scorer, sample_atom, db_session):
    """Test critical confidence level determination"""
    # Failed validation
    validation = ValidationResult(
        validation_id=uuid.uuid4(),
        atom_id=sample_atom.atom_id,
        validation_level="atomic",
        passed=False,
        validation_data={
            "syntax": {"passed": False},
            "semantics": {"passed": False},
            "atomicity": {"passed": False},
            "type_safety": {"passed": False},
            "runtime_safety": {"passed": False}
        },
        created_at=datetime.utcnow()
    )
    db_session.add(validation)
    db_session.commit()

    score = scorer.calculate_confidence(sample_atom.atom_id)

    assert score.overall_score < 0.50
    assert score.confidence_level == "critical"
    assert score.needs_review is True


# ============================================================================
# Batch Operations Tests
# ============================================================================

def test_batch_calculate_confidence(scorer, db_session):
    """Test batch confidence calculation"""
    # Create 3 atoms
    atoms = []
    for i in range(3):
        atom = AtomicUnit(
            atom_id=uuid.uuid4(),
            masterplan_id=uuid.uuid4(),
            task_id=uuid.uuid4(),
            atom_number=i + 1,
            description=f"Atom {i+1}",
            code_to_generate=f"def func_{i}(): pass",
            file_path=f"file_{i}.py",
            language="python",
            complexity=2.0,
            status="completed",
            dependencies=[],
            context_completeness=0.95
        )
        db_session.add(atom)
        atoms.append(atom)
    db_session.commit()

    atom_ids = [atom.atom_id for atom in atoms]
    scores = scorer.batch_calculate_confidence(atom_ids)

    assert len(scores) == 3
    for atom_id in atom_ids:
        assert atom_id in scores
        assert isinstance(scores[atom_id], ConfidenceScore)


def test_get_low_confidence_atoms(scorer, db_session):
    """Test getting low confidence atoms for masterplan"""
    masterplan_id = uuid.uuid4()

    # Create 5 atoms with varying quality
    for i in range(5):
        atom = AtomicUnit(
            atom_id=uuid.uuid4(),
            masterplan_id=masterplan_id,
            task_id=uuid.uuid4(),
            atom_number=i + 1,
            description=f"Atom {i+1}",
            code_to_generate=f"def func_{i}(): pass",
            file_path=f"file_{i}.py",
            language="python",
            complexity=2.0 + (i * 2),  # Increasing complexity
            status="completed",
            dependencies=[],
            context_completeness=0.95
        )
        db_session.add(atom)

        # Add retries for some atoms
        for j in range(i):  # 0, 1, 2, 3, 4 retries
            retry = AtomRetryHistory(
                retry_id=uuid.uuid4(),
                atom_id=atom.atom_id,
                attempt_number=j + 1,
                error_category="syntax",
                error_message="Error",
                temperature_used=0.7,
                retry_prompt="Fix",
                outcome="failed",
                created_at=datetime.utcnow()
            )
            db_session.add(retry)

    db_session.commit()

    # Get low confidence atoms
    low_confidence = scorer.get_low_confidence_atoms(masterplan_id, threshold=0.70)

    # Should have some low confidence atoms
    assert len(low_confidence) > 0

    # Should be sorted by score (lowest first)
    for i in range(len(low_confidence) - 1):
        assert low_confidence[i].overall_score <= low_confidence[i+1].overall_score


# ============================================================================
# Issue Identification Tests
# ============================================================================

def test_identify_issues_validation_failure(scorer, sample_atom):
    """Test issue identification for validation failures"""
    issues = scorer._identify_issues(
        sample_atom,
        validation_score=0.3,  # Low
        attempts_score=1.0,
        complexity_score=1.0,
        integration_score=0.5
    )

    assert any("Validation" in issue for issue in issues)


def test_identify_issues_high_retries(scorer, sample_atom):
    """Test issue identification for high retry count"""
    issues = scorer._identify_issues(
        sample_atom,
        validation_score=1.0,
        attempts_score=0.3,  # Low
        complexity_score=1.0,
        integration_score=0.5
    )

    assert any("retry" in issue.lower() for issue in issues)


def test_identify_issues_high_complexity(scorer, sample_atom):
    """Test issue identification for high complexity"""
    sample_atom.complexity = 8.0

    issues = scorer._identify_issues(
        sample_atom,
        validation_score=1.0,
        attempts_score=1.0,
        complexity_score=0.2,  # Low
        integration_score=0.5
    )

    assert any("complexity" in issue.lower() for issue in issues)


def test_identify_issues_failed_status(scorer, sample_atom):
    """Test issue identification for failed atom"""
    sample_atom.status = "failed"

    issues = scorer._identify_issues(
        sample_atom,
        validation_score=1.0,
        attempts_score=1.0,
        complexity_score=1.0,
        integration_score=0.5
    )

    assert any("failed" in issue.lower() for issue in issues)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
