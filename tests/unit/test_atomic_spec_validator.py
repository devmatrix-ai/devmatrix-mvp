"""
Unit Tests for AtomicSpecValidator

Tests all validation criteria:
1. Single responsibility
2. LOC range (5-15)
3. Complexity limit (≤3.0)
4. Test cases (≥1)
5. Type safety
6. Context completeness
7. Purity constraints
8. Testability
9. Dependency graph validation

Author: DevMatrix Team
Date: 2025-11-12
"""

import pytest
from uuid import uuid4

from src.models.atomic_spec import AtomicSpec
from src.services.atomic_spec_validator import AtomicSpecValidator


class TestAtomicSpecValidator:
    """Test suite for AtomicSpecValidator"""

    @pytest.fixture
    def validator(self):
        """Create validator instance"""
        return AtomicSpecValidator(
            max_loc=15,
            max_complexity=3.0,
            min_test_cases=1
        )

    @pytest.fixture
    def valid_spec(self):
        """Create a valid atomic spec"""
        return AtomicSpec(
            task_id=uuid4(),
            sequence_number=1,
            description="Validate user email format using regex",
            input_types={"email": "str"},
            output_type="bool",
            target_loc=10,
            complexity_limit=2.0,
            imports_required=["import re"],
            dependencies=[],
            preconditions=["email is not None"],
            postconditions=["returns True if valid, False otherwise"],
            test_cases=[
                {"input": {"email": "test@example.com"}, "output": True},
                {"input": {"email": "invalid"}, "output": False}
            ],
            must_be_pure=True,
            must_be_idempotent=True,
            language="python"
        )

    # ==================== Single Responsibility Tests ====================

    def test_single_responsibility_valid(self, validator, valid_spec):
        """Test spec with single clear responsibility passes"""
        result = validator.validate(valid_spec)
        assert result.is_valid
        assert len(result.errors) == 0

    def test_single_responsibility_invalid_multiple_verbs(self, validator, valid_spec):
        """Test spec with multiple action verbs fails"""
        valid_spec.description = "Create user and send email notification"
        result = validator.validate(valid_spec)

        assert not result.is_valid
        assert any("multiple responsibilities" in err for err in result.errors)

    def test_single_responsibility_invalid_multiple_and(self, validator, valid_spec):
        """Test spec with multiple 'and' conjunctions fails"""
        valid_spec.description = "Validate email and validate password and check username"
        result = validator.validate(valid_spec)

        assert not result.is_valid
        assert any("multiple responsibilities" in err for err in result.errors)

    # ==================== LOC Range Tests ====================

    def test_loc_valid_target(self, validator, valid_spec):
        """Test spec with target 10 LOC passes"""
        valid_spec.target_loc = 10
        result = validator.validate(valid_spec)
        assert result.is_valid

    def test_loc_valid_minimum(self, validator, valid_spec):
        """Test spec with minimum 5 LOC passes"""
        valid_spec.target_loc = 5
        result = validator.validate(valid_spec)
        assert result.is_valid

    def test_loc_valid_maximum(self, validator, valid_spec):
        """Test spec with maximum 15 LOC passes"""
        valid_spec.target_loc = 15
        result = validator.validate(valid_spec)
        assert result.is_valid

    def test_loc_invalid_exceeds_max(self, validator, valid_spec):
        """Test spec exceeding max LOC fails"""
        valid_spec.target_loc = 20
        result = validator.validate(valid_spec)

        assert not result.is_valid
        assert any("exceeds maximum" in err for err in result.errors)

    def test_loc_warning_too_small(self, validator, valid_spec):
        """Test spec with very small LOC gets warning"""
        valid_spec.target_loc = 3
        result = validator.validate(valid_spec)

        # Should still be valid but with warning
        assert len(result.warnings) > 0
        assert any("very small" in warn for warn in result.warnings)

    # ==================== Complexity Tests ====================

    def test_complexity_valid(self, validator, valid_spec):
        """Test spec with valid complexity passes"""
        valid_spec.complexity_limit = 2.0
        result = validator.validate(valid_spec)
        assert result.is_valid

    def test_complexity_valid_at_limit(self, validator, valid_spec):
        """Test spec at complexity limit passes"""
        valid_spec.complexity_limit = 3.0
        result = validator.validate(valid_spec)
        assert result.is_valid

    def test_complexity_invalid_exceeds_limit(self, validator, valid_spec):
        """Test spec exceeding complexity limit fails"""
        valid_spec.complexity_limit = 5.0
        result = validator.validate(valid_spec)

        assert not result.is_valid
        assert any("Complexity limit" in err and "exceeds" in err for err in result.errors)

    # ==================== Test Cases Tests ====================

    def test_test_cases_valid_one(self, validator, valid_spec):
        """Test spec with 1 test case passes"""
        valid_spec.test_cases = [
            {"input": {"email": "test@example.com"}, "output": True}
        ]
        result = validator.validate(valid_spec)
        assert result.is_valid

    def test_test_cases_valid_multiple(self, validator, valid_spec):
        """Test spec with multiple test cases passes"""
        valid_spec.test_cases = [
            {"input": {"email": "test@example.com"}, "output": True},
            {"input": {"email": "invalid"}, "output": False},
            {"input": {"email": ""}, "output": False}
        ]
        result = validator.validate(valid_spec)
        assert result.is_valid

    def test_test_cases_invalid_none(self, validator, valid_spec):
        """Test spec with no test cases fails"""
        valid_spec.test_cases = []
        result = validator.validate(valid_spec)

        assert not result.is_valid
        assert any("test case" in err.lower() for err in result.errors)

    # ==================== Type Safety Tests ====================

    def test_type_safety_valid_full(self, validator, valid_spec):
        """Test spec with full type annotations passes"""
        result = validator.validate(valid_spec)
        assert result.is_valid

    def test_type_safety_warning_no_output_type(self, validator, valid_spec):
        """Test spec without output type gets warning"""
        # Can't set output_type to empty due to Pydantic validation
        # This test demonstrates the model validation itself
        with pytest.raises(ValueError):
            valid_spec.output_type = ""

    def test_type_safety_warning_no_input_types(self, validator, valid_spec):
        """Test spec without input types gets warning"""
        valid_spec.input_types = {}
        result = validator.validate(valid_spec)

        # Should have warning for non-trivial spec without input types
        assert len(result.warnings) > 0
        assert any("input types" in warn.lower() for warn in result.warnings)

    # ==================== Context Completeness Tests ====================

    def test_context_completeness_valid_with_imports(self, validator, valid_spec):
        """Test spec with imports for non-trivial code passes"""
        valid_spec.target_loc = 10
        valid_spec.imports_required = ["import re", "from typing import Optional"]
        result = validator.validate(valid_spec)
        assert result.is_valid

    def test_context_completeness_warning_no_imports(self, validator, valid_spec):
        """Test non-trivial spec without imports gets warning"""
        valid_spec.target_loc = 10
        valid_spec.imports_required = []
        result = validator.validate(valid_spec)

        assert len(result.warnings) > 0
        assert any("imports" in warn.lower() for warn in result.warnings)

    def test_context_completeness_no_warning_trivial(self, validator, valid_spec):
        """Test trivial spec without imports doesn't get warning"""
        valid_spec.target_loc = 5
        valid_spec.imports_required = []
        result = validator.validate(valid_spec)

        # Should not have import warning for trivial spec
        import_warnings = [w for w in result.warnings if "import" in w.lower()]
        assert len(import_warnings) == 0

    # ==================== Purity Tests ====================

    def test_purity_valid_pure_function(self, validator, valid_spec):
        """Test pure function marked as must_be_pure passes"""
        valid_spec.must_be_pure = True
        valid_spec.description = "Calculate sum of two numbers"
        result = validator.validate(valid_spec)
        assert result.is_valid

    def test_purity_invalid_has_side_effects(self, validator, valid_spec):
        """Test impure function marked as must_be_pure fails"""
        valid_spec.must_be_pure = True
        valid_spec.description = "Save user data to database"
        result = validator.validate(valid_spec)

        assert not result.is_valid
        assert any("must_be_pure" in err and "side effect" in err for err in result.errors)

    def test_purity_side_effect_keywords_detected(self, validator, valid_spec):
        """Test detection of various side effect keywords"""
        side_effect_descriptions = [
            "Save user to database",
            "Update user record",
            "Delete file from storage",
            "Send email notification",
            "Publish event to queue",
            "Write log entry"
        ]

        for desc in side_effect_descriptions:
            valid_spec.must_be_pure = True
            valid_spec.description = desc
            result = validator.validate(valid_spec)

            assert not result.is_valid, f"Expected failure for: {desc}"
            assert any("side effect" in err for err in result.errors)

    # ==================== Testability Tests ====================

    def test_testability_valid_clear_io(self, validator, valid_spec):
        """Test spec with clear I/O is testable"""
        result = validator.validate(valid_spec)
        assert result.is_valid

    def test_testability_invalid_no_test_cases(self, validator, valid_spec):
        """Test spec without test cases fails testability"""
        valid_spec.test_cases = []
        result = validator.validate(valid_spec)

        assert not result.is_valid
        assert any("testable" in err.lower() or "test case" in err.lower() for err in result.errors)

    # ==================== Batch Validation Tests ====================

    def test_batch_validation_all_valid(self, validator, valid_spec):
        """Test batch validation with all valid specs"""
        specs = [valid_spec.model_copy() for _ in range(3)]
        for i, spec in enumerate(specs):
            spec.sequence_number = i + 1

        valid, invalid = validator.validate_batch(specs)

        assert len(valid) == 3
        assert len(invalid) == 0

    def test_batch_validation_mixed(self, validator, valid_spec):
        """Test batch validation with mixed valid/invalid specs"""
        spec1 = valid_spec.model_copy()
        spec1.sequence_number = 1

        spec2 = valid_spec.model_copy()
        spec2.sequence_number = 2
        spec2.target_loc = 20  # Invalid

        spec3 = valid_spec.model_copy()
        spec3.sequence_number = 3
        spec3.test_cases = []  # Invalid

        valid, invalid = validator.validate_batch([spec1, spec2, spec3])

        assert len(valid) == 1
        assert len(invalid) == 2

    def test_batch_validation_all_invalid(self, validator, valid_spec):
        """Test batch validation with all invalid specs"""
        specs = [valid_spec.model_copy() for _ in range(3)]
        for i, spec in enumerate(specs):
            spec.sequence_number = i + 1
            spec.target_loc = 50  # All invalid

        valid, invalid = validator.validate_batch(specs)

        assert len(valid) == 0
        assert len(invalid) == 3

    # ==================== Dependency Graph Tests ====================

    def test_dependency_graph_valid_no_deps(self, validator, valid_spec):
        """Test dependency graph with no dependencies"""
        specs = [valid_spec.model_copy() for _ in range(3)]
        for i, spec in enumerate(specs):
            spec.sequence_number = i + 1
            spec.spec_id = str(uuid4())

        is_valid, errors = validator.validate_dependency_graph(specs)

        assert is_valid
        assert len(errors) == 0

    def test_dependency_graph_valid_linear_deps(self, validator, valid_spec):
        """Test dependency graph with linear dependencies (1→2→3)"""
        spec1 = valid_spec.model_copy()
        spec1.spec_id = str(uuid4())
        spec1.sequence_number = 1
        spec1.dependencies = []

        spec2 = valid_spec.model_copy()
        spec2.spec_id = str(uuid4())
        spec2.sequence_number = 2
        spec2.dependencies = [spec1.spec_id]

        spec3 = valid_spec.model_copy()
        spec3.spec_id = str(uuid4())
        spec3.sequence_number = 3
        spec3.dependencies = [spec2.spec_id]

        is_valid, errors = validator.validate_dependency_graph([spec1, spec2, spec3])

        assert is_valid
        assert len(errors) == 0

    def test_dependency_graph_invalid_circular(self, validator, valid_spec):
        """Test dependency graph with circular dependencies"""
        spec1 = valid_spec.model_copy()
        spec1.spec_id = str(uuid4())
        spec1.sequence_number = 1

        spec2 = valid_spec.model_copy()
        spec2.spec_id = str(uuid4())
        spec2.sequence_number = 2

        # Circular: 1→2→1
        spec1.dependencies = [spec2.spec_id]
        spec2.dependencies = [spec1.spec_id]

        is_valid, errors = validator.validate_dependency_graph([spec1, spec2])

        assert not is_valid
        assert len(errors) > 0
        assert any("circular" in err.lower() for err in errors)

    def test_dependency_graph_invalid_nonexistent_dep(self, validator, valid_spec):
        """Test dependency graph with reference to non-existent spec"""
        spec1 = valid_spec.model_copy()
        spec1.spec_id = str(uuid4())
        spec1.sequence_number = 1
        spec1.dependencies = [str(uuid4())]  # Non-existent spec

        is_valid, errors = validator.validate_dependency_graph([spec1])

        assert not is_valid
        assert len(errors) > 0
        assert any("non-existent" in err for err in errors)

    # ==================== Score Calculation Tests ====================

    def test_score_perfect(self, validator, valid_spec):
        """Test perfect spec has score 1.0"""
        result = validator.validate(valid_spec)
        assert result.score == 1.0

    def test_score_decreases_with_warnings(self, validator, valid_spec):
        """Test score decreases with warnings"""
        valid_spec.input_types = {}  # Trigger warning
        result = validator.validate(valid_spec)

        assert result.is_valid  # Still valid
        assert result.score < 1.0  # But score reduced

    def test_score_decreases_with_errors(self, validator, valid_spec):
        """Test score decreases significantly with errors"""
        valid_spec.target_loc = 50  # Trigger error
        result = validator.validate(valid_spec)

        assert not result.is_valid
        assert result.score < 0.8

    def test_score_clamped_to_zero(self, validator, valid_spec):
        """Test score never goes below 0.0"""
        # Create spec with multiple errors
        valid_spec.target_loc = 50
        valid_spec.complexity_limit = 10.0
        valid_spec.test_cases = []
        valid_spec.description = "Create and update and delete and send and fetch"

        result = validator.validate(valid_spec)

        assert result.score >= 0.0
        assert result.score <= 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
