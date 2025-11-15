"""
Unit Tests for CPIE (Cognitive Pattern Inference Engine)

TDD Approach: Tests written BEFORE implementation.
All tests should initially FAIL, then pass after implementation.

Test Coverage:
- Pattern matching strategy with ≥85% similarity threshold
- First-principles generation when no patterns match
- Retry mechanism with context enrichment (max 3 retries)
- Constraint enforcement (max 10 LOC, syntax, type hints, no TODOs)
- Co-reasoning integration (mocked Claude/DeepSeek calls)
- Synthesis validation (code quality checks)
- Edge cases and error handling
"""

import pytest
from typing import Dict, Any, List, Tuple
from unittest.mock import Mock, patch, MagicMock

# Import will fail initially - implementation doesn't exist yet
from src.cognitive.inference.cpie import (
    CPIE,
    infer_from_pattern,
    infer_from_first_principles,
    validate_constraints,
    retry_with_context,
    validate_synthesis,
)
from src.cognitive.signatures.semantic_signature import SemanticTaskSignature
from src.cognitive.patterns.pattern_bank import PatternBank, StoredPattern


class TestCPIEInitialization:
    """Test CPIE initialization and setup."""

    def test_cpie_initialization_with_dependencies(self):
        """Test CPIE initializes with required dependencies."""
        mock_pattern_bank = Mock(spec=PatternBank)
        mock_co_reasoning = Mock()

        cpie = CPIE(pattern_bank=mock_pattern_bank, co_reasoning_system=mock_co_reasoning)

        assert cpie.pattern_bank == mock_pattern_bank
        assert cpie.co_reasoning_system == mock_co_reasoning
        assert cpie.max_retries == 3  # Default max retries


class TestPatternMatchingStrategy:
    """Test pattern matching inference strategy."""

    def test_infer_from_pattern_finds_similar_pattern_above_threshold(self):
        """Test that infer_from_pattern finds pattern with ≥85% similarity."""
        signature = SemanticTaskSignature(
            purpose="Validate user email format",
            intent="validate",
            inputs={"email": "str"},
            outputs={"is_valid": "bool"},
            domain="authentication",
        )

        # Mock pattern bank with matching pattern
        mock_pattern_bank = Mock(spec=PatternBank)
        mock_pattern = Mock(spec=StoredPattern)
        mock_pattern.pattern_id = "pat_email_001"
        mock_pattern.code = "def validate_email(email: str) -> bool:\n    return '@' in email"
        mock_pattern.similarity_score = 0.92  # Above 85% threshold
        mock_pattern_bank.search_patterns.return_value = [mock_pattern]

        # Mock co-reasoning system
        mock_co_reasoning = Mock()
        mock_co_reasoning.generate_strategy.return_value = "Check for @ symbol"
        mock_co_reasoning.generate_code.return_value = "def validate(email: str) -> bool:\n    return '@' in email"

        result = infer_from_pattern(signature, mock_pattern_bank, mock_co_reasoning)

        assert result is not None
        assert "validate" in result.lower()
        assert "@" in result
        mock_pattern_bank.search_patterns.assert_called_once()

    def test_infer_from_pattern_returns_none_when_no_match_above_threshold(self):
        """Test that infer_from_pattern returns None when similarity < 85%."""
        signature = SemanticTaskSignature(
            purpose="Calculate fibonacci sequence",
            intent="calculate",
            inputs={"n": "int"},
            outputs={"result": "List[int]"},
            domain="algorithms",
        )

        # Mock pattern bank with no good matches
        mock_pattern_bank = Mock(spec=PatternBank)
        mock_pattern = Mock(spec=StoredPattern)
        mock_pattern.similarity_score = 0.45  # Below 85% threshold
        mock_pattern_bank.search_patterns.return_value = [mock_pattern]

        mock_co_reasoning = Mock()

        result = infer_from_pattern(signature, mock_pattern_bank, mock_co_reasoning)

        assert result is None  # No match above threshold

    def test_infer_from_pattern_calls_claude_for_strategy(self):
        """Test that pattern matching calls Claude for strategic reasoning."""
        signature = SemanticTaskSignature(
            purpose="Hash password securely",
            intent="transform",
            inputs={"password": "str"},
            outputs={"hash": "str"},
            domain="security",
        )

        mock_pattern_bank = Mock(spec=PatternBank)
        mock_pattern = Mock(spec=StoredPattern)
        mock_pattern.pattern_id = "pat_hash_001"
        mock_pattern.code = "import bcrypt\ndef hash_pw(pw): return bcrypt.hashpw(pw, salt)"
        mock_pattern.similarity_score = 0.90
        mock_pattern_bank.search_patterns.return_value = [mock_pattern]

        mock_co_reasoning = Mock()
        mock_co_reasoning.generate_strategy.return_value = "Use bcrypt for secure hashing"
        mock_co_reasoning.generate_code.return_value = "import bcrypt\ndef hash_password(password: str) -> str:\n    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()"

        result = infer_from_pattern(signature, mock_pattern_bank, mock_co_reasoning)

        # Verify Claude was called for strategy
        mock_co_reasoning.generate_strategy.assert_called_once()
        # Verify DeepSeek was called for code
        mock_co_reasoning.generate_code.assert_called_once()


class TestFirstPrinciplesStrategy:
    """Test first-principles inference strategy."""

    def test_infer_from_first_principles_generates_code_from_signature(self):
        """Test first-principles generation from semantic signature."""
        signature = SemanticTaskSignature(
            purpose="Parse JSON string to dictionary",
            intent="transform",
            inputs={"json_str": "str"},
            outputs={"data": "dict"},
            domain="data_processing",
        )

        mock_co_reasoning = Mock()
        mock_co_reasoning.generate_strategy.return_value = "Use json.loads to parse string"
        mock_co_reasoning.generate_code.return_value = "import json\ndef parse_json(json_str: str) -> dict:\n    return json.loads(json_str)"

        result = infer_from_first_principles(signature, mock_co_reasoning)

        assert result is not None
        assert "json" in result.lower()
        assert "parse" in result.lower()
        mock_co_reasoning.generate_strategy.assert_called_once()
        mock_co_reasoning.generate_code.assert_called_once()

    def test_infer_from_first_principles_handles_complex_signatures(self):
        """Test first-principles handles complex multi-input/output signatures."""
        signature = SemanticTaskSignature(
            purpose="Merge two sorted lists into one sorted list",
            intent="transform",
            inputs={"list1": "List[int]", "list2": "List[int]"},
            outputs={"merged": "List[int]"},
            domain="algorithms",
            constraints=["Must be O(n) time complexity"],
        )

        mock_co_reasoning = Mock()
        mock_co_reasoning.generate_strategy.return_value = "Two-pointer merge algorithm"
        mock_co_reasoning.generate_code.return_value = "def merge(list1: List[int], list2: List[int]) -> List[int]:\n    # Implementation"

        result = infer_from_first_principles(signature, mock_co_reasoning)

        assert result is not None
        # Should handle constraints in prompting
        call_args = mock_co_reasoning.generate_strategy.call_args
        assert "O(n)" in str(call_args) or "constraint" in str(call_args).lower()


class TestConstraintEnforcement:
    """Test constraint validation for generated code."""

    def test_validate_constraints_passes_for_valid_code(self):
        """Test that valid code passes all constraints."""
        code = """def validate_email(email: str) -> bool:
    if not isinstance(email, str):
        return False
    return '@' in email and '.' in email
"""
        is_valid, errors = validate_constraints(code, max_loc=10)

        assert is_valid is True
        assert len(errors) == 0

    def test_validate_constraints_fails_when_exceeds_max_loc(self):
        """Test that code exceeding max LOC fails validation."""
        # 12 lines of code (exceeds max_loc=10)
        code = """def long_function(x: int) -> int:
    a = 1
    b = 2
    c = 3
    d = 4
    e = 5
    f = 6
    g = 7
    h = 8
    i = 9
    j = 10
    return x + a + b + c + d + e + f + g + h + i + j
"""
        is_valid, errors = validate_constraints(code, max_loc=10)

        assert is_valid is False
        assert any("LOC" in error or "lines" in error for error in errors)

    def test_validate_constraints_fails_for_syntax_errors(self):
        """Test that code with syntax errors fails validation."""
        code = """def broken_function(x: int) -> int
    return x + 1  # Missing colon
"""
        is_valid, errors = validate_constraints(code, max_loc=10)

        assert is_valid is False
        assert any("syntax" in error.lower() for error in errors)

    def test_validate_constraints_fails_for_missing_type_hints(self):
        """Test that code without type hints fails validation."""
        code = """def no_types(x):  # Missing type hints
    return x + 1
"""
        is_valid, errors = validate_constraints(code, max_loc=10)

        assert is_valid is False
        assert any("type hint" in error.lower() for error in errors)

    def test_validate_constraints_fails_for_todo_comments(self):
        """Test that code with TODO comments fails validation."""
        code = """def incomplete(x: int) -> int:
    # TODO: implement this
    return x
"""
        is_valid, errors = validate_constraints(code, max_loc=10)

        assert is_valid is False
        assert any("TODO" in error for error in errors)


class TestRetryMechanism:
    """Test retry mechanism with context enrichment."""

    def test_retry_with_context_succeeds_on_second_attempt(self):
        """Test that retry mechanism succeeds after initial failure."""
        signature = SemanticTaskSignature(
            purpose="Calculate factorial",
            intent="calculate",
            inputs={"n": "int"},
            outputs={"result": "int"},
            domain="algorithms",
        )

        previous_failure = {
            "code": "def factorial(n): return n * factorial(n-1)",  # Missing base case
            "error": "RecursionError: maximum recursion depth exceeded",
        }

        enriched_context = "Add base case for n <= 1"

        mock_co_reasoning = Mock()
        # First retry returns fixed code
        mock_co_reasoning.generate_code.return_value = "def factorial(n: int) -> int:\n    if n <= 1: return 1\n    return n * factorial(n - 1)"

        result = retry_with_context(signature, previous_failure, enriched_context, mock_co_reasoning)

        assert result is not None
        assert "if n <= 1" in result  # Base case added
        mock_co_reasoning.generate_code.assert_called()

    def test_retry_with_context_gives_up_after_max_retries(self):
        """Test that retry mechanism gives up after 3 attempts."""
        signature = SemanticTaskSignature(
            purpose="Impossible task",
            intent="create",
            inputs={},
            outputs={},
            domain="general",
        )

        previous_failure = {"code": "bad code", "error": "SyntaxError"}
        enriched_context = "Fix syntax"

        mock_co_reasoning = Mock()
        # Always return invalid code
        mock_co_reasoning.generate_code.return_value = "still bad code"

        with patch('src.cognitive.inference.cpie.validate_constraints') as mock_validate:
            mock_validate.return_value = (False, ["Syntax error"])

            result = retry_with_context(signature, previous_failure, enriched_context, mock_co_reasoning, max_retries=3)

            # Should give up after 3 retries
            assert result is None or "bad" in result
            assert mock_co_reasoning.generate_code.call_count <= 3


class TestSynthesisValidation:
    """Test synthesis validation for quality checks."""

    def test_validate_synthesis_passes_for_correct_implementation(self):
        """Test that correct implementation passes synthesis validation."""
        code = """def add_numbers(a: int, b: int) -> int:
    return a + b
"""
        purpose = "Add two numbers and return the sum"

        is_valid = validate_synthesis(code, purpose)

        assert is_valid is True

    def test_validate_synthesis_fails_when_purpose_not_implemented(self):
        """Test that code not matching purpose fails validation."""
        code = """def multiply(a: int, b: int) -> int:
    return a * b
"""
        purpose = "Add two numbers and return the sum"  # Code multiplies, not adds

        is_valid = validate_synthesis(code, purpose)

        assert is_valid is False

    def test_validate_synthesis_fails_for_incomplete_implementation(self):
        """Test that incomplete implementation fails validation."""
        code = """def process_data(data: dict) -> dict:
    pass  # Not implemented
"""
        purpose = "Process data dictionary and return transformed result"

        is_valid = validate_synthesis(code, purpose)

        assert is_valid is False


class TestCPIERetryPath:
    """Test CPIE retry mechanism integration."""

    def test_cpie_retries_when_first_principles_fails_validation(self):
        """Test that CPIE retries with context when first-principles fails validation."""
        signature = SemanticTaskSignature(
            purpose="Calculate factorial",
            intent="calculate",
            inputs={"n": "int"},
            outputs={"result": "int"},
            domain="algorithms",
        )

        mock_pattern_bank = Mock(spec=PatternBank)
        # No patterns found
        mock_pattern_bank.search_patterns.return_value = []

        mock_co_reasoning = Mock()
        # First attempt returns invalid code (exceeds LOC)
        invalid_code = "def factorial(n: int) -> int:\n" + "\n".join([f"    x{i} = {i}" for i in range(15)])
        # Second attempt (retry) returns valid code
        valid_code = "def factorial(n: int) -> int:\n    if n <= 1: return 1\n    return n * factorial(n - 1)"

        mock_co_reasoning.generate_strategy.return_value = "Use recursion"
        mock_co_reasoning.generate_code.side_effect = [invalid_code, valid_code]

        cpie = CPIE(pattern_bank=mock_pattern_bank, co_reasoning_system=mock_co_reasoning)

        result = cpie.infer(signature)

        # Should have retried and succeeded
        assert result is not None
        assert "factorial" in result.lower()
        # Should have called generate_code twice (first attempt + retry)
        assert mock_co_reasoning.generate_code.call_count >= 2


class TestSynthesisValidationEdgeCases:
    """Test synthesis validation edge cases."""

    def test_validate_synthesis_fails_for_code_without_logic(self):
        """Test that code with only variable declarations fails validation."""
        code = """def empty_logic(x: int) -> int:
    y = x
    z = y
"""  # No return, no logic
        purpose = "Process number"

        is_valid = validate_synthesis(code, purpose)

        assert is_valid is False  # No meaningful logic


class TestCPIEIntegration:
    """Test CPIE end-to-end integration."""

    def test_cpie_inference_uses_pattern_when_available(self):
        """Test that CPIE uses pattern matching when similar pattern exists."""
        signature = SemanticTaskSignature(
            purpose="Validate email format",
            intent="validate",
            inputs={"email": "str"},
            outputs={"is_valid": "bool"},
            domain="authentication",
        )

        mock_pattern_bank = Mock(spec=PatternBank)
        mock_pattern = Mock(spec=StoredPattern)
        mock_pattern.pattern_id = "pat_email_002"
        mock_pattern.code = "def validate_email(email: str) -> bool:\n    return '@' in email"
        mock_pattern.similarity_score = 0.90
        mock_pattern_bank.search_patterns.return_value = [mock_pattern]

        mock_co_reasoning = Mock()
        mock_co_reasoning.generate_strategy.return_value = "Check for @ symbol"
        mock_co_reasoning.generate_code.return_value = "def validate(email: str) -> bool:\n    return '@' in email"

        cpie = CPIE(pattern_bank=mock_pattern_bank, co_reasoning_system=mock_co_reasoning)

        with patch('src.cognitive.inference.cpie.validate_constraints') as mock_validate:
            mock_validate.return_value = (True, [])

            result = cpie.infer(signature)

            assert result is not None
            # Should use pattern matching path
            mock_pattern_bank.search_patterns.assert_called_once()

    def test_cpie_inference_falls_back_to_first_principles_when_no_pattern(self):
        """Test that CPIE uses first-principles when no pattern matches."""
        signature = SemanticTaskSignature(
            purpose="Novel algorithm implementation",
            intent="create",
            inputs={"data": "List[int]"},
            outputs={"result": "int"},
            domain="algorithms",
        )

        mock_pattern_bank = Mock(spec=PatternBank)
        # No patterns found or similarity too low
        mock_pattern_bank.search_patterns.return_value = []

        mock_co_reasoning = Mock()
        mock_co_reasoning.generate_strategy.return_value = "Novel approach"
        mock_co_reasoning.generate_code.return_value = "def novel(data: List[int]) -> int:\n    return sum(data)"

        cpie = CPIE(pattern_bank=mock_pattern_bank, co_reasoning_system=mock_co_reasoning)

        with patch('src.cognitive.inference.cpie.validate_constraints') as mock_validate:
            mock_validate.return_value = (True, [])

            result = cpie.infer(signature)

            assert result is not None
            # Should use first-principles path
            mock_co_reasoning.generate_strategy.assert_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
