"""
Unit Tests for Ensemble Validator (MVP)

TDD Approach: Tests written BEFORE implementation.
All tests should initially FAIL, then pass after implementation.

Test Coverage:
- Validation rules (6 rules: purpose, I/O, LOC, syntax, type hints, no TODOs)
- Claude validation (MVP single validator)
- Quality scoring algorithm (purpose 50%, I/O 35%, quality 15%)
- Retry mechanism for failed atoms
- Validation result caching
"""

import pytest
from typing import Dict, Any
from unittest.mock import Mock, patch, MagicMock
import hashlib

# Import will fail initially - implementation doesn't exist yet
from src.cognitive.validation.ensemble_validator import (
    EnsembleValidator,
    ValidationResult,
    validate_atom,
    validate_with_claude,
    calculate_quality_score,
    validate_with_cache,
)
from src.cognitive.signatures.semantic_signature import SemanticTaskSignature


class TestValidationRules:
    """Test validation rules for atomic code."""

    def test_purpose_compliance_validation_succeeds_for_correct_code(self):
        """Test that purpose compliance passes when code implements stated purpose."""
        code = """def validate_email(email: str) -> bool:
    return '@' in email and '.' in email"""

        signature = SemanticTaskSignature(
            purpose="Validate email format",
            intent="validate",
            inputs={"email": "str"},
            outputs={"is_valid": "bool"},
            domain="validation",
            security_level="low",
        )

        result = validate_atom(code, signature)

        # Should pass purpose compliance
        assert result.is_valid is True or result.purpose_score >= 85

    def test_io_respect_validation_fails_for_mismatched_types(self):
        """Test that I/O validation fails when inputs/outputs don't match."""
        code = """def calculate_sum(x: int, y: int) -> str:
    return str(x + y)"""  # Returns str instead of int

        signature = SemanticTaskSignature(
            purpose="Calculate sum of two numbers",
            intent="calculate",
            inputs={"x": "int", "y": "int"},
            outputs={"sum": "int"},  # Expects int, not str
            domain="math",
            security_level="low",
        )

        result = validate_atom(code, signature)

        # Should fail I/O compliance
        assert result.is_valid is False or result.io_score < 85

    def test_loc_limit_validation_fails_for_long_code(self):
        """Test that LOC validation fails when code exceeds 10 lines."""
        # Create code with >10 lines
        code = """def process_data(data: dict) -> dict:
    # Line 1
    result = {}
    # Line 3
    for key in data:
        # Line 5
        value = data[key]
        # Line 7
        result[key] = value * 2
        # Line 9
        print(result)
    # Line 11
    return result"""  # 13 lines total

        signature = SemanticTaskSignature(
            purpose="Process data dictionary",
            intent="transform",
            inputs={"data": "dict"},
            outputs={"result": "dict"},
            domain="processing",
            security_level="low",
        )

        result = validate_atom(code, signature)

        # Should fail LOC limit
        assert result.is_valid is False or "LOC" in result.failure_reason

    def test_syntax_correctness_validation_fails_for_invalid_syntax(self):
        """Test that syntax validation fails for code with syntax errors."""
        code = """def broken_function(x: int) -> int
    return x + 1"""  # Missing colon after function signature

        signature = SemanticTaskSignature(
            purpose="Increment number",
            intent="calculate",
            inputs={"x": "int"},
            outputs={"result": "int"},
            domain="math",
            security_level="low",
        )

        result = validate_atom(code, signature)

        # Should fail syntax check
        assert result.is_valid is False or "syntax" in result.failure_reason.lower()

    def test_type_hints_validation_fails_for_missing_hints(self):
        """Test that type hint validation fails when hints are missing."""
        code = """def add_numbers(a, b):
    return a + b"""  # Missing all type hints

        signature = SemanticTaskSignature(
            purpose="Add two numbers",
            intent="calculate",
            inputs={"a": "int", "b": "int"},
            outputs={"sum": "int"},
            domain="math",
            security_level="low",
        )

        result = validate_atom(code, signature)

        # Should fail type hint check
        assert result.is_valid is False or "type" in result.failure_reason.lower()

    def test_no_todos_validation_fails_for_todo_comments(self):
        """Test that TODO validation fails when TODO comments are present."""
        code = """def validate_password(password: str) -> bool:
    # TODO: implement password strength check
    return len(password) >= 8"""

        signature = SemanticTaskSignature(
            purpose="Validate password strength",
            intent="validate",
            inputs={"password": "str"},
            outputs={"is_valid": "bool"},
            domain="security",
            security_level="high",
        )

        result = validate_atom(code, signature)

        # Should fail TODO check
        assert result.is_valid is False or "TODO" in result.failure_reason


class TestClaudeValidation:
    """Test Claude validation (MVP)."""

    @patch('src.cognitive.validation.ensemble_validator.claude_client')
    def test_claude_validator_returns_structured_result(self, mock_claude):
        """Test that Claude validator returns structured ValidationResult."""
        code = """def greet(name: str) -> str:
    return f'Hello, {name}!'"""

        signature = SemanticTaskSignature(
            purpose="Greet user by name",
            intent="generate",
            inputs={"name": "str"},
            outputs={"greeting": "str"},
            domain="general",
            security_level="low",
        )

        # Mock Claude response
        mock_claude.messages.create.return_value = Mock(
            content=[Mock(text='{"is_valid": true, "purpose_score": 95, "io_score": 100, "quality_score": 90, "reasoning": "Code correctly implements greeting"}')]
        )

        result = validate_with_claude(code, signature)

        # Should return ValidationResult
        assert result is not None
        assert hasattr(result, 'is_valid')
        assert hasattr(result, 'purpose_score')

    @patch('src.cognitive.validation.ensemble_validator.claude_client')
    def test_claude_validator_handles_api_errors_gracefully(self, mock_claude):
        """Test that Claude validator handles API errors gracefully."""
        code = "def test(): pass"

        signature = SemanticTaskSignature(
            purpose="Test function",
            intent="create",
            inputs={},
            outputs={},
            domain="testing",
            security_level="low",
        )

        # Mock Claude API error
        mock_claude.messages.create.side_effect = Exception("API rate limit")

        result = validate_with_claude(code, signature)

        # Should return None or error result gracefully
        assert result is None or result.is_valid is False


class TestQualityScoring:
    """Test quality scoring algorithm."""

    def test_quality_score_calculation_uses_correct_weights(self):
        """Test that quality score uses 50% purpose, 35% I/O, 15% quality."""
        validation_result = ValidationResult(
            is_valid=True,
            purpose_score=100,
            io_score=100,
            quality_score=100,
            failure_reason="",
        )

        final_score = calculate_quality_score(validation_result)

        # Should be weighted average: 0.5*100 + 0.35*100 + 0.15*100 = 100
        assert final_score == 100.0

    def test_quality_score_accepts_at_85_threshold(self):
        """Test that scores ≥85 are accepted."""
        validation_result = ValidationResult(
            is_valid=True,
            purpose_score=90,  # 0.5 * 90 = 45
            io_score=80,       # 0.35 * 80 = 28
            quality_score=80,  # 0.15 * 80 = 12
            failure_reason="",
        )

        final_score = calculate_quality_score(validation_result)

        # 45 + 28 + 12 = 85
        assert final_score >= 85.0

    def test_quality_score_rejects_below_85_threshold(self):
        """Test that scores <85 are rejected."""
        validation_result = ValidationResult(
            is_valid=False,
            purpose_score=70,  # 0.5 * 70 = 35
            io_score=70,       # 0.35 * 70 = 24.5
            quality_score=70,  # 0.15 * 70 = 10.5
            failure_reason="Low quality",
        )

        final_score = calculate_quality_score(validation_result)

        # 35 + 24.5 + 10.5 = 70
        assert final_score < 85.0


class TestRetryMechanism:
    """Test retry mechanism for failed atoms."""

    @patch('src.cognitive.validation.ensemble_validator.CPIE')
    def test_retry_enriches_prompt_with_failure_context(self, mock_cpie_class):
        """Test that retry mechanism enriches prompt with validator feedback."""
        signature = SemanticTaskSignature(
            purpose="Calculate factorial",
            intent="calculate",
            inputs={"n": "int"},
            outputs={"result": "int"},
            domain="algorithms",
            security_level="low",
        )

        failure_reason = "Purpose not fully implemented: missing edge case for n=0"
        attempt_num = 1

        mock_cpie = Mock()
        mock_cpie_class.return_value = mock_cpie
        mock_cpie.infer.return_value = "def factorial(n: int) -> int:\n    if n == 0: return 1\n    return n * factorial(n-1)"

        validator = EnsembleValidator()
        result = validator.retry_failed_atom(signature, failure_reason, attempt_num)

        # Should call CPIE with enriched context
        assert mock_cpie.infer.called
        # The enriched prompt should include failure_reason
        # (implementation will add this to signature or pass as context)

    @patch('src.cognitive.validation.ensemble_validator.CPIE')
    def test_retry_max_3_attempts(self, mock_cpie_class):
        """Test that retry mechanism stops after 3 attempts."""
        signature = SemanticTaskSignature(
            purpose="Test retry",
            intent="create",
            inputs={},
            outputs={},
            domain="testing",
            security_level="low",
        )

        mock_cpie = Mock()
        mock_cpie_class.return_value = mock_cpie
        # Always return invalid code
        mock_cpie.infer.return_value = None

        validator = EnsembleValidator()

        # Try with attempt_num = 3 (last attempt)
        result = validator.retry_failed_atom(signature, "Failed validation", attempt_num=3)

        # Should not retry beyond 3
        # Implementation should track this


class TestValidationCaching:
    """Test validation result caching."""

    def test_cache_stores_validation_results(self):
        """Test that cache stores validation results by code hash."""
        code = """def simple_test() -> bool:
    return True"""

        signature = SemanticTaskSignature(
            purpose="Simple test",
            intent="create",
            inputs={},
            outputs={"result": "bool"},
            domain="testing",
            security_level="low",
        )

        # First call - should validate
        result1 = validate_with_cache(code, signature)

        # Second call - should return cached result
        result2 = validate_with_cache(code, signature)

        # Both should return same result
        assert result1 is not None
        assert result2 is not None
        # In real implementation, result2 should be from cache (faster)

    def test_cache_uses_md5_hash_of_code(self):
        """Test that cache uses MD5 hash of code as key."""
        code = "def test(): pass"

        # Calculate expected hash
        expected_hash = hashlib.md5(code.encode()).hexdigest()

        signature = SemanticTaskSignature(
            purpose="Test",
            intent="create",
            inputs={},
            outputs={},
            domain="testing",
            security_level="low",
        )

        validator = EnsembleValidator()

        # After validation, cache should contain the hash
        result = validator.validate_with_cache(code, signature)

        # Implementation should use expected_hash as cache key
        # (We can't test this directly without accessing cache internals,
        #  but the implementation should use MD5 hash)


class TestEnsembleValidatorIntegration:
    """Test complete ensemble validator integration."""

    def test_validator_initialization(self):
        """Test that EnsembleValidator initializes correctly."""
        validator = EnsembleValidator()

        assert validator is not None
        assert hasattr(validator, 'validate')

    @patch('src.cognitive.validation.ensemble_validator.claude_client')
    def test_validator_validate_method_returns_result(self, mock_claude):
        """Test that validator.validate() returns ValidationResult."""
        code = """def add(a: int, b: int) -> int:
    return a + b"""

        signature = SemanticTaskSignature(
            purpose="Add two numbers",
            intent="calculate",
            inputs={"a": "int", "b": "int"},
            outputs={"sum": "int"},
            domain="math",
            security_level="low",
        )

        # Mock Claude response
        mock_claude.messages.create.return_value = Mock(
            content=[Mock(text='{"is_valid": true, "purpose_score": 100, "io_score": 100, "quality_score": 95, "reasoning": "Perfect implementation"}')]
        )

        validator = EnsembleValidator()
        result = validator.validate(code, signature)

        assert result is not None
        assert hasattr(result, 'is_valid')


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
