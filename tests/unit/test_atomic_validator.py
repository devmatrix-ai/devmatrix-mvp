"""
Unit Tests - AtomicValidator (Level 1)

Tests individual atom validation including syntax, semantics, atomicity,
type safety, and runtime safety checks.

Author: DevMatrix Team
Date: 2025-10-23
"""

import pytest
import uuid
from datetime import datetime
from unittest.mock import Mock, MagicMock

from src.validation.atomic_validator import AtomicValidator, AtomicValidationResult
from src.models import AtomicUnit


@pytest.fixture
def mock_db():
    """Create mock database session"""
    return Mock()


@pytest.fixture
def validator(mock_db):
    """Create AtomicValidator instance"""
    return AtomicValidator(mock_db)


@pytest.fixture
def valid_atom():
    """Create a valid atom for testing"""
    return AtomicUnit(
        atom_id=uuid.uuid4(),
        masterplan_id=uuid.uuid4(),
        task_id=uuid.uuid4(),
        atom_number=1,
        description="Valid Python function",
        code_to_generate="""
def add_numbers(a: int, b: int) -> int:
    \"\"\"Add two numbers\"\"\"
    return a + b
""",
        file_path="src/math.py",
        language="python",
        complexity=1.0,
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


# ============================================================================
# Syntax Validation Tests
# ============================================================================

def test_validate_syntax_valid_python(validator, valid_atom, mock_db):
    """Test syntax validation with valid Python code"""
    mock_db.query().filter().first.return_value = valid_atom

    result = validator.validate_atom(valid_atom.atom_id)

    assert result.syntax_valid == True
    assert len([e for e in result.errors if 'syntax' in e.lower()]) == 0


def test_validate_syntax_invalid_python(validator, mock_db):
    """Test syntax validation with invalid Python code"""
    invalid_atom = AtomicUnit(
        atom_id=uuid.uuid4(),
        masterplan_id=uuid.uuid4(),
        task_id=uuid.uuid4(),
        atom_number=1,
        description="Invalid syntax",
        code_to_generate="def invalid_function(\n    # Missing closing paren",
        file_path="src/invalid.py",
        language="python",
        complexity=1.0,
        status="pending",
        dependencies=[],
        context_completeness=0.5
    )
    mock_db.query().filter().first.return_value = invalid_atom

    result = validator.validate_atom(invalid_atom.atom_id)

    assert result.syntax_valid == False
    assert len(result.errors) > 0


def test_validate_syntax_typescript(validator, mock_db):
    """Test syntax validation with TypeScript code"""
    ts_atom = AtomicUnit(
        atom_id=uuid.uuid4(),
        masterplan_id=uuid.uuid4(),
        task_id=uuid.uuid4(),
        atom_number=1,
        description="TypeScript function",
        code_to_generate="""
function addNumbers(a: number, b: number): number {
    return a + b;
}
""",
        file_path="src/math.ts",
        language="typescript",
        complexity=1.0,
        status="pending",
        dependencies=[],
        context_completeness=0.95
    )
    mock_db.query().filter().first.return_value = ts_atom

    result = validator.validate_atom(ts_atom.atom_id)

    assert result.syntax_valid == True


# ============================================================================
# Semantics Validation Tests
# ============================================================================

def test_validate_semantics_undefined_variable(validator, mock_db):
    """Test semantic validation detects undefined variables"""
    semantic_atom = AtomicUnit(
        atom_id=uuid.uuid4(),
        masterplan_id=uuid.uuid4(),
        task_id=uuid.uuid4(),
        atom_number=1,
        description="Undefined variable",
        code_to_generate="""
def function():
    x = 10
    return y  # y is undefined
""",
        file_path="src/test.py",
        language="python",
        complexity=1.0,
        status="pending",
        dependencies=[],
        context_completeness=0.7
    )
    mock_db.query().filter().first.return_value = semantic_atom

    result = validator.validate_atom(semantic_atom.atom_id)

    assert result.semantic_valid == False
    assert len(result.warnings) > 0


def test_validate_semantics_valid_code(validator, valid_atom, mock_db):
    """Test semantic validation with valid code"""
    mock_db.query().filter().first.return_value = valid_atom

    result = validator.validate_atom(valid_atom.atom_id)

    assert result.semantic_valid == True


# ============================================================================
# Atomicity Validation Tests
# ============================================================================

def test_validate_atomicity_too_long(validator, mock_db):
    """Test atomicity validation detects code that's too long"""
    long_code = "\n".join([f"x{i} = {i}" for i in range(30)])  # 30 lines
    long_atom = AtomicUnit(
        atom_id=uuid.uuid4(),
        masterplan_id=uuid.uuid4(),
        task_id=uuid.uuid4(),
        atom_number=1,
        description="Too long",
        code_to_generate=long_code,
        file_path="src/long.py",
        language="python",
        complexity=1.0,
        status="pending",
        dependencies=[],
        context_completeness=0.9
    )
    mock_db.query().filter().first.return_value = long_atom

    result = validator.validate_atom(long_atom.atom_id)

    assert result.atomicity_valid == False


def test_validate_atomicity_high_complexity(validator, mock_db):
    """Test atomicity validation detects high complexity"""
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
    complex_atom = AtomicUnit(
        atom_id=uuid.uuid4(),
        masterplan_id=uuid.uuid4(),
        task_id=uuid.uuid4(),
        atom_number=1,
        description="High complexity",
        code_to_generate=complex_code,
        file_path="src/complex.py",
        language="python",
        complexity=6.0,
        status="pending",
        dependencies=[],
        context_completeness=0.9
    )
    mock_db.query().filter().first.return_value = complex_atom

    result = validator.validate_atom(complex_atom.atom_id)

    assert result.atomicity_valid == False


def test_validate_atomicity_low_context(validator, mock_db):
    """Test atomicity validation detects low context completeness"""
    low_context_atom = AtomicUnit(
        atom_id=uuid.uuid4(),
        masterplan_id=uuid.uuid4(),
        task_id=uuid.uuid4(),
        atom_number=1,
        description="Low context",
        code_to_generate="def func(): return 1",
        file_path="src/test.py",
        language="python",
        complexity=1.0,
        status="pending",
        dependencies=[],
        context_completeness=0.5  # Below 0.95 threshold
    )
    mock_db.query().filter().first.return_value = low_context_atom

    result = validator.validate_atom(low_context_atom.atom_id)

    assert result.atomicity_valid == False


# ============================================================================
# Type Safety Tests
# ============================================================================

def test_validate_type_safety_with_hints(validator, valid_atom, mock_db):
    """Test type safety validation with type hints"""
    mock_db.query().filter().first.return_value = valid_atom

    result = validator.validate_atom(valid_atom.atom_id)

    assert result.type_safe == True


def test_validate_type_safety_without_hints(validator, mock_db):
    """Test type safety validation without type hints"""
    no_hints_atom = AtomicUnit(
        atom_id=uuid.uuid4(),
        masterplan_id=uuid.uuid4(),
        task_id=uuid.uuid4(),
        atom_number=1,
        description="No type hints",
        code_to_generate="def add(a, b):\n    return a + b",
        file_path="src/math.py",
        language="python",
        complexity=1.0,
        status="pending",
        dependencies=[],
        context_completeness=0.9
    )
    mock_db.query().filter().first.return_value = no_hints_atom

    result = validator.validate_atom(no_hints_atom.atom_id)

    # Missing type hints should trigger warning
    assert len(result.warnings) > 0


# ============================================================================
# Runtime Safety Tests
# ============================================================================

def test_validate_runtime_safety_dangerous_eval(validator, mock_db):
    """Test runtime safety detects eval()"""
    dangerous_atom = AtomicUnit(
        atom_id=uuid.uuid4(),
        masterplan_id=uuid.uuid4(),
        task_id=uuid.uuid4(),
        atom_number=1,
        description="Dangerous eval",
        code_to_generate='def dangerous(): eval("print(1)")',
        file_path="src/dangerous.py",
        language="python",
        complexity=1.0,
        status="pending",
        dependencies=[],
        context_completeness=0.9
    )
    mock_db.query().filter().first.return_value = dangerous_atom

    result = validator.validate_atom(dangerous_atom.atom_id)

    assert result.runtime_safe == False
    assert len(result.warnings) > 0


def test_validate_runtime_safety_dangerous_exec(validator, mock_db):
    """Test runtime safety detects exec()"""
    dangerous_atom = AtomicUnit(
        atom_id=uuid.uuid4(),
        masterplan_id=uuid.uuid4(),
        task_id=uuid.uuid4(),
        atom_number=1,
        description="Dangerous exec",
        code_to_generate='def dangerous(): exec("x = 1")',
        file_path="src/dangerous.py",
        language="python",
        complexity=1.0,
        status="pending",
        dependencies=[],
        context_completeness=0.9
    )
    mock_db.query().filter().first.return_value = dangerous_atom

    result = validator.validate_atom(dangerous_atom.atom_id)

    assert result.runtime_safe == False


def test_validate_runtime_safety_safe_code(validator, valid_atom, mock_db):
    """Test runtime safety with safe code"""
    mock_db.query().filter().first.return_value = valid_atom

    result = validator.validate_atom(valid_atom.atom_id)

    assert result.runtime_safe == True


# ============================================================================
# Overall Validation Tests
# ============================================================================

def test_validate_atom_not_found(validator, mock_db):
    """Test validation when atom doesn't exist"""
    mock_db.query().filter().first.return_value = None

    result = validator.validate_atom(uuid.uuid4())

    assert result.is_valid == False
    assert "not found" in result.errors[0].lower()


def test_validate_atom_score_calculation(validator, valid_atom, mock_db):
    """Test validation score calculation"""
    mock_db.query().filter().first.return_value = valid_atom

    result = validator.validate_atom(valid_atom.atom_id)

    # Score should be based on 5 checks (20% each)
    assert 0.0 <= result.validation_score <= 1.0
    assert result.validation_score >= 0.8  # Should pass most checks


def test_validate_atom_multiple_issues(validator, mock_db):
    """Test validation with multiple issues"""
    problematic_atom = AtomicUnit(
        atom_id=uuid.uuid4(),
        masterplan_id=uuid.uuid4(),
        task_id=uuid.uuid4(),
        atom_number=1,
        description="Multiple issues",
        code_to_generate='def bad(): eval("x")\n' + '\n'.join(['x = 1'] * 20),
        file_path="src/bad.py",
        language="python",
        complexity=1.0,
        status="pending",
        dependencies=[],
        context_completeness=0.5
    )
    mock_db.query().filter().first.return_value = problematic_atom

    result = validator.validate_atom(problematic_atom.atom_id)

    # Should have multiple issues
    assert len(result.issues) > 1
    assert result.validation_score < 0.7


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
