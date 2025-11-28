"""
Unit Tests - RetryOrchestrator

Tests smart retry logic with temperature adjustment and error analysis.

Author: DevMatrix Team
Date: 2025-10-24
"""

import pytest
import uuid
from unittest.mock import Mock, AsyncMock

from src.execution.retry_orchestrator import (
    RetryOrchestrator, ErrorCategory, RetryAttempt, RetryHistory
)
from src.models import AtomicUnit


@pytest.fixture
def mock_db():
    """Create mock database session"""
    db = Mock()
    db.commit.return_value = None
    return db


@pytest.fixture
def sample_atom():
    """Create sample atom for testing"""
    return AtomicUnit(
        atom_id=uuid.uuid4(),
        masterplan_id=uuid.uuid4(),
        task_id=uuid.uuid4(),
        atom_number=1,
        description="Calculate user statistics",
        code_to_generate="def calculate_stats(): pass",
        file_path="src/stats.py",
        language="python",
        complexity=2.0,
        status="failed",
        dependencies=[],
        context_completeness=0.90
    )


@pytest.fixture
def retry_orchestrator(mock_db):
    """Create RetryOrchestrator instance"""
    return RetryOrchestrator(db=mock_db, max_attempts=3, enable_backoff=False)


# ============================================================================
# Error Analysis Tests
# ============================================================================

def test_analyze_error_syntax(retry_orchestrator):
    """Test syntax error detection"""
    errors = [
        "SyntaxError: invalid syntax",
        "Parsing error on line 5",
        "Unexpected token '}'",
    ]

    for error in errors:
        category = retry_orchestrator.analyze_error(error)
        assert category == ErrorCategory.SYNTAX_ERROR


def test_analyze_error_type(retry_orchestrator):
    """Test type error detection"""
    errors = [
        "TypeError: unsupported operand type(s)",
        "Type mismatch: expected int, got str",
        "Cannot convert string to int",
    ]

    for error in errors:
        category = retry_orchestrator.analyze_error(error)
        assert category == ErrorCategory.TYPE_ERROR


def test_analyze_error_logic(retry_orchestrator):
    """Test logic error detection"""
    errors = [
        "Assertion failed: expected 5, got 3",
        "Validation failed for user input",
        "Test failed: incorrect result",
    ]

    for error in errors:
        category = retry_orchestrator.analyze_error(error)
        assert category == ErrorCategory.LOGIC_ERROR


def test_analyze_error_timeout(retry_orchestrator):
    """Test timeout error detection"""
    errors = [
        "Execution timeout (300s)",
        "Operation timed out",
        "Deadline exceeded",
    ]

    for error in errors:
        category = retry_orchestrator.analyze_error(error)
        assert category == ErrorCategory.TIMEOUT


def test_analyze_error_dependency(retry_orchestrator):
    """Test dependency error detection"""
    errors = [
        "Dependencies not satisfied",
        "Module 'numpy' not found",
        "Cannot find required import",
    ]

    for error in errors:
        category = retry_orchestrator.analyze_error(error)
        assert category == ErrorCategory.DEPENDENCY_ERROR


def test_analyze_error_context(retry_orchestrator):
    """Test context insufficient error detection"""
    errors = [
        "Insufficient context information",
        "Needs more context to proceed",
        "Information missing for code generation",
    ]

    for error in errors:
        category = retry_orchestrator.analyze_error(error)
        assert category == ErrorCategory.CONTEXT_INSUFFICIENT


def test_analyze_error_unknown(retry_orchestrator):
    """Test unknown error classification"""
    error = "Some random error message"
    category = retry_orchestrator.analyze_error(error)
    assert category == ErrorCategory.UNKNOWN


# ============================================================================
# Temperature Adjustment Tests
# ============================================================================

def test_adjust_temperature_schedule(retry_orchestrator):
    """Test temperature adjustment follows schedule"""
    assert retry_orchestrator.adjust_temperature(1) == 0.7
    assert retry_orchestrator.adjust_temperature(2) == 0.5
    assert retry_orchestrator.adjust_temperature(3) == 0.3


def test_adjust_temperature_beyond_schedule(retry_orchestrator):
    """Test temperature for attempts beyond schedule"""
    # Should default to 0.3 (most conservative)
    assert retry_orchestrator.adjust_temperature(4) == 0.3
    assert retry_orchestrator.adjust_temperature(10) == 0.3


# ============================================================================
# Backoff Strategy Tests
# ============================================================================

def test_apply_backoff_disabled(mock_db):
    """Test backoff returns 0 when disabled"""
    orchestrator = RetryOrchestrator(db=mock_db, enable_backoff=False)

    assert orchestrator.apply_backoff(1) == 0.0
    assert orchestrator.apply_backoff(2) == 0.0
    assert orchestrator.apply_backoff(3) == 0.0


def test_apply_backoff_schedule(mock_db):
    """Test backoff follows exponential schedule"""
    orchestrator = RetryOrchestrator(db=mock_db, enable_backoff=True)

    assert orchestrator.apply_backoff(1) == 1.0
    assert orchestrator.apply_backoff(2) == 2.0
    assert orchestrator.apply_backoff(3) == 4.0


def test_apply_backoff_beyond_schedule(mock_db):
    """Test backoff for attempts beyond schedule"""
    orchestrator = RetryOrchestrator(db=mock_db, enable_backoff=True)

    # Should default to 4.0 (max backoff)
    assert orchestrator.apply_backoff(4) == 4.0
    assert orchestrator.apply_backoff(10) == 4.0


# ============================================================================
# Feedback Prompt Generation Tests
# ============================================================================

def test_generate_retry_prompt_syntax_error(retry_orchestrator, sample_atom):
    """Test feedback prompt for syntax errors"""
    error = "SyntaxError: invalid syntax on line 5"
    category = ErrorCategory.SYNTAX_ERROR

    prompt = retry_orchestrator.generate_retry_prompt(sample_atom, error, category)

    assert "syntax_error" in prompt
    assert error in prompt
    assert sample_atom.description in prompt
    assert "syntax for python" in prompt.lower()
    assert "indentation" in prompt.lower()


def test_generate_retry_prompt_type_error(retry_orchestrator, sample_atom):
    """Test feedback prompt for type errors"""
    error = "TypeError: expected int, got str"
    category = ErrorCategory.TYPE_ERROR

    prompt = retry_orchestrator.generate_retry_prompt(sample_atom, error, category)

    assert "type_error" in prompt
    assert "type consistency" in prompt.lower()
    assert "type annotations" in prompt.lower()


def test_generate_retry_prompt_timeout(retry_orchestrator, sample_atom):
    """Test feedback prompt for timeout errors"""
    error = "Execution timeout (300s)"
    category = ErrorCategory.TIMEOUT

    prompt = retry_orchestrator.generate_retry_prompt(sample_atom, error, category)

    assert "timeout" in prompt
    assert "efficiency" in prompt.lower()
    assert "complexity" in prompt.lower()
    assert "infinite loops" in prompt.lower()


def test_generate_retry_prompt_includes_context(retry_orchestrator, sample_atom):
    """Test that prompt includes atom context"""
    error = "Some error"
    category = ErrorCategory.UNKNOWN

    prompt = retry_orchestrator.generate_retry_prompt(sample_atom, error, category)

    assert sample_atom.description in prompt
    assert sample_atom.file_path in prompt
    assert sample_atom.language in prompt
    assert error in prompt


# ============================================================================
# Retry Execution Tests
# ============================================================================

@pytest.mark.asyncio
async def test_retry_atom_success(retry_orchestrator, sample_atom):
    """Test successful retry execution"""
    error = "SyntaxError: invalid syntax"

    async def mock_generator(atom, retry_count, temperature, feedback):
        return f"# Fixed code (attempt {retry_count}, temp {temperature})"

    success, code, feedback = await retry_orchestrator.retry_atom(
        atom=sample_atom,
        error=error,
        attempt=1,
        code_generator=mock_generator
    )

    assert success == True
    assert code is not None
    assert "Fixed code" in code
    assert "attempt 1" in code
    assert "temp 0.7" in code


@pytest.mark.asyncio
async def test_retry_atom_failure(retry_orchestrator, sample_atom):
    """Test failed retry execution"""
    error = "TypeError: something wrong"

    async def failing_generator(atom, retry_count, temperature, feedback):
        raise ValueError("Generation failed")

    success, code, feedback = await retry_orchestrator.retry_atom(
        atom=sample_atom,
        error=error,
        attempt=1,
        code_generator=failing_generator
    )

    assert success == False
    assert code is None
    assert feedback is not None


@pytest.mark.asyncio
async def test_retry_atom_max_attempts_exceeded(retry_orchestrator, sample_atom):
    """Test retry rejects when max attempts exceeded"""
    error = "Some error"

    success, code, feedback = await retry_orchestrator.retry_atom(
        atom=sample_atom,
        error=error,
        attempt=4,  # Exceeds max_attempts=3
        code_generator=None
    )

    assert success == False
    assert code is None
    assert "max retry attempts" in feedback.lower()


@pytest.mark.asyncio
async def test_retry_atom_temperature_progression(retry_orchestrator, sample_atom):
    """Test temperature decreases with retry attempts"""
    error = "Some error"
    temperatures = []

    async def tracking_generator(atom, retry_count, temperature, feedback):
        temperatures.append(temperature)
        return "code"

    for attempt in [1, 2, 3]:
        await retry_orchestrator.retry_atom(
            atom=sample_atom,
            error=error,
            attempt=attempt,
            code_generator=tracking_generator
        )

    assert temperatures == [0.7, 0.5, 0.3]  # Decreasing temperature


# ============================================================================
# Retry History Tracking Tests
# ============================================================================

@pytest.mark.asyncio
async def test_track_retry_history(retry_orchestrator, sample_atom):
    """Test retry history is tracked"""
    error = "Some error"

    async def mock_generator(atom, retry_count, temperature, feedback):
        if retry_count < 2:
            raise ValueError("Not yet")
        return "success"

    # First attempt fails
    await retry_orchestrator.retry_atom(sample_atom, error, 1, mock_generator)

    # Check history
    history = retry_orchestrator.track_retry_history(sample_atom.atom_id)
    assert history is not None
    assert history.total_attempts == 1
    assert len(history.attempts) == 1
    assert history.attempts[0].success == False

    # Second attempt succeeds
    await retry_orchestrator.retry_atom(sample_atom, error, 2, mock_generator)

    history = retry_orchestrator.track_retry_history(sample_atom.atom_id)
    assert history.total_attempts == 2
    assert len(history.attempts) == 2
    assert history.attempts[1].success == True
    assert history.final_success == True


@pytest.mark.asyncio
async def test_retry_history_multiple_atoms(retry_orchestrator):
    """Test tracking history for multiple atoms"""
    atom1 = AtomicUnit(
        atom_id=uuid.uuid4(),
        masterplan_id=uuid.uuid4(),
        task_id=uuid.uuid4(),
        atom_number=1,
        description="Test 1",
        code_to_generate="code1",
        file_path="file1.py",
        language="python",
        complexity=1.0,
        status="failed",
        dependencies=[],
        context_completeness=0.9
    )

    atom2 = AtomicUnit(
        atom_id=uuid.uuid4(),
        masterplan_id=uuid.uuid4(),
        task_id=uuid.uuid4(),
        atom_number=2,
        description="Test 2",
        code_to_generate="code2",
        file_path="file2.py",
        language="python",
        complexity=1.0,
        status="failed",
        dependencies=[],
        context_completeness=0.9
    )

    async def mock_generator(atom, retry_count, temperature, feedback):
        return "code"

    # Retry both atoms
    await retry_orchestrator.retry_atom(atom1, "error1", 1, mock_generator)
    await retry_orchestrator.retry_atom(atom2, "error2", 1, mock_generator)

    # Check both histories exist
    history1 = retry_orchestrator.track_retry_history(atom1.atom_id)
    history2 = retry_orchestrator.track_retry_history(atom2.atom_id)

    assert history1 is not None
    assert history2 is not None
    assert history1.atom_id == atom1.atom_id
    assert history2.atom_id == atom2.atom_id


# ============================================================================
# Statistics Tests
# ============================================================================

@pytest.mark.asyncio
async def test_get_retry_statistics_empty(retry_orchestrator):
    """Test statistics when no retries"""
    stats = retry_orchestrator.get_retry_statistics()

    assert stats['total_atoms_retried'] == 0
    assert stats['total_attempts'] == 0
    assert stats['success_rate'] == 0.0
    assert stats['avg_attempts_to_success'] == 0.0


@pytest.mark.asyncio
async def test_get_retry_statistics_with_retries(retry_orchestrator, sample_atom):
    """Test statistics calculation"""
    async def mock_generator(atom, retry_count, temperature, feedback):
        if retry_count == 1:
            raise ValueError("Fail first time")
        return "success"

    # Atom 1: Fails attempt 1, succeeds attempt 2
    await retry_orchestrator.retry_atom(sample_atom, "error", 1, mock_generator)
    await retry_orchestrator.retry_atom(sample_atom, "error", 2, mock_generator)

    # Create atom 2
    atom2 = AtomicUnit(
        atom_id=uuid.uuid4(),
        masterplan_id=uuid.uuid4(),
        task_id=uuid.uuid4(),
        atom_number=2,
        description="Test 2",
        code_to_generate="code",
        file_path="file.py",
        language="python",
        complexity=1.0,
        status="failed",
        dependencies=[],
        context_completeness=0.9
    )

    # Atom 2: Succeeds attempt 1
    await retry_orchestrator.retry_atom(atom2, "error", 1, mock_generator)

    stats = retry_orchestrator.get_retry_statistics()

    assert stats['total_atoms_retried'] == 2
    assert stats['total_attempts'] == 3  # 2 for atom1, 1 for atom2
    assert stats['successful_atoms'] == 2
    assert stats['success_rate'] == 100.0
    assert stats['avg_attempts_to_success'] == 1.5  # (2 + 1) / 2


@pytest.mark.asyncio
async def test_get_retry_statistics_error_categories(retry_orchestrator, sample_atom):
    """Test error category counting in statistics"""
    async def mock_generator(atom, retry_count, temperature, feedback):
        return "code"

    # Retry with different error types
    await retry_orchestrator.retry_atom(sample_atom, "SyntaxError: bad", 1, mock_generator)

    atom2 = AtomicUnit(
        atom_id=uuid.uuid4(),
        masterplan_id=uuid.uuid4(),
        task_id=uuid.uuid4(),
        atom_number=2,
        description="Test",
        code_to_generate="code",
        file_path="file.py",
        language="python",
        complexity=1.0,
        status="failed",
        dependencies=[],
        context_completeness=0.9
    )

    await retry_orchestrator.retry_atom(atom2, "TypeError: wrong type", 1, mock_generator)

    stats = retry_orchestrator.get_retry_statistics()

    assert 'syntax_error' in stats['error_categories']
    assert 'type_error' in stats['error_categories']
    assert stats['error_categories']['syntax_error'] == 1
    assert stats['error_categories']['type_error'] == 1


# ============================================================================
# State Management Tests
# ============================================================================

@pytest.mark.asyncio
async def test_reset_history(retry_orchestrator, sample_atom):
    """Test history reset clears all data"""
    async def mock_generator(atom, retry_count, temperature, feedback):
        return "code"

    # Create some history
    await retry_orchestrator.retry_atom(sample_atom, "error", 1, mock_generator)

    assert len(retry_orchestrator._retry_histories) > 0

    # Reset
    retry_orchestrator.reset_history()

    assert len(retry_orchestrator._retry_histories) == 0
    stats = retry_orchestrator.get_retry_statistics()
    assert stats['total_atoms_retried'] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
